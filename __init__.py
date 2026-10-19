"""Hermes Alive v2.5 plugin registration."""

from __future__ import annotations

from .plugin_cli import alive_command, register_cli
from .tool_receipt_bridge import register_tool_receipt_hook
from .admitted_inbound_bridge import register_admitted_inbound_hook
from .gateway_host_bridge import GatewayHostBinding

_gateway_host_binding=None


def configure_kernel_gateway_host(native,**parameters):
    if _gateway_host_binding is None:
        raise RuntimeError('current plugin instance has not registered')
    _gateway_host_binding.attach(native,**parameters)


async def kernel_gateway_startup():
    if _gateway_host_binding is None:
        raise RuntimeError('current plugin instance has not registered')
    return await _gateway_host_binding.startup()


def register(ctx) -> None:
    global _gateway_host_binding
    _gateway_host_binding=GatewayHostBinding(ctx)
    register_tool_receipt_hook(ctx)
    register_admitted_inbound_hook(ctx)
    ctx.register_cli_command(
        name="alive",
        help="Install, inspect, and control Hermes Alive",
        setup_fn=register_cli,
        handler_fn=alive_command,
        description="Production lifecycle controls for proactive Hermes messages.",
    )
