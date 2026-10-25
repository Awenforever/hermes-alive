#!/usr/bin/env python3
"""Offline probe plumbing/accounting only, not evidence of real model adaptation."""
import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace

spec=importlib.util.spec_from_file_location('learning_probe',Path(__file__).with_name('probe_alive_live_learning.py'))
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
calls=[]
mode='success'
async def fake(**kw):
    data=json.loads(kw['messages'][1]['content'])
    calls.append(data)
    if mode=='failure':
        raise PermissionError('synthetic route failure')
    kw['route_info'].update(provider='synthetic-provider')
    value={'candidates':[{'agenda_item_id':data['opportunities'][0]['agenda_item_id'],
        'kind':'share','text':'synthetic draft','topic':'repair','dimensions':{
            n:{'value':.1 if n in ('risk','interruption_cost') else .8,'reason':'synthetic judgment'}
            for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}
    return SimpleNamespace(model='synthetic-interpreter',choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])
aux=ModuleType('agent.auxiliary_client')
aux.async_call_llm=fake
sys.modules['agent']=ModuleType('agent')
sys.modules['agent.auxiliary_client']=aux
http=ModuleType('httpx')
class Client:
    async def send(self,*a,**kw):
        raise AssertionError('offline learning probe attempted network')
http.AsyncClient=Client
sys.modules['httpx']=http
with tempfile.TemporaryDirectory(prefix='alive-live-learning-contract-') as folder:
    for mode in ('success','failure'):
        root=Path(folder)/mode
        args=SimpleNamespace(journal=root/'journal.sqlite3',output=root/'results')
        before=len(calls)
        with redirect_stdout(io.StringIO()):
            asyncio.run(probe.exercise(args))
        report=json.loads((args.output/'report.json').read_text(encoding='utf-8'))
        assert report['logical_calls']==3 and len(calls)==before+3
        assert calls[-3]['learned_advisory']==[]
        assert len(calls[-2]['learned_advisory'])==1 and len(calls[-1]['learned_advisory'])==1
        assert any('detailed explanation' in x['value'] for x in calls[-1]['user_context'])
        assert report['no_external_dispatch'] and report['sends']==0 and not report['delivery_qualified']
        assert not report['observed_async_http']
        if mode=='success':
            assert all(c['candidates'][0]['authority']=='none' for c in report['cases'])
            assert all('raw_response' in c for c in report['cases'])
        else:
            assert all('error_class' in c for c in report['cases'])
        args.output=root/'different-output'
        try:
            with redirect_stdout(io.StringIO()):
                asyncio.run(probe.exercise(args))
        except ValueError:
            pass
        else:
            raise AssertionError('learning probe repeated inference against a spent journal')
        assert len(calls)==before+3
print('HERMES_ALIVE_KERNEL_LIVE_LEARNING_CONTRACT_OK')
