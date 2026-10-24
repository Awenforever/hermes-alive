"""Opt-in activated native chain with real Core models and an isolated adapter.

Public bounded snapshots are replayed THROUGH Core's tool registry, not represented
as fresh live search/full-page reads. No real channel connects or sends. Complete
original share/main replies stay in operator-supplied PRIVATE evidence, never Git.
This is a diagnostic, not an automatic quality verdict or production acceptance.
"""
import asyncio
import copy
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time

if os.environ.get('ALIVE_ACTIVATED_CHAIN_AUTHORIZATION')!='public_snapshots_real_models_no_delivery':
    raise SystemExit('explicit isolated real-model authorization required')
projection=Path(os.environ['ALIVE_ACTIVATED_CHAIN_MODEL_PROJECTION']).resolve(strict=True)
evidence=Path(os.environ['ALIVE_ACTIVATED_CHAIN_EVIDENCE']).resolve(strict=True)
corpus_file=Path(os.environ['ALIVE_ACTIVATED_CHAIN_CORPUS']).resolve(strict=True)
if not projection.is_file() or not evidence.is_dir():raise SystemExit('private projection/evidence required')
if os.name=='posix' and (stat.S_IMODE(projection.stat().st_mode)&0o077 or stat.S_IMODE(evidence.stat().st_mode)&0o077):
    raise SystemExit('private projection/evidence permissions required')

import run_core_session_routing as core
from run_core_guided_setup import cli

projected=json.loads(projection.read_text(encoding='utf-8'))
corpus=json.loads(corpus_file.read_text(encoding='utf-8'))
if (not isinstance(corpus,dict) or set(corpus)!={'query','sources'}
        or not isinstance(corpus['query'],str) or not 1<=len(corpus['query'])<=128
        or not isinstance(corpus['sources'],list) or not 1<=len(corpus['sources'])<=3):
    raise SystemExit('bounded public snapshot corpus required')
sources={}
for item in corpus['sources']:
    if (not isinstance(item,dict) or set(item)!={'url','title','content'}
            or not all(isinstance(value,str) and value for value in item.values())
            or not item['url'].startswith('https://') or len(item['content'])>6000):
        raise SystemExit('bounded HTTPS public source required')
    sources[item['url']]=item
values=list(projected['environment'].values())
for entry in (projected['config']['model'],*projected['config'].get('custom_providers',[]),
              *projected['config'].get('fallback_providers',[])):
    values.extend(entry.get(key) for key in ('api_key','access_token','token'))
secrets=tuple(value for value in values if isinstance(value,str) and len(value)>8)
report={'contract':'alive-activated-chain-probe-v1','actual_model_inference_requested':True,
    'actual_model_response_observed':False,
    'source_mode':'bounded_operator_prepared_public_digest_replayed_through_Core_registry',
    'live_search_proven':False,'physical_delivery_proven':False,'quality_round_credited':False,
    'semantic_verdict':'pending_original_response_review','source_calls':[],'auxiliary_events':[],
    'submissions':[],'main_turns':[],'structural_result':'in_progress'}


def save():
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if any(value in text for value in secrets):raise RuntimeError('credential disclosure refused')
    (evidence/'report.json').write_text(text,encoding='utf-8')


def contains_share(value,exact):
    if isinstance(value,dict):return any(contains_share(item,exact) for item in value.values())
    if isinstance(value,list):return any(contains_share(item,exact) for item in value)
    if not isinstance(value,str):return False
    if value==exact:return True
    offset=value.find('{"alive_shares":')
    if offset<0:return False
    try:document,_=json.JSONDecoder().raw_decode(value[offset:])
    except ValueError:return False
    return any(item.get('text')==exact for item in document.get('alive_shares',[]))


