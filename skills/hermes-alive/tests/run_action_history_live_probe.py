#!/usr/bin/env python3
"""Probe fault observability and finite calls; zero network/model/channel IO."""
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from probe_alive_live_action_history import run


async def test(root):
    calls=[]
    async def fake(**kwargs):
        data=json.loads(kwargs['messages'][1]['content'])
        calls.append(data)
        assert len(data['recent_action_history'])==1
        if len(calls)==3:
            raise RuntimeError('synthetic-private-provider-detail')
        text=('invalid synthetic model JSON' if len(calls)==2 else
              json.dumps({'candidates':[],'abstentions':[
                  {'agenda_item_id':item['agenda_item_id'],'reason':'Synthetic unit-only abstention.'}
                  for item in data['opportunities']]}))
        return SimpleNamespace(model='synthetic/interpreter',choices=[SimpleNamespace(
            message=SimpleNamespace(content=text))])
    async def forbidden(*args,**kwargs):
        raise AssertionError('unit diagnostic attempted network IO')
    with patch.object(httpx.AsyncClient,'send',forbidden):
        await run(root,model_call=fake)
    text=(root/'report.json').read_text()
    report=json.loads(text)
    assert len(calls)==report['logical_calls']==4
    assert not report['http_requests'] and report['sends']==0 and report['finished']
    assert not report['semantic_quality_qualified'] and not report['longitudinal_utility_qualified']
    assert report['cases'][1]['raw_output']=='invalid synthetic model JSON'
    assert report['cases'][1]['error_class']=='OpportunitySynthesisError'
    assert report['cases'][1]['stage_error_class']=='ModelJSONError'
    assert report['cases'][2]['provider_error_class']=='RuntimeError'
    assert 'synthetic-private-provider-detail' not in text
    assert all(c['new_dispatch_records']==c['new_attempt_records']==0 for c in report['cases'])
    count=len(calls)
    try: await run(root,model_call=fake)
    except ValueError: pass
    else: raise AssertionError('diagnostic overwrote retained evidence')
    assert len(calls)==count


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-action-probe-test-') as directory:
        asyncio.run(test(Path(directory)))
    print('HERMES_ALIVE_ACTION_HISTORY_LIVE_PROBE_OK')
