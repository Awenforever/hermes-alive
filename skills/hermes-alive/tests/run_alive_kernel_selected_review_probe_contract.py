#!/usr/bin/env python3
"""Independent review accounting cannot qualify a same-family fallback."""
import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

from run_alive_kernel_opportunity_expression import scenario
spec = importlib.util.spec_from_file_location('review_probe',
    Path(__file__).with_name('probe_alive_live_selected_review.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
calls = []
mode = 'success'
async def fake(**kw):
    calls.append(kw)
    assert kw['task'] == 'alive_semantic_review'
    data = json.loads(kw['messages'][1]['content'])
    assert set(data) == {'meaning', 'candidate'}
    assert data['meaning']['atoms'][0]['kind'] == 'proposed_content'
    if mode == 'provider-error':
        raise PermissionError('synthetic inaccessible route')
    kw['route_info'].update(provider='synthetic-provider')
    model = 'claude-synthetic' if mode == 'success' else 'deepseek-flash'
    findings = {'atom_reviews': [{'atom_id': 'proposed-message', 'preserved': True, 'risks': []}],
        'added_claims_detected': False, 'speech_act_preserved': True, 'protected_literals_preserved': True}
    return SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(findings)))])
aux = ModuleType('agent.auxiliary_client')
aux.async_call_llm = fake
sys.modules['agent'] = ModuleType('agent')
sys.modules['agent.auxiliary_client'] = aux
http = ModuleType('httpx')
class Client:
    async def send(self, *a, **kw):
        raise AssertionError('offline probe attempted network')
http.AsyncClient = Client
sys.modules['httpx'] = http
with tempfile.TemporaryDirectory(prefix='alive-review-probe-contract-') as folder:
    for mode in ('success','same-family-fallback','provider-error'):
        root = Path(folder) / mode
        journal, candidate_id = asyncio.run(scenario(root / 'fixture', 'probe-fixture', 'user:synthetic'))
        args = SimpleNamespace(journal=journal, candidate_event_id=candidate_id,
                               output=root / 'report', reviewer_family='claude')
        spent = len(calls)
        with redirect_stdout(io.StringIO()):
            asyncio.run(probe.exercise(args))
        report = json.loads((args.output / 'report.json').read_text(encoding='utf-8'))
        assert len(calls) == spent + 1 and report['logical_calls'] == 1
        assert report['sends'] == report['renderer_calls'] == report['selection_calls'] == 0
        assert report['no_action_attempt'] and not report['delivery_qualified']
        assert not report['observed_async_http']
        if mode == 'success':
            assert report['disposition'] == 'shadow_eligible' and report['review_event_id']
            assert not report['safe_for_automatic_delivery']
        else:
            assert report['error_class'] and 'review_event_id' not in report
        args.output = root / 'repeated-report'
        try:
            with redirect_stdout(io.StringIO()):
                asyncio.run(probe.exercise(args))
        except Exception:
            pass
        else:
            raise AssertionError('duplicate review probe reran inference')
        assert len(calls) == spent + 1
print('HERMES_ALIVE_KERNEL_SELECTED_REVIEW_PROBE_CONTRACT_OK')
