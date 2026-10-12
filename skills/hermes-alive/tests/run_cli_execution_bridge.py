#!/usr/bin/env python3
"""Ordering/failure isolation; fake capabilities here do not qualify a runtime."""
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.cli_execution import execute_text_cli_once
from alive_kernel.cli_send_contract import CliSendContractError
from alive_kernel.events import Sensitivity


def main():
    with tempfile.TemporaryDirectory(prefix="alive-cli-bridge-") as directory:
        home = Path(directory).resolve()
        for mode in ("success", "compile_failure", "launch_failure", "guard_failure", "write_failure"):
            trace = []
            body = "MEDIA:/reserved.pdf" if mode == "compile_failure" else "synthetic body"
            execution = SimpleNamespace(
                content={"schema_version": 1, "capability": "hermes.channel.send",
                         "operation": {"text": body, "format": "markdown"}},
                route={"platform": "test", "profile": "fixture", "chat_id": "chat", "thread_id": None})
            class LocalOutbox:
                def begin_execution(self, lease, **kwargs):
                    trace.append("begin")
                    return execution
                def validate_execution_for_launch(self, value, **kwargs):
                    assert value is execution
                    trace.append("guard")
                    if mode == "guard_failure":
                        raise RuntimeError("synthetic revocation")
                def record_cli_observation(self, value, **kwargs):
                    assert value is execution and kwargs["stdout"] == '{"success":true}'
                    trace.append("observe")
                    if mode == "write_failure":
                        raise RuntimeError("synthetic journal failure after possible effect")
                    return SimpleNamespace(event_id="synthetic observation")
            def launch(plan):
                trace.append("launch")
                assert plan.stdin_text == body
                if mode == "launch_failure":
                    raise TimeoutError("synthetic process timeout after possible effect")
                return '{"success":true}', 0
            try:
                result = execute_text_cli_once(
                    LocalOutbox(), object(), clearance=Sensitivity.RESTRICTED,
                    profile_id="fixture", hermes_home=home,
                    resolve_target=lambda p, r: (r, None, None),
                    extract_media=lambda text: ([], text), observe_profile_home=lambda: home,
                    launch=launch)
            except (CliSendContractError, RuntimeError, TimeoutError):
                assert mode != "success"
            else:
                assert mode == "success" and result.execution is execution
                assert body not in repr(result)
            assert trace == {
                "success": ["begin", "guard", "launch", "observe"],
                "compile_failure": ["begin"],
                "launch_failure": ["begin", "guard", "launch"],
                "guard_failure": ["begin", "guard"],
                "write_failure": ["begin", "guard", "launch", "observe"],
            }[mode]
    print("HERMES_ALIVE_CLI_EXECUTION_BRIDGE_OK")


if __name__ == "__main__":
    main()
