"""Test operator bootstrap: replace physical HTTP, execute the real worker script."""
import json
import runpy
from pathlib import Path
import httpx


def controlled(client,request,*args,**kwargs):
    if request.url.path=='/v1/chat/completions':
        body=json.loads(request.content)
        assert not body.get('tools') and not body.get('stream')
        text=json.dumps(body['messages'],ensure_ascii=False)
        assert 'SYNTHETIC_PERSONA_156' in text
        user=next(m['content'] for m in body['messages'] if m['role']=='user')
        try: context=json.loads(user)
        except ValueError: context=None
        if isinstance(context,dict) and 'opportunities' in context:
            assert 'SYNTHETIC_CONTEXT_156' in user
            content=json.dumps(dict(candidates=[],abstentions=[dict(agenda_item_id=e['agenda_item_id'],
                reason='synthetic deliberate silence') for e in context['opportunities']]))
        else:
            assert 'SYNTHETIC_TASK_156' in text and 'SYNTHETIC_CONTEXT_156' in text
            content='native synthetic reply'
        key='PRIVATE_FALLBACK_KEY' if request.url.host=='backup.invalid' else 'PRIVATE_MAIN_KEY'
        assert request.headers['authorization']=='Bearer '+key
        if body['model']=='fail-primary':
            return httpx.Response(403,request=request,json=dict(error=dict(message='synthetic denied',type='permission_error')))
        return httpx.Response(200,request=request,json=dict(id='synthetic-156',object='chat.completion',created=0,
            model='served-label/'+body['model'],choices=[dict(index=0,finish_reason='stop',message=dict(
            role='assistant',content=content))],usage=dict(prompt_tokens=100,completion_tokens=10,total_tokens=110)))
    return httpx.Response(503,request=request,json=dict(error=dict(message='synthetic metadata unavailable')))
httpx.Client.send=controlled
async def controlled_async(client,request,*args,**kwargs): return controlled(client,request,*args,**kwargs)
httpx.AsyncClient.send=controlled_async
runpy.run_path(str(Path(__file__).resolve().parents[2]/'hooks'/'native_model_worker.py'),run_name='__main__')
