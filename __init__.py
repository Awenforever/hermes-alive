"""Hermes Alive native plugin registration."""

from __future__ import annotations

from .plugin_cli import alive_command, register_cli
from .tool_receipt_bridge import register_tool_receipt_hook,register_core_work_hook,register_inspection_guard
from .admitted_inbound_bridge import register_admitted_inbound_hook
from .gateway_host_bridge import GatewayHostBinding
from .kernel_setup_bridge import register_setup_command,attach_configured_continuity

_gateway_host_binding=None


def configure_kernel_gateway_host(native,**parameters):
    if _gateway_host_binding is None:
        raise RuntimeError('current plugin instance has not registered')
    _gateway_host_binding.attach(native,**parameters)


async def kernel_gateway_startup():
    if _gateway_host_binding is None:
        raise RuntimeError('current plugin instance has not registered')
    configured=_gateway_host_binding.context.get_config('kernel_setup',{})
    from . import kernel_execution_bridge as execution
    native_installed=execution.runtime_engine(_gateway_host_binding)=='kernel'
    if configured or native_installed:
        root=_gateway_host_binding.home/'plugin-data/hermes-alive/runtime/kernel'
        if not configured and not root.exists():return await _gateway_host_binding.startup()
        attach_configured_continuity(_gateway_host_binding)
    if _gateway_host_binding.native is None and not _gateway_host_binding.closed:
        if configured or native_installed:
            assembled=execution.assemble(_gateway_host_binding)
            if assembled is not None:execution.attach(_gateway_host_binding,assembled)
        else:
            from .tool_receipt_bridge import _kernel_module
            assembled=_kernel_module('core_shadow_assembly').assemble(_gateway_host_binding.context)
            if assembled is not None:
                native,parameters=assembled
                _gateway_host_binding.attach(native,**parameters)
    return await _gateway_host_binding.startup()


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
