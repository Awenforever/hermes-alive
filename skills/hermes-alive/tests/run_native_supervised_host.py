"""Portable supervised-loop composition; fake supervisor/driver, no model calls."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import tempfile

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'hooks'),str(Path(__file__).resolve().parent)]
from run_autonomous_host_runtime import Driver
from alive_kernel import ExperienceJournal
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
from alive_kernel.native_cognition_host import NativeCognitionHost
from alive_kernel.native_worker_protocol import NativeWorkerError

async def main(root):
    scope={'active':False,'entered':0,'exited':0}
    @asynccontextmanager
    async def profile_scope():
        assert not scope['active']
        scope['active']=True;scope['entered']+=1
        try:yield
        finally:scope['active']=False;scope['exited']+=1
    class BoundDriver(Driver):
        def __init__(self,journal):
            super().__init__(journal);self.callers=[]
        async def cycle(self,**kwargs):
            assert scope['active']
            caller=kwargs['expression_parameters']['call']
            assert caller.operation_id==kwargs['operation_id']
            self.callers.append(caller)
            result=await super().cycle(**kwargs)
            if getattr(self,'stop_after',None)==len(self.operations):self.stop.set()
            return result
    class Supervisor:
        def spawn_task(self,coro,*,name):return asyncio.create_task(coro,name=name)
    driver=BoundDriver(ExperienceJournal(root/'journal.sqlite3'))
    host=AutonomousHostRuntime(driver,subject='user:synthetic',configuration_id='supervised-test')
    native=NativeCognitionHost(host,profile_id='profile:synthetic',profile_home=root,
        read_configuration=lambda:{},read_credential_names=lambda **_:(),interpreter=sys.executable,
        core=root,private_root=root,environment={},resolve_domain=lambda *labels:'synthetic',profile_scope=profile_scope)
    supervisor=Supervisor()
    kwargs=dict(build_parameters=lambda:{'expression_parameters':{}},stop=asyncio.Event(),
        max_cycles=2,interval_seconds=0)
    task=native.start(supervisor,**kwargs)
    try:native.start(supervisor,**kwargs)
    except NativeWorkerError:pass
    else:raise AssertionError('duplicate scheduled task accepted')
    result=await task
    assert result['completed_cycles']==2 and result['exit_reason']=='budget'
    assert len(driver.callers)==2 and driver.callers[0] is not driver.callers[1]
    assert len(set(driver.operations))==2 and not host.running
    assert scope=={'active':False,'entered':2,'exited':2}
    driver.block=True;driver.entered.clear()
    task=native.start(supervisor,**kwargs)
    await driver.entered.wait()
    try:await native.run(**kwargs)
    except NativeWorkerError:pass
    else:raise AssertionError('overlapping native loop accepted')
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass
    else:raise AssertionError('cancellation became success')
    assert driver.cleaned and not host.running and not native.pending
    assert scope=={'active':False,'entered':3,'exited':3}
    assert host.open_cycle().operation_id==driver.operations[-1]
    driver.block=False
    result=await native.start(supervisor,**kwargs)
    assert result['completed_cycles']==2 and not host.running
    assert scope=={'active':False,'entered':5,'exited':5}
    class FailingSupervisor:
        def spawn_task(self,coro,*,name):raise RuntimeError('synthetic host start refusal')
    try:native.start(FailingSupervisor(),**kwargs)
    except RuntimeError:pass
    else:raise AssertionError('host start failure suppressed')
    live_driver=BoundDriver(ExperienceJournal(root/'continuous.sqlite3'))
    live_host=AutonomousHostRuntime(live_driver,subject='user:continuous',
                                   configuration_id='continuous-test',execute=True)
    live=NativeCognitionHost(live_host,profile_id='profile:synthetic',profile_home=root,
        read_configuration=lambda:{},read_credential_names=lambda **_:(),interpreter=sys.executable,
        core=root,private_root=root,environment={},resolve_domain=lambda *labels:'synthetic',
        profile_scope=profile_scope)
    live_driver.stop=asyncio.Event();live_driver.stop_after=2
    result=await live.start(supervisor,build_parameters=lambda:{'expression_parameters':{}},
        stop=live_driver.stop,continuous=True,interval_seconds=.001)
    assert result['completed_cycles']==2 and result['exit_reason']=='stopped'
    assert len(live_driver.callers)==2 and live_driver.callers[0] is not live_driver.callers[1]
    assert len(set(live_driver.operations))==2 and not live_host.running and not live.pending
    assert scope=={'active':False,'entered':7,'exited':7}

with tempfile.TemporaryDirectory(prefix='alive-native-supervision-') as folder:
    asyncio.run(main(Path(folder)))
print('HERMES_ALIVE_NATIVE_SUPERVISED_HOST_UNIT_OK')
