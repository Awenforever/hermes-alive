"""Paired source-only stage/renderer mechanics; fake responses prove no intelligence."""
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from probe_alive_purpose_only import run, CASES, purpose_document


async def exercise(root):
    calls=[]
    def answer(value):
        return SimpleNamespace(model='synthetic/test',choices=[SimpleNamespace(message=SimpleNamespace(
            content=value if isinstance(value,str) else json.dumps(value)))])
    async def fake(**kwargs):
        calls.append(kwargs)
        data=json.loads(kwargs['messages'][1]['content'])
        if kwargs['task']=='alive_semantic_render':
            assert data['language']=='zh' and data['expression_context']['authority_granted'] is False
            return answer('\n'.join(atom['text'] for atom in data['meaning']['atoms']))
        # Purpose receives only the original owner/source data, never output from
        # the other path or an already-proposed goal/message, regardless of order.
        assert set(data)=={'as_of','corrective_reviews','recent_expression_history','recent_action_history',
            'recent_feedback_context','learned_advisory','user_context','opportunities'}
        item=data['opportunities'][0]; key=item['agenda_item_id'].split(':')[-1]
        plan=dict(version=2,recipient_goal='synthetic need',speech_act='inform',
            contents=[dict(kind='fact',text='synthetic')],behavior_constraints=[])
        if kwargs['task']=='alive_purpose_only':
            if key=='p3': return answer(dict(decision='now',reason='synthetic invalid',communication_plan=None))
            return answer(dict(decision='defer' if key in ('p5','p6') else 'now',reason='synthetic',
                communication_plan=None if key in ('p5','p6') else plan))
        assert kwargs['task']=='alive_opportunity_candidates'
        if key=='p1': raise RuntimeError('synthetic provider failure')
        if key in ('p5','p6'):
            return answer(dict(candidates=[],abstentions=[dict(agenda_item_id=item['agenda_item_id'],reason='synthetic')]))
        return answer(dict(candidates=[dict(agenda_item_id=item['agenda_item_id'],kind='share',text='synthetic',
            topic='synthetic',communication_plan=plan,dimensions={k:dict(value=.5,reason='synthetic') for k in (
                'user_value','urgency','novelty','confidence','interruption_cost','risk')})],abstentions=[]))
    report=await run(root/'report',model_call=fake)
    assert report['finished'] and report['logical_calls']==len(calls)==18
    assert not report['http_requests'] and report['sends']==0
    assert not report['semantic_quality_qualified'] and not report['delivery_authority_granted']
    assert not report['independently_reviewed']
    assert len(report['cases'])==len(CASES)==6
    errors=[]; render_prompts=[]
    for case in report['cases']:
        assert set(case['paths'])=={'baseline','purpose_only'}
        assert len({p['input_digest'] for p in case['paths'].values()})==1
        for path in case['paths'].values():
            if 'error_class' in path: errors.append(path['error_class'])
            if path.get('disposition')=='rendered_unreviewed':
                assert path['fidelity_status']=='review_required'
            render_prompts += [call['system_prompt'] for call in path['calls'] if call['task']=='alive_semantic_render']
        if case['fixture']['id'] in ('p5','p6'):
            assert case['paths']['purpose_only']['disposition']=='defer'
            assert len(case['paths']['purpose_only']['calls'])==1
    assert len(set(render_prompts))==1 and len(errors)==2
    before=(root/'report'/'report.json').read_bytes()
    try: await run(root/'report',model_call=fake)
    except ValueError: pass
    else: raise AssertionError('old evidence overwritten')
    assert (root/'report'/'report.json').read_bytes()==before and len(calls)==18
    unavailable_calls=[]
    async def wrong_family(**kwargs):
        unavailable_calls.append(kwargs)
        return answer('fallback returned an unrequested family')
    unavailable=await run(root/'wrong-family',model_call=wrong_family,required_family='qwen')
    assert unavailable['finished'] is False and len(unavailable_calls)==unavailable['logical_calls']==1
    assert unavailable['stopped_reason']=='requested_family_unavailable_or_fallback_changed_family'
    failed_calls=[]
    async def unavailable_provider(**kwargs):
        failed_calls.append(kwargs); raise RuntimeError('synthetic provider unavailable')
    failed=await run(root/'provider-unavailable',model_call=unavailable_provider,required_family='qwen')
    assert not failed['finished'] and len(failed_calls)==failed['logical_calls']==1
    available_calls=[]
    async def available_family(**kwargs):
        available_calls.append(kwargs)
        data=json.loads(kwargs['messages'][1]['content'])
        key=data['opportunities'][0]['agenda_item_id']
        value=(dict(decision='defer',reason='synthetic',communication_plan=None)
               if kwargs['task']=='alive_purpose_only' else
               dict(candidates=[],abstentions=[dict(agenda_item_id=key,reason='synthetic')]))
        result=answer(value); result.model='Qwen3.8-reasoner'; return result
    available=await run(root/'available-family',model_call=available_family,required_family='qwen')
    assert available['finished'] and len(available_calls)==available['logical_calls']==12
    try: purpose_document(json.dumps(dict(decision='defer',reason='x',communication_plan={})))
    except ValueError: pass
    else: raise AssertionError('deferred purpose smuggled a message plan')


with tempfile.TemporaryDirectory(prefix='alive-purpose-only-probe-') as folder:
    asyncio.run(exercise(Path(folder)))
print('HERMES_ALIVE_PURPOSE_ONLY_PROBE_OK')
