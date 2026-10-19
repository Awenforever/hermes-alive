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


async def scenario(root, mode, *, return_ready=False, authority=ActionAuthority.USER_DELEGATED,
                   source_summary='Public workshop, details unverified.', draft_text=None,
                   grounding=False, single_family=False, render_prefix='', model_timeout_seconds=None):
    journal = ExperienceJournal(root / 'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic public fixture', title='Repair workshop',
        summary=source_summary, url='https://example.invalid/workshop',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    calls = []
    async def call(**kw):
        task = kw['task']
        calls.append(task)
        if model_timeout_seconds is not None and task in ('alive_source_support','alive_semantic_render','alive_semantic_review'):
            if task=='alive_source_support':
                assert 0 < kw['timeout'] <= model_timeout_seconds
            else:
                assert kw['timeout']==model_timeout_seconds
        model = 'synthetic/drafter'
        if task == 'alive_opportunity_candidates':
            value = {'candidates': []}
            if mode != 'silence':
                value['candidates'] = [{'agenda_item_id': source.agenda_item_id, 'kind': 'share',
                    'text': draft_text if draft_text is not None else source_summary, 'topic': 'repair',
                    'dimensions': {name: {'value': .1 if name in ('risk', 'urgency', 'interruption_cost')
                    else .8, 'reason': 'synthetic judgment'} for name in
                    ('user_value', 'urgency', 'novelty', 'confidence', 'risk', 'interruption_cost')}}]
        elif task == 'alive_source_support':
            kw['route_info']['provider'] = 'synthetic-provider'
            value = {'verdict':'supported', 'unsupported_claims':[], 'uncertainties':[],
                     'reason':'Synthetic positive fixture, not semantic qualification.'}
        elif task == 'alive_deliberation':
            candidates = json.loads(kw['messages'][1]['content'].split('\n', 1)[1])
            value = {'candidate_id': next(x['candidate_id'] for x in candidates
                if x['candidate_id'].startswith('opportunity-candidate:')), 'rationale': 'synthetic choice'}
        elif task == 'alive_semantic_render':
            if mode == 'cancel':
                raise asyncio.CancelledError()
            data = json.loads(kw['messages'][1]['content'])
            value = render_prefix + '\n'.join(atom['text'] for atom in data['meaning']['atoms'])
            kw['route_info']['provider'] = 'synthetic-render-provider'
            return SimpleNamespace(model='synthetic/renderer', choices=[SimpleNamespace(
                message=SimpleNamespace(content=value))])
        elif task == 'alive_semantic_review':
            data = json.loads(kw['messages'][1]['content'])
            value = {'atom_reviews': [{'atom_id': atom['atom_id'], 'preserved': True, 'risks': []}
                for atom in data['meaning']['atoms']], 'added_claims_detected': False,
                'speech_act_preserved': True, 'protected_literals_preserved': True}
            model = 'synthetic/renderer' if single_family else 'synthetic/reviewer'
            kw['route_info']['provider'] = 'synthetic-review-provider'
        else:
            raise AssertionError(task)
        return SimpleNamespace(model=model, choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])
    def domain(provider, model):
        if single_family: return 'synthetic-shared-family'
        return 'synthetic-render-family' if model.endswith('/renderer') else 'synthetic-review-family'
    params = dict(operation_id='one', subject='user:test', policy_context=PolicyContext(can_interrupt=True),
        call=call, authority=authority, resolve_domain=domain, language='en', grounding=grounding)
    if model_timeout_seconds is not None: params['model_timeout_seconds']=model_timeout_seconds
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
    count_before_invalid=len(calls)
    for invalid in (True,0,-1,241,float('nan'),float('inf'),'90'):
        try: await runtime.run(**{**params,'model_timeout_seconds':invalid})
        except ValueError: pass
        else: raise AssertionError('invalid model budget crossed planning boundary')
    assert len(calls)==count_before_invalid
    assert not result.delivery_authorized
    if single_family:
        assert result.review_disposition == 'correlated_review'
        record = journal.get(result.review_event_id)
        assert not record.event.payload['independent_review']
        assert runtime.store.verify_review(record) is None
    assert len(calls) == (1 if mode == 'silence' else 4 + int(grounding))
    assert (result.text is None) == (mode == 'silence')
    before = journal.last_sequence()
    async def forbidden(**_):
        raise AssertionError('completed expression spent on provider again')
    assert await ExpressionRuntime(ExperienceJournal(journal.path)).run(**{**params, 'call': forbidden}) == result
    assert journal.last_sequence() == before
    try:
        await runtime.run(**{**params,'call':forbidden,
            'model_timeout_seconds':91 if model_timeout_seconds==90 else 90})
    except ValueError: pass
    else: raise AssertionError('same operation rebound to a different stage budget')
    if return_ready:
        return journal, params, result
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
        asyncio.run(scenario(Path(folder) / 'grounded-share', 'share', grounding=True))
        asyncio.run(scenario(Path(folder) / 'single-family', 'share', grounding=True, single_family=True))
        asyncio.run(scenario(Path(folder) / 'explicit-budget', 'share', grounding=True, model_timeout_seconds=90))
    print('HERMES_ALIVE_KERNEL_EXPRESSION_RUNTIME_OK')
