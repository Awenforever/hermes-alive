#!/usr/bin/env python3
"""Completed interpretation recovery, identity stability and stale evidence."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (
    ActionAuthority, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    EventEnvelope, ExperienceJournal, MemoryAuthority, MemoryKind, MemoryProjection,
    MemoryProposal, OpportunitySynthesizer, OpportunitySynthesisError, Sensitivity,
)


def refused(call):
    try:
        call()
    except OpportunitySynthesisError:
        return
    raise AssertionError('invalid recovery was admitted')


async def exercise(root):
    journal = ExperienceJournal(root/'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    discovery = reader.ingest(DiscoveryCandidate(source='synthetic', title='PRIVATE_TITLE',
        summary='PRIVATE_SOURCE_BODY', url='https://example.invalid/recovery',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    memory = MemoryProjection(journal)
    event = EventEnvelope(event_type='conversation.inbound', actor='user:test', subject='user:test',
                          source='synthetic', payload={'fixture': True})
    journal.append(event)
    preference = MemoryProposal(kind=MemoryKind.PREFERENCE, subject='user:test', predicate='profile.interest',
        value='PRIVATE_CONTEXT', authority=MemoryAuthority.USER_EXPLICIT, source_event_ids=(event.event_id,), confidence=1)
    memory.append_proposal(preference, actor='user:test')
    calls = []

    async def generate(**kw):
        calls.append(kw)
        good = {'agenda_item_id': discovery.agenda_item_id, 'kind': 'share', 'text': 'PRIVATE_DRAFT',
                'topic': 'topic', 'dimensions': {n: {'value': .1 if n in ('risk', 'interruption_cost') else .8,
                    'reason': 'model judgment'} for n in ('user_value','urgency','novelty','confidence','interruption_cost','risk')}}
        return SimpleNamespace(model='actual/recovery-model', choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'candidates': [{'invalid': 'first'}, good]})))])

    synthesizer = OpportunitySynthesizer(journal)
    original = await synthesizer.run(subject='user:test', operation_id='partial', call=generate,
                                     authority=ActionAuthority.USER_DELEGATED)
    assert original.rejected_count == 1 and len(original.candidates) == 1
    before = journal.last_sequence()
    reopened = OpportunitySynthesizer(ExperienceJournal(root/'experience.sqlite3'))
    loaded = reopened.load_completed(subject='user:test', operation_id='partial')
    assert loaded.candidates[0].action.authority is ActionAuthority.NONE
    assert loaded.candidates[0].action.candidate_id == original.candidates[0].action.candidate_id
    assert loaded.candidates[0].action.content_id == original.candidates[0].action.content_id
    assert loaded.actual_model == original.actual_model and loaded.receipt_event_id == original.receipt_event_id
    assert loaded.rejected_count == 1
    delegated = reopened.load_completed(subject='user:test', operation_id='partial', authority=ActionAuthority.USER_DELEGATED)
    assert delegated == original
    assert journal.last_sequence() == before and len(calls) == 1
    for index in range(12):
        reader.ingest(DiscoveryCandidate(source='synthetic', title='Unrelated ' + str(index),
            summary='unrelated arrival', url='https://example.invalid/new/' + str(index),
            observed_at=datetime.now(timezone.utc)), subject='user:test')
    before = journal.last_sequence()
    assert reopened.load_completed(subject='user:test', operation_id='partial',
        authority=ActionAuthority.USER_DELEGATED) == original
    assert journal.last_sequence() == before and len(calls) == 1
    refused(lambda: reopened.load_completed(subject='user:other', operation_id='partial'))
    refused(lambda: reopened.load_completed(subject='user:test', operation_id='partial', clearance=Sensitivity.PUBLIC))
    refused(lambda: reopened.load_completed(subject='user:test', operation_id='partial', authority=ActionAuthority.SYSTEM_CRITICAL))
    refused(lambda: reopened.load_completed(subject='user:test', operation_id='not-completed'))
    # Erasure of an accepted bundle cannot be repaired by recovery or model spend.
    erased = await synthesizer.run(subject='user:test', operation_id='erased', call=generate)
    reader.vault.erase_item('opportunity-proposals:erased')
    refused(lambda: reopened.load_completed(subject='user:test', operation_id='erased'))
    # A context withdrawal invalidates a previously completed draft, not just an
    # in-flight provider response. It remains inspectable only as historical facts.
    memory.forget_item(preference.proposal_id, actor='user:test', request_id='recovery-forget')
    refused(lambda: reopened.load_completed(subject='user:test', operation_id='partial'))
    assert len(calls) == 2 and not journal.read(event_type='action.attempted')
    for path in root.glob('experience.sqlite3*'):
        data = path.read_bytes()
        assert b'PRIVATE_CONTEXT' not in data and b'PRIVATE_DRAFT' not in data


with tempfile.TemporaryDirectory(prefix='alive-opportunity-recovery-') as folder:
    asyncio.run(exercise(Path(folder)))
print('HERMES_ALIVE_KERNEL_OPPORTUNITY_RECOVERY_OK')
