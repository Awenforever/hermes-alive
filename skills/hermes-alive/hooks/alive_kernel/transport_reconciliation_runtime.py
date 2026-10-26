"""One bounded host-invoked reconciliation tick; never sends or owns FIFO.

Host supplies authenticated owner and qualified publisher/route resolver. Cursor
wrap deliberately revisits unresolved bindings; no receipt proves final delivery.
No timer, automatic production activation or unbounded retry is installed here.
"""
from contextlib import closing
import asyncio
import inspect

from .dispatch_outbox import DispatchOutboxError
from .events import _thaw_json
from .transport_publisher_consumer import TransportPublisherConsumer


class TransportReconciliationRuntime:
    def __init__(self,outbox):
        self.outbox,self.journal = outbox,outbox.journal
        self.consumer = TransportPublisherConsumer(outbox)
        self.bridge = self.consumer.bridge

    def _owner_policy(self,subject):
        return self.canonical_owner_policy(self.outbox.autonomy,self.journal,subject)

    @staticmethod
    def canonical_owner_policy(autonomy,journal,subject):
        policy = autonomy.current(subject)
        record = journal.get(policy.event_id) if policy else None
        payload = _thaw_json(record.event.payload) if record else {}
        signature = payload.pop('integrity_authenticator',None)
        if (policy is None or record is None or record.event.event_type != 'autonomy.policy_changed'
                or record.event.source != 'hermes.command.alive' or record.event.actor != subject
                or record.event.subject != subject or record.event.sensitivity.value != 'private'
                or payload.get('enabled') is not policy.enabled or payload.get('revision') != policy.revision
                or not autonomy.protector.verify_json('autonomy.policy.v1',payload,signature)):
            raise DispatchOutboxError('canonical owner policy unavailable')
        for candidate in journal.iter_reverse(event_types=('autonomy.policy_changed',),subject=subject,max_records=1000):
            if candidate.event.event_id == policy.event_id:
                return policy
            later = _thaw_json(candidate.event.payload)
            signature = later.pop('integrity_authenticator',None)
            if (candidate.event.actor == subject and candidate.event.subject == subject
                    and candidate.event.source == 'hermes.command.alive'
                    and candidate.event.sensitivity.value == 'private'
                    and autonomy.protector.verify_json('autonomy.policy.v1',later,signature)):
                raise DispatchOutboxError('newer owner command needs policy reconciliation')
        raise DispatchOutboxError('bounded owner policy history unavailable')

    async def tick(self,*,subject,resolve_binding,after_sequence=0,binding_limit=16,receipt_limit=128,
            operation_timeout=10.0,now=None):
        if (not isinstance(subject,str) or not subject or not callable(resolve_binding)
                or type(after_sequence) is not int or after_sequence < 0
                or type(binding_limit) is not int or not 1 <= binding_limit <= 128
                or type(receipt_limit) is not int or not 1 <= receipt_limit <= 1024
                or type(operation_timeout) not in (int,float) or not 0 < operation_timeout <= 60):
            raise ValueError('bounded owner reconciliation contract required')
        current = self.outbox._utc(now)
        with closing(self.journal._connect()) as connection:
            rows = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE subject=? AND event_type=? AND sequence>? ORDER BY sequence LIMIT ?',
                (subject,'transport.publisher.bound',after_sequence,binding_limit+1)).fetchall()
        selected = rows[:binding_limit]
        counts = {'observed':0,'withdrawal_requests':0,'failed_bindings':0}
        failures = []
        through = after_sequence
        for row in selected:
            stage = 'binding_provenance'
            # Corruption and resolver/storage failures isolate one binding. Task
            # cancellation/BaseException still escape rather than becoming retry.
            try:
                record = self.journal._record(row)
                event = record.event
                payload = _thaw_json(event.payload)
                signature = payload.pop('integrity_authenticator',None)
                if (event.event_type != 'transport.publisher.bound' or event.subject != subject
                        or event.source != 'alive.transport.publisher' or event.actor != 'system:alive-transport'
                        or payload.get('subject') != subject or payload.get('sensitivity') != event.sensitivity.value
                        or event.event_id != payload.get('start_event_id','') + ':publisher-binding'
                        or event.causation_id != payload.get('start_event_id') or current < event.observed_at
                        or not self.outbox.protector.verify_json('transport.publisher.bound.v1',payload,signature)):
                    raise DispatchOutboxError('owner binding provenance mismatch')
                stage = 'owner_policy'
                policy = self._owner_policy(subject)
                stage = 'publisher_resolution'
                resolved = resolve_binding(record)
                if inspect.isawaitable(resolved):
                    resolved = await asyncio.wait_for(resolved,timeout=operation_timeout)
                publisher,route = resolved
                stage = 'owner_policy'
                policy = self._owner_policy(subject)
                if not policy.enabled:
                    stage = 'withdrawal'
                    await asyncio.wait_for(self.bridge.withdraw_paused(event.event_id,publisher=publisher,route=route,now=now),timeout=operation_timeout)
                    counts['withdrawal_requests'] += 1
                stage = 'observation'
                page = self.consumer.poll_once(event.event_id,publisher=publisher,route=route,limit=receipt_limit,now=now)
                counts['observed'] += len(page['records'])
            except Exception:
                counts['failed_bindings'] += 1  # do not retain private errors
                failures.append({'reference':self.outbox.protector.authenticate_json('transport.reconciliation.failure.v1',
                    {'subject':subject,'journal_sequence':int(row['sequence'])}),'stage':stage})
            through = int(row['sequence'])
        return {**counts,'failures':tuple(failures),'scanned':len(selected),'through_sequence':through,
            'next_after_sequence':through if len(rows)>binding_limit else 0,
            'wrap_required':len(rows)<=binding_limit,'coverage_uncertain':True,
            'external_delivery_proven':False,'complete_inventory_proven':False}
