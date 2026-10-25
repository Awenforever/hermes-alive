#!/usr/bin/env python3
"""Adversarial composed submission; host owns any already-queued messages."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import MethodType

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection, DispatchOutboxError, PolicyContext, Sensitivity
from alive_kernel.transport_publisher_bridge import QualifiedReceiptPublisher
from run_alive_kernel_host_runtime_chain import prepare
from run_transport_publisher_bridge import adapter_for


async def exercise(root,enhance,core,mode):
    sys.path.insert(0,str(enhance))
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('failure_fixtures',enhance/'scripts/test-v021-bubble-footer.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    route = {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None}
    journal,outbox,lease,_,_,_,prepared,runtime = await prepare(root/'kernel',route)
    home = root/'profile'
    home.mkdir()
    os.environ['HERMES_HOME'] = str(home)
    adapter = adapter_for(fixtures,core)
    original_send = adapter.send
    sentinel = RuntimeError('synthetic original failure')
    cancellation = asyncio.CancelledError('synthetic caller cancellation')
    invocations = []
    returned = []
    async def controlled_send(self,*args,**kwargs):
        invocations.append(1)
        if mode == 'original-error': raise sentinel
        result = await original_send(*args,**kwargs)
        returned.append(result)
        if mode == 'cancel-after-queue': raise cancellation
        if mode == 'publication-failure':
            with self._hermes_transport_receipts_v1._connect() as connection:
                connection.execute('DROP TABLE transport_receipts_v1')
        return result
    adapter.send = MethodType(controlled_send,adapter)
    assert patch_adapter(adapter)
    publisher = QualifiedReceiptPublisher(adapter,hashlib.sha256((enhance/'hermes_wechat_enhance/v021_bubble_footer.py').read_bytes()).hexdigest(),'synthetic',home,True)
    if mode == 'cancel-after-queue': adapter.fail_next = True
    clocks = []
    def clock():
        clocks.append(1)
        if mode == 'pause-before-launch' and len(clocks) == 3:
            policy = AutonomyPolicyProjection(journal)
            current = policy.current('user:test')
            decision = policy.append_update(subject='user:test',actor='user:test',
                expected_revision=current.revision,enabled=False,context=PolicyContext(can_interrupt=False),
                operation_id='pause-before-launch')
            assert policy.apply(decision).outcome == 'recorded'
        return datetime.now(timezone.utc)
    params = dict(publisher=publisher,clearance=Sensitivity.PRIVATE,profile_id='synthetic',
        hermes_home=home,resolve_target=lambda p,t:(t,None,None),extract_media=lambda text:([],text),
        observe_profile_home=lambda:home,clock=clock)
    try:
        observed = await runtime.execute_prepared_with_publisher(prepared,lease,**params)
    except asyncio.CancelledError as exc:
        assert mode == 'cancel-after-queue' and exc is cancellation
    except RuntimeError as exc:
        assert mode == 'original-error' and exc is sentinel
    except DispatchOutboxError:
        assert mode == 'pause-before-launch'
    else:
        assert mode == 'publication-failure' and observed.adapter_result is returned[0]
        assert observed.publication_error_class == 'OperationalError' and observed.observations is None
        assert not observed.external_delivery_proven
    count = len(invocations)
    try: await runtime.execute_prepared_with_publisher(prepared,lease,**params)
    except DispatchOutboxError: pass
    else: raise AssertionError('failed/cancelled action submitted twice')
    assert len(invocations) == count
    if mode == 'pause-before-launch': assert count == 0 and not adapter.sent
    if mode == 'original-error': assert count == 1 and not adapter.sent
    if mode == 'cancel-after-queue':
        assert count == 1 and not adapter.sent
        assert adapter._hermes_wechat_v021_pending_queue.count(adapter._account_id,'peer') > 0
        records = journal.read(event_type='transport.publisher.observed')
        assert records and all(record.event.payload['phase']=='queued' for record in records)
        # Caller cancellation is not a host-FIFO cancellation; do NOT drain here.
    if mode == 'publication-failure': assert count == 1 and adapter.sent
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='outcome.recorded')
    assert not adapter._hermes_wechat_v021_retry_tasks


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enhance-root',type=Path,required=True)
    parser.add_argument('--hermes-root',type=Path)
    args = parser.parse_args()
    if args.hermes_root: sys.path.insert(0,str(args.hermes_root.resolve()))
    with tempfile.TemporaryDirectory(prefix='alive-submission-failure-') as folder:
        for mode in ('original-error','cancel-after-queue','publication-failure','pause-before-launch'):
            asyncio.run(exercise(Path(folder)/mode,args.enhance_root.resolve(),args.hermes_root,mode))
    print('HERMES_ALIVE_PUBLISHED_CHANNEL_FAILURES_OK')
