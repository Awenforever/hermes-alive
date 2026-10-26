"""Two actual Core processes, one protected profile and persistent SessionStore.

Synthetic admitted sources, controlled tool meaning and in-memory adapter only.
Active host startup is restored then deliberately stopped before model/action IO;
this does not prove a post-restart autonomous decision, real daemon or delivery.
"""
import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


async def phase(home,number):
    import run_core_session_routing as core
    from run_core_guided_setup import cli
    import httpx
    if number==1:
        home.mkdir(mode=0o700)
        shutil.copytree(core.repo,home/'plugins/hermes-alive')
        (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
            'model':{'provider':'custom:owner','default':'configured-primary'},
            'custom_providers':[{'name':'owner','model':'configured-primary','base_url':'https://provider.invalid/v1',
                                 'key_env':'OWNER_MAIN_KEY','api_mode':'chat_completions'}]}),encoding='utf-8')
        (home/'.env').write_text('OWNER_MAIN_KEY=SYNTHETIC_OWNER_KEY\n',encoding='utf-8')
        rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery',
                      '--confirm-outbound-retention','--confirm-followup-management')
        assert rc==0 and staged['confirmation_summary']['explicit_followup_management']
        assert cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home);manager=None;calls=[]
    try:
        import model_tools
        from agent.turn_context import _collect_pre_llm_call_context
        from hermes_cli.plugins import get_plugin_command_handler
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];assert loaded.enabled and not loaded.error
        binding=loaded.module._gateway_host_binding
        setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
        class Adapter(core.Adapter):
            async def send(self,*args,**kwargs):
                calls.append('send');raise AssertionError('restart test cannot send')
        adapter=Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-100694231',
                                  user_id='synthetic-restart-owner',message_id='restart-input')
        entry=runner.session_store.get_or_create_session(source)
        handler=get_plugin_command_handler('alive')
        async def command(args):
            return await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,args=args)
        def request(client,request,*args,**kwargs):
            calls.append('http');raise AssertionError('startup should stop before model IO')
        async def async_request(client,request,*args,**kwargs):return request_guard(client,request)
        request_guard=request
        with patch.object(httpx.Client,'send',request),patch.object(httpx.AsyncClient,'send',async_request):
            if number==1:
                assert '已确认' in await command(staged['confirmation_command'].removeprefix('/alive '))
                assert '已启用' in await command('enable')
            else:
                started=await loaded.module.kernel_gateway_startup()
                assert started['status']=='started',started
                assert binding.native.host.execute is True
            binding.arguments['stop'].set()
            await binding.task
            store=setup.setup_store(binding)
            assert store.activation() is not None
            if number==2:
                expected=json.loads((home/'restart-expected.json').read_text())
                assert '已失效' in await command(expected['draft_command'].removeprefix('/alive '))
            variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                session_key=entry.session_key,session_id=entry.session_id)
            try:
                text=('请持续跟进核对实验记录，只提醒，不代为提交。' if number==1 else '实验记录已经核对完成，不用再跟进。')
                turn='restart-main-'+str(number)
                context=_collect_pre_llm_call_context(SimpleNamespace(session_id=entry.session_id,model='configured-primary',
                    platform='telegram',_user_id=source.user_id),effective_task_id='restart-task',turn_id=turn,
                    original_user_message=text,messages=[{'role':'user','content':text}],conversation_history=[])
                assert 'alive_agenda' in context
                def tool(args):
                    return json.loads(model_tools.handle_function_call('alive_agenda',args,task_id='restart-task',
                        session_id=entry.session_id,turn_id=turn,tool_call_id='restart-call',enabled_tools=['alive_agenda']))
                if number==1:
                    recorded=tool({'operation':'record','task':'核对实验记录','constraint':'只提醒，不代为提交',
                        'due_at':(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(),'evidence_span':text})
                    assert recorded.get('status')=='recorded_under_owner_intake_grant',recorded
                    draft=tool({'operation':'propose','task':'尚未确认的另一个事项'})
                    assert draft.get('status')=='temporary_proposal_not_saved'
                    paths=('identity.key','content-vault/content.key','experience-content-vault/content.key')
                    expected={'item_id':recorded['item_id'],'owner':store.configuration().subject,
                        'session_key':entry.session_key,'session_id':entry.session_id,
                        'configuration':store.configuration().event_id,
                        'activation':store.activation()['activation_event_id'],
                        'draft_command':draft['confirmation_command'],
                        'keys':{name:hashlib.sha256((store.root/name).read_bytes()).hexdigest() for name in paths}}
                    (home/'restart-expected.json').write_text(json.dumps(expected),encoding='utf-8')
                else:
                    expected=json.loads((home/'restart-expected.json').read_text())
                    assert entry.session_key==expected['session_key'] and entry.session_id==expected['session_id']
                    assert store.configuration().subject==expected['owner'] and store.configuration().event_id==expected['configuration']
                    assert store.activation()['activation_event_id']==expected['activation']
                    assert all(hashlib.sha256((store.root/name).read_bytes()).hexdigest()==digest for name,digest in expected['keys'].items())
                    listed=tool({'operation':'list','item_id':expected['item_id']})
                    assert 'items' in listed,listed
                    rows=listed['items']
                    assert len(rows)==1 and rows[0]['state']=='active'
                    assert rows[0]['details']['constraint']=='只提醒，不代为提交'
                    result=tool({'operation':'complete','item_id':rows[0]['item_id'],'item_version':rows[0]['item_version'],
                                 'evidence_span':text})
                    assert result.get('state')=='completed',result
                    assert tool({'operation':'list','item_id':expected['item_id']})['items'][0]['state']=='completed'
            finally:core.clear_session_vars(variables)
            assert not calls and not binding.native.pending
        print('HERMES_ALIVE_CORE_RESTART_PHASE_OK='+str(number))
    finally:
        if manager:manager.unload()
        core.reset_hermes_home_override(token)
        from hermes_state_registry import close_all_under
        close_all_under(home)


if __name__=='__main__':
    child=os.environ.get('ALIVE_RESTART_TEST_PHASE')
    if child:
        asyncio.run(phase(Path(os.environ['ALIVE_RESTART_TEST_HOME']),int(child)))
    else:
        with tempfile.TemporaryDirectory(prefix='alive-core-cold-restart-') as root:
            for number in (1,2):
                result=subprocess.run([sys.executable,'-B',__file__,*sys.argv[1:]],env={**os.environ,
                    'ALIVE_RESTART_TEST_PHASE':str(number),'ALIVE_RESTART_TEST_HOME':str(Path(root)/'profile')},
                    capture_output=True,text=True,timeout=180)
                assert result.returncode==0,result.stdout+'\n'+result.stderr
                assert 'HERMES_ALIVE_CORE_RESTART_PHASE_OK='+str(number) in result.stdout
        print('HERMES_ALIVE_CORE_FOLLOWUP_RESTART_OK')
