#!/usr/bin/env python3
"""Submission permission is not delivery proof; old route grants stay strict."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import EventEnvelope, ExperienceJournal, HostCapabilityProjection, ReceiptLevel
from alive_kernel.host_capabilities import HostCapabilityError
from alive_kernel.event_store import JournalRecord
from alive_kernel.events import _thaw_json


def require_failure(operation):
    try:
        operation()
    except HostCapabilityError:
        return
    raise AssertionError('invalid receipt authority was accepted')


def test(root, offered, required):
    journal = ExperienceJournal(root/'experience.sqlite3')
    host = HostCapabilityProjection(journal)
    now = datetime.now(timezone.utc)
    snapshot = host.observe_snapshot(snapshot_id='actual-host-contract', hermes_version='0.22.5',
        plugin_api_version=1, capabilities={'hermes.channel.send': {
            'interface': 'core.adapter.send', 'available': True, 'public_api': True,
            'receipt_level': offered.value}}, observed_at=now)
    def authority(binding, **extra):
        event = EventEnvelope(event_id='user-authority:'+binding, event_type='conversation.inbound',
            source='test.synthetic', actor='user:test', subject='user:test',
            occurred_at=now, observed_at=now,
            payload={'authorizes_route_binding_id':binding, **extra})
        journal.append(event)
        return event.event_id
    def bind(binding, authority_id, **extra):
        return host.bind_route(binding_id=binding, subject='user:test', capability='hermes.channel.send',
            snapshot_event_id=snapshot.event_id,
            route={'platform':'feishu','profile':'synthetic','chat_id':'PRIVATE_CHAT_SENTINEL'},
            authority_event_id=authority_id, observed_at=now+timedelta(seconds=1), **extra)

    legacy = bind('legacy', authority('legacy'))
    assert legacy.receipt_requirement is ReceiptLevel.EXTERNAL_DELIVERED
    old_payload = journal.get(legacy.event_id).event.payload
    assert old_payload['schema_version'] == 1 and 'receipt_requirement' not in old_payload
    allowed, reasons = host.execution_binding('legacy',subject='user:test',capability='hermes.channel.send')
    assert bool(allowed) == (offered is ReceiptLevel.EXTERNAL_DELIVERED)
    if not allowed: assert reasons == ('host_terminal_receipt_unavailable',)

    for mode in ('missing', 'foreign-snapshot', 'foreign-requirement'):
        extra = {} if mode == 'missing' else {
            'authorizes_host_snapshot_event_id': snapshot.event_id if mode != 'foreign-snapshot' else 'other',
            'authorizes_receipt_requirement': required.value if mode != 'foreign-requirement' else 'other'}
        event_id = authority(mode, **extra)
        require_failure(lambda: bind(mode,event_id,receipt_requirement=required))
        assert host.get_binding(mode) is None
    event_id = authority('new', authorizes_receipt_requirement=required.value,
                         authorizes_host_snapshot_event_id=snapshot.event_id)
    new = bind('new', event_id, receipt_requirement=required)
    assert new.receipt_requirement is required
    payload = _thaw_json(journal.get(new.event_id).event.payload)
    assert payload['schema_version'] == 2 and payload['receipt_requirement'] == required.value
    assert not host.protector.verify_json(host.ROUTE_NAMESPACE,
        {k:v for k,v in payload.items() if k!='binding_authenticator'}, payload['binding_authenticator'])
    levels = tuple(ReceiptLevel)
    allowed, reasons = host.execution_binding('new',subject='user:test',capability='hermes.channel.send')
    assert bool(allowed) == (levels.index(offered) >= levels.index(required))
    assert (host.latest_snapshot().claim('hermes.channel.send').receipt_level is offered)
    if allowed:
        assert host.resolve_route(allowed)['platform'] == 'feishu'
    else:
        assert reasons == (('host_terminal_receipt_unavailable' if
            required is ReceiptLevel.EXTERNAL_DELIVERED else 'host_receipt_requirement_unsatisfied'),)

    # Recovery does not upgrade an old grant or infer a new receipt policy.
    reopened = HostCapabilityProjection(ExperienceJournal(journal.path))
    assert reopened.get_binding('legacy').receipt_requirement is ReceiptLevel.EXTERNAL_DELIVERED
    assert reopened.get_binding('new').receipt_requirement is required
    assert reopened.latest_snapshot().claim('hermes.channel.send').receipt_level is offered
    assert not journal.read(event_type='dispatch.started')
    assert not journal.read(event_type='delivery.succeeded')

    record = journal.get(new.event_id)
    def altered(changes, namespace):
        document = _thaw_json(record.event.payload)
        document.pop('binding_authenticator')
        document.update(changes)
        document['binding_authenticator'] = host.protector.authenticate_json(namespace,document)
        event = EventEnvelope(event_id=record.event.event_id,event_type=record.event.event_type,
            source=record.event.source,actor=record.event.actor,subject=record.event.subject,
            causation_id=record.event.causation_id,observed_at=record.event.observed_at,
            occurred_at=record.event.occurred_at,sensitivity=record.event.sensitivity,payload=document)
        return JournalRecord(record.sequence,event)
    require_failure(lambda: host._parse_binding(altered({'schema_version':1},host.ROUTE_NAMESPACE)))
    require_failure(lambda: host._parse_binding(altered({'schema_version':True},host.ROUTE_NAMESPACE)))
    require_failure(lambda: host._parse_binding(altered({'receipt_requirement':'unknown'},host.ROUTE_V2_NAMESPACE)))
    require_failure(lambda: host._parse_binding(altered({'authority_event_id':'user-authority:missing'},host.ROUTE_V2_NAMESPACE)))
    assert host.execution_binding('new',subject='user:foreign',capability='hermes.channel.send')[0] is None
    host.revoke_route('new')
    assert host.execution_binding('new',subject='user:test',capability='hermes.channel.send')[0] is None
    for path in (journal.path, root/'content-vault/content.sqlite3'):
        assert b'PRIVATE_CHAT_SENTINEL' not in path.read_bytes()


with tempfile.TemporaryDirectory(prefix='alive-submission-policy-') as directory:
    for offered in ReceiptLevel:
        for required in ReceiptLevel:
            test(Path(directory)/(offered.value+'-'+required.value), offered, required)
print('HERMES_ALIVE_HOST_SUBMISSION_CONTRACT_OK')
