"""Actual installed Alive → Core job → Core agent/file tool, synthetic owner.

Provider replies are controlled; Core job storage/dispatch/tool effects are real.
This does not prove real-model intent, independent semantic verification or the
Native autonomous decision branch. No channel, real provider or private history.
"""
import asyncio,hashlib,importlib,json,os,shutil,subprocess,sys,tempfile,threading
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

if __name__=='__main__' and os.environ.get('ALIVE_WORK_TEST_CHILD')!='1':
    with tempfile.TemporaryDirectory(prefix='alive-core-work-handoff-') as root:
        env={**os.environ,'HOME':root,'HERMES_HOME':str(Path(root)/'profile'),
             'ALIVE_WORK_TEST_CHILD':'1','PYTHONDONTWRITEBYTECODE':'1'}
        try:
            result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env=env,
                capture_output=True,text=True,timeout=300)
            assert result.returncode==0,result.stdout+'\n'+result.stderr
            assert 'HERMES_ALIVE_CORE_WORK_HANDOFF_OK' in result.stdout,result.stdout
            cold=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],
                env={**env,'ALIVE_WORK_CHECK':'1'},capture_output=True,text=True,timeout=60)
            assert cold.returncode==0,cold.stdout+'\n'+cold.stderr
            assert 'HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK' in cold.stdout,cold.stdout
            print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
        finally:
            # Only this fresh isolated profile's Gateway, never a host instance.
            stopped=subprocess.run([sys.executable,'-B','-m','hermes_cli.main','gateway','stop'],env=env,
                capture_output=True,text=True,timeout=30)
            assert stopped.returncode==0,'isolated Core Gateway did not stop cleanly'
    raise SystemExit(0)

import run_core_session_routing as core
from run_core_guided_setup import cli


