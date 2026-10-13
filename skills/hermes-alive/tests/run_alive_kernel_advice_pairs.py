#!/usr/bin/env python3
"""Offline paired-probe parity/accounting; not a model-benefit experiment."""
import asyncio
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx
from probe_alive_live_advice_pairs import exercise, CASES


async def check(root):
    seen = []
    async def fake(**kw):
        data = json.loads(kw['messages'][1]['content'])
        seen.append(data)
        assert data['learned_advisory'][0]['support_mass'] + data['learned_advisory'][0]['opposition_mass'] == .25
        kw['route_info']['provider'] = 'synthetic-provider'
        value = {'candidates': [{'agenda_item_id': data['opportunities'][0]['agenda_item_id'], 'kind': 'ask',
            'text': 'Synthetic optional question.', 'topic': 'synthetic', 'dimensions': {
                name: {'value': .1 if name in ('risk', 'urgency', 'interruption_cost') else .5,
                       'reason': 'synthetic model judgment'}
                for name in ('user_value', 'urgency', 'novelty', 'confidence', 'interruption_cost', 'risk')}}]}
        if len(seen) == 1:
            value['candidates'] = []
        elif len(seen) == 2:
            value['candidates'][0]['dimensions']['risk']['reason'] = 'x' * 513
        return SimpleNamespace(model='synthetic/interpreter', choices=[
            SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])
    async def forbidden(*a, **kw):
        raise AssertionError('offline paired probe attempted HTTP')
    package = ModuleType('agent')
    package.__path__ = []
    auxiliary = ModuleType('agent.auxiliary_client')
    auxiliary.async_call_llm = fake
    old_logging = logging.root.manager.disable
    try:
        with patch.dict(sys.modules, {'agent': package, 'agent.auxiliary_client': auxiliary}), \
             patch.object(httpx.AsyncClient, 'send', forbidden):
            await exercise(SimpleNamespace(output=root/'results', model=None))
    finally:
        logging.disable(old_logging)
    report = json.loads((root/'results/report.json').read_text(encoding='utf-8'))
    assert len(seen) == report['logical_calls'] == 6 and report['observed_async_http'] == []
    assert all(case['id'] not in json.dumps(value) for value in seen for case in CASES)
    assert not report['utility_improvement_proven'] and not report['automatic_learning_authority']
    for pair in report['pairs']:
        assert pair['matched_inputs_except_notes_and_clock']
        assert all(a['completed'] and a['no_new_preference_signals'] and a['no_external_dispatch'] for a in pair['arms'])
        arms = {a['arm']: a for a in pair['arms']}
        assert 'evidence_notes' in arms['qualified']['input']['learned_advisory'][0]
        assert 'evidence_notes' not in arms['flattened']['input']['learned_advisory'][0]
        assert all(c['authority'] == 'none' for a in pair['arms'] for c in a['candidates'])
    assert [p['arms'][0]['arm'] for p in report['pairs']] == ['qualified','flattened','qualified']
    assert report['pairs'][0]['arms'][0]['decision_observation'] == 'model_empty'
    assert report['pairs'][0]['arms'][1]['decision_observation'] == 'all_rejected'
    assert report['pairs'][0]['arms'][0]['model_proposal_count'] == 0
    assert report['pairs'][0]['arms'][1]['model_proposal_count'] == 1


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-advice-pairs-') as directory:
        asyncio.run(check(Path(directory)))
    print('HERMES_ALIVE_KERNEL_ADVICE_PAIRS_OK')
