"""Actual Core cron inspection scope, fresh read and blocked write, synthetic only."""
import asyncio,importlib,json,os,shutil,subprocess,sys,tempfile,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

if __name__=='__main__' and os.environ.get('ALIVE_SCOPE_TEST_CHILD')!='1':
    with tempfile.TemporaryDirectory(prefix='alive-core-inspection-') as root:
        env={**os.environ,'HOME':root,'HERMES_HOME':str(Path(root)/'profile'),
             'ALIVE_SCOPE_TEST_CHILD':'1','PYTHONDONTWRITEBYTECODE':'1'}
        try:
            for cold in (False,True):
                log=Path(root)/('consumer-'+str(int(cold))+'.log')
                try:
                    with log.open('w') as output:
                        result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],
                            env={**env,**({'ALIVE_INSPECTION_COLD':'1'} if cold else {})},
                            stdout=output,stderr=subprocess.STDOUT,text=True,timeout=180)
                except subprocess.TimeoutExpired:
                    print(log.read_text(),flush=True);raise
                assert result.returncode==0,log.read_text()
        finally:
            stopped=subprocess.run([sys.executable,'-B','-m','hermes_cli.main','gateway','stop'],env=env,
                capture_output=True,text=True,timeout=30)
            assert stopped.returncode==0,'isolated Gateway did not stop'
    print('HERMES_ALIVE_CORE_WORK_INSPECTION_SCOPE_OK')
    raise SystemExit(0)

import run_core_session_routing as core


