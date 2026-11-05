"""Diagnose ordinary feedback ingress through the installed Core callback.

This is a known-gap probe, NOT feedback-learning acceptance. Synthetic owner,
consents and transport; actual installed plugin, route and post-admission hook.
No preseeded user outcomes, models, network or physical messages.
"""
import asyncio
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

import run_core_session_routing as core
from run_core_guided_setup import cli


async def exercise(home):
    home.mkdir()
    shutil.copytree(core.repo, home/'plugins/hermes-alive')
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'auto','default':'synthetic-owner-model'}}), encoding='utf-8')
    rc, staged = cli(home, 'setup', '--confirm-model-calls', '--confirm-delivery',
        '--confirm-outbound-retention', '--interests', 'public synthetic science')
    assert rc == 0
    assert cli(home, 'install-runtime', '--engine', 'kernel')[0] == 0
    token = core.set_hermes_home_override(home)
    manager = None
    try:
        manager = core.get_plugin_manager()
        manager.discover_and_load()
        loaded = manager._plugins['hermes-alive']
        assert loaded.enabled and not loaded.error
        binding = loaded.module._gateway_host_binding
        adapter = core.Adapter(core.Platform.TELEGRAM)
        runner = core.runner_for(home, {core.Platform.TELEGRAM:adapter})
        adapter.gateway_runner = runner
        await adapter.connect()
        source = core.SessionSource(platform=core.Platform.TELEGRAM,
            chat_id='synthetic-feedback-peer', user_id='synthetic-feedback-owner',
            message_id='synthetic-confirm')
        session = runner.session_store.get_or_create_session(source)
        from hermes_cli.plugins import get_plugin_command_handler
        command = get_plugin_command_handler('alive')
        async def owner_command(text):
            return await runner._hm_run_plugin_handler(command, None, source,
                session_entry=session, args=text)
        assert '已确认' in await owner_command(staged['confirmation_command'].removeprefix('/alive '))
        assert '已启用' in await owner_command('enable')
        assert binding.native._caller is None
        binding.arguments['stop'].set()
        await binding.task
        # Resolve the installed package, never a different checkout's kernel.
        from importlib import import_module
        bridge = import_module(loaded.module.__name__+'.kernel_setup_bridge')
        store = bridge.setup_store(binding)
        configured = store.configuration()
        def kernel(name):
            return import_module(store.__class__.__module__.rsplit('.', 1)[0]+'.'+name)
        Sensitivity = kernel('events').Sensitivity
        EventEnvelope = kernel('events').EventEnvelope
        # Synthetic consent fixture demonstrates that merely granting retention
        # and consolidation does not connect the configured input to feedback.
        kernel('retention').RetentionProjection(store.journal, content_vault=store.vault).append_consent(
            subject=configured.subject, actor=configured.subject, enabled=True,
            retention_days=2, directions=('inbound','outbound'), sensitivity=Sensitivity.PRIVATE)
        store.journal.append(EventEnvelope(event_type='consolidation.consent_changed',
            source='hermes.command.memory', actor=configured.subject, subject=configured.subject,
            sensitivity=Sensitivity.PRIVATE, payload={'enabled':True}))
        from gateway.run_inbound_consumer import run_post_admission_hook
        initial_ids = {row.event.event_id for row in store.journal.read(event_type='conversation.inbound')}
        texts = ('有点意思，但是略偏长', '不是不喜欢这个话题，我只是现在没空看。',
                 '转述：有人说“太长了”；这不是我的评价。')
        for index, text in enumerate(texts):
            event = SimpleNamespace(message_id='synthetic-feedback-'+str(index), text=text,
                reply_to_message_id='synthetic-outbound', reply_to_text='synthetic quoted share',
                reply_to_is_own_message=True)
            assert await run_post_admission_hook(runner, event, source, session.session_key) == (False, None)
        captured = [row for row in store.journal.read(event_type='conversation.inbound')
                    if row.event.event_id not in initial_ids]
        assert len(captured) == len(texts), 'each admitted test message must be observed exactly once'
        assert all(row.event.payload.get('method') == 'configured-input-wake-v1' and
            row.event.payload.get('erasable_content_stored') is False and
            row.event.payload.get('learning_authority_granted') is False for row in captured)
        assert not store.journal.read(event_type='outcome.recorded')
        reader = kernel('feedback_context').FeedbackContextReader(store.journal, content_vault=store.vault)
        assert reader.read(subject=configured.subject, clearance=Sensitivity.PRIVATE) == ()
        persisted = store.journal.path.read_bytes()
        assert all(text.encode('utf-8') not in persisted for text in texts)
        assert not store.journal.read(event_type='dispatch.started')
        print('CORE_FEEDBACK_INGRESS_GAP '+json.dumps(dict(
            installed_plugin=True, actual_post_admission_dispatch=True,
            actual_gateway_authorization_proven=False, synthetic_consent_fixture=True,
            inbound_observations=len(captured), consumed=False, retained_feedback_bodies=0,
            attributed_user_outcomes=0, feedback_context_items=0,
            product_feedback_learning_qualified=False, model_calls=0, sends=0)))
    finally:
        if manager is not None:
            manager.unload()
        core.reset_hermes_home_override(token)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-feedback-ingress-') as directory:
        try:
            asyncio.run(exercise(Path(directory)/'profile'))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
