#!/usr/bin/env python3
"""Atomic cadence accounting; starts are not delivery or user benefit."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.cognition_context import CognitionContextReader
from alive_kernel.dispatch_outbox import DispatchOutbox, DispatchOutboxError
from alive_kernel.event_store import ExperienceJournal, JournalRecord
from alive_kernel.events import EventEnvelope, Sensitivity


def scenario(root, interval, maximum):
    journal = ExperienceJournal(root / 'journal.sqlite3')
    outbox = DispatchOutbox(journal)
    now = datetime.now(timezone.utc)
    def authorization(operation, owner='user:test'):
        grant = ActionDelegationStore(journal).grant(subject=owner, actor=owner,
            policy_event_id='policy:1', route_binding_id='route:1', action_kinds=('share',),
            maximum_sensitivity=Sensitivity.PRIVATE, expires_at=now + timedelta(days=3),
            operation_id=operation, now=now, minimum_interval_seconds=interval, max_starts_per_24h=maximum,
            allow_natural_expression=True)
        return JournalRecord(grant.sequence, EventEnvelope(event_type='synthetic.authorization', source='synthetic', actor=owner,
            subject=owner, payload={'delegation_event_id':grant.event.event_id,
            'policy_event_id':'policy:1', 'route_binding_id':'route:1',
            'capability':'hermes.channel.send', 'delegated_action_kind':'share'}))
    auth = authorization('grant')
    def start(identity, when, receipt=auth):
        payload = {'dispatch_id':identity, 'lease_generation':1,
                   'delegation_event_id':receipt.event.payload['delegation_event_id'],
                   'cadence_reserved_at':when.isoformat()}
        payload['integrity_authenticator'] = outbox.protector.authenticate_json('dispatch.start.v1', payload)
        event = EventEnvelope(event_id=outbox._start_event_id(identity, 1), event_type='dispatch.started',
            source='alive.dispatch', actor='system:alive-dispatch', subject=receipt.event.subject,
            observed_at=when, occurred_at=when, payload=payload)
        return journal.append(event, precondition=lambda connection:
            outbox._check_delegated_cadence(connection, receipt, when))
    first = start('first', now)
    def eligible(receipt=auth,when=now):
        return outbox.next_delegated_start(receipt.event.payload['delegation_event_id'],
            subject=receipt.event.subject,policy_event_id='policy:1',route_binding_id='route:1',now=when)
    expected=now+timedelta(days=1) if maximum==1 else now+timedelta(seconds=interval)
    assert eligible()==expected
    assert not start('first', now).created
    new_grant = authorization('new-grant')
    assert eligible(new_grant)==expected  # read-only and final accounting agree across renewal
    assert eligible(when=expected)==expected
    try:
        start('blocked', now + timedelta(seconds=1), new_grant)
    except DispatchOutboxError:
        assert journal.get(outbox._start_event_id('blocked', 1)) is None
    else:
        raise AssertionError('fresh grant reset owner cadence')
    assert start('other-owner', now, authorization('other-grant', owner='user:other')).created
    assert start('after-window', now + timedelta(days=1)).created
    assert not journal.read(event_type='delivery.succeeded')

    # Deterministically simulate another worker satisfying the watermark between
    # the loop condition and its progress sample. No missing memory is invented.
    reader = CognitionContextReader(journal)
    assert reader.read(subject='user:test', clearance=Sensitivity.PRIVATE) == ()
    journal.append(EventEnvelope(event_type='synthetic.unrelated', source='synthetic', actor='user:test', subject='user:test'))
    target = journal.last_sequence()
    checkpoint = journal.checkpoint
    calls = 0
    def concurrent_checkpoint(name):
        nonlocal calls
        if name == reader.memory.CHECKPOINT:
            calls += 1
            if calls == 2:
                journal.advance_checkpoint(name, target)
        return checkpoint(name)
    journal.checkpoint = concurrent_checkpoint
    try:
        assert reader.read(subject='user:test', clearance=Sensitivity.PRIVATE) == ()
    finally:
        journal.checkpoint = checkpoint
    journal.append(EventEnvelope(event_type='synthetic.unrelated', source='synthetic', actor='user:test', subject='user:test'))
    project = reader.memory.project_new
    reader.memory.project_new = lambda **kwargs: 0
    try:
        reader.read(subject='user:test', clearance=Sensitivity.PRIVATE)
    except ValueError as exc:
        assert 'made no progress' in str(exc)
    else:
        raise AssertionError('genuinely stalled projection became acceptable')
    finally:
        reader.memory.project_new = project
    watermark = journal.last_sequence()
    journal.advance_checkpoint('synthetic-coalescing', watermark)
    assert journal.advance_checkpoint('synthetic-coalescing', watermark - 1, coalesce=True) == watermark
    assert journal.checkpoint('synthetic-coalescing') == watermark
    try:
        journal.advance_checkpoint('synthetic-coalescing', watermark - 1)
    except ValueError as exc:
        assert 'backwards' in str(exc)
    else:
        raise AssertionError('strict checkpoint backward rejection changed')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-dispatch-cadence-') as directory:
        scenario(Path(directory) / 'quota', 0, 1)
        scenario(Path(directory) / 'interval', 3600, 10)
    print('HERMES_ALIVE_KERNEL_DISPATCH_CADENCE_OK')
