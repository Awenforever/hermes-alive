"""Generation/profile/startup guards; fake host and Core accessors only."""
import asyncio
from contextvars import ContextVar
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace
from unittest.mock import patch

repo=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('startup_binding_under_test',repo/'gateway_host_bridge.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

async def main(home):
    current=ContextVar('synthetic_current_home',default=home)
    constants=ModuleType('hermes_constants');constants.get_hermes_home=current.get
    class Context:
        _manager=SimpleNamespace(scope_key=str(home))
        def __init__(self):self.cleanup=[]
        def on_unload(self,fn):self.cleanup.append(fn)
    class Native:
        host=SimpleNamespace(execute=False)
        acquisition={'profile_home':home}
        profile_scope=object()
        calls=0
        def __init__(self):self.finish=asyncio.Event()
        def start(self,context,**arguments):
            self.calls+=1
            async def run():
                await self.finish.wait()
                return {'completed_cycles':1,'exit_reason':'budget'}
            return asyncio.create_task(run())
    with patch.dict(sys.modules,{'hermes_constants':constants}):
        context=Context();binding=module.GatewayHostBinding(context);native=Native()
        assert (await binding.startup())['status']=='not_configured'
        binding.attach(native,build_parameters=lambda:{},max_cycles=1)
        legacy=home/'hooks/hermes-alive/handler.py';legacy.parent.mkdir(parents=True)
        legacy.write_text('synthetic legacy presence, never executed',encoding='utf-8')
        assert (await binding.startup())['status']=='legacy_runtime_present' and native.calls==0
        legacy.unlink()
        blocker=asyncio.create_task(asyncio.Event().wait(),name='hermes-alive-watcher')
        try:assert (await binding.startup())['status']=='legacy_runtime_active' and native.calls==0
        finally:
            blocker.cancel();await asyncio.gather(blocker,return_exceptions=True)
        token=current.set(home/'other-profile')
        foreign=asyncio.create_task(asyncio.Event().wait(),name='hermes-alive-watcher')
        current.reset(token)
        try:
            if hasattr(foreign,'get_context'):
                assert (await binding.startup())['status']=='started'
            else:
                assert (await binding.startup())['status']=='legacy_runtime_active'
        finally:
            foreign.cancel();await asyncio.gather(foreign,return_exceptions=True)
        if not binding.started:assert (await binding.startup())['status']=='started'
        assert (await binding.startup())['status']=='already_started' and native.calls==1
        assert binding.runtime_status()['runtime_active']
        native.finish.set()
        await binding.task
        assert (await binding.startup())['status']=='stopped' and native.calls==1
        assert binding.runtime_status()['exit_reason']=='budget'
        assert not binding.runtime_status()['runtime_active']
        context.cleanup[0]()
        assert (await binding.startup())['status']=='unloaded'
        replacement=module.GatewayHostBinding(Context())
        replacement.attach(Native(),build_parameters=lambda:{},max_cycles=1)
        context.cleanup[0]()
        assert not replacement.closed
        async def terminal(result=None,error=None):
            if error is not None:raise error
            return result
        for result,expected in (({'exit_reason':'stopped'},'stopped'),
                                ({'exit_reason':'paused'},'stopped'),
                                ({'exit_reason':'not_authorized'},'needs_attention'),
                                ({'exit_reason':'cycle_failed'},'failed'),
                                ({'completed_cycles':1},'finished_unknown')):
            replacement.task=asyncio.create_task(terminal(result))
            replacement.started=True
            await replacement.task
            assert (await replacement.startup())['status']==expected
        replacement.task=asyncio.create_task(terminal(error=RuntimeError('private marker')))
        await asyncio.gather(replacement.task,return_exceptions=True)
        observed=await replacement.startup()
        assert observed['status']=='failed' and observed['failure_class']=='RuntimeError'
        assert 'private marker' not in str(observed)
        replacement.task=asyncio.create_task(asyncio.Event().wait())
        replacement.native.pending=(object(),)
        replacement.task.cancel()
        await asyncio.gather(replacement.task,return_exceptions=True)
        observed=await replacement.startup()
        assert observed['status']=='cancelled' and observed['pending_work_count']==1
        assert replacement.native.calls==0  # reads never relaunch a terminal host
        replacement.task=asyncio.create_task(asyncio.Event().wait())
        replacement.close()
        assert replacement.runtime_status()['status']=='stopping'
        replacement.task.cancel()
        await asyncio.gather(replacement.task,return_exceptions=True)
        assert replacement.runtime_status()['status']=='unloaded'
        current.set(home/'foreign')
        try:await replacement.startup()
        except ValueError:pass
        else:raise AssertionError('foreign profile startup accepted')

with tempfile.TemporaryDirectory(prefix='alive-startup-binding-') as folder:
    asyncio.run(main(Path(folder)))
print('HERMES_ALIVE_GATEWAY_HOST_BINDING_UNIT_OK')
