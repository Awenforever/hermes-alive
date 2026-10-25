"""Publisher description reaches kernel evidence without inventing video access."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from discovery import ExternalDiscovery
from alive_kernel import ExperienceJournal, DiscoveryOpportunityIngestor, OpportunitySynthesizer, Sensitivity
from alive_kernel.discovery_opportunities import candidate_from_legacy


async def exercise(root):
    source = ExternalDiscovery({'sources': {'bilibili': {'max_results': 3}}})
    class Response:
        status = 200
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return False
        async def json(self):
            return {'data': {'list': [
                dict(title='Synthetic public video A', bvid='fixture-a', desc='PUBLISHER_DESCRIPTION',
                    owner={'name': 'PUBLIC_CREATOR'}, pubdate=1700000000, stat={'view': 2}),
                dict(title='Synthetic public video B', bvid='fixture-b', stat={'view': 999999}),
                dict(title='Synthetic public video C', bvid='fixture-c', desc='x' * 1400 + 'HIDDEN_TAIL',
                    pubdate=True, stat={}),
            ]}}
    async def session(): return object()
    source._get_session = session
    source._request = lambda *_args, **_kwargs: Response()
    materials = await source._collect_bilibili()
    a, b, c = materials
    assert 'PUBLISHER_DESCRIPTION' in a['summary'] and 'PUBLIC_CREATOR' in a['summary']
    assert '未核实视频正文' in a['summary'] and a['evidence_scope'] == 'publisher_description'
    assert a['published_at'] == datetime.fromtimestamp(1700000000, timezone.utc).isoformat()
    assert '未取得内容简介或视频正文' in b['summary']
    assert b['evidence_scope'] == 'listing_metadata_only' and b['published_at'] is None
    assert c['description_truncated'] is True and 'HIDDEN_TAIL' not in c['summary']
    assert '简介已截断' in c['summary'] and c['published_at'] is None
    journal = ExperienceJournal(root / 'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    for material in materials:
        reader.ingest(candidate_from_legacy(material), subject='user:synthetic')
    evidence = reader.active_evidence(subject='user:synthetic', clearance=Sensitivity.PRIVATE)
    first = next(v for v in evidence if v.content['title'] == a['title'])
    assert 'PUBLISHER_DESCRIPTION' in first.content['summary']
    assert first.content['published_at'] == a['published_at']
    async def inspect(**kwargs):
        prompt = json.loads(kwargs['messages'][1]['content'])
        seen = next(v for v in prompt['opportunities'] if v['title'] == a['title'])
        assert 'PUBLISHER_DESCRIPTION' in seen['summary_excerpt']
        assert '未核实视频正文' in seen['summary_excerpt']
        assert seen['published_at'] == a['published_at']
        return SimpleNamespace(model='synthetic/video-evidence', choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"candidates":[]}'))])
    await OpportunitySynthesizer(journal).run(subject='user:synthetic',
        operation_id='synthetic-video-evidence', call=inspect)
    assert not journal.read(event_type='action.attempted')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-video-evidence-') as directory:
        asyncio.run(exercise(Path(directory)))
    print('HERMES_ALIVE_BILIBILI_CONTENT_EVIDENCE_OK')
