"""Reproduce the external-memory/cron input boundary with public synthetic data.

Requires an admitted Core environment and an unmodified Holographic checkout.
No model, live profile, private memory or channel is used. A failing recall exits
nonzero: initialization or a successful short control cannot qualify the gate.
This is a provider-library regression probe, not a full Native/worker test.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',type=Path,required=True)
    parser.add_argument('--provider-source',type=Path,required=True)
    parser.add_argument('--legacy-source',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():raise ValueError('a prior report must not be overwritten')
    sys.path.insert(0,str(args.core.resolve()))
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override
    from hermes_state_registry import close_all_under
    from agent.memory_manager import MemoryManager
    from plugins.memory import load_memory_provider
    from cron.scheduler_prompt import _build_job_prompt
    original_env={key:os.environ.get(key) for key in ('HOME','HERMES_HOME')}
    with tempfile.TemporaryDirectory(prefix='alive-memory-framing-') as directory:
        home=Path(directory)/'profile';home.mkdir()
        os.environ['HOME']=directory;os.environ['HERMES_HOME']=str(home)
        token=set_hermes_home_override(home);manager=None
        try:
            shutil.copytree(args.provider_source,home/'plugins/holographic',
                ignore=shutil.ignore_patterns('.git','__pycache__'))
            config={'memory':{'provider':'holographic'},'plugins':{'enabled':['holographic'],
                'hermes-memory-store':{'db_path':'$HERMES_HOME/memory_store.db','scope':'profile',
                    'auto_extract':False,'mirror_memory_writes':False,'cron_writes':False,
                    'embeddings':'off','rerank':'off'}}}
            (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
            package=types.ModuleType('alive_public_legacy_framing_fixture')
            package.__path__=[str(args.legacy_source.resolve())];sys.modules[package.__name__]=package
            legacy=importlib.import_module(package.__name__+'.store').MemoryStore(home/'memory_store.db')
            try:
                legacy.add_fact('Sable uses amber counters for classroom arithmetic.','preference','public synthetic')
                legacy.add_fact('Lyra studies lunar mapping.','fact','public synthetic')
                legacy.add_fact('Orion has a classroom appointment.','fact','public synthetic')
            finally:legacy.close()
            provider=load_memory_provider('holographic',register_skills=False)
            assert provider is not None and provider.is_available()
            manager=MemoryManager(external_prefetch_timeout=20);manager.add_provider(provider)
            assert manager.initialize_for_agent(session_id='public-framing-probe',hermes_home=str(home),
                platform='cron',agent_context='cron',user_id='public-synthetic-owner')
            questions={'semantic':'Sable classroom arithmetic',
                       'natural':'What does Sable prefer for classroom arithmetic?'}
            observations=[]
            for label,question in questions.items():
                for framed in (False,True):
                    prompt=(_build_job_prompt({'id':'public-framing-probe','name':'public-framing-probe',
                        'prompt':question}) if framed else question)
                    answer=manager.prefetch_all(prompt,session_id=f'public-{label}-{framed}')
                    observations.append({'question':label,'core_cron_framed':framed,
                        'query_characters':len(prompt),'target_fact_recalled':'amber counters' in answer})
            passed=all(item['target_fact_recalled'] for item in observations)
            args.report.write_text(json.dumps({'gate_passed':passed,'observations':observations,
                'scope':'synthetic Core/provider library regression, not actual Native or worker acceptance',
                'private_memory_read':False,'actual_model_calls':0,'external_deliveries':0},indent=2),encoding='utf-8')
            print('CORE_MEMORY_FRAMING_GATE='+('PASS' if passed else 'FAIL'))
            return 0 if passed else 1
        finally:
            if manager is not None:manager.shutdown_all()
            close_all_under(directory)
            reset_hermes_home_override(token)
            for key,value in original_env.items():
                if value is None:os.environ.pop(key,None)
                else:os.environ[key]=value


if __name__=='__main__':raise SystemExit(main())
