#!/usr/bin/env python3
"""Offline accounting for the opt-in paired expression experiment."""
import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

spec = importlib.util.spec_from_file_location('natural_probe',
    Path(__file__).with_name('probe_alive_live_natural.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
calls = []
async def fake(**kw):
    calls.append(kw)
    assert kw['task'] == 'alive_semantic_render'
    data = json.loads(kw['messages'][1]['content'])
    assert data['language'] == 'zh-CN'
    assert '合成' not in data['meaning']['atoms'][0]['text']
    assert data['presentation']['values']['verbosity'] == .2
    kw['route_info'].update(provider='synthetic-provider')
    return SimpleNamespace(model='synthetic-model', choices=[SimpleNamespace(message=SimpleNamespace(
        content='社区举办维修分享活动，参加人数尚未确定。详情：https://example.invalid/repair'))])
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
with tempfile.TemporaryDirectory(prefix='alive-natural-probe-contract-') as folder:
    output = Path(folder) / 'results'
    with redirect_stdout(io.StringIO()):
        asyncio.run(probe.exercise(SimpleNamespace(output=output)))
    report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
    assert len(calls) == report['logical_calls'] == 2
    assert not report['observed_async_http'] and not report['sends']
    assert not report['selection_executed'] and not report['independent_review_executed']
    assert all(not c['delivery_qualified'] and c['structural_fidelity'] == 'review_required'
               for c in report['cases'])
print('HERMES_ALIVE_KERNEL_NATURAL_PROBE_CONTRACT_OK')
