"""Actual installed Native -> first Core job without a fresh main turn.

Synthetic owner/provider, actual Core dispatcher, jobs, agent, file effects and
cold metadata and automatic startup wake. This does not certify real-model
intent, external-channel daemon operation or generic completion.
"""
import asyncio,hashlib,importlib,json,os,shutil,subprocess,sys,tempfile,threading
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

if __name__=='__main__' and os.environ.get('ALIVE_AUTOWORK_CHILD')!='1':
    with tempfile.TemporaryDirectory(prefix='alive-core-autonomous-') as root:
        env={**os.environ,'HOME':root,'HERMES_HOME':str(Path(root)/'profile'),
            'ALIVE_AUTOWORK_CHILD':'1','PYTHONDONTWRITEBYTECODE':'1'}
        try:
            for mode in ('execute','wait','revoked','erased','off','restart'):
                case={**env,'HERMES_HOME':str(Path(root)/mode),'ALIVE_AUTOWORK_CASE':mode}
                result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env=case,
                    capture_output=True,text=True,timeout=300)
                assert result.returncode==0,result.stdout+'\n'+result.stderr
                if mode=='restart':
                    resumed=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env={**case,'ALIVE_AUTOWORK_RESUME':'1'},
                        capture_output=True,text=True,timeout=300)
                    assert resumed.returncode==0,resumed.stdout+'\n'+resumed.stderr
                cold=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env={**case,'ALIVE_AUTOWORK_COLD':'1'},
                    capture_output=True,text=True,timeout=60)
                assert cold.returncode==0,cold.stdout+'\n'+cold.stderr
                stopped=subprocess.run([sys.executable,'-B','-m','hermes_cli.main','gateway','stop'],env=case,
                    capture_output=True,text=True,timeout=30)
                assert stopped.returncode==0
        finally:
            for mode in ('execute','wait','revoked','erased','off','restart'):
                subprocess.run([sys.executable,'-B','-m','hermes_cli.main','gateway','stop'],
                    env={**env,'HERMES_HOME':str(Path(root)/mode)},capture_output=True,text=True,timeout=30)
    print('HERMES_ALIVE_CORE_AUTONOMOUS_WORK_OK')
    raise SystemExit(0)

import run_core_session_routing as core
from run_core_guided_setup import cli


