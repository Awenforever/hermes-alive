"""No recipient or send: qualify scoped Core channel acquisition and retirement."""
import argparse
import asyncio
from contextvars import ContextVar
import gc
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace

parser=argparse.ArgumentParser()
parser.add_argument('--core',type=Path)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[3]
namespace=ModuleType('alive_channel_binding_fixture')
namespace.__path__=[str(repo)]
sys.modules[namespace.__name__]=namespace
module=importlib.import_module(namespace.__name__+'.gateway_channel_bridge')


def refused(operation):
    try: operation()
    except module.ChannelCapabilityUnavailable: return
    raise AssertionError('unavailable/foreign channel was accepted')


async def pure(home):
    current=ContextVar('test_channel_home',default=home)
    class Context:
        _manager=SimpleNamespace(scope_key=str(home))
        def __init__(self): self.factories=[]; self.cleanup=[]
        def register_platform_handler(self,name,factory): self.factories.append((name,factory))
        def on_unload(self,callback): self.cleanup.append(callback)
    class Adapter:
        platform='telegram'
        is_connected=False
        async def send(self,**_): raise AssertionError('capability acquisition sent a message')
    context=Context()
    handle=module.CoreChannelHandle(context,'telegram',observe_home=current.get)
    assert not handle.status()['bound']
    refused(handle.adapter)
    adapter=Adapter()
    context.factories[0][1](None,adapter)
    assert handle.status()['bound'] and not handle.status()['connected']
    refused(handle.adapter)
    adapter.is_connected=True
    assert handle.adapter() is adapter
    assert not handle.status()['recipient_authorized']
    async def wrong_loop(): refused(handle.adapter)
    await asyncio.to_thread(lambda:asyncio.run(wrong_loop()))
    token=current.set(home/'foreign')
    refused(handle.adapter)
    refused(lambda:context.factories[0][1](None,adapter))
    current.reset(token)
    assert handle.adapter() is adapter
    adapter.is_connected=False
    refused(handle.adapter)
    replacement=Adapter()
    context.factories[0][1](None,replacement)
    replacement.is_connected=True
    assert handle.adapter() is replacement
    conflicting=Adapter(); conflicting.is_connected=True
    refused(lambda:context.factories[0][1](None,conflicting))
    assert handle.status()['ambiguous'] and not handle.status()['bound']
    refused(handle.adapter)
    replacement.is_connected=False
    refused(lambda:context.factories[0][1](None,conflicting))
    assert not handle.status()['bound']
    for callback in context.cleanup: callback()
    refused(handle.adapter)
    context.factories[0][1](None,conflicting)  # stale retained factory cannot revive it
    refused(handle.adapter)
    fresh_context=Context()
    fresh=module.CoreChannelHandle(fresh_context,'telegram',observe_home=current.get)
    transient=Adapter(); transient.is_connected=True
    fresh_context.factories[0][1](None,transient)
    del transient
    gc.collect()
    assert not fresh.status()['bound']  # no heavy adapter retained by stale factories
    refused(fresh.adapter)
    fresh.close()
    wrong_context=Context()
    wrong=module.CoreChannelHandle(wrong_context,'telegram',observe_home=current.get)
    refused(lambda:wrong_context.factories[0][1](None,SimpleNamespace(platform='weixin',send=lambda:None)))
    wrong.close()
    for platform in ('','Telegram','../weixin',None):
        refused(lambda:module.CoreChannelHandle(Context(),platform,observe_home=current.get))


async def actual(home):
    sys.path.insert(0,str(args.core.resolve()))
    from hermes_constants import set_hermes_home_override,reset_hermes_home_override,get_hermes_home
    from hermes_cli.plugins import get_plugin_manager,PluginContext,PluginManifest,LoadedPlugin
    from gateway.config import Platform,PlatformConfig
    from gateway.platforms.base import BasePlatformAdapter,SendResult
    binding_module=importlib.import_module(namespace.__name__+'.gateway_host_bridge')
    config={'gateway':{'platforms':{'telegram':{'enabled':True}}},
        'plugins':{'entries':{'hermes-alive':{'settings':{'kernel_shadow':{'enabled':True}}}}}}
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    token=set_hermes_home_override(home)
    try:
        manager=get_plugin_manager()
        def register():
            manifest=PluginManifest(name='hermes-alive',version='0.0.0')
            manager._plugins[manifest.name]=LoadedPlugin(manifest,enabled=True)
            binding=binding_module.GatewayHostBinding(PluginContext(manifest,manager))
            assert binding.channel_error_class is None
            expected=module.known_core_channels()
            assert set(binding.channels)==expected and 'telegram' in expected
            return binding
        class Adapter(BasePlatformAdapter):
            def __init__(self): super().__init__(PlatformConfig(),Platform.TELEGRAM)
            async def connect(self,*,is_reconnect=False):
                self._wire_plugin_handlers(None)
                self._running=True
                return True
            async def disconnect(self): self._running=False
            async def send(self,**_): raise AssertionError('Core channel binding sent a message')
            async def get_chat_info(self,chat_id): return {'name':'synthetic','type':'dm'}
        first=register()
        adapter=Adapter()
        await adapter.connect()
        assert first.channels['telegram'].adapter() is adapter
        adapter.rewire_plugin_handlers()
        assert first.channels['telegram'].adapter() is adapter
        await adapter.disconnect()
        refused(first.channels['telegram'].adapter)
        await adapter.connect(is_reconnect=True)
        assert first.channels['telegram'].adapter() is adapter
        old=first.channels['telegram']
        assert manager.unload('hermes-alive') and first.closed and not first.channels
        refused(old.adapter)
        second=register()
        adapter.rewire_plugin_handlers()
        assert not second.channels['telegram'].status()['bound']
        refused(second.channels['telegram'].adapter)  # no false hot-reload readiness
        manager.unload()
        third=register()
        fresh=Adapter(); await fresh.connect()
        assert third.channels['telegram'].adapter() is fresh
        assert first.closed and second.closed
        other=set_hermes_home_override(home/'foreign')
        try: refused(third.channels['telegram'].adapter)
        finally: reset_hermes_home_override(other)
        assert Path(get_hermes_home()).resolve()==home.resolve()
        manager.unload()
        assert third.closed and fresh.is_connected  # plugin does not stop the Core transport
    finally:
        reset_hermes_home_override(token)


with tempfile.TemporaryDirectory(prefix='alive-channel-binding-') as directory:
    home=Path(directory)
    if args.core: asyncio.run(actual(home))
    else: asyncio.run(pure(home))
print('HERMES_ALIVE_GATEWAY_CHANNEL_BINDING_OK')
