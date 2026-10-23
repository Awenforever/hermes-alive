"""Actual Core SessionStore/identity/delivery helpers, synthetic config/transport.

No real accounts, model, message, memory migration or consumer installation.
"""
import argparse
import asyncio
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace
from unittest.mock import patch

parser=argparse.ArgumentParser()
parser.add_argument('--core',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.core.resolve()))
from hermes_constants import set_hermes_home_override,reset_hermes_home_override
from hermes_cli.plugins import get_plugin_manager,PluginContext,PluginManifest,LoadedPlugin
from gateway.config import GatewayConfig,Platform,PlatformConfig
from gateway.platforms.base import BasePlatformAdapter
from gateway.run import GatewayRunner
from gateway.session import SessionStore,SessionSource
from gateway.session_context import set_session_vars,clear_session_vars

repo=Path(__file__).resolve().parents[3]
namespace=ModuleType('alive_session_fixture');namespace.__path__=[str(repo)]
sys.modules[namespace.__name__]=namespace
module=importlib.import_module(namespace.__name__+'.gateway_session_bridge')
binding_module=importlib.import_module(namespace.__name__+'.gateway_host_bridge')
hooks=repo/'skills/hermes-alive/hooks'
kernel=ModuleType('alive_session_kernel_fixture');kernel.__path__=[str(hooks/'alive_kernel')]
sys.modules[kernel.__name__]=kernel
Protector=importlib.import_module(kernel.__name__+'.privacy').LocalIdentityProtector


def refused(operation):
    try:operation()
    except module.SessionScopeUnavailable:return
    raise AssertionError('foreign, stale or unavailable Core route was accepted')


class Adapter(BasePlatformAdapter):
    def __init__(self,platform):super().__init__(PlatformConfig(),platform)
    async def connect(self,*,is_reconnect=False):
        self._wire_plugin_handlers(None);self._running=True;return True
    async def disconnect(self):self._running=False
    async def send(self,**_):raise AssertionError('session resolution sent a message')
    async def get_chat_info(self,chat_id):return {'name':'synthetic','type':'dm'}


def runner_for(home,adapters):
    # Actual Core methods and actual persistent store; no fake routing callbacks.
    # Avoid starting a daemon/SDK, which is not the scope of this component test.
    config=GatewayConfig()
    runner=object.__new__(GatewayRunner)
    runner.config=config;runner.adapters=adapters
    runner._primary_profile_name='default';runner._profile_adapters={}
    runner.session_store=SessionStore(home/'sessions',config)
    return runner


