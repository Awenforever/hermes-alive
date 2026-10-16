"""Host acquisition/lifetime tests; worker replaced, no Core or model HTTP."""
import asyncio
from dataclasses import replace
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.native_host_caller import (HostModelBinding,HostModelCapability,
    HostNativeCaller,minimal_model_environment)
from alive_kernel.native_worker_protocol import NativeWorkerError


async def main():
    binding=HostModelBinding('owner:test','profile:test','operation:test','revision:1')
    live=[True]
    reads=[]
    workers=[]
    configuration={'model':{'default':'synthetic','provider':'custom:owner'}}
    def read(bound,name):
        assert bound is binding
        reads.append(name)
        return 'synthetic-secret'
    cap=HostModelCapability(binding,configuration,('OWNER_KEY',),read,lambda _:live[0])
    selected=[cap]
    started=asyncio.Event()
    release=asyncio.Event()
    block=[False]
    retain=[False]
    class Worker:
        def __init__(self,**kw):
            self.arguments=kw
            self.pending=()
            workers.append(self)
        async def reap_pending(self,**kw): return {'closed':0,'remaining':len(self.pending)}
        async def __call__(self,**kw):
            assert self.arguments['assert_current']() is True
            if block[0]:
                started.set()
                await release.wait()
            if retain[0]: self.pending=({'request_id':'synthetic-pending'},)
            return self.arguments['resolve_runtime']()['host_snapshot']
    def caller():
        return HostNativeCaller(subject=binding.subject,profile_id=binding.profile_id,
            operation_id=binding.operation_id,acquire=lambda **_:selected[0],
            interpreter=sys.executable,core='.',private_root='.',
            environment={'PATH':'synthetic-path','OWNER_KEY':'ambient-secret',
                         'HOME':'foreign-home','USERPROFILE':'foreign-profile','PYTHONPATH':'foreign-code'})
    async def invoke(instance):
        return await instance(task='synthetic',model=None,messages=[],temperature=.2,max_tokens=512)
    async def reject(capability,read_count):
        selected[0]=capability
        before=len(workers)
        try: await invoke(caller())
        except NativeWorkerError: pass
        else: raise AssertionError('invalid host capability accepted')
        assert len(workers)==before and len(reads)==read_count
    with patch('alive_kernel.native_host_caller.NativeWorkerCaller',Worker):
        result=await invoke(caller())
        assert result['secrets']=={'OWNER_KEY':'synthetic-secret'}
        assert workers[-1].arguments['environment']=={'PATH':'synthetic-path'}
        configuration['model']['default']='changed-after-acquisition'
        assert result['config']['model']['default']=='synthetic'
        await reject(replace(cap,binding=replace(binding,profile_id='profile:other')),1)
        await reject(replace(cap,credential_names=([],)),1)
        await reject(replace(cap,credential_names=('OWNER_KEY','OWNER_KEY')),1)
        await reject(replace(cap,configuration={'model':{},'plugins':{'enabled':True}}),1)
        await reject(replace(cap,unauthenticated_endpoints='https://invalid.test'),1)
        live[0]=False
        await reject(cap,1)
        live[0]=True
        def revoke(bound,name):
            value=read(bound,name)
            live[0]=False
            return value
        await reject(replace(cap,read_secret=revoke),2)
        live[0]=True
        selected[0]=cap
        limited=caller()
        limited.max_calls=1
        await invoke(limited)
        try: await invoke(limited)
        except NativeWorkerError: pass
        else: raise AssertionError('budget not enforced')
        concurrent=caller()
        block[0]=True
        active=asyncio.create_task(invoke(concurrent))
        await started.wait()
        before=len(reads)
        try: await invoke(concurrent)
        except NativeWorkerError: pass
        else: raise AssertionError('overlapping acquisition accepted')
        assert len(reads)==before
        release.set()
        await active
        block[0]=False
        retain[0]=True
        retained=caller()
        await invoke(retained)
        assert retained.pending
        before=len(reads)
        try: await invoke(retained)
        except NativeWorkerError: pass
        else: raise AssertionError('uncertain worker allowed another acquisition')
        assert len(reads)==before
        workers[-1].pending=()
        retain[0]=False
        await invoke(retained)
    assert minimal_model_environment({'https_proxy':'synthetic-proxy'})=={'https_proxy':'synthetic-proxy'}
    try: minimal_model_environment({'PATH':'one','Path':'two'})
    except NativeWorkerError: pass
    else: raise AssertionError('ambiguous environment accepted')
    print('HERMES_ALIVE_NATIVE_HOST_CALLER_UNIT_OK')


asyncio.run(main())
