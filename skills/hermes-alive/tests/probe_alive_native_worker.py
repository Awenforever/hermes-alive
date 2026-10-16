"""Actual Core worker protocol/routing under controlled HTTP, no production profile."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import tempfile

parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--core',type=Path,required=True)
args=parser.parse_args(); core=args.core.resolve(strict=True)


async def exercise(root):
    from alive_kernel.native_worker_caller import NativeWorkerCaller
    from alive_kernel.native_worker_protocol import NativeWorkerError
    work=root/'workers'; work.mkdir()
    route=dict(provider='custom',requested_provider='custom',model='configured-primary',api_mode='chat_completions',
        base_url='https://provider.invalid/v1',api_key='PRIVATE_MAIN_KEY',fallback_model=[dict(provider='custom',
            model='configured-backup',base_url='https://backup.invalid/v1',api_key='PRIVATE_FALLBACK_KEY')])
    selections=[]
    def resolve(**kwargs):
        selections.append(kwargs)
        selected={'existing-alias':'configured-other','fallback-check':'fail-primary'}.get(kwargs['model'],'configured-primary')
        return {**route,'model':selected}
    caller=NativeWorkerCaller(subject='user:synthetic',operation_id='actual-core-worker',interpreter=sys.executable,
        core=core,private_root=work,environment=dict(os.environ),resolve_runtime=resolve,assert_current=lambda:True,
        identity='SYNTHETIC_PERSONA_156: a candid concise assistant.',entrypoint=Path(__file__).resolve().parent/
        'fixtures'/'native-worker-http-bootstrap.py',timeout_seconds=60)
    params=dict(task='native_synthetic',model=None,messages=[dict(role='system',content='SYNTHETIC_TASK_156: draft only.'),
        dict(role='user',content='SYNTHETIC_CONTEXT_156: synthetic evidence only.')],temperature=.2,max_tokens=512)
    for requested,expected in ((None,'configured-primary'),('existing-alias','configured-other'),('fallback-check','configured-backup')):
        try: result=await caller(**{**params,'model':requested})
        except NativeWorkerError as error:
            print('NATIVE_WORKER_ERROR_CLASS='+getattr(error,'worker_error_class',type(error).__name__),flush=True)
            print(json.dumps(getattr(error,'worker_diagnostics',None)),flush=True)
            raise
        assert result.model=='served-label/'+expected and result.choices[0].message.content=='native synthetic reply'
        assert not result.native_completion.authority_granted
        assert not caller.pending and not list(work.iterdir())
        print('HERMES_ALIVE_NATIVE_WORKER_ROUTE_OK='+str(requested),flush=True)
    assert [v['model'] for v in selections]==[None,'existing-alias','fallback-check']
    from probe_alive_live_feedback import prepare_case
    from alive_kernel import (AutonomyPolicyProjection,DiscoveryCandidate,DiscoveryOpportunityIngestor,PolicyContext)
    from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
    interpreter,owner,_=prepare_case(root/'canonical',dict(id='native-worker-156',sent='Synthetic prior source.',
        reply='SYNTHETIC_CONTEXT_156: I am busy today, not permanently uninterested.'))
    journal=interpreter.journal
    policies=AutonomyPolicyProjection(journal); policies.project_new(); current=policies.current(owner)
    assert policies.apply(policies.append_update(subject=owner,actor=owner,expected_revision=current.revision,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='worker-enable')).outcome=='recorded'
    DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(source='synthetic',
        title='SYNTHETIC_CONTEXT_156 public observation',summary='An uncertain nonurgent reading lead.',
        url='https://example.invalid/native-worker',observed_at=datetime.now(timezone.utc)),subject=owner)
    canonical_caller=NativeWorkerCaller(subject=owner,operation_id='canonical-worker',interpreter=sys.executable,
        core=core,private_root=work,environment=dict(os.environ),resolve_runtime=resolve,assert_current=lambda:True,
        identity='SYNTHETIC_PERSONA_156: a candid concise assistant.',entrypoint=Path(__file__).resolve().parent/
        'fixtures'/'native-worker-http-bootstrap.py',timeout_seconds=60)
    runtime=AutonomousCycleRuntime(journal,content_vault=interpreter.vault)
    parameters=dict(subject=owner,expression_parameters=dict(call=canonical_caller,
        resolve_domain=lambda provider,model:'synthetic-family'),resolve_binding=lambda record:None)
    result=await runtime.cycle(operation_id='native-protocol-shadow',**parameters)
    assert result.disposition=='silence' and canonical_caller.calls==1
    assert (await AutonomousCycleRuntime(journal,content_vault=interpreter.vault).cycle(
        operation_id='native-protocol-shadow',**parameters)).disposition=='silence'
    assert canonical_caller.calls==1 and not canonical_caller.pending and not list(work.iterdir())
    print('HERMES_ALIVE_NATIVE_WORKER_CANONICAL_REPLAY_OK',flush=True)
    print('HERMES_ALIVE_ACTUAL_NATIVE_WORKER_OK',flush=True)


with tempfile.TemporaryDirectory(prefix='alive-actual-native-worker-') as folder:
    previous={k:os.environ.get(k) for k in ('HERMES_HOME','HERMES_ALIVE_SHARED_DIR')}
    os.environ['HERMES_HOME']=str(Path(folder)/'profile')
    os.environ['HERMES_ALIVE_SHARED_DIR']=str(Path(folder)/'runtime')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    try: asyncio.run(exercise(Path(folder)))
    finally:
        for key,value in previous.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
