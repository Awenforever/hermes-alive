#!/usr/bin/env python3
"""Offline accounting and label isolation; fake outputs are not quality evidence."""
import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

spec = importlib.util.spec_from_file_location('calibration_probe',
    Path(__file__).with_name('probe_alive_live_review_calibration.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
calls = []
mode = 'authored-expectations'
async def fake(**kw):
    calls.append(kw)
    assert kw['task'] == 'alive_semantic_review'
    data = json.loads(kw['messages'][1]['content'])
    assert set(data) == {'meaning','candidate'}
    assert 'authored_expected' not in kw['messages'][1]['content']
    case_id = data['meaning']['message_id'].split('-')[-1]
    fixture = next(x for x in probe.cases() if x[0] == case_id)
    assert data['candidate'] == fixture[2]
    assert data['meaning']['atoms'][0]['text'] == fixture[1]
    if mode == 'provider-error':
        raise PermissionError('synthetic permission failure')
    preserved = fixture[3] if mode == 'authored-expectations' else True
    findings = {'atom_reviews': [{'atom_id': 'proposed-message', 'preserved': preserved,
        'risks': [] if preserved else ['contradiction']}], 'added_claims_detected': False,
        'speech_act_preserved': True, 'protected_literals_preserved': True}
    if mode == 'invalid-atom':
        findings['atom_reviews'][0].update(preserved=True, risks=['contradiction'])
    kw['route_info'].update(provider='synthetic-provider')
    return SimpleNamespace(model='deepseek-flash' if mode == 'wrong-family' else 'claude-synthetic',
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(findings)))])
aux = ModuleType('agent.auxiliary_client')
aux.async_call_llm = fake
sys.modules['agent'] = ModuleType('agent')
sys.modules['agent.auxiliary_client'] = aux
http = ModuleType('httpx')
class Client:
    async def send(self, *a, **kw):
        raise AssertionError('offline calibration attempted network')
http.AsyncClient = Client
sys.modules['httpx'] = http

with tempfile.TemporaryDirectory(prefix='alive-review-calibration-') as folder:
    for mode in ('authored-expectations', 'all-accept', 'wrong-family', 'provider-error', 'invalid-atom'):
        root = Path(folder) / mode
        args = SimpleNamespace(output=root / 'results', journal=root / 'journal.sqlite3',
                               reviewer_family='claude')
        spent = len(calls)
        with redirect_stdout(io.StringIO()):
            asyncio.run(probe.exercise(args))
        report = json.loads((args.output / 'report.json').read_text(encoding='utf-8'))
        assert len(calls) == spent + 8 and report['logical_calls'] == 8
        assert not report['observed_async_http']
        assert report['sends'] == 0 and not report['delivery_qualified'] and not report['human_gold']
        assert not report['production_config_changed']
        summary = report['summary']
        if mode == 'authored-expectations':
            assert summary == {'completed': 8, 'errors': 0, 'unsafe_acceptances': 0,
                               'faithful_rejections': 0}
        elif mode == 'all-accept':
            assert summary['unsafe_acceptances'] == 6 and summary['completed'] == 8
        else:
            assert summary['errors'] == 8 and summary['completed'] == 0
        for item in report['cases']:
            if mode == 'invalid-atom':
                assert item['error_stage'] == 'findings_contract'
                assert json.loads(item['raw_review'])['atom_reviews'][0]['preserved']
                assert 'accepted' not in item
            elif mode == 'provider-error':
                assert item['error_stage'] == 'provider_call' and 'raw_review' not in item
        args.output = root / 'another-output'
        try:
            with redirect_stdout(io.StringIO()):
                asyncio.run(probe.exercise(args))
        except ValueError:
            pass
        else:
            raise AssertionError('calibration fence permitted repeat inference')
        assert len(calls) == spent + 8
    root = Path(folder) / 'unrelated-journal'
    journal = probe.ExperienceJournal(root / 'journal.sqlite3')
    journal.append(probe.EventEnvelope(event_type='runtime.observation',
        source='unrelated-runtime', subject='user:other', actor='system:test', payload={}))
    spent = len(calls)
    try:
        with redirect_stdout(io.StringIO()):
            asyncio.run(probe.exercise(SimpleNamespace(output=root / 'results',
                journal=journal.path, reviewer_family='claude')))
    except ValueError:
        pass
    else:
        raise AssertionError('calibration appended to an unrelated existing journal')
    assert len(calls) == spent and len(journal.read()) == 1
print('HERMES_ALIVE_KERNEL_REVIEW_CALIBRATION_CONTRACT_OK')
