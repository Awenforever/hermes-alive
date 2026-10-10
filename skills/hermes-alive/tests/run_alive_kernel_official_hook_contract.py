#!/usr/bin/env python3
"""Load and dispatch the adapter through Hermes' real HookRegistry contract."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import shutil
import sys
import tempfile


EXPECTED_EVENTS = {
    "gateway:startup", "session:start", "session:end", "session:reset",
    "agent:start", "agent:step", "agent:end",
}


def main() -> int:
    try:
        from gateway.hooks import HookRegistry
    except ImportError:
        print("HERMES_ALIVE_OFFICIAL_HOOK_CONTRACT_SKIPPED=no_hermes_runtime")
        return 0

    skill_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="alive-official-hook-") as directory:
        root = Path(directory)
        hermes_home = root / "hermes-home"
        installed_hook = hermes_home / "hooks" / "hermes-alive"
        shutil.copytree(skill_root / "hooks", installed_hook)
        shared = root / "runtime"
        os.environ["HERMES_HOME"] = str(hermes_home)
        os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
        os.environ["HERMES_ALIVE_KERNEL_SHADOW_ENABLED"] = "true"
        os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "false"

        # gateway.hooks may have been imported before HERMES_HOME was changed;
        # its supported test/runtime override is the module-level HOOKS_DIR.
        import gateway.hooks as hooks_module
        hooks_module.HOOKS_DIR = hermes_home / "hooks"

        registry = HookRegistry()
        registry.discover_and_load()
        loaded = registry.loaded_hooks
        assert len(loaded) == 1
        assert set(loaded[0]["events"]) == EXPECTED_EVENTS

        context = {
            "platform": "weixin",
            "user_id": "official-user",
            "chat_id": "official-chat",
            "session_id": "official-session",
            "message": "official private message must not persist",
        }

        async def dispatch() -> None:
            await registry.emit("agent:start", dict(context))
            await registry.emit("agent:step", {
                **context, "iteration": 1, "tool_names": ["terminal"],
                "tools": [{"name": "terminal", "arguments": "private", "result": "private"}],
            })
            await registry.emit("session:end", dict(context))
            await registry.emit("session:reset", dict(context))

        asyncio.run(dispatch())

        sys.path.insert(0, str(installed_hook))
        from alive_kernel import ExperienceJournal
        journal = ExperienceJournal(shared / "kernel" / "experience.sqlite3")
        records = journal.read(limit=100)
        assert [record.event.event_type for record in records] == [
            "conversation.inbound", "tool.round_observed", "session.ended", "session.reset"
        ]
        database = (shared / "kernel" / "experience.sqlite3").read_bytes()
        wal = shared / "kernel" / "experience.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        assert b"official private message" not in database
        assert b'"arguments":"private"' not in database
        assert b'"result":"private"' not in database

    print("HERMES_ALIVE_OFFICIAL_HOOK_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
