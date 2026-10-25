#!/usr/bin/env python3
"""Offline qualification of opt-in probe composition and its spend cap."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

path = Path(__file__).with_name('probe_alive_live_opportunity.py')
spec = importlib.util.spec_from_file_location('alive_live_probe', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
calls = []


async def fake(**kw):
    calls.append(kw['task'])
    if kw.get('provider') == 'synthetic-fallback':
        assert kw['model'] == 'configured-model'
        assert kw['base_url'] == 'https://example.invalid/v1'
        assert kw['api_key'] == 'synthetic-test-key'
    kw['route_info'].update(provider='synthetic', model='fake-context-model')
    if kw['task'] == 'alive_opportunity_candidates':
        data = json.loads(kw['messages'][1]['content'])
        assert data['user_context'], 'synthetic preference was not retrieved'
        candidate = {'agenda_item_id': data['opportunities'][0]['agenda_item_id'], 'kind': 'share',
                     'text': 'Synthetic repair workshop: https://example.invalid/repair', 'topic': 'repair',
                     'dimensions': {n: {'value': .1 if n in ('risk', 'interruption_cost', 'urgency') else .9,
                                        'reason': 'synthetic judgment'} for n in (
                         'user_value', 'urgency', 'novelty', 'confidence', 'interruption_cost', 'risk')}}
        value = {'candidates': [] if 'rumor' in data['opportunities'][0]['summary_excerpt'] else [candidate]}
    else:
        data = json.loads(kw['messages'][1]['content'].split('\n', 1)[1])
        selected = next(x for x in data if x['action_kind'] == 'share')
        value = {'candidate_id': selected['candidate_id'], 'rationale': 'synthetic choice'}
    return SimpleNamespace(model='fake-context-model', choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value)))])


aux = ModuleType('agent.auxiliary_client')
aux.async_call_llm = fake
sys.modules['agent'] = ModuleType('agent')
sys.modules['agent.auxiliary_client'] = aux
http = ModuleType('httpx')
class Client:
    async def send(self, *a, **kw):
        raise AssertionError('offline probe invoked network')
http.AsyncClient = Client
sys.modules['httpx'] = http

with tempfile.TemporaryDirectory(prefix='alive-probe-contract-') as folder:
    root = Path(folder)
    args = SimpleNamespace(output=root/'composed', logical_call_limit=3,
                           scenarios=['grounded', 'uncertain'], synthetic_profile=True, configured_fallback=False)
    asyncio.run(probe.exercise(args))
    report = json.loads((args.output/'report.json').read_text(encoding='utf-8'))
    assert report['logical_calls'] == 3 and len(calls) == 3
    scenarios = [x for x in report['results'] if 'scenario' in x]
    assert scenarios[0]['candidate_count'] == 1 and scenarios[0]['selection'] == 'share'
    assert scenarios[1]['candidate_count'] == 0
    assert all(x['no_action_attempt'] for x in scenarios)
    calls.clear()
    args.output = root/'bounded'
    args.logical_call_limit = 1
    args.scenarios = ['grounded']
    asyncio.run(probe.exercise(args))
    report = json.loads((args.output/'report.json').read_text(encoding='utf-8'))
    assert report['logical_calls'] == 1 and calls == ['alive_opportunity_candidates']
    assert report['results'][-1]['selection_not_run_reason'] == 'logical_budget'
    assert report['sends'] == 0 and report['human_quality_qualified'] is False
    config = ModuleType('hermes_cli.config')
    config.load_config_readonly = lambda: {}
    fallback = ModuleType('hermes_cli.fallback_config')
    fallback.get_fallback_chain = lambda _: [{'provider': 'synthetic-fallback',
        'model': 'configured-model', 'base_url': 'https://example.invalid/v1', 'api_key': 'synthetic-test-key'}]
    sys.modules['hermes_cli'] = ModuleType('hermes_cli')
    sys.modules['hermes_cli.config'] = config
    sys.modules['hermes_cli.fallback_config'] = fallback
    calls.clear()
    args.output = root/'configured-fallback'
    args.configured_fallback = True
    asyncio.run(probe.exercise(args))
    assert calls == ['alive_opportunity_candidates']
print('HERMES_ALIVE_KERNEL_LIVE_PROBE_CONTRACT_OK')
