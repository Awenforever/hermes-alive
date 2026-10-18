#!/usr/bin/env python3
"""Three opt-in synthetic learning interpretations; no sends or benefit claim."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (EventEnvelope, ExperienceJournal, OpportunitySynthesizer,
    DiscoveryCandidate, DiscoveryOpportunityIngestor, MemoryProjection, MemoryProposal,
    MemoryKind, MemoryAuthority)
from alive_kernel.preference_learning import PreferenceDirection
from alive_kernel.events import _thaw_json
from alive_kernel.semantic_comparator import SemanticComparator
from run_alive_kernel_learning_context import seed


def preference(journal, predicate, value):
    event = EventEnvelope(event_type='conversation.inbound', source='synthetic-public-fixture',
        actor='user:synthetic', subject='user:synthetic', payload={'fixture':True})
    journal.append(event)
    MemoryProjection(journal).append_proposal(MemoryProposal(subject='user:synthetic',
        kind=MemoryKind.PREFERENCE, predicate=predicate, value=value,
        authority=MemoryAuthority.USER_EXPLICIT, source_event_ids=(event.event_id,), confidence=1),
        actor='user:synthetic')


async def exercise(args):
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True, exist_ok=False)
    journal = ExperienceJournal(args.journal)
    if journal.read(limit=1):
        raise ValueError('learning probe requires a fresh synthetic-only journal; no repeat spend')
    journal.append(EventEnvelope(event_id='learning-probe-v1:started', event_type='test.model_probe_started',
        source='synthetic-public-fixture', actor='system:alive-test', subject='user:synthetic',
        payload={'logical_call_limit':3,'sends_allowed':False,'human_gold':False}))
    DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic-public-fixture',
        title='Public repair recording', summary='A public notice mentions a free ten-minute online '
        'recording about safe hand-sewing repairs for torn clothing. It is available anytime and '
        'requires no registration, deadline or purchase. The notice has not been independently verified.',
        url='https://example.invalid/repair', observed_at=datetime.now(timezone.utc)), subject='user:synthetic')
    preference(journal, 'profile.interest', 'I enjoy practical household repair and online learning.')
    interpreter = OpportunitySynthesizer(journal)
    report={'logical_calls':0,'observed_async_http':[],'cases':[], 'sends':0,
        'selection_model_calls':0,'human_gold':False,'delivery_qualified':False,
        'fixture_prior_attempts_are_not_delivery':True}
    original=httpx.AsyncClient.send
    old_logging=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    async def send(client,request,*a,**kw):
        if len(report['observed_async_http'])>=12:
            raise RuntimeError('learning transport budget exhausted')
        item={'host':request.url.host}
        report['observed_async_http'].append(item)
        try:
            response=await original(client,request,*a,**kw)
            item['status']=response.status_code
            return response
        except Exception as exc:
            item['error_class']=type(exc).__name__
            raise
    httpx.AsyncClient.send=send
    try:
        for name in ('baseline','learned-concise','explicit-detailed'):
            if name=='learned-concise':
                seed(journal,'user:synthetic',PreferenceDirection.SUPPORT)
            elif name=='explicit-detailed':
                preference(journal,'profile.communication_detail',
                    'For this opportunity please give a detailed explanation, not a terse one-line summary.')
            item={'case_id':name}
            report['cases'].append(item)
            async def call(**kw):
                report['logical_calls']+=1
                if report['logical_calls']>3:
                    raise RuntimeError('learning logical budget exhausted')
                data=json.loads(kw['messages'][1]['content'])
                assert all(x['provenance_metadata']['collector']=='synthetic-public-fixture' for x in data['opportunities'])
                item['input']=data
                route={}
                response=await asyncio.wait_for(async_call_llm(**kw,route_info=route),timeout=50)
                text,model,provider=SemanticComparator._response(response,route)
                item.update(actual_model=model,actual_provider=provider,raw_response=text)
                return response
            try:
                result=await interpreter.run(subject='user:synthetic',operation_id='learning-probe:'+name,
                    call=call,timeout_seconds=55)
                item.update(receipt_event_id=result.receipt_event_id,rejected_count=result.rejected_count,
                    candidates=[{'kind':c.action.action_kind.value,
                        'authority':c.action.authority.value,'content':_thaw_json(c.content)} for c in result.candidates])
            except Exception as exc:
                item['error_class']=type(exc).__name__
            (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        httpx.AsyncClient.send=original
        logging.disable(old_logging)
        report['no_external_dispatch']=not bool(journal.read(event_type='dispatch.externally_started'))
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'logical_calls':report['logical_calls'],'cases':len(report['cases']),
                      'sends':0,'delivery_qualified':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models',action='store_true',required=True)
    parser.add_argument('--journal',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    asyncio.run(exercise(parser.parse_args()))
