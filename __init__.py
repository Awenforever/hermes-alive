"""Hermes Alive v2.5 plugin registration."""

from __future__ import annotations

from .plugin_cli import alive_command, register_cli
from .tool_receipt_bridge import register_tool_receipt_hook
from .admitted_inbound_bridge import register_admitted_inbound_hook


def register(ctx) -> None:
    register_tool_receipt_hook(ctx)
    register_admitted_inbound_hook(ctx)
    ctx.register_cli_command(
        name="alive",
        help="Install, inspect, and control Hermes Alive",
        setup_fn=register_cli,
        handler_fn=alive_command,
        description="Production lifecycle controls for proactive Hermes messages.",
    )
