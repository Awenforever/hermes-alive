#!/usr/bin/env python3
"""Host lifetime/identity tests; fake cycle driver is not model-quality proof."""
import asyncio
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import DispatchOutbox,ExperienceJournal,EventEnvelope
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime


class Driver:
    def __init__(self,journal):
        self.outbox = DispatchOutbox(journal)
        self.operations = []
        self.fail = False
        self.change = False
        self.block = False
        self.entered = asyncio.Event()
        self.cleaned = False
    async def cycle(self,**kwargs):
        self.operations.append(kwargs['operation_id'])
        self.entered.set()
        if self.fail: raise RuntimeError('synthetic private failure')
        if self.change:
            self.change=False
            from alive_kernel.opportunity_synthesis import OpportunityEvidenceChanged
            raise OpportunityEvidenceChanged('synthetic evidence changed during inference')
        if self.block:
            try: await asyncio.Event().wait()
            finally: self.cleaned = True
        return SimpleNamespace(disposition='silence',reconciliation={'next_after_sequence':7},external_delivery_proven=False)


async def test(root):
    journal = ExperienceJournal(root/'journal.sqlite3')
    first = Driver(journal)
    host = AutonomousHostRuntime(first,subject='user:one',configuration_id='config')
    first.fail = True
    try: await host.step({})
    except RuntimeError: pass
    else: raise AssertionError('failed cycle became completion')
    failed=journal.read(event_type='autonomous.host.failed')[-1].event
    payload=dict(failed.payload);signature=payload.pop('integrity_authenticator')
    assert payload['failure_class']=='RuntimeError' and payload['phase']=='cognition'
    assert payload['subject']=='user:one' and payload['authority_granted'] is False
    assert 'synthetic private failure' not in repr(payload)
    assert host.protector.verify_json('autonomous.host.failed.v1',payload,signature)
    assert failed.causation_id==payload['cycle_event_id']
    operation = first.operations[-1]
    restarted = Driver(ExperienceJournal(journal.path))
    recovered = AutonomousHostRuntime(restarted,subject='user:one',configuration_id='config')
    await recovered.step({})
    assert restarted.operations==[operation]
    await recovered.step({})
    assert restarted.operations[-1]!=operation
    bound_identity=[]
    await recovered.step_bound(lambda cycle:bound_identity.append(cycle.operation_id) or {})
    assert bound_identity==[restarted.operations[-1]]
    try: await recovered.step_bound(lambda cycle:{'operation_id':'foreign-operation'})
    except ValueError: pass
    else: raise AssertionError('factory overrode durable operation identity')
    waiting=recovered.open_cycle().operation_id
    await recovered.step_bound(lambda cycle:{})
    assert restarted.operations[-1]==waiting
    before = len(journal.read(event_type='autonomous.host.closed'))
    stop = asyncio.Event()
    result = await recovered.run(build_parameters=lambda:{},stop=stop,max_cycles=2,interval_seconds=0)
    assert result['completed_cycles']==2 and result['exit_reason']=='budget'
    assert len(journal.read(event_type='autonomous.host.closed'))==before+2
    stepped=[]
    async def bound_step(parameters):
        stepped.append(parameters)
        return await recovered.step_bound(lambda _cycle:parameters)
    result=await recovered.run(build_parameters=lambda:{},stop=asyncio.Event(),max_cycles=2,
        interval_seconds=0,cycle_step=bound_step)
    assert result['completed_cycles']==2 and stepped==[{},{}]
    continuous_driver=Driver(journal)
    continuous_host=AutonomousHostRuntime(continuous_driver,subject='user:continuous',
                                         configuration_id='config',execute=True)
    continuous_stop=asyncio.Event()
    async def continuous_step(parameters):
        outcome=await continuous_host.step(parameters)
        if len(continuous_driver.operations)==2:continuous_stop.set()
        return outcome
    result=await continuous_host.run(build_parameters=lambda:{},stop=continuous_stop,
        continuous=True,interval_seconds=.001,cycle_step=continuous_step)
    assert result['completed_cycles']==2 and result['exit_reason']=='stopped'
    assert len(set(continuous_driver.operations))==2 and not continuous_host.running
    continuous_driver.change=True
    changed_stop=asyncio.Event();prior_count=len(continuous_driver.operations)
    async def changed_step(parameters):
        result=await continuous_host.step(parameters)
        if len(continuous_driver.operations)==prior_count+2:changed_stop.set()
        return result
    result=await continuous_host.run(build_parameters=lambda:{},stop=changed_stop,
        continuous=True,interval_seconds=.001,cycle_step=changed_step)
    assert result['completed_cycles']==2 and result['exit_reason']=='stopped'
    assert continuous_driver.operations[-2]!=continuous_driver.operations[-1]
    closed=journal.read(event_type='autonomous.host.closed')
    assert [r.event.payload['disposition'] for r in closed][-2:]==['evidence_changed','silence']
    async def paused_step(parameters):return SimpleNamespace(disposition='paused')
    result=await continuous_host.run(build_parameters=lambda:{},stop=asyncio.Event(),
        continuous=True,interval_seconds=.001,cycle_step=paused_step)
    assert result['completed_cycles']==1 and result['exit_reason']=='paused'
    for disposition in ('not_authorized','attempt_unavailable','reconciliation_attention',
                        'content_review_attention','shadow_selected',None):
        async def attention_step(parameters):return SimpleNamespace(disposition=disposition)
        result=await continuous_host.run(build_parameters=lambda:{},stop=asyncio.Event(),
            continuous=True,interval_seconds=.001,cycle_step=attention_step)
        expected=disposition if disposition not in ('shadow_selected',None) else 'unexpected_disposition'
        assert result['completed_cycles']==1 and result['exit_reason']==expected
    # Lifetime control only: these synthetic outcomes confer no send authority.
    review=journal.append(EventEnvelope(event_id='test:bounded-review',event_type='test.review',
        source='test',actor='system:test',subject='user:continuous')).event
    witness=SimpleNamespace(review_event_id=review.event_id,
        valid_until=review.observed_at+timedelta(hours=1))
    for capable,proof,window,expected_cycles in (
            (False,witness,300,1),(True,witness,300,2),
            (True,None,300,1),(True,witness,None,1),
            (True,SimpleNamespace(review_event_id=review.event_id,
                valid_until=datetime.now(timezone.utc)-timedelta(seconds=1)),300,1)):
        calls=[];bounded_stop=asyncio.Event()
        async def bounded_step(parameters):
            calls.append(parameters)
            if len(calls)==2:
                bounded_stop.set()
                return SimpleNamespace(disposition='content_deferred')
            return SimpleNamespace(disposition='content_review_attention',content_rejection=proof,
                content_rejection_window_seconds=window)
        result=await continuous_host.run(build_parameters=lambda:{},stop=bounded_stop,
            continuous=True,continue_content_review=capable,interval_seconds=.001,cycle_step=bounded_step)
        assert result['completed_cycles']==expected_cycles
        assert result['exit_reason']==('stopped' if expected_cycles==2 else 'content_review_attention')
    continuous_driver.fail=True
    result=await continuous_host.run(build_parameters=lambda:{},stop=asyncio.Event(),
        continuous=True,interval_seconds=.001)
    assert result['completed_cycles']==0 and result['exit_reason']=='cycle_failed'
    for options in ({}, {'continuous':True,'interval_seconds':0},
                    {'continuous':True,'max_cycles':2}, {'continuous':'yes'}):
        try:await continuous_host.run(build_parameters=lambda:{},stop=asyncio.Event(),**options)
        except ValueError:pass
        else:raise AssertionError('implicit/unbounded/busy-loop lifetime accepted')
    try:await recovered.run(build_parameters=lambda:{},stop=asyncio.Event(),continuous=True)
    except ValueError:pass
    else:raise AssertionError('bounded shadow silently became continuous')
    other = AutonomousHostRuntime(Driver(journal),subject='user:other',configuration_id='config')
    assert other.open_cycle().operation_id not in restarted.operations
    # Cooperative shutdown interrupts active work but does not close/fabricate it.
    blocked = Driver(journal)
    blocked.block = True
    blocked_host = AutonomousHostRuntime(blocked,subject='user:blocked',configuration_id='config')
    stop = asyncio.Event()
    task = asyncio.create_task(blocked_host.run(build_parameters=lambda:{},stop=stop,max_cycles=3,interval_seconds=0))
    await blocked.entered.wait()
    stop.set()
    status = await task
    assert status['exit_reason']=='stopped' and status['completed_cycles']==0 and blocked.cleaned
    assert not blocked_host.running
    active = blocked_host.open_cycle()
    assert active.operation_id==blocked.operations[-1]
    changed = AutonomousHostRuntime(Driver(journal),subject='user:blocked',configuration_id='changed')
    try: changed.open_cycle()
    except ValueError: pass
    else: raise AssertionError('active work reused changed configuration')
    already = asyncio.Event()
    already.set()
    untouched = Driver(journal)
    result = await AutonomousHostRuntime(untouched,subject='user:idle',configuration_id='config').run(
        build_parameters=lambda:{},stop=already,max_cycles=1)
    assert not untouched.operations and result['exit_reason']=='stopped'
    external = Driver(journal)
    external.block = True
    external_host = AutonomousHostRuntime(external,subject='user:external',configuration_id='config')
    active_task = asyncio.create_task(external_host.run(build_parameters=lambda:{},stop=asyncio.Event(),max_cycles=1))
    await external.entered.wait()
    active_task.cancel()
    try: await active_task
    except asyncio.CancelledError: pass
    else: raise AssertionError('external cancellation returned ordinary completion')
    assert external.cleaned and not external_host.running
    assert external_host.open_cycle().operation_id==external.operations[-1]
    promoted = AutonomousHostRuntime(Driver(journal),subject='user:external',configuration_id='config',execute=True)
    try: promoted.open_cycle()
    except ValueError: pass
    else: raise AssertionError('unfinished shadow promoted to live execution')
    foreign_open = other.open_cycle()
    foreign = journal.get(foreign_open.event_id).event
    journal.append(replace(foreign,event_id='foreign-signed-clone',subject='user:one',correlation_id=host.lane))
    try: recovered.open_cycle()
    except ValueError: pass
    else: raise AssertionError('signed foreign payload adopted another owner')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-host-runtime-') as folder:
        asyncio.run(test(Path(folder)))
    print('HERMES_ALIVE_AUTONOMOUS_HOST_RUNTIME_OK')
