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

    def _append(self, *, event_id, kind, cause, subject, sensitivity, payload, now, precondition=None):
        payload = dict(payload)
        payload['integrity_authenticator'] = self.protector.authenticate_json(kind + '.v1', payload)
        def factory(connection):
            row = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_id=?',(event_id,)).fetchone()
            if row is not None:
                existing = self.journal._record(row)
                if (existing.event.event_type != kind or existing.event.source != 'alive.transport.publisher'
                        or existing.event.actor != 'system:alive-transport' or existing.event.subject != subject
                        or existing.event.sensitivity != sensitivity or existing.event.causation_id != cause
                        or _thaw_json(existing.event.payload) != payload):
                    raise EventConflictError('transport occurrence differs from canonical evidence')
                return existing.event
            return EventEnvelope(event_id=event_id,event_type=kind,
                source='alive.transport.publisher',actor='system:alive-transport',subject=subject,
                sensitivity=sensitivity,causation_id=cause,occurred_at=now,observed_at=now,payload=payload)
        return self.journal.append(factory,precondition=precondition)

    def bind(self, execution, publisher, *, now=None):
        """Bind an already-started/live launch; never grant another send."""
        current = self.outbox._utc(now)
        self.outbox.validate_execution_for_launch(execution, now=current)
        lease = self.outbox._channel_observation_owner(execution, current)
        publisher.validate(execution.route)
        epoch = publisher.adapter._hermes_transport_receipts_v1.publisher_epoch
        if not _digest(epoch):
            raise DispatchOutboxError('qualified publisher ledger epoch required')
        payload = {'dispatch_id':lease.dispatch_id, 'attempt_id':lease.attempt_id,
            'start_event_id':execution.start_event_id, 'publisher_source_digest':publisher.source_digest,
            'publisher_epoch':epoch,
            'subject':lease.subject, 'sensitivity':lease.sensitivity.value,
            'account_reference':self.protector.authenticate_json('transport.publisher.account.v1', str(publisher.adapter._account_id)),
            'route_reference':self.protector.authenticate_json('transport.publisher.route.v1', execution.route),
            'lease_generation':lease.generation, 'delivery_authority_granted':False}
        payload['transport_binding'] = self.protector.authenticate_json('transport.publisher.binding.v1', payload)
        return self._append(event_id=execution.start_event_id + ':publisher-binding',
            kind='transport.publisher.bound', cause=execution.start_event_id, subject=lease.subject,
            sensitivity=lease.sensitivity, payload=payload, now=current)

    def _qualified_binding(self, binding_event_id, publisher, route, current):
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
        if not _digest(payload.get('publisher_epoch')) or payload['publisher_epoch'] != store.publisher_epoch:
            raise DispatchOutboxError('publisher ledger epoch changed; explicit reconciliation required')
        return record, payload, store

    def ingest(self, binding_event_id, *, publisher, route, after_sequence=0, limit=128, now=None):
        """Read bounded reports under a historical binding, including late ACKs.

        Does not require a still-live send lease and never updates dispatch state.
        Never interpret an empty page as absence of effects or completed delivery.
        """
        current = self.outbox._utc(now)
        record, payload, store = self._qualified_binding(binding_event_id,publisher,route,current)
        event = record.event
        if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= 1024:
            raise DispatchOutboxError('bounded receipt page required')
        page = store.read_receipts(str(publisher.adapter._account_id), route['chat_id'],
            payload['transport_binding'], after_sequence=after_sequence, limit=limit)
        if (page.get('version') != 1 or type(page.get('available')) is not bool
                or page.get('publisher_epoch') != payload['publisher_epoch']
                or type(page.get('high_water_sequence')) is not int
                or page['high_water_sequence'] < after_sequence
                or any(page.get(key) is not False for key in ('complete_inventory_proven',
                    'external_delivery_proven','canonical_quote_mapping_proven'))
                or not isinstance(page.get('records'), list) or len(page['records']) > limit):
            raise DispatchOutboxError('publisher report exceeds its evidence contract')
        checked, previous = [], after_sequence
        for row in page['records']:
            if (set(row) != {'seq','occurrence_id','client_reference','phase','observed_at'}
                    or type(row['seq']) is not int or row['seq'] <= previous
                    or row['seq'] > page['high_water_sequence']
                    or not _digest(row['occurrence_id']) or not _digest(row['client_reference'])
                    or row['phase'] not in ('queued','acknowledged','withdrawn')
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
                'publisher_epoch':payload['publisher_epoch'],
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

    async def withdraw_paused(self,binding_event_id,*,publisher,route,now=None):
        """Withdraw only this user's explicitly paused, historically bound work.

        This asks the host; never edits FIFO or promises recall of in-flight IO.
        No implicit pause can be inferred from model prose, silence or availability.
        """
        current = self.outbox._utc(now)
        binding,payload,_ = self._qualified_binding(binding_event_id,publisher,route,current)
        policy = self.outbox.autonomy.current(binding.event.subject)
        if policy is None or policy.enabled or policy.updated_at < binding.event.observed_at:
            raise DispatchOutboxError('explicit current owner pause required for withdrawal')
        policy_record = self.journal.get(policy.event_id)
        policy_payload = _thaw_json(policy_record.event.payload) if policy_record else {}
        policy_signature = policy_payload.pop('integrity_authenticator',None)
        if (policy_record is None or policy_record.event.event_type != 'autonomy.policy_changed'
                or policy_record.event.source != 'hermes.command.alive'
                or policy_record.event.actor != binding.event.subject or policy_record.event.subject != binding.event.subject
                or policy_record.event.observed_at < binding.event.observed_at
                or policy_record.event.sensitivity.value != 'private'
                or policy_payload.get('enabled') is not False or policy_payload.get('revision') != policy.revision
                or not self.outbox.autonomy.protector.verify_json('autonomy.policy.v1',policy_payload,policy_signature)):
            raise DispatchOutboxError('pause projection lacks canonical owner authority')
        found_current = False
        for candidate in self.journal.iter_reverse(event_types=('autonomy.policy_changed',),
                subject=binding.event.subject,max_records=1000):
            if candidate.event.event_id == policy.event_id:
                found_current = True
                break
            later_payload = _thaw_json(candidate.event.payload)
            later_signature = later_payload.pop('integrity_authenticator',None)
            if (candidate.event.source == 'hermes.command.alive'
                    and candidate.event.actor == binding.event.subject
                    and candidate.event.subject == binding.event.subject
                    and candidate.event.sensitivity.value == 'private'
                    and self.outbox.autonomy.protector.verify_json('autonomy.policy.v1',later_payload,later_signature)):
                raise DispatchOutboxError('newer owner policy command requires current-state reconciliation')
        if not found_current:
            raise DispatchOutboxError('bounded canonical pause history unavailable')
        cancel = getattr(publisher.adapter,'_hermes_transport_withdraw_binding_v1',None)
        filename = inspect.getsourcefile(cancel) if callable(cancel) else None
        if filename is None or hashlib.sha256(Path(filename).read_bytes()).hexdigest() != publisher.source_digest:
            raise DispatchOutboxError('qualified host withdrawal interface required')
        request_payload = {'binding_event_id':binding_event_id,'policy_event_id':policy.event_id,
            'publisher_epoch':payload['publisher_epoch'],'delivery_authority_granted':False}
        identity = self.protector.authenticate_json('transport.publisher.withdrawal.identity.v1',request_payload)
        request = self._append(event_id='transport-withdrawal:'+identity,
            kind='transport.publisher.withdrawal_requested',cause=binding_event_id,
            subject=binding.event.subject,sensitivity=binding.event.sensitivity,payload=request_payload,now=current)
        result_id = request.event.event_id + ':result'
        existing = self.journal.get(result_id)
        if existing is not None:
            existing_payload = _thaw_json(existing.event.payload)
            signature = existing_payload.pop('integrity_authenticator',None)
            if (not self.protector.verify_json('transport.publisher.withdrawal_reported.v1',existing_payload,signature)
                    or any(existing_payload.get(key) != value for key,value in request_payload.items())
                    or any(existing_payload.get(key) is not False for key in ('external_delivery_proven','complete_inventory_proven','external_recall_proven'))):
                raise DispatchOutboxError('withdrawal replay differs from canonical request')
            # A prior report is history, not proof that a restored host database
            # still carries its deny. Reassert the idempotent host request; never
            # infer recall or add another send from this recovery.
            await cancel(route['chat_id'],payload['transport_binding'])
            return self._append(event_id=result_id,kind='transport.publisher.withdrawal_reported',
                cause=request.event.event_id,subject=binding.event.subject,sensitivity=binding.event.sensitivity,
                payload=existing_payload,now=current)
        result = await cancel(route['chat_id'],payload['transport_binding'])
        if (set(result) != {'removed_count','observation_available','already_sent_possible','external_recall_proven'}
                or type(result['removed_count']) is not int or not 0 <= result['removed_count'] <= 500
                or type(result['observation_available']) is not bool
                or result['already_sent_possible'] is not True or result['external_recall_proven'] is not False):
            raise DispatchOutboxError('withdrawal report exceeds qualified contract')
        return self._append(event_id=result_id,kind='transport.publisher.withdrawal_reported',
            cause=request.event.event_id,subject=binding.event.subject,sensitivity=binding.event.sensitivity,
            payload={**result,**request_payload,'external_delivery_proven':False,'complete_inventory_proven':False},
            now=self.outbox._utc(now))
