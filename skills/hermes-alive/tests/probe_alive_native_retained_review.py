"""One opt-in native independent review of retained synthetic interpretation.

Preserve the original experiment, never invent a verdict or provider family.
"""
import argparse
import asyncio
from contextlib import ExitStack
import json
import math
import os
import re
from pathlib import Path
import shutil
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-live-models',action='store_true',required=True)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--original',type=Path,required=True)
parser.add_argument('--model-projection',type=Path,required=True)
parser.add_argument('--reviewer-model',required=True)
parser.add_argument('--timeout-seconds',type=float,default=40)
parser.add_argument('--allow-correlated-review',action='store_true')
parser.add_argument('--repair',action='store_true')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if not math.isfinite(args.timeout_seconds) or not 1<=args.timeout_seconds<=240:
    parser.error('timeout must be finite and between 1 and 240 seconds')
sys.path[:0]=[str(args.core.resolve(strict=True)),str(Path(__file__).resolve().parents[1]/'hooks')]


def family(model):
    label=model.lower()
    if 'deepseek' in label: return 'deepseek'
    if 'qwen' in label: return 'qwen'
    return None  # Only explicit experiment families, not a production registry.


async def exercise():
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    from agent.secret_scope import set_secret_scope,reset_secret_scope,set_multiplex_context,reset_multiplex_context
    from alive_kernel import ExperienceJournal,OpportunitySynthesizer
    from alive_kernel.outcomes import OutcomeProjection
    from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
    from alive_kernel.native_host_caller import HostModelBinding,HostNativeCaller
    from alive_kernel.source_support import SourceSupportReviewer
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    shutil.copytree(args.original/'kernel',args.output/'kernel')
    journal=ExperienceJournal(args.output/'kernel/kernel.sqlite3')
    owner='user:synthetic-native-longitudinal'
    interpretation='native-longitudinal:pause-withdrawn'
    # The original prepare_case explicitly shared its outcome vault with
    # discovery/hypotheses. Preserve that host choice; never invent a new vault.
    vault=OutcomeProjection(journal).content_vault
    retained=OpportunitySynthesizer(journal,content_vault=vault).load_completed(subject=owner,operation_id=interpretation)
    assert len(retained.candidates)==1
    candidate=retained.candidates[0].action.candidate_id
    projection=json.loads(args.model_projection.read_text())
    home=args.output/'host'; home.mkdir(mode=0o700)
    workers=args.output/'workers'; workers.mkdir(mode=0o700)
    binding=HostModelBinding(owner,'profile:synthetic','operation:retained-review','generation:1')
    report=dict(logical_calls=0,sends=0,requested_model=args.reviewer_model,timeout_seconds=args.timeout_seconds,
        generator_model=retained.actual_model,independent_review_proven=False,
        automatic_delivery_authority=False,semantic_accuracy_proven=False,
        correlated_diagnostic=args.allow_correlated_review,calls=[])
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
            identity='Synthetic evidence review. No private user data or delivery authority.')
        caller=HostNativeCaller(subject=owner,profile_id=binding.profile_id,operation_id=binding.operation_id,
            acquire=acquire,interpreter=sys.executable,core=args.core,private_root=workers,
            environment=dict(os.environ),timeout_seconds=max(120,args.timeout_seconds+5),
            max_calls=3 if args.repair else 1)
        async def call(**kwargs):
            report['logical_calls']+=1
            item=dict(task=kwargs['task'],snapshot=json.loads(kwargs['messages'][1]['content']))
            report['calls'].append(item)
            save()
            result=await caller(**kwargs)
            item.update(actual_model=result.model,actual_provider=result.native_completion.provider,
                raw_response=result.choices[0].message.content)
            if report['logical_calls']==1:
                report.update(actual_model=result.model,actual_provider=result.native_completion.provider,
                    raw_review=result.choices[0].message.content)
            save()
            return result
        try:
            result=await SourceSupportReviewer(journal,content_vault=vault).run(subject=owner,interpretation_id=interpretation,
                candidate_id=candidate,operation_id='native-retained-independent-review',call=call,
                resolve_domain=family,reviewer_model=args.reviewer_model,
                require_independence=not args.allow_correlated_review,
                timeout_seconds=args.timeout_seconds)
            report.update(verdict=result.verdict,independent_review_proven=result.independent,
                receipt_event_id=result.event_id)
            if args.repair and result.verdict in ('unsupported','uncertain'):
                synth=OpportunitySynthesizer(journal,content_vault=vault)
                repaired=await synth.run(subject=owner,operation_id='native-retained-v2-repair',call=call,
                    recipient_meaning=True,revision_event_ids=(result.event_id,))
                report['repair']=dict(candidates=len(repaired.candidates),abstentions=len(repaired.abstentions),
                    rejected=repaired.rejected_count,actual_model=repaired.actual_model,
                    proposals=[synth.retained_proposal(receipt_event_id=repaired.receipt_event_id,
                        candidate_id=c.action.candidate_id,subject=owner,clearance='private')
                        for c in repaired.candidates])
                if len(repaired.candidates)==1:
                    second=await SourceSupportReviewer(journal,content_vault=vault).run(subject=owner,
                        interpretation_id='native-retained-v2-repair',candidate_id=repaired.candidates[0].action.candidate_id,
                        operation_id='native-retained-repair-review',call=call,resolve_domain=family,
                        reviewer_model=args.reviewer_model,require_independence=not args.allow_correlated_review,
                        timeout_seconds=args.timeout_seconds)
                    report['repair'].update(verdict=second.verdict,independent=second.independent,
                        receipt_event_id=second.event_id)
        except Exception as error:
            report['error_class']=type(error).__name__
            for key in ('worker_error_class','worker_error_stage'):
                value=getattr(error,key,None)
                if isinstance(value,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',value):
                    report[key]=value
            if getattr(error,'worker_error_class',None)=='NativeCompletionError':
                report['completion_diagnostics']=getattr(error,'worker_diagnostics',None)
            if str(error) in ('model worker timed out; owned lease is closed',
                    'model worker output limit exceeded','model worker launch or capture failed'):
                report['worker_failure']=str(error)
        finally:
            await caller.reap_pending(timeout_seconds=5)
            report['pending_workers']=len(caller.pending)
            save()
    print(json.dumps({key:report.get(key) for key in ('logical_calls','actual_model',
        'actual_provider','verdict','independent_review_proven','error_class','pending_workers','sends')}))


asyncio.run(exercise())
