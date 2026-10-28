"""Actual installed Alive → Core job → Core agent/file tool, synthetic owner.

Provider replies are controlled; Core job storage/dispatch/tool effects are real.
This does not prove real-model intent, independent semantic verification or the
Native autonomous decision branch. No channel, real provider or private history.
"""
import asyncio,hashlib,importlib,json,os,shutil,subprocess,sys,tempfile,threading
from dataclasses import replace
from contextlib import closing
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
            if os.environ.get('ALIVE_RETIRE_RUNNING'):
                proof='CORE_RUNNING_RETIREMENT_PROVEN '+os.environ['ALIVE_RETIRE_RUNNING']+' '
                assert proof in result.stdout,result.stdout
                print(next(line for line in result.stdout.splitlines() if line.startswith(proof)),flush=True)
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
    project_mode=os.environ.get('ALIVE_WORK_PROJECT_TEST')=='1'
    stop_mode=os.environ.get('ALIVE_WORK_STOP_TEST','')
    assert stop_mode in ('','pending','running','fenced','retry')
    stop_entered=threading.Event();stop_release=threading.Event()
    stopped_inspection=os.environ.get('ALIVE_WORK_INSPECTION_STOP_TEST')=='1'
    concurrent_inspection=os.environ.get('ALIVE_WORK_INSPECTION_CONCURRENT_TEST')=='1'
    concurrent_fired=[]
    revoked_inspection=os.environ.get('ALIVE_WORK_INSPECTION_REVOKE_TEST')=='1'
    inspection_mode=os.environ.get('ALIVE_WORK_INSPECTION_TEST')=='1' or revoked_inspection or stopped_inspection
    review_records=os.environ.get('ALIVE_WORK_REVIEW_TEST')=='1' or inspection_mode
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
        '--confirm-followup-management','--confirm-core-background-work','--automatic-core-toolset','file',
        *(['--confirm-core-work-result-review'] if review_records else []),
        *(['--confirm-core-file-inspection'] if inspection_mode else []))
    assert rc==0 and staged['confirmation_summary']['native_core_background_work']
    assert staged['confirmation_summary']['exact_current_work_message_retained_by_core'] is True
    assert staged['confirmation_summary']['automatic_core_toolsets']==['file']
    assert staged['confirmation_summary']['bounded_owned_core_result_review'] is review_records
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
        if project_mode:
            project=home/'assigned-project';project.mkdir()
            other=home/'other-project';other.mkdir()
            (project/'AGENTS.md').write_text('PUBLIC_INSPECTION_PROJECT_RULE_A',encoding='utf-8')
            (other/'AGENTS.md').write_text('PUBLIC_INSPECTION_PROJECT_RULE_B',encoding='utf-8')
            artifact=project/artifact.name
        producer_path=artifact.name if project_mode else str(artifact)
        variables=None
        def turn(name,text):
            nonlocal variables
            if variables:core.clear_session_vars(variables)
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            if project_mode:
                from tools.terminal_tool import record_session_cwd
                record_session_cwd(name,str(project if name=='work-intake' else other))
            context=_collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id=name,turn_id=name,
                original_user_message=text,messages=[{'role':'user','content':text}],conversation_history=[])
            assert 'alive_agenda' in context
            contract=json.JSONDecoder().raw_decode(context[context.index('{"tool":"alive_agenda"'):])[0]
            turn.last_contract=contract
            bridge=importlib.import_module(loaded.module.__name__+'.gateway_agenda_bridge')
            assert set(contract['operations'])==set(bridge._OPERATION_FIELDS)==set(bridge._OPERATION_EFFECTS)
            assert all(v['effect']==bridge._OPERATION_EFFECTS[k] for k,v in contract['operations'].items())
            assert set(contract['operations'])==set(bridge.AGENDA_SCHEMA['parameters']['properties']['operation']['enum'])
            assert all(set(value['fields'])==set(bridge._OPERATION_FIELDS[name])-{'operation'} for name,value in contract['operations'].items())
            assert contract['eligible_is_not_operation_confirmation'] is True
            assert contract['background_work']['project_binding_change_operations']==[]
            assert contract['runtime']['proactive_runtime']=='stopped'
            if not text:
                assert not contract['operations']['record']['eligible_for_request_evaluation']
                assert not contract['operations']['work']['eligible_for_request_evaluation']
                assert contract['operations']['list']['eligible_for_request_evaluation']
            def tool(args):
                return json.loads(model_tools.handle_function_call('alive_agenda',args,task_id=name,
                    session_id=entry.session_id,turn_id=name,tool_call_id=name+'-call',enabled_tools=['alive_agenda']))
            return tool
        if os.environ.get('ALIVE_WORK_CONTRACT_TEST')=='1':
            before=store.journal.last_sequence()
            empty=turn('empty-owner-turn','')
            rejected=empty({'operation':'record','task':'MUST_NOT_RECORD_EMPTY_TURN','evidence_span':'MUST_NOT_RECORD_EMPTY_TURN'})
            assert 'error' in rejected and store.journal.last_sequence()==before and not jobs.list_jobs(include_disabled=True)
            configured=store.configuration();intake=execution.kernel('followup_intake')
            intake.set_permission(store,configured,False)
            before=store.journal.last_sequence()
            revoked=turn('revoked-owner-intake','请登记这项合成任务。')
            denied=revoked({'operation':'record','task':'MUST_NOT_RECORD_REVOKED','evidence_span':'请登记这项合成任务。'})
            assert 'error' in denied and store.journal.last_sequence()==before and not jobs.list_jobs(include_disabled=True)
            assert turn.last_contract['owner_delegation']['direct_intake_grant_active'] is False
            assert not turn.last_contract['operations']['record']['eligible_for_request_evaluation']
            assert not binding._agenda.operation_contract(configured,current_turn_eligible=False)['operations']['record']['eligible_for_request_evaluation']
            intake.set_permission(store,configured,True)
        text='持续整理测试记录，并在我要求执行时写到指定结果文件。不要发送消息。'
        tool=turn('work-intake',text)
        assert turn.last_contract['owner_delegation']['clear_current_assignment_mode']=='record_without_per_item_confirmation'
        item=tool({'operation':'record','task':'将测试记录标识 INDEPENDENT_SYNTHETIC_ARTIFACT 原样写入 '+str(artifact),
            'constraint':'不要发送消息','evidence_span':text})
        assert item.get('status')=='recorded_under_owner_intake_grant',item
        row=tool({'operation':'list','item_id':item['item_id']})['items'][0]
        original_request=text
        assert row['original_owner_message']==original_request
        assert row['details_origin']=='agenda_description_not_verified_verbatim'
        assert row['original_owner_message']!=row['details']['task']
        inventory=tool({'operation':'list'})['items'][0]
        assert inventory['original_source_available'] and not inventory['original_owner_message_included']
        assert 'original_owner_message' not in inventory
        source_record=store.journal.get(row['source_event_id'])
        assert source_record.event.payload['raw_content_stored'] is True
        assert original_request not in source_record.event.canonical_json()
        oversized=turn('work-oversized','查'*6001)
        refused=oversized({'operation':'work','item_id':row['item_id'],'item_version':row['item_version'],
                          'toolsets':['file'],'evidence_span':'查'})
        assert refused['error']=='bounded_current_work_request_required' and not jobs.list_jobs(include_disabled=True)
        text='现在执行这项工作，写入指定结果文件。\n不要发送消息。'
        tool=turn('work-launch',text)
        payload={'operation':'work','item_id':row['item_id'],'item_version':row['item_version'],
                 'toolsets':['file'],'evidence_span':text}
        before_invalid=store.journal.last_sequence()
        invalid=tool({**payload,'task':'Unsupported model-supplied rewrite','constraint':'Do not silently discard me'})
        assert invalid['error']=='alive_agenda_arguments_invalid' and not invalid['request_processed']
        assert not invalid['new_job_created'] and 'task' not in invalid['allowed_fields']
        assert not jobs.list_jobs(include_disabled=True)
        assert store.journal.last_sequence()==before_invalid
        started=tool(payload);assert started.get('status')=='submitted_to_core',started
        assert tool(payload)['work_id']==started['work_id']
        assert len(jobs.list_jobs(include_disabled=True))==1
        job=jobs.get_job(started['job_id'])
        assert json.loads(job['prompt'].rsplit('\n',1)[1])['current_owner_message']==text
        work_store=execution.kernel('core_work').CoreWorkStore(store)
        configured=store.configuration()
        receipt=work_store._read(started['work_id'],'requested',configured.subject)
        assert text not in store.journal.get(started['work_id']+':requested').event.canonical_json()
        for candidate,body_request in ((replace(configured,options={**dict(configured.options),
                'core_work_request_retention':False}),text),(configured,text+' tampered')):
            try:
                work_store.launch(candidate,item=row,turn_evidence=dict(receipt['turn_evidence']),
                    owner_request=body_request,toolsets=['file'],validate=lambda:None)
                raise AssertionError('legacy retention or changed source silently admitted')
            except ValueError:pass
        assert len(jobs.list_jobs(include_disabled=True))==1
        assert job['enabled_toolsets']==['file','no_mcp'] and job['deliver']=='local'
        if project_mode:assert job['workdir']==str(project.resolve())
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
                if kw['task']=='alive_core_file_inspection':
                    assert inspection_mode
                    source=json.loads(kw['messages'][-1]['content'])
                    target=source['targets'][0]
                    return SimpleNamespace(model='synthetic-model',choices=[SimpleNamespace(message=SimpleNamespace(
                        content=json.dumps({'decision':'inspect','target_id':target['target_id'],
                            'reason':'Read the current artifact independently before judging the producer result.',
                            'reconsider_after_seconds':None})))])
                assert kw['task']=='alive_opportunity_candidates',kw['task']
                progress_prompts.append(json.dumps(kw['messages'],ensure_ascii=False))
                if concurrent_inspection and not concurrent_fired and 'separate_result_inspection' in progress_prompts[-1]:
                    concurrent_fired.append(True)
                    assert await asyncio.to_thread(tick,verbose=False,sync=True,headless=False)==1

                if isinstance(kw.get('route_info'),dict):kw['route_info']['provider']='synthetic-provider'
                document={'candidates':[]}
                if review_records:
                    current=json.loads(kw['messages'][-1]['content'])['opportunities'][0]
                    reason=('Untrusted worker claim needs independent verification.'
                        if 'SYNTHETIC_UNVERIFIED_WORKER_CLAIM' in progress_prompts[-1] else
                        'Recorded write/read is available; fresh verification is still missing.'
                        if 'core_work_record_review' in current.get('summary_excerpt','') else
                        'Wait for attributable execution evidence.')
                    if inspection_mode and 'FRESH_EXTERNAL_STATE_AFTER_PRODUCER' in progress_prompts[-1]:
                        reason='Fresh inspection shows changed content; keep this work unresolved.'
                    document['abstentions']=[{'agenda_item_id':current['agenda_item_id'],'reason':reason}]
                return SimpleNamespace(model='synthetic-model',choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(document)))])
        native.caller_factory=lambda **kw:ProgressCaller(**kw)
        first=await native.step(build())
        assert first.disposition=='silence',first.disposition
        assert len(progress_prompts)==1 and 'submitted_to_core' in progress_prompts[0]
        assert original_request in progress_prompts[0] and 'original_owner_message' in progress_prompts[0]
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
            if project_mode:
                assert 'PUBLIC_INSPECTION_PROJECT_RULE_A' in rendered
                assert 'PUBLIC_INSPECTION_PROJECT_RULE_B' not in rendered
            assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' in rendered
            assert 'current_owner_message' in rendered and '写入指定结果文件' in rendered
            if stop_mode in ('running','fenced','retry'):
                stop_entered.set()
                assert stop_release.wait(30),'stop qualification did not release provider'
            if any(c.get('function',{}).get('name')=='read_file' for m in data['messages'] for c in m.get('tool_calls',[])):
                message={'role':'assistant','content':'The requested test artifact was created.'};finish='stop'
            elif any(m['role']=='tool' for m in data['messages']):
                message={'role':'assistant','content':None,'tool_calls':[{'id':'read-owned-result','type':'function',
                    'function':{'name':'read_file','arguments':json.dumps({'path':producer_path})}}]};finish='tool_calls'
            else:
                names=[t.get('function',{}).get('name') for t in data.get('tools',[])]
                assert 'write_file' in names,names
                message={'role':'assistant','content':None,'tool_calls':[{'id':'write-owned-result','type':'function',
                    'function':{'name':'write_file','arguments':json.dumps({'path':producer_path,'content':body})}}]};finish='tool_calls'
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
        if stop_mode:
            if stop_mode=='pending':
                scope=binding._continuity.router.capture_target(session_key=entry.session_key,
                    user_id=source.user_id,platform='telegram')
                execution.pause(binding,scope)  # pausing Alive cannot revoke the owner's ability to stop its work
            clock=None
            if stop_mode in ('running','fenced','retry'):
                clock=asyncio.create_task(asyncio.to_thread(tick,verbose=False,sync=True,headless=False))
                assert await asyncio.to_thread(stop_entered.wait,20),'Core worker did not enter its model request'
            if os.environ.get('ALIVE_RETIRE_RUNNING'):
                from run_core_work_retirement import qualify_running
                await qualify_running(binding=binding,manager=manager,home=home,store=store,
                    execution=execution,command=command,started=started,configured=configured,
                    stop_release=stop_release,clock=clock,artifact=artifact,work_store=work_store)
                print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
                return
            text='停止这项合成文件工作，不要再执行。'
            stop_tool=turn('owner-stop-work',text)
            count=len(list(store.journal.read()))
            bad=await asyncio.to_thread(stop_tool,{'operation':'work_stop','work_id':started['work_id'],
                'evidence_span':'not in current owner message'})
            assert 'error' in bad and len(list(store.journal.read()))==count
            foreign=await asyncio.to_thread(stop_tool,{'operation':'work_stop','work_id':'core-work:'+'f'*64,
                'evidence_span':text})
            assert 'error' in foreign and len(list(store.journal.read()))==count
            try:
                stop_args={'operation':'work_stop','work_id':started['work_id'],'evidence_span':text}
                if stop_mode in ('fenced','retry'):
                    control_type=execution.kernel('core_work_control').CoreWorkControl
                    async def unavailable_owner(*args,**kwargs):raise TimeoutError('synthetic lost cancellation answer')
                    with patch.object(control_type,'_cancel_owner',unavailable_owner):
                        stopped=await asyncio.to_thread(stop_tool,stop_args)
                        before_attempts=len(list(store.journal.read(event_type='work.stop_dispatch_started')))
                        repeated=await asyncio.to_thread(stop_tool,stop_args)
                        assert repeated['targets'][0]['needs_attention'] is True
                        another_span=await asyncio.to_thread(stop_tool,{**stop_args,'evidence_span':'不要再执行'})
                        assert another_span['targets'][0]['needs_attention'] is True
                        assert len(list(store.journal.read(event_type='work.stop_dispatch_started')))==before_attempts==1
                    assert stopped['targets'][0]['status']=='owner_stop_outcome_unknown'
                    assert stopped['targets'][0]['execution_stopped_proven'] is False
                    if stop_mode=='retry':
                        stopped=json.loads(await command('agenda stop-work '+started['work_id']))
                        assert len(list(store.journal.read(event_type='work.stop_dispatch_started')))==2
                else:
                    stopped=await asyncio.to_thread(stop_tool,stop_args)
                assert stopped['status']=='stop_requested',stopped
                assert stopped['effects_undone'] is False and stopped['new_work_submitted'] is False
                assert len(stopped['targets'])==1
                observed=stopped['targets'][0]
                if stop_mode in ('running','retry'):
                    assert observed.get('cancel_acknowledged') is True,observed
                elif stop_mode=='fenced':
                    assert observed['needs_attention'] and observed['cancel_acknowledged'] is False
                else:
                    assert observed['status']=='schedule_paused_no_execution_observed',observed
                    assert tick(verbose=False,sync=True,headless=False)==0
            finally:
                stop_release.set()
                if clock is not None:await clock
            assert not artifact.exists(),'a stopped Core worker wrote its file'
            if stop_mode=='fenced':
                assert 'This work no longer has valid authorization' in json.dumps(requests)
            assert len(jobs.list_jobs(include_disabled=True))==1
            current=work_store.status(started['work_id'],subject=configured.subject)
            assert current['owner_stop_requested'] is True
            assert current.get('core_execution_state') not in ('claimed','running')
            before=len(list(store.journal.read(event_type='work.stop_dispatch_started')))
            replay=json.loads(await command('agenda stop-work '+started['work_id']))
            assert replay['status']=='stop_requested' and len(list(store.journal.read(event_type='work.stop_dispatch_started')))==before
            assert not artifact.exists() and len(jobs.list_jobs(include_disabled=True))==1
            assert tool({'operation':'work_stop','work_id':started['work_id'],
                'evidence_span':original_request}).get('error')  # retired turn cannot authorize a stop
            assert json.loads(await command('agenda list'))['items'][0]['state']=='active'
            keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
            (home/'stop-expected.json').write_text(json.dumps({'work_id':started['work_id'],
                'owner':configured.subject,'artifact':str(artifact),
                'keys':{n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in keys}}))
            print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
            return
        assert tick(verbose=False,sync=True,headless=False)==1
        status=tool({'operation':'work_status','work_id':started['work_id']})
        assert status.get('core_execution_state')=='completed',(status,jobs.get_job(started['job_id']).get('last_error'))
        assert artifact.read_text()==body and requests
        sessions=list(store.journal.read(event_type='work.session_observed'))
        assert len(sessions)==1,sessions
        observed=work_store.session_binding(started['work_id'],
            sessions[0].event.event_id.removeprefix(started['work_id']+':'),subject=configured.subject)
        assert observed['work_id']==started['work_id'] and observed['execution_id']==status['execution_id']
        assert observed['session_body_copied'] is False and observed['task_success_proven'] is False
        assert observed['private_session_id_encrypted'] is True
        assert observed['session_id'] not in sessions[0].event.canonical_json()
        assert work_store.observe_session(configured,execution=SimpleNamespace(job_id=started['job_id'],
            execution_id=status['execution_id']),session_id=observed['session_id']) is False
        from hermes_state import SessionDB
        db=SessionDB()
        try:
            actual_session=db.get_session(observed['session_id'])
            actual_messages=db.get_messages(observed['session_id'],limit=64)
            assert actual_session is not None and actual_session['source']=='cron',actual_session
            names={c['id']:c.get('function',{}).get('name') for m in actual_messages for c in (m.get('tool_calls') or [])}
            assert any(m['role']=='tool' and (m.get('tool_name') or names.get(m.get('tool_call_id')))=='read_file'
                and 'INDEPENDENT_SYNTHETIC_ARTIFACT' in str(m.get('content')) for m in actual_messages)
        finally:db.close()
        assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' not in sessions[0].event.canonical_json()
        evidence=tool({'operation':'work_evidence','work_id':started['work_id']})
        definition=tool({'operation':'work_evidence','work_id':started['work_id'],'part':'request'})
        assert definition['status']=='core_work_request_evidence' and definition['contains_exact_current_owner_message']
        assert definition['assignment_item_version']==row['item_version'] and str(artifact) in definition['content']
        assert definition['content_complete'] and 'current_owner_message' in definition['content']
        assert evidence['status']=='core_execution_evidence' and evidence['core_execution_state']=='completed',evidence
        assert evidence['task_success_proven'] is False and evidence['content_persisted_by_alive'] is False
        witness=next(e for e in evidence['entries'] if e['tool_name']=='read_file' and e['kind']=='recorded_tool_result')
        assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' in witness['content']
        read_request=next(e for e in evidence['entries'] if any(c['name']=='read_file' for c in e['tool_requests']))
        assert read_request['arguments_omitted_from_default_window'] and not read_request['content']
        before_page=store.journal.last_sequence()
        with patch('hermes_state.SessionDB',side_effect=AssertionError('malformed page opened Core bodies')):
            missing_work=tool({'operation':'work_evidence','evidence_reference':evidence['evidence_reference'],
                              'message_id':read_request['message_id']})
        assert missing_work['error']=='alive_agenda_arguments_invalid'
        assert missing_work['required_fields']==['work_id'] and not missing_work['request_processed']
        assert store.journal.last_sequence()==before_page and len(jobs.list_jobs(include_disabled=True))==1
        request_page=tool({'operation':'work_evidence','work_id':started['work_id'],
            'evidence_reference':evidence['evidence_reference'],'message_id':read_request['message_id'],
            'fingerprint':read_request['fingerprint']})
        actual_call=json.loads(request_page['entries'][0]['content'])['tool_calls'][0]
        assert json.loads(actual_call['function']['arguments'])['path']==producer_path
        assert actual_call['id']==witness['tool_call_id']
        page=tool({'operation':'work_evidence','work_id':started['work_id'],
            'evidence_reference':evidence['evidence_reference'],'message_id':witness['message_id'],
            'fingerprint':witness['fingerprint'],'max_chars':256})
        assert page['entries'][0]['fingerprint']==witness['fingerprint']
        continuation=tool({'operation':'work_evidence','work_id':started['work_id'],
            'evidence_reference':evidence['evidence_reference'],'message_id':witness['message_id'],
            'fingerprint':witness['fingerprint'],'offset':1,'max_chars':256})
        assert continuation['entries'][0]['content']==witness['content'][1:257]
        bad=tool({'operation':'work_evidence','work_id':started['work_id'],
            'evidence_reference':evidence['evidence_reference'],'message_id':witness['message_id'],
            'fingerprint':'0'*64,'offset':1})
        assert 'error' in bad and 'entries' not in bad,bad
        reader_module=execution.kernel('core_work_evidence')
        with patch('hermes_state.SessionDB',side_effect=AssertionError('foreign owner opened Core bodies')):
            try:
                reader_module.CoreWorkEvidence(work_store).read(started['work_id'],subject='foreign-owner')
                raise AssertionError('foreign owner was accepted')
            except ValueError:pass
        db=SessionDB()
        try:
            db.create_session('foreign-evidence-session',source='cli')
            db.append_message('foreign-evidence-session','assistant','FOREIGN_BODY_MUST_NOT_BE_READ')
            foreign_id=db.get_messages('foreign-evidence-session',limit=1)[0]['id']
        finally:db.close()
        foreign=tool({'operation':'work_evidence','work_id':started['work_id'],
            'evidence_reference':evidence['evidence_reference'],'message_id':foreign_id})
        assert 'error' in foreign and 'FOREIGN_BODY_MUST_NOT_BE_READ' not in json.dumps(foreign)
        assert status['task_success_proven'] is False and status['agenda_completed'] is False
        by_item=tool({'operation':'work_status','item_id':row['item_id']})
        assert by_item['work_id']==started['work_id'] and len(jobs.list_jobs(include_disabled=True))==1
        assert tool({'operation':'list','item_id':row['item_id']})['items'][0]['state']=='active'
        reader=execution.kernel('cognition_opportunities').CognitionOpportunityReader(store.journal)
        # A changed Core state invalidates the old snapshot until the next host
        # observation; it must never reappear as a reminder to perform the task.
        assert reader.commitments(subject=store.configuration().subject,
            clearance=execution.kernel('events').Sensitivity.PRIVATE)==()
        if inspection_mode:
            inspector_module=execution.kernel('core_file_inspection')
            inspector=inspector_module.CoreFileInspection(store)
            fresh='FRESH_EXTERNAL_STATE_AFTER_PRODUCER'
            artifact.write_text(fresh)
            unapproved=home/'unapproved.txt';unapproved.write_text('MUST_NOT_BE_READ')
            inspection_requests=[]
            original_handler=responses['handler']
            def inspect_respond(client,request,*args,**kwargs):
                data=json.loads(request.content)
                if not any('Inspect ONLY the file named inspection_target' in str(m.get('content')) for m in data['messages']):
                    return original_handler(client,request,*args,**kwargs)
                inspection_requests.append(data)
                names={t.get('function',t)['name'] for t in data.get('tools',[])}
                assert names=={'read_file'},names
                if project_mode:
                    assert 'PUBLIC_INSPECTION_PROJECT_RULE_A' in json.dumps(data['messages'])
                    assert 'PUBLIC_INSPECTION_PROJECT_RULE_B' not in json.dumps(data['messages'])
                rendered=json.dumps(data['messages'])
                assert 'MUST_NOT_BE_READ' not in rendered
                if revoked_inspection:
                    if len(inspection_requests)==1:
                        message={'role':'assistant','content':None,'tool_calls':[{'id':'revoked-inspection-file','type':'function',
                            'function':{'name':'read_file','arguments':json.dumps({'path':str(artifact)})}}]};finish='tool_calls'
                    else:
                        assert fresh not in rendered
                        assert any(m.get('role')=='tool' and 'authorization' in str(m.get('content')) for m in data['messages'])
                        message={'role':'assistant','content':'The owner paused inspection; no file result was available.'};finish='stop'
                elif len(inspection_requests)==1:
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'wrong-inspection-file','type':'function',
                        'function':{'name':'read_file','arguments':json.dumps({'path':str(unapproved)})}}]};finish='tool_calls'
                elif len(inspection_requests)==2:
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'approved-inspection-file','type':'function',
                        'function':{'name':'read_file','arguments':json.dumps({'path':str(artifact)})}}]};finish='tool_calls'
                else:
                    assert any(m.get('role')=='tool' and fresh in str(m.get('content')) for m in data['messages'])
                    message={'role':'assistant','content':'Current inspection returned a changed artifact; no completion inferred.'};finish='stop'
                if data.get('stream'):
                    delta={k:v for k,v in message.items() if k!='role'}
                    if 'tool_calls' in delta:delta['tool_calls'][0]['index']=0
                    chunk={'id':'synthetic-inspector','object':'chat.completion.chunk','created':0,'model':'configured-primary',
                        'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
                    return httpx.Response(200,request=request,headers={'content-type':'text/event-stream'},
                        content='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
                return httpx.Response(200,request=request,json={'id':'synthetic-inspector','object':'chat.completion','created':0,
                    'model':'configured-primary','choices':[{'index':0,'message':message,'finish_reason':finish}],
                    'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}})
            responses['handler']=inspect_respond
            if concurrent_inspection:
                before_completed=len(list(store.journal.read(event_type='opportunity.synthesis_completed')))
                changed=await native.step(build())
                assert changed.disposition=='evidence_changed'
                assert len(list(store.journal.read(event_type='opportunity.synthesis_completed')))==before_completed
                failed=list(store.journal.read(event_type='opportunity.synthesis_failed'))[-1].event
                assert failed.payload['error_class']=='OpportunityEvidenceChanged'
                closed=list(store.journal.read(event_type='autonomous.host.closed'))[-1].event
                assert closed.payload['disposition']=='evidence_changed'
            else:
                after=await native.step(build())
                assert after.disposition=='silence'
            leaf=inspector.latest(started['work_id'],subject=configured.subject)
            assert leaf is not None and len(jobs.list_jobs(include_disabled=True))==2
            assert work_store.previous(row['item_id'],subject=configured.subject)['work_id']==started['work_id']
            if os.environ.get('ALIVE_WORK_INSPECTION_ATTENTION')=='1':
                text='这件事明天再向我跟进，已经授权的核验继续。'
                tool=turn('inspection-attention-snooze',text)
                current=tool({'operation':'list','item_id':row['item_id']})['items'][0]
                changed=tool({'operation':'snooze','item_id':row['item_id'],'item_version':current['item_version'],
                    'evidence_span':text,'available_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
                assert changed.get('state')=='snoozed',changed
                assert inspector.source(started['work_id'],configured) is None
                assert not inspector.snapshot(started['work_id'],subject=configured.subject).get('source_item_changed')
            if stopped_inspection:
                answer=json.loads(await command('agenda stop-work '+started['work_id']))
                assert answer['status']=='stop_requested' and len(answer['targets'])==2,answer
                assert answer['targets'][0]['work_kind']=='perform' and answer['targets'][0]['parent_work_id'] is None
                assert answer['targets'][1]['work_kind']=='inspection' and answer['targets'][1]['parent_work_id']==started['work_id']
                assert answer['targets'][0]['status']=='execution_already_terminal'
                assert answer['targets'][1]['status']=='schedule_paused_no_execution_observed'
                assert tick(verbose=False,sync=True,headless=False)==0 and not inspection_requests
                assert artifact.read_text()==fresh and unapproved.read_text()=='MUST_NOT_BE_READ'
                assert (await native.step(build())).disposition=='silence'
                assert len(jobs.list_jobs(include_disabled=True))==2
                keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
                (home/'inspection-expected.json').write_text(json.dumps({'parent':started['work_id'],'child':leaf[0],
                    'owner':configured.subject,'stopped':True,'keys':{n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in keys}}))
                print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
                return
            if revoked_inspection:
                scope=binding._continuity.router.capture_target(session_key=entry.session_key,
                    user_id=source.user_id,platform='telegram')
                execution.pause(binding,scope)
                # Attempt to re-enable only the derived cache. The signed owner
                # pause must still block the actual Core pre-tool call.
                with closing(store.journal._connect()) as c:
                    c.execute('UPDATE autonomy_policies_v1 SET enabled=1 WHERE subject=?',(configured.subject,))
            if not concurrent_inspection:
                assert tick(verbose=False,sync=True,headless=False)==1
            assert work_store.status(leaf[0],subject=configured.subject)['core_execution_state']=='completed'
            if revoked_inspection:
                assert len(inspection_requests)==2
                assert artifact.read_text()==fresh and unapproved.read_text()=='MUST_NOT_BE_READ'
                try:
                    inspector.snapshot(started['work_id'],subject=configured.subject)
                    raise AssertionError('paused inspection results were made available')
                except ValueError:pass
                with closing(store.journal._connect()) as c:
                    c.execute('UPDATE autonomy_policies_v1 SET enabled=0 WHERE subject=?',(configured.subject,))
                assert (await native.step(build())).disposition=='paused'
                assert len(jobs.list_jobs(include_disabled=True))==2
                keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
                (home/'inspection-expected.json').write_text(json.dumps({'parent':started['work_id'],'child':leaf[0],
                    'owner':configured.subject,'paused':True,'keys':{n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in keys}}))
                print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
                return
            assert artifact.read_text()==fresh and unapproved.read_text()=='MUST_NOT_BE_READ'
            assert len(inspection_requests)==3
            if os.environ.get('ALIVE_WORK_INSPECTION_ATTENTION')=='1':
                text='恢复这件事的关注，核验权限不变。'
                tool=turn('inspection-attention-resume',text)
                current=tool({'operation':'list','item_id':row['item_id']})['items'][0]
                changed=tool({'operation':'resume','item_id':row['item_id'],'item_version':current['item_version'],
                    'evidence_span':text})
                assert changed.get('state')=='active',changed
            after_inspection=await native.step(build())
            assert after_inspection.disposition=='silence'
            assert 'separate_result_inspection' in progress_prompts[-1] and fresh in progress_prompts[-1]
            latest=list(store.journal.read(event_type='opportunity.synthesis_completed'))[-1].event
            assessed=store.vault.resolve_json(latest.payload['content']['content_id'],expected_subject=configured.subject,
                expected_purpose='opportunity.candidates',expected_sensitivity=execution.kernel('events').Sensitivity.PRIVATE)
            assert assessed['abstentions'][0]['reason']=='Fresh inspection shows changed content; keep this work unresolved.'

            snapshot=inspector.snapshot(started['work_id'],subject=configured.subject)
            parent_status=work_store.status(started['work_id'],subject=configured.subject)
            assert parent_status['work_kind']=='perform' and parent_status['parent_work_id'] is None
            linked=parent_status['related_inspections']
            assert len(linked)==1 and linked[0]['work_id']==leaf[0]
            assert linked[0]['work_kind']=='inspection' and linked[0]['parent_work_id']==started['work_id']
            assert linked[0]['core_execution_state']=='completed'
            assert snapshot['work_id']==leaf[0] and snapshot['task_success_proven'] is False
            assert snapshot['target_path']==str(artifact)
            before_calls=len(progress_prompts)
            assert (await native.step(build())).disposition=='waiting_for_change'
            assert len(progress_prompts)==before_calls and len(jobs.list_jobs(include_disabled=True))==2
            assert tool({'operation':'list','item_id':row['item_id']})['items'][0]['state']=='active'
            raw='\n'.join(r.event.canonical_json() for r in store.journal.read())
            assert fresh not in raw and str(artifact) not in raw and 'MUST_NOT_BE_READ' not in raw
            keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
            (home/'inspection-expected.json').write_text(json.dumps({'parent':started['work_id'],'child':leaf[0],
                'owner':configured.subject,'fresh':fresh,'keys':{n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in keys}}))
            print('HERMES_ALIVE_CORE_WORK_HANDOFF_OK')
            return
        after=await native.step(build())
        assert after.disposition=='silence' and len(progress_prompts)==2,after.disposition
        assert 'core_completed_result_unverified' in progress_prompts[-1]
        assert 'task_success_proven' in progress_prompts[-1]
        if review_records:
            assert 'core_work_record_review' in progress_prompts[-1]
            assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' in progress_prompts[-1]
            assert 'bounded_historical_core_records' in progress_prompts[-1]
            assert 'independent_current_result_verification' in progress_prompts[-1]
        else:
            assert 'not result contents' in progress_prompts[-1]
            assert 'core_work_record_review' not in reader.commitments(
                subject=configured.subject,clearance=execution.kernel('events').Sensitivity.PRIVATE)[0].content
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
        if review_records:
            review=work_store.review_evidence(evidence[0].content['core_work'],subject=configured.subject)
            assert review['independent_current_result_verification'] is False
            assert review['execution_records']['status']=='core_execution_evidence'
            assert any(e['kind']=='recorded_tool_result' and e['tool_name']=='read_file'
                and 'INDEPENDENT_SYNTHETIC_ARTIFACT' in e['content'] for e in review['execution_records']['entries'])
            changed_view={**dict(evidence[0].content['core_work']),'record_review':{'fingerprint':'0'*64}}
            assert work_store.review_evidence(changed_view,subject=configured.subject) is None
        else:
            with patch('hermes_state.SessionDB',side_effect=AssertionError('legacy grant read Core bodies')):
                assert 'record_review' not in work_store.observation_state(started['work_id'],subject=configured.subject)
        # Actual authored Core-definition drift must also wake the same host,
        # without executing the broadened job or hiding the uncertainty.
        jobs.update_job(started['job_id'],{'enabled_toolsets':['terminal']})
        assert (await native.step(build())).disposition=='silence'
        assert len(progress_prompts)==3 and 'core_job_definition_changed' in progress_prompts[-1]
        jobs.update_job(started['job_id'],{'enabled_toolsets':['file','no_mcp']})
        if os.environ.get('ALIVE_WORK_HISTORY_TEST')=='1':
            # Controlled fixtures appended through Core's actual store, not
            # claimed to be additional worker calls. They push the real earlier
            # readback outside the default last-16 window.
            db=SessionDB()
            try:
                for index in range(20):
                    db.append_message(observed['session_id'],'assistant',f'SYNTHETIC_HISTORY_FIXTURE_{index:02d}')
                all_rows=db.get_messages(observed['session_id'],limit=64)
                assert 20<len(all_rows)<64
            finally:db.close()
            before_history=store.journal.last_sequence();job_count=len(jobs.list_jobs(include_disabled=True))
            newest=tool({'operation':'work_evidence','work_id':started['work_id']})
            assert not any('INDEPENDENT_SYNTHETIC_ARTIFACT' in e['content'] for e in newest['entries'])
            collected=[];cursor=0;reference=None;page_count=0
            while True:
                history=tool({'operation':'work_evidence','work_id':started['work_id'],
                    'after_message_id':cursor,**({'evidence_reference':reference} if reference else {})})
                assert history['status']=='core_execution_evidence',history
                reference=reference or history['evidence_reference']
                assert history['evidence_reference']==reference and not history['entire_execution_history_loaded']
                details=history['history_page'];assert details['scanned_rows']<=16
                assert not details['atomic_multi_page_snapshot']
                collected.extend(history['entries']);page_count+=1
                assert page_count<6
                if not details['has_more_active_rows']:
                    assert details['next_after_message_id'] is None
                    break
                assert details['next_after_message_id']>cursor
                cursor=details['next_after_message_id']
            expected_ids=[m['id'] for m in all_rows if m['role'] in ('tool','assistant')
                and (m.get('content') or m.get('tool_calls'))]
            assert page_count>=2 and [e['message_id'] for e in collected]==expected_ids
            assert len(set(expected_ids))==len(expected_ids)
            assert any('INDEPENDENT_SYNTHETIC_ARTIFACT' in e['content'] for e in collected)
            with patch('hermes_state.SessionDB',side_effect=AssertionError('invalid history selector opened Core')):
                for extra in ({'after_message_id':True},{'after_message_id':-1},
                        {'after_message_id':1},{'after_message_id':0,'message_id':witness['message_id']},
                        {'after_message_id':0,'part':'request'},{'after_message_id':0,'offset':1}):
                    rejected=tool({'operation':'work_evidence','work_id':started['work_id'],**extra})
                    assert 'error' in rejected and 'entries' not in rejected,rejected
            assert store.journal.last_sequence()==before_history
            assert len(jobs.list_jobs(include_disabled=True))==job_count
            assert not any('SYNTHETIC_HISTORY_FIXTURE_' in r.event.canonical_json() for r in store.journal.read())
            print('HERMES_ALIVE_CORE_WORK_HISTORY_PAGING_OK')
        assert (await native.step(build())).disposition=='silence'
        assert len(progress_prompts)==4 and 'core_completed_result_unverified' in progress_prompts[-1]
        assert len(list(store.journal.read(event_type='work.observed')))==3
        for observation in store.journal.read(event_type='work.observed'):
            assert 'INDEPENDENT_SYNTHETIC_ARTIFACT' not in observation.event.canonical_json()
        if review_records:
            # Same Core execution status, new actual Core record: the exact
            # window digest changes, so the existing Native loop reconsiders.
            db=SessionDB()
            try:db.append_message(observed['session_id'],'assistant','SYNTHETIC_UNVERIFIED_WORKER_CLAIM')
            finally:db.close()
            assert (await native.step(build())).disposition=='silence'
            assert len(progress_prompts)==5 and 'SYNTHETIC_UNVERIFIED_WORKER_CLAIM' in progress_prompts[-1]
            latest=list(store.journal.read(event_type='opportunity.synthesis_completed'))[-1].event
            result=store.vault.resolve_json(latest.payload['content']['content_id'],
                expected_subject=configured.subject,expected_purpose='opportunity.candidates',
                expected_sensitivity=execution.kernel('events').Sensitivity.PRIVATE)
            assert result['abstentions'][0]['reason']=='Untrusted worker claim needs independent verification.'
            assert latest.payload['raw_prompt_stored'] is False
            assert (await native.step(build())).disposition=='waiting_for_change'
            assert len(progress_prompts)==5 and len(list(store.journal.read(event_type='work.observed')))==4
            for observation in store.journal.read(event_type='work.observed'):
                assert 'SYNTHETIC_UNVERIFIED_WORKER_CLAIM' not in observation.event.canonical_json()
            assert tool({'operation':'list','item_id':row['item_id']})['items'][0]['state']=='active'
            assert len(jobs.list_jobs(include_disabled=True))==1 and artifact.read_text()==body
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
        if review_records:
            with closing(store.journal._connect()) as c:
                c.execute('UPDATE autonomy_policies_v1 SET enabled=1 WHERE subject=?',(configured.subject,))
            try:
                with patch('hermes_state.SessionDB',side_effect=AssertionError('tampered paused cache opened Core bodies')):
                    try:
                        execution.kernel('core_work_evidence').CoreWorkEvidence(work_store).for_review(
                            started['work_id'],subject=configured.subject,state=status)
                        raise AssertionError('tampered policy projection was trusted')
                    except ValueError:pass
            finally:
                with closing(store.journal._connect()) as c:
                    c.execute('UPDATE autonomy_policies_v1 SET enabled=0 WHERE subject=?',(configured.subject,))
        observations_before_pause=len(list(store.journal.read(event_type='work.observed')))
        calls_before_pause=len(progress_prompts)
        assert (await native.step(build())).disposition=='paused'
        assert len(progress_prompts)==calls_before_pause
        assert len(list(store.journal.read(event_type='work.observed')))==observations_before_pause
        with patch('hermes_state.SessionDB',side_effect=AssertionError('paused owner read Core bodies')):
            assert execution.kernel('core_work_evidence').CoreWorkEvidence(work_store).for_review(
                started['work_id'],subject=configured.subject,state=status) is None
        # Removing original evidence never reconstructs it from the description.
        text='持续跟进 SOURCE_ERASURE_ONLY，原文与整理稿必须区别。'
        erasure_tool=turn('source-erasure',text)
        erasure=erasure_tool({'operation':'record','task':'保存一条合成待办','evidence_span':text})
        erasure_row=erasure_tool({'operation':'list','item_id':erasure['item_id']})['items'][0]
        source_event=store.journal.get(erasure_row['source_event_id']).event
        intake=execution.kernel('followup_intake')
        try:
            intake._validated_source(store.journal,source_event.event_id,store.configuration().subject,
                datetime.fromisoformat(source_event.payload['retention_until']))
            raise AssertionError('expired original source admitted')
        except ValueError:pass
        ref=source_event.payload['content'];store.vault.erase_item(ref['content_id'])
        execution.kernel('agenda').AgendaProjection(store.journal).rebuild()
        erased=erasure_tool({'operation':'list','item_id':erasure['item_id']})['items'][0]
        assert erased['state']=='active' and not erased['original_source_available'] and 'original_owner_message' not in erased
        tool=erasure_tool  # The newly admitted Core turn retires earlier tool tickets.
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
            'original_request':original_request,
            'erased_item_id':erasure['item_id'],
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
        if os.environ.get('ALIVE_WORK_STOP_TEST'):
            expected=json.loads((home/'stop-expected.json').read_text())
            execution=importlib.import_module('alive_session_fixture.kernel_execution_bridge')
            store=execution.kernel('kernel_setup').KernelSetupStore(home/'plugin-data/hermes-alive/runtime/kernel')
            assert all(hashlib.sha256((store.root/n).read_bytes()).hexdigest()==v for n,v in expected['keys'].items())
            state=execution.kernel('core_work').CoreWorkStore(store).status(expected['work_id'],subject=expected['owner'])
            assert state['owner_stop_requested'] and state.get('core_execution_state') not in ('claimed','running')
            assert not Path(expected['artifact']).exists()
            from cron.jobs import list_jobs
            assert len(list_jobs(include_disabled=True))==1
            print('HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK')
            raise SystemExit(0)
        if os.environ.get('ALIVE_WORK_INSPECTION_TEST')=='1' or os.environ.get('ALIVE_WORK_INSPECTION_REVOKE_TEST')=='1' or os.environ.get('ALIVE_WORK_INSPECTION_STOP_TEST')=='1':
            expected=json.loads((home/'inspection-expected.json').read_text())
            execution=importlib.import_module('alive_session_fixture.kernel_execution_bridge')
            store=execution.kernel('kernel_setup').KernelSetupStore(home/'plugin-data/hermes-alive/runtime/kernel')
            assert all(hashlib.sha256((store.root/n).read_bytes()).hexdigest()==v for n,v in expected['keys'].items())
            work=execution.kernel('core_work').CoreWorkStore(store)
            inspection=execution.kernel('core_file_inspection').CoreFileInspection(store)
            if expected.get('stopped'):
                with patch('hermes_state.SessionDB',side_effect=AssertionError('stopped inspector opened Core records')):
                    result=inspection.snapshot(expected['parent'],subject=expected['owner'])
                assert result['work_id']==expected['child'] and result['state']['owner_stop_requested'] is True
                assert result['inspection_records'] is None
                from cron.jobs import list_jobs
                assert len(list_jobs(include_disabled=True))==2
                print('HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK')
                raise SystemExit(0)
            if expected.get('paused'):
                with patch('hermes_state.SessionDB',side_effect=AssertionError('cold paused inspection opened Core bodies')):
                    try:
                        inspection.snapshot(expected['parent'],subject=expected['owner'])
                        raise AssertionError('cold paused inspection was readable')
                    except ValueError:pass
                assert work.previous(inspection.work._read(expected['parent'],'requested',expected['owner'])['item_id'],subject=expected['owner'])['work_id']==expected['parent']
                from cron.jobs import list_jobs
                assert len(list_jobs(include_disabled=True))==2
                print('HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK')
                raise SystemExit(0)
            with patch('model_tools.handle_function_call',side_effect=AssertionError('cold inspection replayed a tool')):
                result=inspection.snapshot(expected['parent'],subject=expected['owner'])
            assert result['work_id']==expected['child']
            assert expected['fresh'] in json.dumps(result) and result['task_success_proven'] is False
            assert work.previous(work.status(expected['parent'],subject=expected['owner'])['item_id'],
                subject=expected['owner'])['work_id']==expected['parent']
            from cron.jobs import list_jobs
            assert len(list_jobs(include_disabled=True))==2
            print('HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK')
            raise SystemExit(0)
        expected=json.loads((home/'work-handoff-expected.json').read_text())
        execution=importlib.import_module('alive_session_fixture.kernel_execution_bridge')
        store=execution.kernel('kernel_setup').KernelSetupStore(home/'plugin-data/hermes-alive/runtime/kernel')
        assert all(hashlib.sha256((store.root/name).read_bytes()).hexdigest()==digest for name,digest in expected['keys'].items())
        status=execution.kernel('core_work').CoreWorkStore(store).status(expected['work_id'],subject=expected['owner'])
        assert status['core_execution_state']=='completed' and status['task_success_proven'] is False,status
        original=execution.kernel('followup_intake').item_source_view(store,status['item_id'],
            subject=expected['owner'],include_message=True)
        assert original['original_owner_message']==expected['original_request']
        recovered=execution.kernel('core_work_evidence').CoreWorkEvidence(
            execution.kernel('core_work').CoreWorkStore(store)).read(expected['work_id'],subject=expected['owner'])
        if os.environ.get('ALIVE_WORK_HISTORY_TEST')=='1':
            reader=execution.kernel('core_work_evidence').CoreWorkEvidence(execution.kernel('core_work').CoreWorkStore(store))
            history=reader.read(expected['work_id'],subject=expected['owner'],after_message_id=0)
            assert history['history_page']['has_more_active_rows']
            next_page=reader.read(expected['work_id'],subject=expected['owner'],
                reference=history['evidence_reference'],after_message_id=history['history_page']['next_after_message_id'])
            assert all(e['message_id']>history['history_page']['last_scanned_message_id'] for e in next_page['entries'])
            assert not history['entire_execution_history_loaded']
            recovered=history
        assert recovered['status']=='core_execution_evidence'
        assert any(e['kind']=='recorded_tool_result' and e['tool_name']=='read_file'
            and 'INDEPENDENT_SYNTHETIC_ARTIFACT' in e['content'] for e in recovered['entries'])
        definition=execution.kernel('core_work_evidence').CoreWorkEvidence(
            execution.kernel('core_work').CoreWorkStore(store)).read(expected['work_id'],subject=expected['owner'],part='request')
        assert definition['contains_exact_current_owner_message'] and definition['content_complete']
        projection=execution.kernel('agenda').AgendaProjection(store.journal)
        projection.rebuild()
        erased=projection.list_items(subject=expected['owner'],item_ids=(expected['erased_item_id'],),
            clearance=execution.kernel('events').Sensitivity.PRIVATE)
        assert len(erased)==1 and erased[0].state.value=='active'
        assert execution.kernel('followup_intake').item_source_view(store,expected['erased_item_id'],
            subject=expected['owner'],include_message=True)['original_source_available'] is False
        observation=execution.kernel('core_work').CoreWorkStore(store).current_observation(
            status['item_id'],subject=expected['owner'])
        if os.environ.get('ALIVE_WORK_REVIEW_TEST')=='1':
            # The persisted owner is paused. The old reviewed body remains in
            # Core, but no background reading resumes during cold recovery.
            with patch('hermes_state.SessionDB',side_effect=AssertionError('cold paused review read bodies')):
                assert execution.kernel('core_work_evidence').CoreWorkEvidence(
                    execution.kernel('core_work').CoreWorkStore(store)).for_review(
                        expected['work_id'],subject=expected['owner'],state=status) is None
            assert observation is None
        else:
            assert observation is not None and observation[1]==status
        print('HERMES_ALIVE_CORE_WORK_COLD_ASSOCIATION_OK')
    else:
        asyncio.run(test(Path(os.environ['HERMES_HOME'])))
