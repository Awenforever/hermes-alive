"""Projection boundary without Core imports or credential discovery."""
import copy
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.native_host_snapshot import private_snapshot_config,validate_host_snapshot
from alive_kernel.native_worker_protocol import NativeWorkerError,validate_request,request_digest

snapshot=dict(config=dict(model=dict(default='synthetic',provider='custom:owner'),
    agent=dict(reasoning_effort=False)),secrets=dict(OWNER_KEY='synthetic-only'),selected_model=None)
before=copy.deepcopy(snapshot)
projected=private_snapshot_config(snapshot)
projected['model']['default']='changed'
assert snapshot==before
messages=[dict(role='system',content='synthetic'),dict(role='user',content='synthetic')]
request=dict(version=1,operation_id='op:synthetic',request_id='request:synthetic',subject='owner:synthetic',
    task='synthetic',context_digest=request_digest(messages),messages=messages,runtime=dict(host_snapshot=snapshot),
    identity='',temperature=.2,max_tokens=512,budget_seconds=30)
assert validate_request(request)==request
for patch in (
        dict(config={**snapshot['config'],'plugins':{'enabled':['foreign']}}),
        dict(config={**snapshot['config'],'agent':{'max_iterations':150}}),
        dict(config={**snapshot['config'],'custom_providers':[dict(name='backup',extra_body={'tools':[{'name':'unadmitted'}]})]}),
        dict(config={**snapshot['config'],'providers':{'backup':{'models':{'future':{'extra_body':{'max_tokens':999999}}}}}}),
        dict(selected_model=''),dict(secrets={'OWNER_KEY':lambda:'not transferable'}),
        dict(unauthenticated_endpoints='https://not-an-explicit-list.invalid'),
        dict(secrets={'not-an-env-name':'synthetic'})):
    try: validate_host_snapshot({**snapshot,**patch})
    except NativeWorkerError: pass
    else: raise AssertionError('unadmitted owner projection accepted')
try: validate_request({**request,'runtime':{**request['runtime'],'provider':'foreign'}})
except NativeWorkerError: pass
else: raise AssertionError('mixed resolved and host projection accepted')
from alive_kernel.native_host_snapshot import _route
runtime=dict(api_key='no-key-required',provider='custom',base_url='https://synthetic.invalid/v1',api_mode='chat_completions')
effective=lambda entry,runtime:runtime['provider']
try: _route(runtime,'custom','synthetic',effective,[])
except NativeWorkerError: pass
else: raise AssertionError('SDK placeholder treated as owner authentication')
assert _route(runtime,'custom','synthetic',effective,[runtime['base_url']])['api_key']=='no-key-required'
print('HERMES_ALIVE_NATIVE_HOST_SNAPSHOT_OK')