async def exercise(home):
    mode=os.environ['ALIVE_AUTOWORK_CASE'];resuming=os.environ.get('ALIVE_AUTOWORK_RESUME')=='1';home.mkdir(exist_ok=True)
    if not resuming:shutil.copytree(core.repo,home/'plugins/hermes-alive')
    work_requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.send_error(503)
        def do_POST(self):
            data=json.loads(self.rfile.read(int(self.headers.get('content-length','0'))))
            actual=any('Perform this ongoing owner assignment' in str(m.get('content')) for m in data['messages'])
            message={'role':'assistant','content':'Auxiliary probe.'};finish='stop'
            if actual:
                work_requests.append(data)
                assert {'write_file','read_file'}<={t.get('function',t)['name'] for t in data.get('tools',[])}
                if any(m.get('role')=='tool' and m.get('tool_call_id')=='autonomous-read' for m in data['messages']):
                    message={'role':'assistant','content':'Actual write and readback recorded; no messages or completion claimed.'}
                else:
                    read=any(m.get('role')=='tool' for m in data['messages'])
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'autonomous-read' if read else 'autonomous-write',
                        'type':'function','function':{'name':'read_file' if read else 'write_file',
                            'arguments':json.dumps({'path':str(artifact),**({} if read else {'content':body})})}}]}
                    finish='tool_calls'
            if data.get('stream'):
                delta={k:v for k,v in message.items() if k!='role'}
                if 'tool_calls' in delta:delta['tool_calls'][0]['index']=0
                chunk={'id':'synthetic-autonomous','object':'chat.completion.chunk','created':0,'model':'configured-primary',
                    'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
                payload=('data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n').encode();kind='text/event-stream'
            else:
                payload=json.dumps({'id':'synthetic-autonomous','object':'chat.completion','created':0,'model':'configured-primary',
                    'choices':[{'index':0,'message':message,'finish_reason':finish}],
                    'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}}).encode();kind='application/json'
            self.send_response(200);self.send_header('content-type',kind);self.send_header('content-length',str(len(payload)))
            self.end_headers();self.wfile.write(payload)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    artifact=home/'autonomous-result.txt';body='ACTUAL_AUTONOMOUS_CORE_RESULT\n'
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'custom:owner','default':'configured-primary'},
        'custom_providers':[{'name':'owner','model':'configured-primary','base_url':f'http://127.0.0.1:{server.server_port}/v1',
            'key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}]}),encoding='utf-8')
    (home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n',encoding='utf-8')
    if not resuming:
        rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
            '--confirm-followup-management','--confirm-core-background-work','--automatic-core-toolset','file',
            *(() if mode=='off' else ('--confirm-autonomous-core-work',)))
        assert rc==0 and staged['confirmation_summary']['autonomous_initial_core_work']==(mode!='off')
        assert cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None;variables=None
    try:
        from hermes_cli.plugins import get_plugin_command_handler
        from agent.turn_context import _collect_pre_llm_call_context
        from cron import jobs
        from cron.scheduler import tick
        import model_tools
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];assert loaded.enabled and not loaded.error
        binding=loaded.module._gateway_host_binding
        execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
        class Adapter(core.Adapter):
            async def send(self,*args,**kwargs):raise AssertionError('autonomous work cannot send')
        adapter=Adapter(core.Platform.TELEGRAM);runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter})
        adapter.gateway_runner=runner;await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-10074016',
            user_id='synthetic-autonomous-owner',message_id='autonomous-setup')
        entry=runner.session_store.get_or_create_session(source);handler=get_plugin_command_handler('alive')
        async def command(text):return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=text)
        if resuming:
            started=await loaded.module.kernel_gateway_startup()
            assert started['status']=='started' and binding.native.host.execute is True
        else:
            assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
            assert '已启用' in await command('enable')
        if not resuming:
            binding.arguments['stop'].set();await binding.task
        store=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge').setup_store(binding)
        original=(('登记持续整理这项合成工作；从下一次自然唤醒开始，' if mode!='wait'
            else '仅登记这项合成工作，必须等我以后明确说执行，不能自行开工；')
            +f'在本地文件 {artifact} 写入 {body.strip()} 和一个换行并读回结果，不发消息。')
        if not resuming:
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id='register-autonomous',turn_id='register-autonomous',
                original_user_message=original,messages=[{'role':'user','content':original}],conversation_history=[])
            saved=json.loads(model_tools.handle_function_call('alive_agenda',{'operation':'record',
                'task':'Write '+body.strip()+' plus newline into '+str(artifact)+' and read it back.',
                'constraint':'No messages. '+original,'evidence_span':original},task_id='register-autonomous',
                session_id=entry.session_id,turn_id='register-autonomous',tool_call_id='register-autonomous-call',enabled_tools=['alive_agenda']))
            assert saved['status']=='recorded_under_owner_intake_grant' and not jobs.list_jobs(include_disabled=True)
            core.clear_session_vars(variables);variables=None
            with binding._agenda.lock:
                binding._agenda.turns.clear();binding._agenda.latest_turn.clear()
        else:
            saved=json.loads((home/'autonomous-restart-source.json').read_text(encoding='utf-8'))
            assert entry.session_key==saved['session_key'] and entry.session_id==saved['session_id']
            assert store.configuration().event_id==saved['configuration']
            assert store.activation()['activation_event_id']==saved['activation']
            assert all(hashlib.sha256((store.root/n).read_bytes()).hexdigest()==v for n,v in saved['keys'].items())
            assert not binding._agenda.turns and not jobs.list_jobs(include_disabled=True)
        if mode=='restart' and not resuming:
            keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
            saved.update(session_key=entry.session_key,session_id=entry.session_id,
                configuration=store.configuration().event_id,activation=store.activation()['activation_event_id'],
                keys={n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in keys})
            (home/'autonomous-restart-source.json').write_text(json.dumps(saved),encoding='utf-8')
            assert not artifact.exists() and not jobs.list_jobs(include_disabled=True)
            return
        if mode=='execute':
            # Eight projection-only rows cannot grant authority or starve the
            # ninth authentic item. They have no source proposal/history.
            from contextlib import closing
            with closing(store.journal._connect()) as c:
                template=dict(c.execute('SELECT * FROM agenda_items_v1 WHERE item_id=?',(saved['item_id'],)).fetchone())
                for index in range(8):
                    fake={**template,'proposal_event_id':'unbacked-proposal-'+str(index),'item_id':'projection-only-'+str(index),'created_at':'2000-01-01T00:00:00+00:00'}
                    columns=list(fake)
                    c.execute('INSERT INTO agenda_items_v1 ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',
                        tuple(fake[k] for k in columns))
        counts={'start':0,'cognition':0}
        class Caller:
            pending=()
            def __init__(self,*,cycle,read_binding):self.calls=0;self.read_binding=read_binding
            async def reap_pending(self,**kw):return {'closed':0,'remaining':0}
            async def __call__(self,**kw):
                self.read_binding();self.calls+=1
                if kw['task']=='alive_core_autonomous_work':
                    counts['start']+=1;supplied=json.loads(kw['messages'][-1]['content'])
                    assert supplied['item']['original_owner_request']==original
                    answer={'decision':'wait' if mode=='wait' else 'execute','toolsets':[] if mode=='wait' else ['file'],
                        'step':'Write the exact requested marker and read it back.' if mode!='wait' else None,
                        'reason':'Original owner authorizes the later wake.' if mode!='wait' else 'Original owner requires a future instruction.',
                        'reconsider_after_seconds':3600 if mode=='wait' else None}
                else:
                    assert kw['task']=='alive_opportunity_candidates',kw['task'];counts['cognition']+=1
                    if mode=='wait':assert 'autonomous_work_wait' in str(kw['messages'])
                    answer={'candidates':[],'abstentions':[]}
                return SimpleNamespace(model='synthetic-model',choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(answer)))])
        binding.native.caller_factory=lambda **kw:Caller(**kw)
        if mode=='execute':
            auto=execution.kernel('core_autonomous_work').CoreAutonomousWork(store);cfg=store.configuration()
            await auto.run(cfg,call=Caller(cycle=None,read_binding=lambda:None),
                validate=lambda:auto.authority(cfg),operation_id='synthetic-projection-page')
            assert counts['start']==0 and not jobs.list_jobs(include_disabled=True)
            assert saved['item_id'] in [row['item_id'] for row in auto.scan(cfg)[1]]
        if mode=='erased':
            proposal=store.journal.get('agenda.proposal:'+saved['item_id']).event
            intake=store.journal.get(proposal.payload['source_event_ids'][0]).event
            ref=execution.kernel('followup_intake')._source_reference(intake,
                __import__('datetime').datetime.fromisoformat(intake.payload['retention_until']))
            store.vault.erase_item(ref.content_id)
        if resuming:
            # Leave the actual startup loop running. No manual Native step and
            # no shortened interval: its first automatic wake starts the work.
            assert binding.arguments['interval_seconds']==600 and not binding.task.done()
            deadline=asyncio.get_running_loop().time()+60
            while binding.native.last_call_count<2:
                assert not binding.task.done() and asyncio.get_running_loop().time()<deadline
                await asyncio.sleep(.05)
            binding.arguments['stop'].set()
            stopped=await binding.task
            assert stopped['completed_cycles']>=1 and stopped['exit_reason']=='stopped'
        else:
            first=await binding.native.step(binding.arguments['build_parameters']())
            assert first.disposition in ('silence','evidence_changed')
        work=execution.kernel('core_work').CoreWorkStore(store)
        if mode in ('execute','revoked','restart'):
            state=work.previous(saved['item_id'],subject=store.configuration().subject);assert state is not None
            assert len(jobs.list_jobs(include_disabled=True))==1
            request=work._read(state['work_id'],'requested',store.configuration().subject)
            assert request['authority']=='guided_autonomous_initial_work' and request['current_owner_turn'] is False
            assert 'turn_evidence' not in request and request['historical_owner_request_retained_by_core'] is True
            job=jobs.get_job(state['job_id']);retained=json.loads(job['prompt'].rsplit('\n',1)[1])
            assert retained['retained_original_owner_request']==original and 'current_owner_message' not in retained
            assert job['enabled_toolsets']==['file','no_mcp'] and job['deliver']=='local'
            if mode=='revoked':
                scope=binding._continuity.router.capture_target(session_key=entry.session_key,
                    user_id=source.user_id,platform='telegram')
                execution.pause(binding,scope)
                # Derived cache cannot override the signed pause in the actual pre-tool guard.
                from contextlib import closing
                with closing(store.journal._connect()) as c:
                    c.execute('UPDATE autonomy_policies_v1 SET enabled=1 WHERE subject=?',(store.configuration().subject,))
            deadline=asyncio.get_running_loop().time()+120
            while state.get('core_execution_state') not in ('completed','failed','unknown'):
                assert asyncio.get_running_loop().time()<deadline
                if state.get('core_execution_state') not in ('claimed','running'):
                    await asyncio.to_thread(tick,verbose=False,sync=True,headless=False)
                await asyncio.sleep(.1);state=work.status(state['work_id'],subject=store.configuration().subject)
            assert state['core_execution_state']=='completed'
            assert not artifact.exists() if mode=='revoked' else artifact.read_text(encoding='utf-8')==body
            assert len(work_requests)==3 and state['task_success_proven'] is False
        else:
            state=None;assert not jobs.list_jobs(include_disabled=True) and not artifact.exists()
            if mode=='wait':
                waiting=execution.kernel('core_autonomous_work').CoreAutonomousWork(store).wait_evidence(saved['item_id'],store.configuration())
                assert waiting['work_submitted'] is False and 'future instruction' in waiting['reason']
        if mode=='revoked':
            with closing(store.journal._connect()) as c:
                c.execute('UPDATE autonomy_policies_v1 SET enabled=0 WHERE subject=?',(store.configuration().subject,))
        await binding.native.step(binding.arguments['build_parameters']())
        assert counts['start']==(0 if mode in ('erased','off') else 1) and len(jobs.list_jobs(include_disabled=True))==(1 if mode in ('execute','revoked','restart') else 0)
        from contextlib import closing
        with closing(store.journal._connect()) as c:
            assert c.execute('SELECT state FROM agenda_items_v1 WHERE item_id=?',(saved['item_id'],)).fetchone()[0]=='active'
        raw='\n'.join(r.event.canonical_json() for r in store.journal.read())
        assert original not in raw and str(artifact) not in raw and body.strip() not in raw
        keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
        (home/'autonomous-expected.json').write_text(json.dumps({'work_id':state['work_id'] if state else None,
            'owner':store.configuration().subject,'artifact':str(artifact),'body':body,'revoked':mode=='revoked',
            'keys':{n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in keys}}),encoding='utf-8')
    finally:
        if variables:core.clear_session_vars(variables)
        if manager:manager.unload()
        core.reset_hermes_home_override(token)
        server.shutdown();server.server_close();thread.join(timeout=2)
        from hermes_state_registry import close_all_under
        close_all_under(home)


if __name__=='__main__':
    if os.environ.get('ALIVE_AUTOWORK_COLD')=='1':
        home=Path(os.environ['HERMES_HOME']);expected=json.loads((home/'autonomous-expected.json').read_text(encoding='utf-8'))
        execution=importlib.import_module('alive_session_fixture.kernel_execution_bridge')
        store=execution.kernel('kernel_setup').KernelSetupStore(home/'plugin-data/hermes-alive/runtime/kernel')
        assert all(hashlib.sha256((store.root/n).read_bytes()).hexdigest()==v for n,v in expected['keys'].items())
        from cron.jobs import list_jobs
        if expected['work_id']:
            state=execution.kernel('core_work').CoreWorkStore(store).status(expected['work_id'],subject=expected['owner'])
            assert state['core_execution_state']=='completed' and state['historical_owner_request_retained_by_core']
            assert not Path(expected['artifact']).exists() if expected['revoked'] else Path(expected['artifact']).read_text(encoding='utf-8')==expected['body']
        assert len(list_jobs(include_disabled=True))==(1 if expected['work_id'] else 0)
    else:asyncio.run(exercise(Path(os.environ['HERMES_HOME'])))
