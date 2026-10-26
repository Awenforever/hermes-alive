"""Actual Core file tools and observer hooks, isolated synthetic owner profile.

OS reads independently check the artifact. Observation does not initiate the
work, prove arbitrary tool success, learn a preference or grant any tool access.
"""
import asyncio
import importlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import run_core_session_routing as core
from run_core_guided_setup import cli


async def test(home,*,authorized):
    home.mkdir()
    shutil.copytree(core.repo,home/'plugins/hermes-alive')
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':{'provider':'auto','default':'synthetic-not-called'}}))
    args=['setup','--confirm-model-calls','--confirm-delivery','--confirm-outbound-retention']
    if authorized:args.append('--confirm-core-tool-observation')
    rc,staged=cli(home,*args)
    assert rc==0 and staged['confirmation_summary']['core_tool_structural_observation']==authorized
    assert not staged['confirmation_summary']['core_tool_arguments_or_results_retained']
    assert cli(home,'install-runtime','--engine','kernel')[0]==0
    token=core.set_hermes_home_override(home)
    manager=None
    try:
        import httpx
        import model_tools
        import tools.file_tools  # actual Core read_file/write_file registration
        from hermes_cli.plugins import get_plugin_command_handler
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive']
        assert loaded.enabled and not loaded.error
        binding=loaded.module._gateway_host_binding
        setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
        adapter=core.Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter});adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-100694239',
            user_id='synthetic-tool-owner',message_id='synthetic-tool-setup')
        entry=runner.session_store.get_or_create_session(source)
        handler=get_plugin_command_handler('alive')
        confirmed=await runner._hm_run_plugin_handler(handler,None,source,session_entry=entry,
            args=staged['confirmation_command'].removeprefix('/alive '))
        assert '已确认' in confirmed
        store=setup.setup_store(binding)
        owner=store.configuration().subject
        def receipts():return store.journal.read(event_type='tool.execution_observed')
        assert not receipts()
        def no_http(*args,**kwargs):raise AssertionError('tool observation must not call HTTP')
        artifact=home/'synthetic-artifact.txt'
        contents='SYNTHETIC_ARTIFACT_BODY_NOT_IN_RECEIPT\n'
        def call(name,args,*,call_id,session_id=entry.session_id):
            return model_tools.handle_function_call(name,args,task_id='synthetic-tool-task',
                session_id=session_id,turn_id='synthetic-tool-turn',tool_call_id=call_id,
                enabled_tools=['read_file','write_file'])
        variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
            session_key=entry.session_key,session_id=entry.session_id)
        try:
            with patch.object(httpx.Client,'send',no_http),patch.object(httpx.AsyncClient,'send',no_http):
                written=call('write_file',{'path':str(artifact),'content':contents},call_id='synthetic-write')
                assert artifact.is_file() and artifact.read_text()==contents,written
                read=call('read_file',{'path':str(artifact)},call_id='synthetic-read')
                assert 'SYNTHETIC_ARTIFACT_BODY_NOT_IN_RECEIPT' in read,read
                # Replayed observer coordinates deduplicate receipts, not Core IO.
                call('read_file',{'path':str(artifact)},call_id='synthetic-read')
                assert len(receipts())==(2 if authorized else 0)
                before=len(receipts())
                call('read_file',{'path':str(artifact)},call_id='foreign-envelope',session_id='foreign-core-session')
                assert len(receipts())==before
                peer=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-100694240',
                    user_id='synthetic-other-owner',message_id='synthetic-other-input')
                peer_entry=runner.session_store.get_or_create_session(peer)
                peer_variables=core.set_session_vars(platform='telegram',chat_id=peer.chat_id,user_id=peer.user_id,
                    session_key=peer_entry.session_key,session_id=peer_entry.session_id)
                try:
                    call('read_file',{'path':str(artifact)},call_id='foreign-valid-conversation',session_id=peer_entry.session_id)
                    assert len(receipts())==before
                finally:
                    core.clear_session_vars(peer_variables)
                    variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                        session_key=entry.session_key,session_id=entry.session_id)
                def block(**values):
                    if values['tool_name']=='write_file':
                        return {'action':'block','message':'SYNTHETIC_BLOCK_BODY_NOT_IN_RECEIPT'}
                loaded.module._gateway_host_binding.context.register_hook('pre_tool_call',block)
                blocked=call('write_file',{'path':str(artifact),'content':'SHOULD_NOT_REPLACE'},call_id='synthetic-block')
                assert artifact.read_text()==contents and 'SYNTHETIC_BLOCK_BODY_NOT_IN_RECEIPT' in blocked
                assert len(receipts())==(3 if authorized else 0)
                # Cron/background work must not borrow its owner's conversation.
                cron=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                    session_key=entry.session_key,session_id=entry.session_id,cron_session='1')
                try:
                    call('read_file',{'path':str(artifact)},call_id='synthetic-cron')
                    assert len(receipts())==(3 if authorized else 0)
                finally:
                    core.clear_session_vars(cron)
                    variables=core.set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
                        session_key=entry.session_key,session_id=entry.session_id)
                # A missing protected key never authorizes a replacement key.
                identity=store.root/'identity.key';backup=store.root/'identity.key.test-held'
                identity.rename(backup)
                try:
                    call('read_file',{'path':str(artifact)},call_id='synthetic-missing-key')
                    assert not identity.exists()
                    assert len(receipts())==(3 if authorized else 0)
                finally:backup.rename(identity)
        finally:core.clear_session_vars(variables)
        if authorized:
            records=receipts()
            assert all(r.event.subject==owner and r.event.expires_at is not None for r in records)
            assert all(r.event.payload['configuration_event_id']==store.configuration().event_id for r in records)
            assert all(r.event.payload['task_success_proven'] is False for r in records)
            assert all(r.event.payload['automatic_learning_authority'] is False for r in records)
            assert records[0].event.payload['outcome']=='unknown'
            assert records[1].event.payload['outcome']=='unknown'
            assert records[2].event.payload['outcome']=='blocked'
            document=json.dumps([r.event.canonical_dict() for r in records])
            for forbidden in (contents.strip(),str(artifact),'SYNTHETIC_BLOCK_BODY_NOT_IN_RECEIPT',
                              'synthetic-tool-task',entry.session_id,'synthetic-write','synthetic-tool-owner'):
                assert forbidden not in document,forbidden
        # Tool observation works without activating a background host.
        assert store.activation() is None and binding.native is None
        print('HERMES_ALIVE_CORE_TOOL_OBSERVATION_CASE_OK='+str(authorized))
    finally:
        if manager:manager.unload()
        core.reset_hermes_home_override(token)
        from hermes_state_registry import close_all_under
        close_all_under(home)


async def main():
    with tempfile.TemporaryDirectory(prefix='alive-core-tool-observation-') as root:
        for authorized in (False,True):
            await test(Path(root)/str(authorized),authorized=authorized)
    print('HERMES_ALIVE_CORE_TOOL_OBSERVATION_OK')


if __name__=='__main__':asyncio.run(main())
