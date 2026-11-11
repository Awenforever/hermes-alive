"""Cold Core plugin handoff on one isolated profile with a pending erasure."""

import asyncio
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

import run_core_session_routing as core
from run_core_guided_setup import cli


def select_fixture_plugin(home, enabled):
    # This fixture swaps local source trees without involving package
    # admission. Core still reads its normal profile selection at startup.
    from hermes_cli.config import load_config, save_config
    token = core.set_hermes_home_override(home)
    try:
        config = load_config()
        plugins = config.setdefault('plugins', {})
        for name, selected in (('enabled', enabled), ('disabled', not enabled)):
            keys = set(plugins.get(name) or ()) - {'hermes-alive'}
            if selected:
                keys.add('hermes-alive')
            plugins[name] = sorted(keys)
        save_config(config)
    finally:
        core.reset_hermes_home_override(token)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def phase(home, stage):
    from gateway.hooks import HookRegistry
    from hermes_cli.plugins import get_plugin_command_handler
    from hermes_state_registry import close_all_under

    manager = core.get_plugin_manager()
    try:
        manager.discover_and_load()
        loaded = manager._plugins.get('hermes-alive')
        adapter = core.Adapter(core.Platform.TELEGRAM)
        runner = core.runner_for(home, {core.Platform.TELEGRAM: adapter})
        adapter.gateway_runner = runner
        assert await adapter.connect()
        source = core.SessionSource(platform=core.Platform.TELEGRAM, chat_id='synthetic-rollback-chat',
                                    user_id='synthetic-rollback-owner', message_id='synthetic-rollback-message')
        session = runner.session_store.get_or_create_session(source)
        assert (await adapter.get_chat_info(source.chat_id))['type'] == 'dm'
        snapshot_path = home / 'expected.json'
        expected = json.loads(snapshot_path.read_text()) if snapshot_path.exists() else None
        if expected:
            assert session.session_id == expected['session']
            assert digest(home / expected['key_path']) == expected['key_digest']
        hooks = HookRegistry()
        hooks.discover_and_load()
        if stage == 'dormant':
            assert loaded is None or not loaded.enabled
            assert get_plugin_command_handler('alive') is None
            assert await hooks.emit_collect('gateway:startup', {}) == [
                {'status': 'plugin_unavailable', 'legacy_allowed': False}]
            return
        assert loaded.enabled and loaded.error is None
        binding = loaded.module._gateway_host_binding
        if stage == 'old-active':
            assert await hooks.emit_collect('gateway:startup', {}) == []
            assert binding.native is None and binding.task is None
            setup = importlib.import_module(loaded.module.__name__ + '.kernel_setup_bridge')
            try:
                setup.setup_store(binding)
            except RuntimeError as error:
                assert str(error) == 'unsupported content-vault schema'
            else:
                raise AssertionError('old plugin opened upgraded storage')
            return
        setup = importlib.import_module(loaded.module.__name__ + '.kernel_setup_bridge')
        if stage == 'legacy':
            code_path = home / 'synthetic-setup-command'
            handler = get_plugin_command_handler('alive')
            reply = await runner._hm_run_plugin_handler(handler, None, source, session_entry=session,
                                                       args=code_path.read_text())
            code_path.unlink()
            assert '已确认' in reply
        assert (await hooks.emit_collect('gateway:startup', {}))[0]['status'] == 'not_configured'
        assert binding.native is None and binding.task is None
        store = setup.setup_store(binding)
        config = store.configuration()
        assert store.activation() is None
        vault, subject = store.vault, config.subject
        if stage == 'legacy':
            vault.put_json('old feedback', subject=subject, purpose='test.feedback', content_id='feedback:rollback')
            vault.put_json('kept history', subject=subject, purpose='test.history', content_id='history:rollback')
            vault.create_managed_backup('before-service-upgrade')
            snapshot_path.write_text(json.dumps(dict(session=session.session_id, subject=subject,
                configuration=config.event_id, key_path=vault.key_path.relative_to(home).as_posix(),
                key_digest=digest(vault.key_path))))
        else:
            assert subject == expected['subject'] and config.event_id == expected['configuration']
            assert vault.resolve_json('history:rollback') == 'kept history'
        if stage == 'upgrade':
            assert vault.resolve_json('feedback:rollback') == 'old feedback'
            vault.put_json('linked body', subject=subject, purpose='test.plan',
                           content_id='plan:rollback', depends_on=('feedback:rollback',))
            with patch.object(vault, '_purge_affected_backups', side_effect=OSError('interrupted purge')):
                try:
                    vault.erase_item('feedback:rollback')
                except OSError as error:
                    assert str(error) == 'interrupted purge'
                else:
                    raise AssertionError('purge interruption was not exercised')
            assert vault.pending_erasure_jobs() and (vault.backup_root / 'before-service-upgrade').exists()
        if stage == 'restored':
            assert not vault.pending_erasure_jobs() and not (vault.backup_root / 'before-service-upgrade').exists()
            erased = importlib.import_module(store.__class__.__module__.rsplit('.', 1)[0] + '.content_vault').ContentErasedError
            for content_id in ('feedback:rollback', 'plan:rollback'):
                try:
                    vault.resolve_json(content_id)
                except erased:
                    assert vault.explicit_erasure_recorded(content_id)
                else:
                    raise AssertionError('withdrawn body returned after service rollback')
        assert not store.journal.read(event_type='dispatch.started')
    finally:
        manager.unload()
        close_all_under(home)


def exercise(home, previous):
    def run(stage):
        subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--core', str(core.args.core.resolve())],
            env={**os.environ, 'HERMES_HOME': str(home), 'HERMES_ALIVE_ROLLBACK_PHASE': stage},
            check=True, timeout=180)

    plugin = home / 'plugins/hermes-alive'
    shutil.copytree(previous, plugin, ignore=shutil.ignore_patterns('.git'))
    (home / 'config.yaml').write_text(json.dumps({'plugins': {'enabled': ['hermes-alive']}}))
    rc, staged = cli(home, 'setup', '--confirm-model-calls', '--confirm-delivery',
                     '--confirm-outbound-retention', '--confirm-share-feedback')
    assert rc == 0
    (home / 'synthetic-setup-command').write_text(staged['confirmation_command'].removeprefix('/alive '))
    assert cli(home, 'install-runtime', '--engine', 'kernel')[0] == 0
    run('legacy')
    old, new = home / 'previous-alive', home / 'candidate-alive'
    plugin.rename(old)
    shutil.copytree(core.repo, plugin, ignore=shutil.ignore_patterns('.git'))
    assert cli(home, 'install-runtime', '--engine', 'kernel')[0] == 0
    run('upgrade')
    plugin.rename(new)
    old.rename(plugin)
    run('old-active')
    plugin.rename(old)
    new.rename(plugin)
    select_fixture_plugin(home, False)
    plugin.rename(new)
    old.rename(plugin)
    run('dormant')
    plugin.rename(old)
    new.rename(plugin)
    select_fixture_plugin(home, True)
    run('restored')
    print('HERMES_ALIVE_CORE_FEEDBACK_ROLLBACK_OK', flush=True)


if __name__ == '__main__':
    stage = os.environ.get('HERMES_ALIVE_ROLLBACK_PHASE')
    if stage:
        asyncio.run(phase(Path(os.environ['HERMES_HOME']), stage))
    else:
        with tempfile.TemporaryDirectory(prefix='alive-core-feedback-rollback-') as directory:
            exercise(Path(directory), Path(os.environ['HERMES_ALIVE_ROLLBACK_PREVIOUS']))
