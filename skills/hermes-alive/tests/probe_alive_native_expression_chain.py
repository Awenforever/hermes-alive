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
parser.add_argument('--reviewer-model',required=True)
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
    if (set(spec)!={'title','url','excerpt','collection_note','synthetic_user_context'}
            or any(not isinstance(v,str) or not v.strip() or len(v)>1800 for v in spec.values())
            or not spec['url'].startswith('https://')):
        raise ValueError('explicit bounded public evidence and synthetic context required')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    if args.resume_expression:
        original=json.loads((args.resume_expression/'report.json').read_text(encoding='utf-8'))
        if (original.get('source')!=spec or original.get('synthetic_owner')!='user:synthetic-native-public-expression'
                or original.get('error_class') is not None or 'result' not in original):
            raise ValueError('resume requires the exact completed synthetic public expression context')
        shutil.copytree(args.resume_expression/'kernel',args.output/'kernel')
    journal=ExperienceJournal(args.output/'kernel'/'experience.sqlite3')
    owner='user:synthetic-native-public-expression'
    if not args.resume_expression:
        DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(
            source=spec['collection_note'],title=spec['title'],url=spec['url'],summary=spec['excerpt'],
            observed_at=datetime.now(timezone.utc)),subject=owner)
        inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-user',
            actor=owner,subject=owner,payload={'synthetic':True}))
        MemoryProjection(journal).append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,
            subject=owner,predicate='profile.interest',value=spec['synthetic_user_context'],
            authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(inbound.event.event_id,),confidence=1),actor=owner)
    projection=json.loads(args.model_projection.read_text())
    home=args.output/'host'; home.mkdir(mode=0o700)
    workers=args.output/'workers'; workers.mkdir(mode=0o700)
    binding=HostModelBinding(owner,'profile:synthetic','operation:public-expression','generation:1')
    report=dict(logical_calls=0,calls=[],source=spec,synthetic_owner=owner,
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
        token=set_secret_scope(projection['environment'],profile_home=str(home)); stack.callback(reset_secret_scope,token)
        acquire=CoreScopedModelAcquirer(profile_home=home,read_binding=lambda:binding,
            read_configuration=lambda:projection['config'],read_credential_names=lambda **_:tuple(projection['environment']),
            identity='Helpful candid assistant in an isolated synthetic-owner experiment. No sending authority.')
        caller=HostNativeCaller(subject=owner,profile_id=binding.profile_id,operation_id=binding.operation_id,
            acquire=acquire,interpreter=sys.executable,core=args.core,private_root=workers,
            environment=dict(os.environ),timeout_seconds=185,max_calls=10)
        async def call(**kwargs):
            report['logical_calls']+=1
            item=dict(task=kwargs['task'],requested_model=kwargs['model'],messages=kwargs['messages'])
            report['calls'].append(item); save()
            kwargs.setdefault('timeout',180)
            try:
                response=await caller(**kwargs)
                item.update(actual_model=response.model,provider=response.native_completion.provider,
                    completion_evidence=asdict(response.native_completion),
                    raw_response=response.choices[0].message.content)
                return response
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
