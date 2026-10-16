"""Real child protocol/context binding on this OS; fake worker is not native Core."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


async def exercise(root):
    from alive_kernel.native_worker_caller import NativeWorkerCaller
    from alive_kernel.native_worker_protocol import NativeWorkerError
    from alive_kernel.model_process import ManagedModelProcess
    core=root/'core'; core.mkdir()
    work=root/'work'; work.mkdir()
    fixture=Path(__file__).resolve().parent/'fixtures'/'model-protocol-worker.py'
    resolutions=[]
    route=dict(provider='custom',model='configured-primary',api_mode='chat_completions',
        base_url='https://provider.invalid/v1',api_key='PRIVATE_SYNTHETIC_KEY',fallback_model=[dict(
            provider='custom',model='configured-backup',base_url='https://backup.invalid/v1',api_key='PRIVATE_BACKUP_KEY')])
    def resolve(**kwargs):
        resolutions.append(kwargs)
        return {**route,'model':'configured-alias-target' if kwargs['model'] else route['model']}
    def caller(**kwargs):
        return NativeWorkerCaller(subject='user:synthetic',operation_id='parent:test',interpreter=sys.executable,
            core=core,private_root=work,environment=dict(os.environ),resolve_runtime=kwargs.pop('resolve_runtime',resolve),
            assert_current=kwargs.pop('assert_current',lambda:True),identity='synthetic consented identity',
            entrypoint=fixture,**kwargs)
    params=dict(task='normal',model=None,messages=[dict(role='system',content='synthetic task'),
        dict(role='user',content='synthetic current context')],temperature=.2,max_tokens=512)
    one=caller(max_calls=16); info={}
    reply=await one(**params,route_info=info)
    assert reply.model=='provider-reported-label' and info['provider']=='custom'
    assert json.loads(reply.choices[0].message.content)==dict(model='configured-primary',has_identity=True,fallback_count=1)
    assert resolutions[-1]==dict(task='normal',model=None) and not one.pending and not list(work.iterdir())
    reply=await one(**{**params,'model':'Hermes-configured-alias'})
    assert json.loads(reply.choices[0].message.content)['model']=='configured-alias-target'
    assert resolutions[-1]['model']=='Hermes-configured-alias'
    from alive_kernel.native_worker_protocol import invocation_limits
    assert invocation_limits(None,90)==(90,85)
    assert invocation_limits(40,90)==(45,40)
    assert invocation_limits(120,60)==(60,55)
    assert invocation_limits(1,90)==(10,1)
    for invalid_timeout in (True,0,-1,241,float('nan'),float('inf'),'40'):
        before=len(resolutions)
        try: await one(**params,timeout=invalid_timeout)
        except NativeWorkerError: pass
        else: raise AssertionError('invalid per-call timeout admitted')
        assert len(resolutions)==before
    observed=[]
    original_run=ManagedModelProcess.run
    async def capture(lease,payload):
        observed.append((lease.timeout_seconds,json.loads(payload)['budget_seconds']))
        return await original_run(lease,payload)
    with patch.object(ManagedModelProcess,'run',capture):
        await one(**params,timeout=40)
    assert observed==[(45,40)]
    for mode in ('wrong_context','mixed_text','fail','wrong_request','authority','old_evidence','not_json',
                 'bad_projection','bad_source_hash','bad_source_length','missing_source_hash'):
        attempts=one.calls
        try: await one(**{**params,'task':mode})
        except NativeWorkerError as error: assert 'PRIVATE_SYNTHETIC_KEY' not in str(error)
        else: raise AssertionError('failed or foreign worker result accepted')
        assert not one.pending and not list(work.iterdir())
        assert one.calls==attempts+1
    denied=caller(assert_current=lambda:False)
    before=len(resolutions)
    try: await denied(**params)
    except NativeWorkerError: pass
    else: raise AssertionError('missing current host binding spent a worker')
    assert denied.calls==0 and len(resolutions)==before
    for invalid_route in (
            {**route,'api_key':lambda:'not JSON'},
            {**route,'request_overrides':{'extra_body':{'tools':[{'name':'unadmitted'}]}}},
            {**route,'fallback_model':[{**route['fallback_model'][0],
                'request_overrides':{'extra_body':{'tools':[{'name':'unadmitted'}]}}}]},
            {**route,'fallback_model':[{'provider':'custom','model':'unresolved-backup','key_env':'NOT_PROJECTED'}]}):
        invalid=caller(resolve_runtime=lambda **_kw:invalid_route)
        try: await invalid(**params)
        except NativeWorkerError: pass
        else: raise AssertionError('unadmitted runtime crossed process boundary')
        assert not invalid.pending and not list(work.iterdir())
    checks=[]
    def changes(): checks.append(True); return len(checks)<3
    changed=caller(assert_current=changes)
    try: await changed(**params)
    except NativeWorkerError: pass
    else: raise AssertionError('changed binding accepted after model await')
    assert changed.calls==1 and not list(work.iterdir())
    budget=caller(max_calls=1); await budget(**params)
    try: await budget(**params)
    except NativeWorkerError: pass
    else: raise AssertionError('parent call budget ignored')

    # Startup deliberately remains pending across repeated caller cancellation.
    # Capture ownership outlives the awaiter; only that same launch resumes.
    pending=caller(); gate=asyncio.Event(); entered=asyncio.Event(); count=[]
    original=ManagedModelProcess._spawn
    async def delayed(lease,*streams):
        entered.set(); await gate.wait(); count.append(1); return await original(lease,*streams)
    with patch.object(ManagedModelProcess,'_spawn',delayed):
        active=asyncio.create_task(pending(**params)); await entered.wait()
        active.cancel(); await asyncio.sleep(0); active.cancel()
        try: await active
        except asyncio.CancelledError: pass
        else: raise AssertionError('cancelled worker emitted a result')
        assert pending.pending and not pending.pending[0]['closed'] and list(work.iterdir())
        try: await pending(**params)
        except NativeWorkerError: pass
        else: raise AssertionError('unknown worker restarted')
        gate.set()
        for _ in range(300):
            await pending.reap_pending()
            if not pending.pending: break
            await asyncio.sleep(.01)
        assert count==[1] and not pending.pending and not list(work.iterdir())


with tempfile.TemporaryDirectory(prefix='alive-native-worker-protocol-') as folder:
    previous={k:os.environ.get(k) for k in ('HERMES_HOME','HERMES_ALIVE_SHARED_DIR')}
    os.environ['HERMES_HOME']=str(Path(folder)/'profile')
    os.environ['HERMES_ALIVE_SHARED_DIR']=str(Path(folder)/'runtime')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
    try: asyncio.run(exercise(Path(folder)))
    finally:
        for key,value in previous.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
print('HERMES_ALIVE_NATIVE_WORKER_PROTOCOL_OK')
