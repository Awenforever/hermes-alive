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
from unittest.mock import patch

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
    explicit_interests='Scientific history and public infrastructure; other worthwhile discoveries are welcome.'
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery',
                  '--confirm-outbound-retention','--retention-days','30',
                  '--interests',explicit_interests,'--confirm-hermes-profile-memory')
    assert rc==0 and staged['ok'] and staged['delivery_enabled'] is False
    assert staged['phase']=='awaiting_authorized_conversation_confirmation'
    assert staged['confirmation_summary']['interest_preferences']==explicit_interests
    assert staged['confirmation_summary']['explicit_interest_memory_until_updated_or_forgotten'] is True
    assert staged['confirmation_summary']['public_queries']==[]
    assert staged['confirmation_summary']['use_personal_hermes_curated_user_profile'] is True
    assert staged['confirmation_summary']['external_memory_provider_recall_enabled'] is False
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
        from importlib import import_module
        package=store.__class__.__module__.rsplit('.',1)[0]
        CognitionContextReader=import_module(package+'.cognition_context').CognitionContextReader
        Sensitivity=import_module(package+'.events').Sensitivity
        preferences=CognitionContextReader(store.journal).read(subject=configured.subject,clearance=Sensitivity.PRIVATE)
        assert any(p.predicate=='profile.interests' and p.value==explicit_interests
            and p.source_event_ids==(configured.event_id,) for p in preferences)
        assert explicit_interests.encode() not in store.journal.path.read_bytes()
        # Consume the current Core-curated profile, not a second chat logger or
        # a permanent user-explicit MemoryProposal. These are synthetic files.
        from tools.memory_tool import MemoryStore
        core_profile=MemoryStore();core_profile.load_from_disk()
        profile_text='SYNTHETIC_CORE_CURATED_USER_PROFILE_SENTINEL'
        assert core_profile.add('user',profile_text)['success']
        before={p.name:p.read_bytes() for p in (home/'memories').iterdir() if p.is_file()}
        reader=CognitionContextReader(store.journal)
        def advice():return [p for p in reader.read(subject=configured.subject,clearance=Sensitivity.PRIVATE)
                            if p.kind=='core_curated_advisory']
        observed=advice()
        assert len(observed)==1 and profile_text in observed[0].value
        assert observed[0].predicate=='profile.hermes_curated'
        assert before=={p.name:p.read_bytes() for p in (home/'memories').iterdir() if p.is_file()}
        assert profile_text.encode() not in store.journal.path.read_bytes()
        assert advice()==observed
        assert len(store.journal.read(event_type='memory.core_profile_observed'))==1
        with patch.object(MemoryStore,'load_from_disk',side_effect=AssertionError('unauthorized Core profile read')):
            assert not any(p.kind=='core_curated_advisory' for p in reader.read(
                subject=configured.subject,clearance=Sensitivity.PUBLIC))
            assert not reader.read(subject='user:foreign',clearance=Sensitivity.PRIVATE)
            from hermes_yaml import safe_load
            saved_config_bytes=(home/'config.yaml').read_bytes()
            saved_config=safe_load(saved_config_bytes.decode('utf-8'))
            disabled_config={**saved_config,'memory':{'user_profile_enabled':False}}
            (home/'config.yaml').write_text(json.dumps(disabled_config))
            try:assert advice()==[]
            finally:(home/'config.yaml').write_bytes(saved_config_bytes)
        assert core_profile.remove('user',profile_text)['success']
        assert advice()==[],'forgotten Core profile came back from an Alive cache'
        assert len(store.journal.read(event_type='memory.proposed'))==1
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
        # A pending Alive subject-forget blocks an old read grant before the
        # erase worker runs, without deleting Core's separately owned memory.
        assert core_profile.add('user','SYNTHETIC_UPDATED_CORE_PROFILE')['success']
        assert 'SYNTHETIC_UPDATED_CORE_PROFILE' in advice()[0].value
        retention=import_module(package+'.retention').RetentionProjection(store.journal)
        retention.append_erasure_request(subject=configured.subject,actor=configured.subject,
            operation_id='synthetic-profile-context-forget')
        profile_reader=import_module(package+'.core_profile_context').read_core_profile_evidence
        with patch.object(MemoryStore,'load_from_disk',side_effect=AssertionError('forgotten Core read grant revived')):
            assert profile_reader(store.journal,subject=configured.subject) is None
        assert 'SYNTHETIC_UPDATED_CORE_PROFILE' in (home/'memories/USER.md').read_text()
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
