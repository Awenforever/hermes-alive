"""Hermes Alive v2.5 plugin registration."""

from __future__ import annotations

from .plugin_cli import alive_command, register_cli


def register(ctx) -> None:
    ctx.register_cli_command(
        name="alive",
        help="Install, inspect, and control Hermes Alive",
        setup_fn=register_cli,
        handler_fn=alive_command,
        description="Production lifecycle controls for proactive Hermes messages.",
    )