async def main(home):
    home.mkdir()
    config={'plugins':{'entries':{'hermes-alive':{'settings':{'kernel_shadow':{'enabled':True}}}}}}
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    token=set_hermes_home_override(home)
    manager=None
    try:
        manager=get_plugin_manager()
        manifest=PluginManifest(name='hermes-alive',version='0.0.0')
        manager._plugins[manifest.name]=LoadedPlugin(manifest,enabled=True)
        context=PluginContext(manifest,manager)
        binding=binding_module.GatewayHostBinding(context)
        telegram=Adapter(Platform.TELEGRAM);slack=Adapter(Platform.SLACK)
        runner=runner_for(home,{Platform.TELEGRAM:telegram,Platform.SLACK:slack})
        telegram.gateway_runner=runner;slack.gateway_runner=runner
        await telegram.connect();await slack.connect()
        router=binding.session_router('telegram')
        assert binding.session_router('telegram') is router
        source=SessionSource(platform=Platform.TELEGRAM,chat_id='chat-42',user_id='same-raw-user',
            thread_id='7',message_id='synthetic-anchor')
        entry=runner.session_store.get_or_create_session(source)
        arguments=dict(session_key=entry.session_key,user_id=source.user_id,platform='telegram')
        before=entry.to_dict()
        scope=router.capture_target(**arguments)
        assert entry.to_dict()==before and getattr(entry.origin,'_identity',None) is None
        assert scope.session_id==entry.session_id and dict(scope.route)=={
            'profile':'default','platform':'telegram','chat_id':'chat-42','thread_id':'7'}
        adapter,metadata=router.resolve_channel(scope,scope.route)
        assert adapter is telegram and metadata['thread_id']=='7'
        assert metadata['direct_messages_topic_id']=='7'
        assert await asyncio.to_thread(router.for_turn,session_id=entry.session_id,**arguments)==scope
        envelope={'session_id':entry.session_id,'sender_id':source.user_id,'platform':'telegram'}
        assert router.scope_for_hook(envelope) is None
        variables=set_session_vars(platform='telegram',chat_id=source.chat_id,user_id=source.user_id,
            session_key=entry.session_key,session_id=entry.session_id)
        try:
            assert await asyncio.to_thread(router.scope_for_hook,envelope)==scope
            # Run the actual Core hook dispatcher/turn context collector too,
            # not just a direct method call with a matching synthetic dict.
            from agent.turn_context import _collect_pre_llm_call_context
            observed=[]
            def observe_scope(**values):
                current=router.scope_for_hook(values)
                if current is not None:
                    observed.append(current)
                    return {'context':'scope-confirmed-for-fixture-only'}
            context.register_hook('pre_llm_call',observe_scope)
            agent=SimpleNamespace(session_id=entry.session_id,model='never-called',
                platform='telegram',_user_id=source.user_id)
            messages=[{'role':'system','content':'UNCHANGED PREFIX'},
                      {'role':'user','content':'A synthetic follow-up, not private content.'}]
            unchanged=json.dumps(messages)
            def collect():
                return _collect_pre_llm_call_context(agent,effective_task_id='synthetic-task',
                    turn_id='synthetic-turn',original_user_message=messages[-1]['content'],
                    messages=messages,conversation_history=messages[:-1])
            assert collect()=='scope-confirmed-for-fixture-only' and observed==[scope]
            assert json.dumps(messages)==unchanged
            agent._parent_session_id='synthetic-parent'
            assert collect()=='' and observed==[scope]
            refused(lambda:router.scope_for_hook({**envelope,'sender_id':'foreign-user'}))
            refused(lambda:router.scope_for_hook({**envelope,'session_id':'foreign-session'}))
            assert router.scope_for_hook({**envelope,'parent_session_id':'a-parent'}) is None
        finally:clear_session_vars(variables)
        # Stale legacy environment must never select a session without a bound
        # task-local key, even if all the remaining values resemble a live turn.
        with patch.dict(os.environ,HERMES_SESSION_KEY=entry.session_key,
                HERMES_SESSION_ID=entry.session_id,HERMES_SESSION_USER_ID=source.user_id,
                HERMES_SESSION_PLATFORM='telegram'):
            assert router.scope_for_hook(envelope) is None
        for change in ({'user_id':'foreign-user'},{'session_key':'missing-key'},
                       {'platform':'slack'}):
            refused(lambda:router.capture_target(**{**arguments,**change}))
        refused(lambda:router.for_turn(session_id='wrong-session',**arguments))
        refused(lambda:router.resolve_channel(scope,{**dict(scope.route),'thread_id':'8'}))
        for change in ({'user_id':'foreign-user'},{'transport_profile':'other-bot'},
                       {'scope_id':'foreign-workspace'},{'runtime_profile':'foreign-profile'},
                       {'chat_type':'group'}):
            forged=replace(scope,**change)
            refused(lambda:router.resolve_channel(forged,forged.route))
        foreign=set_hermes_home_override(home/'foreign')
        try:refused(lambda:router.for_turn(session_id=entry.session_id,**arguments))
        finally:reset_hermes_home_override(foreign)
        async def wrong_loop():refused(lambda:router.resolve_channel(scope,scope.route))
        await asyncio.to_thread(lambda:asyncio.run(wrong_loop()))
        await asyncio.to_thread(lambda:refused(lambda:router.resolve_channel(scope,scope.route)))
        protector=Protector(home/'alive-private/identity.key')
        principal=scope.principal(protector)
        assert principal!=protector.pseudonym('user',source.user_id)
        assert principal.startswith('user:core-v2:') and 'same-raw-user' not in principal
        assert replace(scope,session_id='new-id').principal(protector)==principal
        for change in ({'platform':'slack'},{'transport_profile':'other-bot'},
                       {'scope_id':'other-workspace'},{'guild_id':'other-guild'}):
            assert replace(scope,**change).principal(protector)!=principal
        # Receive-side scope remains readable if the transport disconnects mid
        # admitted turn. A new physical submission still requires connectivity.
        await telegram.disconnect()
        assert router.for_turn(session_id=entry.session_id,**arguments)==scope
        refused(lambda:router.capture_target(**arguments))
        refused(lambda:router.resolve_channel(scope,scope.route))
        await telegram.connect(is_reconnect=True)
        assert router.capture_target(**arguments)==scope
        # A cold Core store must reconstruct the same exact route from disk,
        # not borrow the first store's in-memory source or identity.
        restarted=runner_for(home,runner.adapters)
        reopened=module.CoreSessionRouter(context,restarted)
        assert reopened.for_turn(session_id=entry.session_id,**arguments)==scope
        assert reopened.capture_target(**arguments).principal(protector)==principal
        reset=runner.session_store.reset_session(entry.session_key)
        assert reset is not None and reset.session_id!=scope.session_id
        refused(lambda:router.for_turn(session_id=scope.session_id,**arguments))
        refused(lambda:router.resolve_channel(scope,scope.route))
        assert router.capture_target(**arguments).principal(protector)==principal
        # Slack's native team/user/thread metadata must not be reconstructed or
        # dropped by Alive's route bridge.
        slack_source=SessionSource(platform=Platform.SLACK,chat_id='channel-1',user_id='same-raw-user',
            scope_id='team-1',parent_chat_id='parent-1',thread_id='thread-1',message_id='anchor-2')
        slack_entry=runner.session_store.get_or_create_session(slack_source)
        slack_scope=router.capture_target(session_key=slack_entry.session_key,
            user_id=slack_source.user_id,platform='slack')
        slack_adapter,slack_metadata=router.resolve_channel(slack_scope,slack_scope.route)
        assert slack_adapter is slack and slack_metadata['slack_team_id']=='team-1'
        assert slack_metadata['user_id']==slack_source.user_id
        assert slack_metadata['parent_chat_id']=='parent-1'
        assert slack_scope.principal(protector)!=principal
        assert manager.unload('hermes-alive')
        refused(lambda:router.capture_target(**arguments))
        refused(lambda:reopened.capture_target(**arguments))
        assert telegram.is_connected and slack.is_connected
        assert not binding._session_routers
    finally:
        if manager is not None:manager.unload()
        reset_hermes_home_override(token)


