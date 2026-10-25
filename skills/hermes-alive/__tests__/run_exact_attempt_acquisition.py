#!/usr/bin/env python3
"""Prepared-cycle acquisition does not lease an unrelated eligible attempt."""
import asyncio
from datetime import timedelta
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import DispatchOutboxError
from run_alive_kernel_opportunity_execution import scenario


async def test(root):
    _,outbox,lease,_,_ = await scenario(root,'expression',return_ready=True)
    moment = lease.lease_until + timedelta(microseconds=1)
    assert moment < lease.execute_by
    assert outbox.acquire(worker_id='other',subject='user:other',attempt_id=lease.attempt_id,now=moment) is None
    assert outbox.acquire(worker_id='other',subject=lease.subject,attempt_id='missing-attempt',now=moment) is None
    actual = outbox.acquire(worker_id='cycle',subject=lease.subject,attempt_id=lease.attempt_id,now=moment)
    assert actual is not None and actual.attempt_id==lease.attempt_id and actual.subject==lease.subject
    assert actual.generation==lease.generation+1
    assert outbox.acquire(worker_id='contender',subject=lease.subject,attempt_id=lease.attempt_id,now=moment) is None
    for bad in ('',False,'a'*129):
        try: outbox.acquire(worker_id='invalid',subject=bad,now=moment)
        except DispatchOutboxError: pass
        else: raise AssertionError('invalid owner selector admitted')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-exact-acquire-') as folder:
        asyncio.run(test(Path(folder)))
    print('HERMES_ALIVE_EXACT_ATTEMPT_ACQUISITION_OK')
