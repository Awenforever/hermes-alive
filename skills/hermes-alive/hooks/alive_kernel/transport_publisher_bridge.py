"""Research bridge for qualified host-owned deferred transport observations.

Does not send, drain/reorder FIFO, acknowledge the dispatch or infer feedback.
Source qualification is operator-owned; SQLite reports are not cryptographic
proof of remote delivery, even when their journal provenance is authenticated.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import inspect
import math
from pathlib import Path
import re

from .dispatch_outbox import DispatchOutboxError
from .event_store import EventConflictError
from .events import EventEnvelope, _thaw_json


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


@dataclass(frozen=True, slots=True)
class QualifiedReceiptPublisher:
    adapter: object = field(repr=False)
    source_digest: str
    profile_id: str
    profile_home: Path = field(repr=False)
    qualified: bool = False

    def validate(self, route):
        store = getattr(self.adapter, '_hermes_transport_receipts_v1', None)
        reader = getattr(store, 'read_receipts', None)
        if (self.qualified is not True or not _digest(self.source_digest)
                or not callable(reader) or route.get('platform') != 'weixin'
                or route.get('profile') != self.profile_id
                or store is not getattr(self.adapter, '_hermes_wechat_v021_pending_queue', None)):
            raise DispatchOutboxError('qualified scoped receipt publisher required')
        filename = inspect.getsourcefile(reader)
        if (filename is None or hashlib.sha256(Path(filename).read_bytes()).hexdigest() != self.source_digest
                or Path(store.path).resolve() != self.profile_home.resolve() / 'plugin-data' / 'hermes-wechat-enhance' / 'send-queue.sqlite3'):
            raise DispatchOutboxError('publisher source or profile differs from qualification')
        return store


class TransportPublisherBridge:
    def __init__(self, outbox):
        self.outbox, self.journal, self.protector = outbox, outbox.journal, outbox.protector

    def _append(self, *, event_id, kind, cause, subject, sensitivity, payload, now):
        payload = dict(payload)
        payload['integrity_authenticator'] = self.protector.authenticate_json(kind + '.v1', payload)
        existing = self.journal.get(event_id)
        if existing is not None:
            if (existing.event.event_type != kind or existing.event.source != 'alive.transport.publisher'
                    or existing.event.actor != 'system:alive-transport' or existing.event.subject != subject
                    or existing.event.sensitivity != sensitivity or existing.event.causation_id != cause
                    or _thaw_json(existing.event.payload) != payload):
                raise EventConflictError('transport occurrence differs from canonical evidence')
            return existing
        return self.journal.append(EventEnvelope(event_id=event_id, event_type=kind,
            source='alive.transport.publisher', actor='system:alive-transport', subject=subject,
            sensitivity=sensitivity, causation_id=cause, occurred_at=now, observed_at=now, payload=payload))

    def bind(self, execution, publisher, *, now=None):
        """Bind an already-started/live launch; never grant another send."""
        current = self.outbox._utc(now)
        self.outbox.validate_execution_for_launch(execution, now=current)
        lease = self.outbox._channel_observation_owner(execution, current)
        publisher.validate(execution.route)
        payload = {'dispatch_id':lease.dispatch_id, 'attempt_id':lease.attempt_id,
            'start_event_id':execution.start_event_id, 'publisher_source_digest':publisher.source_digest,
            'subject':lease.subject, 'sensitivity':lease.sensitivity.value,
            'account_reference':self.protector.authenticate_json('transport.publisher.account.v1', str(publisher.adapter._account_id)),
            'route_reference':self.protector.authenticate_json('transport.publisher.route.v1', execution.route),
            'lease_generation':lease.generation, 'delivery_authority_granted':False}
        payload['transport_binding'] = self.protector.authenticate_json('transport.publisher.binding.v1', payload)
        return self._append(event_id=execution.start_event_id + ':publisher-binding',
            kind='transport.publisher.bound', cause=execution.start_event_id, subject=lease.subject,
            sensitivity=lease.sensitivity, payload=payload, now=current)

    def ingest(self, binding_event_id, *, publisher, route, after_sequence=0, limit=128, now=None):
        """Read bounded reports under a historical binding, including late ACKs.

        Does not require a still-live send lease and never updates dispatch state.
        Never interpret an empty page as absence of effects or completed delivery.
        """
        current = self.outbox._utc(now)
        record = self.journal.get(binding_event_id)
        if record is None:
            raise DispatchOutboxError('canonical publisher binding required')
        event = record.event
        payload = _thaw_json(event.payload)
        signature = payload.pop('integrity_authenticator', None)
        if (event.event_type != 'transport.publisher.bound' or event.source != 'alive.transport.publisher'
                or event.actor != 'system:alive-transport'
                or event.event_id != payload.get('start_event_id', '') + ':publisher-binding'
                or event.causation_id != payload.get('start_event_id')
                or event.subject != payload.get('subject') or event.sensitivity.value != payload.get('sensitivity')
                or not self.protector.verify_json('transport.publisher.bound.v1', payload, signature)
                or payload.get('publisher_source_digest') != publisher.source_digest
                or payload.get('route_reference') != self.protector.authenticate_json('transport.publisher.route.v1', route)
                or payload.get('account_reference') != self.protector.authenticate_json('transport.publisher.account.v1', str(publisher.adapter._account_id))
                or current < event.observed_at):
            raise DispatchOutboxError('publisher binding provenance or scope mismatch')
        store = publisher.validate(route)
        if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= 1024:
            raise DispatchOutboxError('bounded receipt page required')
        page = store.read_receipts(str(publisher.adapter._account_id), route['chat_id'],
            payload['transport_binding'], after_sequence=after_sequence, limit=limit)
        if (page.get('version') != 1 or type(page.get('available')) is not bool
                or any(page.get(key) is not False for key in ('complete_inventory_proven',
                    'external_delivery_proven','canonical_quote_mapping_proven'))
                or not isinstance(page.get('records'), list) or len(page['records']) > limit):
            raise DispatchOutboxError('publisher report exceeds its evidence contract')
        checked, previous = [], after_sequence
        for row in page['records']:
            if (set(row) != {'seq','occurrence_id','client_reference','phase','observed_at'}
                    or type(row['seq']) is not int or row['seq'] <= previous
                    or not _digest(row['occurrence_id']) or not _digest(row['client_reference'])
                    or row['phase'] not in ('queued','acknowledged')
                    or type(row['observed_at']) not in (int,float) or not math.isfinite(row['observed_at'])
                    or not event.observed_at.timestamp() <= row['observed_at'] <= current.timestamp()
                    or row['occurrence_id'] != hashlib.sha256((row['client_reference'] + ':' + row['phase']).encode()).hexdigest()):
                raise DispatchOutboxError('invalid or unscoped transport occurrence')
            checked.append(row)
            previous = row['seq']
        # Validate the whole page before writing; append replay is idempotent.
        results = []
        for row in checked:
            observation = {'binding_event_id':binding_event_id,
                'dispatch_id':payload['dispatch_id'], 'attempt_id':payload['attempt_id'],
                'start_event_id':payload['start_event_id'], 'publisher_source_digest':publisher.source_digest,
                'publisher_sequence':row['seq'], 'publisher_occurrence':row['occurrence_id'],
                'client_reference':row['client_reference'], 'phase':row['phase'],
                'reported_at':row['observed_at'], 'evidence_scope':'host_sqlite_report',
                'external_delivery_proven':False, 'complete_inventory_proven':False,
                'canonical_quote_target_proven':False, 'delivery_authority_granted':False}
            identity = self.protector.authenticate_json('transport.publisher.occurrence.v1',
                {'binding_event_id':binding_event_id,'occurrence':row['occurrence_id']})
            results.append(self._append(event_id='transport-observation:' + identity,
                kind='transport.publisher.observed', cause=binding_event_id, subject=event.subject,
                sensitivity=event.sensitivity, payload=observation, now=current))
        return {'records':tuple(results), 'next_sequence':previous,
            'available':page['available'], 'coverage_uncertain':True,
            'complete_inventory_proven':False, 'external_delivery_proven':False}
