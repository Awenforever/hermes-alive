#!/usr/bin/env python3
"""Opt-in real-model history ablation, synthetic evidence only, no transport."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (DiscoveryCandidate, DiscoveryOpportunityIngestor, EventEnvelope,
    MemoryProjection, MemoryProposal, MemoryKind, MemoryAuthority)
from alive_kernel.events import _thaw_json
from alive_kernel.events import Sensitivity
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer
from run_alive_kernel_expression_runtime import scenario

BASELINE = ('Synthetic organizer notice: a free online recording teaches hand-sewing '
    'repairs for torn clothing. Available anytime, no registration or deadline. '
    'Source: https://example.invalid/workshop. It does not teach electrical repair.')
CASES = (
    ('unchanged', None),
    ('development', 'Synthetic new organizer notice: a new free online module now '
     'demonstrates replacing a broken jacket zipper step by step, including tool '
     'selection and safety. This is new material beyond the prior hand-sewing recording.'),
    ('correction', 'Synthetic organizer correction: the previously described recording '
     'is NOT free; access costs $30. The earlier free-access claim was wrong. '
     'The material still covers hand-sewing; no registration deadline exists.'),
)


async def exercise(output, dry_run=False):
    if dry_run:
        from types import SimpleNamespace
        async def async_call_llm(**_):
            return SimpleNamespace(model='synthetic/dry-run', choices=[SimpleNamespace(
                message=SimpleNamespace(content='{"candidates":[]}'))])
    else:
        from agent.auxiliary_client import async_call_llm
    import httpx
    output.mkdir(parents=True, exist_ok=False)
    logging.disable(logging.CRITICAL)
    logical, requests, results = 0, [], []
    original_send = httpx.AsyncClient.send
    async def tracked_send(client, request, *args, **kwargs):
        if len(requests) >= 18:
            raise RuntimeError('probe HTTP budget exhausted')
        item = {'call': logical, 'host': request.url.host, 'status': None}
        requests.append(item)
        try:
            response = await original_send(client, request, *args, **kwargs)
            item['status'] = response.status_code
            return response
        except Exception as exc:
            item['error_class'] = type(exc).__name__
            raise
    async def call(**kwargs):
        nonlocal logical
        if logical >= 6:
            raise RuntimeError('probe logical budget exhausted')
        logical += 1
        return await async_call_llm(**kwargs, timeout=40)
    httpx.AsyncClient.send = tracked_send
    try:
        for name, update in CASES:
            for with_history in (False, True):
                label = name + ('-history' if with_history else '-control')
                journal, _, _ = await scenario(output / label, 'share', return_ready=True,
                    source_summary=BASELINE, draft_text=BASELINE)
                reader = DiscoveryOpportunityIngestor(journal)
                statement = journal.append(EventEnvelope(event_type='conversation.inbound',
                    source='synthetic-fixture', actor='user:test', subject='user:test',
                    payload={'synthetic': True}))
                memory = MemoryProjection(journal)
                memory.append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,
                    subject='user:test', predicate='profile.content_preferences',
                    value='I enjoy practical clothing repair. Do not repeat the same tips. '
                          'Meaningful new methods and corrections are welcome.',
                    authority=MemoryAuthority.USER_EXPLICIT,
                    source_event_ids=(statement.event.event_id,), confidence=1), actor='user:test')
                if update:
                    reader.ingest(DiscoveryCandidate(source='synthetic organizer', title=name,
                        summary=update, url='https://example.invalid/' + name,
                        observed_at=datetime.now(timezone.utc)), subject='user:test')
                synthesizer = OpportunitySynthesizer(journal, content_vault=reader.vault)
                if not with_history:
                    # Explicit experimental ablation only; not a public setting.
                    class EmptyHistory:
                        def read(self, **_): return ()
                    synthesizer.history_reader = EmptyHistory()
                history_count = len(synthesizer.history_reader.read(subject='user:test',
                    clearance=Sensitivity.PRIVATE))
                assert history_count == int(with_history)
                entry = {'case': name, 'history': with_history, 'history_entries': history_count}
                try:
                    result = await synthesizer.run(subject='user:test', operation_id='novelty-' + label,
                        call=call, timeout_seconds=90)
                    entry.update(actual_model=result.actual_model,
                        drafts=[_thaw_json(c.content) for c in result.candidates],
                        abstentions=[a.reason for a in result.abstentions],
                        rejected_count=result.rejected_count)
                except Exception as exc:
                    entry['error_class'] = type(exc).__name__
                assert not journal.read(event_type='action.attempted')
                assert not journal.read(event_type='dispatch.started')
                results.append(entry)
    finally:
        httpx.AsyncClient.send = original_send
        report = {'logical_calls': logical, 'http_requests': requests,
            'results': results, 'sends': 0, 'semantic_quality_qualified': False}
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'logical_calls': logical, 'http_requests': len(requests), 'sends': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-live-models', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    asyncio.run(exercise(args.output, args.dry_run))
