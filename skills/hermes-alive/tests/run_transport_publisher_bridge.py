#!/usr/bin/env python3
"""Real journal/lease with a separate actual enhance producer, synthetic IO."""
import argparse
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import DispatchOutbox, DispatchOutboxError, ExperienceJournal, Sensitivity
from alive_kernel.event_store import EventConflictError
from alive_kernel.dispatch_verifier import DispatchEvidenceVerifier
from alive_kernel.transport_publisher_bridge import QualifiedReceiptPublisher, TransportPublisherBridge
from run_alive_kernel_opportunity_execution import scenario


def adapter_for(fixtures, hermes_root):
    if hermes_root is None:
        return fixtures.FakeAdapter()
    from gateway.config import PlatformConfig
    from gateway.platforms.weixin import WeixinAdapter
    class NativeAdapter(WeixinAdapter):
        def __init__(self):
            super().__init__(PlatformConfig(enabled=True,token='synthetic-token',extra={
                'account_id':'synthetic-account','send_chunk_delay_seconds':0}))
            self._send_session = object()
            self._token_store = fixtures.Tokens()
            self.sent, self.fail_next, self.cooldown_failures = [], False, 0
        async def _send_text_chunk(self, **kwargs):
            await fixtures.FakeAdapter._send_text_chunk(self, **kwargs)
    return NativeAdapter()


async def test(root, enhance, hermes_root=None):
    sys.path.insert(0, str(enhance))
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('receipt_fixtures', enhance / 'scripts/test-v021-bubble-footer.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    route = {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None}
    journal, outbox, lease, _, text = await scenario(root/'kernel', 'expression', transport_route=route, return_ready=True)
    execution = outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
    home = root/'profile'
    home.mkdir()
    os.environ['HERMES_HOME'] = str(home)
    adapter = adapter_for(fixtures,hermes_root)
    assert patch_adapter(adapter)
    digest = hashlib.sha256((enhance/'hermes_wechat_enhance/v021_bubble_footer.py').read_bytes()).hexdigest()
    publisher = QualifiedReceiptPublisher(adapter,digest,'synthetic',home,True)
    bridge = TransportPublisherBridge(outbox)
    binding = bridge.bind(execution, publisher)
    assert bridge.bind(execution, publisher).event.event_id == binding.event.event_id
    try: bridge.bind(replace(execution, lease=replace(lease,token='wrong-token')),publisher)
    except DispatchOutboxError: pass
    else: raise AssertionError('foreign lease bound publisher')
    adapter.fail_next = True
    result = await adapter.send('peer',text,metadata={'_hermes_transport_binding_v1':binding.event.payload['transport_binding']})
    assert result.success and not adapter.sent
    page = bridge.ingest(binding.event.event_id,publisher=publisher,route=route)
    assert [r.event.payload['phase'] for r in page['records']] == ['queued']
    assert page['coverage_uncertain'] and not page['external_delivery_proven']
    # Reopen the kernel and consume a deferred ACK after the original lease expired.
    reopened = TransportPublisherBridge(DispatchOutbox(ExperienceJournal(journal.path)))
    await asyncio.create_task(adapter._drain_pending('peer'))
    late = datetime.now(timezone.utc) + timedelta(minutes=2)
    complete = reopened.ingest(binding.event.event_id,publisher=publisher,route=route,now=late)
    assert [r.event.payload['phase'] for r in complete['records']] == ['queued','acknowledged']
    count = journal.last_sequence()
    assert [r.event.event_id for r in reopened.ingest(binding.event.event_id,publisher=publisher,route=route,now=late)['records']] == [r.event.event_id for r in complete['records']]
    assert journal.last_sequence() == count
    assert not reopened.ingest(binding.event.event_id,publisher=publisher,route=route,after_sequence=complete['next_sequence'],now=late)['records']
    for wrong_route, wrong_publisher in (({**route,'chat_id':'other'},publisher),
            (route,replace(publisher,source_digest='a'*64)),(route,replace(publisher,profile_home=root))):
        try: reopened.ingest(binding.event.event_id,publisher=wrong_publisher,route=wrong_route,now=late)
        except DispatchOutboxError: pass
        else: raise AssertionError('foreign publisher/route accepted')
    store = adapter._hermes_transport_receipts_v1
    original_reader = store.read_receipts
    # Changing an otherwise structurally valid occurrence cannot overwrite history.
    def conflict(*args, **kwargs):
        original = original_reader(*args, **kwargs)
        original['records'][0]['seq'] += 100
        original['records'] = original['records'][:1]
        return original
    store.read_receipts = conflict
    try: reopened.ingest(binding.event.event_id,publisher=publisher,route=route,now=late)
    except DispatchOutboxError: pass  # reader's source digest is no longer qualified
    else: raise AssertionError('changed reader implementation accepted')
    store.read_receipts = original_reader
    with store._connect() as connection:
        connection.execute('UPDATE transport_receipts_v1 SET observed_at=observed_at+0.5 WHERE seq=?', (complete['records'][0].event.payload['publisher_sequence'],))
    try: reopened.ingest(binding.event.event_id,publisher=publisher,route=route,now=late)
    except EventConflictError: pass
    else: raise AssertionError('changed occurrence replaced canonical evidence')
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='outcome.recorded')
    assert not journal.read(event_type='dispatch.delivered')
    for record in journal.read(event_type='transport.publisher.observed'):
        assert not record.event.payload['external_delivery_proven']
        assert not record.event.payload['delivery_authority_granted']
        assert text not in record.event.canonical_json() and 'id-1' not in record.event.canonical_json()
        assert not DispatchEvidenceVerifier(journal,outbox.protector).verify(record,journal.get('action.attempt:' + lease.attempt_id))


