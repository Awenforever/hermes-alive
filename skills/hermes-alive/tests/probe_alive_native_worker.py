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
    # The real Core client must apply common and endpoint-specific headers,
    # including after an actual primary403 -> backup switch. No SDK constructor
    # or Core fallback function is replaced by this qualification.
    policy=dict(default_headers={'X-Owner-Policy':'synthetic-common'},routes=[
        dict(base_url=route['base_url'],extra_headers={'X-Route-Policy':'synthetic-main'},ssl_verify=True),
        dict(base_url='https://backup.invalid/v1',extra_headers={'X-Route-Policy':'synthetic-backup'},ssl_verify=True)])
    policy_caller=NativeWorkerCaller(subject='user:synthetic',operation_id='actual-policy-worker',
        interpreter=sys.executable,core=core,private_root=work,environment={**os.environ,
            'ALIVE_TEST_HTTP_DIAGNOSTIC':str(root/'policy-http.jsonl')},
        resolve_runtime=lambda **_kw:{**route,'model':'policy-fail-primary','client_policy':policy,
            'fallback_model':[{**route['fallback_model'][0],'model':'policy-backup','provider':'custom:owner-backup'}],
            'providers_allowed':['synthetic-approved'],'providers_ignored':['synthetic-denied'],
            'provider_data_collection':'deny','provider_require_parameters':True,
            'capabilities':{'vision':False}},assert_current=lambda:True,
        identity='SYNTHETIC_PERSONA_156: concise.',entrypoint=Path(__file__).resolve().parent/
        'fixtures'/'native-worker-http-bootstrap.py',timeout_seconds=60)
    try: result=await policy_caller(**params)
    finally:
        if (root/'policy-http.jsonl').exists():
            print('NATIVE_POLICY_WIRE_DIAGNOSTIC='+ (root/'policy-http.jsonl').read_text(),flush=True)
    assert result.model=='served-label/policy-backup'
    assert not policy_caller.pending and not list(work.iterdir())
    print('HERMES_ALIVE_ACTUAL_NATIVE_CLIENT_POLICY_OK',flush=True)
    snapshot=dict(config=dict(model=dict(default='configured-primary',provider='custom:owner-main',
        default_headers={'X-Owner-Policy':'synthetic-common','X-Host-Snapshot':'yes'}),
        custom_providers=[dict(name='owner-main',model='configured-primary',base_url=route['base_url'],
            api_mode='chat_completions',key_env='OWNER_MAIN_KEY',extra_headers={'X-Route-Policy':'synthetic-main'},
            extra_body={'native_policy_probe':'synthetic-marker'}),
            dict(name='owner-backup',base_url='https://backup.invalid/v1',api_mode='chat_completions',
                key_env='OWNER_BACKUP_KEY',extra_headers={'X-Route-Policy':'synthetic-backup'})],
        model_aliases=dict(chosen=dict(model='configured-other',provider='custom',base_url=route['base_url'],
            key_env='OWNER_ALIAS_KEY'),failover=dict(model='fail-primary',provider='custom',
                base_url=route['base_url'],key_env='OWNER_ALIAS_KEY')),
        fallback_providers=[dict(provider='custom:owner-backup',model='configured-backup',key_env='OWNER_BACKUP_KEY')],
        agent=dict(reasoning_effort=False),provider_routing=dict(data_collection='deny',
            only=['synthetic-approved'],models={'configured-other':{'only':['synthetic-model-pin']}})),
        secrets=dict(OWNER_MAIN_KEY='PRIVATE_MAIN_KEY',OWNER_ALIAS_KEY='PRIVATE_MAIN_KEY',OWNER_BACKUP_KEY='PRIVATE_FALLBACK_KEY'),
        selected_model=None)
    host_caller=NativeWorkerCaller(subject='user:synthetic',operation_id='actual-host-worker',
        interpreter=sys.executable,core=core,private_root=work,
        environment={**os.environ,'OWNER_MAIN_KEY':'FOREIGN_AMBIENT_KEY','OWNER_ALIAS_KEY':'FOREIGN_AMBIENT_KEY',
            'OWNER_BACKUP_KEY':'FOREIGN_AMBIENT_KEY'},
        resolve_runtime=lambda **kw:dict(host_snapshot={**snapshot,'selected_model':kw['model']}),
        assert_current=lambda:True,identity='SYNTHETIC_PERSONA_156: concise.',
        entrypoint=Path(__file__).resolve().parent/'fixtures'/'native-worker-http-bootstrap.py',timeout_seconds=60)
    for selected,expected in ((None,'configured-primary'),('chosen','configured-other'),('failover','configured-backup')):
        try: result=await host_caller(**{**params,'model':selected})
        except NativeWorkerError as error:
            print('HOST_SNAPSHOT_ERROR_CLASS='+getattr(error,'worker_error_class',type(error).__name__),flush=True)
            raise
        assert result.model=='served-label/'+expected
        assert not host_caller.pending and not list(work.iterdir())
        print('HERMES_ALIVE_ACTUAL_NATIVE_HOST_SNAPSHOT_OK='+str(selected),flush=True)
    import copy
    private_snapshot=copy.deepcopy(snapshot)
    private_snapshot['config']['fallback_providers']=[]
    private_snapshot['secrets']={}
    missing=NativeWorkerCaller(subject='user:synthetic',operation_id='missing-owner-credential',
        interpreter=sys.executable,core=core,private_root=work,
        environment={**os.environ,'OWNER_MAIN_KEY':'FOREIGN_AMBIENT_KEY',
            'ALIVE_TEST_HTTP_DIAGNOSTIC':str(root/'missing-http.jsonl')},
        resolve_runtime=lambda **_kw:dict(host_snapshot=private_snapshot),assert_current=lambda:True,
        identity='SYNTHETIC_PERSONA_156: concise.',entrypoint=Path(__file__).resolve().parent/
            'fixtures'/'native-worker-http-bootstrap.py',timeout_seconds=60)
    try: await missing(**params)
    except NativeWorkerError as error:
        assert getattr(error,'worker_error_class',None) in ('AuthError','NativeWorkerError')
    else: raise AssertionError('undeclared ambient owner credential was accepted')
    finally:
        if (root/'missing-http.jsonl').exists():
            print('MISSING_OWNER_WIRE_DIAGNOSTIC='+ (root/'missing-http.jsonl').read_text(),flush=True)
    assert not (root/'missing-http.jsonl').exists(), 'missing credential reached model HTTP'
    assert not missing.pending and not list(work.iterdir())
    assert snapshot['selected_model'] is None and snapshot['secrets']['OWNER_MAIN_KEY']=='PRIVATE_MAIN_KEY'
    print('HERMES_ALIVE_ACTUAL_NATIVE_HOST_SECRET_DENIED_OK',flush=True)
    router_snapshot=copy.deepcopy(snapshot)
    router_snapshot['config']['model'].update(default='policy-openrouter',provider='openrouter')
    router_snapshot['config']['fallback_providers']=[]
    router_snapshot['config']['provider_routing']['models']={'policy-openrouter':{'only':['synthetic-model-pin']}}
    router_snapshot['secrets']={'OPENROUTER_API_KEY':'PRIVATE_MAIN_KEY'}
    router=NativeWorkerCaller(subject='user:synthetic',operation_id='host-policy-on-wire',
        interpreter=sys.executable,core=core,private_root=work,environment={**os.environ,
            'ALIVE_TEST_HTTP_DIAGNOSTIC':str(root/'router-http.jsonl')},
        resolve_runtime=lambda **_kw:dict(host_snapshot=router_snapshot),assert_current=lambda:True,
        identity='SYNTHETIC_PERSONA_156: concise.',entrypoint=Path(__file__).resolve().parent/
            'fixtures'/'native-worker-http-bootstrap.py',timeout_seconds=60)
    try: result=await router(**params)
    except NativeWorkerError as error:
        print('HOST_ROUTER_ERROR_CLASS='+getattr(error,'worker_error_class',type(error).__name__),flush=True)
        print('HOST_ROUTER_ERROR_STAGE='+getattr(error,'worker_error_stage','unavailable'),flush=True)
        print(json.dumps(getattr(error,'worker_diagnostics',None)),flush=True)
        raise
    finally:
        if (root/'router-http.jsonl').exists():
            print('ROUTER_WIRE_DIAGNOSTIC='+ (root/'router-http.jsonl').read_text(),flush=True)
    assert result.model=='served-label/policy-openrouter'
    assert not router.pending and not list(work.iterdir())
    print('HERMES_ALIVE_ACTUAL_NATIVE_HOST_ROUTING_WIRE_OK',flush=True)
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
        core=core,private_root=work,environment=dict(os.environ),
        resolve_runtime=lambda **kw:dict(host_snapshot={**snapshot,'selected_model':kw['model']}),assert_current=lambda:True,
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