async def exercise(home):
    home.mkdir(mode=0o700)
    config=copy.deepcopy(projected['config'])
    config['plugins']={'enabled':['hermes-alive']}
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    (home/'config.yaml').chmod(0o600)
    # A routed Core profile intentionally cannot borrow process-only credentials
    # from its launch profile. Place ONLY the authorized model credential
    # projection in this synthetic private profile, using Core's own dotenv
    # loader. This file is never copied into retained kernel evidence.
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',key)
            or not isinstance(value,str) for key,value in projected['environment'].items()):
        raise RuntimeError('invalid model credential projection')
    (home/'.env').write_text(''.join(key+'='+json.dumps(value,ensure_ascii=False)+'\n'
        for key,value in projected['environment'].items()),encoding='utf-8')
    (home/'.env').chmod(0o600)
    # Keep authentication in the isolated environment only. No production route,
    # session, memory, mailbox or gateway configuration is projected.
    previous={key:os.environ.get(key) for key in projected['environment']}
    os.environ.update(projected['environment'])
    shutil.copytree(core.repo,home/'plugins/hermes-alive')
    manager=None;binding=None;store=None
    token=core.set_hermes_home_override(home)
    try:
        rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery',
            '--confirm-outbound-retention','--public-query',corpus['query'],'--confirm-public-reads')
        if rc!=0:raise RuntimeError('actual Core setup failed')
        rc,installed=cli(home,'install-runtime','--engine','kernel')
        if rc!=0 or installed['engine']!='kernel':raise RuntimeError('native runtime installation failed')
        from tools.registry import registry
        from hermes_constants import get_hermes_home
        def source_handler(name):
            def handle(arguments,**_):
                if Path(get_hermes_home()).resolve()!=home.resolve():raise RuntimeError('foreign public-read scope')
                report['source_calls'].append({'name':name,'arguments':arguments});save()
                if name=='web_search':
                    if arguments!=dict(query=corpus['query'],limit=3):raise RuntimeError('unapproved search')
                    return json.dumps({'success':True,'data':{'web':[dict(url=s['url'],title=s['title'],
                        description=s['content'][:180]) for s in sources.values()]}})
                urls=arguments.get('urls')
                if not isinstance(urls,list) or len(urls)!=1 or urls[0] not in sources:
                    raise RuntimeError('snapshot read outside approved source corpus')
                item=sources[urls[0]]
                return json.dumps({'results':[{'url':item['url'],'title':item['title'],
                    'content':item['content'],'snapshot_scope':'bounded_public_excerpt','full_page_read':False}]})
            return handle
        for name in ('web_search','web_extract'):
            registry.register(name=name,toolset='web',schema=dict(name=name,
                description='Isolated public snapshot replay',parameters={'type':'object'}),
                handler=source_handler(name),override=True,scope=str(home))
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];binding=loaded.module._gateway_host_binding
        if not loaded.enabled or loaded.error:raise RuntimeError('actual Core plugin admission failed')
        context=binding.context
        context.register_hook('pre_auxiliary_call',lambda **v:report['auxiliary_events'].append(
            {'phase':'pre',**{key:v.get(key) for key in ('aux_task','model','provider')}}))
        def observe_auxiliary(**values):
            report['auxiliary_events'].append({'phase':'post',**{key:values.get(key) for key in
                ('aux_task','model','provider','response_model','finish_reason','error_type','assistant_content_chars')}})
            if values.get('response_model') and values.get('error') is None:
                report['actual_model_response_observed']=True
            save()
        context.register_hook('post_auxiliary_call',observe_auxiliary)
        from hermes_cli.version_info import get_version_info
        version=get_version_info()
        if version.dirty:raise RuntimeError('Core supply dirty')
        report['core']={'version':version.display_version,'commit':version.commit,'identity_source':version.source}
        class Adapter(core.Adapter):
            async def send(self,chat_id,content,**kwargs):
                if chat_id!='-10098765':raise RuntimeError('foreign channel submission')
                metadata=kwargs.get('metadata') or {}
                if not metadata.get('model_name') or metadata['model_name']=='hermes':
                    raise RuntimeError('actual renderer provenance missing')
                report['submissions'].append({'exact_text':content,'metadata':metadata,
                    'adapter_kind':'isolated in-memory Core adapter, not external delivery'})
                save()
                return core.SimpleNamespace(success=True,message_id='synthetic-local-submission')
        adapter=Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-10098765',
            user_id='synthetic-chain-owner',thread_id='7',message_id='synthetic-chain-command')
        entry=runner.session_store.get_or_create_session(source)
        from hermes_cli.plugins import get_plugin_command_handler
        handler=get_plugin_command_handler('alive')
        async def command(arguments):
            return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=arguments)
        confirmed=await command(staged['confirmation_command'].removeprefix('/alive '))
        if '已确认' not in confirmed:raise RuntimeError('actual Core conversation confirmation failed')
        setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge');store=setup.setup_store(binding)
        enabled=await command('enable')
        if '已启用' not in enabled:raise RuntimeError('actual Core native enable failed')
        before=0;deadline=time.monotonic()+1800
        while time.monotonic()<deadline:
            closed=next(store.journal.iter_reverse(event_types=('autonomous.host.closed',),
                subject=store.configuration().subject,max_records=1),None)
            if closed is not None and closed.sequence>before:
                report['cycle_disposition']=closed.event.payload['disposition'];break
            if binding.task.done():
                report['task_result']=binding.task.result();break
            await asyncio.sleep(.2)
        else:raise TimeoutError('first native cycle did not settle within diagnostic budget')
        await command('pause')
        await asyncio.wait_for(asyncio.shield(binding.task),15)
        report['pending_owned_work']=len(binding.native.pending)
        report['native_model_calls_last_cycle']=binding.native.last_call_count
        if report['pending_owned_work']:raise RuntimeError('native work still physically pending')
        if len(report['submissions'])!=1:
            report['structural_result']='no_single_submission';save();return
        await main_followup(home,context,entry,source,report['submissions'][0]['exact_text'])
        report['structural_result']='completed_pending_semantic_review';save()
    finally:
        if binding is not None and binding.arguments is not None:binding.arguments['stop'].set()
        if manager is not None:manager.unload()
        if (store is not None and (binding.task is None or binding.task.done())
                and (binding.native is None or not binding.native.pending)):
            from hermes_state_registry import close_all_under
            close_all_under(home)
            # Copy only the now-offline synthetic/public kernel, not model config,
            # .env, real routes or any production memory. Retain original evidence
            # even when the model abstains or a stage fails.
            shutil.copytree(store.root,evidence/'kernel-state')
            report['kernel_snapshot_status']='offline_copy_after_owned_work_settled'
            save()
        else:
            report['kernel_snapshot_status']='not_copied_without_settlement'
            save()
        core.reset_hermes_home_override(token)
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value


