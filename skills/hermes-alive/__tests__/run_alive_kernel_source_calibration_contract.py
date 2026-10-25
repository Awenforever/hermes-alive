#!/usr/bin/env python3
"""Check accounting/label isolation; fake findings do not validate semantics."""
import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

spec = importlib.util.spec_from_file_location('source_calibration',
    Path(__file__).with_name('probe_alive_live_source_calibration.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
calls = []
mode = 'expectations'
async def fake(**kw):
    calls.append(kw)
    assert kw['task'] == 'alive_source_support'
    assert kw['messages'][0]['content'] in (probe.PROMPT, probe.BASELINE_PROMPT, probe.CLAIM_EVIDENCE_PROMPT)
    data = json.loads(kw['messages'][1]['content'])
    case_id = data['candidate']['id']
    fixture = next(x for x in (*probe.cases(), *probe.comparison_cases()) if x[0] == case_id)
    assert data == probe.snapshot(case_id, fixture[2], fixture[3])
    assert 'authored_acceptable_verdicts' not in kw['messages'][1]['content']
    if mode == 'provider-error':
        raise PermissionError('synthetic model permission failure')
    verdict = fixture[4][0] if mode == 'expectations' else 'supported'
    findings = {'verdict': verdict, 'unsupported_claims': ['synthetic problem'] if verdict == 'unsupported' else [],
                'uncertainties': [], 'reason': 'synthetic reason'}
    if mode == 'invalid':
        findings['unsupported_claims'] = ['contradictory result']
    kw['route_info'].update(provider='synthetic-provider')
    return SimpleNamespace(model='deepseek-flash' if mode == 'wrong-family' else 'claude-synthetic',
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(findings)))])
aux = ModuleType('agent.auxiliary_client')
aux.async_call_llm = fake
sys.modules['agent'] = ModuleType('agent')
sys.modules['agent.auxiliary_client'] = aux
http = ModuleType('httpx')
class Client:
    async def send(self, *args, **kwargs):
        raise AssertionError('offline source calibration attempted network')
http.AsyncClient = Client
sys.modules['httpx'] = http

with tempfile.TemporaryDirectory(prefix='alive-source-calibration-') as folder:
    for mode in ('expectations', 'all-accept', 'invalid', 'wrong-family', 'provider-error', 'comparison'):
        root = Path(folder) / mode
        args = SimpleNamespace(output=root / 'results', journal=root / 'journal.sqlite3',
            reviewer_family='claude', comparison=mode=='comparison')
        spent = len(calls)
        with redirect_stdout(io.StringIO()):
            asyncio.run(probe.exercise(args))
        report = json.loads((args.output / 'report.json').read_text(encoding='utf-8'))
        assert report['logical_calls'] == 8 and len(calls) == spent + 8
        assert report['sends'] == 0 and not report['delivery_qualified'] and not report['human_gold']
        assert not report['production_config_changed'] and not report['observed_async_http']
        if mode == 'expectations':
            assert report['summary'] == {'completed': 8, 'errors': 0, 'authored_unsupported_acceptances': 0,
                'grounded_nonacceptances': 0, 'expectation_mismatches': 0}
        elif mode == 'all-accept':
            assert report['summary']['authored_unsupported_acceptances'] == 6
        elif mode == 'comparison':
            assert report['summary']['authored_unsupported_acceptances'] == 4
            assert report['candidate_origin'] == 'one-retained-generated-and-three-authored'
            assert [(x['case_id'],x['method']) for x in report['cases']] == [
                ('09','baseline'),('09','claim-evidence'),('10','claim-evidence'),('10','baseline'),
                ('11','baseline'),('11','claim-evidence'),('12','claim-evidence'),('12','baseline')]
        else:
            assert report['summary']['errors'] == 8 and report['summary']['completed'] == 0
            assert all('raw_review' in item for item in report['cases']) if mode != 'provider-error' else all(
                'raw_review' not in item for item in report['cases'])
        args.output = root / 'another-output'
        try:
            with redirect_stdout(io.StringIO()):
                asyncio.run(probe.exercise(args))
        except ValueError:
            pass
        else:
            raise AssertionError('spent calibration journal allowed more calls')
        assert len(calls) == spent + 8
print('HERMES_ALIVE_KERNEL_SOURCE_CALIBRATION_CONTRACT_OK')
