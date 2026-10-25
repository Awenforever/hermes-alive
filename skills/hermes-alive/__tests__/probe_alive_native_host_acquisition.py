"""Actual Core scopes -> parent acquisition -> native child; synthetic HTTP only."""
import argparse
import asyncio
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core',type=Path,required=True)
args=parser.parse_args()
core=args.core.resolve(strict=True)
package=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(core),str(package/'hooks'),str(package/'__tests__')]


async def exercise(root):
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    from agent.secret_scope import set_secret_scope,reset_secret_scope,set_multiplex_context,reset_multiplex_context
    from alive_kernel.native_host_caller import HostModelBinding,HostNativeCaller
    from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
    from alive_kernel.native_worker_protocol import NativeWorkerError
    home=root/'host'; home.mkdir()
    workers=root/'workers'; workers.mkdir()
    original=dict(os.environ)
    secrets={'OWNER_MAIN_KEY':'PRIVATE_MAIN_KEY','OWNER_BACKUP_KEY':'PRIVATE_FALLBACK_KEY',
        'UNRELATED_MAIL_SECRET':'not-a-model-capability'}
    configuration=dict(model=dict(default='configured-primary',provider='custom:owner'),
        custom_providers=[dict(name='owner',model='configured-primary',base_url='https://provider.invalid/v1',
            key_env='OWNER_MAIN_KEY',api_mode='chat_completions'),
            dict(name='backup',model='configured-backup',base_url='https://backup.invalid/v1',
            key_env='OWNER_BACKUP_KEY',api_mode='chat_completions')],
        model_aliases=dict(chosen=dict(model='configured-other',provider='custom',
            base_url='https://provider.invalid/v1',key_env='OWNER_MAIN_KEY'),
            failover=dict(model='fail-primary',provider='custom',
            base_url='https://provider.invalid/v1',key_env='OWNER_MAIN_KEY')),
        fallback_providers=[dict(provider='custom:backup',model='configured-backup',key_env='OWNER_BACKUP_KEY')],
        agent=dict(reasoning_effort=False,max_iterations=999),
        plugins={'private':'must-not-be-copied'},memory={'private':'must-not-be-copied'})
    current=[HostModelBinding('user:synthetic','profile:synthetic','operation:acquire','generation:1')]
    granted=[('OWNER_MAIN_KEY','OWNER_BACKUP_KEY')]
    with ExitStack() as stack:
        token=set_hermes_home_override(home); stack.callback(reset_hermes_home_override,token)
        token=set_multiplex_context(True); stack.callback(reset_multiplex_context,token)
        token=set_secret_scope(secrets,profile_home=str(home)); stack.callback(reset_secret_scope,token)
        acquire=CoreScopedModelAcquirer(profile_home=home,read_binding=lambda:current[0],
            read_configuration=lambda:configuration,
            read_credential_names=lambda **_:granted[0],
            identity='SYNTHETIC_PERSONA_156: concise and candid.')
        capability=acquire(task='synthetic',model=None)
        assert 'plugins' not in capability.configuration and 'memory' not in capability.configuration
        assert capability.configuration['agent']=={'reasoning_effort':False}
        assert capability.is_current(capability.binding)
        granted[0]=()
        assert not capability.is_current(capability.binding)
        try: capability.read_secret(capability.binding,'OWNER_MAIN_KEY')
        except NativeWorkerError: pass
        else: raise AssertionError('revoked model credential grant remained readable')
        granted[0]=('OWNER_MAIN_KEY','OWNER_BACKUP_KEY')
        configuration['model']['default']='changed'
        assert not capability.is_current(capability.binding)
        configuration['model']['default']='configured-primary'
        secrets['OWNER_MAIN_KEY']='rotated'
        assert not capability.is_current(capability.binding)
        secrets['OWNER_MAIN_KEY']='PRIVATE_MAIN_KEY'
        current[0]=replace(current[0],revision='generation:2')
        assert not capability.is_current(capability.binding)  # lifecycle generation defeats ABA.
        binding=current[0]
        caller=HostNativeCaller(subject=binding.subject,profile_id=binding.profile_id,
            operation_id=binding.operation_id,acquire=acquire,interpreter=sys.executable,
            core=core,private_root=workers,environment={**os.environ,'OWNER_MAIN_KEY':'foreign-ambient'},
            entrypoint=package/'tests/fixtures/native-worker-http-bootstrap.py',timeout_seconds=60)
        params=dict(task='synthetic',model=None,messages=[dict(role='system',content='SYNTHETIC_TASK_156'),
            dict(role='user',content='SYNTHETIC_CONTEXT_156')],temperature=.2,max_tokens=256)
        for model,expected in ((None,'configured-primary'),('chosen','configured-other'),('failover','configured-backup')):
            result=await caller(**{**params,'model':model})
            assert result.model=='served-label/'+expected
            assert not caller.pending and not list(workers.iterdir())
        print('HERMES_ALIVE_CORE_ACQUISITION_DEFAULT_ALIAS_FALLBACK_OK',flush=True)
        configuration['model_aliases']['hold']=dict(model='hold-primary',provider='custom',
            base_url='https://provider.invalid/v1',key_env='OWNER_MAIN_KEY')
        active=asyncio.create_task(caller(**{**params,'model':'hold'}))
        try:
            deadline=asyncio.get_running_loop().time()+45
            while not list(workers.glob('alive-native-worker-*/worker/scope-test-ready')):
                if active.done():
                    await active
                    raise AssertionError('worker completed without controlled hold')
                if asyncio.get_running_loop().time()>deadline:
                    raise AssertionError('native child did not reach controlled request')
                await asyncio.sleep(.05)
            marker=next(workers.glob('alive-native-worker-*/worker/scope-test-ready'))
            current[0]=replace(current[0],revision='generation:revoked-during-call')
            marker.with_name('scope-test-release').touch()
            try: await active
            except NativeWorkerError: pass
            else: raise AssertionError('revoked in-flight model result accepted')
            assert not caller.pending and not list(workers.iterdir())
            print('HERMES_ALIVE_CORE_ACQUISITION_INFLIGHT_REVOCATION_OK',flush=True)
        finally:
            if not active.done():
                active.cancel()
                try: await active
                except asyncio.CancelledError: pass
                await caller.reap_pending(timeout_seconds=5)
        token=set_secret_scope(secrets,profile_home=str(root/'foreign'))
        try:
            try: acquire(task='synthetic',model=None)
            except NativeWorkerError: pass
            else: raise AssertionError('foreign scope accepted')
        finally: reset_secret_scope(token)
        token=set_secret_scope(None)
        try:
            try: acquire(task='synthetic',model=None)
            except NativeWorkerError: pass
            else: raise AssertionError('ambient credentials accepted without scope')
        finally: reset_secret_scope(token)

        from probe_alive_live_feedback import prepare_case
        from alive_kernel import AutonomyPolicyProjection,DiscoveryCandidate,DiscoveryOpportunityIngestor,PolicyContext
        from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
        interpreter,owner,_=prepare_case(root/'canonical',dict(id='native-host-acquisition',sent='Synthetic prior source.',
            reply='SYNTHETIC_CONTEXT_156: I am busy today, not permanently uninterested.'))
        journal=interpreter.journal
        policies=AutonomyPolicyProjection(journal); policies.project_new(); policy=policies.current(owner)
        assert policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=policy.revision,
            enabled=True,context=PolicyContext(can_interrupt=True),operation_id='acquire-enable')).outcome=='recorded'
        DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(source='synthetic',
            title='SYNTHETIC_CONTEXT_156 public observation',summary='An uncertain nonurgent reading lead.',
            url='https://example.invalid/native-acquisition',observed_at=datetime.now(timezone.utc)),subject=owner)
        current[0]=HostModelBinding(owner,binding.profile_id,'operation:canonical','generation:3')
        canonical=HostNativeCaller(subject=owner,profile_id=binding.profile_id,operation_id='operation:canonical',
            acquire=acquire,interpreter=sys.executable,core=core,private_root=workers,environment=dict(os.environ),
            entrypoint=package/'tests/fixtures/native-worker-http-bootstrap.py',timeout_seconds=60)
        runtime=AutonomousCycleRuntime(journal,content_vault=interpreter.vault)
        arguments=dict(subject=owner,expression_parameters=dict(call=canonical,
            resolve_domain=lambda provider,model:'synthetic-family'),resolve_binding=lambda _:None)
        assert (await runtime.cycle(operation_id='acquire-shadow',**arguments)).disposition=='silence'
        assert (await runtime.cycle(operation_id='acquire-shadow',**arguments)).disposition=='silence'
        assert canonical.calls==1 and not canonical.pending and not list(workers.iterdir())
        assert dict(os.environ)==original
        print('HERMES_ALIVE_CORE_ACQUISITION_CANONICAL_REPLAY_OK',flush=True)
        from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
        from alive_kernel.native_cognition_host import NativeCognitionHost
        from alive_kernel.opportunity_synthesis import OpportunitySynthesisError
        durable=AutonomousHostRuntime(runtime,subject=owner,configuration_id='native-cognition-host')
        wired=NativeCognitionHost(durable,profile_id='profile:synthetic',profile_home=home,
            read_configuration=lambda:configuration,
            read_credential_names=lambda **_:('OWNER_MAIN_KEY','OWNER_BACKUP_KEY'),
            interpreter=sys.executable,core=core,private_root=workers,environment=dict(os.environ),
            resolve_domain=lambda provider,model:'synthetic-family',
            identity='SYNTHETIC_PERSONA_156: concise and candid.',
            entrypoint=package/'tests/fixtures/native-worker-http-bootstrap.py',timeout_seconds=60)
        opened=durable.open_cycle()
        parameters=dict(expression_parameters={},resolve_binding=lambda _:None,reconsider_after_seconds=300)
        result=await wired.step(parameters)
        assert result.disposition=='silence' and wired.last_call_count==1
        assert not wired.pending and not list(workers.iterdir())
        assert journal.get(opened.event_id+':closed') is not None
        replay=await wired.step(parameters)
        assert replay.disposition in ('silence','waiting_for_change') and wired.last_call_count==0
        active=asyncio.create_task(wired.step(dict(expression_parameters={'requested_model':'hold'},
            resolve_binding=lambda _:None)))
        try:
            deadline=asyncio.get_running_loop().time()+45
            while not list(workers.glob('alive-native-worker-*/worker/scope-test-ready')):
                if active.done():
                    await active
                    raise AssertionError('native host returned without controlled hold')
                if asyncio.get_running_loop().time()>deadline:
                    raise AssertionError('native host did not reach controlled request')
                await asyncio.sleep(.05)
            marker=next(workers.glob('alive-native-worker-*/worker/scope-test-ready'))
            interrupted=durable.open_cycle()
            failed_before=len(journal.read(event_type='opportunity.synthesis_failed'))
            policy=policies.current(owner)
            command=policies.append_update(subject=owner,actor=owner,expected_revision=policy.revision,
                enabled=False,context=policy.context,operation_id='pause-native-host')
            assert policies.apply(command).outcome=='recorded'
            marker.with_name('scope-test-release').touch()
            try: await active
            except OpportunitySynthesisError:
                failures=journal.read(event_type='opportunity.synthesis_failed')
                assert len(failures)==failed_before+1
                assert failures[-1].event.payload['error_class']=='NativeWorkerError'
                assert journal.get(interrupted.event_id+':closed') is None
            else: raise AssertionError('in-flight cycle accepted output after real owner pause')
            assert not wired.pending and not list(workers.iterdir())
        finally:
            if not active.done():
                active.cancel()
                try: await active
                except asyncio.CancelledError: pass
                await wired.reap_pending(timeout_seconds=5)
        assert (await wired.step(parameters)).disposition=='paused' and wired.last_call_count==0
        assert dict(os.environ)==original
        print('HERMES_ALIVE_NATIVE_COGNITION_DURABLE_HOST_PAUSE_OK',flush=True)


with tempfile.TemporaryDirectory(prefix='alive-host-acquisition-') as folder:
    asyncio.run(exercise(Path(folder)))
