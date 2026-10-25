"""Recall and interpretation share a frozen fair pool; synthetic inference only."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from run_feedback_recall import prepare_history,response
from alive_kernel import DiscoveryCandidate,DiscoveryOpportunityIngestor,PolicyContext,Sensitivity,EventEnvelope
from alive_kernel import ExperienceJournal
from alive_kernel.content_vault import ContentReference
from alive_kernel.events import _thaw_json
from alive_kernel.opportunity_synthesis import OpportunitySynthesisError
from alive_kernel.planning_runtime import PlanningRuntime

async def test(root):
    interpreter,owner,target=prepare_history(root,noise=0)
    journal,vault=interpreter.journal,interpreter.vault
    before_attempts=tuple(journal.read(event_type='action.attempted'))
    ingestor=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    now=datetime.now(timezone.utc);short=now+timedelta(hours=12)
    def ingest(index,subject=owner):return ingestor.ingest(DiscoveryCandidate(source='synthetic',
        title='Synthetic research '+str(index),summary=('Synthetic evidence paragraph. '*36)+str(index),
        url='https://example.invalid/material/'+str(index),observed_at=now,
        priority_hint=.01 if index<3 else .99,
        expires_at=short if index==31 else now+timedelta(days=3)),subject=subject)
    sources=[ingest(i) for i in range(35)]
    runtime=PlanningRuntime(journal,content_vault=vault)
    latest=tuple(e.observation_event_id for e in runtime.synth.reader.active_evidence(
        subject=owner,clearance=Sensitivity.PRIVATE,limit=32))
    fair=tuple(e.observation_event_id for e in runtime.synth.source_pool(subject=owner,clearance=Sensitivity.PRIVATE)[0])
    assert latest!=fair and fair[0]==sources[0].observation_event_id
    calls=[];query_ids=[];admitted=[];late=[]
    async def call(**kw):
        calls.append(kw['task']);data=json.loads(kw['messages'][1]['content'])
        if kw['task']=='alive_feedback_recall':
            assert data['query']['material_scope']['planned_pool_not_final_draft']
            query_ids.extend(v['observation_event_id'] for v in data['query']['opportunities'])
            assert tuple(query_ids)==fair and tuple(query_ids)!=latest
            late.append(ingest(35))  # Arrival during inference cannot replace old material.
            return response(dict(outcome_event_ids=[target],continue_older=False,reason='Synthetic supplied evidence.'))
        assert kw['task']=='alive_opportunity_candidates'
        admitted.extend(v['observation_event_id'] for v in data['opportunities'])
        assert admitted and tuple(admitted)==fair[:len(admitted)] and len(admitted)<32
        assert late[0].observation_event_id not in admitted
        return response(dict(candidates=[]))
    parameters=dict(operation_id='bound-material',subject=owner,call=call,
        policy_context=PolicyContext(can_interrupt=False),semantic_feedback_recall=True)
    planned=await runtime.run(**parameters)
    assert calls==['alive_feedback_recall','alive_opportunity_candidates'] and planned.action_kind=='silence'
    done=journal.get(planned.interpretation_event_id);start=journal.get(done.event.causation_id)
    scope=_thaw_json(start.event.payload['material_scope'])
    assert tuple(scope['pool_ids'])==fair and start.event.payload['source_scan']['after_sequence']==scope['cursor']
    assert ContentReference.from_event_payload(done.event.payload['content']).retention_until==short
    async def forbidden(**_):raise AssertionError('completed scoped material called a model again')
    assert await PlanningRuntime(journal,content_vault=vault).run(**{**parameters,'call':forbidden})==planned
    # Frozen pre-scope planning contract: preserve its query instead of silently
    # creating a new source window when an existing operation is reopened.
    original_plan=next(r for r in journal.read(event_type='planning.runtime_started')
        if r.event.payload.get('feedback_material_scope') is not None)
    binding=_thaw_json(original_plan.event.payload);binding.pop('feedback_material_scope')
    legacy_op='legacy-unbound'
    digest=vault.digest_json(dict(operation=legacy_op,subject=owner))[:40]
    journal.append(EventEnvelope(event_id='planning.runtime:'+digest+':started',event_type='planning.runtime_started',
        source='alive.planning-runtime',actor='system:alive-runtime',subject=owner,sensitivity=Sensitivity.PRIVATE,
        payload=binding))
    legacy_calls=[]
    async def legacy_call(**kw):
        legacy_calls.append(kw['task']);data=json.loads(kw['messages'][1]['content'])
        if kw['task']=='alive_feedback_recall':
            assert 'material_scope' not in data['query']
            return response(dict(outcome_event_ids=[target],continue_older=False,reason='Legacy supplied evidence.'))
        return response(dict(candidates=[]))
    legacy=await runtime.run(**{**parameters,'operation_id':legacy_op,'call':legacy_call})
    assert len(legacy_calls)==2
    assert await runtime.run(**{**parameters,'operation_id':legacy_op,'call':forbidden})==legacy
    for bad_id,frontier in ((late[0].observation_event_id,scope['origin_frontier']),
            (ingest(100,'user:foreign').observation_event_id,journal.last_sequence())):
        invalid={**scope,'origin_frontier':frontier,'pool_ids':[*scope['pool_ids'][:-1],bad_id],
            'fair_pool_ids':[*scope['fair_pool_ids'][:-1],bad_id]}
        with patch.object(vault,'resolve_json',side_effect=AssertionError('foreign/future scope body read')):
            try:runtime.synth.source_pool(subject=owner,clearance=Sensitivity.PRIVATE,scope=invalid)
            except OpportunitySynthesisError:pass
            else:raise AssertionError('foreign or future source scope accepted')
    # Even an unadmitted tail influenced recall: deleting it invalidates use,
    # rather than silently substituting today's source list.
    assert sources[31].observation_event_id not in admitted
    vault.erase_item(journal.get(sources[31].observation_event_id).event.payload['content']['content_id'])
    try:await runtime.run(**{**parameters,'call':forbidden})
    except OpportunitySynthesisError:pass
    else:raise AssertionError('withdrawn recall material survived planning recovery')
    assert tuple(journal.read(event_type='action.attempted'))==before_attempts
    assert not journal.read(event_type='dispatch.externally_started')

async def research_group_test(root):
    from alive_kernel.discovery_inquiry import DiscoveryInquiryContext
    from alive_kernel.host_discovery import HostDiscoveryReader
    interpreter,owner,target=prepare_history(root,noise=0)
    journal,vault=interpreter.journal,interpreter.vault
    ingestor=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    listing=ingestor.ingest(DiscoveryCandidate(source='synthetic',title='Original research listing',
        summary='Synthetic original listing.',url='https://example.invalid/listing'),subject=owner)
    inquiries=DiscoveryInquiryContext(ingestor)
    inquiries.remember(item_id='inquiry:material',subject=owner,question='Synthetic research question.',
        value_hypothesis='Tentative potential value, not a user request.',
        source_event_ids=(listing.observation_event_id,),model_actor='model:synthetic',
        expires_at=datetime.now(timezone.utc)+timedelta(hours=1),
        expected_context_digest=inquiries.context_digest(subject=owner))
    async def search(*args,**kwargs):raise AssertionError('read-only fixture searched externally')
    async def allow(url):return url.startswith('https://example.invalid/')
    async def extract(urls,**kwargs):return json.dumps(dict(results=[dict(url=url,title='Original '+url,
        content='Synthetic original page evidence.',error=None) for url in urls]))
    read=await HostDiscoveryReader(ingestor,subject=owner,search=search,extract=extract,allow_url=allow,
        is_current=lambda:True).collect(operation_id='owned-material-read',
            read_urls=('https://example.invalid/primary','https://example.invalid/secondary'),
            inquiry_item_ids=('inquiry:material',))
    for index in range(36):
        ingestor.ingest(DiscoveryCandidate(source='synthetic later source',title='Later '+str(index),
            summary='Synthetic unrelated source.',url='https://example.invalid/later/'+str(index),priority_hint=.99),subject=owner)
    latest=ingestor.active_evidence(subject=owner,clearance=Sensitivity.PRIVATE,limit=32)
    assert not set(read.observation_ids)&{e.observation_event_id for e in latest}
    runtime=PlanningRuntime(journal,content_vault=vault);calls=[]
    async def call(**kw):
        calls.append(kw['task']);data=json.loads(kw['messages'][1]['content'])
        if kw['task']=='alive_feedback_recall':
            ids=tuple(v['observation_event_id'] for v in data['query']['opportunities'])
            assert ids[:2]==read.observation_ids
            return response(dict(outcome_event_ids=[target],continue_older=False,reason='Synthetic bound recall.'))
        assert tuple(v['observation_event_id'] for v in data['opportunities'])[:2]==read.observation_ids
        return response(dict(candidates=[],abstentions=[dict(agenda_item_id=data['opportunities'][0]['agenda_item_id'],
            reason='Synthetic scoped assessment, not recipient value proof.')]))
    parameters=dict(operation_id='bound-research',subject=owner,call=call,semantic_feedback_recall=True,
        recipient_meaning=True,policy_context=PolicyContext(can_interrupt=False),
        inquiry_item_ids=('inquiry:material',),research_read_receipt_ids=(read.receipt_id,))
    planned=await runtime.run(**parameters)
    assert calls==['alive_feedback_recall','alive_opportunity_candidates']
    async def forbidden(**_):raise AssertionError('research replay repeated provider work')
    assert await runtime.run(**{**parameters,'call':forbidden})==planned
    vault.erase_item(journal.get(read.observation_ids[0]).event.payload['content']['content_id'])
    try:await runtime.run(**{**parameters,'call':forbidden})
    except ValueError:pass
    else:raise AssertionError('partial forgotten research group was reused')
    assert not journal.read(event_type='dispatch.externally_started')

async def empty_pool_test(root):
    journal=ExperienceJournal(root/'kernel.sqlite3')
    runtime=PlanningRuntime(journal)
    async def forbidden(**_):raise AssertionError('empty material pool spent on recall or inference')
    parameters=dict(operation_id='empty',subject='user:empty',call=forbidden,
        semantic_feedback_recall=True,policy_context=PolicyContext(can_interrupt=False))
    planned=await runtime.run(**parameters)
    assert planned.action_kind=='silence'
    assert await runtime.run(**parameters)==planned
    assert not journal.read(event_type='feedback.recall_started')
    DiscoveryOpportunityIngestor(journal,content_vault=runtime.synth.vault).ingest(DiscoveryCandidate(
        source='synthetic',title='New material',summary='Synthetic later arrival.',
        url='https://example.invalid/after-empty'),subject='user:empty')
    try:await runtime.run(**parameters)
    except OpportunitySynthesisError:pass
    else:raise AssertionError('old empty completion ignored newly available material')

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-feedback-material-') as directory:
        asyncio.run(test(Path(directory)))
    with tempfile.TemporaryDirectory(prefix='alive-feedback-material-group-') as directory:
        asyncio.run(research_group_test(Path(directory)))
    with tempfile.TemporaryDirectory(prefix='alive-feedback-material-empty-') as directory:
        asyncio.run(empty_pool_test(Path(directory)))
    print('HERMES_ALIVE_FEEDBACK_MATERIAL_SCOPE_OK')
