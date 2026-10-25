#!/usr/bin/env python3
"""Change-sensitive wait/restart/expiry composition; synthetic inference only."""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (AutonomyPolicyProjection, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    EventEnvelope, ExperienceJournal, PolicyContext, MemoryProjection, MemoryProposal, MemoryKind, MemoryAuthority)
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
from alive_kernel.agenda import AgendaProposal, AgendaItemKind, AgendaAuthority, AgendaState
from alive_kernel.events import Sensitivity
from run_alive_kernel_expression_runtime import scenario


async def test(root):
    journal, params, _ = await scenario(root/'kernel', 'share', return_ready=True)
    runtime = AutonomousCycleRuntime(journal)
    policies = AutonomyPolicyProjection(journal)
    def policy(enabled):
        current = policies.current('user:test')
        policies.apply(policies.append_update(subject='user:test',actor='user:test',
            expected_revision=current.revision if current else 0,enabled=enabled,
            context=PolicyContext(can_interrupt=enabled),operation_id='policy:'+str(journal.last_sequence())))
    policy(True)
    calls, reconciliations = [], []
    async def silent(**kwargs):
        calls.append(kwargs['task'])
        assert kwargs['task']=='alive_opportunity_candidates'
        return SimpleNamespace(model='synthetic/silence',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({'candidates':[]})))])
    async def resolve(record):
        raise AssertionError('fixture has no publisher bindings')
    expression = {k:v for k,v in params.items() if k not in ('subject','operation_id','policy_context')}
    expression['call'] = silent
    original_tick = runtime.reconciliation.tick
    async def tick(**kwargs):
        reconciliations.append(kwargs)
        return await original_tick(**kwargs)
    runtime.reconciliation.tick = tick
    serial = 0
    async def step(**changes):
        nonlocal serial
        serial += 1
        options = dict(subject='user:test',operation_id='reconsider:'+str(serial),
            expression_parameters=expression,resolve_binding=resolve,reconsider_after_seconds=300,
            cognition_configuration_id='fixture-config')
        return await runtime.cycle(**{**options, **changes})
    assert (await step()).disposition=='silence' and len(calls)==1
    first = journal.read(event_type='cognition.wait_recorded')[-1]
    runtime.reconsideration.clock=lambda:first.event.observed_at-timedelta(seconds=1)
    context=runtime.reconsideration.capture(subject='user:test',configuration_id='fixture-config',
        execute=False,policy=policies.current('user:test'),parameters=expression,window_seconds=300)
    assert runtime.reconsideration.current(subject='user:test',configuration_id='fixture-config',context=context) is None
    runtime.reconsideration.clock=lambda:datetime.now(timezone.utc)
    try: await step(reconsider_after_seconds=True)
    except ValueError: pass
    else: raise AssertionError('boolean reconsideration budget accepted')
    assert len(calls)==1
    replay = await runtime.cycle(subject='user:test',operation_id='reconsider:1',
        expression_parameters=expression,resolve_binding=resolve,reconsider_after_seconds=300,
        cognition_configuration_id='fixture-config')
    assert replay.disposition=='silence' and len(calls)==1
    assert journal.read(event_type='cognition.wait_recorded')[-1].event==first.event
    assert (await step()).disposition=='waiting_for_change' and len(calls)==1
    assert len(reconciliations)==4 and len(journal.read(event_type='cognition.wait_recorded'))==1
    assert not first.event.payload['authority_granted']
    runtime = AutonomousCycleRuntime(ExperienceJournal(journal.path))
    assert (await step()).disposition=='waiting_for_change' and len(calls)==1
    # Another owner's journal activity must not wake this owner.
    journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor='user:other',subject='user:other',payload={'synthetic':True}))
    assert (await step()).disposition=='waiting_for_change' and len(calls)==1
    journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor='user:test',subject='user:test',payload={'synthetic':True}))
    assert (await step()).disposition=='silence' and len(calls)==2
    # A fresh source changes the active evidence before any model is spent.
    DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic-fixture',
        title='new finding',summary='A new bicycle method, unverified.',
        url='https://example.invalid/new-finding',observed_at=datetime.now(timezone.utc)),subject='user:test')
    assert (await step()).disposition=='silence' and len(calls)==3
    assert (await step()).disposition=='waiting_for_change' and len(calls)==3
    # Synthetic clock advance, not a wall-clock sleep; wait is not extended by reuse.
    latest = journal.read(event_type='cognition.wait_recorded')[-1]
    deadline = datetime.fromisoformat(latest.event.payload['valid_until'])
    runtime.reconsideration.clock = lambda: deadline + timedelta(seconds=1)
    assert (await step()).disposition=='silence' and len(calls)==4
    runtime.reconsideration.clock = lambda: datetime.now(timezone.utc)
    # Pause is reconciled before waiting and must never enter the model.
    policy(False)
    assert (await step()).disposition=='paused' and len(calls)==4
    policy(True)
    assert (await step()).disposition=='silence' and len(calls)==5
    # If retained generation content disappears, it is no longer proof for wait.
    completed = journal.read(event_type='opportunity.synthesis_completed')[-1]
    runtime.preparation.vault.erase_item(completed.event.payload['content']['content_id'])
    assert (await step()).disposition=='silence' and len(calls)==6
    # Host-owned configuration and cycle identities remain usable across waits.
    host = AutonomousHostRuntime(runtime,subject='user:test',configuration_id='fixture-config')
    result = await host.run(build_parameters=lambda:dict(expression_parameters=expression,
        resolve_binding=resolve,reconsider_after_seconds=300),stop=asyncio.Event(),max_cycles=2,interval_seconds=0)
    assert result['completed_cycles']==2 and len(calls)==6
    assert [r.event.payload['disposition'] for r in journal.read(event_type='autonomous.host.closed')]==[
        'waiting_for_change','waiting_for_change']
    assert (await step(cognition_configuration_id='changed-model-route')).disposition=='silence' and len(calls)==7
    assert (await step(cognition_configuration_id='changed-model-route')).disposition=='waiting_for_change' and len(calls)==7
    assert (await step(reconsider_after_seconds=60)).disposition=='silence' and len(calls)==8
    # A source event entering while inference runs must prevent wait publication.
    def inbound():
        return journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
            actor='user:test',subject='user:test',payload={'synthetic':True}))
    inbound()
    previous = len(journal.read(event_type='cognition.wait_recorded'))
    async def interrupted(**kwargs):
        inbound()
        return await silent(**kwargs)
    changed = {**expression,'call':interrupted}
    assert (await step(expression_parameters=changed)).disposition=='silence' and len(calls)==9
    assert len(journal.read(event_type='cognition.wait_recorded'))==previous
    assert (await step()).disposition=='silence' and len(calls)==10
    memory = MemoryProjection(journal).append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,
        subject='user:test',predicate='profile.content_preferences',value='Prefer bicycle repair.',
        authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(inbound().event.event_id,),confidence=1),actor='user:test')
    assert (await step()).disposition=='silence' and len(calls)==11
    assert (await step()).disposition=='waiting_for_change' and len(calls)==11
    before_erasure=journal.last_sequence()
    runtime.preparation.expression.planning.synth.context_reader.memory.content_vault.erase_item(
        memory.event.payload['content']['content_id'])
    assert journal.last_sequence()==before_erasure
    assert (await step()).disposition=='silence' and len(calls)==12
    source=journal.read(event_type='discovery.opportunity_observed')[-1]
    before_erasure=journal.last_sequence()
    runtime.preparation.vault.erase_item(source.event.payload['content']['content_id'])
    assert journal.last_sequence()==before_erasure
    assert (await step()).disposition=='silence' and len(calls)==13
    # Transport attention still wins over an otherwise current wait.
    original_tick=runtime.reconciliation.tick
    async def attention(**kwargs):
        return {**await original_tick(**kwargs),'failed_bindings':1}
    runtime.reconciliation.tick=attention
    assert (await step()).disposition=='reconciliation_attention' and len(calls)==13
    runtime.reconciliation.tick=original_tick
    # An unresolved provider run stays attempted; it is not silence or wait.
    inbound()
    failed_calls=[]
    async def failed(**kwargs):
        failed_calls.append(kwargs['task'])
        raise RuntimeError('synthetic provider failure')
    failure_args=dict(subject='user:test',operation_id='failed-reconsideration',
        expression_parameters={**expression,'call':failed},resolve_binding=resolve,
        reconsider_after_seconds=300,cognition_configuration_id='fixture-config')
    previous=len(journal.read(event_type='cognition.wait_recorded'))
    for _ in range(2):
        try: await runtime.cycle(**failure_args)
        except (ValueError, RuntimeError): pass
        else: raise AssertionError('provider failure became a closed wait')
    assert len(failed_calls)==1 and len(journal.read(event_type='cognition.wait_recorded'))==previous
    # A future agenda boundary caps wait even if no source text changes.
    authority=inbound()
    agenda=runtime.preparation.expression.planning.synth.reader.agenda
    due=datetime.now(timezone.utc)+timedelta(minutes=1)
    proposal=agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.COMMITMENT,
        subject='user:test',details={'synthetic':'upcoming commitment'},
        authority=AgendaAuthority.USER_EXPLICIT,source_event_ids=(authority.event.event_id,),
        confidence=1,due_at=due),actor='user:test')
    assert agenda.apply(proposal).outcome=='active'
    transition=agenda.append_transition(item_id=proposal.event.payload['item_id'],
        to_state=AgendaState.SNOOZED,actor='user:test',authority=AgendaAuthority.USER_EXPLICIT,
        source_event_id=authority.event.event_id,reason='synthetic snooze',available_at=due)
    assert agenda.apply(transition).outcome=='transitioned'
    context=runtime.reconsideration.capture(subject='user:test',configuration_id='fixture-config',
        execute=False,policy=policies.current('user:test'),parameters=expression,window_seconds=300)
    assert context.valid_until<=due
    # A copied signed body under another event identity is not a canonical wait.
    assert (await step()).disposition=='silence'
    wait=journal.read(event_type='cognition.wait_recorded')[-1]
    journal.append(replace(wait.event,event_id='forged-wait-alias'))
    try: await step()
    except ValueError as error: assert str(error)=='reconsideration history lacks canonical provenance'
    else: raise AssertionError('cloned wait accepted')
    assert not journal.read(event_type='action.attempted') and not journal.read(event_type='dispatch.started')


with tempfile.TemporaryDirectory(prefix='alive-reconsideration-') as folder:
    asyncio.run(test(Path(folder)))
print('HERMES_ALIVE_RECONSIDERATION_OK')
