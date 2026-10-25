#!/usr/bin/env python3
"""Opt-in synthetic expression experiment, not independent review or delivery."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path

from run_alive_kernel_natural_presentation import fixture
from alive_kernel import (PresentationAuthority, PresentationDimension, PresentationPreference,
                          RendererClass, assess_fidelity)
from alive_kernel.semantic_comparator import SemanticComparator, _RENDER_PROMPT
from alive_kernel.semantic_rendering import serialize_meaning


async def exercise(args):
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'logical_calls': 0, 'observed_async_http': [], 'cases': [], 'sends': 0,
              'selection_executed': False, 'independent_review_executed': False,
              'experiment': 'isolated synthetic prompt comparison only'}
    original = httpx.AsyncClient.send
    logging.disable(logging.CRITICAL)
    async def send(client, request, *a, **kw):
        if len(report['observed_async_http']) >= 8:
            raise RuntimeError('transport budget exhausted')
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
        for name, warmth, formality in (('warm-brief', .85, .2), ('formal-brief', .2, .85)):
            journal, store, owner, evidence, meaning_id, _candidate = fixture(args.output / name)
            comparator = SemanticComparator(store)
            for dimension, value in ((PresentationDimension.WARMTH, warmth),
                                     (PresentationDimension.FORMALITY, formality),
                                     (PresentationDimension.VERBOSITY, .2)):
                now = datetime.now(timezone.utc)
                comparator.presentation.append_preference(PresentationPreference(owner, dimension, value,
                    PresentationAuthority.USER_EXPLICIT, 'user_requested', now, now + timedelta(hours=1),
                    source_event_id=evidence.event_id), actor=owner)
            meaning = store.meanings.resolve(meaning_id)
            style = comparator._style(owner, 'proactive_social')
            prompt = json.dumps({'meaning': serialize_meaning(meaning), 'presentation': style,
                                 'language': 'zh-CN'}, ensure_ascii=False, separators=(',', ':'))
            case = {'name': name, 'synthetic_input': serialize_meaning(meaning), 'style': style}
            report['cases'].append(case)
            if report['logical_calls'] >= 2:
                raise RuntimeError('logical budget exhausted')
            report['logical_calls'] += 1
            route = {}
            try:
                response = await async_call_llm(task='alive_semantic_render', model=None,
                    messages=[{'role': 'system', 'content': _RENDER_PROMPT},
                              {'role': 'user', 'content': prompt}],
                    temperature=.3, max_tokens=1000, timeout=40, route_info=route)
                text, model, provider = comparator._response(response, route)
                fidelity = assess_fidelity(meaning, text, renderer_class=RendererClass.MODEL_CANDIDATE)
                case.update(text=text, actual_model=model, actual_provider=provider,
                    structural_fidelity=fidelity.status.value,
                    missing_literals=list(fidelity.missing_literals),
                    delivery_qualified=False)
            except Exception as exc:
                case['error_class'] = type(exc).__name__
            assert not journal.read(event_type='action.attempted')
    finally:
        httpx.AsyncClient.send = original
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(exercise(parser.parse_args()))
