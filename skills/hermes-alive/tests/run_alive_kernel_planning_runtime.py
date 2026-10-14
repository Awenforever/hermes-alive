#!/usr/bin/env python3
"""Actual planning composition with synthetic model responses, no transport."""
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
from alive_kernel.planning_runtime import PlanningRuntime, PlanningRuntimeError
from alive_kernel.opportunity_synthesis import OpportunitySynthesisError
from alive_kernel.deliberation_synthesis import DeliberationSynthesisError


def response(value):
    return SimpleNamespace(model='synthetic/actual-model', choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value)))])


async def scenario(root, mode):
    path = root / 'experience.sqlite3'
    journal = ExperienceJournal(path)
    item = DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(
        source='synthetic public fixture', title='Workshop', summary='Unverified public workshop.',
        url='https://example.invalid/workshop', observed_at=datetime.now(timezone.utc)), subject='user:test')
    calls = []
    async def call(**kw):
        calls.append(kw['task'])
        if len(calls) == 1:
            if mode == 'incomplete':
                raise asyncio.CancelledError()
            if mode == 'abstain':
                return response({'candidates': [], 'abstentions': [
                    {'agenda_item_id': item.agenda_item_id, 'reason': 'Usefulness unknown.'}]})
            return response({'candidates': [{'agenda_item_id': item.agenda_item_id,
                'kind': 'share', 'text': 'Workshop; public notice unverified.', 'topic': 'repair',
                'dimensions': {n: {'value': .1 if n in ('risk', 'urgency', 'interruption_cost') else .8,
                'reason': 'synthetic judgment'} for n in
                ('user_value', 'urgency', 'novelty', 'confidence', 'risk', 'interruption_cost')}}]})
        if mode == 'incomplete-selection':
            raise asyncio.CancelledError()
        values = json.loads(kw['messages'][1]['content'].split('\n', 1)[1])
        candidate = next(x for x in values if x['candidate_id'].startswith('opportunity-candidate:'))
        return response({'candidate_id': candidate['candidate_id'], 'rationale': 'synthetic selection'})
    params = dict(operation_id='one', subject='user:test',
        policy_context=PolicyContext(can_interrupt=mode != 'protected'), call=call,
        authority=ActionAuthority.USER_DELEGATED)
    runtime = PlanningRuntime(journal)
    for invalid in ({'requested_model': 'invalid model\nprivate data'},
                    {'policy_context': PolicyContext(can_interrupt='false')}):
        before = journal.last_sequence()
        try:
            await runtime.run(**{**params, **invalid})
        except PlanningRuntimeError:
            pass
        else:
            raise AssertionError('invalid host contract entered durable planning')
        assert journal.last_sequence() == before and not calls
    if mode in ('incomplete', 'incomplete-selection'):
        try:
            await runtime.run(**params)
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError('cancelled provider became successful planning')
        try:
            await PlanningRuntime(ExperienceJournal(path)).run(**params)
        except (OpportunitySynthesisError, DeliberationSynthesisError):
            pass
        else:
            raise AssertionError('unfinished provider operation silently retried')
        assert len(calls) == (1 if mode == 'incomplete' else 2)
        return
    result = await runtime.run(**params)
    assert result.action_kind == ('share' if mode == 'share' else 'silence')
    assert len(calls) == (2 if mode == 'share' else 1)
    async def forbidden(**_):
        raise AssertionError('completed cycle called a provider during recovery')
    before = journal.last_sequence()
    reopened = PlanningRuntime(ExperienceJournal(path))
    assert await reopened.run(**{**params, 'call': forbidden}) == result
    assert journal.last_sequence() == before
    try:
        await reopened.run(**{**params, 'call': forbidden,
                              'policy_context': PolicyContext(can_interrupt=mode == 'protected')})
    except PlanningRuntimeError:
        pass
    else:
        raise AssertionError('same operation accepted changed host policy')
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-planning-runtime-') as folder:
        for mode in ('share', 'protected', 'abstain', 'incomplete', 'incomplete-selection'):
            asyncio.run(scenario(Path(folder) / mode, mode))
    print('HERMES_ALIVE_KERNEL_PLANNING_RUNTIME_OK')
