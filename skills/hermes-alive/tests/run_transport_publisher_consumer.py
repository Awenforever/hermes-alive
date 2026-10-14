#!/usr/bin/env python3
"""Bounded durable consumer recovery, with no resend or real transport."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import DispatchOutbox, DispatchOutboxError, ExperienceJournal, Sensitivity
from alive_kernel.transport_publisher_bridge import QualifiedReceiptPublisher, TransportPublisherBridge
from alive_kernel.transport_publisher_consumer import TransportPublisherConsumer
from run_alive_kernel_opportunity_execution import scenario
from run_transport_publisher_bridge import adapter_for


async def exercise(root, enhance, core, race=False):
    sys.path.insert(0,str(enhance))
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('consumer_fixtures',enhance/'scripts/test-v021-bubble-footer.py')
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
    binding = bridge.bind(execution,publisher).event.event_id
    consumer = TransportPublisherConsumer(outbox)
    args = dict(publisher=publisher,route=route)
    adapter.fail_next = True
    await adapter.send('peer',text,metadata={'_hermes_transport_binding_v1':journal.get(binding).event.payload['transport_binding']})
    if race:
        await adapter._drain_pending('peer')
        physical = len(adapter.sent)
        barrier = threading.Barrier(2)
        def concurrent_poll(limit):
            competing = TransportPublisherConsumer(DispatchOutbox(ExperienceJournal(journal.path)))
            append_original = competing.journal.append
            def synchronized(event,**kwargs):
                if kwargs.get('precondition') is not None:
                    barrier.wait(timeout=30)
                return append_original(event,**kwargs)
            competing.journal.append = synchronized
            try: return competing.poll_once(binding,limit=limit,**args)
            except DispatchOutboxError as exc: return type(exc).__name__
        with ThreadPoolExecutor(max_workers=2) as pool:
            first,second = pool.submit(concurrent_poll,1),pool.submit(concurrent_poll,1024)
            results = [first.result(),second.result()]
        assert results.count('DispatchOutboxError') == 1
        assert len(journal.read(event_type='transport.publisher.checkpoint')) == 1
        consumer.poll_once(binding,**args)
        expected = adapter._hermes_transport_receipts_v1.read_receipts(adapter._account_id,'peer',journal.get(binding).event.payload['transport_binding'])['records'][-1]['seq']
        assert consumer.progress(binding,**args).through_sequence == expected
        assert len(adapter.sent) == physical and len(journal.read(event_type='dispatch.started')) == 1
        return
    append = journal.append
    def interrupted(event,**kwargs):
        if callable(event) and kwargs.get('precondition') is not None:
            raise OSError('synthetic interruption before checkpoint')
        return append(event,**kwargs)
    journal.append = interrupted
    try: consumer.poll_once(binding,**args)
    except OSError: pass
    else: raise AssertionError('checkpoint interruption ignored')
    journal.append = append
    assert journal.read(event_type='transport.publisher.observed')
    assert consumer.progress(binding,**args).through_sequence == 0
    before = len(journal.read(event_type='transport.publisher.observed'))
    reopened = TransportPublisherConsumer(DispatchOutbox(ExperienceJournal(journal.path)))
    page = reopened.poll_once(binding,**args)
    assert page['progress_advanced'] and page['progress'].through_sequence > 0
    assert len(journal.read(event_type='transport.publisher.observed')) == before
    await adapter._drain_pending('peer')
    physical = len(adapter.sent)
    page = reopened.poll_once(binding,**args)
    assert page['progress_advanced'] and all(r.event.payload['phase']=='acknowledged' for r in page['records'])
    sequence = journal.last_sequence()
    empty = reopened.poll_once(binding,**args)
    assert not empty['progress_advanced'] and empty['coverage_uncertain']
    assert journal.last_sequence() == sequence and len(adapter.sent) == physical
    store = adapter._hermes_transport_receipts_v1
    store.receipts_available = False
    await adapter.send('peer','third synthetic notification',metadata={'_hermes_transport_binding_v1':journal.get(binding).event.payload['transport_binding']})
    physical = len(adapter.sent)
    prior = reopened.progress(binding,**args)
    unhealthy = reopened.poll_once(binding,**args)
    assert unhealthy['available'] is False and not unhealthy['progress_advanced']
    assert unhealthy['records'] and reopened.progress(binding,**args) == prior
    before = len(journal.read(event_type='transport.publisher.observed'))
    store.receipts_available = True
    healthy = reopened.poll_once(binding,**args)
    assert healthy['progress_advanced']
    assert len(journal.read(event_type='transport.publisher.observed')) == before
    # A same-epoch rolled-back sequence counter must not look like an empty page.
    with store._connect() as connection:
        high_water = connection.execute('SELECT seq FROM sqlite_sequence WHERE name=?',('transport_receipts_v1',)).fetchone()['seq']
        connection.execute('UPDATE sqlite_sequence SET seq=0 WHERE name=?',('transport_receipts_v1',))
    try: reopened.poll_once(binding,**args)
    except DispatchOutboxError: pass
    else: raise AssertionError('ledger sequence rollback silently accepted')
    with store._connect() as connection:
        connection.execute('UPDATE sqlite_sequence SET seq=? WHERE name=?',(high_water,'transport_receipts_v1'))
        original_epoch = store.publisher_epoch
        connection.execute('UPDATE transport_receipt_meta_v1 SET value=? WHERE name=?',('f'*64,'epoch'))
    try: reopened.progress(binding,**args)
    except DispatchOutboxError: pass
    else: raise AssertionError('rebuilt ledger resumed old cursor')
    with store._connect() as connection:
        connection.execute('UPDATE transport_receipt_meta_v1 SET value=? WHERE name=?',(original_epoch,'epoch'))
    latest = journal.read(event_type='transport.publisher.checkpoint')[-1]
    fake = replace(latest.event,event_id='consumer-forged',subject='user:other')
    journal.append(fake)
    try: reopened.progress(binding,**args)
    except DispatchOutboxError: pass
    else: raise AssertionError('foreign-owner checkpoint silently skipped')
    assert len(adapter.sent) == physical
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='outcome.recorded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enhance-root',type=Path,required=True)
    parser.add_argument('--hermes-root',type=Path)
    args = parser.parse_args()
    if args.hermes_root: sys.path.insert(0,str(args.hermes_root.resolve()))
    with tempfile.TemporaryDirectory(prefix='alive-consumer-') as folder:
        asyncio.run(exercise(Path(folder)/'recovery',args.enhance_root.resolve(),args.hermes_root))
        asyncio.run(exercise(Path(folder)/'race',args.enhance_root.resolve(),args.hermes_root,True))
    print('HERMES_ALIVE_TRANSPORT_PUBLISHER_CONSUMER_OK')
