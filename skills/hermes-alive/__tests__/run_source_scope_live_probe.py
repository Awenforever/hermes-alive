#!/usr/bin/env python3
"""Probe accounting/evidence mechanics with a fake model; not semantic evidence."""
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from probe_alive_live_source_scope import run, CASES


async def exercise(root):
    calls = []
    async def fake(**kwargs):
        calls.append(kwargs)
        if kwargs['task']=='alive_opportunity_candidates':
            opportunity = json.loads(kwargs['messages'][1]['content'])['opportunities'][0]
            value = dict(candidates=[dict(agenda_item_id=opportunity['agenda_item_id'],kind='share',
                text=opportunity['summary_excerpt']+' '+opportunity['url'],topic='bicycle',
                dimensions={name:dict(value=.2,reason='synthetic') for name in
                    ('user_value','urgency','novelty','confidence','risk','interruption_cost')})])
        else:
            kwargs['route_info'].update(provider='synthetic-provider')
            value = dict(verdict='unsupported' if kwargs['task']=='alive_source_scope_contrast' else 'supported',
                unsupported_claims=['synthetic assertion'] if kwargs['task']=='alive_source_scope_contrast' else [],
                uncertainties=[],reason='fake protocol fixture, not a real assessment')
        return SimpleNamespace(model='synthetic-model',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])
    report = await run(root/'report', model_call=fake)
    assert report['finished'] and report['logical_calls']==len(calls)==3*len(CASES)
    assert not report['http_requests'] and report['sends']==0
    assert report['semantic_quality_qualified'] is False
    assert report['delivery_authority_granted'] is False
    assert all(c['contrast_review']['diagnostic_only'] and c['generated_review'] is not None
               for c in report['cases'])
    before = (root/'report'/'report.json').read_bytes()
    try:
        await run(root/'report',model_call=fake)
    except ValueError:
        pass
    else:
        raise AssertionError('probe overwrote previous evidence')
    assert (root/'report'/'report.json').read_bytes()==before and len(calls)==12
    contrast = await run(root/'scope-only', model_call=fake, contrasts_only=True, contrast_mode='scope')
    assert contrast['finished'] and contrast['logical_calls']==4 and len(calls)==16
    for case, fixture in zip(contrast['cases'], CASES):
        assert len(case['model_calls'])==1 and 'candidates' not in case
        snapshot=json.loads(case['model_calls'][0]['messages'][1]['content'])
        assert snapshot['candidate']['text']==fixture['scope_contrast']


with tempfile.TemporaryDirectory(prefix='alive-scope-probe-') as folder:
    asyncio.run(exercise(Path(folder)))
print('HERMES_ALIVE_SOURCE_SCOPE_LIVE_PROBE_OK')
