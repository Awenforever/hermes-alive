"""Exercise factorial input/accounting evidence with fake models, not intelligence."""
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from probe_alive_plan_order import run, ARMS, CASES, OUTPUT_SCHEMA


async def exercise(root):
    calls=[]
    async def fake(**kwargs):
        calls.append(kwargs)
        if len(calls)==2: raise RuntimeError('synthetic provider failure')
        if len(calls)==3:
            return SimpleNamespace(model='synthetic/test',choices=[SimpleNamespace(message=SimpleNamespace(content='not json'))])
        data=json.loads(kwargs['messages'][1]['content'])
        item=data['opportunities'][0]
        plan=dict(version=2,recipient_goal='synthetic fixture',speech_act='inform',
            contents=[dict(kind='fact',text='synthetic')],behavior_constraints=[])
        purpose_first='Write communication_plan BEFORE text' in kwargs['messages'][0]['content']
        proposal={'communication_plan':plan,'text':'synthetic'} if purpose_first else {'text':'synthetic','communication_plan':plan}
        proposal.update(agenda_item_id=item['agenda_item_id'],kind='share',topic='synthetic',
            dimensions={k:dict(value=.5,reason='synthetic') for k in (
                'user_value','urgency','novelty','confidence','interruption_cost','risk')})
        kwargs['route_info']['provider']='synthetic'
        return SimpleNamespace(model='synthetic/test',choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps(dict(candidates=[proposal],abstentions=[],reconsiderations=[]))))])
    result=await run(root/'results',model_call=fake)
    assert result['finished'] and result['logical_calls']==len(calls)==len(CASES)*len(ARMS)==24
    assert result['http_requests']==[] and result['sends']==0
    assert result['delivery_authority_granted'] is False and result['semantic_quality_qualified'] is False
    assert result['independently_reviewed'] is False
    assert result['protocol_version']==2
    assert set(OUTPUT_SCHEMA['candidates'][0])=={'agenda_item_id','kind','text','topic','communication_plan','dimensions'}
    for case in result['cases']:
        if case['fixture']['id']=='b':
            summary=json.loads(case['source_payload']['opportunities'][0]['summary_excerpt'])
            assert summary['temporal_bounds']['target_deadline'] is None
    assert all(json.dumps(OUTPUT_SCHEMA) in call['messages'][0]['content'] for call in calls)
    flat=[r for c in result['cases'] for r in c['results']]
    assert len({r['blind_id'] for r in flat})==24
    assert sum('error_class' in r for r in flat)==2
    assert flat[1]['error_class']=='RuntimeError'
    assert flat[2]['raw_output']=='not json' and flat[2]['error_class']=='ModelJSONError'
    for case in result['cases']:
        assert {r['arm'] for r in case['results']}==set(ARMS)
        assert len({r['input_digest'] for r in case['results']})==1
        for r in case['results']:
            if 'error_class' not in r:
                assert r['structural_accepted']==1 and r['structural_rejected']==0
                assert r['plan_before_text']==[r['arm'].endswith('purpose-first')]
    assert all(case['fixture']['expectation'] not in call['messages'][1]['content']
               for case in result['cases'] for call in calls)
    raw=(root/'results'/'report.json').read_bytes()
    try: await run(root/'results',model_call=fake)
    except ValueError: pass
    else: raise AssertionError('evidence overwritten')
    assert (root/'results'/'report.json').read_bytes()==raw and len(calls)==24


with tempfile.TemporaryDirectory(prefix='alive-plan-order-probe-') as folder:
    asyncio.run(exercise(Path(folder)))
print('HERMES_ALIVE_PLAN_ORDER_PROBE_OK')
