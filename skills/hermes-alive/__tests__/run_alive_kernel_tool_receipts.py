#!/usr/bin/env python3
"""Native plugin receipt registration, privacy and authority contracts."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / "skills" / "hermes-alive" / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import ExperienceJournal, ToolOutcome  # noqa: E402
from alive_kernel import assess_reported_outcome  # noqa: E402


class FakePluginContext:
    def __init__(self) -> None:
        self.hooks: dict[str, object] = {}
        self.cli: dict[str, object] = {}
        self.commands: dict[str, object] = {}
        self._manager=SimpleNamespace(scope_key=str(Path.cwd()))
        self.unload=[]

    def on_unload(self,callback):
        self.unload.append(callback)

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def register_cli_command(self, **values):
        self.cli[str(values["name"])] = values

    def register_command(self,name,handler,*,description,args_hint,argument_mode):
        assert argument_mode=='text' and callable(handler)
        self.commands[name]=handler


def _load_plugin():
    name = "hermes_alive_receipt_contract_plugin"
    spec = importlib.util.spec_from_file_location(
        name, REPO / "__init__.py", submodule_search_locations=[str(REPO)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    assert assess_reported_outcome("ok", None).outcome is ToolOutcome.UNKNOWN
    inferred = assess_reported_outcome("error", "tool_error")
    assert inferred.outcome is ToolOutcome.UNKNOWN and not inferred.learning_eligible
    explicit = {
        ("blocked", "plugin_block"): ToolOutcome.BLOCKED,
        ("cancelled", "keyboard_interrupt"): ToolOutcome.CANCELLED,
        ("timeout", "tool_timeout"): ToolOutcome.TIMED_OUT,
        ("error", "ValueError"): ToolOutcome.FAILED,
    }
    for values, expected in explicit.items():
        decision = assess_reported_outcome(*values)
        assert decision.outcome is expected and decision.learning_eligible

    with tempfile.TemporaryDirectory(prefix="alive-tool-receipt-") as directory:
        shared = Path(directory)
        previous = {
            key: os.environ.get(key)
            for key in (
                "HERMES_ALIVE_SHARED_DIR",
                "HERMES_ALIVE_KERNEL_SHADOW_ENABLED",
            )
        }
        try:
            os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
            os.environ["HERMES_ALIVE_KERNEL_SHADOW_ENABLED"] = "false"
            plugin = _load_plugin()
            context = FakePluginContext()
            plugin.register(context)
            assert set(context.hooks) == {"post_tool_call", "post_gateway_admission"}
            assert set(context.cli) == {"alive"}
            assert set(context.commands)=={'alive'}
            callback = context.hooks["post_tool_call"]
            values = {
                "tool_name": "terminal",
                "task_id": "private-task-id",
                "session_id": "private-session-id",
                "tool_call_id": "private-call-id",
                "turn_id": "private-turn-id",
                "api_request_id": "private-api-id",
                "duration_ms": 42,
                "status": "ok",
                "error_type": None,
                "args": {"command": "private argument sentinel"},
                "result": "private result sentinel",
                "error_message": "private error sentinel",
            }
            callback(**values)
            assert not (shared / "kernel" / "experience.sqlite3").exists()

            os.environ["HERMES_ALIVE_KERNEL_SHADOW_ENABLED"] = "true"
            callback(**values)
            callback(**values)
            journal = ExperienceJournal(shared / "kernel" / "experience.sqlite3")
            records = journal.read(event_type="tool.execution_observed")
            assert len(records) == 1
            event = records[0].event
            assert event.payload["outcome"] == "unknown"
            assert event.payload["learning_eligible"] is False
            assert event.payload["terminal_observed"] is True
            assert event.payload["arguments_stored"] is False
            assert event.payload["result_stored"] is False
            assert event.payload["error_message_stored"] is False
            assert event.payload["identities"]["session_id"].startswith("session:")

            callback(**{
                **values,
                "tool_call_id": "private-call-id-2",
                "status": "timeout",
                "error_type": "tool_timeout",
                "error_message": "private timeout details",
            })
            timeout = journal.read(event_type="tool.execution_observed")[-1].event
            assert timeout.payload["outcome"] == "timed_out"
            assert timeout.payload["learning_eligible"] is True

            raw = (shared / "kernel" / "experience.sqlite3").read_bytes()
            wal = shared / "kernel" / "experience.sqlite3-wal"
            if wal.exists():
                raw += wal.read_bytes()
            for forbidden in (
                b"private-task-id", b"private-session-id", b"private-call-id",
                b"private-turn-id", b"private-api-id", b"private argument sentinel",
                b"private result sentinel", b"private error sentinel",
                b"private timeout details",
            ):
                assert forbidden not in raw
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    print("HERMES_ALIVE_KERNEL_TOOL_RECEIPTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