async def main_followup(home,context,entry,source,exact_share):
    from run_agent import AIAgent
    from hermes_cli.config import load_config_readonly
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_cli.fallback_config import get_fallback_chain
    observations=[]
    context.register_hook('pre_api_request',lambda **v:observations.append(
        {key:copy.deepcopy(v.get(key)) for key in ('model','provider','request_messages','session_id')}))
    def turn(question):
        variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
            session_key=entry.session_key,session_id=entry.session_id)
        agent=None;before=len(observations)
        try:
            config=load_config_readonly();model=config['model']
            runtime=resolve_runtime_provider(requested=model.get('provider'),target_model=model['default'])
            agent=AIAgent(model=runtime.get('model') or model['default'],provider=runtime['provider'],
                requested_provider=model.get('provider'),base_url=runtime.get('base_url'),api_key=runtime.get('api_key'),
                api_mode=runtime.get('api_mode'),fallback_model=get_fallback_chain(config),enabled_toolsets=[],
                max_iterations=2,max_tokens=2048,run_budget_seconds=480,quiet_mode=True,save_trajectories=False,
                skip_context_files=True,load_soul_identity=False,skip_memory=True,skip_background_review=True,
                session_id=entry.session_id,gateway_session_key=entry.session_key,platform='telegram',
                user_id=source.user_id,chat_id=source.chat_id,chat_type='dm',thread_id=source.thread_id,cwd=str(home))
            if agent.tools:raise RuntimeError('main diagnostic unexpectedly has tools')
            result=agent.run_conversation(question,conversation_history=[],task_id='public-activated-followup')
            requests=observations[before:]
            report['main_turns'].append({'question':question,'original_final_response':result.get('final_response'),
                'error_present':bool(result.get('error')),'final_model':agent.model,'final_provider':agent.provider,
                'fallback_activated':bool(agent._fallback_activated),'observed_requests':requests})
            save()
            if not requests:raise RuntimeError('actual main request not observed')
            # Context must come from the actual plugin hook, not supplied history.
            if not any(contains_share(r['request_messages'],exact_share) for r in requests):
                raise RuntimeError('native main turn lacks the exact submitted share')
        finally:
            if agent is not None:
                agent.close()
            core.clear_session_vars(variables)
    await asyncio.to_thread(turn,'你刚才分享的这件事，具体做到哪一步了？')
    await asyncio.to_thread(turn,'你读过完整原文吗？哪些内容是原文说的，哪些是你的判断？')


try:
    with tempfile.TemporaryDirectory(prefix='alive-activated-public-') as directory:
        try:asyncio.run(exercise(Path(directory)/'profile'))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
except BaseException as error:
    report['structural_result']='failed';report['exception_type']=type(error).__name__;save()
    raise
print('HERMES_ALIVE_ACTIVATED_CHAIN_PROBE_FINISHED')
