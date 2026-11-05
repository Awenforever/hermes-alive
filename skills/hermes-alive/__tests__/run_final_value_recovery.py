"""Persisted earlier interpretations retain their original review contracts."""
import asyncio
from pathlib import Path
import tempfile
from unittest.mock import patch

from run_discovery_authoring import exercise
from alive_kernel import ExperienceJournal, OpportunitySynthesizer
from alive_kernel.content_vault import ContentReference
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from alive_kernel.review_contracts import (LEGACY_SPLIT_SOURCE_REVIEW, FIRST_FACTS_AND_FIT_REVIEW,
    FACTS_AND_FIT_ASSESSMENT, SPLIT_SOURCE_REVIEW, FIRST_FLAT_REVIEW, FLAT_FIT_ASSESSMENT)


async def test(root, original_contract, original_scope):
    root.mkdir()
    original = OpportunitySynthesizer.run

    async def historical_start(self, **kwargs):
        # Only interpretation generation runs with the previous default. Its
        # stored method must determine later author/review/recovery semantics.
        with patch('alive_kernel.opportunity_synthesis.SPLIT_SOURCE_REVIEW', original_contract):
            return await original(self, **kwargs)

    with patch.object(OpportunitySynthesizer, 'run', historical_start):
        await exercise(root, 'supported')  # Includes cold completed recovery, no new calls.
    import alive_kernel.opportunity_synthesis as synthesis
    assert synthesis.SPLIT_SOURCE_REVIEW == SPLIT_SOURCE_REVIEW
    journal = ExperienceJournal(root / 'journal.sqlite3')
    starts = [r for r in journal.read() if 'interpreter_method' in r.event.payload]
    assert starts and any(r.event.payload['interpreter_method'].get('discovery_source_review')
                         == original_contract for r in starts)
    reviews = journal.read(event_type='opportunity.source_support_completed')
    assert len(reviews) == 1
    reviewer = ExpressionSourceSupportReviewer(journal)
    ref = ContentReference.from_event_payload(reviews[0].event.payload['content'])
    retained = reviewer.vault.resolve_json(ref.content_id, expected_subject='user:test',
                                           expected_purpose='opportunity.source-support')
    assert retained['snapshot']['expression_binding'].get('final_assessment_scope') == original_scope
    assert ('factual_support' in retained['findings']) == (original_scope is not None)
    assert reviewer.validate_stored_findings(retained['findings'], retained['snapshot']) == retained['findings']


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-final-value-recovery-') as directory:
        asyncio.run(test(Path(directory) / 'legacy', LEGACY_SPLIT_SOURCE_REVIEW, None))
        asyncio.run(test(Path(directory) / 'first-fit', FIRST_FACTS_AND_FIT_REVIEW, FACTS_AND_FIT_ASSESSMENT))
        asyncio.run(test(Path(directory) / 'previous-flat', FIRST_FLAT_REVIEW, FLAT_FIT_ASSESSMENT))
    print('FINAL_VALUE_RECOVERY_OK')
