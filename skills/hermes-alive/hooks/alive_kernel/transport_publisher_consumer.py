"""Durable bounded observation consumer, not a delivery queue or sender.

Progress advances only after canonical observations exist; interruptions replay
those same observations. No scheduler/background task is installed here.
"""
from contextlib import closing
from dataclasses import dataclass

from .dispatch_outbox import DispatchOutboxError
from .events import _thaw_json
from .transport_publisher_bridge import TransportPublisherBridge


@dataclass(frozen=True, slots=True)
class PublisherConsumerProgress:
    through_sequence: int = 0
    checkpoint_event_id: str | None = None
    coverage_uncertain: bool = True


class TransportPublisherConsumer:
    def __init__(self, outbox):
        self.bridge = TransportPublisherBridge(outbox)
        self.journal, self.protector = outbox.journal, outbox.protector

    def _head(self, connection, binding):
        row = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_type=? AND causation_id=? ORDER BY sequence DESC LIMIT 1',
            ('transport.publisher.checkpoint',binding.event.event_id)).fetchone()
        if row is None:
            return PublisherConsumerProgress()
        event = self.journal._record(row).event
        payload = _thaw_json(event.payload)
        signature = payload.pop('integrity_authenticator',None)
        if (event.event_type != 'transport.publisher.checkpoint' or event.causation_id != binding.event.event_id
                or event.source != 'alive.transport.publisher' or event.actor != 'system:alive-transport'
                or event.subject != binding.event.subject or event.sensitivity != binding.event.sensitivity
                or payload.get('binding_event_id') != binding.event.event_id
                or not self.protector.verify_json('transport.publisher.checkpoint.v1',payload,signature)
                or type(payload.get('after_sequence')) is not int or payload['after_sequence'] < 0
                or type(payload.get('through_sequence')) is not int or payload['through_sequence'] <= payload['after_sequence']
                or payload.get('coverage_uncertain') is not True or payload.get('external_delivery_proven') is not False
                or payload.get('complete_inventory_proven') is not False
                or not isinstance(payload.get('observation_event_ids'),list)
                or not 1 <= len(payload['observation_event_ids']) <= 1024):
            raise DispatchOutboxError('consumer checkpoint is not canonical scoped progress')
        expected_id = 'transport-checkpoint:' + self.protector.authenticate_json('transport.publisher.checkpoint.identity.v1',payload)
        if event.event_id != expected_id:
            raise DispatchOutboxError('consumer checkpoint identity mismatch')
        previous = payload['after_sequence']
        for observation_id in payload['observation_event_ids']:
            observation_row = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_id=?',(observation_id,)).fetchone()
            if observation_row is None:
                raise DispatchOutboxError('checkpoint references missing observation')
            observation = self.journal._record(observation_row).event
            item = _thaw_json(observation.payload)
            authenticator = item.pop('integrity_authenticator',None)
            if (observation.event_type != 'transport.publisher.observed'
                    or observation.source != 'alive.transport.publisher' or observation.actor != 'system:alive-transport'
                    or observation.subject != binding.event.subject or observation.sensitivity != binding.event.sensitivity
                    or observation.causation_id != binding.event.event_id
                    or item.get('binding_event_id') != binding.event.event_id
                    or item.get('publisher_source_digest') != binding.event.payload['publisher_source_digest']
                    or item.get('publisher_epoch') != binding.event.payload['publisher_epoch']
                    or any(item.get(key) is not False for key in ('external_delivery_proven',
                        'complete_inventory_proven','canonical_quote_target_proven','delivery_authority_granted'))
                    or not self.protector.verify_json('transport.publisher.observed.v1',item,authenticator)
                    or type(item.get('publisher_sequence')) is not int or item['publisher_sequence'] <= previous):
                raise DispatchOutboxError('checkpoint observation scope or ordering mismatch')
            previous = item['publisher_sequence']
        if previous != payload['through_sequence']:
            raise DispatchOutboxError('checkpoint exceeds persisted observations')
        return PublisherConsumerProgress(previous,event.event_id)

    def progress(self, binding_event_id, *, publisher, route, now=None):
        current = self.bridge.outbox._utc(now)
        binding, _, _ = self.bridge._qualified_binding(binding_event_id,publisher,route,current)
        with closing(self.journal._connect()) as connection:
            return self._head(connection,binding)

    def poll_once(self, binding_event_id, *, publisher, route, limit=128, now=None):
        """One bounded read; durable progress is not delivery completion."""
        current = self.bridge.outbox._utc(now)
        binding, _, _ = self.bridge._qualified_binding(binding_event_id,publisher,route,current)
        with closing(self.journal._connect()) as connection:
            prior = self._head(connection,binding)
        page = self.bridge.ingest(binding_event_id,publisher=publisher,route=route,
            after_sequence=prior.through_sequence,limit=limit,now=current)
        if not page['records'] or page['available'] is not True:
            return {**page,'progress':prior,'progress_advanced':False}
        payload = {'binding_event_id':binding_event_id,'previous_checkpoint_id':prior.checkpoint_event_id,
            'after_sequence':prior.through_sequence,'through_sequence':page['next_sequence'],
            'observation_event_ids':[record.event.event_id for record in page['records']],
            'coverage_uncertain':True,'complete_inventory_proven':False,'external_delivery_proven':False}
        event_id = 'transport-checkpoint:' + self.protector.authenticate_json('transport.publisher.checkpoint.identity.v1',payload)
        def unchanged(connection):
            if self._head(connection,binding) != prior:
                raise DispatchOutboxError('consumer progress changed; reread without sending')
        checkpoint = self.bridge._append(event_id=event_id,kind='transport.publisher.checkpoint',
            cause=binding_event_id,subject=binding.event.subject,sensitivity=binding.event.sensitivity,
            payload=payload,now=current,precondition=unchanged)
        return {**page,'progress':PublisherConsumerProgress(page['next_sequence'],checkpoint.event.event_id),
            'progress_advanced':True}
