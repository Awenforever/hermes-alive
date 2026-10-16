"""Test operator bootstrap: replace physical HTTP, execute the real worker script."""
import json
import os
import runpy
import sys
import time
from pathlib import Path
import httpx


def controlled(client,request,*args,**kwargs):
    if request.url.path.endswith('/chat/completions'):
        body=json.loads(request.content)
        if body['model']=='policy-openrouter':
            if os.environ.get('ALIVE_TEST_HTTP_DIAGNOSTIC'):
                with open(os.environ['ALIVE_TEST_HTTP_DIAGNOSTIC'],'a',encoding='utf-8') as output:
                    output.write(json.dumps(dict(model='policy-openrouter',
                        only=body.get('provider',{}).get('only')==['synthetic-model-pin'],
                        privacy=body.get('provider',{}).get('data_collection')=='deny'))+'\n')
            assert body['provider']['only']==['synthetic-model-pin']
            assert body['provider']['data_collection']=='deny'
        if request.headers.get('X-Host-Snapshot')=='yes' and body['model']=='configured-primary':
            assert body['native_policy_probe']=='synthetic-marker'
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
        if os.environ.get('ALIVE_TEST_HTTP_DIAGNOSTIC'):
            with open(os.environ['ALIVE_TEST_HTTP_DIAGNOSTIC'],'a',encoding='utf-8') as output:
                output.write(json.dumps(dict(model=body['model'],
                    common=request.headers.get('X-Owner-Policy')=='synthetic-common',
                    route=request.headers.get('X-Route-Policy')==('synthetic-backup' if request.url.host=='backup.invalid' else 'synthetic-main'),
                    key=request.headers.get('authorization')=='Bearer '+key))+'\n')
        assert request.headers['authorization']=='Bearer '+key
        if request.headers.get('X-Owner-Policy'):
            assert request.headers['X-Owner-Policy']=='synthetic-common'
            if request.url.host in ('provider.invalid','backup.invalid'):
                assert request.headers['X-Route-Policy']==('synthetic-backup' if request.url.host=='backup.invalid' else 'synthetic-main')
            elif body['model']=='policy-openrouter':
                assert 'X-Route-Policy' not in request.headers  # Do not leak custom endpoint headers.
        if body['model'] in ('policy-fail-primary','policy-backup'):
            assert request.headers.get('X-Owner-Policy')=='synthetic-common'
        if body['model'] in ('fail-primary','policy-fail-primary'):
            return httpx.Response(403,request=request,json=dict(error=dict(message='synthetic denied',type='permission_error')))
        if body['model']=='hold-primary':
            workspace=Path(sys.argv[sys.argv.index('--workspace')+1])
            (workspace/'scope-test-ready').touch()
            deadline=time.monotonic()+20
            while not (workspace/'scope-test-release').exists():
                if time.monotonic()>deadline: raise RuntimeError('synthetic host change test timed out')
                time.sleep(.05)
        return httpx.Response(200,request=request,json=dict(id='synthetic-156',object='chat.completion',created=0,
            model='served-label/'+body['model'],choices=[dict(index=0,finish_reason='stop',message=dict(
            role='assistant',content=content))],usage=dict(prompt_tokens=100,completion_tokens=10,total_tokens=110)))
    return httpx.Response(503,request=request,json=dict(error=dict(message='synthetic metadata unavailable')))
httpx.Client.send=controlled
async def controlled_async(client,request,*args,**kwargs): return controlled(client,request,*args,**kwargs)
httpx.AsyncClient.send=controlled_async
runpy.run_path(str(Path(__file__).resolve().parents[2]/'hooks'/'native_model_worker.py'),run_name='__main__')
