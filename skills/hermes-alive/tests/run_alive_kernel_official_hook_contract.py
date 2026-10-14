#!/usr/bin/env python3
"""Load and dispatch the adapter through Hermes' real HookRegistry contract."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile


EXPECTED_EVENTS = {
    "gateway:startup", "session:start", "session:end", "session:reset",
    "agent:start", "agent:step", "agent:end", "command:memory",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed-profile", type=Path,
                        help="Disposable, publicly admitted profile; never a production profile")
    args = parser.parse_args()
    if importlib.util.find_spec("gateway") is None:
        if args.installed_profile is not None:
            raise RuntimeError("installed profile requires a real Hermes runtime")
        print("HERMES_ALIVE_OFFICIAL_HOOK_CONTRACT_SKIPPED=no_hermes_runtime")
        return 0

    skill_root = Path(__file__).resolve().parents[1]
    repo_root = skill_root.parents[1]
    with tempfile.TemporaryDirectory(prefix="alive-official-hook-") as directory:
        root = Path(directory)
        hermes_home = (root / "hermes-home" if args.installed_profile is None
                       else args.installed_profile.resolve(strict=True))
        installed_hook = hermes_home / "hooks" / "hermes-alive"
        installed_plugin = hermes_home / "plugins" / "hermes-alive"
        if args.installed_profile is None:
            shutil.copytree(skill_root / "hooks", installed_hook)
        else:
            # The admission runner owns this disposable profile and invokes this
            # very installed test file using its committed managed interpreter.
            assert Path(os.environ["HERMES_HOME"]).resolve() == hermes_home
            assert repo_root == installed_plugin.resolve(strict=True)
            assert (installed_hook / "handler.py").is_file()
            from importlib.metadata import version
            from packaging.specifiers import SpecifierSet
            assert version("PyYAML") in SpecifierSet(">=6.0.3,<7")
            assert version("tzdata") in SpecifierSet(">=2025.2")
        shared = root / "runtime"
        os.environ["HERMES_HOME"] = str(hermes_home)
        os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
        os.environ["HERMES_ALIVE_KERNEL_SHADOW_ENABLED"] = "true"
        os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "false"
        os.environ["HERMES_BUNDLED_PLUGINS"] = str(hermes_home / "empty-bundled")
        if args.installed_profile is None:
            (hermes_home / "config.yaml").write_text(
                "plugins:\n  enabled: [hermes-alive]\n", encoding="utf-8"
            )

        # Import after profile selection, exactly as a fresh host process does.
        # Missing dependencies are failures, not an absent-runtime skip.
        from gateway.hooks import HookRegistry

        registry = HookRegistry()
        registry.discover_and_load()
        loaded = registry.loaded_hooks
        assert len(loaded) == 1
        assert set(loaded[0]["events"]) == EXPECTED_EVENTS
        assert Path(loaded[0]["path"]).resolve() == installed_hook.resolve()

        context = {
            "platform": "weixin",
            "user_id": "official-user",
            "chat_id": "official-chat",
            "session_id": "official-session",
            "message": "official private message must not persist",
        }

        async def dispatch() -> tuple[list[object], list[object]]:
            await registry.emit("agent:start", dict(context))
            await registry.emit("agent:step", {
                **context, "iteration": 1, "tool_names": ["terminal"],
                "tools": [{"name": "terminal", "arguments": "private", "result": "private"}],
            })
            await registry.emit("session:end", dict(context))
            await registry.emit("session:reset", dict(context))
            alive = await registry.emit_collect("command:memory", {
                "platform": "weixin", "user_id": "official-user",
                "command": "memory", "args": "alive status",
            })
            ordinary = await registry.emit_collect("command:memory", {
                "platform": "weixin", "user_id": "official-user",
                "command": "memory", "args": "pending",
            })
            return alive, ordinary

        alive_results, ordinary_results = asyncio.run(dispatch())
        assert alive_results and alive_results[0]["decision"] == "handled"
        assert ordinary_results == []

        # Discover the package through Hermes' real plugin manager and dispatch
        # its native post_tool_call observer. Copy only distributable material,
        # never the working tree metadata.
        if args.installed_profile is None:
            installed_plugin.mkdir(parents=True)
            for name in ("__init__.py", "plugin_cli.py", "tool_receipt_bridge.py",
                         "admitted_inbound_bridge.py", "plugin.yaml"):
                shutil.copy2(repo_root / name, installed_plugin / name)
            shutil.copytree(
                skill_root, installed_plugin / "skills" / "hermes-alive"
            )
        from hermes_cli.plugins import PluginManager
        manager = PluginManager()
        manager.discover_and_load()
        assert manager.has_hook("post_tool_call")
        manager.invoke_hook(
            "post_tool_call",
            tool_name="terminal",
            args={"command": "official private argument"},
            result="official private result",
            error_message="official private error",
            status="timeout",
            error_type="tool_timeout",
            duration_ms=25,
            task_id="official-task",
            session_id="official-session",
            tool_call_id="official-tool-call",
            turn_id="official-turn",
            api_request_id="official-request",
        )
        manager.unload()

        sys.path.insert(0, str(installed_hook))
        from alive_kernel import ExperienceJournal
        journal = ExperienceJournal(shared / "kernel" / "experience.sqlite3")
        records = journal.read(limit=100)
        assert [record.event.event_type for record in records] == [
            "conversation.inbound", "tool.round_observed", "session.ended", "session.reset",
            "tool.execution_observed",
        ]
        receipt = records[-1].event
        assert receipt.payload["outcome"] == "timed_out"
        assert receipt.payload["learning_eligible"] is True
        database = (shared / "kernel" / "experience.sqlite3").read_bytes()
        wal = shared / "kernel" / "experience.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        assert b"official private message" not in database
        assert b'"arguments":"private"' not in database
        assert b'"result":"private"' not in database
        assert b"official private argument" not in database
        assert b"official private result" not in database
        assert b"official private error" not in database

    print("HERMES_ALIVE_OFFICIAL_HOOK_CONTRACT_OK")
    if args.installed_profile is not None:
        print("HERMES_ALIVE_ADMITTED_HOOK_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
