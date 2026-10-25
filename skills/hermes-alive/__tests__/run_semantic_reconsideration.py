#!/usr/bin/env python3
"""Source-linked timing is a revisable cognitive suggestion, never a send timer."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (AutonomyPolicyProjection, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    EventEnvelope, ExperienceJournal, OpportunitySynthesizer, PolicyContext)
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.events import _thaw_json
from run_alive_kernel_expression_runtime import scenario


def response(value):
    return SimpleNamespace(model='synthetic/temporal-model',choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value)))])


async def test(root):
    journal,params,_=await scenario(root/'kernel','share',return_ready=True)
    policies=AutonomyPolicyProjection(journal)
    policies.apply(policies.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable'))
    runtime=AutonomousCycleRuntime(journal)
    calls=[]
    async def temporal(**kwargs):
        calls.append(kwargs)
        assert kwargs['task']=='alive_opportunity_candidates'
        data=json.loads(kwargs['messages'][1]['content'])
        item=data['opportunities'][0]
        return response(dict(candidates=[],abstentions=[dict(agenda_item_id=item['agenda_item_id'],
            reason='PRIVATE_TEMPORAL_REASON: user is temporarily busy; not a lasting preference.')],
            reconsiderations=[dict(agenda_item_id=item['agenda_item_id'],after_seconds=120,
                reason='PRIVATE_TIMING_REASON: re-evaluate later, without assuming availability or permission.')]))
    expression={k:v for k,v in params.items() if k not in ('subject','operation_id','policy_context')}
    expression['call']=temporal
    def args(operation):
        return dict(subject='user:test',operation_id=operation,expression_parameters=expression,
            resolve_binding=lambda record:None,reconsider_after_seconds=600,cognition_configuration_id='temporal-fixture')
    first=await runtime.cycle(**args('first'))
    assert first.disposition=='silence' and len(calls)==1
    planning=first.expression.planning
    origin=planning.interpretation_event_id.removeprefix('opportunity.synthesis:').removesuffix(':completed')
    interpreted=runtime.preparation.expression.planning.synth.load_completed(subject='user:test',operation_id=origin)
    hint=interpreted.reconsiderations[0]
    anchor=datetime.fromisoformat(json.loads(calls[0]['messages'][1]['content'])['as_of'])
    assert hint.reconsider_at==anchor+timedelta(seconds=120)
    wait=journal.read(event_type='cognition.wait_recorded')[-1]
    assert datetime.fromisoformat(wait.event.payload['valid_until'])==hint.reconsider_at
    assert wait.event.payload['timing'][0]['agenda_item_id']==hint.agenda_item_id
    assert 'PRIVATE_TIMING_REASON' not in repr(wait.event.payload)
    assert 'PRIVATE_TEMPORAL_REASON' not in repr(interpreted)
    runtime=AutonomousCycleRuntime(ExperienceJournal(journal.path))
    reopened=runtime.preparation.expression.planning.synth.load_completed(subject='user:test',operation_id=origin)
    assert reopened==interpreted
    assert (await runtime.cycle(**args('second'))).disposition=='waiting_for_change' and len(calls)==1
    assert journal.read(event_type='cognition.wait_recorded')[-1].event==wait.event
    # A new user input can reopen cognition before the model's proposed time.
    journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor='user:test',subject='user:test',payload={'synthetic':True}))
    positive=await runtime.cycle(**{**args('new-user-input'),
        'expression_parameters':{**expression,'call':params['call']}})
    assert positive.disposition=='shadow_selected' and positive.submission is None
    assert len(journal.read(event_type='cognition.wait_recorded'))==1
    # Resolved timing never moves just because the current clock moved.
    runtime.reconsideration.clock=lambda:hint.reconsider_at+timedelta(seconds=1)
    assert runtime.preparation.expression.planning.synth.load_completed(
        subject='user:test',operation_id=origin).reconsiderations[0].reconsider_at==hint.reconsider_at
    runtime.reconsideration.clock=lambda:datetime.now(timezone.utc)
    # Old signed wait records survive upgrades but cannot become current waits.
    legacy=_thaw_json(wait.event.payload)
    legacy.pop('integrity_authenticator'); legacy.pop('timing')
    legacy['method']='alive-reconsideration-v1'
    identity=runtime.outbox.protector.authenticate_json('alive-reconsideration-v1.identity',
        dict(subject='user:test',configuration_id=legacy['configuration_id'],operation_id=legacy['operation_id']))
    legacy['integrity_authenticator']=runtime.outbox.protector.authenticate_json('cognition.wait_recorded.v1',legacy)
    journal.append(replace(wait.event,event_id='cognition-wait:'+identity,payload=legacy))
    context=runtime.reconsideration.capture(subject='user:test',configuration_id='temporal-fixture',
        execute=False,policy=policies.current('user:test'),parameters=expression,window_seconds=600)
    assert runtime.reconsideration.current(subject='user:test',configuration_id='temporal-fixture',context=context) is None
    assert not journal.read(event_type='preference.observed')
    assert not journal.read(event_type='action.attempted') and not journal.read(event_type='dispatch.started')
    # Isolate bad optional suggestions; retain the abstention and any good ones.
    abstentions=interpreted.abstentions
    valid=dict(agenda_item_id=hint.agenda_item_id,after_seconds=120,reason='synthetic revisit')
    invalid=[{**valid,'after_seconds':True},{**valid,'after_seconds':1.0},
        {**valid,'after_seconds':0},{**valid,'after_seconds':86401},
        {**valid,'agenda_item_id':'foreign'}, {**valid,'reason':''},
        {**valid,'send_at_expiry':True}]
    synth=runtime.preparation.expression.planning.synth
    for value in invalid:
        accepted,rejected=synth._reconsiderations([value],abstentions,anchor)
        assert not accepted and rejected==1
    assert synth._reconsiderations([valid,valid],abstentions,anchor)==((),2)
    partial,rejected=synth._reconsiderations([valid,{**valid,'agenda_item_id':'foreign'}],abstentions,anchor)
    assert len(partial)==1 and rejected==1
    assert synth._reconsiderations({},abstentions,anchor)==((),1)
    assert synth._reconsiderations([valid],(),anchor)==((),1)
    # A malformed optional envelope does not erase separately valid non-action.
    async def malformed_hint(**kwargs):
        item=json.loads(kwargs['messages'][1]['content'])['opportunities'][0]
        return response(dict(candidates=[],abstentions=[dict(agenda_item_id=item['agenda_item_id'],
            reason='Synthetic valid non-action')],reconsiderations='not-an-envelope'))
    result=await synth.run(subject='user:test',operation_id='malformed-optional-hint',call=malformed_hint)
    assert len(result.abstentions)==1 and not result.reconsiderations and result.rejected_reconsideration_count==1
    assert synth.load_completed(subject='user:test',operation_id='malformed-optional-hint')==result
    # A bad suggestion must not suppress another source's legitimate candidate.
    extra=DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic-fixture',
        title='Other fixture',summary='Another public repair method.',url='https://example.invalid/other',
        observed_at=datetime.now(timezone.utc)),subject='user:test')
    async def mixed(**kwargs):
        data=json.loads(kwargs['messages'][1]['content'])
        first,second=data['opportunities'][:2]
        return response(dict(candidates=[dict(agenda_item_id=first['agenda_item_id'],kind='share',
            text='Tentative synthetic repair guide.',topic='fixture',dimensions={
                name:dict(value=.2,reason='synthetic') for name in
                ('user_value','urgency','novelty','confidence','risk','interruption_cost')})],
            abstentions=[dict(agenda_item_id=second['agenda_item_id'],reason='Temporarily defer this source.')],
            reconsiderations=[dict(agenda_item_id=first['agenda_item_id'],after_seconds=120,reason='invalid: positive source'),
                dict(agenda_item_id=second['agenda_item_id'],after_seconds=180,reason='Revisit this deferred source.')]))
    mixed_result=await synth.run(subject='user:test',operation_id='mixed-hints',call=mixed)
    assert len(mixed_result.candidates)==len(mixed_result.reconsiderations)==1
    assert mixed_result.rejected_reconsideration_count==1
    assert synth.load_completed(subject='user:test',operation_id='mixed-hints')==mixed_result
    for path in (root/'kernel').glob('experience.sqlite3*'):
        assert b'PRIVATE_TIMING_REASON' not in path.read_bytes()


with tempfile.TemporaryDirectory(prefix='alive-semantic-reconsideration-') as directory:
    asyncio.run(test(Path(directory)))
print('HERMES_ALIVE_SEMANTIC_RECONSIDERATION_OK')
