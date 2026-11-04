"""Hermes Alive native plugin registration."""

from __future__ import annotations

import asyncio
import logging

from .plugin_cli import alive_command, register_cli
from .tool_receipt_bridge import register_tool_receipt_hook,register_core_work_hook,register_inspection_guard
from .admitted_inbound_bridge import register_admitted_inbound_hook
from .gateway_host_bridge import GatewayHostBinding
from .kernel_setup_bridge import register_setup_command,attach_configured_continuity

_gateway_host_binding=None
_STARTUP_CHANNEL_RETRY_SECONDS = 5


def configure_kernel_gateway_host(native,**parameters):
    if _gateway_host_binding is None:
        raise RuntimeError('current plugin instance has not registered')
    _gateway_host_binding.attach(native,**parameters)


async def kernel_gateway_startup():
    binding = _gateway_host_binding
    if binding is None:
        raise RuntimeError('current plugin instance has not registered')
    from .gateway_channel_bridge import ChannelCapabilityUnavailable
    from .gateway_session_bridge import ReceivingAdapterUnavailable
    from .kernel_setup_bridge import setup_store
    unavailable = (ChannelCapabilityUnavailable, ReceivingAdapterUnavailable)
    async with binding.control_lock:
        if binding.startup_recovery is not None and not binding.startup_recovery.done():
            return binding.runtime_status()
        try:
            return await _start_kernel_gateway(binding)
        except unavailable:
            store = setup_store(binding)
            configured, active = store.configuration(), store.activation()
            if configured is None or binding.closed or binding.started or binding.startup_recovery is not None:
                raise

        async def wait_for_owner_channel():
            # Core owns reconnection. This task only waits for publication of
            # the already authorized route, within one startup recovery window.
            try:
                async with asyncio.timeout(600):
                    while True:
                        await asyncio.sleep(_STARTUP_CHANNEL_RETRY_SECONDS)
                        async with binding.control_lock:
                            if (binding.closed or binding.started or store.configuration() != configured
                                    or store.activation() != active):
                                return
                            try:
                                await _start_kernel_gateway(binding)
                            except unavailable:
                                continue
                            return
            except TimeoutError:
                logging.getLogger(__name__).warning('Alive startup recovery timed out awaiting the owner channel')
            except Exception as error:
                logging.getLogger(__name__).warning('Alive startup recovery stopped: %s', type(error).__name__)

        binding.startup_recovery = binding.context.spawn_task(
            wait_for_owner_channel(), name='hermes-alive-startup-recovery')
        return binding.runtime_status()


async def _start_kernel_gateway(binding):
    if binding.closed:
        return await binding.startup()
    configured=binding.context.get_config('kernel_setup',{})
    from . import kernel_execution_bridge as execution
    native_installed=execution.runtime_engine(binding)=='kernel'
    if configured or native_installed:
        root=binding.home/'plugin-data/hermes-alive/runtime/kernel'
        if not configured and not root.exists():return await binding.startup()
        attach_configured_continuity(binding)
    if binding.native is None and not binding.closed:
        if configured or native_installed:
            assembled=execution.assemble(binding)
            if assembled is not None:execution.attach(binding,assembled)
        else:
            from .tool_receipt_bridge import _kernel_module
            assembled=_kernel_module('core_shadow_assembly').assemble(binding.context)
            if assembled is not None:
                native,parameters=assembled
                binding.attach(native,**parameters)
    return await binding.startup()


def register(ctx) -> None:
    global _gateway_host_binding
    from .core_work_inspection_scope import register as register_inspection_scope
    register_inspection_scope(ctx)
    _gateway_host_binding=GatewayHostBinding(ctx)
    register_setup_command(ctx,_gateway_host_binding)
    register_tool_receipt_hook(ctx,_gateway_host_binding)
    register_core_work_hook(ctx,_gateway_host_binding)
    register_inspection_guard(ctx,_gateway_host_binding)
    register_admitted_inbound_hook(ctx,_gateway_host_binding)
    ctx.register_cli_command(
        name="alive",
        help="Install, inspect, and control Hermes Alive",
        setup_fn=register_cli,
        handler_fn=alive_command,
        description="Production lifecycle controls for proactive Hermes messages.",
    )
