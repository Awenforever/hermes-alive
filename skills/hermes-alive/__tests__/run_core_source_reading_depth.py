"""Current Core guided setup -> authorized native cycle -> deeper source -> share.

Core SDK/registry/session/adapter paths are real; HTTP, pages, model decisions and
URL safety are controlled. No actual provider call, physical message or quality
round. In particular this does not use the old kernel-shadow setup surface.
"""
import asyncio,importlib,json,shutil,tempfile
from pathlib import Path
from unittest.mock import patch
import run_core_session_routing as core
from run_core_guided_setup import cli


async def test(home):
    import httpx
    home.mkdir();shutil.copytree(core.repo,home/'plugins/hermes-alive')
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'custom:owner','default':'configured-primary'},
        'custom_providers':[{'name':'owner','model':'configured-primary','base_url':'https://provider.invalid/v1',
            'key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}],'agent':{'reasoning_effort':False}}))
    (home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n')
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
        '--public-query','synthetic public observation','--confirm-public-reads','--confirm-cited-reads',
        '--confirm-public-refinement')
    assert rc==0 and cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None
    url='https://example.invalid/observation';reads=[];stages=[];sent=[]
    qualifier='The trial used an existing instrument, not a newly constructed one.'
    try:
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];binding=loaded.module._gateway_host_binding
        from hermes_cli.plugins import get_plugin_command_handler
        from tools.registry import registry
        handler=get_plugin_command_handler('alive')
        class Adapter(core.Adapter):
            async def send(self,chat_id,content,**kwargs):
                sent.append((chat_id,content))
                return core.SimpleNamespace(success=True,message_id='synthetic-local-submission')
        adapter=Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='7654321',
            user_id='synthetic-depth-owner',message_id='synthetic-depth-confirm')
        entry=runner.session_store.get_or_create_session(source)
        async def command(args):
            return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=args)
        assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
        def dispatch(name):
            def operation(args,**kwargs):
                reads.append((name,args))
                if name=='web_search':
                    assert args==dict(query='synthetic public observation',limit=3)
                    return json.dumps({'success':True,'data':{'web':[dict(url=url,title='Public trial',
                        description='A public observation with a qualification worth understanding.')]}})
                assert args['urls']==[url] and args['char_limit'] in (6000,15000)
                text=('An introduction describes observing before intervention.' if args['char_limit']==6000
                    else 'Public background. '*510+qualifier)
                return json.dumps({'results':[dict(url=url,title='Public trial',content=text)]})
            return operation
        for name in ('web_search','web_extract'):
            registry.register(name=name,toolset='web',schema=dict(name=name,description='Synthetic public source',
                parameters={'type':'object'}),handler=dispatch(name),override=True,scope=str(home))
        def excerpt(row):
            return row.get('summary_excerpt') or ''.join(p['text'] for p in row.get('summary_passages',[]))
        def respond(request):
            if not request.url.path.endswith('/chat/completions'):
                return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
            assert request.url.host=='provider.invalid'
            body=json.loads(request.content)
            raw=next(m['content'] for m in body['messages'] if m['role']=='user')
            try:data=json.loads(raw)
            except ValueError:data=json.loads(raw.split('\n',1)[1])
            if isinstance(data,list):
                stage='select';value={'candidate_id':next(c['candidate_id'] for c in data
                    if c['candidate_id'].startswith('opportunity-candidate:')),'rationale':'Synthetic selection'}
            elif data.get('method')=='public-source-depth-v2':
                stage='deepen';assert 'user_context' not in data
                value=dict(search_query=None,read_targets=[],deepen_source_ref=data['deeper_read_sources'][0]['source_ref'],
                    reason='Read the scope qualification of the current trial.')
            elif 'sources' in data:
                stage='reading';value=dict(source_refs=[data['sources'][0]['source_ref']],question='What was actually tried?',
                    value_hypothesis='A bounded understandable result.')
            elif 'opportunities' in data:
                stage='interpret';assert any(qualifier in excerpt(e) for e in data['opportunities'])
                item=next(e for e in data['opportunities'] if qualifier in excerpt(e))
                value={'candidates':[dict(agenda_item_id=item['agenda_item_id'],kind='share',topic='public trial',
                    communication_plan=dict(version=3,recipient_goal='Synthetic contribution',speech_act='share',contents=[],behavior_constraints=[]),
                    dimensions={n:dict(value=.05 if n in ('risk','urgency','interruption_cost') else .9,reason='Synthetic judgment')
                        for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})]}
            elif 'expression_binding' in data:
                stage='final';value=dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='Synthetic verdict')
            elif 'meaning' in data and 'candidate' in data:
                stage='semantic';value=dict(atom_reviews=[dict(atom_id=x['atom_id'],preserved=True,risks=[])
                    for x in data['meaning']['atoms']],added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
            elif 'meaning' in data:
                stage='author';assert qualifier in raw
                value=qualifier+' [Source](<'+url+'>)'
            elif 'candidate' in data and 'evidence' in data:
                stage='source';assert qualifier in raw
                value=dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='Synthetic source verdict')
            else:raise AssertionError('unexpected controlled stage '+str(list(data)))
            stages.append(stage)
            return httpx.Response(200,request=request,json=dict(id='synthetic-depth',object='chat.completion',created=0,
                model=body['model'],choices=[dict(index=0,message=dict(role='assistant',content=value if isinstance(value,str)
                    else json.dumps(value)),finish_reason='stop')],usage=dict(prompt_tokens=30,completion_tokens=30,total_tokens=60)))
        def checked(request):
            try:return respond(request)
            except AssertionError:
                import traceback;traceback.print_exc();raise
        async def send(client,request,*args,**kwargs):return checked(request)
        execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
        async def allowed(self,target):return target==url
        with patch.object(httpx.AsyncClient,'send',send),patch.object(httpx.Client,'send',lambda client,request,*a,**k:checked(request)),\
             patch.object(execution.kernel('core_discovery_tools').CoreDiscoveryTools,'allow_url',allowed):
            assert '已启用' in await command('enable')
            binding.arguments['stop'].set();await binding.task
            native=binding.native;result=await native.step(binding.arguments['build_parameters']())
            assert result.disposition=='submitted',result
            assert not native.pending
        assert reads==[('web_search',dict(query='synthetic public observation',limit=3)),
            ('web_extract',dict(urls=[url],char_limit=6000)),('web_extract',dict(urls=[url],char_limit=15000))]
        assert len(sent)==1 and qualifier in sent[0][1]
        assert stages.count('reading')==stages.count('deepen')==1
        assert all(stage in stages for stage in ('interpret','select','author','semantic','final'))
        print('HERMES_ALIVE_CORE_SOURCE_READING_DEPTH_OK '+json.dumps(dict(stages=stages,
            requested_windows=[6000,15000],local_adapter_submissions=1,physical_sends=0,actual_model_inference=False,
            qualification_after_old_window_preserved=True,quality_rounds=0)),flush=True)
    finally:
        if manager is not None:manager.unload()
        core.reset_hermes_home_override(token)


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-source-depth-') as directory:
        try:asyncio.run(test(Path(directory)/'profile'))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
