#!/usr/bin/env python3
"""Host lifetime/identity tests; fake cycle driver is not model-quality proof."""
import asyncio
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import DispatchOutbox,ExperienceJournal
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime


class Driver:
    def __init__(self,journal):
        self.outbox = DispatchOutbox(journal)
        self.operations = []
        self.fail = False
        self.block = False
        self.entered = asyncio.Event()
        self.cleaned = False
    async def cycle(self,**kwargs):
        self.operations.append(kwargs['operation_id'])
        self.entered.set()
        if self.fail: raise RuntimeError('synthetic private failure')
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
    operation = first.operations[-1]
    restarted = Driver(ExperienceJournal(journal.path))
    recovered = AutonomousHostRuntime(restarted,subject='user:one',configuration_id='config')
    await recovered.step({})
    assert restarted.operations==[operation]
    await recovered.step({})
    assert restarted.operations[-1]!=operation
    before = len(journal.read(event_type='autonomous.host.closed'))
    stop = asyncio.Event()
    result = await recovered.run(build_parameters=lambda:{},stop=stop,max_cycles=2,interval_seconds=0)
    assert result['completed_cycles']==2 and result['exit_reason']=='budget'
    assert len(journal.read(event_type='autonomous.host.closed'))==before+2
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
