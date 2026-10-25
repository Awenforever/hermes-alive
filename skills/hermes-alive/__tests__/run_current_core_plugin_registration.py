"""Actual current-Core manifest gate/import/registration; no model or transport IO.

Run in a Core-PM environment including this plugin's declared dependencies.
This is not a public consumer install, enabled autonomous loop or fleet proof.
"""
import argparse
import asyncio
import faulthandler
import json
from pathlib import Path
import shutil
import sys
import tempfile

parser=argparse.ArgumentParser()
parser.add_argument('--core',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.core.resolve()))
from hermes_constants import set_hermes_home_override,reset_hermes_home_override
from hermes_cli.version_info import get_version_info
from hermes_cli.plugins import get_plugin_manager
from hermes_cli.plugins_manifest import parse_manifest_file,requires_hermes_error
from gateway.config import Platform,PlatformConfig
from gateway.platform_registry import platform_registry
from gateway.platforms.base import BasePlatformAdapter

repo=Path(__file__).resolve().parents[3]


async def exercise(home,shadow):
    installed=home/'plugins/hermes-alive'
    shutil.copytree(repo,installed)
    config={'plugins':{'enabled':['hermes-alive'],'entries':{'hermes-alive':{'settings':{
        'kernel_shadow':{'enabled':True,'consent':'model_calls_no_delivery',
                         'subject':'user:synthetic','max_cycles':1}} if shadow else {}}}},
        'gateway':{'platforms':{'telegram':{'enabled':True}}}}
    (home/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    token=set_hermes_home_override(home)
    manager=None
    try:
        manifest=parse_manifest_file(installed/'plugin.yaml',installed,'user','')
        assert manifest is not None and requires_hermes_error(manifest) is None
        manager=get_plugin_manager()
        # Exercise public discovery, not a private _load_plugin call outside its
        # discovery lifecycle. Config reads can re-enter discovery during import;
        # Core's public sweep owns that re-entry guard and load deadline.
        # These are exact candidate bytes, not installed-file repairs. Remote
        # installation and dependency-consent UX remain separate qualification.
        faulthandler.dump_traceback_later(8)
        try:manager.discover_and_load()
        finally:faulthandler.cancel_dump_traceback_later()
        loaded=manager._plugins['hermes-alive']
        assert loaded.enabled and loaded.error is None,loaded.error
        binding=loaded.module._gateway_host_binding
        assert binding.home==home.resolve() and not binding.closed
        assert binding.native is None and binding.task is None
        assert binding.channel_error_class is None
        assert {'post_tool_call','post_gateway_admission'}<=set(loaded.hooks_registered)
        if not shadow:
            assert not binding.channels
            assert (await loaded.module.kernel_gateway_startup())['status']=='not_configured'
        else:
            expected={p.value for p in Platform}|platform_registry.registered_names()
            assert set(binding.channels)==expected and 'telegram' in expected
            # A platform appearing later in the sweep must join the inventory
            # without importing its SDK/loader. This is an explicit synthetic
            # discovery event, not a real platform or a consumer send proof.
            late='alive_synthetic_late_channel'
            def forbidden_loader():raise AssertionError('Alive materialized a deferred adapter')
            platform_registry.register_deferred(late,forbidden_loader,scope=manager.scope_key)
            try:
                manager._notify_plugin_loaded(frozenset())
                assert late in binding.channels and binding.channel_error_class is None
                assert late in platform_registry.pending_names()
            finally:platform_registry.unregister(late,scope=manager.scope_key)
            class Adapter(BasePlatformAdapter):
                def __init__(self):super().__init__(PlatformConfig(),Platform.TELEGRAM)
                async def connect(self,*,is_reconnect=False):
                    self._wire_plugin_handlers(None)
                    self._running=True
                    return True
                async def disconnect(self):self._running=False
                async def send(self,**_):raise AssertionError('registration sent a message')
                async def get_chat_info(self,chat_id):return {'name':'synthetic','type':'dm'}
            adapter=Adapter()
            await adapter.connect()
            handle=binding.channels['telegram']
            assert handle.adapter() is adapter
            assert not handle.status()['recipient_authorized']
        # No startup of the shadow worker: no inference is allowed in this test.
        assert binding.task is None and binding.native is None
        assert manager.unload('hermes-alive')
        assert binding.closed and not binding.channels
        assert binding._unsubscribe_channels is None
        assert not any(r.plugin_key=='hermes-alive' for r in manager._registration_order)
        if shadow:
            assert adapter.is_connected
            try:handle.adapter()
            except ValueError:pass
            else:raise AssertionError('unload retained a live plugin channel handle')
        print('current_core_registration='+('shadow_opt_in' if shadow else 'default')+':PASS')
    finally:
        if manager is not None:manager.unload()
        reset_hermes_home_override(token)


identity=get_version_info()
assert identity.base_version!='unknown','real Core identity required; never inject a version fixture'
with tempfile.TemporaryDirectory(prefix='alive-current-registration-') as directory:
    root=Path(directory)
    for name,shadow in (('default',False),('shadow',True)):
        home=root/name;home.mkdir()
        asyncio.run(exercise(home,shadow))
print('HERMES_ALIVE_CURRENT_CORE_PLUGIN_REGISTRATION_OK')
