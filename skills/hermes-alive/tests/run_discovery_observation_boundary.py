"""Collector evidence survives legacy ranking without changing its send view."""
import asyncio
from copy import deepcopy
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))


async def exercise(root):
    from discovery import DiscoveryEngine
    from proactive_watcher import ProactivePlatformWatcher

    materials = [dict(source='synthetic-feed', feed_name='A', title=f'Routine {i}',
                      url=f'https://example.invalid/a/{i}', summary='Unreviewed data')
                 for i in range(140)]
    materials.append(dict(source='synthetic-feed', feed_name='B',
        title='Significant outside profile', url='https://example.invalid/b',
        summary='Synthetic control, not an actual event', score=.01))
    original = deepcopy(materials)
    async def external():
        return materials
    async def local():
        return [dict(title='LOCAL_PRIVATE_SENTINEL')]
    engine = DiscoveryEngine.__new__(DiscoveryEngine)
    engine._external = SimpleNamespace(collect=external, last_health={
        'synthetic-feed': {'ok': True, 'fetched': len(materials)}})
    engine._local = SimpleNamespace(collect=local)
    # Simulate the old pipeline filtering everything AND mutating its input.
    def legacy_gate(items):
        items[0]['title'] = 'LEGACY_MUTATION'
        return []
    engine._apply_pipeline = legacy_gate
    result = await engine.collect()
    assert result['external'] == [] and result['local'][0]['title'] == 'LOCAL_PRIVATE_SENTINEL'
    assert not any('observation' in k for k in result), 'raw evidence leaked into legacy composer context'
    observed = engine.get_observations()
    assert observed['observation_scope'] == 'collector_only'
    assert len(observed['external']) == 128 and observed['omitted_observations'] == 13
    assert observed['external'][:2] == [original[0], original[-1]], 'feed diversity lost before model judgment'
    assert 'local' not in observed and 'LOCAL_PRIVATE_SENTINEL' not in str(observed)
    assert 'LEGACY_MUTATION' not in str(observed)
    # Accessors cannot mutate retained evidence or invoke the legacy delivery guard.
    observed['external'][0]['title'] = 'CALLER_MUTATION'
    observed['source_health'].clear()
    again = engine.get_observations()
    assert again['external'][0]['title'] == original[0]['title'] and again['source_health']
    assert again['fetched_at'] == result['fetched_at']
    assert engine.has_fresh()

    watcher = ProactivePlatformWatcher.__new__(ProactivePlatformWatcher)
    watcher._discovery_engine = engine
    from alive_kernel.discovery_opportunities import mirror_legacy_discovery_batch
    calls = []
    def record(*args, **kwargs):
        calls.append(kwargs)
        return mirror_legacy_discovery_batch(root, **kwargs)
    with patch('alive_kernel.discovery_opportunities.discovery_shadow_enabled', return_value=True), \
         patch('alive_kernel.discovery_opportunities.mirror_legacy_discovery_batch', side_effect=record):
        watcher._mirror_discovery_kernel_shadow(chat_id='synthetic-owner', discovery_context=result)
    assert len(calls) == 1 and calls[0]['max_candidates'] == 128
    assert calls[0]['discovery_context']['external'] == again['external']
    # No source is promoted to permission, action or delivery by this admission.
    from alive_kernel import ExperienceJournal
    journal = ExperienceJournal(root / 'kernel' / 'experience.sqlite3')
    records = journal.read(event_type='discovery.opportunity_observed', limit=256)
    assert len(records) == 128
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')
    assert result['external'] == [], 'shadow changed legacy behavior'

    # Stale or missing observation snapshots are not replaced with a gated batch.
    engine._last_fetch = 0
    before = len(calls)
    with patch('alive_kernel.discovery_opportunities.discovery_shadow_enabled', return_value=True), \
         patch('alive_kernel.discovery_opportunities.mirror_legacy_discovery_batch', side_effect=record):
        watcher._mirror_discovery_kernel_shadow(chat_id='synthetic-owner', discovery_context=result)
    assert len(calls) == before

    from alive_kernel.discovery_opportunities import candidate_from_legacy
    dated = dict(original[0], published_at='Fri, 01 Jan 1999 12:00:00 +0800')
    assert candidate_from_legacy(dated).published_at.isoformat() == '1999-01-01T04:00:00+00:00'
    invalid_date = dict(original[0], published_at='unknown source date')
    unknown = candidate_from_legacy(invalid_date)
    assert unknown.published_at is None and unknown.attributes['published_at_raw'] == 'unknown source date'
    naive_date = dict(original[0], published_at='1999-01-01T12:00:00')
    assert candidate_from_legacy(naive_date).published_at is None
    watcher._discovery_engine = False
    with patch('alive_kernel.discovery_opportunities.discovery_shadow_enabled', return_value=True), \
         patch('alive_kernel.discovery_opportunities.mirror_legacy_discovery_batch', side_effect=record):
        watcher._mirror_discovery_kernel_shadow(chat_id='synthetic-owner', discovery_context=result)
    assert len(calls) == before


async def request_health():
    import discovery
    class Response:
        def __init__(self, url):
            self.url = url
            self.status = 503 if 'bad.invalid' in url or 'bilibili' in url else 200
        async def __aenter__(self):
            if 'v2ex' in self.url:
                raise TimeoutError('private URL or credentials must not enter health metadata')
            return self
        async def __aexit__(self, *_): return False
        async def text(self):
            if 'good.invalid' in self.url:
                return '<rss><channel><item><title>Public fixture</title><link>https://example.invalid/one</link></item></channel></rss>'
            return '<rss><channel /></rss>'
    class Session:
        closed = False
        def get(self, url, **_): return Response(url)
        async def close(self): self.closed = True
    source = discovery.ExternalDiscovery({'sources': {
        'v2ex': {'enabled': True}, 'bilibili': {'enabled': True},
        'sspai': {'enabled': True}, 'rss': {'enabled': True, 'feeds': [
            {'url': 'https://bad.invalid/feed'}, {'url': 'https://good.invalid/feed'}]}}})
    session = Session()
    source._session = session
    async def get_session(): return session
    source._get_session = get_session
    # No HTTP library or network is used; actual collectors handle controlled replies.
    with patch.object(discovery, 'aiohttp', object()):
        items = await source.collect()
    assert len(items) == 1 and session.closed
    health = source.last_health
    assert health['v2ex']['ok'] is False and health['v2ex']['error'] == 'TimeoutError'
    assert health['bilibili']['ok'] is False and health['bilibili']['error'] == 'HTTP503'
    assert health['rss']['status'] == 'partial' and health['rss']['fetched'] == 1
    assert health['sspai']['ok'] is None and health['sspai']['status'] == 'empty_or_unverified'
    assert 'private URL' not in str(health) and 'bad.invalid' not in str(health)
    assert source._collector_context.get() is None


with tempfile.TemporaryDirectory(prefix='alive-observation-boundary-') as temp:
    root = Path(temp)
    os.environ['HERMES_HOME'] = str(root / 'home')
    os.environ['HERMES_ALIVE_SHARED_DIR'] = str(root / 'runtime')
    asyncio.run(exercise(root))
    asyncio.run(request_health())
print('HERMES_ALIVE_DISCOVERY_OBSERVATION_BOUNDARY_OK')
