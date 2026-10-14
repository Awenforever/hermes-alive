#!/usr/bin/env python3
"""Bounded owner reconciliation across reopen, failure, wrap and pause."""
import argparse
import asyncio
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection,DispatchOutbox,EventEnvelope,ExperienceJournal,PolicyContext,Sensitivity
from alive_kernel.transport_publisher_bridge import QualifiedReceiptPublisher,TransportPublisherBridge
from alive_kernel.transport_reconciliation_runtime import TransportReconciliationRuntime
from run_alive_kernel_opportunity_execution import scenario
from run_transport_publisher_bridge import adapter_for


async def test(root,enhance,core):
    preseed = ExperienceJournal(root/'kernel'/'journal.sqlite3')
    for owner in ('user:test','user:other'):
        preseed.append(EventEnvelope(event_type='transport.publisher.bound',source='alive.transport.publisher',
            actor='system:alive-transport',subject=owner,payload={'unsigned':True}))
    sys.path.insert(0,str(enhance))
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('tick_fixtures',enhance/'scripts/test-v021-bubble-footer.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    route = {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None}
    journal,outbox,lease,_,text = await scenario(root/'kernel','expression',transport_route=route,return_ready=True)
    execution = outbox.begin_execution(lease,clearance=Sensitivity.PRIVATE)
    home = root/'profile'
    home.mkdir()
    os.environ['HERMES_HOME'] = str(home)
    adapter = adapter_for(fixtures,core)
    assert patch_adapter(adapter)
    publisher = QualifiedReceiptPublisher(adapter,hashlib.sha256((enhance/'hermes_wechat_enhance/v021_bubble_footer.py').read_bytes()).hexdigest(),'synthetic',home,True)
    bridge = TransportPublisherBridge(outbox)
    binding = bridge.bind(execution,publisher)
    adapter.fail_next = True
    await adapter.send('peer',text,metadata={'_hermes_transport_binding_v1':binding.event.payload['transport_binding']})
    calls = []
    def resolve(record):
        assert record.event.event_id == binding.event.event_id
        calls.append(record.event.event_id)
        return publisher,route
    runtime = TransportReconciliationRuntime(outbox)
    first = await runtime.tick(subject='user:test',resolve_binding=resolve,binding_limit=1)
    assert first['scanned']==1 and first['failed_bindings']==1 and not calls
    assert first['failures'][0]['stage']=='binding_provenance' and len(first['failures'][0]['reference'])==64
    assert first['next_after_sequence'] > 0 and not first['wrap_required']
    reopened = TransportReconciliationRuntime(DispatchOutbox(ExperienceJournal(journal.path)))
    second = await reopened.tick(subject='user:test',resolve_binding=resolve,after_sequence=first['next_after_sequence'],binding_limit=1)
    assert second['scanned']==1 and not second['failed_bindings'] and second['observed']>=1
    assert second['wrap_required'] and second['next_after_sequence']==0 and not adapter.sent
    # A corrupt old binding must not stop the next legitimate one in a batch.
    batch = await reopened.tick(subject='user:test',resolve_binding=resolve,binding_limit=16)
    assert batch['scanned']==2 and batch['failed_bindings']==1 and len(calls)==2
    assert batch['failures']==first['failures']
    stopped = []
    async def stalled_resolution(record):
        try: await asyncio.Event().wait()
        finally: stopped.append(True)
    timed = await reopened.tick(subject='user:test',resolve_binding=stalled_resolution,
        after_sequence=first['next_after_sequence'],operation_timeout=0.01)
    assert timed['failed_bindings']==1 and timed['failures'][0]['stage']=='publisher_resolution'
    assert stopped==[True] and not adapter.sent
    policy = AutonomyPolicyProjection(journal)
    async def pause_during_resolution(record):
        await asyncio.sleep(0)
        current = policy.current('user:test')
        change = policy.append_update(subject='user:test',actor='user:test',expected_revision=current.revision,
            enabled=False,context=PolicyContext(can_interrupt=False),operation_id='pause-during-resolution')
        assert policy.apply(change).outcome=='recorded'
        return publisher,route
    paused = await reopened.tick(subject='user:test',resolve_binding=pause_during_resolution,
        after_sequence=first['next_after_sequence'],binding_limit=1)
    assert not paused['failed_bindings'] and paused['withdrawal_requests']==1
    assert adapter._hermes_transport_receipts_v1.count(adapter._account_id,'peer')==0
    await adapter._drain_pending('peer')
    assert not adapter.sent
    cancelled = asyncio.CancelledError()
    async def cancel_resolution(record): raise cancelled
    try: await reopened.tick(subject='user:test',resolve_binding=cancel_resolution,after_sequence=first['next_after_sequence'])
    except asyncio.CancelledError as exc: assert exc is cancelled
    else: raise AssertionError('cancelled host tick became a silent retry')
    assert len(journal.read(event_type='dispatch.started'))==1 and not journal.read(event_type='outcome.recorded')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--enhance-root',type=Path,required=True)
    parser.add_argument('--hermes-root',type=Path)
    args=parser.parse_args()
    if args.hermes_root: sys.path.insert(0,str(args.hermes_root.resolve()))
    with tempfile.TemporaryDirectory(prefix='alive-reconcile-') as folder:
        asyncio.run(test(Path(folder),args.enhance_root.resolve(),args.hermes_root))
    print('HERMES_ALIVE_RECONCILIATION_RUNTIME_OK')
