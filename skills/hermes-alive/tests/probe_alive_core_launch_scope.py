"""Actual Core launch/routed profile scopes -> native worker; offline HTTP only."""
import argparse
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
launch=a.output/'launch';launch.mkdir(mode=0o700)
routed=launch/'profiles/beta';routed.mkdir(mode=0o700,parents=True)
workers=a.output/'workers';workers.mkdir(mode=0o700)
# Set the synthetic process home before importing Core; never touch real homes.
os.environ['HERMES_HOME']=str(launch)
os.environ['OWNER_MAIN_KEY']='FOREIGN_AMBIENT_NOT_ALLOWED'
package=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(a.core.resolve(strict=True)),str(package/'hooks')]
configuration=dict(model=dict(default='configured-primary',provider='custom:owner'),
    custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
        key_env='OWNER_MAIN_KEY',api_mode='chat_completions')],fallback_providers=[],agent=dict(reasoning_effort=False))
for home in (launch,routed):
    (home/'config.yaml').write_text(json.dumps(configuration),encoding='utf-8')
    (home/'.env').write_text('OWNER_MAIN_KEY=PRIVATE_MAIN_KEY\n',encoding='utf-8')

async def main():
    from agent.secret_scope import (current_secret_scope,current_secret_scope_home,set_secret_scope,
        reset_secret_scope,set_multiplex_context,reset_multiplex_context)
    from hermes_constants import (get_hermes_home_override,set_hermes_home_override,
        reset_hermes_home_override,get_routing_process_hermes_home)
    from hermes_cli.config import load_config_readonly
    from gateway.run import _profile_runtime_scope
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
    from alive_kernel.native_host_caller import HostModelBinding,HostNativeCaller
    from alive_kernel.native_worker_protocol import NativeWorkerError
    assert Path(get_routing_process_hermes_home()).resolve()==launch.resolve()
    baseline=dict(os.environ)
    acquired=[];calls=0
    def acquire_for(home):
        return CoreScopedModelAcquirer(profile_home=home,
            read_binding=lambda:HostModelBinding('user:synthetic','profile:'+home.name,'operation:scope','generation:1'),
            read_configuration=load_config_readonly,read_credential_names=lambda **_:('OWNER_MAIN_KEY',),
            identity='SYNTHETIC_PERSONA_156: profile scope wiring only.')
    async def invoke(home):
        nonlocal calls
        acquire=acquire_for(home)
        capability=acquire(task='synthetic',model=None);acquired.append(capability)
        assert capability.read_secret(capability.binding,'OWNER_MAIN_KEY')=='PRIVATE_MAIN_KEY'
        caller=HostNativeCaller(subject=capability.binding.subject,profile_id=capability.binding.profile_id,
            operation_id=capability.binding.operation_id,acquire=acquire,interpreter=sys.executable,
            core=a.core,private_root=workers,environment=dict(os.environ),
            entrypoint=package/'tests/fixtures/native-worker-http-bootstrap.py',timeout_seconds=60)
        result=await caller(task='synthetic',model=None,messages=[dict(role='system',content='SYNTHETIC_TASK_156'),
            dict(role='user',content='SYNTHETIC_CONTEXT_156')],temperature=.2,max_tokens=256)
        assert result.model=='served-label/configured-primary'
        assert not caller.pending and not list(workers.iterdir())
        calls+=caller.calls
    def rejected(home):
        try: acquire_for(home)(task='synthetic',model=None)
        except NativeWorkerError: return
        raise AssertionError('unbound or foreign profile scope accepted')
    for multiplex in (False,True):
        with ExitStack() as stack:
            token=set_multiplex_context(multiplex);stack.callback(reset_multiplex_context,token)
            # Actual Core launch binder deliberately omits the optional secret stamp.
            with launch_profile_runtime_scope(launch):
                assert current_secret_scope_home() is None
                assert Path(get_hermes_home_override()).resolve()==launch.resolve()
                await invoke(launch)
                launch_mapping=current_secret_scope()
                # A launch secret mapping is never authority for a routed profile.
                token=set_hermes_home_override(routed)
                try: rejected(routed)
                finally: reset_hermes_home_override(token)
                token=set_secret_scope(launch_mapping,profile_home=str(routed))
                try: rejected(launch)
                finally: reset_secret_scope(token)
                token=set_secret_scope(None)
                try: rejected(launch)
                finally: reset_secret_scope(token)
            with _profile_runtime_scope(routed,{'OWNER_MAIN_KEY':'PRIVATE_MAIN_KEY'}):
                await invoke(routed)
                rejected(launch)
            rejected(launch)
            token=set_secret_scope({'OWNER_MAIN_KEY':'PRIVATE_MAIN_KEY'})
            try: rejected(launch)  # Correct process home alone does not bind a scope.
            finally: reset_secret_scope(token)
            assert all(not cap.is_current(cap.binding) for cap in acquired)
    assert dict(os.environ)==baseline
    report=dict(core_launch_modes=2,routed_modes=2,controlled_native_calls=calls,
        actual_model_inference=False,physical_sends=0,unbound_and_foreign_rejected=True,
        expired_capabilities_rejected=True,ambient_environment_unchanged=True,
        production_installation_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_CORE_LAUNCH_SCOPE_OK '+json.dumps(report))
asyncio.run(main())
