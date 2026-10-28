"""Owner contact changes cannot revive a prepared message from an older scope."""
import asyncio
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys,tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.kernel_setup import KernelSetupStore
from alive_kernel.followup_intake import record_request,permission,ACTOR
from alive_kernel.agenda import AgendaProjection,AgendaProposal,AgendaAuthority,AgendaItemKind
from alive_kernel import agenda_revisions
from alive_kernel.cognition_opportunities import CognitionOpportunityReader
from alive_kernel.events import Sensitivity,EventEnvelope
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer,OpportunitySynthesisError
from alive_kernel.autonomy_policy import AutonomyPolicyProjection
from alive_kernel.deliberation import ActionAuthority,PolicyContext
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.dispatch_outbox import DispatchOutbox,DispatchOutboxError
from alive_kernel_testkit import install_terminal_route
from run_task_contact_scope import SCOPE

async def exercise(root,delegated,transport=False):
    store=KernelSetupStore(root,initialize=True)
    intent,token=store.stage({'model_calls':True,'delivery':True,'outbound_retention_days':30,
        'outbound_retention_confirmed':True,'model':None,'public_queries':['public synthetic topic'],
        'cited_reads':False,'accept_explicit_followups':True,'manage_explicit_followups':True,
        'revise_explicit_followups':True,'retain_followup_source':True})
    configured=store.confirm(intent.event.event_id,token,scope=SCOPE)
    agenda=AgendaProjection(store.journal);owner=configured.subject
    task='Review a synthetic classroom activity.'
    details={'task':task,'constraint':'Do not submit the activity.','notify_owner':True}
    def intake(message,turn,**purpose):
        return record_request(store,configured,turn_identity=turn,
            request_fingerprint=store.protector.authenticate_json('alive.intake.request.v1',message),
            evidence_fingerprint='synthetic-exact-owner-evidence',permission_id=permission(store,configured)[1],
            source_message=message,**purpose)
    source=(intake('Remind me to review the synthetic activity.','initial',notify_owner=True) if delegated else
        store.journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-explicit-owner',
            actor=owner,subject=owner,payload={'synthetic':True})))
    proposal=agenda.append_proposal(AgendaProposal(item_id='contact-revision-item',kind=AgendaItemKind.COMMITMENT,
        subject=owner,details=details,authority=AgendaAuthority.USER_DELEGATED if delegated else AgendaAuthority.USER_EXPLICIT,
        source_event_ids=(source.event.event_id,),confidence=1,
        expires_at=datetime.now(timezone.utc)+timedelta(days=7)),actor=ACTOR if delegated else owner)
    assert agenda.apply(proposal).outcome=='active'
    item_id=proposal.event.payload['item_id']
    private=CognitionOpportunityReader(store.journal);synth=OpportunitySynthesizer(store.journal)
    scope=dict(subject=owner,clearance=Sensitivity.PRIVATE,limit=32)
    def version():
        with closing(store.journal._connect()) as connection:
            last=connection.execute('SELECT caused_by_event_id FROM agenda_transitions_v1 WHERE item_id=? '
                'ORDER BY transition_id DESC LIMIT 1',(item_id,)).fetchone()[0]
        return store.protector.authenticate_json('alive.agenda.item_version.v1',{
            'configuration':configured.event_id,'owner':owner,'item':item_id,'event':last})
    revision_number=0
    def revise(flag,*,stale_version=None):
        nonlocal revision_number,details
        revision_number+=1
        message=('Keep doing the private work, but do not send updates.' if flag is False else
            'You may send me updates again; keep all other work constraints.' if flag is True else
            'Keep the same contact choice and add this synthetic clarification.')
        changed={**details,**({'notify_owner':flag} if flag is not None else
            {'constraint':details['constraint']+' Preserve the original activity.'})}
        def writer(binding,*,contact_scope_only):
            return intake(message,'amend-'+str(revision_number),operation='revise',target_item_id=item_id,
                from_state='active',revision_binding=binding,contact_scope_only=contact_scope_only,
                **({'notify_owner':flag} if flag is not None else {}))
        result=agenda_revisions.append(store,configured,agenda,item_id=item_id,item_version=stale_version or version(),
            details=changed,due_at=None,source_writer=writer,validate=lambda:None)
        details=changed
        return result
    async def generate(operation):
        async def call(**kwargs):
            data=json.loads(kwargs['messages'][-1]['content'])
            assert len(data['opportunities'])==1
            response={'candidates':[{'agenda_item_id':item_id,'kind':'ask','text':'Please review the synthetic activity.',
                'topic':'synthetic reminder','dimensions':{name:{'value':.1 if name in ('risk','interruption_cost') else .8,
                    'reason':'Synthetic current owner reminder'} for name in
                    ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}
            return SimpleNamespace(model='synthetic/contact-revision',choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(response)))])
        result=await synth.run(subject=owner,operation_id=operation,call=call)
        assert len(result.candidates)==1
        return result
    def unrecoverable(operation):
        try:synth.load_completed(subject=owner,operation_id=operation)
        except OpportunitySynthesisError:return
        raise AssertionError('old contact epoch revived a prepared candidate')
    original=await generate('before-stop')
    assert synth.load_completed(subject=owner,operation_id='before-stop')==original
    launch_guard=None
    if transport:
        async def model(**kwargs):
            stage=kwargs['task'];data=json.loads(kwargs['messages'][1]['content'].split('\n',1)[1]
                if stage=='alive_deliberation' else kwargs['messages'][1]['content'])
            if stage=='alive_opportunity_candidates':
                value={'candidates':[{'agenda_item_id':item_id,'kind':'share','text':'Please review the synthetic activity.',
                    'topic':'synthetic reminder','dimensions':{name:{'value':.1 if name in ('risk','interruption_cost') else .8,
                        'reason':'Synthetic current owner reminder'} for name in
                        ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}
            elif stage=='alive_source_support':
                value={'verdict':'supported','unsupported_claims':[],'uncertainties':[],'reason':'Synthetic review'}
            elif stage=='alive_deliberation':
                value={'candidate_id':next(v['candidate_id'] for v in data
                    if v['candidate_id'].startswith('opportunity-candidate:')),'rationale':'Synthetic selection'}
            elif stage=='alive_semantic_render':value='\n'.join(a['text'] for a in data['meaning']['atoms'])
            elif stage=='alive_semantic_review':
                value={'atom_reviews':[{'atom_id':a['atom_id'],'preserved':True,'risks':[]} for a in data['meaning']['atoms']],
                    'added_claims_detected':False,'speech_act_preserved':True,'protected_literals_preserved':True}
            else:raise AssertionError('unexpected contact dispatch task '+stage)
            if isinstance(kwargs.get('route_info'),dict):kwargs['route_info']['provider']='synthetic-'+stage
            return SimpleNamespace(model='synthetic/'+stage,choices=[SimpleNamespace(message=SimpleNamespace(
                content=value if isinstance(value,str) else json.dumps(value)))])
        policies=AutonomyPolicyProjection(store.journal)
        policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=0,enabled=True,
            context=PolicyContext(can_interrupt=True),operation_id='enable-test-contact'))
        runtime=AutonomousCycleRuntime(store.journal)
        route=install_terminal_route(store.journal,subject=owner,content_vault=runtime.preparation.vault)
        grant=ActionDelegationStore(store.journal).grant(subject=owner,actor=owner,
            policy_event_id=policies.current(owner).event_id,route_binding_id=route,action_kinds=('share',),
            maximum_sensitivity=Sensitivity.PRIVATE,expires_at=datetime.now(timezone.utc)+timedelta(minutes=30),
            operation_id='contact-dispatch-grant',allow_natural_expression=True)
        prepared=await runtime.preparation.prepare(subject=owner,operation_id='dispatch-before-stop',
            policy_context=policies.current(owner).context,call=model,resolve_domain=lambda provider,model:model,
            resolve_grounding_domain=lambda model:model,grounding=True,authority=ActionAuthority.USER_DELEGATED,
            language='en',authorization_operation_id='prepare-contact',route_binding_id=route,
            delegation_event_id=grant.event.event_id)
        assert prepared.attempt_event_id is not None and prepared.authorization.authorized,prepared
        outbox=DispatchOutbox(store.journal,content_vault=runtime.preparation.vault)
        anchor=datetime.now(timezone.utc)
        lease=outbox.acquire(worker_id='synthetic-contact-worker',now=anchor,lease_ttl=timedelta(seconds=30))
        assert lease is not None
        execution=outbox.begin_execution(lease,clearance=Sensitivity.PRIVATE,now=anchor)
        outbox.validate_execution_for_launch(execution,now=anchor+timedelta(seconds=1))
        def revoked_launch():
            try:outbox.validate_execution_for_launch(execution,now=anchor+timedelta(seconds=1))
            except DispatchOutboxError as error:
                assert 'selection inputs' in str(error),str(error)
                return
            raise AssertionError('revoked contact crossed final adapter-launch fence')
        launch_guard=revoked_launch
    stale=version();revise(False)
    assert not synth.reader.active_evidence(**scope) and len(private.active_evidence(**scope))==1
    unrecoverable('before-stop')
    if launch_guard:launch_guard()
    count=len(store.journal.read())
    try:revise(True,stale_version=stale)
    except ValueError:pass
    else:raise AssertionError('stale item version changed contact scope')
    assert len(store.journal.read())==count and not synth.reader.active_evidence(**scope)
    revise(None)
    assert not synth.reader.active_evidence(**scope),'unrelated revision widened contact scope'
    revise(True)
    comm=synth.reader.active_evidence(**scope)
    assert len(comm)==1 and comm[0].observation_event_id!=proposal.event.event_id
    assert comm[0].observation_event_id==comm[0].content['owner_contact_revision_event_id']
    unrecoverable('before-stop')
    if launch_guard:launch_guard()
    current=await generate('after-regrant')
    assert synth.load_completed(subject=owner,operation_id='after-regrant')==current
    revise(False);unrecoverable('after-regrant')
    revise(True);unrecoverable('after-regrant')
    latest=synth.reader.active_evidence(**scope)[0].content['owner_contact_revision_event_id']
    revision=store.journal.get(latest)
    store.vault.erase_item(revision.event.payload['content']['content_id'])
    assert not synth.reader.active_evidence(**scope),'erased amendment still authorized contact'
    assert len(private.active_evidence(**scope))==1,'contact erasure destroyed private task state'
    assert len(store.journal.read(event_type='dispatch.started'))==int(transport)
    assert not store.journal.read(event_type='delivery.succeeded')

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-contact-revision-') as root:
        for delegated in (False,True):
            for transport in (False,True):
                asyncio.run(exercise(Path(root)/(str(delegated)+'-'+str(transport)),delegated,transport))
    print('HERMES_ALIVE_TASK_CONTACT_REVISION_OK')
