"""Actual Core task request timeout vs Alive total deadline; controlled HTTP only."""
import argparse
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--repo',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--expect-old-preemption',action='store_true')
p.add_argument('--expect-stage-timeout',action='store_true')
a=p.parse_args();a.output.mkdir(parents=True,mode=0o700,exist_ok=False)
home=a.output/'profile';home.mkdir(mode=0o700)
os.environ['HERMES_HOME']=str(home)
sys.path[:0]=[str(a.core),str(a.repo/'skills/hermes-alive/hooks')]
config=dict(model=dict(default='synthetic-primary',provider='custom:owner'),
    custom_providers=[dict(name='owner',model='synthetic-primary',base_url='https://primary.invalid/v1',
        key_env='SYNTHETIC_PRIMARY_KEY',api_mode='chat_completions'),
        dict(name='backup',model='synthetic-backup',base_url='https://backup.invalid/v1',
            key_env='SYNTHETIC_BACKUP_KEY',api_mode='chat_completions')],
    fallback_providers=[dict(provider='custom:backup',model='synthetic-backup',timeout=.2)],
    auxiliary={'hermes_alive_kernel':{'timeout':.04}},agent={'reasoning_effort':False},
    plugins={'enabled':['hermes-alive'],'entries':{'hermes-alive':{'settings':{}}}})
(home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
(home/'.env').write_text('SYNTHETIC_PRIMARY_KEY=synthetic-primary-key\nSYNTHETIC_BACKUP_KEY=synthetic-backup-key\n',encoding='utf-8')
shutil.copytree(a.repo,home/'plugins/hermes-alive',ignore=shutil.ignore_patterns('.git','__pycache__'))


async def main():
    import httpx
    from hermes_cli.plugins import get_plugin_manager
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from alive_kernel.core_plugin_model_call import CorePluginModelCaller
    from alive_kernel.native_host_caller import HostModelBinding
    requests=[]
    async def send(client,request,*args,**kwargs):
        if not request.url.path.endswith('/chat/completions'):
            return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
        body=json.loads(request.content)
        timeout=request.extensions['timeout']['read']
        requests.append(dict(endpoint=request.url.host,timeout=timeout))
        if request.url.host=='primary.invalid':
            assert request.headers['authorization']=='Bearer synthetic-primary-key'
            await asyncio.sleep(timeout)
            raise httpx.ReadTimeout('synthetic full request timeout',request=request)
        assert request.url.host=='backup.invalid'
        assert request.headers['authorization']=='Bearer synthetic-backup-key'
        await asyncio.sleep(.005)
        return httpx.Response(200,request=request,json=dict(id='synthetic',object='chat.completion',created=0,
            model=body['model'],choices=[dict(index=0,message=dict(role='assistant',content='OK'),finish_reason='stop')],
            usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2)))
    original=httpx.AsyncClient.send;httpx.AsyncClient.send=send
    try:
        with launch_profile_runtime_scope(home):
            manager=get_plugin_manager();manager.discover_and_load()
            context=manager._plugins['hermes-alive'].module._gateway_host_binding.context
            context.register_auxiliary_task('hermes_alive_kernel',display_name='Synthetic timeout probe',
                description='Controlled IO only',defaults={'provider':'auto','model':'','timeout':90,
                    'fallback_chain':config['fallback_providers']})
            caller=CorePluginModelCaller(context,read_binding=lambda:HostModelBinding(
                'user:synthetic','profile:synthetic','operation:timeout-probe','revision:1'),max_calls=1)
            result=None;error=None
            try:
                result=await caller(task='synthetic-timeout',model=None,messages=[{'role':'user','content':'synthetic'}],
                    temperature=0,max_tokens=128,timeout=.02 if a.expect_stage_timeout else 3)
            except TimeoutError:error='TimeoutError'
            if a.expect_stage_timeout:
                # Cold Core initialization also consumes the total deadline;
                # cancellation may precede HTTP. Never require an API start.
                assert error=='TimeoutError' and len(requests)<=1,requests
                assert all(r==dict(endpoint='primary.invalid',timeout=.04) for r in requests),requests
            elif a.expect_old_preemption:
                assert error=='TimeoutError' and requests==[dict(endpoint='primary.invalid',timeout=3)],requests
            else:
                assert error is None and result.model=='synthetic-backup',requests
                assert requests[-1]==dict(endpoint='backup.invalid',timeout=.2),requests
                assert all(r['timeout']==.04 for r in requests[:-1]),requests
            assert not caller.pending
            report=dict(old_preemption_reproduced=a.expect_old_preemption,requests=requests,
                stage_timeout_enforced=a.expect_stage_timeout,
                actual_core=True,real_model_calls=0,sends=0,production_changed=False,
                source='controlled HTTP; not a real-model availability or utility test')
            (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report))
    finally:httpx.AsyncClient.send=original


asyncio.run(main())