async def multiplex(home):
    from hermes_cli.profiles import get_profile_dir
    from gateway.session_identity import canonical_identity
    home.mkdir()
    (home/'config.yaml').write_text('{}',encoding='utf-8')
    # Only the synthetic process home is changed, inside a fixture context. This
    # prevents Core's real profile resolver from reaching any user's own profile.
    with patch.dict(os.environ,HERMES_HOME=str(home)):
        primary_token=set_hermes_home_override(home)
        satellite_token=None
        manager=None
        try:
            satellite=get_profile_dir('alive-satellite')
            assert satellite.resolve().is_relative_to(home.resolve())
            satellite.mkdir(parents=True)
            (satellite/'config.yaml').write_text('{}',encoding='utf-8')
            primary=Adapter(Platform.TELEGRAM);secondary=Adapter(Platform.TELEGRAM)
            runner=runner_for(home,{Platform.TELEGRAM:primary})
            runner.config.multiplex_profiles=True
            runner._profile_adapters={'alive-satellite':{Platform.TELEGRAM:secondary}}
            primary.gateway_runner=runner;secondary.gateway_runner=runner
            await primary.connect();await secondary.connect()
            source=SessionSource(platform=Platform.TELEGRAM,chat_id='shared-chat',
                user_id='same-raw-user',thread_id='7',profile='alive-satellite')
            identity=canonical_identity(source,runner=runner,adapter=primary)
            assert identity is not None and identity.runtime_home.resolve()==satellite.resolve()
            assert identity.transport_profile=='default'
            satellite_token=set_hermes_home_override(satellite)
            entry=runner.session_store.get_or_create_session(source)
            assert entry.transport_profile=='default'
            manager=get_plugin_manager()
            manifest=PluginManifest(name='hermes-alive',version='0.0.0')
            manager._plugins[manifest.name]=LoadedPlugin(manifest,enabled=True)
            context=PluginContext(manifest,manager)
            router=module.CoreSessionRouter(context,runner)
            args=dict(session_key=entry.session_key,user_id=source.user_id,platform='telegram')
            scope=router.capture_target(**args)
            assert scope.runtime_profile=='alive-satellite' and scope.transport_profile=='default'
            adapter,_=router.resolve_channel(scope,scope.route)
            assert adapter is primary and adapter is not secondary
            await primary.disconnect()
            # The runtime's OTHER connected bot may not answer for the receiver.
            refused(lambda:router.capture_target(**args))
            refused(lambda:router.resolve_channel(scope,scope.route))
            assert router.for_turn(session_id=entry.session_id,**args)==scope
            await primary.connect(is_reconnect=True)
            entry.transport_profile=None
            refused(lambda:router.capture_target(**args))
            entry.transport_profile='default'
            outside=set_hermes_home_override(home)
            try:refused(lambda:router.capture_target(**args))
            finally:reset_hermes_home_override(outside)
            assert manager.unload('hermes-alive')
            refused(lambda:router.capture_target(**args))
        finally:
            if manager is not None:manager.unload()
            if satellite_token is not None:reset_hermes_home_override(satellite_token)
            reset_hermes_home_override(primary_token)


with tempfile.TemporaryDirectory(prefix='alive-core-session-') as directory:
    try:
        asyncio.run(main(Path(directory)/'profile'))
        asyncio.run(multiplex(Path(directory)/'multiplex-primary'))
    finally:
        # Windows cannot remove open SQLite/WAL files. This is ONLY the owned
        # fixture directory, never global process/profile storage teardown.
        from hermes_state_registry import close_all_under
        close_all_under(directory)
print('HERMES_ALIVE_CORE_SESSION_ROUTING_OK')
