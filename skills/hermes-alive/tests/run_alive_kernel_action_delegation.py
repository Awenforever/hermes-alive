#!/usr/bin/env python3
"""Synthetic bounded permission; no real gateway or transport qualification."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.action_delegation import ActionDelegationStore, ActionDelegationError
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.events import EventEnvelope, Sensitivity, _thaw_json


def main(root):
    journal = ExperienceJournal(root / 'journal.sqlite3')
    store = ActionDelegationStore(journal)
    now = datetime.now(timezone.utc)
    record = store.grant(subject='user:test', actor='user:test', policy_event_id='policy:1',
        route_binding_id='route:1', action_kinds=('share',), maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=now + timedelta(hours=1), operation_id='grant', now=now)
    expected = dict(subject='user:test', policy_event_id='policy:1', route_binding_id='route:1',
                    capability='hermes.channel.send', action_kind='share', sensitivity=Sensitivity.PRIVATE, now=now)
    assert store.permits(record.event.event_id, **expected)
    for change in ({'subject':'user:other'}, {'policy_event_id':'policy:2'},
                   {'route_binding_id':'route:2'}, {'action_kind':'ask'},
                   {'sensitivity':Sensitivity.RESTRICTED}, {'capability':'hermes.tool.execute'},
                   {'now':now + timedelta(hours=1)}, {'now':now - timedelta(seconds=1)}):
        assert not store.permits(record.event.event_id, **{**expected, **change})
    altered = _thaw_json(record.event.payload)
    altered['operation_id'] = 'forged'
    altered['action_kinds'] = ['share', 'ask']
    forged = journal.append(EventEnvelope(event_id='action.delegation:forged',
        event_type='action.delegation_granted', source='hermes.command.alive', actor='user:test',
        subject='user:test', sensitivity=Sensitivity.PRIVATE, observed_at=now, occurred_at=now,
        expires_at=now + timedelta(hours=1), payload=altered))
    assert not store.permits(forged.event.event_id, **{**expected, 'action_kind':'ask'})
    try:
        store.revoke(delegation_event_id=record.event.event_id, subject='user:other', actor='user:other')
    except ActionDelegationError:
        pass
    else:
        raise AssertionError('foreign owner revoked delegation')
    try:
        store.grant(subject='user:test', actor='user:other', policy_event_id='policy:1',
            route_binding_id='route:1', action_kinds=('share',), maximum_sensitivity=Sensitivity.PRIVATE,
            expires_at=now + timedelta(hours=1), operation_id='foreign', now=now)
    except ActionDelegationError:
        pass
    else:
        raise AssertionError('foreign actor created delegation')
    store.revoke(delegation_event_id=record.event.event_id, subject='user:test', actor='user:test')
    assert not store.permits(record.event.event_id, **expected)
    retained = journal.get(record.event.event_id)
    assert retained.sequence == record.sequence
    assert retained.event.canonical_json() == record.event.canonical_json()


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-action-delegation-') as directory:
        main(Path(directory))
    print('HERMES_ALIVE_KERNEL_ACTION_DELEGATION_OK')
