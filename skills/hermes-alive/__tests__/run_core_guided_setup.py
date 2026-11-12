"""Installed-byte Core CLI + native command confirmation, no models/messages.

Public discovery and actual Gateway command dispatch use synthetic admitted
sources. This is not remote consumer dependency admission or live activation.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib import import_module
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


async def test(home,*,public_refinement=False,adaptive_import=False):
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
    public_options=('--public-query','public synthetic topic','--confirm-public-reads','--confirm-cited-reads',
                    '--confirm-public-refinement') if public_refinement else ()
    setup_args=('setup','--confirm-model-calls','--confirm-delivery',
                  '--confirm-outbound-retention','--retention-days','30',
                  '--interests',explicit_interests,'--confirm-hermes-profile-memory',*public_options)
    quiet={'start':'22:45','end':'08:15','timezone':'Asia/Shanghai'} if public_refinement else None
    if quiet:
        legacy_config=legacy.parent/'config/hermes-alive.json'
        legacy_config.parent.mkdir()
        legacy_bytes=b'{"values":{"enabled":false,"quiet_start":"22:45","quiet_end":"08:15","timezone":"Asia/Shanghai"}}'
        dynamic=json.loads(legacy_bytes)
        dynamic['values'].update(circadian_enabled=True,circadian_mode='live',circadian_timezone='UTC')
        legacy_config.write_text(json.dumps(dynamic),encoding='utf-8')
        circadian_state=legacy.parent/'circadian_state.json'
        now=datetime.now(timezone.utc)
        schedule_date=(now-timedelta(days=int(now.hour<12))).date().isoformat()
        raw=json.dumps({'schema_version':1,'phase':'awake','schedule_date':schedule_date,
            'planned_sleep_at':(now+timedelta(hours=3)).isoformat(),
            'planned_wake_at':(now+timedelta(hours=11)).isoformat(),
            'learned_sleep_offset_minutes':18,'learned_wake_offset_minutes':-9,'sleep_debt_minutes':0,
            'history':[{'private_note':'DO_NOT_EXPORT'}]}).encode()
        circadian_state.write_bytes(raw)
        rc,preview=cli(home,'contact-hours')
        assert rc==0 and preview['legacy_contact_hours']['state']=='dynamic'
        assert preview['legacy_contact_hours']['adaptive_contact']=={'state':'open','timezone':'UTC','checkpoint_schema':1}
        assert circadian_state.read_bytes()==raw and not list(legacy.parent.glob('*.lock'))
        assert 'DO_NOT_EXPORT' not in json.dumps(preview)
        circadian_state.write_bytes(b'invalid fixture')
        rc,preview=cli(home,'contact-hours')
        assert rc==0 and preview['legacy_contact_hours']['adaptive_contact']=={'state':'unavailable'}
        assert circadian_state.read_bytes()==b'invalid fixture'
        if adaptive_import:
            rc,refused=cli(home,*setup_args,'--stage-legacy-adaptive-contact')
            assert rc==2 and refused['adaptive_checkpoint_unavailable'] is True
            protected=json.loads(raw)
            protected['planned_sleep_at']=(now-timedelta(hours=1)).isoformat()
            protected['planned_wake_at']=(now+timedelta(hours=3)).isoformat()
            raw=json.dumps(protected).encode()
            circadian_state.write_bytes(raw)
            setup_args=(*setup_args,'--stage-legacy-adaptive-contact')
        else:
            circadian_state.unlink()
            legacy_config.write_bytes(legacy_bytes)
            rc,preview=cli(home,'contact-hours')
            assert rc==0 and preview['legacy_contact_hours']=={'state':'fixed','window':quiet}
            rc,required=cli(home,*setup_args)
            assert rc==2 and required['contact_hours_choice_required'] is True
            setup_args=(*setup_args,'--keep-legacy-quiet-window')
    rc,staged=cli(home,*setup_args)
    assert rc==0 and staged['ok'] and staged['delivery_enabled'] is False
    assert staged['phase']=='awaiting_authorized_conversation_confirmation'
    assert staged['confirmation_summary']['interest_preferences']==explicit_interests
    assert staged['confirmation_summary']['quiet_window']==(None if adaptive_import else quiet)
    if adaptive_import:
        assert staged['confirmation_summary']['adaptive_contact']=={
            'state':'staged','timezone':'UTC','activation_ready':False}
        assert 'source_digest' not in json.dumps(staged) and 'planned_sleep_at' not in json.dumps(staged)
    assert staged['confirmation_summary']['explicit_interest_memory_until_updated_or_forgotten'] is True
    assert staged['confirmation_summary']['public_queries']==(['public synthetic topic'] if public_refinement else [])
    assert staged['confirmation_summary']['public_source_refinement'] is public_refinement
    assert staged['confirmation_summary']['additional_public_queries_per_cycle']==int(public_refinement)
    assert staged['confirmation_summary']['private_context_in_public_query_planning'] is False
    assert staged['confirmation_summary']['use_personal_hermes_curated_user_profile'] is True
    assert staged['confirmation_summary']['external_memory_provider_recall_enabled'] is False
    command=staged['confirmation_command'].removeprefix('/alive ')
    token_text=command.split()[1]
    engine='kernel' if adaptive_import else 'kernel-shadow'
    rc,installed_result=cli(home,'install-runtime','--engine',engine)
    assert rc==0 and installed_result['engine']==engine
    token=core.set_hermes_home_override(home)
    manager=None
    try:
        # Actual Core plugin removal clears its config hint but preserves the
        # separately owned Alive state. Confirmation must use signed state,
        # while still requiring the original valid challenge and Core route.
        from hermes_cli.plugins_state import save_plugin_setting
        save_plugin_setting('hermes-alive',('kernel_setup',),{})
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
        if adaptive_import:
            assert '旧版动态作息检查点已私下保存' in reply
            snapshot=configured.options['adaptive_contact']
            assert snapshot['checkpoint']['learned_sleep_offset_minutes']==18
            assert snapshot['checkpoint']['pending_sleep_at'] is None
            assert 'history' not in snapshot['checkpoint'] and 'DO_NOT_EXPORT' not in repr(snapshot)
            from hashlib import sha256
            assert snapshot['source_digest']==sha256(raw).hexdigest()
            assert circadian_state.read_bytes()==raw
            assert not store.activation() and not store.journal.read(event_type='action.delegation_granted')
            assert snapshot['source_digest'].encode() not in store.journal.path.read_bytes()
            rc,status=cli(home,'status')
            assert rc==0 and status['contact_hours']['state']=='adaptive_staged' and not status['enabled']
            async def command(argument):
                return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=argument)
            circadian_state.write_bytes(raw+b' ')
            assert '未完成' in await command('enable') and not store.activation()
            assert not store.journal.read(event_type='action.delegation_granted')
            circadian_state.write_bytes(raw)
            assert '已启用' in await command('enable')
            projection_module=import_module(loaded.module.__name__+'.kernel_execution_bridge').kernel('adaptive_contact')
            projection_type=projection_module.AdaptiveContactProjection
            try:
                async with asyncio.timeout(20):
                    while not store.journal.read(event_type='autonomous.host.closed'):
                        assert not binding.task.done(),binding.task.result()
                        await asyncio.sleep(.03)
                closed=store.journal.read(event_type='autonomous.host.closed')[-1].event
                assert closed.payload['disposition']=='contact_hours_closed'
                current,checkpoint=projection_type(setup_bridge.setup_store(binding),configured).current()
                assert current is not None and checkpoint['phase'] in ('asleep','light_sleep')
                assert checkpoint['learned_sleep_offset_minutes']==18
                assert binding.native.last_call_count==0 and not store.journal.read(event_type='dispatch.started')
                assert circadian_state.read_bytes()==raw
                assert '动态免打扰' in await command('status')
                rc,status=cli(home,'status')
                assert rc==0 and status['contact_hours']['state']=='adaptive_quiet' and status['enabled']
            finally:
                binding.arguments['stop'].set()
                await asyncio.wait_for(asyncio.shield(binding.task),10)
            # Interleave two owners of the same committed generation at the
            # precise CAS boundary, without depending on thread scheduling.
            first_store=setup_bridge.setup_store(binding)
            second_store=setup_bridge.setup_store(binding)
            first=projection_type(first_store,configured)
            second=projection_type(second_store,configured)
            authority=first_store.activation()
            after_wake=current.observed_at.replace(hour=13,minute=0,second=0,microsecond=0)+timedelta(days=1)
            original_append=first_store.journal.append
            winner=[]
            def competing_append(event, **kwargs):
                if event.event_type==projection_type.EVENT:
                    winner.append(second.advance(authority,after_wake+timedelta(seconds=1)))
                return original_append(event,**kwargs)
            with patch.object(first_store.journal,'append',competing_append):
                try:
                    first.advance(authority,after_wake)
                except projection_module.AdaptiveContactChanged:
                    pass
                else:
                    raise AssertionError('stale adaptive writer overwrote the new checkpoint')
            reopened=projection_type(setup_bridge.setup_store(binding),configured)
            final_event,final_checkpoint=reopened.current()
            assert winner==[final_checkpoint] and final_event.causation_id==current.event_id
            assert reopened.evaluate(final_checkpoint,after_wake+timedelta(seconds=1))[0]
            assert len(store.journal.read(event_type=projection_type.EVENT))==2
            assert circadian_state.read_bytes()==raw and not store.journal.read(event_type='dispatch.started')
            print('HERMES_ALIVE_CORE_ADAPTIVE_CUTOVER_OK')
            return
        if quiet:
            assert dict(configured.options['quiet_window'])==quiet
            assert '22:45–08:15' in reply and legacy_config.read_bytes()==legacy_bytes
        assert configured.options.get('refine_public_sources',False) is public_refinement
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
        foreign_home=home/'synthetic-foreign-home'
        foreign_token=core.set_hermes_home_override(foreign_home)
        try:
            with patch.object(MemoryStore,'load_from_disk',side_effect=AssertionError('foreign home read Core profile')):
                assert advice()==[]
            assert not foreign_home.exists()
        finally:core.reset_hermes_home_override(foreign_token)
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
        status_reply=await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args='status')
        if quiet:
            assert status['contact_hours']['window']==quiet and status['contact_hours']['state'] in ('quiet','open')
            assert '22:45–08:15（Asia/Shanghai）' in status_reply
        else:
            assert status['contact_hours']=={'state':'unrestricted','window':None}
            assert '主动联系时段不限' in status_reply
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
        try:
            asyncio.run(test(Path(directory)/'profile'))
            asyncio.run(test(Path(directory)/'refinement-profile',public_refinement=True))
            asyncio.run(test(Path(directory)/'adaptive-profile',public_refinement=True,adaptive_import=True))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
