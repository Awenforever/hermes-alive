#!/usr/bin/env python3
"""Only an explicit owner pause may ask the host to withdraw scoped work."""
import argparse
import asyncio
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection, DispatchOutboxError, PolicyContext, Sensitivity
from alive_kernel.transport_publisher_bridge import QualifiedReceiptPublisher,TransportPublisherBridge
from run_alive_kernel_opportunity_execution import scenario
from run_transport_publisher_bridge import adapter_for


async def test(root,enhance,core):
    sys.path.insert(0,str(enhance))
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('pause_fixtures',enhance/'scripts/test-v021-bubble-footer.py')
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
    args = dict(publisher=publisher,route=route)
    adapter.fail_next = True
    await adapter.send('peer',text,metadata={'_hermes_transport_binding_v1':binding.event.payload['transport_binding']})
    try: await bridge.withdraw_paused(binding.event.event_id,**args)
    except DispatchOutboxError: pass
    else: raise AssertionError('enabled policy allowed withdrawal')
    queue = adapter._hermes_transport_receipts_v1
    assert queue.count(adapter._account_id,'peer') > 0
    owner = binding.event.subject
    policies = AutonomyPolicyProjection(journal)
    prior = policies.current(owner)
    with closing(policies._connect()) as connection,connection:
        connection.execute('UPDATE autonomy_policies_v1 SET enabled=0,updated_at=? WHERE subject=?',(datetime.now(timezone.utc).isoformat(),owner))
    try: await bridge.withdraw_paused(binding.event.event_id,**args)
    except DispatchOutboxError: pass
    else: raise AssertionError('forged policy cache authorized withdrawal')
    with closing(policies._connect()) as connection,connection:
        connection.execute('UPDATE autonomy_policies_v1 SET enabled=1,updated_at=? WHERE subject=?',(prior.updated_at.isoformat(),owner))
    change = policies.append_update(subject=owner,actor=owner,expected_revision=prior.revision,
        enabled=False,context=PolicyContext(can_interrupt=False),operation_id='explicit-pause')
    assert policies.apply(change).outcome == 'recorded'
    result = await bridge.withdraw_paused(binding.event.event_id,**args)
    assert result.event.payload['removed_count'] > 0 and not result.event.payload['external_recall_proven']
    assert queue.count(adapter._account_id,'peer') == 0 and not adapter.sent
    count = journal.last_sequence()
    replay = await bridge.withdraw_paused(binding.event.event_id,**args)
    assert replay.event.event_id == result.event.event_id and journal.last_sequence()==count
    # Simulate loss of a host deny without changing the ledger epoch. The previous
    # journal result must not cause recovery to skip reasserting the host request.
    with queue._connect() as connection:
        connection.execute('DELETE FROM transport_withdrawals_v1')
    adapter.fail_next = True
    await adapter.send('peer','simulated restored pending work',metadata={'_hermes_transport_binding_v1':binding.event.payload['transport_binding']})
    assert queue.count(adapter._account_id,'peer')==1
    await bridge.withdraw_paused(binding.event.event_id,**args)
    assert queue.count(adapter._account_id,'peer')==0
    await adapter._drain_pending('peer')
    assert not adapter.sent
    observations = bridge.ingest(binding.event.event_id,**args)
    assert [r.event.payload['phase'] for r in observations['records']] == ['queued','withdrawn','queued','withdrawn']
    assert not journal.read(event_type='outcome.recorded')
    disabled = policies.current(owner)
    resumed = policies.append_update(subject=owner,actor=owner,expected_revision=disabled.revision,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='resume')
    assert policies.apply(resumed).outcome == 'recorded'
    with closing(policies._connect()) as connection,connection:
        connection.execute('UPDATE autonomy_policies_v1 SET enabled=0,revision=?,policy_event_id=?,updated_at=? WHERE subject=?',
            (disabled.revision,disabled.event_id,disabled.updated_at.isoformat(),owner))
    try: await bridge.withdraw_paused(binding.event.event_id,**args)
    except DispatchOutboxError: pass
    else: raise AssertionError('stale genuine pause replayed after newer resume')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enhance-root',type=Path,required=True)
    parser.add_argument('--hermes-root',type=Path)
    args = parser.parse_args()
    if args.hermes_root: sys.path.insert(0,str(args.hermes_root.resolve()))
    with tempfile.TemporaryDirectory(prefix='alive-withdraw-') as folder:
        asyncio.run(test(Path(folder),args.enhance_root.resolve(),args.hermes_root))
    print('HERMES_ALIVE_PUBLISHER_WITHDRAWAL_OK')
