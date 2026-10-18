"""Opt-in native public-evidence/synthetic-owner expression chain; never send.

The evidence file is an explicit operator artifact, not a production profile.
This probe has no transport or authority to deliver its resulting wording.
"""
import argparse
import asyncio
from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime,timezone
import json
import os
import shutil
from pathlib import Path
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-live-models',action='store_true',required=True)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--model-projection',type=Path,required=True)
parser.add_argument('--evidence',type=Path,required=True)
parser.add_argument('--profile-choice',choices=('a','b'),default='a',
    help='Synthetic profile for a collected multi-material interest fixture')
parser.add_argument('--reviewer-model',required=True)
parser.add_argument('--reviewer-model-projection',type=Path)
parser.add_argument('--resume-expression',type=Path)
parser.add_argument('--final-grounding',action='store_true')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
sys.path[:0]=[str(args.core.resolve(strict=True)),str(Path(__file__).resolve().parents[1]/'hooks')]


def family(*labels):
    model=labels[-1].lower()
    if 'deepseek' in model: return 'deepseek'
    if 'qwen' in model: return 'qwen'
    return None  # Explicit operator knowledge, not a production model registry.


async def exercise():
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    from agent.secret_scope import set_secret_scope,reset_secret_scope,set_multiplex_context,reset_multiplex_context
    from alive_kernel import (ExperienceJournal,DiscoveryOpportunityIngestor,DiscoveryCandidate,
        MemoryProjection,MemoryProposal,MemoryKind,MemoryAuthority,EventEnvelope,ActionAuthority,PolicyContext)
    from alive_kernel.expression_runtime import ExpressionRuntime
    from alive_kernel.native_host_caller import HostModelBinding,HostNativeCaller
    from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
    spec=json.loads(args.evidence.read_text(encoding='utf-8'))
    if set(spec)=={'title','url','excerpt','collection_note','synthetic_user_context'}:
        if (any(not isinstance(v,str) or not v.strip() or len(v)>1800 for v in spec.values())
                or not spec['url'].startswith('https://')):
            raise ValueError('explicit bounded public evidence and synthetic context required')
        materials=[dict(title=spec['title'],url=spec['url'],excerpt=spec['excerpt'],priority_hint=.5)]
        collection_note=spec['collection_note']
        user_context=spec['synthetic_user_context']
    elif set(spec)=={'materials','preference_a','preference_b'}:
        materials=spec['materials']
        if (not isinstance(materials,list) or not 2<=len(materials)<=24
                or any(not isinstance(spec[k],str) or not 1<=len(spec[k])<=1500
                       for k in ('preference_a','preference_b'))):
            raise ValueError('bounded material pool and synthetic preferences required')
        for item in materials:
            if (not isinstance(item,dict) or set(item)!={'title','url','excerpt','priority_hint'}
                    or any(not isinstance(item[k],str) or not 1<=len(item[k])<=1500
                           for k in ('title','url','excerpt')) or not item['url'].startswith('https://')
                    or type(item['priority_hint']) not in (int,float) or not 0<=item['priority_hint']<=1):
                raise ValueError('explicit bounded public material required')
        if len({m['url'] for m in materials})!=len(materials):
            raise ValueError('distinct material identities required')
        collection_note='Public publisher/listing collection; not full article/video verification'
        user_context=spec['preference_'+args.profile_choice]
    else:
        raise ValueError('explicit bounded public evidence and synthetic context required')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    if args.resume_expression:
        original=json.loads((args.resume_expression/'report.json').read_text(encoding='utf-8'))
        if (original.get('source')!=spec or original.get('synthetic_owner')!='user:synthetic-native-public-expression'
                or original.get('error_class') is not None or 'result' not in original
                or original.get('profile_choice','a')!=args.profile_choice):
            raise ValueError('resume requires the exact completed synthetic public expression context')
        shutil.copytree(args.resume_expression/'kernel',args.output/'kernel')
    journal=ExperienceJournal(args.output/'kernel'/'experience.sqlite3')
    owner='user:synthetic-native-public-expression'
    if not args.resume_expression:
        ingestor=DiscoveryOpportunityIngestor(journal)
        for material in materials:
            ingestor.ingest(DiscoveryCandidate(source=collection_note,title=material['title'],
                url=material['url'],summary=material['excerpt'],priority_hint=material['priority_hint'],
                observed_at=datetime.now(timezone.utc)),subject=owner)
        inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-user',
            actor=owner,subject=owner,payload={'synthetic':True}))
        MemoryProjection(journal).append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,
            subject=owner,predicate='profile.interest',value=user_context,
            authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(inbound.event.event_id,),confidence=1),actor=owner)
    projection=json.loads(args.model_projection.read_text())
    review_projection=json.loads(args.reviewer_model_projection.read_text()) if args.reviewer_model_projection else projection
    active_projection=projection
    secrets=dict(projection['environment'])
    for key,value in review_projection['environment'].items():
        if key in secrets and secrets[key]!=value: raise ValueError('conflicting model credential scope')
        secrets[key]=value
    home=args.output/'host'; home.mkdir(mode=0o700)
    workers=args.output/'workers'; workers.mkdir(mode=0o700)
    binding=HostModelBinding(owner,'profile:synthetic','operation:public-expression','generation:1')
    report=dict(logical_calls=0,calls=[],source=spec,profile_choice=args.profile_choice,
        admitted_materials=len(materials),synthetic_owner=owner,
        sends=0,automatic_delivery_authority=False,semantic_accuracy_proven=False,
        synthetic_policy_only=True,family_resolver_is_experiment_only=True,
        final_grounding=args.final_grounding,resumed_expression=str(args.resume_expression) if args.resume_expression else None)
    def save():
        path=args.output/'report.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        path.chmod(0o600)
    save()
    with ExitStack() as stack:
        token=set_hermes_home_override(home); stack.callback(reset_hermes_home_override,token)
        token=set_multiplex_context(True); stack.callback(reset_multiplex_context,token)
        token=set_secret_scope(secrets,profile_home=str(home)); stack.callback(reset_secret_scope,token)
        acquire=CoreScopedModelAcquirer(profile_home=home,read_binding=lambda:binding,
            read_configuration=lambda:active_projection['config'],read_credential_names=lambda **_:tuple(active_projection['environment']),
            identity='Helpful candid assistant in an isolated synthetic-owner experiment. No sending authority.')
        caller=HostNativeCaller(subject=owner,profile_id=binding.profile_id,operation_id=binding.operation_id,
            acquire=acquire,interpreter=sys.executable,core=args.core,private_root=workers,
            environment=dict(os.environ),timeout_seconds=185,max_calls=16)
        report['logical_call_limit']=16
        async def call(**kwargs):
            nonlocal active_projection
            is_review=kwargs.get('model')==args.reviewer_model
            active_projection=review_projection if is_review else projection
            report['logical_calls']+=1
            item=dict(task=kwargs['task'],requested_model=kwargs['model'],messages=kwargs['messages'],
                host_model_scope='review' if is_review else 'generation')
            report['calls'].append(item); save()
            kwargs.setdefault('timeout',180)
            try:
                response=await caller(**kwargs)
                item.update(actual_model=response.model,provider=response.native_completion.provider,
                    completion_evidence=asdict(response.native_completion),
                    raw_response=response.choices[0].message.content)
                return response
            except Exception as error:
                item['error_class']=type(error).__name__
                for key in ('worker_error_class','worker_error_stage'):
                    value=getattr(error,key,None)
                    if isinstance(value,str) and value.isidentifier(): item[key]=value
                if getattr(error,'worker_error_class',None)=='NativeCompletionError':
                    item['completion_diagnostics']=getattr(error,'worker_diagnostics',None)
                raise
            finally: save()
        parameters=dict(operation_id='native-public-expression:one',subject=owner,call=call,
            policy_context=PolicyContext(can_interrupt=True),authority=ActionAuthority.USER_DELEGATED,
            grounding=True,recipient_meaning=True,grounding_model=args.reviewer_model,
            resolve_grounding_domain=family,require_independent_grounding=True,
            reviewer_model=args.reviewer_model,resolve_domain=family,language='zh',model_timeout_seconds=180)
        try:
            async def run(current,**params):
                if args.final_grounding:
                    from alive_kernel.send_preparation_runtime import SendPreparationRuntime
                    return await SendPreparationRuntime(current).assess(**params)
                return await ExpressionRuntime(current).run(**params)
            result=await run(journal,**parameters)
            report['result']=asdict(result)
            before=journal.last_sequence()
            report['replay_inference_attempts']=0
            async def forbidden(**_):
                report['replay_inference_attempts']+=1
                raise AssertionError('completed chain repeated inference')
            recovered=await run(ExperienceJournal(journal.path),**{**parameters,'call':forbidden})
            report['replay_without_inference']=(recovered==result and journal.last_sequence()==before
                and report['replay_inference_attempts']==0)
        except Exception as error:
            report['error_class']=type(error).__name__
            report['worker_error_class']=getattr(error,'worker_error_class',None)
            report['worker_error_stage']=getattr(error,'worker_error_stage',None)
        finally:
            await caller.reap_pending(timeout_seconds=5)
            report['pending_workers']=len(caller.pending)
            report['action_attempts']=len(journal.read(event_type='action.attempted'))
            report['authorization_evaluations']=len(journal.read(event_type='action.authorization_evaluated'))
            report['external_dispatches']=len(journal.read(event_type='dispatch.externally_started'))
            save()
    print(json.dumps({k:report.get(k) for k in ('logical_calls','error_class',
        'replay_without_inference','pending_workers','action_attempts','external_dispatches','sends')}))


asyncio.run(exercise())