async def test(home):
    home.mkdir(exist_ok=True);shutil.copytree(core.repo,home/'plugins/hermes-alive')
    responses={}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.send_error(503)
        def do_POST(self):
            import httpx
            data=self.rfile.read(int(self.headers.get('content-length','0')))
            response=responses['handler'](None,httpx.Request('POST',
                'http://127.0.0.1:'+str(server.server_port)+self.path,content=data))
            self.send_response(response.status_code)
            self.send_header('content-type',response.headers.get('content-type','application/json'))
            payload=response.read();self.send_header('content-length',str(len(payload)))
            self.end_headers();self.wfile.write(payload)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'custom:owner','default':'configured-primary'},
        'custom_providers':[{'name':'owner','model':'configured-primary','base_url':'http://127.0.0.1:'+str(server.server_port)+'/v1',
                             'key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}]}))
    (home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n')
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
        '--confirm-followup-management','--confirm-core-background-work','--automatic-core-toolset','file')
    assert rc==0 and staged['confirmation_summary']['native_core_background_work']
    assert staged['confirmation_summary']['automatic_core_toolsets']==['file']
    assert cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None
    try:
        import httpx,model_tools
        import tools.file_tools
        from agent.turn_context import _collect_pre_llm_call_context
        from hermes_cli.plugins import get_plugin_command_handler
        from cron import jobs
        from cron.scheduler import tick,_resolve_cron_enabled_toolsets
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];assert loaded.enabled and not loaded.error
        binding=loaded.module._gateway_host_binding
        setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
        execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
        adapter=core.Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-100694241',
            user_id='synthetic-work-owner',message_id='work-setup')
        entry=runner.session_store.get_or_create_session(source);handler=get_plugin_command_handler('alive')
        async def command(args):
            return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=args)
        def forbidden(*args,**kwargs):raise AssertionError('unexpected model/network IO')
        with patch.object(httpx.Client,'send',forbidden),patch.object(httpx.AsyncClient,'send',forbidden):
            assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
            assert '已启用' in await command('enable')
            binding.arguments['stop'].set();await binding.task
        store=setup.setup_store(binding)
        artifact=home/'core-work-result.txt';body='INDEPENDENT_SYNTHETIC_ARTIFACT\n'
        variables=None
        def turn(name,text):
            nonlocal variables
            if variables:core.clear_session_vars(variables)
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            context=_collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id=name,turn_id=name,
                original_user_message=text,messages=[{'role':'user','content':text}],conversation_history=[])
            assert 'alive_agenda' in context
            def tool(args):
                return json.loads(model_tools.handle_function_call('alive_agenda',args,task_id=name,
                    session_id=entry.session_id,turn_id=name,tool_call_id=name+'-call',enabled_tools=['alive_agenda']))
            return tool
        text='持续整理测试记录，并在我要求执行时写到指定结果文件。不要发送消息。'
        tool=turn('work-intake',text)
        item=tool({'operation':'record','task':'将测试记录标识 INDEPENDENT_SYNTHETIC_ARTIFACT 原样写入 '+str(artifact),
            'constraint':'不要发送消息','evidence_span':text})
        assert item.get('status')=='recorded_under_owner_intake_grant',item
        row=tool({'operation':'list','item_id':item['item_id']})['items'][0]
        text='现在执行这项工作，写入指定结果文件，不要发送消息。'
        tool=turn('work-launch',text)
        payload={'operation':'work','item_id':row['item_id'],'item_version':row['item_version'],
                 'toolsets':['file'],'evidence_span':text}
        started=tool(payload);assert started.get('status')=='submitted_to_core',started
        assert tool(payload)['work_id']==started['work_id']
        assert len(jobs.list_jobs(include_disabled=True))==1
        job=jobs.get_job(started['job_id'])
        assert job['enabled_toolsets']==['file','no_mcp'] and job['deliver']=='local'
        cfg={'mcp_servers':{'synthetic-new-server':{'command':'not-executed'}}}
        assert set(_resolve_cron_enabled_toolsets({'enabled_toolsets':['file']},cfg))>{'file'}
        assert set(_resolve_cron_enabled_toolsets(job,cfg))=={'file'}
        # Drive the actually assembled Native owner loop, not a separate poller.
        # Replies are controlled abstention; lifecycle facts and wakeups are real.
        native=binding.native;build=binding.arguments['build_parameters'];progress_prompts=[]
        class ProgressCaller:
            pending=()
            def __init__(self,*,cycle,read_binding):self.calls=0;self.read_binding=read_binding
            async def reap_pending(self,**kw):return {'closed':0,'remaining':0}
            async def __call__(self,**kw):
                self.read_binding();self.calls+=1
                assert kw['task']=='alive_opportunity_candidates',kw['task']
                progress_prompts.append(json.dumps(kw['messages'],ensure_ascii=False))
                if isinstance(kw.get('route_info'),dict):kw['route_info']['provider']='synthetic-provider'
                return SimpleNamespace(model='synthetic-model',choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps({'candidates':[]})))])
        native.caller_factory=lambda **kw:ProgressCaller(**kw)
        first=await native.step(build())
        assert first.disposition=='silence',first.disposition
        assert len(progress_prompts)==1 and 'submitted_to_core' in progress_prompts[0]
        observations=list(store.journal.read(event_type='work.observed'))
        assert len(observations)==1
        assert (await native.step(build())).disposition=='waiting_for_change'
        assert len(progress_prompts)==1 and len(list(store.journal.read(event_type='work.observed')))==1
        requests=[]
        def respond(client,request,*args,**kwargs):
            if not request.url.path.endswith('/chat/completions'):
                return httpx.Response(503,request=request,json={'error':{'message':'synthetic metadata unavailable'}})
            assert request.url.host=='127.0.0.1' and request.url.port==server.server_port
            data=json.loads(request.content);requests.append(data)
            rendered=json.dumps(data['messages'],ensure_ascii=False)
            assert str(artifact) in rendered and '不要发送消息' in rendered
            assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' in rendered
            if any(m['role']=='tool' for m in data['messages']):
                message={'role':'assistant','content':'The requested test artifact was created.'};finish='stop'
            else:
                names=[t.get('function',{}).get('name') for t in data.get('tools',[])]
                assert 'write_file' in names,names
                message={'role':'assistant','content':None,'tool_calls':[{'id':'write-owned-result','type':'function',
                    'function':{'name':'write_file','arguments':json.dumps({'path':str(artifact),'content':body})}}]};finish='tool_calls'
            if data.get('stream'):
                delta={k:v for k,v in message.items() if k!='role'}
                if 'tool_calls' in delta:delta['tool_calls'][0]['index']=0
                chunk={'id':'synthetic-work','object':'chat.completion.chunk','created':0,'model':'configured-primary',
                       'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
                return httpx.Response(200,request=request,headers={'content-type':'text/event-stream'},
                    content='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
            return httpx.Response(200,request=request,json={'id':'synthetic-work','object':'chat.completion','created':0,
                'model':'configured-primary','choices':[{'index':0,'message':message,'finish_reason':finish}],
                'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}})
        responses['handler']=respond
        assert tick(verbose=False,sync=True,headless=False)==1
        status=tool({'operation':'work_status','work_id':started['work_id']})
        assert status.get('core_execution_state')=='completed',(status,jobs.get_job(started['job_id']).get('last_error'))
        assert artifact.read_text()==body and requests
        assert status['task_success_proven'] is False and status['agenda_completed'] is False
        by_item=tool({'operation':'work_status','item_id':row['item_id']})
        assert by_item['work_id']==started['work_id'] and len(jobs.list_jobs(include_disabled=True))==1
        assert tool({'operation':'list','item_id':row['item_id']})['items'][0]['state']=='active'
        reader=execution.kernel('cognition_opportunities').CognitionOpportunityReader(store.journal)
        # A changed Core state invalidates the old snapshot until the next host
        # observation; it must never reappear as a reminder to perform the task.
        assert reader.commitments(subject=store.configuration().subject,
            clearance=execution.kernel('events').Sensitivity.PRIVATE)==()
        after=await native.step(build())
        assert after.disposition=='silence' and len(progress_prompts)==2,after.disposition
        assert 'core_completed_result_unverified' in progress_prompts[-1]
        assert 'task_success_proven' in progress_prompts[-1] and 'not result contents' in progress_prompts[-1]
        evidence=reader.commitments(subject=store.configuration().subject,
            clearance=execution.kernel('events').Sensitivity.PRIVATE)
        assert len(evidence)==1 and evidence[0].content['core_work']['task_success_proven'] is False
        assert evidence[0].observation_event_id!=observations[0].event.event_id
        assert reader.active_evidence(subject=store.configuration().subject,
            clearance=execution.kernel('events').Sensitivity.PRIVATE,
            observation_event_ids=(evidence[0].observation_event_id,))[0]==evidence[0]
        assert (await native.step(build())).disposition=='waiting_for_change'
        assert len(progress_prompts)==2 and len(list(store.journal.read(event_type='work.observed')))==2
        assert len(jobs.list_jobs(include_disabled=True))==1 and artifact.read_text()==body
        # Actual authored Core-definition drift must also wake the same host,
        # without executing the broadened job or hiding the uncertainty.
        jobs.update_job(started['job_id'],{'enabled_toolsets':['terminal']})
        assert (await native.step(build())).disposition=='silence'
        assert len(progress_prompts)==3 and 'core_job_definition_changed' in progress_prompts[-1]
        jobs.update_job(started['job_id'],{'enabled_toolsets':['file','no_mcp']})
        assert (await native.step(build())).disposition=='silence'
        assert len(progress_prompts)==4 and 'core_completed_result_unverified' in progress_prompts[-1]
        assert len(list(store.journal.read(event_type='work.observed')))==3
        for observation in store.journal.read(event_type='work.observed'):
            assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' not in observation.event.canonical_json()
        assert tick(verbose=False,sync=True,headless=True)==0
        # New attempts, even in the automatic scope, disclose prior effects.
        text='请再做一次刚才的工作。';tool=turn('work-repeat',text)
        repeated=tool({**payload,'evidence_span':text})
        assert repeated['status']=='work_confirmation_required' and not repeated['job_created']
        assert repeated['preview']['new_attempt_may_repeat_existing_effects']
        assert len(jobs.list_jobs(include_disabled=True))==1
        # A different item with a broader toolset needs exact owner confirmation.
        text='持续检查另一项测试，只在我要求时处理。';tool=turn('other-work',text)
        other=tool({'operation':'record','task':'另一项合成测试','evidence_span':text})
        other_row=tool({'operation':'list','item_id':other['item_id']})['items'][0]
        draft=tool({'operation':'work','item_id':other_row['item_id'],'item_version':other_row['item_version'],
                    'toolsets':['terminal'],'evidence_span':text})
        assert draft['status']=='work_confirmation_required' and len(jobs.list_jobs(include_disabled=True))==1
        result=json.loads(await command(draft['confirmation_command'].removeprefix('/alive ')))
        assert result['status']=='submitted_to_core',result
        assert len(jobs.list_jobs(include_disabled=True))==2
        duplicate=json.loads(await command(draft['confirmation_command'].removeprefix('/alive ')))
        assert duplicate['confirmation_already_handled'] and duplicate['new_job_created'] is False
        assert duplicate['work_id']==result['work_id'] and len(jobs.list_jobs(include_disabled=True))==2
        jobs.pause_job(result['job_id'],reason='Synthetic qualification: registration only')
        from cron.executions import latest_execution
        assert latest_execution(result['job_id']) is None
        # Fault after Core creates a real paused job, before Alive can bind it.
        text='持续准备第三项合成工作，只在要求时处理。';tool=turn('fault-intake',text)
        third=tool({'operation':'record','task':'第三项合成工作','evidence_span':text})
        third_row=tool({'operation':'list','item_id':third['item_id']})['items'][0]
        payload={'operation':'work','item_id':third_row['item_id'],'item_version':third_row['item_version'],
                 'toolsets':['file'],'evidence_span':text}
        original_create=jobs.create_job
        created=[]
        def create_then_fault(*args,**kwargs):
            actual=original_create(*args,**kwargs);created.append(actual)
            raise RuntimeError('synthetic handoff fault after Core creation')
        with patch.object(jobs,'create_job',create_then_fault):
            failed=tool(payload)
            assert failed['status']=='handoff_uncertain' and failed['needs_attention'],failed
        assert len(created)==1 and jobs.get_job(created[0]['id'])['state']=='paused'
        replay=tool(payload)
        assert replay['status']=='handoff_uncertain' and replay['automatic_retry_allowed'] is False
        assert len(jobs.list_jobs(include_disabled=True))==3
        text='持续准备以后才开始的第五项工作。';tool=turn('future-work',text)
        future=tool({'operation':'record','task':'尚未到开始时间的事项','evidence_span':text,
                     'available_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()})
        future_row=tool({'operation':'list','item_id':future['item_id']})['items'][0]
        early=tool({'operation':'work','item_id':future_row['item_id'],'item_version':future_row['item_version'],
                    'toolsets':['file'],'evidence_span':text})
        assert early['error']=='work_not_available_yet' and early['job_created'] is False
        assert len(jobs.list_jobs(include_disabled=True))==3
        # Grant revocation after paused preparation must precede activation.
        text='记下第四项合成工作，按要求处理。';tool=turn('pause-work',text)
        fourth=tool({'operation':'record','task':'第四项合成工作','evidence_span':text})
        fourth_row=tool({'operation':'list','item_id':fourth['item_id']})['items'][0]
        prepared=[]
        scope=binding._continuity.router.capture_target(session_key=entry.session_key,
            user_id=source.user_id,platform='telegram')
        def create_then_pause(*args,**kwargs):
            actual=original_create(*args,**kwargs);prepared.append(actual)
            execution.pause(binding,scope)  # controlled revocation through the real control API
            return actual
        with patch.object(jobs,'create_job',create_then_pause):
            revoked=tool({'operation':'work','item_id':fourth_row['item_id'],'item_version':fourth_row['item_version'],
                          'toolsets':['file'],'evidence_span':text})
            assert revoked['status']=='prepared_not_activated_by_alive' and revoked['needs_attention'],revoked
        assert len(prepared)==1 and jobs.get_job(prepared[0]['id'])['state']=='paused'
        assert latest_execution(prepared[0]['id']) is None
        held=tool({'operation':'work_status','item_id':fourth_row['item_id']})
        assert held['status']=='prepared_not_activated_by_alive' and held['automatic_result_followup_enabled'] is False
        observations_before_pause=len(list(store.journal.read(event_type='work.observed')))
        calls_before_pause=len(progress_prompts)
        assert (await native.step(build())).disposition=='paused'
        assert len(progress_prompts)==calls_before_pause
        assert len(list(store.journal.read(event_type='work.observed')))==observations_before_pause
        for record in store.journal.read(event_type='work.requested'):
            assert record.event.payload['task_body_copied_into_alive_journal'] is False
            assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' not in record.event.canonical_json()
        # Exact definition changes are detected instead of reporting a healthy run.
        jobs.update_job(started['job_id'],{'enabled_toolsets':['terminal']})
        changed=tool({'operation':'work_status','work_id':started['work_id']})
        assert changed['status']=='core_job_definition_changed' and changed['needs_attention']
        jobs.update_job(started['job_id'],{'enabled_toolsets':['file','no_mcp']})
        keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
        (home/'work-handoff-expected.json').write_text(json.dumps({'work_id':started['work_id'],
            'owner':store.configuration().subject,
            'keys':{name:hashlib.sha256((store.root/name).read_bytes()).hexdigest() for name in keys}}))
        # Do not tick this broader job: this test proves authorization/registration,
        # not a terminal command run or an additional authorized external effect.
        print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
    finally:
        if 'variables' in locals() and variables:core.clear_session_vars(variables)
        if manager:manager.unload()
        core.reset_hermes_home_override(token)
        from hermes_state_registry import close_all_under
        close_all_under(home)
        server.shutdown();server.server_close();server_thread.join(timeout=5)
        assert not server_thread.is_alive()


if __name__=='__main__':
    if os.environ.get('ALIVE_WORK_CHECK')=='1':
        home=Path(os.environ['HERMES_HOME'])
        expected=json.loads((home/'work-handoff-expected.json').read_text())
        execution=importlib.import_module('alive_session_fixture.kernel_execution_bridge')
        store=execution.kernel('kernel_setup').KernelSetupStore(home/'plugin-data/hermes-alive/runtime/kernel')
        assert all(hashlib.sha256((store.root/name).read_bytes()).hexdigest()==digest for name,digest in expected['keys'].items())
        status=execution.kernel('core_work').CoreWorkStore(store).status(expected['work_id'],subject=expected['owner'])
        assert status['core_execution_state']=='completed' and status['task_success_proven'] is False,status
        observation=execution.kernel('core_work').CoreWorkStore(store).current_observation(
            status['item_id'],subject=expected['owner'])
        assert observation is not None and observation[1]==status
        print('HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK')
    else:
        asyncio.run(test(Path(os.environ['HERMES_HOME'])))
