"""Real Core/provider semantic read with synthetic signed read grants.

No model, live private memory, message, or Gateway-admission proof. This
qualifies the read capability; it does not qualify Native automatic selection.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch

OPTIONS={'model_calls':True,'delivery':True,'outbound_retention_days':30,
         'outbound_retention_confirmed':True,'model':None,'public_queries':[],'cited_reads':False}
SCOPE={'contract':'hermes-core-conversation-v1','runtime_profile':'default','transport_profile':'default',
    'platform':'telegram','chat_id':'public-synthetic-peer','chat_type':'dm','thread_id':'',
    'user_id':'public-synthetic-owner','scope_id':'','guild_id':'','parent_chat_id':'',
    'session_key':'public-synthetic-session-key','session_id':'public-synthetic-session'}


def exercise(args):
    sys.path[:0]=[str(args.core.resolve()),str(Path(__file__).resolve().parents[1]/'hooks')]
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override,get_hermes_home
    from hermes_state_registry import close_all_under
    from alive_kernel.kernel_setup import KernelSetupStore,KernelSetupError
    from alive_kernel.core_memory_context import (CoreMemoryRecall,core_memory_context,
        core_memory_cycle,publish_core_memory_context)
    from agent.memory_manager import MemoryManager
    from plugins import memory as memory_loader
    mode=os.environ['ALIVE_MEMORY_CONTEXT_CASE'];home=Path(os.environ['HERMES_HOME']);home.mkdir(exist_ok=True)
    token=set_hermes_home_override(home)
    try:
        shutil.copytree(args.provider_source,home/'plugins/holographic',
            ignore=shutil.ignore_patterns('.git','__pycache__'))
        cfg={'memory':{'provider':'builtin' if mode=='builtin' else 'holographic'},
            'plugins':{'enabled':['holographic'],'hermes-memory-store':{
                'db_path':'$HERMES_HOME/memory_store.db','scope':'profile','auto_extract':False,
                'mirror_memory_writes':False,'cron_writes':False,'embeddings':'off','rerank':'off'}}}
        (home/'config.yaml').write_text(json.dumps(cfg),encoding='utf-8')
        package=types.ModuleType('alive_synthetic_legacy_memory_context')
        package.__path__=[str(args.legacy_source.resolve())];sys.modules[package.__name__]=package
        legacy=importlib.import_module(package.__name__+'.store').MemoryStore(home/'memory_store.db')
        try:legacy.add_fact('Sable uses amber counters for classroom arithmetic.','preference','public synthetic')
        finally:legacy.close()
        store=KernelSetupStore(home/'plugin-data/hermes-alive/runtime/kernel',initialize=True)
        opts={**OPTIONS,**({'use_hermes_user_profile':True} if mode=='old-grant' else
                          {'use_hermes_external_memory':True})}
        if mode=='context':opts['communication_preference']='Prefer brief grounded explanations.'
        intent,code=store.stage(opts)
        if mode=='group':
            try:store.confirm(intent.event.event_id,code,scope={**SCOPE,'chat_type':'group'})
            except KernelSetupError:pass
            else:raise AssertionError('personal memory grant accepted in group')
            assert store.configuration() is None
            print('CORE_SEMANTIC_MEMORY_CASE_OK '+mode,flush=True)
            return
        configured=store.confirm(intent.event.event_id,code,scope=SCOPE)
        initial_memory_proposals=len(store.journal.read(event_type='memory.proposed'))
        authority={'valid':True}
        def validate():
            if not authority['valid']:raise ValueError('synthetic Native read scope retired')
        capability=CoreMemoryRecall(store,configured,validate=validate)
        if mode in ('old-grant','foreign'):
            foreign=(home.parent/'unrelated-foreign-profile').resolve()
            assert foreign!=home.resolve()
            other=set_hermes_home_override(foreign) if mode=='foreign' else None
            try:
                if mode=='foreign':assert get_hermes_home().resolve()==foreign
                with patch.object(memory_loader,'load_memory_provider',side_effect=AssertionError('ungranted provider load')):
                    try:capability.read('Sable classroom arithmetic')
                    except ValueError:pass
                    else:raise AssertionError('unauthorized read accepted')
            finally:
                if other is not None:reset_hermes_home_override(other)
            assert not store.journal.read(event_type='memory.core_recall_observed')
            assert not foreign.exists()
        else:
            original=MemoryManager.prefetch_all
            returned=[]
            def observed(instance,query,**kwargs):
                answer=original(instance,query,**kwargs);returned.append(answer)
                if mode=='revoke-during':
                    pending,newcode=store.stage(OPTIONS,replace=True)
                    store.confirm(pending.event.event_id,newcode,scope=SCOPE)
                elif mode=='config-during':
                    cfg['memory']['provider']='builtin'
                    (home/'config.yaml').write_text(json.dumps(cfg),encoding='utf-8')
                elif mode=='authority-during':authority['valid']=False
                return answer
            with patch.object(MemoryManager,'prefetch_all',observed):
                try:
                    result=capability.read('quartz submarine navigation' if mode=='empty' else 'Sable classroom arithmetic')
                except ValueError:
                    assert mode in ('revoke-during','config-during','authority-during')
                    assert returned and 'amber counters' in returned[0]
                    assert not store.journal.read(event_type='memory.core_recall_observed')
                else:
                    assert mode not in ('revoke-during','config-during','authority-during'),result
                    if mode=='builtin':assert result=={'status':'no_external_provider','evidence':None}
                    elif mode=='empty':assert result=={'status':'no_usable_context_returned','evidence':None}
                    else:
                        assert result['status']=='recalled' and 'amber counters' in result['evidence']['value'],result
                        assert result['evidence']['kind']=='core_recalled_advisory'
                        records=store.journal.read(event_type='memory.core_recall_observed');assert len(records)==1
                        assert records[0].event.payload['user_explicit_statement'] is False
                        assert records[0].event.payload['raw_content_stored'] is False
                        if mode=='context':
                            from contextvars import copy_context
                            from alive_kernel.cognition_context import CognitionContextReader
                            from alive_kernel.discovery_opportunities import DiscoveryOpportunityIngestor
                            from alive_kernel.discovery_inquiry import DiscoveryInquiryContext
                            from alive_kernel.events import Sensitivity
                            from agent.memory_provider import spawn_context_thread
                            reader=CognitionContextReader(store.journal)
                            discovery=DiscoveryInquiryContext(DiscoveryOpportunityIngestor(
                                store.journal,content_vault=store.vault))
                            def recalled(values):return [v for v in values if v.kind=='core_recalled_advisory']
                            baseline=reader.read(subject=configured.subject,clearance=Sensitivity.PRIVATE)
                            assert len(baseline)==1 and baseline[0].predicate=='profile.communication'
                            with core_memory_context(capability,result):
                                private=reader.read(subject=configured.subject,clearance=Sensitivity.PRIVATE)
                                assert len(private)==2 and len(recalled(private))==1
                                assert 'amber counters' in recalled(private)[0].value
                                assert not reader.read(subject=configured.subject,clearance=Sensitivity.PUBLIC)
                                assert not reader.read(subject='user:other',clearance=Sensitivity.PRIVATE)
                                public_input=discovery.owner_context.read(subject=configured.subject,clearance=Sensitivity.PRIVATE)
                                assert not recalled(public_input) and public_input==baseline
                                copied=copy_context();thread_result=[]
                                thread=spawn_context_thread(lambda:thread_result.extend(reader.read(
                                    subject=configured.subject,clearance=Sensitivity.PRIVATE)),name='public-memory-context-proof')
                                thread.start();thread.join(10);assert not thread.is_alive()
                                assert len(thread_result)==2 and recalled(thread_result)[0].value==recalled(private)[0].value
                            assert reader.read(subject=configured.subject,clearance=Sensitivity.PRIVATE)==baseline
                            assert copied.run(reader.read,subject=configured.subject,clearance=Sensitivity.PRIVATE)==baseline
                            import asyncio
                            with core_memory_cycle():
                                assert reader.read(subject=configured.subject,clearance=Sensitivity.PRIVATE)==baseline
                                async def child():publish_core_memory_context(capability,result)
                                asyncio.run(child())
                                # A child publishes to the cycle's shared slot;
                                # merely setting its own ContextVar would vanish.
                                assert recalled(reader.read(subject=configured.subject,clearance=Sensitivity.PRIVATE))[0].value==recalled(private)[0].value
                                try:publish_core_memory_context(capability,result)
                                except ValueError:pass
                                else:raise AssertionError('cycle recall was silently replaced')
                            changed={**result,'evidence':{**result['evidence'],'value':'forged recalled instructions'}}
                            try:
                                with core_memory_context(capability,changed):raise AssertionError('tampered evidence entered context')
                            except ValueError:pass
        serialized='\n'.join(record.event.canonical_json() for record in store.journal.read())
        assert 'amber counters' not in serialized and 'Sable classroom arithmetic' not in serialized
        assert len(store.journal.read(event_type='memory.proposed'))==initial_memory_proposals
        assert not store.journal.read(event_type='work.requested')
        print('CORE_SEMANTIC_MEMORY_CASE_OK '+mode,flush=True)
    finally:
        close_all_under(home)
        reset_hermes_home_override(token)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',type=Path,required=True)
    parser.add_argument('--provider-source',type=Path,required=True)
    parser.add_argument('--legacy-source',type=Path,required=True)
    args=parser.parse_args()
    if os.environ.get('ALIVE_MEMORY_CONTEXT_CASE'):
        exercise(args)
    else:
        with tempfile.TemporaryDirectory(prefix='alive-core-memory-context-') as directory:
            for mode in ('recalled','context','old-grant','foreign','group','revoke-during','config-during','authority-during','empty','builtin'):
                env={**os.environ,'HOME':directory,'HERMES_HOME':str(Path(directory)/mode),
                    'ALIVE_MEMORY_CONTEXT_CASE':mode,'PYTHONDONTWRITEBYTECODE':'1'}
                result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env=env,
                    capture_output=True,text=True,timeout=120)
                assert result.returncode==0,mode+'\n'+result.stdout+'\n'+result.stderr
                assert 'CORE_SEMANTIC_MEMORY_CASE_OK '+mode in result.stdout
                print(result.stdout,flush=True)
        print('HERMES_ALIVE_CORE_SEMANTIC_MEMORY_CAPABILITY_OK')