def run(home):
    cold=os.environ.get('ALIVE_INSPECTION_COLD')=='1'
    requests=[];scope_errors=[];auxiliary_requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.send_error(503)
        def do_POST(self):
            data=json.loads(self.rfile.read(int(self.headers.get('content-length','0'))))
            is_inspection=any(m.get('role')=='user' and 'SYNTHETIC_INSPECTION_TASK_V1' in str(m.get('content'))
                for m in data.get('messages',[]))
            if not is_inspection:
                auxiliary_requests.append({'stream':data.get('stream'),'has_tools':bool(data.get('tools'))})
                message={'role':'assistant','content':'Synthetic model metadata probe ready.'};finish='stop'
            else:
                requests.append(data)
                names={t.get('function',t)['name'] for t in (data.get('tools') or [])}
                if names!={'read_file'}:
                    scope_errors.append(sorted(names))
                    raw=json.dumps({'error':{'message':'inspection scope mismatch','type':'invalid_request_error'}}).encode()
                    self.send_response(400);self.send_header('content-type','application/json')
                    self.send_header('content-length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
                if len(requests)==1:
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'forbidden-write','type':'function',
                        'function':{'name':'write_file','arguments':json.dumps({'path':str(artifact),'content':'SHOULD_NOT_WRITE'})}}]};finish='tool_calls'
                elif len(requests)==2:
                    assert 'SHOULD_NOT_WRITE' not in artifact.read_text()
                    message={'role':'assistant','content':None,'tool_calls':[{'id':'fresh-read','type':'function',
                        'function':{'name':'read_file','arguments':json.dumps({'path':str(artifact)})}}]};finish='tool_calls'
                else:
                    if not any(m.get('role')=='tool' and 'FRESH_INSPECTION_VIEW' in str(m.get('content')) for m in data['messages']):
                        scope_errors.append({'missing_fresh_result':[(m.get('role'),str(m.get('content'))[-300:]) for m in data['messages'][-4:]]})
                        self.send_error(400,'missing expected fresh tool result');return
                    message={'role':'assistant','content':'The read tool returned the fresh file view.'};finish='stop'
            if data.get('stream'):
                delta={k:v for k,v in message.items() if k!='role'}
                if 'tool_calls' in delta:delta['tool_calls'][0]['index']=0
                chunk={'id':'synthetic-inspection','object':'chat.completion.chunk','created':0,'model':'configured-primary',
                    'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
                raw=('data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n').encode();mime='text/event-stream'
            else:
                raw=json.dumps({'id':'synthetic-inspection','object':'chat.completion','created':0,'model':'configured-primary',
                    'choices':[{'index':0,'message':message,'finish_reason':finish}],
                    'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}}).encode();mime='application/json'
            self.send_response(200);self.send_header('content-type',mime)
            self.send_header('content-length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=None;worker=None
    if not cold:
        home.mkdir(exist_ok=True);shutil.copytree(core.repo,home/'plugins/hermes-alive')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        configuration={'plugins':{'enabled':['hermes-alive']},
            'memory':{'provider':'builtin','memory_enabled':False,'user_profile_enabled':False},
            'model':{'provider':'custom:owner','default':'configured-primary'},
            'custom_providers':[{'name':'owner','model':'configured-primary','key_env':'OWNER_MAIN_KEY',
                'base_url':'http://127.0.0.1:'+str(server.server_port)+'/v1','api_mode':'chat_completions'}]}
        (home/'config.yaml').write_text(json.dumps(configuration));(home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_SCOPE_KEY\n')
    token=core.set_hermes_home_override(home);manager=None
    try:
        import run_agent,tools.file_tools
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];assert loaded.enabled and not loaded.error,loaded.error
        scope=importlib.import_module(loaded.module.__name__+'.core_work_inspection_scope')
        assert scope.effective_tools()=={'read_file'}
        if cold:
            print('HERMES_ALIVE_CORE_WORK_INSPECTION_COLD_OK');return
        # Core's ordinary disabled file toolset must subtract even through this
        # composition. No allowlist alias may re-enable a user-disabled tool.
        configuration['agent']={'disabled_toolsets':['file']}
        (home/'config.yaml').write_text(json.dumps(configuration))
        assert not scope.effective_tools()
        configuration['agent']={'disabled_toolsets':[scope.NAME]}
        (home/'config.yaml').write_text(json.dumps(configuration))
        assert not scope.effective_tools()
        configuration.pop('agent');(home/'config.yaml').write_text(json.dumps(configuration))
        assert scope.effective_tools()=={'read_file'}
        artifact=home/'artifact.txt';artifact.write_text('OLD_PRODUCER_VIEW')
        # Change the world after the producer's old view. Inspector must call
        # Core read_file now; historical output or a canned claim cannot pass.
        artifact.write_text('FRESH_INSPECTION_VIEW')
        from cron.jobs import create_job,trigger_job,list_jobs,get_job
        from cron.scheduler import tick
        from cron.scheduler_provider import resolve_cron_scheduler
        from cron.executions import latest_execution
        job=create_job(prompt='SYNTHETIC_INSPECTION_TASK_V1: Inspect the existing file '+str(artifact)+' with read_file. Do not modify it.',
            schedule='1h',repeat=1,deliver='local',paused=True,enabled_toolsets=[scope.NAME,'no_mcp'])
        resolve_cron_scheduler().register_job(trigger_job(job['id']))
        assert tick(verbose=False,sync=True,headless=False)==1
        assert not scope_errors,{'unexpected_tool_sets':scope_errors}
        assert latest_execution(job['id'])['status']=='completed',get_job(job['id']).get('last_error')
        assert artifact.read_text()=='FRESH_INSPECTION_VIEW' and len(requests)==3
        assert len(list_jobs(include_disabled=True))==1
        assert any(m.get('role')=='tool' and m.get('tool_call_id')=='forbidden-write'
            and ('not' in str(m.get('content')).lower() or 'error' in str(m.get('content')).lower())
            for m in requests[-1]['messages'])
        print('HERMES_ALIVE_CORE_WORK_INSPECTION_SCOPE_OK')
    finally:
        if manager:manager.unload()
        core.reset_hermes_home_override(token)
        from hermes_state_registry import close_all_under
        close_all_under(home)
        if server:server.shutdown();server.server_close();worker.join(timeout=5)

if __name__=='__main__':run(Path(os.environ['HERMES_HOME']))
