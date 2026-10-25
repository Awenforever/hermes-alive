"""Installed public plugin + actual Core disk startup hook; controlled HTTP only."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
launch=a.output/'launch';launch.mkdir(mode=0o700)
routed=launch/'profiles/beta';routed.mkdir(mode=0o700,parents=True)
os.environ['HERMES_HOME']=str(launch)
package=Path(__file__).resolve().parents[1];repo=package.parents[1]
sys.path[:0]=[str(a.core.resolve(strict=True)),str(package/'hooks'),str(package/'__tests__')]
config=dict(model=dict(default='configured-primary',provider='custom:owner'),
    custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
        key_env='OWNER_MAIN_KEY',api_mode='chat_completions')],fallback_providers=[],agent=dict(reasoning_effort=False),
    model_aliases={'hold':dict(model='hold-primary',provider='custom',base_url='https://provider.invalid/v1',key_env='OWNER_MAIN_KEY')},
    plugins={'enabled':['hermes-alive']})
for home in (launch,routed):
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    (home/'.env').write_text('OWNER_MAIN_KEY=PRIVATE_MAIN_KEY\n',encoding='utf-8')
    shutil.copytree(repo,home/'plugins/hermes-alive',ignore=shutil.ignore_patterns('.git','__pycache__'))
    hook=home/'hooks/hermes-alive-kernel';hook.mkdir(parents=True)
    (hook/'HOOK.yaml').write_text('name: hermes-alive-kernel\nevents: [gateway:startup]\n',encoding='utf-8')
    shutil.copyfile(package/'hooks/kernel_gateway_handler.py',hook/'handler.py')

async def main():
    from hermes_cli.plugins import get_plugin_manager
    from hermes_cli.config import load_config_readonly
    from gateway.hooks import HookRegistry
    from gateway.run import _profile_runtime_scope
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from alive_kernel import AutonomyPolicyProjection,PolicyContext,DiscoveryCandidate,DiscoveryOpportunityIngestor
    from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
    from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
    from alive_kernel.native_cognition_host import NativeCognitionHost
    from alive_kernel.native_core_scope import core_profile_cycle_scope
    from probe_alive_live_feedback import prepare_case
    modules=[];previous_native=None
    for home in (launch,routed):
        scope=launch_profile_runtime_scope(home) if home==launch else _profile_runtime_scope(home)
        with scope:
            manager=get_plugin_manager();manager.discover_and_load()
            installed=manager._plugins.get('hermes-alive')
            assert installed is not None and installed.enabled,manager.list_plugins()
            module=installed.module;modules.append(module.__name__)
            assert Path(module.__file__).resolve()==(home/'plugins/hermes-alive/__init__.py').resolve()
            registry=HookRegistry();registry.discover_and_load()
            assert len(registry.loaded_hooks)==1
            result=await registry.emit_collect('gateway:startup',{'platforms':[]})
            assert result==[{'status':'not_configured','legacy_allowed':False}]
            if previous_native is not None:
                try:module.configure_kernel_gateway_host(previous_native,build_parameters=lambda:{},max_cycles=1)
                except ValueError:pass
                else:raise AssertionError('foreign profile native host attached')
            case=a.output/('case-'+home.name);case.mkdir(mode=0o700)
            fixture,owner,_=prepare_case(case/'kernel',dict(id='startup-'+home.name,
                sent='Synthetic earlier message.',reply='SYNTHETIC_CONTEXT_156: synthetic only.'))
            journal=fixture.journal;policies=AutonomyPolicyProjection(journal);current=policies.current(owner)
            policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=current.revision,
                enabled=True,context=PolicyContext(can_interrupt=True),operation_id='startup-enable'))
            DiscoveryOpportunityIngestor(journal,content_vault=fixture.vault).ingest(DiscoveryCandidate(source='synthetic',
                title='SYNTHETIC_CONTEXT_156 public observation',summary='SYNTHETIC_CONTEXT_156: an uncertain nonurgent source.',
                url='https://example.invalid/startup',observed_at=datetime.now(timezone.utc)),subject=owner)
            workers=case/'workers';workers.mkdir(mode=0o700)
            host=AutonomousHostRuntime(AutonomousCycleRuntime(journal,content_vault=fixture.vault),
                subject=owner,configuration_id='installed-startup')
            native=NativeCognitionHost(host,profile_id='profile:'+home.name,profile_home=home,
                read_configuration=load_config_readonly,read_credential_names=lambda **_:('OWNER_MAIN_KEY',),
                interpreter=sys.executable,core=a.core,private_root=workers,environment=dict(os.environ),
                resolve_domain=lambda *labels:'synthetic',identity='SYNTHETIC_PERSONA_156',
                entrypoint=package/'tests/fixtures/native-worker-http-bootstrap.py',timeout_seconds=60,
                profile_scope=lambda home=home:core_profile_cycle_scope(home))
            expression={'requested_model':'hold'} if home==launch else {}
            module.configure_kernel_gateway_host(native,build_parameters=lambda:dict(
                expression_parameters=expression,resolve_binding=lambda _:None),max_cycles=1,interval_seconds=0)
            result=await registry.emit_collect('gateway:startup',{'platforms':[]})
            assert result[0]['status']=='started' and result[0]['legacy_allowed'] is False
            task=module._gateway_host_binding.task
            assert (await registry.emit_collect('gateway:startup',{}))[0]['status']=='already_started'
            assert module._gateway_host_binding.task is task
            if home==launch:
                deadline=asyncio.get_running_loop().time()+45
                while not list(workers.glob('alive-native-worker-*/worker/scope-test-ready')):
                    if task.done():await task;raise AssertionError('startup task ended before held request')
                    if asyncio.get_running_loop().time()>deadline:raise AssertionError('startup worker never became active')
                    await asyncio.sleep(.05)
                opened=host.open_cycle()
                assert manager.unload('hermes-alive') is True
                try:await task
                except asyncio.CancelledError:pass
                else:raise AssertionError('installed plugin unload did not cancel native task')
                assert journal.get(opened.event_id+':closed') is None
            else:
                assert (await task)['completed_cycles']==1
                assert (await registry.emit_collect('gateway:startup',{}))[0]['status']=='already_started'
                assert manager.unload('hermes-alive') is True
            assert (await module.kernel_gateway_startup())['status']=='unloaded'
            assert (await registry.emit_collect('gateway:startup',{}))[0]['status']=='plugin_unavailable'
            await asyncio.sleep(0)
            assert not native.pending and not list(workers.iterdir()) and not host.running
            assert 'hermes-alive' not in manager._ownership_ledger
            previous_native=native
    assert len(set(modules))==2
    report=dict(installed_public_plugin=True,actual_disk_startup_hook=True,profiles=2,
        duplicate_start_rejected=True,cross_profile_attach_rejected=True,unload_stops_inflight=True,
        old_watcher_started=False,actual_model_inference=False,physical_sends=0,
        automatic_host_assembly_proven=False,default_installer_selection_proven=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_INSTALLED_GATEWAY_STARTUP_OK '+json.dumps(report))
asyncio.run(main())
