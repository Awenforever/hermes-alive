"""Installed-byte Core CLI + native command confirmation, no models/messages.

Public discovery and actual Gateway command dispatch use synthetic admitted
sources. This is not remote consumer dependency admission or live activation.
"""
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import run_core_session_routing as core


def cli(home,*arguments):
    environment={**os.environ,'HERMES_HOME':str(home),'HERMES_ACCEPT_HOOKS':'1',
                 'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run([sys.executable,'-B','-m','hermes_cli.main','alive',*arguments],
        env=environment,capture_output=True,text=True,timeout=120)
    # Never echo command output: setup's one-use code belongs only to its caller.
    decoder=json.JSONDecoder()
    for index,char in enumerate(result.stdout):
        if char=='{':
            try:document,end=decoder.raw_decode(result.stdout[index:])
            except ValueError:continue
            if isinstance(document,dict) and 'ok' in document:
                return result.returncode,document
    raise AssertionError('actual Core plugin CLI did not return a result')


async def test(home):
    home.mkdir()
    installed=home/'plugins/hermes-alive'
    shutil.copytree(core.repo,installed)
    original_model={'provider':'auto','default':'owner-configured-model'}
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':original_model}),encoding='utf-8')
    legacy=home/'plugin-data/hermes-alive/runtime/legacy-fixture.json'
    legacy.parent.mkdir(parents=True)
    legacy.write_text('LEGACY_PRESERVE_SENTINEL',encoding='utf-8')
    rc,denied=cli(home,'setup')
    assert rc==2 and denied['confirmation_required'] is True
    rc,denied=cli(home,'setup','--confirm-model-calls','--confirm-delivery')
    assert rc==2 and denied['confirmation_required'] is True
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery',
                  '--confirm-outbound-retention','--retention-days','30')
    assert rc==0 and staged['ok'] and staged['delivery_enabled'] is False
    assert staged['phase']=='awaiting_authorized_conversation_confirmation'
    command=staged['confirmation_command'].removeprefix('/alive ')
    token_text=command.split()[1]
    rc,installed_result=cli(home,'install-runtime','--engine','kernel-shadow')
    assert rc==0 and installed_result['engine']=='kernel-shadow'
    token=core.set_hermes_home_override(home)
    manager=None
    try:
        manager=core.get_plugin_manager()
        manager.discover_and_load()
        loaded=manager._plugins['hermes-alive']
        assert loaded.enabled and loaded.error is None
        binding=loaded.module._gateway_host_binding
        from hermes_cli.plugins import get_plugin_command_handler
        handler=get_plugin_command_handler('alive')
        assert callable(handler) and binding.channels and binding.native is None
        adapter=core.Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter})
        adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='PRIVATE_CORE_SETUP_CHAT',
            user_id='PRIVATE_CORE_SETUP_USER',thread_id='7',message_id='synthetic-confirmation')
        # A slash command alone must not fabricate a routing session.
        no_session=await runner._hm_run_plugin_handler(handler,None,source,args=command)
        assert '普通消息' in no_session
        entry=runner.session_store.get_or_create_session(source)
        reply=await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=command)
        assert '已确认' in reply and '未启用' in reply
        assert binding._continuity is not None and binding.native is None and binding.task is None
        setup_bridge=__import__(loaded.module.__name__+'.kernel_setup_bridge',fromlist=['setup_store'])
        store=setup_bridge.setup_store(binding)
        configured=store.configuration()
        assert configured is not None and configured.options['model'] is None
        assert configured.scope['chat_id']==source.chat_id
        assert configured.scope['session_id']==entry.session_id
        assert not store.journal.read(event_type='action.delegation_granted')
        assert not store.journal.read(event_type='autonomy.policy_changed')
        assert not store.journal.read(event_type='dispatch.started')
        assert token_text.encode() not in store.journal.path.read_bytes()
        assert b'PRIVATE_CORE_SETUP_' not in store.journal.path.read_bytes()
        # A repeated confirmation is not another setup, receiver or activation.
        repeated=await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=command)
        assert '已确认' in repeated
        wrong=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id=source.chat_id,
            user_id='other-user',thread_id='7',message_id='synthetic-foreign')
        wrong_entry=runner.session_store.get_or_create_session(wrong)
        refused=await runner._hm_run_plugin_handler(handler,None,wrong,session_entry=wrong_entry,args=command)
        assert '未完成' in refused
        assert store.configuration().subject==configured.subject
        # Startup restores the configured reader through its actual entry;
        # it must NOT start the shadow/legacy sender or claim live enablement.
        before=binding._continuity
        result=await loaded.module.kernel_gateway_startup()
        assert result['status']=='not_configured'
        assert binding._continuity is before and not before._closed
        assert binding.native is None and binding.task is None
        rc,enabled=cli(home,'enable')
        assert rc==2 and enabled['authorized_conversation_required'] is True
        assert enabled['legacy_fallback_allowed'] is False
        rc,status=cli(home,'status')
        assert rc==0 and status['setup_phase']=='configured_not_activated'
        assert status['enabled'] is False and status['live_runtime_verified'] is False
        # Uninstall/reinstall preserves configuration, identity and confirmation,
        # without applying an installed-file overlay or reviving delivery.
        rc,removed=cli(home,'uninstall-runtime')
        assert rc==0 and removed['user_state_preserved']
        rc,reinstalled=cli(home,'install-runtime')
        assert rc==0 and reinstalled['engine']=='kernel-shadow'
        assert store.configuration().event_id==configured.event_id
        assert legacy.read_text(encoding='utf-8')=='LEGACY_PRESERVE_SENTINEL'
        from hermes_yaml import safe_load
        assert safe_load((home/'config.yaml').read_text())['model']==original_model
        assert token_text not in (home/'config.yaml').read_text()
        assert 'PRIVATE_CORE_SETUP_' not in (home/'config.yaml').read_text()
        assert not store.journal.read(event_type='action.delegation_granted')
        # Status must diagnose missing migrated keys, never silently seed a
        # replacement installation identity. Restore only this synthetic key.
        key=store.protector.key_path
        saved=key.read_bytes()
        key.unlink()
        rc,status=cli(home,'status')
        assert rc==0 and status['setup_phase']=='recovery_required' and not key.exists()
        key.write_bytes(saved)
        # A surviving Core setup hint also fences a completely missing store.
        # Preserve/restore this synthetic directory; never seed another identity.
        backup=home/'synthetic-kernel-backup'
        store.root.rename(backup)
        rc,refused_setup=cli(home,'setup','--confirm-model-calls','--confirm-delivery',
            '--confirm-outbound-retention','--replace')
        assert rc==2 and refused_setup['configuration_recovery_required'] is True
        assert refused_setup['identity_replaced'] is False and not store.root.exists()
        backup.rename(store.root)
        assert store.configuration().event_id==configured.event_id
        print('HERMES_ALIVE_CORE_GUIDED_SETUP_OK')
    finally:
        if manager is not None:manager.unload()
        core.reset_hermes_home_override(token)


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-guided-setup-') as directory:
        try:asyncio.run(test(Path(directory)/'profile'))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
