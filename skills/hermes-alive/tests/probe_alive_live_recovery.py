#!/usr/bin/env python3
"""Opt-in synthetic completed-candidate recovery followed by one live selection."""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ActionAuthority, CognitionCycleCoordinator, ExperienceJournal,
                         OpportunitySynthesizer, PolicyContext, Sensitivity)


async def exercise(args):
    from agent.auxiliary_client import async_call_llm
    import httpx
    args.output.mkdir(parents=True, exist_ok=False)
    journal = ExperienceJournal(args.journal)
    interpreter = OpportunitySynthesizer(journal)
    sources = interpreter.reader.active_evidence(subject='user:synthetic', clearance=Sensitivity.PRIVATE)
    if not sources or any(s.content['source'] != 'synthetic-public-fixture' for s in sources):
        raise ValueError('only explicitly synthetic discovery fixtures are permitted')
    before = journal.last_sequence()
    draft = interpreter.load_completed(subject='user:synthetic', operation_id=args.operation_id,
                                        authority=ActionAuthority.USER_DELEGATED)
    assert journal.last_sequence() == before
    report = {'interpretation_model': draft.actual_model, 'recovered_count': len(draft.candidates),
              'interpretation_calls': 0, 'selection_calls': 0, 'httpx_async_requests': [], 'sends': 0}
    original = httpx.AsyncClient.send
    logging.disable(logging.CRITICAL)

    async def send(client, request, *a, **kw):
        if len(report['httpx_async_requests']) >= 6:
            raise RuntimeError('recovery experiment transport budget exhausted')
        item = {'host': request.url.host, 'status': None}
        report['httpx_async_requests'].append(item)
        try:
            response = await original(client, request, *a, **kw)
            item['status'] = response.status_code
            return response
        except Exception as exc:
            item['error_class'] = type(exc).__name__
            raise

    async def call(**kw):
        if report['selection_calls'] >= 1:
            raise RuntimeError('recovery experiment logical-call budget exhausted')
        report['selection_calls'] += 1
        route = {}
        response = await async_call_llm(**kw, timeout=40, route_info=route)
        report['route'] = route
        report['response_model'] = getattr(response, 'model', None)
        return response

    httpx.AsyncClient.send = send
    try:
        result = await CognitionCycleCoordinator(journal, content_vault=interpreter.vault).plan_with_model(
            cycle_id=args.cycle_id, subject='user:synthetic', candidates=draft.candidates,
            causation_id=draft.receipt_event_id, policy_context=PolicyContext(can_interrupt=True),
            call=call, attempts=1)
        report.update(selection=result.selection.candidate.action_kind.value,
                      selection_event_id=result.selection_event_id,
                      model_receipt_event_ids=list(result.model_receipt_event_ids))
    except Exception as exc:
        report['error_class'] = type(exc).__name__
    finally:
        httpx.AsyncClient.send = original
        report['no_action_attempt'] = not bool(journal.read(event_type='action.attempted'))
        (args.output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live-models', action='store_true', required=True)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--operation-id', required=True)
    parser.add_argument('--cycle-id', required=True)
    asyncio.run(exercise(parser.parse_args()))
