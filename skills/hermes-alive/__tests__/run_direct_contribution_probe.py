"""Envelope, raw-source separation, failed-call accounting and no sending proof."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

async def exercise(root):
    from probe_alive_direct_contribution import CASES, run, validate
    calls=[]
    async def fake(**kwargs):
        calls.append(kwargs)
        assert kwargs['task']=='alive_direct_contribution' and kwargs['model'] is None
        payload=json.loads(kwargs['messages'][1]['content'])
        assert 'expectation' not in kwargs['messages'][1]['content']
        assert payload['owner_timezone']=='Asia/Shanghai' and payload['as_of']=='2026-10-16T02:00:00+00:00'
        assert len(payload['opportunities'])==1 and not payload['recent_expression_history']
        identity=payload['opportunities'][0]['agenda_item_id']
        if identity=='item:d2': raise RuntimeError('synthetic failed provider')
        value=dict(decision='silence',message=None,reason='synthetic')
        if identity=='item:d3': value['message']='not a valid silent proposal'
        if identity=='item:d1': value.update(decision='message',message='synthetic reminder')
        return SimpleNamespace(model='synthetic/model',choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps(value)))])
    report=await run(root/'result',model_call=fake)
    assert report['finished'] and report['logical_calls']==len(calls)==len(CASES)==6
    assert report['http_requests']==[] and report['sends']==0
    assert not any(report[k] for k in ('delivery_authority_granted','semantic_quality_qualified','independently_reviewed'))
    assert [c.get('error_class') for c in report['cases']]==[None,'RuntimeError','ValueError',None,None,None]
    for item in report['cases']:
        assert item['source_payload']['opportunities'][0]['agenda_item_id']=='item:'+item['fixture']['id']
        if 'proposal' in item: assert item['review_status']=='unreviewed'
    before=(root/'result'/'report.json').read_bytes()
    try: await run(root/'result',model_call=fake)
    except ValueError: pass
    else: raise AssertionError('evidence overwritten')
    assert before==(root/'result'/'report.json').read_bytes() and len(calls)==6
    for document in (
            dict(decision='silence',message='hidden message',reason='x'),
            dict(decision='message',message='',reason='x'),
            dict(decision='message',message='x',reason=''),
            dict(decision='silence',message=None,reason='x',authority=True)):
        try: validate(json.dumps(document))
        except ValueError: pass
        else: raise AssertionError('invalid envelope accepted')


with tempfile.TemporaryDirectory(prefix='alive-direct-contribution-') as folder:
    previous=os.environ.get('HERMES_HOME')
    os.environ['HERMES_HOME']=str(Path(folder)/'profile')
    try: asyncio.run(exercise(Path(folder)))
    finally:
        if previous is None: os.environ.pop('HERMES_HOME',None)
        else: os.environ['HERMES_HOME']=previous
print('HERMES_ALIVE_DIRECT_CONTRIBUTION_PROBE_OK')
