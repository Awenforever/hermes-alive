#!/usr/bin/env python3
"""A competing projector reaching the target is completion, not lost evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, EventEnvelope, DiscoveryCandidate, DiscoveryOpportunityIngestor, Sensitivity
from alive_kernel.discovery_opportunities import DiscoveryOpportunityError

with tempfile.TemporaryDirectory(prefix='alive-discovery-race-') as folder:
    journal = ExperienceJournal(Path(folder) / 'journal.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture', title='Source',
        summary='Unverified public fixture.', url='https://example.invalid/01',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    competitor = DiscoveryOpportunityIngestor(journal, content_vault=reader.vault)
    journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor='user:test', subject='user:test', payload={'synthetic':True}))
    target = journal.last_sequence()
    original = reader.projection_checkpoint
    reads = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        def scheduled_checkpoint():
            previous = original()
            reads.append(previous)
            if len(reads) == 1:
                assert previous < target
                pool.submit(competitor.project_new).result(timeout=15)
                assert competitor.projection_checkpoint() == target
            return previous
        reader.projection_checkpoint = scheduled_checkpoint
        reader.project_new()
    reader.projection_checkpoint = original
    assert reader.projection_checkpoint() == target and reader.validate_projection()
    evidence = reader.active_evidence(subject='user:test', clearance=Sensitivity.PRIVATE,
        observation_event_ids=(source.observation_event_id,))
    assert len(evidence) == 1 and evidence[0].observation_event_id == source.observation_event_id
    # A real inability to replay an unapplied prefix must still fail closed.
    journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor='user:test', subject='user:test', payload={'synthetic':True}))
    replay = journal.iter_replay
    journal.iter_replay = lambda **kw:iter(())
    try:
        reader.project_new()
    except DiscoveryOpportunityError:
        pass
    else:
        raise AssertionError('missing replay prefix was silently accepted')
    finally:
        journal.iter_replay = replay
    assert reader.projection_checkpoint() < journal.last_sequence()
    reader.project_new()
    assert reader.projection_checkpoint() == journal.last_sequence()
print('HERMES_ALIVE_KERNEL_DISCOVERY_PROJECTION_RACE_OK')
