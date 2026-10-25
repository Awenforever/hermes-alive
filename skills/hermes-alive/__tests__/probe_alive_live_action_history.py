"""Opt-in configured-model interpretation diagnostic; synthetic history, no sends."""
import argparse
import asyncio
from datetime import datetime,timedelta,timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (AutonomyPolicyProjection,DiscoveryCandidate,DiscoveryOpportunityIngestor,
    EventEnvelope,MemoryAuthority,MemoryKind,MemoryProjection,MemoryProposal,PolicyContext,Sensitivity)
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.events import _thaw_json
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer
from alive_kernel.outcomes import OutcomeKind
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel_testkit import install_terminal_route,authenticated_dispatch_receipt
from run_alive_kernel_expression_runtime import scenario
import httpx

BASE='Synthetic public organizer notice: a free online recording demonstrates hand-sewing repairs to a torn pocket. No registration or deadline is stated.'
UPDATE='Synthetic public organizer update: a new free online recording demonstrates replacing a broken jacket zipper, including choosing a matching zipper and safely removing old stitches. This is distinct from the earlier pocket-patching lesson. No registration or deadline is stated.'
CASES=('registered-no-result','delivery-observed','failure-observed','new-method')

async def run(output, *, model_call=None):
    """Single-pass fault observability, not a test of protocol recovery.

    Recovery has its own multi-call tests. Keep intentional raw failures visible
    here and do not silently expand the diagnostic's four-case call contract.
    """
    if model_call is None:
        from agent.auxiliary_client import async_call_llm
        model_call=async_call_llm
    ROOT=Path(output)
    ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any(ROOT.iterdir()):
        raise ValueError('diagnostic output must be empty; do not overwrite evidence')
    previous_logging=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    report={'scope':'real interpretation only; initial intent and canonical IO are synthetic fixtures',
        'logical_calls':0,'http_requests':[],'cases':[],'sends':0,'finished':False,
        'semantic_quality_qualified':False,'longitudinal_utility_qualified':False,
        'protocol_recovery':False}
    def save(): (ROOT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    original=httpx.AsyncClient.send
    async def tracked_send(client,request,*args,**kwargs):
        if len(report['http_requests'])>=24: raise RuntimeError('HTTP-start bound exhausted')
        item={'call':report['logical_calls'],'host':request.url.host}
        report['http_requests'].append(item); save()
        try:
            response=await original(client,request,*args,**kwargs)
            item['status']=response.status_code
            return response
        except Exception as exc:
            item['error_class']=type(exc).__name__
            raise
        finally: save()
    httpx.AsyncClient.send=tracked_send
    try:
        for name in CASES:
            entry={'case':name,'source':BASE,'calls':[]}
            report['cases'].append(entry); save()
            journal,params,ancestor=await scenario(ROOT/name,'share',return_ready=True,
                source_summary=BASE,draft_text=BASE)
            runtime=SendPreparationRuntime(journal)
            policy=AutonomyPolicyProjection(journal)
            policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
                enabled=True,context=PolicyContext(can_interrupt=True),operation_id='policy'))
            route=install_terminal_route(journal,subject='user:test',content_vault=runtime.vault,
                route_document={'platform':'weixin','profile':'synthetic','chat_id':'synthetic-no-send','thread_id':None})
            grant=ActionDelegationStore(journal).grant(subject='user:test',actor='user:test',
                policy_event_id=policy.current('user:test').event_id,route_binding_id=route,
                action_kinds=('share',),maximum_sensitivity=Sensitivity.PRIVATE,
                expires_at=datetime.now(timezone.utc)+timedelta(hours=1),operation_id='grant',allow_natural_expression=True)
            async def forbidden(**_): raise AssertionError('seeded plan unexpectedly requested inference')
            prepared=await runtime.prepare(**{**params,'call':forbidden},authorization_operation_id='prepare',
                route_binding_id=route,delegation_event_id=grant.event.event_id)
            if name in ('delivery-observed','failure-observed'):
                attempt=journal.get(prepared.attempt_event_id)
                kind=(OutcomeKind.DELIVERY_SUCCEEDED if name=='delivery-observed' else OutcomeKind.DELIVERY_FAILED)
                receipt=authenticated_dispatch_receipt(journal,attempt,event_id='synthetic:transport-result',
                    event_type='delivery.succeeded' if name=='delivery-observed' else 'delivery.failed')
                outcome=runtime.outcomes.append_outcome(attempt_id=attempt.event.payload['attempt_id'],
                    kind=kind,subject='user:test',source_event_id=receipt.event_id,
                    details={'synthetic':True,'no_real_io':True},actor='system:test',outcome_id='synthetic-result')
                assert runtime.outcomes.apply(outcome).outcome=='recorded'
            statement=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
                actor='user:test',subject='user:test',payload={'synthetic':True}))
            MemoryProjection(journal).append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,
                subject='user:test',predicate='profile.content_preferences',
                value='I enjoy useful practical clothing-repair tutorials. Do not repeat unchanged tips. Meaningfully different techniques and factual corrections are welcome. Do not ask me to reconfirm this preference.',
                authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(statement.event.event_id,),confidence=1),actor='user:test')
            if name=='new-method':
                DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic public organizer',
                    title='New zipper-replacement method',summary=UPDATE,url='https://example.invalid/new-method',
                    observed_at=datetime.now(timezone.utc)),subject='user:test')
            synth=OpportunitySynthesizer(journal,content_vault=runtime.vault)
            entry['registered_context']=[a.to_prompt() for a in synth.action_reader.read(subject='user:test',clearance=Sensitivity.PRIVATE)]
            assert len(entry['registered_context'])==1
            seeded_dispatch_count=len(journal.read(event_type='dispatch.started'))
            seeded_attempt_count=len(journal.read(event_type='action.attempted'))
            async def call(**kwargs):
                if report['logical_calls']>=8: raise RuntimeError('logical-call bound exhausted')
                report['logical_calls']+=1
                entry['prompt']=json.loads(kwargs['messages'][1]['content']); save()
                invocation={'prompt':entry['prompt']}
                entry['calls'].append(invocation); save()
                try:
                    response=await model_call(**kwargs)
                    entry['actual_model']=getattr(response,'model',None)
                    entry['raw_output']=response.choices[0].message.content
                    invocation.update(actual_model=entry['actual_model'],raw_output=entry['raw_output'])
                    return response
                except Exception as exc:
                    entry['provider_error_class']=type(exc).__name__
                    invocation['provider_error_class']=type(exc).__name__
                    raise
                finally: save()
            try:
                result=await synth.run(subject='user:test',operation_id='actual-next-cycle',call=call,
                    protocol_recovery=False)
                entry.update(candidates=[{'agenda_item_id':c.action.agenda_item_id,'kind':c.action.action_kind.value,
                    'content':_thaw_json(c.content)} for c in result.candidates],
                    abstentions=[{'agenda_item_id':a.agenda_item_id,'reason':a.reason} for a in result.abstentions],
                    rejected_count=result.rejected_count,unassessed=list(result.unassessed_agenda_item_ids))
            except Exception as exc:
                entry['error_class']=type(exc).__name__
                failed=journal.get('opportunity.synthesis:actual-next-cycle:failed')
                if failed is not None: entry['stage_error_class']=failed.event.payload['error_class']
            entry['new_dispatch_records']=len(journal.read(event_type='dispatch.started'))-seeded_dispatch_count
            entry['new_attempt_records']=len(journal.read(event_type='action.attempted'))-seeded_attempt_count
            assert entry['new_dispatch_records']==entry['new_attempt_records']==0
            # Synthetic authenticated receipts create fixture dispatch records;
            # they are not real sends. No adapter/execution function is invoked.
            save()
        report['finished']=True
    finally:
        httpx.AsyncClient.send=original; save()
        logging.disable(previous_logging)
    print(json.dumps({'logical_calls':report['logical_calls'],'http_starts':len(report['http_requests']),
                      'sends':0,'finished':report['finished']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,
                        help='Empty private directory for synthetic diagnostic evidence')
    arguments=parser.parse_args()
    asyncio.run(run(arguments.output))
