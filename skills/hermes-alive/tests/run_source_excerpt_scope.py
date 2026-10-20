"""Same versioned bounded evidence reaches interpretation and source review."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor, OpportunitySynthesizer
from alive_kernel.host_discovery import source_prompt_excerpt, SOURCE_EXCERPT_POLICY, HostDiscoveryError
from alive_kernel.source_support import SourceSupportReviewer
import alive_kernel.opportunity_synthesis as synthesis


async def exercise(root, legacy):
    journal = ExperienceJournal(root/'journal.sqlite3')
    ingestor = DiscoveryOpportunityIngestor(journal)
    summary = 'Source introduction. ' * 130 + 'LATE_QUALIFICATION: demonstrated at two museums, not all settings.'
    assert 1800 < summary.index('LATE_QUALIFICATION') < 8192
    page = ingestor.ingest(DiscoveryCandidate(source='hermes.web.extract',title='Public source',
        summary=summary,url='https://example.invalid/page',observed_at=datetime.now(timezone.utc),
        attributes={'read_scope':'webpage_extract'}),subject='user:test')
    listing = ingestor.ingest(DiscoveryCandidate(source='hermes.web.search',title='Public listing',
        summary=summary,url='https://example.invalid/listing',observed_at=datetime.now(timezone.utc),
        attributes={'read_scope':'search_listing'}),subject='user:test')
    observed = []
    async def generate(**kw):
        data = json.loads(kw['messages'][1]['content'])
        assert len(kw['messages'][1]['content']) <= 24000  # Existing shared admission budget.
        by_id = {o['agenda_item_id']:o for o in data['opportunities']}
        assert ('LATE_QUALIFICATION' in by_id[page.agenda_item_id]['summary_excerpt']) is not legacy
        assert 'LATE_QUALIFICATION' not in by_id[listing.agenda_item_id]['summary_excerpt']
        assert by_id[page.agenda_item_id]['summary_may_be_truncated'] is legacy
        observed.append(by_id[page.agenda_item_id]['summary_excerpt'])
        value = {'candidates':[{'agenda_item_id':page.agenda_item_id,'kind':'share','topic':'museum',
            'text':'A public source describes a conservation method. https://example.invalid/page',
            'dimensions':{n:{'value':.1 if n in ('risk','interruption_cost') else .8,'reason':'synthetic'}
                for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}
        return SimpleNamespace(model='synthetic/model',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])
    with patch.object(synthesis,'SOURCE_EXCERPT_POLICY',None if legacy else SOURCE_EXCERPT_POLICY):
        result = await OpportunitySynthesizer(journal).run(subject='user:test',operation_id='one',call=generate)
    start = journal.get('opportunity.synthesis:one:started')
    assert start.event.payload['interpreter_method']['source_excerpt_policy'] == (None if legacy else SOURCE_EXCERPT_POLICY)
    data, recovered = SourceSupportReviewer(journal).snapshot(subject='user:test',interpretation_id='one',
        candidate_id=result.candidates[0].action.candidate_id)
    assert recovered == result
    assert next(e['excerpt'] for e in data['evidence'] if e['event_id']==page.observation_event_id) == observed[0]
    assert not journal.read(event_type='action.attempted')


sample = dict(source='hermes.web.extract',attributes={'read_scope':'webpage_extract'},summary='x'*8192)
assert len(source_prompt_excerpt(sample,policy=SOURCE_EXCERPT_POLICY)) == 8192
assert len(source_prompt_excerpt(sample)) == 1800  # Absent historical method field.
assert len(source_prompt_excerpt({**sample,'source':'other'},policy=SOURCE_EXCERPT_POLICY)) == 1800
try: source_prompt_excerpt(sample,policy='unknown')
except HostDiscoveryError: pass
else: raise AssertionError('unknown evidence scope silently widened')
with tempfile.TemporaryDirectory(prefix='alive-source-scope-') as directory:
    for legacy in (False,True):
        root = Path(directory)/str(legacy); root.mkdir()
        asyncio.run(exercise(root,legacy))
print('HERMES_ALIVE_SOURCE_EXCERPT_SCOPE_OK')
