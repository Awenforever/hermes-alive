"""Core-supervised native host unload/recovery, synthetic HTTP, no real sends."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from datetime import datetime,timezone

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--core',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
home=a.output/'profile';home.mkdir(mode=0o700)
workers=a.output/'workers';workers.mkdir(mode=0o700)
os.environ['HERMES_HOME']=str(home)
package=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(a.core.resolve(strict=True)),str(package/'hooks'),str(package/'__tests__')]
configuration=dict(model=dict(default='configured-primary',provider='custom:owner'),
    custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
        key_env='OWNER_MAIN_KEY',api_mode='chat_completions')],
    model_aliases={'hold':dict(model='hold-primary',provider='custom',base_url='https://provider.invalid/v1',key_env='OWNER_MAIN_KEY')},
    fallback_providers=[],agent=dict(reasoning_effort=False))
(home/'config.yaml').write_text(json.dumps(configuration),encoding='utf-8')
(home/'.env').write_text('OWNER_MAIN_KEY=PRIVATE_MAIN_KEY\n',encoding='utf-8')

async def main():
    from hermes_cli.plugins import PluginContext,PluginManager,PluginManifest
    from hermes_cli.config import load_config_readonly
    from tui_gateway.launch_profile_policy import launch_profile_runtime_scope
    from alive_kernel import AutonomyPolicyProjection,PolicyContext,DiscoveryCandidate,DiscoveryOpportunityIngestor
    from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
    from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
    from alive_kernel.native_cognition_host import NativeCognitionHost
    from alive_kernel.native_worker_protocol import NativeWorkerError
    from alive_kernel.native_core_scope import core_profile_cycle_scope
    from probe_alive_live_feedback import prepare_case
    fixture,owner,_=prepare_case(a.output/'kernel',dict(id='supervised-native-host',
        sent='Synthetic earlier message.',reply='SYNTHETIC_CONTEXT_156: no permanent inference authorized.'))
    journal=fixture.journal;vault=fixture.vault
    policies=AutonomyPolicyProjection(journal)
    def policy(enabled,operation):
        current=policies.current(owner)
        policies.apply(policies.append_update(subject=owner,actor=owner,
            expected_revision=current.revision if current else 0,enabled=enabled,
            context=PolicyContext(can_interrupt=True),operation_id=operation))
    policy(True,'enable-supervised')
    reader=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    def observe(summary):
        reader.ingest(DiscoveryCandidate(source='synthetic',title='SYNTHETIC_CONTEXT_156',summary=summary,
            url='https://example.invalid/supervised-native',observed_at=datetime.now(timezone.utc)),subject=owner)
    observe('SYNTHETIC_CONTEXT_156: first public observation.')
    host=AutonomousHostRuntime(AutonomousCycleRuntime(journal,content_vault=vault),subject=owner,
        configuration_id='supervised-native')
    native=NativeCognitionHost(host,profile_id='profile:synthetic',profile_home=home,
        read_configuration=load_config_readonly,read_credential_names=lambda **_:('OWNER_MAIN_KEY',),
        interpreter=sys.executable,core=a.core,private_root=workers,environment=dict(os.environ),
        resolve_domain=lambda *labels:'synthetic-family',identity='SYNTHETIC_PERSONA_156',
        entrypoint=package/'tests/fixtures/native-worker-http-bootstrap.py',timeout_seconds=60,
        profile_scope=lambda:core_profile_cycle_scope(home))
    manifest=PluginManifest(name='alive_supervision_probe',version='0',description='',source='user')
    def manager_context():
        manager=PluginManager(scope_key=str(home.resolve()))
        return manager,PluginContext(manifest,manager)
    manager,ctx=manager_context()
    def start(ctx,parameters,max_cycles=1):
        with launch_profile_runtime_scope(home):
            return native.start(ctx,build_parameters=lambda:parameters,stop=asyncio.Event(),
                max_cycles=max_cycles,interval_seconds=0)
    held=dict(expression_parameters={'requested_model':'hold'},resolve_binding=lambda _:None)
    task=start(ctx,held)
    try:
        deadline=asyncio.get_running_loop().time()+45
        while not list(workers.glob('alive-native-worker-*/worker/scope-test-ready')):
            if task.done():
                await task
                raise AssertionError('host returned without controlled in-flight native request')
            if asyncio.get_running_loop().time()>deadline:
                raise AssertionError('supervised worker never reached controlled request')
            await asyncio.sleep(.05)
        opened=host.open_cycle()
        try:start(ctx,held)
        except NativeWorkerError:pass
        else:raise AssertionError('duplicate supervised task accepted')
        assert manager.unload('alive_supervision_probe') is True
        try:await task
        except asyncio.CancelledError:pass
        else:raise AssertionError('Core unload did not cancel the host')
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
    await asyncio.sleep(0)
    assert 'alive_supervision_probe' not in manager._ownership_ledger
    assert not host.running and not native.pending and not list(workers.iterdir())
    assert journal.get(opened.event_id+':closed') is None
    assert host.open_cycle().operation_id==opened.operation_id
    started=len(journal.read(event_type='opportunity.synthesis_started'))
    assert started==1
    # A consumed interrupted inference is not silently retried under the same ID.
    manager2,ctx2=manager_context()
    result=await start(ctx2,held)
    assert result['exit_reason']=='cycle_failed' and result['completed_cycles']==0
    assert len(journal.read(event_type='opportunity.synthesis_started'))==started
    assert native.last_call_count==0 and journal.get(opened.event_id+':closed') is None
    # Explicit owner pause closes that retained cycle without spending again.
    policy(False,'pause-for-explicit-recovery')
    result=await start(ctx2,held)
    assert result['completed_cycles']==1 and journal.get(opened.event_id+':closed')
    assert native.last_call_count==0
    policy(True,'resume-after-explicit-recovery')
    observe('SYNTHETIC_CONTEXT_156: materially updated public observation.')
    parameters=dict(expression_parameters={},resolve_binding=lambda _:None,reconsider_after_seconds=300)
    result=await start(ctx2,parameters,max_cycles=2)
    assert result['completed_cycles']==2 and result['exit_reason']=='budget'
    assert len(journal.read(event_type='opportunity.synthesis_started'))==started+1
    assert not native.pending and not list(workers.iterdir()) and not host.running
    await asyncio.sleep(0)
    assert 'alive_supervision_probe' not in manager2._ownership_ledger
    report=dict(real_core_supervisor=True,unload_cancelled_inflight_worker=True,
        expired_task_ledger_empty=True,interrupted_cycle_retained=True,automatic_inference_retry=False,
        explicit_pause_recovery=True,resumed_completed_cycles=2,actual_model_inference=False,
        physical_sends=0,production_startup_installed=False)
    (a.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('HERMES_ALIVE_CORE_SUPERVISED_HOST_OK '+json.dumps(report))
asyncio.run(main())
