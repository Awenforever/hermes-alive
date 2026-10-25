"""Offline test transport for the real native worker; no physical HTTP is allowed."""
import json
from pathlib import Path
import runpy
import sys
import httpx

workspace=Path(sys.argv[sys.argv.index('--workspace')+1])
trace=workspace.parents[2]/'http-observations.jsonl'

def controlled(client,request,*args,**kwargs):
    if not request.url.path.endswith('/chat/completions'):
        return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
    body=json.loads(request.content)
    assert request.url.host=='provider.invalid' and body['model']=='configured-primary'
    assert request.headers['authorization']=='Bearer SYNTHETIC_CYCLE_KEY'
    assert not body.get('tools') and not body.get('stream')
    assert 'SYNTHETIC_NATIVE_LIVING_CYCLE' in json.dumps(body['messages'])
    user=next(item['content'] for item in body['messages'] if item['role']=='user')
    try: data=json.loads(user)
    except ValueError: data=json.loads(user.split('\n',1)[1])
    record={}
    if isinstance(data,list):
        stage='selection'
        chosen=next(item for item in data if item['candidate_id'].startswith('opportunity-candidate:'))
        value=dict(candidate_id=chosen['candidate_id'],rationale='Synthetic wiring choice, not utility evidence.')
    elif 'feedback_text' in data:
        stage='feedback'
        assert 'SYNTHETIC_RAW_FEEDBACK' in data['feedback_text']
        value=dict(summary='Synthetic mixed feedback, not a profile update.',signals=[
            dict(axis='presentation',key='detail',option='brief-first',direction='support',scope='uncertain',
                quote='Please start with brief points',hypothesis='Tentative presentation request.',
                uncertainties=['Single synthetic reply.']),
            dict(axis='interruption',key='availability',option='busy-today',direction='oppose',scope='situational',
                quote='I am busy today',hypothesis='Temporary availability, not topic dislike.',
                uncertainties=['End time unknown.'])],unresolved=[])
    elif 'opportunities' in data:
        stage='generation'
        advice=[item for item in data['learned_advisory'] if item.get('kind')=='tentative_feedback_interpretation']
        feedback=data['recent_feedback_context']
        record.update(feedback_hypotheses=len(advice),raw_feedback_present='SYNTHETIC_RAW_FEEDBACK' in user)
        assert bool(advice)==bool(feedback)
        if advice:
            assert advice[0]['automatic_learning_authority'] is False
            assert len(advice[0]['findings']['signals'])==2
            assert 'SYNTHETIC_RAW_FEEDBACK' in feedback[0]['feedback_text']
        else:
            assert 'SYNTHETIC_RAW_FEEDBACK' not in user
        for previous in data['recent_expression_history']:
            assert previous['status']=='generated_wording_only_delivery_unknown'
            assert previous['action_authority'] is False and previous['user_preference_evidence'] is False
        source=data['opportunities'][0]
        value=dict(candidates=[dict(agenda_item_id=source['agenda_item_id'],kind='share',topic='synthetic repair',
            dimensions={key:dict(value=.1 if key in ('risk','urgency','interruption_cost') else .8,
                reason='Synthetic model judgment; not actual recipient quality.') for key in (
                'user_value','urgency','novelty','confidence','interruption_cost','risk')},
            communication_plan=dict(version=2,recipient_goal='Share the one synthetic public fact.',speech_act='share',
                contents=[dict(kind='fact',text=source['summary_excerpt'])],behavior_constraints=[]))])
    elif 'meaning' in data:
        if 'atom_reviews' in json.dumps(body['messages'][0]):
            stage='semantic_review'
            value=dict(atom_reviews=[dict(atom_id=item['atom_id'],preserved=True,risks=[]) for item in data['meaning']['atoms']],
                added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
        else:
            stage='expression'
            value='\n\n'.join(item['text'] for item in data['meaning']['atoms'])
    elif 'candidate' in data:
        stage='purpose' if data.get('assessment_kind')=='recipient-purpose-v2' else 'source_review'
        value=dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='Synthetic assessment, not semantic proof.')
    else: raise AssertionError('unknown synthetic task shape')
    record['stage']=stage
    with trace.open('a',encoding='utf-8') as output:output.write(json.dumps(record)+'\n')
    content=value if isinstance(value,str) else json.dumps(value)
    return httpx.Response(200,request=request,json=dict(id='synthetic-living-cycle',object='chat.completion',created=0,
        model=body['model'],choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content=content))],
        usage=dict(prompt_tokens=100,completion_tokens=20,total_tokens=120)))

httpx.Client.send=controlled
async def controlled_async(client,request,*args,**kwargs):return controlled(client,request,*args,**kwargs)
httpx.AsyncClient.send=controlled_async
runpy.run_path(str(Path(__file__).resolve().parents[2]/'hooks/native_model_worker.py'),run_name='__main__')
