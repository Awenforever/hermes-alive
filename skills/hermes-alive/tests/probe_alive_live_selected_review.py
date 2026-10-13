#!/usr/bin/env python3
"""One independent live review of a retained synthetic expression; never send."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (EventEnvelope, ExperienceJournal, IndependentSemanticReview,
                         OpportunitySynthesizer, ReviewerKind, Sensitivity)
from alive_kernel.opportunity_expression import OpportunityExpressionStore
from alive_kernel.semantic_comparator import SemanticComparator, _REVIEW_PROMPT
from alive_kernel.semantic_rendering import serialize_meaning


async def exercise(args):
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True, exist_ok=False)
    journal = ExperienceJournal(args.journal)
    interpreter = OpportunitySynthesizer(journal)
    sources = interpreter.reader.active_evidence(subject='user:synthetic', clearance=Sensitivity.PRIVATE)
    if not sources or any(s.content['source'] != 'synthetic-public-fixture' for s in sources):
        raise ValueError('only explicitly synthetic fixtures are permitted')
    store = OpportunityExpressionStore(journal, content_vault=interpreter.vault)
    candidate = store.resolve_model_candidate(args.candidate_event_id)
    if candidate is None:
        raise ValueError('synthetic candidate is unavailable or stale')
    _source, document, _frame, _candidate = store._selection_context(
        selection_event_id=candidate.selection_event_id, meaning_event_id=candidate.meaning_event_id,
        subject='user:synthetic', observed_at=datetime.now(timezone.utc))
    comparator = SemanticComparator(store)
    operation = 'selected-review-probe:' + interpreter.vault.digest_json(
        {'candidate_event_id': candidate.event_id, 'reviewer_family': args.reviewer_family})[:40]
    started = journal.append(EventEnvelope(event_id=operation + ':started',
        event_type='test.model_probe_started', source='synthetic-public-fixture',
        actor='system:alive-test', subject='user:synthetic', sensitivity=_source.event.sensitivity,
        causation_id=candidate.event_id, payload={'logical_call_limit': 1, 'raw_prompt_stored': False,
                                                'raw_response_stored': False, 'sends_allowed': False}))
    if not started.created:
        raise ValueError('selected review probe was already attempted')
    report = {'logical_calls': 0, 'observed_async_http': [], 'sends': 0,
              'renderer_calls': 0, 'selection_calls': 0, 'delivery_qualified': False,
              'renderer_model': candidate.renderer_model}
    original = httpx.AsyncClient.send
    logging.disable(logging.CRITICAL)
    async def send(client, request, *a, **kw):
        if len(report['observed_async_http']) >= 4:
            raise RuntimeError('review transport budget exhausted')
        item = {'host': request.url.host}
        report['observed_async_http'].append(item)
        try:
            response = await original(client, request, *a, **kw)
            item['status'] = response.status_code
            return response
        except Exception as exc:
            item['error_class'] = type(exc).__name__
            raise
    httpx.AsyncClient.send = send
    try:
        report['logical_calls'] += 1
        route = {}
        response = await async_call_llm(task='alive_semantic_review', model=None,
            messages=[{'role': 'system', 'content': _REVIEW_PROMPT}, {'role': 'user', 'content':
                json.dumps({'meaning': serialize_meaning(document), 'candidate': candidate.text}, ensure_ascii=False)}],
            temperature=0, max_tokens=1500, timeout=40, route_info=route)
        text, model, provider = comparator._response(response, route)
        report.update(actual_reviewer_model=model, actual_reviewer_provider=provider)
        if not model.lower().startswith(args.reviewer_family):
            raise ValueError('actual reviewer is not the explicitly configured independent family')
        findings = comparator._findings(text)
        review = IndependentSemanticReview(review_id=operation, meaning_event_id=candidate.meaning_event_id,
            candidate_digest=candidate.digest, renderer_execution_id=candidate.renderer_execution_id,
            renderer_model=candidate.renderer_model, renderer_independence_domain=candidate.renderer_independence_domain,
            reviewer_kind=ReviewerKind.MODEL, reviewer_execution_id=operation,
            reviewer_model=model, reviewer_independence_domain=args.reviewer_family + '-family', **findings)
        receipt = store.record_review(candidate_event_id=candidate.event_id, review=review,
                                      actor='system:alive-shadow-reviewer')
        assert store.verify_review(journal.get(receipt.event_id)) is not None
        report.update(review_event_id=receipt.event_id, disposition=receipt.assessment.disposition.value,
                      review_findings=json.loads(text), safe_for_automatic_delivery=False)
    except Exception as exc:
        report['error_class'] = type(exc).__name__
    finally:
        httpx.AsyncClient.send = original
        report['no_action_attempt'] = not bool(journal.read(event_type='action.attempted'))
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models', action='store_true', required=True)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--candidate-event-id', required=True)
    parser.add_argument('--reviewer-family', choices=('qwen','claude','glm','gemini','gpt'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(exercise(parser.parse_args()))