async def composed(root, enhance, hermes_root=None):
    from run_alive_kernel_host_runtime_chain import prepare
    from hermes_wechat_enhance.v021_bubble_footer import patch_adapter
    spec = importlib.util.spec_from_file_location('composed_fixtures', enhance / 'scripts/test-v021-bubble-footer.py')
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    route = {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None}
    journal, outbox, lease, _, expected, _, prepared, runtime = await prepare(root/'kernel',route)
    home = root/'profile'
    home.mkdir()
    os.environ['HERMES_HOME'] = str(home)
    adapter = adapter_for(fixtures,hermes_root)
    adapter.MAX_MESSAGE_LENGTH = 10000
    assert patch_adapter(adapter)
    digest = hashlib.sha256((enhance/'hermes_wechat_enhance/v021_bubble_footer.py').read_bytes()).hexdigest()
    publisher = QualifiedReceiptPublisher(adapter,digest,'synthetic',home,True)
    params = dict(publisher=publisher,clearance=Sensitivity.PRIVATE,profile_id='synthetic',
        hermes_home=home,resolve_target=lambda p,t:(t,None,None),extract_media=lambda text:([],text),
        observe_profile_home=lambda:home)
    expected_chunks = adapter._split_text(adapter.format_message(expected))
    adapter.fail_next = True
    observed = await runtime.execute_prepared_with_publisher(prepared,lease,**params)
    assert observed.adapter_result.success and not adapter.sent and not observed.external_delivery_proven
    assert [r.event.payload['phase'] for r in observed.observations['records']] == ['queued'] * len(expected_chunks)
    try: await runtime.execute_prepared_with_publisher(prepared,lease,**params)
    except DispatchOutboxError: pass
    else: raise AssertionError('prepared action submitted twice')
    await adapter._drain_pending('peer')
    assert [sent[1].rsplit('\n\n---\n\n',1)[0] for sent in adapter.sent] == expected_chunks
    bridge = TransportPublisherBridge(DispatchOutbox(ExperienceJournal(journal.path)))
    result = bridge.ingest(observed.binding_event_id,publisher=publisher,route=route)
    assert [r.event.payload['phase'] for r in result['records']] == ['queued'] * len(expected_chunks) + ['acknowledged'] * len(expected_chunks)
    assert [r.event.payload['client_reference'] for r in result['records'][:len(expected_chunks)]] == [r.event.payload['client_reference'] for r in result['records'][len(expected_chunks):]]
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='outcome.recorded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enhance-root',type=Path,required=True)
    parser.add_argument('--hermes-root',type=Path)
    args = parser.parse_args()
    if args.hermes_root:
        sys.path.insert(0,str(args.hermes_root.resolve()))
    with tempfile.TemporaryDirectory(prefix='alive-publisher-bridge-') as folder:
        root = Path(folder)
        asyncio.run(test(root/'observations',args.enhance_root.resolve(),args.hermes_root))
        asyncio.run(composed(root/'composed',args.enhance_root.resolve(),args.hermes_root))
    print('HERMES_ALIVE_TRANSPORT_PUBLISHER_BRIDGE_OK')
