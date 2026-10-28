"""Installed Native -> semantic query -> real Core memory -> cognition.

Synthetic paired peer, controlled model/public-search replies, actual provider,
Core command dispatch and Native lifetime. No real model, message or account.
"""
import asyncio
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
from types import SimpleNamespace
from unittest.mock import patch

if __name__=='__main__' and not os.environ.get('ALIVE_NATIVE_MEMORY_CASE'):
    with tempfile.TemporaryDirectory(prefix='alive-native-memory-') as directory:
        for mode in ('granted','old-grant','declined','invalid-query'):
            env={**os.environ,'HOME':directory,'HERMES_HOME':str(Path(directory)/mode),
                'ALIVE_NATIVE_MEMORY_CASE':mode,'PYTHONDONTWRITEBYTECODE':'1'}
            result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env=env,
                capture_output=True,text=True,timeout=300)
            assert result.returncode==0,mode+'\n'+result.stdout+'\n'+result.stderr
            assert 'CORE_NATIVE_MEMORY_PROOF ' in result.stdout,result.stdout
            print(result.stdout,flush=True)
    print('HERMES_ALIVE_CORE_NATIVE_MEMORY_OK')
    raise SystemExit(0)

import run_core_session_routing as core
from run_core_guided_setup import cli


async def exercise(home):
    mode=os.environ['ALIVE_NATIVE_MEMORY_CASE'];granted=mode!='old-grant';has_context=mode=='granted';home.mkdir(exist_ok=True)
    shutil.copytree(core.repo,home/'plugins/hermes-alive')
    shutil.copytree('/holo-catalog',home/'plugins/holographic',ignore=shutil.ignore_patterns('.git','__pycache__'))
    cfg={'model':{'provider':'auto','default':'synthetic-owner-model'},'memory':{'provider':'holographic'},
        'plugins':{'enabled':['hermes-alive','holographic'],'hermes-memory-store':{
            'db_path':'$HERMES_HOME/memory_store.db','scope':'profile','auto_extract':False,
            'mirror_memory_writes':False,'cron_writes':False,'embeddings':'off','rerank':'off'}}}
    (home/'config.yaml').write_text(json.dumps(cfg),encoding='utf-8')
    package=types.ModuleType('alive_native_memory_legacy');package.__path__=['/legacy'];sys.modules[package.__name__]=package
    legacy=importlib.import_module(package.__name__+'.store').MemoryStore(home/'memory_store.db')
    try:legacy.add_fact('Sable uses amber counters for classroom arithmetic.','preference','public synthetic')
    finally:legacy.close()
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
        '--interests','Sable classroom arithmetic','--communication-preference','Prefer brief grounded explanations.',
        '--public-query','public synthetic science','--confirm-public-reads',
        '--confirm-hermes-external-memory' if granted else '--confirm-hermes-profile-memory')
    assert rc==0 and staged['confirmation_summary']['external_memory_provider_recall_enabled'] is granted
    assert cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None
    calls=[];cognition=[];searches=[]
    try:
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];assert loaded.enabled and not loaded.error
        binding=loaded.module._gateway_host_binding
        class Adapter(core.Adapter):
            async def send(self,*args,**kwargs):raise AssertionError('memory qualification cannot send')
        adapter=Adapter(core.Platform.TELEGRAM);runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter})
        adapter.gateway_runner=runner;await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='public-native-memory-peer',
            user_id='public-native-memory-owner',message_id='public-native-memory-confirm')
        entry=runner.session_store.get_or_create_session(source)
        from hermes_cli.plugins import get_plugin_command_handler
        handler=get_plugin_command_handler('alive')
        async def command(text):
            return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=text)
        assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
        assert '已启用' in await command('enable')
        native=binding.native
        assert native._caller is None,'background model started before controlled caller admission'
        binding.arguments['stop'].set();await binding.task
        assert native.private_context is not None if granted else native.private_context is None
        from tools.registry import registry
        def public_search(arguments,**kwargs):
            searches.append(arguments)
            assert 'amber counters' not in json.dumps(arguments) and 'Sable' not in json.dumps(arguments)
            return json.dumps({'success':True,'data':{'web':[{'url':'https://example.invalid/memory-context',
                'title':'Synthetic classroom resource','description':'Public synthetic listing; no verified new finding.'}]}})
        registry.register(name='web_search',toolset='web',schema={'name':'web_search',
            'description':'Public synthetic no-network search','parameters':{'type':'object'}},
            handler=public_search,override=True,scope=str(home))
        class Caller:
            def __init__(self,**kwargs):self.calls=0;self.pending=()
            async def reap_pending(self,**kwargs):return {'closed':0,'remaining':0}
            async def __call__(self,**kwargs):
                self.calls+=1;calls.append(kwargs['task'])
                text=json.dumps(kwargs['messages'],ensure_ascii=False)
                if kwargs['task']=='alive_private_memory_query':
                    assert granted and 'Sable' in text
                    assert 'amber counters' not in text,'query planner received the answer before retrieval'
                    document=({'query':None} if mode=='declined' else {'unexpected':'not an admitted question'}
                              if mode=='invalid-query' else {'query':'Sable classroom arithmetic'})
                elif kwargs['task']=='alive_discovery_reading':
                    assert 'amber counters' not in text,'private recall entered public reading planner'
                    document={'source_refs':[],'question':None,'value_hypothesis':'No new material in this public synthetic search.'}
                elif kwargs['task']=='alive_opportunity_candidates':
                    cognition.append({'has_fact':'amber counters' in text,'has_advisory_kind':'core_recalled_advisory' in text})
                    assert cognition[-1]['has_fact'] is has_context,cognition[-1]
                    if has_context:assert cognition[-1]['has_advisory_kind']
                    assert 'Prefer brief grounded explanations.' in text
                    document={'candidates':[]}
                else:raise AssertionError('unexpected Native model task '+kwargs['task'])
                return SimpleNamespace(model='synthetic-owner-model',choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(document)))])
        native.caller_factory=lambda **kwargs:Caller(**kwargs)
        execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
        async def allow(self,url):return url=='https://example.invalid/memory-context'
        with patch.object(execution.kernel('core_discovery_tools').CoreDiscoveryTools,'allow_url',allow):
            first=await native.step(binding.arguments['build_parameters']())
            second=await native.step(binding.arguments['build_parameters']())
            before_third=calls.count('alive_private_memory_query')
            third=await native.step(binding.arguments['build_parameters']())
            assert calls.count('alive_private_memory_query')==before_third,'unchanged semantic inputs repeated query planning'
        assert first.disposition in ('silence','waiting_for_change'),first.disposition
        assert second.disposition in ('silence','waiting_for_change'),second.disposition
        assert cognition and searches,{'calls':calls,'first':first.disposition,'second':second.disposition,'third':third.disposition,
            'memory':native.private_context.last_status if granted else None,'searches':len(searches)}
        assert 1<=calls.count('alive_private_memory_query')<=2 if granted else calls.count('alive_private_memory_query')==0,calls
        store=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge').setup_store(binding)
        records=store.journal.read(event_type='memory.core_recall_observed')
        assert len(records)==(1 if has_context else 0)
        if mode in ('declined','invalid-query'):
            assert native.private_context.last_status==('no_question_selected' if mode=='declined' else 'query_not_admitted')
        from cron.jobs import list_jobs
        assert not list_jobs(include_disabled=True)
        serialized='\n'.join(row.event.canonical_json() for row in store.journal.read())
        assert 'amber counters' not in serialized
        from_module=importlib.import_module(store.__class__.__module__.rsplit('.',1)[0]+'.cognition_context')
        current=from_module.CognitionContextReader(store.journal).read(subject=store.configuration().subject,clearance='private')
        assert not any(value.kind=='core_recalled_advisory' for value in current),'recall escaped the completed Native cycle'
        print('CORE_NATIVE_MEMORY_PROOF '+json.dumps({'mode':mode,'query_model_calls':calls.count('alive_private_memory_query'),
            'cognition':cognition,'public_search_calls':len(searches),'memory_events':len(records),
            'jobs':0,'external_deliveries':0,'real_model_calls':0,'cycle_context_closed':True}),flush=True)
    finally:
        if manager is not None:manager.unload()
        from hermes_state_registry import close_all_under
        close_all_under(home)
        core.reset_hermes_home_override(token)


if __name__=='__main__':asyncio.run(exercise(Path(os.environ['HERMES_HOME'])))
