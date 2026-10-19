"""Real Core key rotation between native host cycles; no model or network calls."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
launch=a.output/'launch';launch.mkdir(mode=0o700)
routed=launch/'profiles/beta';routed.mkdir(mode=0o700,parents=True)
os.environ['HERMES_HOME']=str(launch)
package=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(a.core.resolve(strict=True)),str(package/'hooks')]
config={'model':{'default':'synthetic','provider':'custom:owner'}}
for home in (launch,routed):
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    (home/'.env').write_text('OWNER_KEY=SYNTHETIC_INITIAL\n',encoding='utf-8')

async def main():
    from hermes_cli.config import load_config_readonly
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from gateway.run import _profile_runtime_scope
    from agent.secret_scope import current_secret_scope,set_secret_scope,reset_secret_scope
    from alive_kernel import DispatchOutbox,ExperienceJournal
    from alive_kernel.native_cognition_host import NativeCognitionHost
    from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
    from alive_kernel.native_core_scope import core_profile_cycle_scope
    from alive_kernel.native_worker_protocol import NativeWorkerError
    baseline=dict(os.environ)
    class Driver:
        def __init__(self,home,label):
            self.outbox=DispatchOutbox(ExperienceJournal(a.output/(label+'.sqlite3')))
            self.home=home;self.observed=[];self.caps=[]
            self.reconciliation=SimpleNamespace(_owner_policy=lambda _:SimpleNamespace(enabled=True,event_id='synthetic-policy',revision=1))
        async def cycle(self,**values):
            caller=values['expression_parameters']['call']
            cap=caller.acquire(task='synthetic',model=None)
            self.caps.append(cap)
            self.observed.append(cap.read_secret(cap.binding,'OWNER_KEY'))
            if len(self.observed)==1:
                (self.home/'.env').write_text('OWNER_KEY=SYNTHETIC_ROTATED_LONGER\n',encoding='utf-8')
            return SimpleNamespace(disposition='silence',reconciliation={'next_after_sequence':0},external_delivery_proven=False)
    results={}
    for home in (launch,routed):
        for refreshed in (False,True):
            label=home.name+('-refresh' if refreshed else '-startup-only')
            (home/'.env').write_text('OWNER_KEY=SYNTHETIC_INITIAL\n',encoding='utf-8')
            driver=Driver(home,label)
            host=AutonomousHostRuntime(driver,subject='user:synthetic',configuration_id=label)
            native=NativeCognitionHost(host,profile_id='profile:'+home.name,profile_home=home,
                read_configuration=load_config_readonly,read_credential_names=lambda **_:('OWNER_KEY',),
                interpreter=sys.executable,core=a.core,private_root=a.output,environment={},
                resolve_domain=lambda *labels:'synthetic',
                profile_scope=(lambda home=home:core_profile_cycle_scope(home)) if refreshed else None)
            scope=launch_profile_runtime_scope(home) if home==launch else _profile_runtime_scope(home)
            with scope:
                startup_mapping=current_secret_scope()
                result=await native.run(build_parameters=lambda:dict(expression_parameters={}),
                    stop=asyncio.Event(),max_cycles=2,interval_seconds=0)
                assert result['completed_cycles']==2
                assert current_secret_scope() is startup_mapping
                assert startup_mapping.get('OWNER_KEY')=='SYNTHETIC_INITIAL'
                expected=['SYNTHETIC_INITIAL','SYNTHETIC_ROTATED_LONGER' if refreshed else 'SYNTHETIC_INITIAL']
                assert driver.observed==expected
                if refreshed:
                    assert all(not cap.is_current(cap.binding) for cap in driver.caps)
            results[label]=dict(rotation_visible=refreshed,cycles=2)
    with launch_profile_runtime_scope(launch):
        try:
            async with core_profile_cycle_scope(routed):pass
        except NativeWorkerError:pass
        else:raise AssertionError('scope factory switched to another profile')
        token=set_secret_scope({'OWNER_KEY':'synthetic-foreign'},profile_home=str(routed))
        try:
            try:
                async with core_profile_cycle_scope(launch):pass
            except NativeWorkerError:pass
            else:raise AssertionError('foreign stamp was overwritten')
        finally:reset_secret_scope(token)
    assert dict(os.environ)==baseline
    report=dict(cases=results,real_core_loaders=True,actual_model_calls=0,physical_sends=0,
        foreign_scope_rejected=True,parent_scope_restored=True,environment_unchanged=True,
        production_startup_installed=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_CORE_CYCLE_SCOPE_OK '+json.dumps(report))
asyncio.run(main())
