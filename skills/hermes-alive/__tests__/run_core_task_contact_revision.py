"""Actual Core intake/revision tool under a guided grant; no models or sending."""
import asyncio,importlib,json,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
import run_core_session_routing as core
from run_core_guided_setup import cli

async def exercise(home):
    home.mkdir();shutil.copytree(core.repo,home/'plugins/hermes-alive')
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'auto','default':'synthetic-owner-model'}}),encoding='utf-8')
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
        '--confirm-followup-management','--confirm-followup-revisions')
    assert rc==0 and staged.get('confirmation_command')
    assert cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None
    try:
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];assert loaded.enabled and not loaded.error
        binding=loaded.module._gateway_host_binding
        class Adapter(core.Adapter):
            async def send(self,*args,**kwargs):raise AssertionError('contact revision cannot send')
        adapter=Adapter(core.Platform.TELEGRAM);runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter})
        adapter.gateway_runner=runner;await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='contact-revision-peer',
            user_id='contact-revision-owner',message_id='contact-revision-confirm')
        entry=runner.session_store.get_or_create_session(source)
        from hermes_cli.plugins import get_plugin_command_handler
        reply=await runner._hm_run_plugin_handler(get_plugin_command_handler('alive'),None,source,
            session_entry=entry,args=staged['confirmation_command'].removeprefix('/alive '))
        assert '已确认' in reply and binding.native is None and binding.task is None
        store=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge').setup_store(binding)
        configured=store.configuration();assert configured.options['revise_explicit_followups'] is True
        package=store.__class__.__module__.rsplit('.',1)[0]
        reader=importlib.import_module(package+'.cognition_opportunities').CognitionOpportunityReader
        sensitivity=importlib.import_module(package+'.events').Sensitivity
        from agent.turn_context import _collect_pre_llm_call_context
        import model_tools
        turn_count=0
        def tool(arguments,message):
            nonlocal turn_count
            turn_count+=1;turn='contact-owner-turn-'+str(turn_count)
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            try:
                _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='synthetic-owner-model',
                    platform='telegram',_user_id=source.user_id),effective_task_id=turn,turn_id=turn,
                    original_user_message=message,messages=[{'role':'user','content':message}],conversation_history=[])
                return json.loads(model_tools.handle_function_call('alive_agenda',arguments,task_id=turn,
                    session_id=entry.session_id,turn_id=turn,tool_call_id=turn,enabled_tools=['alive_agenda']))
            finally:core.clear_session_vars(variables)
        message='Keep tracking this synthetic activity and remind me to review it.'
        saved=tool({'operation':'record','task':'Review a synthetic activity.','constraint':'Do not submit it.',
            'notify_owner':True,'evidence_span':message},message)
        assert saved.get('status')=='recorded_under_owner_intake_grant',saved
        item_id=saved['item_id']
        def current():
            answer=tool({'operation':'list','item_id':item_id},'Show my synthetic activity.')
            assert len(answer['items'])==1;return answer['items'][0]
        scope=dict(subject=configured.subject,clearance=sensitivity.PRIVATE,limit=32)
        original=current();assert original['details']['notify_owner'] is True
        assert len(reader(store.journal,communication_only=True).active_evidence(**scope))==1
        message='Continue doing the work privately, but stop sending me updates.'
        stopped=tool({'operation':'revise','item_id':item_id,'item_version':original['item_version'],
            'notify_owner':False,'evidence_span':message},message)
        assert stopped.get('status')=='revised_under_owner_management_grant',stopped
        assert stopped['old_work_admissions_valid_for_revision'] is True
        sources=importlib.import_module(package+'.core_work_source').OwnedWorkSource(store)
        assert sources.existing(item_id,configured,original['item_version']) is not None
        now=current();assert now['state']=='active' and now['details']['task']==original['details']['task']
        assert now['details']['notify_owner'] is False and now['item_version']!=original['item_version']
        assert len(reader(store.journal).active_evidence(**scope))==1
        assert not reader(store.journal,communication_only=True).active_evidence(**scope)
        count=len(store.journal.read());message='You may send updates again.'
        stale=tool({'operation':'revise','item_id':item_id,'item_version':original['item_version'],
            'notify_owner':True,'evidence_span':message},message)
        assert 'error' in stale and len(store.journal.read())==count
        malformed=tool({'operation':'revise','item_id':item_id,'item_version':now['item_version'],
            'notify_owner':1,'evidence_span':message},message)
        assert 'error' in malformed and len(store.journal.read())==count
        reserved=tool({'operation':'revise','item_id':item_id,'item_version':now['item_version'],
            'notify_owner':True,'contact_scope_only':True,'evidence_span':message},message)
        assert reserved.get('error')=='alive_agenda_arguments_invalid' and len(store.journal.read())==count
        message='Keep updates stopped; preserve all original activity requirements and do not submit it.'
        revised=tool({'operation':'revise','item_id':item_id,'item_version':now['item_version'],
            'constraint':'Do not submit it; keep all original activity requirements.','evidence_span':message},message)
        assert revised.get('status')=='revised_under_owner_management_grant',revised
        assert revised['old_work_admissions_valid_for_revision'] is False
        assert sources.existing(item_id,configured,now['item_version']) is None
        now=current();assert now['details']['notify_owner'] is False
        assert not reader(store.journal,communication_only=True).active_evidence(**scope)
        message='You may send updates again.'
        granted=tool({'operation':'revise','item_id':item_id,'item_version':now['item_version'],
            'notify_owner':True,'evidence_span':message},message)
        assert granted.get('status')=='revised_under_owner_management_grant',granted
        contact=reader(store.journal,communication_only=True).active_evidence(**scope)
        assert len(contact)==1 and contact[0].observation_event_id==contact[0].content['owner_contact_revision_event_id']
        assert current()['details']['notify_owner'] is True
        assert store.activation() is None and binding.native is None and binding.task is None
        assert not store.journal.read(event_type='dispatch.started')
        print('CORE_TASK_CONTACT_REVISION_PROOF '+json.dumps({'actual_core_tool_and_confirmation':True,
            'private_task_kept':True,'stale_version_and_nonboolean_rejected':True,
            'omission_preserves_scope':True,'regrant_has_new_epoch':True,'actual_model_calls':0,'actual_sends':0}),flush=True)
    finally:
        if manager:manager.unload()
        core.reset_hermes_home_override(token)

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-contact-revision-') as root:
        try:asyncio.run(exercise(Path(root)/'profile'))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(root)
    print('HERMES_ALIVE_CORE_TASK_CONTACT_REVISION_OK')
