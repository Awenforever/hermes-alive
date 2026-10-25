#!/usr/bin/env python3
"""Once-only feedback hypotheses inform cognition, never profile/weight writes."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection, DiscoveryCandidate, DiscoveryOpportunityIngestor, EventEnvelope, PolicyContext, Sensitivity
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.feedback_assimilation import FeedbackAssimilationRuntime
from alive_kernel.feedback_synthesis import FeedbackSynthesisError
from alive_kernel.learning_context import CognitionLearningReader
from alive_kernel.opportunity_synthesis import OpportunitySynthesisError
from probe_alive_live_feedback import prepare_case


def response(value):
    return SimpleNamespace(model='synthetic/feedback-model',choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])


async def test(root):
    fixture=dict(id='assimilation',sent='Synthetic detailed bicycle guide.',
        reply='我喜欢自行车保养，但今天在开会。以后请先给简短要点，需要时我会追问。')
    interpreter,subject,outcome=prepare_case(root/'main',fixture)
    journal=interpreter.journal
    runtime=FeedbackAssimilationRuntime(journal,content_vault=interpreter.vault)
    before={kind:len(journal.read(event_type=kind)) for kind in
        ('memory.proposed','preference.observed','reflection.reviewed','action.attempted')}
    calls=[]
    async def call(**kwargs):
        calls.append(kwargs['task'])
        if kwargs['task']=='alive_feedback_interpretation':
            kwargs['route_info']['provider']='synthetic-provider'
            snapshot=json.loads(kwargs['messages'][1]['content'])
            assert snapshot['feedback_text']==fixture['reply'] and snapshot['delivered_text']==fixture['sent']
            return response(dict(summary='PRIVATE_HYPOTHESIS: mixed timing and presentation, not topic dislike.',
                signals=[dict(axis='presentation',key='detail',option='brief-first',direction='support',scope='durable',
                    quote='以后请先给简短要点',hypothesis='Tentatively prefers concise first messages.',uncertainties=['May request detail.']),
                    dict(axis='interruption',key='current-availability',option='meeting',direction='oppose',scope='situational',
                    quote='今天在开会',hypothesis='Currently busy, not a lasting refusal.',uncertainties=['End time unknown.'])],unresolved=[]))
        assert kwargs['task']=='alive_opportunity_candidates'
        data=json.loads(kwargs['messages'][1]['content'])
        hypotheses=[v for v in data['learned_advisory'] if v.get('kind')=='tentative_feedback_interpretation']
        assert len(hypotheses)==1 and len(hypotheses[0]['findings']['signals'])==2
        assert hypotheses[0]['automatic_learning_authority'] is False
        assert data['recent_feedback_context'][0]['feedback_text']==fixture['reply']
        return response(dict(candidates=[]))
    first=await runtime.tick(subject=subject,call=call)
    assert first['interpreted']==1 and calls==['alive_feedback_interpretation']
    assert runtime.read(subject=subject,clearance=Sensitivity.PRIVATE)[0].actual_model=='synthetic/feedback-model'
    assert not runtime.read(subject='user:foreign',clearance=Sensitivity.PRIVATE)
    second=await FeedbackAssimilationRuntime(journal,content_vault=interpreter.vault).tick(subject=subject,call=call)
    assert second['interpreted']==0 and len(calls)==1
    reader=CognitionLearningReader(journal,hypothesis_vault=interpreter.vault)
    values=reader.read(subject=subject,clearance=Sensitivity.PRIVATE)
    assert any(v.to_prompt().get('kind')=='tentative_feedback_interpretation' for v in values)
    policy=AutonomyPolicyProjection(journal)
    current=policy.current(subject)
    if current is None or not current.enabled:
        policy.apply(policy.append_update(subject=subject,actor=subject,expected_revision=current.revision if current else 0,
            enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable'))
    DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(source='synthetic-fixture',
        title='New practical guide',summary='A different bicycle guide, unverified.',url='https://example.invalid/another',
        observed_at=datetime.now(timezone.utc)),subject=subject)
    cycle=AutonomousCycleRuntime(journal,content_vault=interpreter.vault)
    params=dict(subject=subject,expression_parameters=dict(call=call,resolve_domain=lambda provider,model:'synthetic-family'),
        resolve_binding=lambda record:None,interpret_feedback=True,reconsider_after_seconds=300,
        cognition_configuration_id='assimilation-fixture')
    assert (await cycle.cycle(operation_id='first-cognition',**params)).disposition=='silence'
    assert calls==['alive_feedback_interpretation','alive_opportunity_candidates']
    assert (await cycle.cycle(operation_id='unchanged-cognition',**params)).disposition=='waiting_for_change'
    assert len(calls)==2
    # Erasing the derived interpretation mid-await invalidates a proposed result.
    operation=runtime.operation(subject,outcome)
    prefix=interpreter._prefix(subject,operation)
    completed=journal.get(prefix+':completed')
    async def erase_during(**kwargs):
        interpreter.vault.erase_item(completed.event.payload['content']['content_id'])
        return response(dict(candidates=[]))
    try:
        await cycle.preparation.expression.planning.synth.run(subject=subject,operation_id='in-flight-erasure',call=erase_during)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('erased hypotheses survived model await')
    assert not runtime.read(subject=subject,clearance=Sensitivity.PRIVATE)
    assert before=={kind:len(journal.read(event_type=kind)) for kind in before}
    for path in (root/'main').glob('kernel.sqlite3*'):
        assert b'PRIVATE_HYPOTHESIS' not in path.read_bytes()

    # Disabled consent must block even pre-inference private content resolution.
    denied,owner,_=prepare_case(root/'denied',{**fixture,'id':'denied'})
    denied.journal.append(EventEnvelope(event_type='consolidation.consent_changed',source='hermes.command.memory',
        actor=owner,subject=owner,sensitivity=Sensitivity.PRIVATE,payload={'enabled':False}))
    denied_runtime=FeedbackAssimilationRuntime(denied.journal,content_vault=denied.vault)
    with patch.object(denied.vault,'resolve_json',side_effect=AssertionError('revoked private body read')):
        result=await denied_runtime.tick(subject=owner,call=call)
    assert result['interpreted']==0 and len(calls)==2

    # A losing atomic insert never spends on the model, even after a stale precheck.
    race,owner,event_id=prepare_case(root/'race',{**fixture,'id':'race'})
    original=race.journal.append
    def competing(event):
        if event.event_type=='feedback.synthesis_started': original(event)
        return original(event)
    race.journal.append=competing
    blocked_calls=[]
    async def forbidden(**kwargs):
        blocked_calls.append(kwargs)
        raise AssertionError('losing feedback writer spent inference')
    try:
        await race.run(subject=owner,outcome_event_id=event_id,operation_id='race',call=forbidden)
    except FeedbackSynthesisError: pass
    else: raise AssertionError('losing feedback writer became completion')
    assert not race.journal.read(event_type='feedback.synthesis_completed')
    assert not blocked_calls

    raw,owner,_=prepare_case(root/'raw-erased',{**fixture,'id':'raw-erased'})
    raw_runtime=FeedbackAssimilationRuntime(raw.journal,content_vault=raw.vault)
    assert (await raw_runtime.tick(subject=owner,call=call))['interpreted']==1
    assert len(raw_runtime.read(subject=owner,clearance=Sensitivity.RESTRICTED))==1
    count=len(calls)
    assert (await raw_runtime.tick(subject=owner,call=call,clearance=Sensitivity.RESTRICTED))['interpreted']==0
    assert len(calls)==count
    with patch.object(raw.vault,'resolve_json',side_effect=AssertionError('private data below clearance read')):
        assert not raw_runtime.read(subject=owner,clearance=Sensitivity.PUBLIC)
    raw.vault.erase_item(raw.journal.get('input:fixture').event.payload['content']['content_id'])
    assert not raw_runtime.read(subject=owner,clearance=Sensitivity.PRIVATE)

    revoked,owner,_=prepare_case(root/'revoked',{**fixture,'id':'revoked'})
    revoked_runtime=FeedbackAssimilationRuntime(revoked.journal,content_vault=revoked.vault)
    await revoked_runtime.tick(subject=owner,call=call)
    revoked.journal.append(EventEnvelope(event_type='consolidation.consent_changed',source='hermes.command.memory',
        actor=owner,subject=owner,sensitivity=Sensitivity.PRIVATE,payload={'enabled':False}))
    with patch.object(revoked.vault,'resolve_json',side_effect=AssertionError('revoked hypothesis read')):
        assert not revoked_runtime.read(subject=owner,clearance=Sensitivity.PRIVATE)

    failed,owner,_=prepare_case(root/'failed',{**fixture,'id':'failed'})
    failed_runtime=FeedbackAssimilationRuntime(failed.journal,content_vault=failed.vault)
    failed_calls=[]
    async def fail(**kwargs):
        failed_calls.append(kwargs)
        raise RuntimeError('synthetic provider error')
    result=await failed_runtime.tick(subject=owner,call=fail)
    assert result['attempted']==result['unresolved']==1 and result['interpreted']==0
    await FeedbackAssimilationRuntime(failed.journal,content_vault=failed.vault).tick(subject=owner,call=fail)
    assert len(failed_calls)==1 and not failed_runtime.read(subject=owner,clearance=Sensitivity.PRIVATE)


with tempfile.TemporaryDirectory(prefix='alive-feedback-assimilation-') as folder:
    asyncio.run(test(Path(folder)))
print('HERMES_ALIVE_FEEDBACK_ASSIMILATION_OK')
