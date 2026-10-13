#!/usr/bin/env python3
"""Interpretation evidence must stay valid throughout later model selection."""
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (
    ActionAuthority, ActionKind, CognitionCycleCoordinator, CycleCandidate, DiscoveryCandidate,
    DiscoveryOpportunityIngestor, EventEnvelope, ExperienceJournal, MemoryAuthority,
    MemoryKind, MemoryProjection, MemoryProposal, OpportunitySynthesizer, PolicyContext,
)
from alive_kernel.deliberation_synthesis import DeliberationContextChanged
from alive_kernel.events import _thaw_json


def response(value):
    return SimpleNamespace(model='actual/epoch-model', choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value)))])


async def scenario(root, mode):
    journal = ExperienceJournal(root/'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic', title='Fixture', summary='original',
        url='https://example.invalid/item', observed_at=datetime.now(timezone.utc)), subject='user:test')
    memory = MemoryProjection(journal)
    statement = EventEnvelope(event_type='conversation.inbound', source='synthetic', actor='user:test',
                               subject='user:test', payload={'fixture': True})
    journal.append(statement)
    preference = MemoryProposal(kind=MemoryKind.PREFERENCE, subject='user:test', predicate='profile.interest',
        value='PRIVATE_INTEREST', authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(statement.event_id,), confidence=1)
    memory.append_proposal(preference, actor='user:test')

    async def generate(**kw):
        return response({'candidates': [{'agenda_item_id': source.agenda_item_id, 'kind': 'share',
            'text': 'PRIVATE_DRAFT', 'topic': 'fixture', 'dimensions': {
                n: {'value': .1 if n in ('risk','interruption_cost') else .9, 'reason': 'synthetic judgment'}
                for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]})
    draft = await OpportunitySynthesizer(journal).run(subject='user:test', operation_id='generate',
        call=generate, authority=ActionAuthority.USER_DELEGATED)
    calls = []

    def withdraw():
        memory.forget_item(preference.proposal_id, actor='user:test', request_id='withdraw')

    if mode == 'before-call':
        withdraw()
    candidates = draft.candidates
    owner = 'user:test'
    if mode == 'relabeled':
        original = candidates[0]
        candidates = (CycleCandidate(replace(original.action, candidate_id='renamed-candidate'),
            _thaw_json(original.content), original.topic, original.source_label),)
    elif mode == 'foreign-owner':
        owner = 'user:other'

    async def choose(**kw):
        calls.append(kw)
        if mode in ('withdrawal', 'retry-withdrawal'):
            withdraw()
        elif mode == 'source-erasure':
            content_id = journal.get(source.observation_event_id).event.payload['content']['content_id']
            reader.vault.erase_item(content_id)
        elif mode == 'supersession':
            reader.ingest(DiscoveryCandidate(source='synthetic', title='Fixture', summary='updated',
                url='https://example.invalid/item', observed_at=datetime.now(timezone.utc)), subject='user:test')
        if mode == 'retry-withdrawal':
            raise RuntimeError('synthetic provider error after withdrawal')
        return response({'candidate_id': draft.candidates[0].action.candidate_id, 'rationale': 'fixture choice'})

    try:
        chosen = await CognitionCycleCoordinator(journal).plan_with_model(cycle_id='cycle', subject=owner,
            candidates=candidates, policy_context=PolicyContext(can_interrupt=True),
            causation_id=draft.receipt_event_id, call=choose, attempts=2)
    except DeliberationContextChanged:
        assert mode != 'unchanged'
        assert len(calls) == (0 if mode in ('before-call','relabeled','foreign-owner') else 1)
        assert not journal.read(event_type='deliberation.selected')
        if mode in ('before-call','relabeled','foreign-owner'):
            assert not journal.read(event_type='deliberation.framed')
    else:
        assert mode == 'unchanged', 'stale source/profile accepted by selector: ' + mode
        assert chosen.selection.candidate.action_kind is ActionKind.SHARE and len(calls) == 1
    assert not journal.read(event_type='action.attempted')


async def main(root):
    for mode in ('withdrawal','source-erasure','supersession','before-call','retry-withdrawal',
                 'relabeled','foreign-owner','unchanged'):
        await scenario(root/mode, mode)

with tempfile.TemporaryDirectory(prefix='alive-source-epoch-') as folder:
    asyncio.run(main(Path(folder)))
print('HERMES_ALIVE_KERNEL_SOURCE_EPOCH_OK')
