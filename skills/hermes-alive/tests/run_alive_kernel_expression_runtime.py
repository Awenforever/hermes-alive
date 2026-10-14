#!/usr/bin/env python3
"""Composed planning/expression with fake model families and no transport."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ActionAuthority, DiscoveryCandidate, DiscoveryOpportunityIngestor,
                          ExperienceJournal, PolicyContext)
from alive_kernel.expression_runtime import ExpressionRuntime, ExpressionRuntimeError
from alive_kernel.semantic_review import SemanticReviewError


async def scenario(root, mode):
    journal = ExperienceJournal(root / 'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic public fixture', title='Repair workshop',
        summary='Public workshop, details unverified.', url='https://example.invalid/workshop',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    calls = []
    async def call(**kw):
        task = kw['task']
        calls.append(task)
        model = 'synthetic/drafter'
        if task == 'alive_opportunity_candidates':
            value = {'candidates': []}
            if mode != 'silence':
                value['candidates'] = [{'agenda_item_id': source.agenda_item_id, 'kind': 'share',
                    'text': 'Public workshop, details unverified.', 'topic': 'repair',
                    'dimensions': {name: {'value': .1 if name in ('risk', 'urgency', 'interruption_cost')
                    else .8, 'reason': 'synthetic judgment'} for name in
                    ('user_value', 'urgency', 'novelty', 'confidence', 'risk', 'interruption_cost')}}]
        elif task == 'alive_deliberation':
            candidates = json.loads(kw['messages'][1]['content'].split('\n', 1)[1])
            value = {'candidate_id': next(x['candidate_id'] for x in candidates
                if x['candidate_id'].startswith('opportunity-candidate:')), 'rationale': 'synthetic choice'}
        elif task == 'alive_semantic_render':
            if mode == 'cancel':
                raise asyncio.CancelledError()
            data = json.loads(kw['messages'][1]['content'])
            value = '\n'.join(atom['text'] for atom in data['meaning']['atoms'])
            kw['route_info']['provider'] = 'synthetic-render-provider'
            return SimpleNamespace(model='synthetic/renderer', choices=[SimpleNamespace(
                message=SimpleNamespace(content=value))])
        elif task == 'alive_semantic_review':
            data = json.loads(kw['messages'][1]['content'])
            value = {'atom_reviews': [{'atom_id': atom['atom_id'], 'preserved': True, 'risks': []}
                for atom in data['meaning']['atoms']], 'added_claims_detected': False,
                'speech_act_preserved': True, 'protected_literals_preserved': True}
            model = 'synthetic/reviewer'
            kw['route_info']['provider'] = 'synthetic-review-provider'
        else:
            raise AssertionError(task)
        return SimpleNamespace(model=model, choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])
    def domain(provider, model):
        return 'synthetic-render-family' if model.endswith('/renderer') else 'synthetic-review-family'
    params = dict(operation_id='one', subject='user:test', policy_context=PolicyContext(can_interrupt=True),
        call=call, authority=ActionAuthority.USER_DELEGATED, resolve_domain=domain, language='en')
    class InterruptedCommitRuntime(ExpressionRuntime):
        def _bound_record(self, event_id, kind, *args):
            if kind == 'expression.runtime_completed':
                raise RuntimeError('synthetic crash before outer completion')
            return super()._bound_record(event_id, kind, *args)
    runtime = InterruptedCommitRuntime(journal) if mode == 'commit-crash' else ExpressionRuntime(journal)
    if mode == 'cancel':
        try:
            await runtime.run(**params)
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError('cancelled expression returned success')
        count = len(calls)
        try:
            await ExpressionRuntime(ExperienceJournal(journal.path)).run(**params)
        except ExpressionRuntimeError:
            pass
        else:
            raise AssertionError('unfinished expression retried implicitly')
        assert len(calls) == count == 3
        return
    if mode == 'commit-crash':
        try:
            await runtime.run(**params)
        except RuntimeError as exc:
            assert str(exc) == 'synthetic crash before outer completion'
        else:
            raise AssertionError('outer completion crash was not injected')
        runtime = ExpressionRuntime(ExperienceJournal(journal.path))
    result = await runtime.run(**params)
    assert not result.delivery_authorized
    assert len(calls) == (1 if mode == 'silence' else 4)
    assert (result.text is None) == (mode == 'silence')
    before = journal.last_sequence()
    async def forbidden(**_):
        raise AssertionError('completed expression spent on provider again')
    assert await ExpressionRuntime(ExperienceJournal(journal.path)).run(**{**params, 'call': forbidden}) == result
    assert journal.last_sequence() == before
    if mode != 'silence':
        assert 'https://example.invalid/workshop' in result.text
        try:
            await runtime.run(**{**params, 'call': forbidden, 'language': 'zh'})
        except ExpressionRuntimeError:
            pass
        else:
            raise AssertionError('changed language reused expression')
        reader.vault.erase_item('opportunity-proposals:' + result.planning.interpretation_event_id
            .removeprefix('opportunity.synthesis:').removesuffix(':completed'))
        try:
            await runtime.run(**{**params, 'call': forbidden})
        except ValueError:
            pass
        else:
            raise AssertionError('erased interpretation still supported expression')
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-expression-runtime-') as folder:
        for mode in ('share', 'silence', 'cancel', 'commit-crash'):
            asyncio.run(scenario(Path(folder) / mode, mode))
    print('HERMES_ALIVE_KERNEL_EXPRESSION_RUNTIME_OK')
