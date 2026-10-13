#!/usr/bin/env python3
"""One independent review of a retained current synthetic draft; never send."""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal,Sensitivity
from alive_kernel.source_support import SourceSupportReviewer
from alive_kernel.claim_support import ClaimSupportReviewer,FacetedClaimSupportReviewer
from alive_kernel.semantic_comparator import SemanticComparator


async def exercise(args):
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True,exist_ok=False)
    claim_accounting=bool(getattr(args,'claim_accounting',False))
    facets=bool(getattr(args,'faceted_accounting',False))
    experiment=str(getattr(args,'experiment_id','') or '')
    reviewer=(FacetedClaimSupportReviewer if facets else ClaimSupportReviewer if claim_accounting else SourceSupportReviewer)(ExperienceJournal(args.journal))
    generated=reviewer.interpreter.load_completed(subject='user:synthetic',operation_id=args.interpretation_id)
    if len(generated.candidates)!=1:
        raise ValueError('probe requires one retained synthetic candidate')
    candidate=generated.candidates[0]
    snapshot,_=reviewer.snapshot(subject='user:synthetic',interpretation_id=args.interpretation_id,
                               candidate_id=candidate.action.candidate_id)
    if any(s['provenance_metadata']['collector']!='synthetic-public-fixture' for s in snapshot['evidence']):
        raise ValueError('only explicit synthetic public discovery is permitted')
    report={'logical_calls':0,'observed_async_http':[],'sends':0,'delivery_qualified':False,
            'generation_calls':0,'selection_model_calls':0,
            'experiment_id':experiment or None,
            'review_method':'discourse-assertion-facets' if facets else 'claim-accounting' if claim_accounting else 'whole-message'}
    original=httpx.AsyncClient.send
    old_logging=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    async def send(client,request,*a,**kw):
        if len(report['observed_async_http'])>=4:
            raise RuntimeError('source-support transport budget exhausted')
        item={'host':request.url.host}
        report['observed_async_http'].append(item)
        try:
            response=await original(client,request,*a,**kw)
            item['status']=response.status_code
            return response
        except Exception as exc:
            item['error_class']=type(exc).__name__
            raise
    def domain(model):
        if model.lower().startswith('deepseek'):
            return 'deepseek-family'
        if model.lower().startswith(args.reviewer_family):
            return args.reviewer_family+'-family'
        return None
    async def call(**kw):
        report['logical_calls']+=1
        if report['logical_calls']>1:
            raise RuntimeError('source-support logical budget exhausted')
        response=await async_call_llm(**kw)
        text,model,provider=SemanticComparator._response(response,kw['route_info'])
        report.update(raw_review=text,actual_model=model,actual_provider=provider)
        return response
    httpx.AsyncClient.send=send
    try:
        receipt=await reviewer.run(subject='user:synthetic',interpretation_id=args.interpretation_id,
            candidate_id=candidate.action.candidate_id,
            operation_id=('synthetic-assertion-facets:' if facets else 'synthetic-claim-accounting:' if claim_accounting else 'synthetic-source-support:')+args.reviewer_family+(':'+experiment if experiment else ''),
            call=call,resolve_domain=domain)
        findings=reviewer.verify_current(receipt.event_id,subject='user:synthetic',
            interpretation_id=args.interpretation_id,candidate_id=candidate.action.candidate_id)
        if findings is None:
            raise ValueError('completed source-support receipt is no longer valid')
        report.update(receipt_event_id=receipt.event_id,findings=findings,
            candidate_text=snapshot['candidate']['text'],safe_for_automatic_delivery=False)
    except Exception as exc:
        report['error_class']=type(exc).__name__
    finally:
        httpx.AsyncClient.send=original
        logging.disable(old_logging)
        report['no_external_dispatch']=not bool(reviewer.journal.read(event_type='dispatch.externally_started'))
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'logical_calls':report['logical_calls'],'verdict':report.get('findings',{}).get('verdict'),
                      'error_class':report.get('error_class'),'sends':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models',action='store_true',required=True)
    parser.add_argument('--journal',type=Path,required=True)
    parser.add_argument('--interpretation-id',required=True)
    parser.add_argument('--reviewer-family',choices=('claude','qwen','glm','gemini','gpt'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--claim-accounting',action='store_true')
    parser.add_argument('--faceted-accounting',action='store_true')
    parser.add_argument('--experiment-id',help='Explicit separate experiment; never replaces a spent operation.')
    asyncio.run(exercise(parser.parse_args()))
