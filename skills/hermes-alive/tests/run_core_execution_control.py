"""Installed Core command/lifetime control, synthetic peers, no model or send.

This does not prove daemon restart, real transport or full discovery quality.
"""
import asyncio
import importlib
import json
from pathlib import Path
import shutil
import tempfile
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace

import run_core_session_routing as core
from run_core_guided_setup import cli


async def test(home):
    home.mkdir()
    shutil.copytree(core.repo,home/'plugins/hermes-alive')
    model={'provider':'auto','default':'owner-configured-model'}
    (home/'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']},
        'model':model,'display':{'language':'fr'}}),encoding='utf-8')
    rc,staged=cli(home,'setup','--confirm-model-calls','--confirm-delivery',
        '--confirm-outbound-retention','--public-query','public astronomy news','--confirm-public-reads',
        '--language','zh-CN','--communication-preference','Use plain language; depth follows the material.')
    assert rc==0 and not staged['delivery_enabled']
    assert staged['confirmation_summary']['conversation_language']=='zh-CN'
    assert staged['confirmation_summary']['communication_preference']=='Use plain language; depth follows the material.'
    assert staged['confirmation_summary']['explicit_communication_memory_until_updated_or_forgotten'] is True
    command=staged['confirmation_command'].removeprefix('/alive ')
    rc,result=cli(home,'install-runtime','--engine','kernel')
    assert rc==0 and result['engine']=='kernel'
    token=core.set_hermes_home_override(home)
    manager=None
    try:
        manager=core.get_plugin_manager();manager.discover_and_load()
        loaded=manager._plugins['hermes-alive'];binding=loaded.module._gateway_host_binding
        assert loaded.enabled and loaded.error is None
        from hermes_cli.plugins import get_plugin_command_handler
        handler=get_plugin_command_handler('alive')
        adapter=core.Adapter(core.Platform.TELEGRAM)
        runner=core.runner_for(home,{core.Platform.TELEGRAM:adapter})
        adapter.gateway_runner=runner
        await adapter.connect()
        source=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id='-10054321',
            user_id='synthetic-owner',thread_id='7',message_id='synthetic-control')
        entry=runner.session_store.get_or_create_session(source)
        async def invoke(arguments,*,origin=source,session=entry):
            return await runner._hm_run_plugin_handler(handler,None,origin,session_entry=session,args=arguments)
        assert '已确认' in await invoke(command)
        setup=importlib.import_module(loaded.module.__name__+'.kernel_setup_bridge')
        execution=importlib.import_module(loaded.module.__name__+'.kernel_execution_bridge')
        store=setup.setup_store(binding)
        assert execution.expression_language(SimpleNamespace(options={}))=='fr'
        assert execution.expression_language(store.configuration())=='zh-CN'
        # Public-plugin namespace imports must work WITHOUT legacy hooks on
        # sys.path. Pure tests formerly masked the missing global safe_io import.
        from tools.registry import registry
        reads=[]
        def public_read(arguments,**_):
            reads.append(arguments)
            return json.dumps({'success':True,'data':{'web':[]}})
        registry.register(name='web_search',toolset='web',schema={'name':'web_search',
            'description':'Synthetic public-read import regression','parameters':{'type':'object'}},
            handler=public_read,override=True,scope=str(home))
        tools=execution.kernel('core_discovery_tools').CoreDiscoveryTools(binding.context,
            read_binding=lambda:'synthetic-current-binding',approved_queries=('public astronomy news',))
        assert json.loads(await tools.search('public astronomy news',limit=3))['success']
        assert reads==[{'query':'public astronomy news','limit':3}]
        assert not tools.pending
        tools.close()
        assert store.activation() is None
        assert '已启用' in await invoke('enable')
        active=store.activation()
        assert active and binding.task is not None and not binding.task.done()
        assert binding.native.host.execute and binding.arguments['continuous'] is True
        assert binding.native.context_reads is None  # no implicit private-memory permission
        assert binding.arguments['build_parameters']()['expression_parameters']['language']=='zh-CN'
        preferences=execution.kernel('cognition_context').CognitionContextReader(store.journal).read(
            subject=store.configuration().subject,clearance=execution.kernel('events').Sensitivity.PRIVATE)
        assert any(p.predicate=='profile.communication' and p.value=='Use plain language; depth follows the material.' for p in preferences)
        assert binding.arguments['build_parameters']()['expression_parameters']['authority']==execution.kernel('deliberation').ActionAuthority.USER_DELEGATED
        assert binding.native._caller is None
        # Hold the lifetime before yielding again: the actual native task is
        # tested without permitting source/model calls in this control fixture.
        binding.arguments['stop'].set()
        # Ordinary native ingress uses the configured Core principal without
        # the legacy shadow environment flag. Observe, never claim the turn.
        from gateway.run_inbound_consumer import run_post_admission_hook
        def inputs():return store.journal.read(event_type='conversation.inbound')
        host=binding.native.host
        def input_snapshot():
            return host.runtime.reconsideration.capture(subject=host.subject,
                configuration_id=host.configuration_id,execute=True,
                policy=host.runtime.reconciliation._owner_policy(host.subject),
                parameters=binding.arguments['build_parameters']()['expression_parameters'],window_seconds=600)
        original_input=input_snapshot()
        before_inputs=len(inputs())
        event=SimpleNamespace(message_id='synthetic-ordinary-input',text='PRIVATE_CURRENT_BODY_SENTINEL')
        assert await run_post_admission_hook(runner,event,source,entry.session_key)==(False,None)
        assert len(inputs())==before_inputs+1
        observed=inputs()[-1].event
        assert observed.subject==store.configuration().subject
        assert observed.actor=='system:alive-configured-input'
        assert observed.payload['method']=='configured-input-wake-v1'
        assert observed.payload['raw_content_stored'] is False
        assert observed.payload['erasable_content_stored'] is False
        assert observed.payload['learning_authority_granted'] is False
        current_input=input_snapshot()
        assert current_input.owner_frontier>original_input.owner_frontier
        assert current_input.semantic_digest!=original_input.semantic_digest
        assert b'PRIVATE_CURRENT_BODY_SENTINEL' not in store.journal.path.read_bytes()
        assert await run_post_admission_hook(runner,event,source,entry.session_key)==(False,None)
        assert len(inputs())==before_inputs+1,'ordinary replay became another wake'
        edited=SimpleNamespace(message_id=event.message_id,text='PRIVATE_EDITED_BODY_SENTINEL')
        assert await run_post_admission_hook(runner,edited,source,entry.session_key)==(False,None)
        assert len(inputs())==before_inputs+2,'changed normalized text did not wake'
        assert await run_post_admission_hook(runner,event,source,entry.session_key)==(False,None)
        assert len(inputs())==before_inputs+2,'old content replay superseded its newer revision'
        foreign=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id=source.chat_id,
            user_id='synthetic-other',thread_id='7')
        assert await run_post_admission_hook(runner,event,foreign,entry.session_key)==(False,None)
        assert len(inputs())==before_inputs+2
        other_thread=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id=source.chat_id,
            user_id=source.user_id,thread_id='8')
        assert await run_post_admission_hook(runner,event,other_thread,entry.session_key)==(False,None)
        assert len(inputs())==before_inputs+2
        # A separate consumer can own @actions. Alive neither requires that
        # plugin nor stores its body or turns it into a user-authorized memory.
        binding.context.register_hook('post_gateway_admission',lambda **v:
            {'action':'handled','reply':'synthetic consumer'} if v.get('text')=='@synthetic-action' else None)
        event=SimpleNamespace(message_id='synthetic-consumed-input',text='@synthetic-action')
        assert await run_post_admission_hook(runner,event,source,entry.session_key)==(True,'synthetic consumer')
        assert len(inputs())==before_inputs+3
        assert '有效' in await invoke('status')
        assert '仍在运行' in await invoke('enable')
        assert len(store.journal.read(event_type='alive.setup.activated'))==1
        rc,status=cli(home,'status')
        assert rc==0 and status['enabled'] and status['delivery_authority_activated']
        assert status['setup_phase']=='authorized_runtime_unverified' and not status['live_runtime_verified']
        rc,blocked=cli(home,'setup','--replace','--confirm-model-calls','--confirm-delivery',
            '--confirm-outbound-retention')
        assert rc==2 and blocked['existing_runtime_must_be_paused']
        foreign=core.SessionSource(platform=core.Platform.TELEGRAM,chat_id=source.chat_id,
            user_id='synthetic-foreign',thread_id='7',message_id='foreign')
        foreign_entry=runner.session_store.get_or_create_session(foreign)
        for operation in ('status','enable','pause'):
            reply=await invoke(operation,origin=foreign,session=foreign_entry)
            assert '未完成' in reply and '当前发送授权：有效' not in reply
        assert store.activation()==active
        # Simulate a clean Gateway task stop, retaining the owner's authorization.
        original_native=binding.native
        binding.arguments['stop'].set()
        stopped=await binding.task
        assert stopped['exit_reason']=='stopped' and original_native._caller is None
        assert not original_native.pending
        rc,shadow=cli(home,'install-runtime','--engine','kernel-shadow')
        assert rc==0 and shadow['engine']=='kernel-shadow'
        assert store.activation()==active and execution.assemble(binding) is None
        assert '影子模式保持不发送' in await invoke('enable')
        assert len(store.journal.read(event_type='alive.setup.activated'))==1
        rc,native_installed=cli(home,'install-runtime','--engine','kernel')
        assert rc==0 and native_installed['engine']=='kernel'
        restored=execution.assemble(binding)
        assert restored is not None and restored[0] is not original_native
        assert restored[0].host.configuration_id==active['activation_event_id']
        execution.attach(binding,restored)
        assert (await loaded.module.kernel_gateway_startup())['status']=='started'
        assert len(store.journal.read(event_type='alive.setup.activated'))==1
        assert store.activation()==active  # startup did not renew expiry/grants
        record=store.journal.get(active['activation_event_id'])
        assert record.event.expires_at is None and record.event.payload['lifetime']=='until_revoked'
        assert store.activation(now=datetime.now(timezone.utc)+timedelta(days=366))==active
        assert store.journal.get(active['delegation_event_id']).event.expires_at is None
        assert '已暂停' in await invoke('pause')
        paused_inputs=len(inputs())
        assert await run_post_admission_hook(runner,SimpleNamespace(
            message_id='synthetic-paused-input',text='PRIVATE_PAUSED_BODY'),source,entry.session_key)==(False,None)
        assert len(inputs())==paused_inputs
        await binding.task
        assert store.activation(now=datetime.now(timezone.utc)+timedelta(days=366)) is None
        assert store.activation() is None and not binding.native.pending
        assert (await loaded.module.kernel_gateway_startup())['status']=='stopped'
        assert execution.assemble(binding) is None
        rc,status=cli(home,'status')
        assert rc==0 and not status['enabled'] and not status['delivery_authority_activated']
        assert not store.journal.read(event_type='dispatch.started')
        assert not store.journal.read(event_type='transport.adapter.observed')
        assert not store.journal.read(event_type='model.call.started')
        # Re-enable explicitly, then prove a cross-process CLI pause stops the
        # real native loop before source/model work, not just legacy markers.
        assert '已启用' in await invoke('enable')
        rc,disabled=cli(home,'disable')
        assert rc==0 and disabled['new_work_authority_revoked'] and not disabled['transport_queue_drained']
        result=await binding.task
        assert result['exit_reason']=='paused' and store.activation() is None
        assert binding.native.last_call_count==0 and not binding.native.pending
        assert not store.journal.read(event_type='dispatch.started')
        # The next explicit activation is subject to the same owner's cadence.
        assert '已启用' in await invoke('enable')
        binding.arguments['stop'].set()
        await binding.task
        interrupted=binding.native.host.open_cycle()  # durable synthetic interruption, no model/IO
        assert '已暂停' in await invoke('pause')
        assert '已启用' in await invoke('enable')
        binding.arguments['stop'].set()
        await binding.task
        assert store.activation()['supersedes_cycle_event_id']==interrupted.event_id
        closed=store.journal.get(interrupted.event_id+':closed')
        assert closed and closed.event.payload['disposition']=='paused'
        assert closed.event.payload['external_delivery_proven'] is False
        # Replaying the authorized transition cannot retire a NEW operation.
        active=store.activation()
        next_cycle=binding.native.host.open_cycle()
        execution._complete_supersession(binding.native.host.runtime,store.configuration(),active)
        assert not store.journal.get(next_cycle.event_id+':closed')
        assert next_cycle.event_id!=interrupted.event_id
        binding.native.host.close_cycle(next_cycle,execution.kernel('autonomous_cycle_runtime').AutonomousCycleResult(
            'paused',{'next_after_sequence':next_cycle.reconciliation_cursor}))
        active=store.activation();native=binding.native;runtime=native.host.runtime
        when=datetime.now(timezone.utc)
        payload={'dispatch_id':'synthetic-consumed-start','lease_generation':1,
            'delegation_event_id':active['delegation_event_id'],'cadence_reserved_at':when.isoformat()}
        payload['integrity_authenticator']=runtime.outbox.protector.authenticate_json('dispatch.start.v1',payload)
        event=execution.kernel('events').EventEnvelope(
            event_id=runtime.outbox._start_event_id('synthetic-consumed-start',1),
            event_type='dispatch.started',source='alive.dispatch',actor='system:alive-dispatch',
            subject=store.configuration().subject,observed_at=when,occurred_at=when,payload=payload)
        store.journal.append(event)  # isolated signed cadence fixture, NOT an actual send
        async def forbidden(**_):raise AssertionError('cooldown invoked source/model work')
        build=binding.arguments['build_parameters']
        bound=await native.preparation(cycle=SimpleNamespace(operation_id='control-cooldown'),
            parameters=build(),call=forbidden,read_binding=forbidden)
        assert bound['defer_until_eligible'] and bound['authorization_parameters']['authorization_operation_id']
        another=await native.preparation(cycle=SimpleNamespace(operation_id='another-cooldown'),
            parameters=build(),call=forbidden,read_binding=forbidden)
        assert another['authorization_parameters']['authorization_operation_id']!=bound['authorization_parameters']['authorization_operation_id']
        waiting=await runtime.cycle(subject=store.configuration().subject,operation_id='control-cooldown',
            execute=True,**{**bound,'expression_parameters':{**bound['expression_parameters'],'call':forbidden}})
        assert waiting.disposition=='waiting_for_change'
        assert len(store.journal.read(event_type='dispatch.started'))==1
        assert '已暂停' in await invoke('pause')
        original_key=store.protector.key_path.read_bytes()
        original_configuration=store.configuration()
        rc,removed=cli(home,'uninstall-runtime')
        assert rc==0 and removed['user_state_preserved']
        rc,reinstalled=cli(home,'install-runtime')
        assert rc==0 and reinstalled['engine']=='kernel'
        assert store.protector.key_path.read_bytes()==original_key
        assert store.configuration()==original_configuration and store.activation() is None
        from hermes_yaml import safe_load
        assert safe_load((home/'config.yaml').read_text())['model']==model
        assert command.split()[1] not in (home/'config.yaml').read_text()
        print('HERMES_ALIVE_CORE_EXECUTION_CONTROL_OK')
    finally:
        if manager is not None:manager.unload()
        core.reset_hermes_home_override(token)


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-execution-control-') as directory:
        try:asyncio.run(test(Path(directory)/'profile'))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
