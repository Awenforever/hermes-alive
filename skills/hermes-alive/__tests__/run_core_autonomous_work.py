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
        modes=os.environ.get('ALIVE_AUTOWORK_CASES','execute,wait,revoked,erased,off,restart').split(',')
        assert set(modes)<=set(('execute','wait','revoked','erased','off','restart','outcome-complete','outcome-partial','outcome-forged','outcome-revoked','outcome-recover','outcome-manual-long','outcome-wrong-result','outcome-window','outcome-malformed','outcome-attention','attention-snooze','attention-resume','attention-cancel','attention-reopen','revision-before','revision-after','revision-legacy','revision-deadline','revision-manual','revision-recover','project-pinned','project-manual','project-missing','project-replaced','project-restart'))
        try:
            for mode in modes:
                case={**env,'HERMES_HOME':str(Path(root)/mode),'ALIVE_AUTOWORK_CASE':mode}
                result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env=case,
                    capture_output=True,text=True,timeout=300)
                assert result.returncode==0,mode+'\n'+result.stdout+'\n'+result.stderr
                if mode in ('restart','project-restart'):
                    resumed=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env={**case,'ALIVE_AUTOWORK_RESUME':'1'},
                        capture_output=True,text=True,timeout=300)
                    assert resumed.returncode==0,resumed.stdout+'\n'+resumed.stderr
                cold=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env={**case,'ALIVE_AUTOWORK_COLD':'1'},
                    capture_output=True,text=True,timeout=60)
                assert cold.returncode==0,mode+'\n'+cold.stdout+'\n'+cold.stderr
                stopped=subprocess.run([sys.executable,'-B','-m','hermes_cli.main','gateway','stop'],env=case,
                    capture_output=True,text=True,timeout=30)
                assert stopped.returncode==0
        finally:
            for mode in modes:
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
            actual=any(any(prefix in str(m.get('content')) for prefix in ('Perform this ongoing owner assignment','Perform the following ongoing owner-assigned work.')) for m in data['messages'])
            message={'role':'assistant','content':'Auxiliary probe.'};finish='stop'
            if actual:
                work_requests.append(data)
                if mode.startswith('project-') and len(work_requests)==1:
                    rendered=json.dumps(data['messages'],ensure_ascii=False)
                    assert 'PUBLIC_PROJECT_A_RULE_SENTINEL_228' in rendered, 'Core did not load project A rules'
                    assert 'PUBLIC_PROJECT_B_RULE_MUST_NOT_APPLY' not in rendered, 'another project supplied Core rules'
                    if mode=='project-replaced':
                        assert project.resolve().parent==home.resolve() and not moved.exists()
                        project.rename(moved);project.mkdir()
                        (project/'AGENTS.md').write_text('PUBLIC_PROJECT_B_RULE_MUST_NOT_APPLY',encoding='utf-8')
                assert {'write_file','read_file'}<={t.get('function',t)['name'] for t in data.get('tools',[])}
                if any(m.get('role')=='tool' and m.get('tool_call_id')=='autonomous-read' for m in data['messages']):
                    message={'role':'assistant','content':'Actual write and readback recorded; no messages or completion claimed.'}
                else:
                    read=any(m.get('role')=='tool' and m.get('tool_call_id')=='autonomous-write' for m in data['messages'])
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'autonomous-read' if read else 'autonomous-write',
                        'type':'function','function':{'name':'read_file' if read else 'write_file',
                            'arguments':json.dumps({'path':'relative-result.txt' if mode.startswith('project-') else str(artifact),**({} if read else {'content':actual_body})})}}]}
                    finish='tool_calls'
            if actual and mode=='outcome-window' and not any(m.get('role')=='tool' for m in data['messages']):
                message={'role':'assistant','content':None,'tool_calls':[{'id':'autonomous-preface','type':'function',
                    'function':{'name':'read_file','arguments':json.dumps({'path':str(preface)})}}]};finish='tool_calls'
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
    project=home/'project-a';other=home/'project-b';moved=home/'project-a-retired'
    if mode.startswith('project-'):
        for directory,marker in ((project,'PUBLIC_PROJECT_A_RULE_SENTINEL_228'),(other,'PUBLIC_PROJECT_B_RULE_MUST_NOT_APPLY')):
            directory.mkdir(exist_ok=True)
            (directory/'AGENTS.md').write_text('# Project instructions\n'+marker+'\nKeep the synthetic task inside this project.\n',encoding='utf-8')
        artifact=project/'relative-result.txt'
    actual_body='ACTUAL_WRONG_RESULT\n' if mode=='outcome-wrong-result' else body
    preface=home/'public-preface.txt'
    if mode=='outcome-window':preface.write_text('\n'.join(str(i)+': public background '+'x'*70 for i in range(200)),encoding='utf-8')
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'custom:owner','default':'configured-primary'},
        'custom_providers':[{'name':'owner','model':'configured-primary','base_url':f'http://127.0.0.1:{server.server_port}/v1',
            'key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}]}),encoding='utf-8')
    (home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n',encoding='utf-8')
    if not resuming:
        rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention',
            '--confirm-followup-management','--confirm-core-background-work','--automatic-core-toolset','file',
            *(() if mode=='off' else ('--confirm-autonomous-core-work',)),
            *(('--confirm-followup-revisions',) if mode.startswith('revision-') and mode!='revision-legacy' else ()),
            *(('--confirm-core-work-outcomes','--confirm-core-work-result-review') if mode.startswith('outcome-') else ()))
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
        if mode.startswith('project-'):original='登记并持续跟进当前项目：把 '+body.strip()+' 加换行写入 relative-result.txt，并读回核对。允许后续唤醒在 file 范围内自主处理；本轮仅登记，不动文件，不发消息、不重试。'
        if mode=='outcome-window':original+=f'执行时允许先读取 {preface} 作为背景，无需输出其内容；最终验收仍仅以目标文件写入并读回一致为准。'
        if not resuming:
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            if mode.startswith('project-'):
                from agent.runtime_cwd import set_session_cwd
                from tools.terminal_tool import record_session_cwd
                set_session_cwd(str(other))
                record_session_cwd('register-autonomous',str(project))
            _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id='register-autonomous',turn_id='register-autonomous',
                original_user_message=original,messages=[{'role':'user','content':original}],conversation_history=[])
            saved=json.loads(model_tools.handle_function_call('alive_agenda',{'operation':'record',
                'task':'Write '+body.strip()+' plus newline into '+('relative-result.txt' if mode.startswith('project-') else str(artifact))+' and read it back.',
                'constraint':'No messages. '+original,'evidence_span':original},task_id='register-autonomous',
                session_id=entry.session_id,turn_id='register-autonomous',tool_call_id='register-autonomous-call',enabled_tools=['alive_agenda']))
            assert saved['status']=='recorded_under_owner_intake_grant' and not jobs.list_jobs(include_disabled=True)
            if mode.startswith('project-'):
                view=execution.kernel('followup_intake').item_source_view(store,saved['item_id'],subject=store.configuration().subject,include_message=True)
                assert view['core_project_context']['source']=='core_task'
                assert view['core_project_context']['declared_cwd']==str(project)
                record_session_cwd('register-autonomous',str(other))
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
        original_artifact=artifact;revision_messages=[]
        async def amend(patch,message):
            nonlocal variables
            current=json.loads(await command('agenda list'))['items'][0]
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            name='revision-'+str(len(revision_messages));revision_messages.append(message)
            _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id=name,turn_id=name,
                original_user_message=message,messages=[{'role':'user','content':message}],conversation_history=[])
            args={'operation':'revise','item_id':saved['item_id'],'item_version':current['item_version'],
                'evidence_span':message,**patch}
            def apply(args):
                return json.loads(model_tools.handle_function_call('alive_agenda',args,task_id=name,
                    session_id=entry.session_id,turn_id=name,tool_call_id=name+'-call',enabled_tools=['alive_agenda']))
            if mode=='revision-recover':
                from unittest.mock import patch
                projection=execution.kernel('agenda').AgendaProjection
                project=projection.project_new
                def interrupted(obj,*a,**kw):
                    if list(store.journal.read(event_type='agenda.revised')):
                        raise RuntimeError('synthetic crash after durable amendment before projection')
                    return project(obj,*a,**kw)
                with patch.object(projection,'project_new',interrupted):result=apply(args)
                assert 'error' in result and len(list(store.journal.read(event_type='agenda.revised')))==1,result
                from contextlib import closing
                with closing(store.journal._connect()) as c:
                    assert c.execute('SELECT COUNT(*) FROM agenda_transitions_v1 WHERE item_id=?',(saved['item_id'],)).fetchone()[0]==1
                core.clear_session_vars(variables);variables=None
                return result
            result=apply(args)
            if mode=='revision-legacy':
                assert result.get('error')=='guided_followup_revision_setup_required',result
                assert not list(store.journal.read(event_type='agenda.revised'))
            else:
                assert result.get('status')=='revised_under_owner_management_grant',result
                assert result['item_id']==saved['item_id'] and result['item_version']!=current['item_version']
                assert result['original_owner_message']==original
                assert [a['message'] for a in result['owner_amendments']]==revision_messages
                assert not result['replacement_job_created'] and not result['old_execution_cancellation_proven']
                assert result['details']['constraint']==current['details']['constraint']
                count=len(list(store.journal.read(event_type='agenda.revised')))
                assert 'error' in apply(args),'stale old version cannot apply another amendment'
                assert len(list(store.journal.read(event_type='agenda.revised')))==count
            core.clear_session_vars(variables);variables=None
            return result
        if mode in ('revision-before','revision-legacy'):
            new_artifact=home/'revised-result.txt';new_body='ACTUAL_REVISED_RESULT\n'
            result=await amend({'task':'Write '+new_body.strip()+' plus newline into '+str(new_artifact)+' and read it back.'},
                '修改这项任务：之后改为写入 '+str(new_artifact)+'，内容改为 '+new_body.strip()+' 加换行，并读回；其他要求保持不变。')
            if mode=='revision-before':artifact=new_artifact;actual_body=new_body
        if mode=='revision-deadline':
            from datetime import datetime,timedelta,timezone
            due=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
            updated=await amend({'due_at':due},'这项任务截止时间改为 '+due+'，其他要求不变。')
            assert updated['due_at']==due
            cleared=await amend({'due_at':None},'这项任务取消截止时间，其他要求不变。')
            assert cleared['due_at'] is None and cleared['details']==updated['details']
        if mode in ('restart','project-restart') and not resuming:
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
        manual=None
        if mode in ('outcome-manual-long','revision-manual','project-manual'):
            current=json.loads(await command('agenda list'))['items'][0]
            if mode=='project-manual':
                from tools.terminal_tool import record_session_cwd
                record_session_cwd('manual-long',str(other))
            manual='现在执行这个已登记的文件任务。'+(('这是公开合成附录，不改变任务目标。'*240)+'即使文件已正确写入并读回，也不要自动结项，等我另外确认。' if mode=='outcome-manual-long' else '请遵守原任务约束。')
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id='manual-long',turn_id='manual-long',
                original_user_message=manual,messages=[{'role':'user','content':manual}],conversation_history=[])
            submitted=json.loads(model_tools.handle_function_call('alive_agenda',{'operation':'work',
                'item_id':saved['item_id'],'item_version':current['item_version'],'toolsets':['file'],
                'evidence_span':'现在执行这个已登记的文件任务。'},task_id='manual-long',
                session_id=entry.session_id,turn_id='manual-long',tool_call_id='manual-long-call',enabled_tools=['alive_agenda']))
            core.clear_session_vars(variables);variables=None
            assert submitted.get('work_id') and len(jobs.list_jobs(include_disabled=True))==1,submitted
        counts={'start':0,'cognition':0,'outcome':0}
        class Caller:
            pending=()
            def __init__(self,*,cycle,read_binding):self.calls=0;self.read_binding=read_binding
            async def reap_pending(self,**kw):return {'closed':0,'remaining':0}
            async def __call__(self,**kw):
                self.read_binding();self.calls+=1
                if kw['task']=='alive_core_autonomous_work':
                    counts['start']+=1;supplied=json.loads(kw['messages'][-1]['content'])
                    assert supplied['item']['original_owner_request']==original
                    if mode.startswith('project-'):
                        assert supplied['item']['core_project_context']['declared_cwd']==str(project)
                        if mode=='project-missing':
                            assert project.resolve().parent==home.resolve() and not moved.exists()
                            project.rename(moved)
                    if mode in ('revision-before','revision-deadline'):
                        assert [a['message'] for a in supplied['item']['owner_amendments']]==revision_messages
                    answer={'decision':'wait' if mode=='wait' else 'execute','toolsets':[] if mode=='wait' else ['file'],
                        'step':'Write the exact requested marker and read it back.' if mode!='wait' else None,
                        'reason':'Original owner authorizes the later wake.' if mode!='wait' else 'Original owner requires a future instruction.',
                        'reconsider_after_seconds':3600 if mode=='wait' else None}
                elif kw['task']=='alive_core_work_outcome':
                    counts['outcome']+=1;supplied=json.loads(kw['messages'][-1]['content'])
                    assert supplied['item']['original_owner_request']==original
                    if mode in ('revision-before','revision-deadline'):
                        assert [a['message'] for a in supplied['item']['owner_amendments']]==revision_messages
                    refs=[v['evidence_id'] for v in supplied['evidence']
                        if v.get('tool_name')=='read_file' and actual_body.strip() in v.get('content','')]
                    assert refs,'actual complete readback evidence required'
                    if os.environ.get('ALIVE_OUTCOME_CAPTURE_DIR'):
                        capture=Path(os.environ['ALIVE_OUTCOME_CAPTURE_DIR'])/('source-'+mode+'.json')
                        capture.write_text(json.dumps({'task':kw['task'],'messages':kw['messages']},ensure_ascii=False),encoding='utf-8')
                    if manual is not None:
                        assert supplied['owner_work_instruction']['complete'] and supplied['owner_work_instruction']['message']==manual
                        assert supplied['owner_work_instruction']['kind']=='current_owner_message'
                    answer={'outcome':'partial' if mode in ('outcome-partial','outcome-wrong-result') else 'achieved',
                        'agenda_action':'keep_active' if mode in ('outcome-partial','outcome-manual-long','outcome-wrong-result') else 'complete',
                        'support_refs':['invented'] if mode=='outcome-forged' else refs,
                        'reason':'Actual readback records support this bounded assessment.',
                        'next_step':'Await the owner decision.' if mode in ('outcome-partial','outcome-manual-long','outcome-wrong-result') else None}
                    answer['benign_additional_field']='future annotation, not an action'
                    if mode=='outcome-malformed':answer='not an outcome object'
                    if mode=='outcome-revoked':
                        scope=binding._continuity.router.capture_target(session_key=entry.session_key,
                            user_id=source.user_id,platform='telegram')
                        execution.pause(binding,scope)
                else:
                    assert kw['task']=='alive_opportunity_candidates' ,kw['task'];counts['cognition']+=1
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
        if mode in ('execute','revoked','restart','attention-snooze','attention-resume','attention-cancel','attention-reopen','revision-before','revision-after','revision-legacy','revision-deadline','revision-manual','revision-recover','project-pinned','project-manual','project-replaced','project-restart') or mode.startswith('outcome-'):
            state=work.previous(saved['item_id'],subject=store.configuration().subject);assert state is not None
            assert len(jobs.list_jobs(include_disabled=True))==1
            request=work._read(state['work_id'],'requested',store.configuration().subject)
            if manual is None:
                assert request['authority']=='guided_autonomous_initial_work' and request['current_owner_turn'] is False
                assert 'turn_evidence' not in request and request['historical_owner_request_retained_by_core'] is True
            else:
                assert request['authority']=='user_delegated' and request['turn_evidence']
                assert request['exact_current_work_message_retained_by_core'] is True
            job=jobs.get_job(state['job_id']);retained=json.loads(job['prompt'].rsplit('\n',1)[1])
            if mode.startswith('project-'):
                assert job['workdir']==str(project.resolve())
                assert state['project_context_binding']['status']=='available'
            if manual is None:
                assert retained['retained_original_owner_request']==original and 'current_owner_message' not in retained
                assert retained['work_turn_context']['kind']=='later_background_execution'
                assert retained['work_turn_context']['original_intake_turn_is_current'] is False
            else:
                assert retained['current_owner_message']==manual
                if mode=='outcome-manual-long':assert len(job['prompt'])>4096
            assert job['enabled_toolsets']==['file','no_mcp'] and job['deliver']=='local'
            if mode=='revision-before' and os.environ.get('ALIVE_REVISION_FORGED_TEST')=='1':
                from dataclasses import replace
                from contextlib import closing
                valid=list(store.journal.read(event_type='agenda.revised'))[-1].event
                # Copying a real receipt under another identity is not a fresh
                # owner's amendment, even with otherwise well-formed metadata.
                forged=replace(valid,event_id='forged-owner-amendment-with-copied-signature')
                store.journal.append(forged)
                projection=execution.kernel('agenda').AgendaProjection(store.journal)
                projection.project_new()
                with closing(store.journal._connect()) as c:
                    rejected=c.execute('SELECT outcome FROM agenda_decisions_v1 WHERE event_id=?',
                        (forged.event_id,)).fetchone()
                assert rejected[0]=='rejected'
                assert not work.status(state['work_id'],subject=store.configuration().subject).get('later_owner_amendment')
            if mode in ('revision-after','revision-manual','revision-recover'):
                await amend({'task':'Write NEW_REVISION_ONLY to '+str(home/'new-revision-target.txt')},
                    '原来的目标不再适用；这项任务改为写 NEW_REVISION_ONLY 到 '+str(home/'new-revision-target.txt')+'，其他要求不变。')
                assert work.status(state['work_id'],subject=store.configuration().subject)['later_owner_amendment']
            if mode.startswith('attention-') or mode=='outcome-attention':
                from datetime import datetime,timedelta,timezone
                # A real fresh owner turn changes attention, not execution scope.
                actions={'attention-snooze':('snooze',),'attention-resume':('snooze','resume'),
                    'attention-cancel':('cancel',),'attention-reopen':('cancel','resume'),
                    'outcome-attention':('snooze','resume')}
                for action in actions[mode]:
                    listed=json.loads(await command('agenda list'))['items'][0]
                    message=('明天再来跟我说这件事，已经授权的工作继续进行。' if action=='snooze'
                             else '取消这件事。' if action=='cancel' else '重新打开这件事，不要重新执行旧工作。' if mode=='attention-reopen'
                             else '恢复这件事的关注，工作内容和权限保持不变。')
                    variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                        session_key=entry.session_key,session_id=entry.session_id)
                    _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                        platform='telegram',_user_id=source.user_id),effective_task_id=action,turn_id=action,
                        original_user_message=message,messages=[{'role':'user','content':message}],conversation_history=[])
                    change={'operation':action,'item_id':saved['item_id'],'item_version':listed['item_version'],
                            'evidence_span':message}
                    if action=='snooze':change['available_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
                    changed=json.loads(model_tools.handle_function_call('alive_agenda',change,task_id=action,
                        session_id=entry.session_id,turn_id=action,tool_call_id=action+'-call',enabled_tools=['alive_agenda']))
                    core.clear_session_vars(variables);variables=None
                    assert changed.get('state')==('snoozed' if action=='snooze' else 'dismissed' if action=='cancel' else 'active'),changed
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
            assert not artifact.exists() if mode in ('revoked','attention-cancel','attention-reopen','revision-after','revision-manual','revision-recover','project-replaced') else artifact.read_text(encoding='utf-8')==actual_body
            assert len(work_requests)==(4 if mode=='outcome-window' else 3) and state['task_success_proven'] is False
        else:
            state=None;assert not jobs.list_jobs(include_disabled=True) and not artifact.exists()
            if mode=='wait':
                waiting=execution.kernel('core_autonomous_work').CoreAutonomousWork(store).wait_evidence(saved['item_id'],store.configuration())
                assert waiting['work_submitted'] is False and 'future instruction' in waiting['reason']
        if mode=='revoked':
            with closing(store.journal._connect()) as c:
                c.execute('UPDATE autonomy_policies_v1 SET enabled=0 WHERE subject=?',(store.configuration().subject,))
        if mode=='outcome-recover':
            from unittest.mock import patch
            cls=execution.kernel('core_work_outcomes').CoreWorkOutcomes
            with patch.object(cls,'close',side_effect=RuntimeError('synthetic interruption after signed admission')):
                try:
                    await binding.native.step(binding.arguments['build_parameters']())
                    raise AssertionError('synthetic interruption was not observed')
                except RuntimeError:pass
            assert len(list(store.journal.read(event_type='work.outcome_decided')))==1
        elif mode=='outcome-malformed':
            stop=asyncio.Event()
            task=binding.native.start(binding.context,build_parameters=binding.arguments['build_parameters'],
                stop=stop,max_cycles=None,interval_seconds=600,continuous=True)
            deadline=asyncio.get_running_loop().time()+60
            while not list(store.journal.read(event_type='work.outcome_rejected')) or not binding.native.last_call_count:
                assert not task.done() and asyncio.get_running_loop().time()<deadline
                await asyncio.sleep(.05)
            assert not task.done(),'one bad model proposal must not terminate the host'
            stop.set();summary=await task
            assert summary['exit_reason']=='stopped' and summary['completed_cycles']>=1
            assert len(list(store.journal.read(event_type='work.outcome_rejected')))==1
            assert not list(store.journal.read(event_type='work.outcome_decided'))
        elif mode=='outcome-forged':
            result=await binding.native.step(binding.arguments['build_parameters']())
            assert result.disposition in ('silence','evidence_changed')
            assert len(list(store.journal.read(event_type='work.outcome_rejected')))==1
            assert not list(store.journal.read(event_type='work.outcome_decided'))
        elif mode=='outcome-revoked':
            try:
                await binding.native.step(binding.arguments['build_parameters']())
                raise AssertionError('unauthorized outcome was accepted')
            except ValueError:pass
        elif mode!='revision-recover':await binding.native.step(binding.arguments['build_parameters']())
        if mode.startswith('outcome-'):assert counts['outcome']==1
        if mode in ('outcome-complete','outcome-window','outcome-attention'):
            listed=json.loads(await command('agenda list'))['items'][0]
            assert listed['state']=='completed'
            outcomes=execution.kernel('core_work_outcomes').CoreWorkOutcomes(store)
            assert outcomes.view(state['work_id'],store.configuration())['current_item_state']=='completed'
            # A clear owner correction reopens it; old work cannot close it again.
            correction='刚才这项工作还没完成，请重新打开；不要重新执行。'
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            _collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                platform='telegram',_user_id=source.user_id),effective_task_id='reopen-outcome',turn_id='reopen-outcome',
                original_user_message=correction,messages=[{'role':'user','content':correction}],conversation_history=[])
            reopened=json.loads(model_tools.handle_function_call('alive_agenda',{'operation':'resume',
                'item_id':saved['item_id'],'item_version':listed['item_version'],'evidence_span':correction},
                task_id='reopen-outcome',session_id=entry.session_id,turn_id='reopen-outcome',
                tool_call_id='reopen-outcome-call',enabled_tools=['alive_agenda']))
            core.clear_session_vars(variables);variables=None
            assert reopened.get('state')=='active',reopened
            await binding.native.step(binding.arguments['build_parameters']())
            assert counts['outcome']==1 and outcomes.view(state['work_id'],store.configuration())['later_item_change']
        if mode.startswith('project-'):
            assert not (other/'relative-result.txt').exists() and not (home/'relative-result.txt').exists()
            if mode in ('project-missing','project-replaced'):assert not (moved/'relative-result.txt').exists()
        if mode=='revision-before':assert not original_artifact.exists()
        if mode in ('revision-after','revision-manual','revision-recover'):assert not (home/'new-revision-target.txt').exists()
        assert counts['start']==(0 if mode in ('erased','off','outcome-manual-long','revision-manual','project-manual') else 1) and len(jobs.list_jobs(include_disabled=True))==(1 if mode in ('execute','revoked','restart','attention-snooze','attention-resume','attention-cancel','attention-reopen','revision-before','revision-after','revision-legacy','revision-deadline','revision-manual','revision-recover','project-pinned','project-manual','project-replaced','project-restart') or mode.startswith('outcome-') else 0)
        from contextlib import closing
        with closing(store.journal._connect()) as c:
            assert c.execute('SELECT state FROM agenda_items_v1 WHERE item_id=?',(saved['item_id'],)).fetchone()[0]==('snoozed' if mode=='attention-snooze' else 'dismissed' if mode=='attention-cancel' else 'active')
        raw='\n'.join(r.event.canonical_json() for r in store.journal.read())
        assert original not in raw and str(artifact) not in raw and body.strip() not in raw
        if manual is not None:assert manual not in raw
        keys=('identity.key','content-vault/content.key','experience-content-vault/content.key')
        (home/'autonomous-expected.json').write_text(json.dumps({'work_id':state['work_id'] if state else None,
            'owner':store.configuration().subject,'artifact':str(artifact),'body':actual_body,'revoked':mode in ('revoked','attention-cancel','attention-reopen','revision-after','revision-manual','revision-recover','project-replaced'),'outcomes':mode.startswith('outcome-'),'pending_closure':mode=='outcome-recover','manual':manual is not None,'revision_item':saved['item_id'] if mode.startswith('revision-') else None,
            'project_dir':str(project) if mode.startswith('project-') else None,'project_missing':mode in ('project-missing','project-replaced'),
            'revision_due':json.loads(await command('agenda list'))['items'][0]['due_at'] if mode.startswith('revision-') and mode!='revision-recover' else None,
            'revision_expected_task':'Write NEW_REVISION_ONLY to '+str(home/'new-revision-target.txt') if mode=='revision-recover' else None,
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
        if expected['outcomes']:
            if expected['pending_closure']:
                cls=execution.kernel('core_work_outcomes').CoreWorkOutcomes
                async def no_new_model(**kwargs):raise AssertionError('pending admission must not need another model call')
                outcome=cls(store);cfg=store.configuration()
                asyncio.run(outcome.run(cfg,call=no_new_model,validate=lambda:outcome.authority(cfg),operation_id='cold-outcome-recovery'))
                assert len(list(store.journal.read(event_type='work.outcome_decided')))==1
            projection=execution.kernel('agenda').AgendaProjection(store.journal);projection.rebuild()
            assert projection.list_items(subject=expected['owner'],clearance='private',include_future=True,states=tuple(execution.kernel('agenda').AgendaState))[0].state.value==('completed' if expected['pending_closure'] else 'active')
        if expected.get('revision_item'):
            projection=execution.kernel('agenda').AgendaProjection(store.journal);projection.rebuild()
            row=projection.list_items(subject=expected['owner'],clearance='private',include_future=True)[0]
            assert row.item_id==expected['revision_item'] and (row.due_at.isoformat() if row.due_at else None)==expected['revision_due']
            if expected.get('revision_expected_task'):assert row.details['task']==expected['revision_expected_task']
            reader=execution.kernel('cognition_opportunities').CognitionOpportunityReader(store.journal,content_vault=store.vault)
            if expected.get('revision_expected_task'):
                # The crashed process never reached the host's normal lifecycle
                # refresh. The goal itself must already be valid after replay.
                from contextlib import closing
                from datetime import datetime,timezone
                with closing(store.journal._connect()) as c:
                    cached=c.execute('SELECT * FROM agenda_items_v1 WHERE item_id=?',(row.item_id,)).fetchone()
                assert reader._commitment(cached,subject=expected['owner'],now=datetime.now(timezone.utc))
                work=execution.kernel('core_work').CoreWorkStore(store)
                assert work.current_observation(row.item_id,subject=expected['owner']) is None
                cfg=store.configuration()
                work.refresh_observations(cfg,validate=lambda:execution.kernel('core_work_source').OwnedWorkSource(store).authority(cfg))
            assert reader.commitments(subject=expected['owner'],clearance='private')
        if expected.get('project_dir'):
            work=execution.kernel('core_work').CoreWorkStore(store)
            if expected['work_id']:
                value=work.status(expected['work_id'],subject=expected['owner'])
                assert value['project_context_binding']['status']==('unavailable' if expected['project_missing'] else 'available')
                from cron.jobs import get_job
                assert get_job(value['job_id'])['workdir']==expected['project_dir']
        from cron.jobs import list_jobs
        if expected['work_id']:
            state=execution.kernel('core_work').CoreWorkStore(store).status(expected['work_id'],subject=expected['owner'])
            assert state['core_execution_state']=='completed' and state['historical_owner_request_retained_by_core'] is (not expected['manual'])
            assert not Path(expected['artifact']).exists() if expected['revoked'] else Path(expected['artifact']).read_text(encoding='utf-8')==expected['body']
        assert len(list_jobs(include_disabled=True))==(1 if expected['work_id'] else 0)
    else:asyncio.run(exercise(Path(os.environ['HERMES_HOME'])))
