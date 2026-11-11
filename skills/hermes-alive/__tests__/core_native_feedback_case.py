"""Controlled current-main-turn tools after an actually submitted Native share.

Called by the actual Core source-depth journey. Does not seed feedback records.
"""
import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch


async def exercise(core, loaded, binding, runner, source, session, command, before_forgetting=None):
    from gateway.run_inbound_consumer import run_post_admission_hook
    from agent.turn_context import _collect_pre_llm_call_context
    import model_tools
    setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
    store=setup.setup_store(binding)
    package=store.__class__.__module__.rsplit('.',1)[0]
    feedback=importlib.import_module(package+'.native_feedback')
    Reader=importlib.import_module(package+'.feedback_context').FeedbackContextReader
    Sensitivity=importlib.import_module(package+'.events').Sensitivity
    reader=Reader(store.journal,content_vault=store.vault)
    text='这个有点意思，但是略偏长；不是说以后每条都要短。'
    event=SimpleNamespace(message_id='synthetic-native-feedback-1',text=text)
    before=store.journal.last_sequence()
    authority_before={kind:len(store.journal.read(event_type=kind)) for kind in
        ('memory.proposed','autonomy.policy_changed','action.delegation_granted')}
    assert await run_post_admission_hook(runner,event,source,session.session_key)==(False,None)
    variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
        session_key=session.session_key,session_id=session.session_id)
    task='native-feedback-current-turn'
    try:
        def collect(message_id=None):
            _collect_pre_llm_call_context(SimpleNamespace(session_id=session.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id=task,turn_id=task,
                original_user_message=text,messages=[{'role':'user','content':text,
                    'platform_message_id':message_id or event.message_id}],conversation_history=[])
        collect()
        targets=[handle for handle,item in binding._continuity._references.items() if item[1]==task]
        assert len(targets)==1,targets
        arguments=dict(reference=targets[0],evidence_span=text,
            association_reason='The current owner evaluates the preceding retained synthetic trial share, with an explicit one-off qualification.')
        def call(args=None,**overrides):
            if args is None:args=arguments
            return json.loads(model_tools.handle_function_call('alive_record_feedback',args,
                task_id=task,session_id=session.session_id,turn_id=task,
                tool_call_id='feedback-tool-'+str(store.journal.last_sequence()),
                enabled_tools=['alive_record_feedback'],**overrides))
        bad=call({**arguments,'evidence_span':'paraphrased feedback not in the current input'})
        assert bad.get('error')=='alive_feedback_unavailable',bad
        saved=call()
        assert saved.get('status')=='recorded_tentative_share_feedback',saved
        assert call()['event_id']==saved['event_id']
        rows=store.journal.read(event_type=feedback.EVENT)
        assert len(rows)==1 and rows[0].sequence>before
        assert not store.journal.read(event_type='outcome.recorded') or all(
            row.event.payload.get('kind') not in ('user_replied','explicit_feedback')
            for row in store.journal.read(event_type='outcome.recorded'))
        values=reader.read(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)
        assert len(values)==1 and values[0].feedback_text==text
        assert values[0].to_prompt()['status']=='native_main_turn_semantic_association_not_quote_proof'
        assert not values[0].to_prompt()['automatic_profile_update']
        assert authority_before=={kind:len(store.journal.read(event_type=kind)) for kind in authority_before}
        assert text.encode() not in store.journal.path.read_bytes()
        assert reader.catalog(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)['entries'][0][
            'attribution']=='main_turn_semantic_association_not_quote_proof'
        assert reader.resolve(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE,
            outcome_event_ids=(saved['event_id'],))==values
        assert not reader.read(subject='user:foreign',clearance=Sensitivity.PRIVATE)
        assert not reader.read(subject=store.configuration().subject,clearance=Sensitivity.PUBLIC)
        if before_forgetting is not None:
            await before_forgetting(text)
        assert '已关闭' in await command('feedback off')
        assert call().get('error')=='alive_feedback_unavailable'
        assert not reader.read(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)
        assert json.loads(await command('feedback list'))[0]['id']==saved['event_id']
        shown=json.loads(await command('feedback show '+saved['event_id']))
        assert shown[0]['original_text']==text
        assert shown[0]['model_association']==arguments['association_reason']
        assert not feedback.inspect_feedback(store,'user:foreign',saved['event_id'])
        assert feedback.forget_feedback(store,'user:foreign',saved['event_id']) is None
        assert '已开启' in await command('feedback on')
        assert reader.read(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)==values
        # Commands have their own Core scope and clear session variables on
        # exit. Bind a fresh normal-turn scope, as the Gateway does in use.
        core.clear_session_vars(variables)
        variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
            session_key=session.session_key,session_id=session.session_id)
        task='native-feedback-restored-turn'
        collect()
        targets=[handle for handle,item in binding._continuity._references.items() if item[1]==task]
        assert len(targets)==1,dict(restored_references=len(targets))
        arguments={**arguments,'reference':targets[0]}
        repeated=call()
        assert repeated.get('event_id')==saved['event_id'],repeated
        # Fresh reader/store instances represent cold evidence reconstruction,
        # not proof that the whole Gateway was restarted.
        assert Reader(store.journal,content_vault=store.vault).read(
            subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)==values
        ref=rows[0].event.payload['content']['content_id']
        backup=store.vault.create_managed_backup('before-feedback-forget')
        assert backup.exists()
        assert '已遗忘' in await command('feedback forget '+saved['event_id'])
        assert '已遗忘' in await command('feedback forget '+saved['event_id'])
        assert not backup.exists() and store.vault.explicit_erasure_recorded(ref)
        assert '没有找到' in await command('feedback show '+saved['event_id'])
        assert not reader.read(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)
        core.clear_session_vars(variables)
        variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
            session_key=session.session_key,session_id=session.session_id)
        task='native-feedback-after-forget'
        collect()
        target=next(handle for handle,item in binding._continuity._references.items() if item[1]==task)
        arguments={**arguments,'reference':target}
        assert call().get('error')=='alive_feedback_unavailable'
        assert len(store.journal.read(event_type=feedback.EVENT))==1
        # Revoke after body creation but before journal publication. This is
        # fault injection of a concurrent owner command, not a preseeded outcome.
        event=SimpleNamespace(message_id='synthetic-native-feedback-race',text=text)
        assert await run_post_admission_hook(runner,event,source,session.session_key)==(False,None)
        task='native-feedback-stale-identical-turn'
        collect('synthetic-native-feedback-1')
        assert all(ticket[1]!=task for ticket in binding._feedback.turns), 'identical text bound to a different message'
        task='native-feedback-race-turn'
        collect()
        targets=[handle for handle,item in binding._continuity._references.items() if item[1]==task]
        assert len(targets)==1
        arguments={**arguments,'reference':targets[0]}
        Vault=type(store.vault);original_put=Vault.put_json;created=[]
        def revoke_after_put(vault,value,**kwargs):
            reference=original_put(vault,value,**kwargs)
            if kwargs.get('purpose')=='feedback.native_association':
                created.append(reference.content_id)
                feedback.set_permission(store,store.configuration(),False)
            return reference
        with patch.object(Vault,'put_json',revoke_after_put):
            assert call(arguments).get('error')=='alive_feedback_unavailable'
        assert len(created)==1 and store.vault.explicit_erasure_recorded(created[0])
        assert len(store.journal.read(event_type=feedback.EVENT))==1
        assert not reader.read(subject=store.configuration().subject,clearance=Sensitivity.PRIVATE)
        # A different admitted message invalidates the old normal-turn ticket.
        other=SimpleNamespace(message_id='synthetic-native-feedback-2',text='普通话题继续，不是评价。')
        assert binding._feedback.turns,'race turn must exist before invalidation test'
        assert await run_post_admission_hook(runner,other,source,session.session_key)==(False,None)
        assert not binding._feedback.turns,'new actual admission must invalidate old interpretation tickets'
        assert call().get('error')=='alive_feedback_unavailable'
    finally:
        core.clear_session_vars(variables)
    print('CORE_NATIVE_FEEDBACK_ASSOCIATION_OK '+json.dumps(dict(
        actual_installed_plugin=True,actual_Core_dispatch=True,actual_local_submission=True,
        controlled_main_tool_call=True,actual_model_inference=False,
        feedback_outcomes_preseeded=False,association_records=1,
        automatic_profile_updates=0,physical_sends=0,quality_rounds=0)),flush=True)
