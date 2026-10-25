#!/usr/bin/env python3
"""Explicit context provenance and revocation across inference."""
import asyncio
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (
    EventEnvelope, ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    MemoryProjection, MemoryProposal, MemoryKind, MemoryAuthority, Sensitivity,
    OpportunitySynthesizer, OpportunitySynthesisError,
)
from alive_kernel.cognition_context import CognitionContextReader


async def exercise(root):
    journal = ExperienceJournal(root / 'experience.sqlite3')
    discovery = DiscoveryOpportunityIngestor(journal)
    memory = MemoryProjection(journal)

    def seed(owner, value, *, actor=None, authority=MemoryAuthority.USER_EXPLICIT, expired=False):
        source = EventEnvelope(event_type='conversation.inbound', source='synthetic',
                               actor=owner, subject=owner, payload={'synthetic': True})
        journal.append(source)
        proposal = MemoryProposal(kind=MemoryKind.PREFERENCE, subject=owner,
                                  predicate='profile.interest.' + str(journal.last_sequence()),
                                  value=value, authority=authority, source_event_ids=(source.event_id,),
                                  confidence=1, valid_until=datetime.now(timezone.utc)-timedelta(seconds=1) if expired else None)
        memory.append_proposal(proposal, actor=actor or owner)
        return proposal

    own = seed('user:test', 'CONTEXT_PRIVATE: I enjoy astronomy discussions')
    seed('user:other', 'OTHER_PRIVATE')
    seed('user:test', 'INFERRED_PRIVATE', authority=MemoryAuthority.MODEL_INFERENCE)
    seed('user:test', 'FORGED_EXPLICIT', actor='model:attacker')
    seed('user:test', 'EXPIRED_PRIVATE', expired=True)
    reader = CognitionContextReader(journal)
    scope = reader.read(subject='user:test', clearance=Sensitivity.PRIVATE)
    assert len(scope) == 1 and scope[0].memory_id == own.proposal_id
    assert reader.read(subject='user:test', clearance=Sensitivity.PUBLIC) == ()
    discovery.ingest(DiscoveryCandidate(source='synthetic', title='Astronomy discussion',
                     summary='Public online astronomy talk', url='https://example.invalid/talk',
                     observed_at=datetime.now(timezone.utc)), subject='user:test')
    synthesizer = OpportunitySynthesizer(journal, content_vault=discovery.vault)

    async def inspect(**kw):
        prompt = json.loads(kw['messages'][1]['content'])
        assert prompt['user_context'][0]['memory_id'] == own.proposal_id
        assert 'CONTEXT_PRIVATE' in kw['messages'][1]['content']
        for forbidden in ('OTHER_PRIVATE', 'INFERRED_PRIVATE', 'FORGED_EXPLICIT', 'EXPIRED_PRIVATE'):
            assert forbidden not in kw['messages'][1]['content']
        return SimpleNamespace(model='actual/context-model', choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"candidates":[]}'))])

    result = await synthesizer.run(subject='user:test', operation_id='context-ok', call=inspect)
    started = journal.get('opportunity.synthesis:context-ok:started')
    assert started.event.payload['context_proposal_event_ids'] == (scope[0].proposal_event_id,)
    assert result.actual_model == 'actual/context-model'

    async def revoke(**kw):
        response = await inspect(**kw)
        memory.forget_item(own.proposal_id, actor='user:test', request_id='context-revoked')
        return response

    try:
        await synthesizer.run(subject='user:test', operation_id='context-revoke', call=revoke)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('revoked user context admitted after model await')
    assert journal.get('opportunity.synthesis:context-revoke:failed') is not None
    assert journal.get('opportunity.synthesis:context-revoke:completed') is None
    assert reader.read(subject='user:test', clearance=Sensitivity.PRIVATE) == ()
    for path in root.glob('experience.sqlite3*'):
        assert b'CONTEXT_PRIVATE' not in path.read_bytes()
    assert not journal.read(event_type='action.attempted')


with tempfile.TemporaryDirectory(prefix='alive-context-test-') as directory:
    asyncio.run(exercise(Path(directory)))
print('HERMES_ALIVE_KERNEL_CONTEXT_SYNTHESIS_OK')
