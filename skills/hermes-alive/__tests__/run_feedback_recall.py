"""Actual recall/planning/cache contracts; synthetic oracle, no real IO/model."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from probe_alive_live_feedback import prepare_case
from alive_kernel import EventEnvelope,Sensitivity,OutcomeKind,DiscoveryCandidate,DiscoveryOpportunityIngestor,PolicyContext
from alive_kernel.feedback_context import FeedbackContextReader
from alive_kernel.feedback_recall import FeedbackRecallSelector
from alive_kernel.feedback_synthesis import FeedbackSynthesisError
from alive_kernel.planning_runtime import PlanningRuntime,PlanningRuntimeError
from alive_kernel.reconsideration import ReconsiderationStore
from alive_kernel.privacy import LocalIdentityProtector

def response(value):return NS(model='synthetic/selector',choices=[NS(message=NS(content=json.dumps(value)))])

def prepare_history(root,noise=17):
    interpreter,owner,target=prepare_case(root/'case',dict(id='semantic-recall',
        sent='Synthetic mixed research and shopping notice.',
        reply='Research detail is welcome; no shopping promotions. This does not ask for more messages.'))
    journal,vault=interpreter.journal,interpreter.vault
    retention=journal.get('retention.consent:fixture')
    replies=('A colleague said "I like shopping recommendations"; that was not my preference.',
        'I am in a meeting today; I will look later.',
        'The phrase "I only like shopping" was dialogue in a demonstration.',
        'I was asking for a colleague on that occasion, not stating my research interests.')
    for index in range(noise):
        ref=vault.put_json(dict(text=replies[index%len(replies)]+' Synthetic occasion '+str(index),
            direction='inbound',may_be_truncated=False),
            subject=owner,purpose='conversation.inbound',sensitivity=Sensitivity.PRIVATE,
            retention_until=datetime.now(timezone.utc)+timedelta(days=29),content_id='recall-input:'+str(index))
        inbound=journal.append(EventEnvelope(event_id='recall-input:'+str(index),event_type='conversation.inbound',
            source='synthetic-public-fixture',actor=owner,subject=owner,sensitivity=Sensitivity.PRIVATE,
            causation_id='action.attempt:attempt:'+owner,payload=dict(erasable_content_stored=True,
                content_may_be_truncated=False,consent_event_id=retention.event.event_id,content=ref.to_event_payload())))
        outcome=interpreter.outcomes.append_outcome(attempt_id='attempt:'+owner,kind=OutcomeKind.USER_REPLIED,
            source_event_id=inbound.event.event_id,details=dict(classification='ordinary_reply',synthetic=True),
            actor=owner,subject=owner,outcome_id='recall-reply:'+str(index))
        assert interpreter.outcomes.apply(outcome).outcome=='recorded'
    return interpreter,owner,target

async def test(root):
    interpreter,owner,target=prepare_history(root)
    journal,vault=interpreter.journal,interpreter.vault
    attempts_before=tuple(journal.read(event_type='action.attempted'))
    reader=FeedbackContextReader(journal,content_vault=vault)
    selector=FeedbackRecallSelector(reader)
    query=dict(inquiry='Consider a public research contribution, not a shopping offer.')
    expiry=datetime.now(timezone.utc)+timedelta(minutes=30)
    calls=[]
    async def choose(**kw):
        calls.append(kw['task']);assert kw['task']=='alive_feedback_recall' and kw['model'] is None
        data=json.loads(kw['messages'][1]['content']);assert not data['authority_granted']
        refs={v['outcome_event_id'] for window in data['index_windows'] for v in window['entries']}
        return response(dict(outcome_event_ids=[target] if target in refs else [],
            continue_older=target not in refs and data['older_available_after_head'],
            reason='Controlled ID oracle, not a semantic relevance proof.'))
    params=dict(subject=owner,query=query,validate_query=lambda:query,retention_until=expiry,call=choose)
    selected=await selector.run(operation_id='select',**params)
    assert selected['outcome_event_ids']==[target] and len(calls)==1
    assert selected['coverage_complete'] is False and not selected['authority_granted']
    async def forbidden(**kw):raise AssertionError('completed or interrupted recall repeated a provider call')
    before=journal.last_sequence()
    assert await FeedbackRecallSelector(reader).run(operation_id='select',**{**params,'call':forbidden})==selected
    assert journal.last_sequence()==before
    limited=await selector.run(operation_id='bounded',max_pages=1,**params)
    assert not limited['outcome_event_ids'] and limited['more_available'] and not limited['coverage_complete']
    async def invented(**kw):return response(dict(outcome_event_ids=[target],continue_older=False,reason='Not in this page.'))
    with patch.object(reader,'resolve',side_effect=AssertionError('unprovided reference resolved')):
        try:await selector.run(operation_id='unprovided',max_pages=1,**{**params,'call':invented})
        except FeedbackSynthesisError:pass
        else:raise AssertionError('unprovided reference accepted')
    async def cancelled(**kw):raise asyncio.CancelledError()
    try:await selector.run(operation_id='cancelled',**{**params,'call':cancelled})
    except asyncio.CancelledError:pass
    else:raise AssertionError('cancellation became completed recall')
    try:await selector.run(operation_id='cancelled',**{**params,'call':forbidden})
    except FeedbackSynthesisError:pass
    else:raise AssertionError('incomplete recall reopened')
    mutable=dict(query)
    async def changed(**kw):
        result=await choose(**kw);mutable['inquiry']='A different current inquiry.';return result
    try:await selector.run(operation_id='changed',**{**params,'call':changed,'validate_query':lambda:mutable})
    except FeedbackSynthesisError:pass
    else:raise AssertionError('changed inquiry accepted after model wait')
    source=DiscoveryOpportunityIngestor(journal,content_vault=vault).ingest(DiscoveryCandidate(
        source='synthetic',title='Research observation',summary='A synthetic public observation.',
        url='https://example.invalid/observation',observed_at=datetime.now(timezone.utc)),subject=owner)
    runtime=PlanningRuntime(journal,content_vault=vault)
    async def planning_call(**kw):
        if kw['task']=='alive_feedback_recall':return await choose(**kw)
        data=json.loads(kw['messages'][1]['content'])
        assert target in [v['outcome_event_id'] for v in data['recent_feedback_context']]
        assert any(v['agenda_item_id']==source.agenda_item_id for v in data['opportunities'])
        return response(dict(candidates=[]))
    planning=dict(operation_id='semantic-planning',subject=owner,call=planning_call,
        policy_context=PolicyContext(can_interrupt=False),semantic_feedback_recall=True)
    planned=await runtime.run(**planning)
    assert planned.action_kind=='silence'
    assert await runtime.run(**{**planning,'call':forbidden})==planned
    try:await runtime.run(**{**planning,'call':forbidden,'semantic_feedback_recall':False})
    except PlanningRuntimeError:pass
    else:raise AssertionError('planning reused different recall contract')
    preparation=NS(expression=NS(planning=runtime))
    reconsider=ReconsiderationStore(preparation,LocalIdentityProtector(root/'capture.key'))
    policy=NS(event_id='synthetic:policy',context=PolicyContext(can_interrupt=False))
    def capture(**parameters):return reconsider.capture(subject=owner,configuration_id='synthetic',execute=False,
        policy=policy,parameters=parameters,window_seconds=300)
    archive_before=capture(semantic_feedback_recall=True)
    exact_before=capture(recalled_feedback_event_ids=(target,))
    original,_=interpreter.snapshot(subject=owner,outcome_event_id=target)
    vault.erase_item(original['feedback_content_id'])
    assert capture(semantic_feedback_recall=True).semantic_digest!=archive_before.semantic_digest
    try:capture(recalled_feedback_event_ids=(target,))
    except FeedbackSynthesisError:pass
    else:raise AssertionError('cached exact references survived erasure')
    try:await selector.run(operation_id='select',**{**params,'call':forbidden})
    except FeedbackSynthesisError:pass
    else:raise AssertionError('erased archive survived retained recall')
    assert exact_before.valid_until<=expiry+timedelta(minutes=5)
    assert tuple(journal.read(event_type='action.attempted'))==attempts_before
    assert not journal.read(event_type='dispatch.externally_started')
    now=datetime.now(timezone.utc)
    journal.append(EventEnvelope(event_type='consolidation.consent_changed',source='hermes.command.memory',
        actor=owner,subject=owner,sensitivity=Sensitivity.PRIVATE,payload=dict(enabled=True),
        occurred_at=now-timedelta(minutes=2),observed_at=now-timedelta(minutes=2),expires_at=now-timedelta(minutes=1)))
    with patch.object(vault,'resolve_json',side_effect=AssertionError('expired consent private body read')):
        try:await selector.run(operation_id='expired-consent',**{**params,'call':forbidden})
        except FeedbackSynthesisError:pass
        else:raise AssertionError('expired consolidation consent admitted recall')

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-semantic-recall-') as directory:
        asyncio.run(test(Path(directory)))
    print('HERMES_ALIVE_FEEDBACK_RECALL_OK')
