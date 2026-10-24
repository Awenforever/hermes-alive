"""Dedicated experimental kernel hook. Never starts the legacy watcher.

Not selected by the legacy lifecycle installer. Host assembly must explicitly
attach the current profile's bounded shadow host or authenticated native host.
The installed engine and current signed authority jointly govern execution.
"""
from pathlib import Path


async def handle(event_type,context):
    if event_type!='gateway:startup':return None
    from hermes_constants import get_hermes_home
    from hermes_cli.plugins import get_plugin_manager
    manager=get_plugin_manager()
    if Path(manager.scope_key).resolve()!=Path(get_hermes_home()).resolve():
        raise RuntimeError('Gateway plugin manager scope mismatch')
    loaded=manager._plugins.get('hermes-alive')
    if loaded is None or not loaded.enabled:
        return {'status':'plugin_unavailable','legacy_allowed':False}
    startup=getattr(loaded.module,'kernel_gateway_startup',None)
    if not callable(startup):
        return {'status':'startup_contract_unavailable','legacy_allowed':False}
    return await startup()
