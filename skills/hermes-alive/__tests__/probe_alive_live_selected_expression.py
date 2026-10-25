#!/usr/bin/env python3
"""One opt-in actual expression from a retained, selected synthetic opportunity."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import EventEnvelope, ExperienceJournal, OpportunitySynthesizer, Sensitivity
from alive_kernel.opportunity_expression import OpportunityExpressionStore
from alive_kernel.semantic_comparator import SemanticComparator, _RENDER_PROMPT
from alive_kernel.semantic_rendering import serialize_meaning


async def exercise(args):
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True, exist_ok=False)
    journal = ExperienceJournal(args.journal)
    interpreter = OpportunitySynthesizer(journal)
    sources = interpreter.reader.active_evidence(subject='user:synthetic', clearance=Sensitivity.PRIVATE)
    if not sources or any(s.content['source'] != 'synthetic-public-fixture' for s in sources):
        raise ValueError('only explicitly synthetic discovery fixtures are allowed')
    store = OpportunityExpressionStore(journal, content_vault=interpreter.vault)
    owner = 'user:synthetic'
    meaning = store.define_for_selection(selection_event_id=args.selection_event_id, subject=owner)
    _source, document, _frame, _candidate = store._selection_context(
        selection_event_id=args.selection_event_id, meaning_event_id=meaning.event.event_id,
        subject=owner, observed_at=datetime.now(timezone.utc))
    comparator = SemanticComparator(store)
    style = comparator._style(owner, 'proactive_social')
    serialized = serialize_meaning(document)
    report = {'logical_calls': 0, 'observed_async_http': [], 'sends': 0,
              'interpretation_calls': 0, 'selection_calls': 0,
              'independent_review_executed': False, 'delivery_qualified': False,
              'selected_draft': document.atoms[0].text}
    operation = 'selected-expression-probe:' + interpreter.vault.digest_json(
        {'selection_event_id': args.selection_event_id})[:40]
    started = journal.append(EventEnvelope(event_id=operation + ':started',
        event_type='test.model_probe_started', source='synthetic-public-fixture',
        actor='system:alive-test', subject=owner, sensitivity=_source.event.sensitivity,
        causation_id=args.selection_event_id, payload={'logical_call_limit': 1,
            'raw_prompt_stored': False, 'raw_response_stored': False, 'sends_allowed': False}))
    if not started.created:
        raise ValueError('selected expression probe was already attempted')
    original = httpx.AsyncClient.send
    logging.disable(logging.CRITICAL)
    async def send(client, request, *a, **kw):
        if len(report['observed_async_http']) >= 4:
            raise RuntimeError('expression transport budget exhausted')
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
        comparator._revalidate(args.selection_event_id, meaning.event.event_id,
                                owner, serialized, 'proactive_social', style)
        report['logical_calls'] += 1
        route = {}
        response = await async_call_llm(task='alive_semantic_render', model=None,
            messages=[{'role': 'system', 'content': _RENDER_PROMPT}, {'role': 'user',
                'content': json.dumps({'meaning': serialized, 'presentation': style,
                                      'language': 'zh-CN'}, ensure_ascii=False)}],
            temperature=.3, max_tokens=1000, timeout=40, route_info=route)
        comparator._revalidate(args.selection_event_id, meaning.event.event_id,
                                owner, serialized, 'proactive_social', style)
        text, model, provider = comparator._response(response, route)
        if 'deepseek' not in model.lower():
            raise ValueError('actual renderer family is not known to this isolated experiment')
        candidate = store.record_model_candidate(selection_event_id=args.selection_event_id,
            meaning_event_id=meaning.event.event_id, subject=owner, text=text,
            renderer_execution_id=operation, renderer_model=model,
            renderer_independence_domain='deepseek-family')
        report.update(text=candidate.text, actual_model=model, actual_provider=provider,
                      candidate_event_id=candidate.event_id)
        assert store.resolve_model_candidate(candidate.event_id) is not None
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
    parser.add_argument('--selection-event-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(exercise(parser.parse_args()))
