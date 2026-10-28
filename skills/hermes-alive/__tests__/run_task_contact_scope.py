"""Signed task contact scope is distinct from private reasoning and global grants."""
import asyncio
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import json
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.kernel_setup import KernelSetupStore
from alive_kernel.followup_intake import record_request, permission, ACTOR
from alive_kernel.agenda import AgendaProjection, AgendaProposal, AgendaAuthority, AgendaItemKind
from alive_kernel.cognition_opportunities import CognitionOpportunityReader
from alive_kernel.events import Sensitivity
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer, OpportunitySynthesisError
from alive_kernel.autonomy_policy import AutonomyPolicyProjection
from alive_kernel.deliberation import PolicyContext
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime

SCOPE={'contract':'hermes-core-conversation-v1','runtime_profile':'default','transport_profile':'default',
    'platform':'telegram','chat_id':'SYNTHETIC_PEER','chat_type':'dm','thread_id':'',
    'user_id':'SYNTHETIC_OWNER','scope_id':'','guild_id':'','parent_chat_id':'',
    'session_key':'SYNTHETIC_KEY','session_id':'SYNTHETIC_SESSION'}

async def exercise(root,retain=True):
    store=KernelSetupStore(root,initialize=True)
    intent,token=store.stage({'model_calls':True,'delivery':True,'outbound_retention_days':30,
        'outbound_retention_confirmed':True,'model':None,'public_queries':['public synthetic topic'],
        'cited_reads':False,'accept_explicit_followups':True,'retain_followup_source':retain})
    configured=store.confirm(intent.event.event_id,token,scope=SCOPE)
    agenda=AgendaProjection(store.journal)
    def admit(turn,message,notify=None):
        kwargs=dict(turn_identity=turn,
            request_fingerprint=store.protector.authenticate_json('alive.intake.request.v1',message),
            evidence_fingerprint='synthetic-exact-evidence',permission_id=permission(store,configured)[1],
            source_message=message if retain else None)
        if notify is not None:kwargs['notify_owner']=notify
        source=record_request(store,configured,**kwargs)
        item_id='contact-scope-'+turn
        if store.journal.get('agenda.proposal:'+item_id) is None:
            record=agenda.append_proposal(AgendaProposal(item_id=item_id,kind=AgendaItemKind.COMMITMENT,
                subject=configured.subject,details={'task':message,'constraint':'Synthetic fixture'},
                authority=AgendaAuthority.USER_DELEGATED,source_event_ids=(source.event.event_id,),
                confidence=1,expires_at=datetime.fromisoformat(source.event.payload['retention_until'])),actor=ACTOR)
            assert agenda.apply(record).outcome=='active'
        return item_id,kwargs
    private_id,private_args=admit('private','Prepare an activity privately. No messages.',False)
    default_id,_=admit('default','Prepare another activity privately.')
    private=CognitionOpportunityReader(store.journal)
    synth=OpportunitySynthesizer(store.journal)
    args=dict(subject=configured.subject,clearance=Sensitivity.PRIVATE,limit=32)
    assert {e.agenda_item_id for e in private.active_evidence(**args)}=={private_id,default_id}
    assert not synth.reader.active_evidence(**args)
    assert not synth.reader.candidate_evidence(**args)
    async def forbidden(**kwargs):raise AssertionError('private tasks reached communication inference')
    result=await synth.run(subject=configured.subject,operation_id='private-only',call=forbidden)
    assert not result.candidates and result.actual_model=='system/alive-no-current-material'
    assert synth.load_completed(subject=configured.subject,operation_id='private-only')==result
    policies=AutonomyPolicyProjection(store.journal)
    policies.apply(policies.append_update(subject=configured.subject,actor=configured.subject,
        expected_revision=0,enabled=True,context=PolicyContext(can_interrupt=True),operation_id='contact-test-enable'))
    def forbidden_route(_record):raise AssertionError('private work requested an outbound route')
    cycle=await AutonomousCycleRuntime(store.journal).cycle(subject=configured.subject,
        operation_id='private-contact-full-cycle',expression_parameters=dict(call=forbidden,
            resolve_domain=lambda provider,model:model),resolve_binding=forbidden_route,
        reconsider_after_seconds=300,cognition_configuration_id='contact-scope-test')
    assert cycle.disposition=='silence'
    # Same literal turn/request cannot create a second task or widen its grant.
    count=len(store.journal.read())
    try:record_request(store,configured,**{**private_args,'notify_owner':True})
    except ValueError:pass
    else:raise AssertionError('replay widened task communication scope')
    assert len(store.journal.read())==count
    allowed_id,_=admit('report','Remind me to review the activity.',True)
    assert {e.agenda_item_id for e in private.active_evidence(**args)}=={private_id,default_id,allowed_id}
    assert {e.agenda_item_id for e in synth.reader.active_evidence(**args)}=={allowed_id}
    try:synth.load_completed(subject=configured.subject,operation_id='private-only')
    except OpportunitySynthesisError:pass
    else:raise AssertionError('selection recovery ignored new communication evidence')
    def proposal(item_id):
        return {'agenda_item_id':item_id,'kind':'ask','text':'A synthetic authorized reminder.',
            'topic':'classroom preparation','dimensions':{name:{'value':.1 if name in ('risk','interruption_cost') else .8,
                'reason':'synthetic judgment'} for name in
                ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}
    async def adversarial(**kwargs):
        text=json.dumps(kwargs['messages'])
        assert 'Prepare an activity privately' not in text and private_id not in text
        assert 'Prepare another activity privately' not in text and default_id not in text
        return SimpleNamespace(model='synthetic/contact-test',choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'candidates':[proposal(private_id),proposal(allowed_id)]})))])
    chosen=await synth.run(subject=configured.subject,operation_id='forced-private-candidate',call=adversarial)
    assert chosen.rejected_count==1 and len(chosen.candidates)==1
    assert chosen.candidates[0].action.agenda_item_id==allowed_id
    assert synth.load_completed(subject=configured.subject,operation_id='forced-private-candidate')==chosen
    if not retain:
        contact=synth.reader.active_evidence(**args)[0].content
        assert contact['owner_updates_allowed'] is True and contact['original_source_available'] is False
        assert 'original_owner_message' not in contact
        assert not store.journal.read(event_type='dispatch.started')
        return
    # Dispatch's existing selection-source validator reopens this same reader.
    # Erasure must invalidate an already retained positive proposal, not just new inference.
    proposal_record=store.journal.get('agenda.proposal:'+allowed_id)
    source=store.journal.get(proposal_record.event.payload['source_event_ids'][0])
    store.vault.erase_item(source.event.payload['content']['content_id'])
    try:synth.load_completed(subject=configured.subject,operation_id='forced-private-candidate')
    except OpportunitySynthesisError:pass
    else:raise AssertionError('retained communication survived erasure of its source')
    assert not store.journal.read(event_type='dispatch.started')

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-task-contact-') as root:
        asyncio.run(exercise(Path(root)/'retained'))
        asyncio.run(exercise(Path(root)/'not-retained',retain=False))
    print('HERMES_ALIVE_TASK_CONTACT_SCOPE_OK')
