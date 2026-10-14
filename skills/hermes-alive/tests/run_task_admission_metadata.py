#!/usr/bin/env python3
"""Task-bound scope, isolation, resource cleanup and actual loop timers."""
import asyncio
from contextvars import ContextVar
from pathlib import Path
import sys
from run_admission_metadata_cache import event, values

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.admission_metadata import TaskAdmissionMetadataHandoff


async def run():
    origin = TaskAdmissionMetadataHandoff(ttl_seconds=1, max_pending=1)
    receiver = TaskAdmissionMetadataHandoff(ttl_seconds=1)
    sample = event()
    initial_callback_count = len(asyncio.current_task()._callbacks or ())
    marker = ContextVar('synthetic-private-context')
    token = marker.set('synthetic-do-not-retain')
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    state = getattr(asyncio.current_task(), origin.ATTRIBUTE)
    assert list(state['timer']._context.items()) == []
    assert all(not context.items() for _, context in asyncio.current_task()._callbacks)
    marker.reset(token)
    async def other():
        assert receiver.take(values(sample), runtime_home='/synthetic/profile-b') is None
        origin.remember(event('different-task'), runtime_home='/synthetic/profile-b')
        assert not hasattr(asyncio.current_task(), origin.ATTRIBUTE)
    await asyncio.create_task(other())
    received = receiver.take(values(sample), runtime_home='/synthetic/profile-b')
    assert received.quoted_message_id == 'outbound-1'
    assert origin.pending_tasks() == 0
    assert len(asyncio.current_task()._callbacks or ()) == initial_callback_count
    assert receiver.take(values(sample), runtime_home='/synthetic/profile-b') is None
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    assert receiver.take(values(sample), runtime_home='/synthetic/profile-c') is None
    assert origin.pending_tasks() == 0
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    origin.remember(sample, runtime_home='/synthetic/profile-c')
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    assert receiver.take(values(sample), runtime_home='/synthetic/profile-b') is None
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    assert receiver.take(values(event(text='rewritten')), runtime_home='/synthetic/profile-b') is None
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    origin.remember(sample, runtime_home='/synthetic/profile-b')
    assert receiver.take(values(sample), runtime_home='/synthetic/profile-b') is None
    cleanup = TaskAdmissionMetadataHandoff(ttl_seconds=.02)
    cleanup.remember(sample, runtime_home='/synthetic/profile-b')
    timed_state = getattr(asyncio.current_task(), cleanup.ATTRIBUTE)
    await asyncio.sleep(.04)
    assert not hasattr(asyncio.current_task(), cleanup.ATTRIBUTE)
    assert timed_state['cache']._entries == {} and cleanup.pending_tasks() == 0
    states = []
    async def dropped():
        origin.remember(sample, runtime_home='/synthetic/profile-b')
        states.append(getattr(asyncio.current_task(), origin.ATTRIBUTE))
    task = asyncio.create_task(dropped())
    await task
    await asyncio.sleep(0)
    assert not hasattr(task, origin.ATTRIBUTE) and origin.pending_tasks() == 0
    assert states[0]['cache']._entries == {} and states[0]['timer'].cancelled()
    entered = asyncio.Event()
    async def cancelled():
        origin.remember(sample, runtime_home='/synthetic/profile-b')
        entered.set()
        await asyncio.Event().wait()
    task = asyncio.create_task(cancelled())
    await entered.wait()
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass
    await asyncio.sleep(0)
    assert not hasattr(task, origin.ATTRIBUTE) and origin.pending_tasks() == 0
    print('HERMES_ALIVE_TASK_ADMISSION_METADATA_OK')


if __name__ == '__main__':
    asyncio.run(run())
