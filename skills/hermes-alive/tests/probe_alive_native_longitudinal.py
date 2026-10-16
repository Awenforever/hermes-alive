"""Opt-in real native interpretation across synthetic feedback/context changes.

Not delivery, independent semantic review, automatic host install or acceptance.
Model-only projection is operator-supplied; never print its contents.
"""
import argparse
import asyncio
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-live-models',action='store_true',required=True)
parser.add_argument('--core',type=Path,required=True)
parser.add_argument('--model-projection',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
sys.path[:0]=[str(args.core.resolve(strict=True)),str(Path(__file__).resolve().parents[1]/'hooks'),
    str(Path(__file__).resolve().parent)]


async def exercise():
    from contextlib import ExitStack
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    from agent.secret_scope import set_secret_scope,reset_secret_scope,set_multiplex_context,reset_multiplex_context
    from alive_kernel import (DiscoveryCandidate,DiscoveryOpportunityIngestor,MemoryProposal,
        MemoryKind,MemoryAuthority,MemoryProjection,EventEnvelope,OpportunitySynthesizer)
    from alive_kernel.native_host_caller import HostNativeCaller,HostModelBinding
    from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
    from alive_kernel.feedback_assimilation import FeedbackAssimilationRuntime
    from probe_alive_live_feedback import prepare_case
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    projection=json.loads(args.model_projection.read_text())
    host=args.output/'host'; host.mkdir(mode=0o700)
    workers=args.output/'workers'; workers.mkdir(mode=0o700)
    report=dict(logical_calls=0,cases=[],sends=0,semantic_accuracy_proven=False,
        experiment='prospective synthetic native longitudinal interpretation only')
    def save():
        path=args.output/'report.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        path.chmod(0o600)
    interpreter,owner,outcome=prepare_case(args.output/'kernel',dict(id='native-longitudinal',
        sent='合成先前分享：自行车保养的详细长文。',
        reply='维修话题我喜欢，但你上次太啰嗦。以后先给要点，想要细节我会问。'))
    journal=interpreter.journal
    binding=HostModelBinding(owner,'profile:synthetic','operation:longitudinal','generation:1')
    with ExitStack() as stack:
        token=set_hermes_home_override(host); stack.callback(reset_hermes_home_override,token)
        token=set_multiplex_context(True); stack.callback(reset_multiplex_context,token)
        token=set_secret_scope(projection['environment'],profile_home=str(host)); stack.callback(reset_secret_scope,token)
        acquire=CoreScopedModelAcquirer(profile_home=host,read_binding=lambda:binding,
            read_configuration=lambda:projection['config'],
            read_credential_names=lambda **_:tuple(projection['environment']),
            identity='Synthetic experiment: a candid helpful assistant. All user/scenario material is fictional.')
        caller=HostNativeCaller(subject=owner,profile_id=binding.profile_id,operation_id=binding.operation_id,
            acquire=acquire,interpreter=sys.executable,core=args.core,private_root=workers,
            environment=dict(os.environ),timeout_seconds=120,max_calls=4)
        async def call(**kwargs):
            report['logical_calls']+=1
            item=dict(task=kwargs['task'],prompt=json.loads(kwargs['messages'][1]['content']))
            report['cases'].append(item); save()
            try:
                result=await caller(**kwargs)
                item.update(actual_model=result.model,response=result.choices[0].message.content)
                return result
            except Exception as error:
                item['error_class']=type(error).__name__
                raise
            finally: save()
        assimilation=FeedbackAssimilationRuntime(journal,content_vault=interpreter.vault)
        try:
            report['feedback_tick']=await assimilation.tick(subject=owner,call=call)
            source=DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(
                source='explicitly synthetic public scenario',title='合成社区公益自行车保养指南',
                summary='虚构材料：免费的图文指南讲解清洁链条、检查刹车与轮胎；不要求注册或购买。'
                    '这是实验素材，不代表真实活动或事实。',url='https://example.invalid/synthetic-repair',
                observed_at=datetime.now(timezone.utc)),subject=owner)
            report['source_agenda_item_id']=source.agenda_item_id
            memory=MemoryProjection(journal)
            async def phase(name):
                synth=OpportunitySynthesizer(type(journal)(journal.path),content_vault=interpreter.vault)
                result=await synth.run(subject=owner,operation_id='native-longitudinal:'+name,call=call)
                report.setdefault('phases',[]).append(dict(name=name,structurally_completed=True,
                    rejected_count=result.rejected_count,candidate_count=len(result.candidates),
                    abstention_count=len(result.abstentions)))
                save()
            await phase('after-feedback')
            request=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-user',
                actor=owner,subject=owner,payload={'synthetic':True}))
            pause=MemoryProposal(kind=MemoryKind.PREFERENCE,subject=owner,predicate='profile.interest',
                value='从现在起，维修相关内容先不要推送，等我明确恢复；这不表示我不再喜欢维修。',
                authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(request.event.event_id,),confidence=1)
            memory.append_proposal(pause,actor=owner)
            await phase('topic-paused')
            memory.forget_item(pause.proposal_id,actor=owner,request_id='synthetic-resume-topic')
            await phase('pause-withdrawn')
            assert not journal.read(event_type='dispatch.externally_started')
        except Exception as error:
            report['terminal_error_class']=type(error).__name__
        finally:
            report['pending_workers']=len(caller.pending)
            report['authority_granted']=False
            save()
    print(json.dumps(dict(logical_calls=report['logical_calls'],phases=len(report.get('phases',[])),
        pending_workers=report['pending_workers'],terminal_error_class=report.get('terminal_error_class'),sends=0)))


asyncio.run(exercise())
