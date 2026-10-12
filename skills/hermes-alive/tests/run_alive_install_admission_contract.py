#!/usr/bin/env python3
"""Injected failure checks for the opt-in admission runner, not install proof."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch


def main() -> int:
    path = Path(__file__).with_name("run_alive_install_admission.py")
    spec = importlib.util.spec_from_file_location("alive_admission_fixture", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    with tempfile.TemporaryDirectory(prefix="alive-admission-contract-") as directory:
        core = Path(directory) / "core"
        (core / "hermes_cli").mkdir(parents=True)
        (core / "hermes_cli" / "main.py").write_text("", encoding="utf-8")
        for failure in ("unloaded", "invalid_json", "wrong_home", "not_ok", "already_enabled"):
            calls = []
            def fake_run(command, **kwargs):
                calls.append(command)
                stdout, code = "", 0
                if "-c" in command:
                    stdout = str(core / "hermes_cli" / "__init__.py") + "\n"
                if command[-1] == "--enable":
                    stdout = "Installed; dependency enablement refused\n"
                if command[-2:] == ["alive", "status"]:
                    state = {"ok": True, "hermes_home": kwargs["env"]["HERMES_HOME"],
                             "hook_installed": False, "enabled": False}
                    if failure == "unloaded":
                        code = 2
                    elif failure == "invalid_json":
                        stdout = "not JSON"
                    else:
                        if failure == "wrong_home":
                            state["hermes_home"] = str(core)
                        if failure == "not_ok":
                            state["ok"] = False
                        if failure == "already_enabled":
                            state["enabled"] = True
                        stdout = json.dumps(state)
                return subprocess.CompletedProcess(command, code, stdout, "fixture refusal")
            output = io.StringIO()
            with patch.object(sys, "argv", [str(path), "--hermes-root", str(core),
                                           "--allow-dependency-install"]), \
                 patch.object(runner.subprocess, "run", side_effect=fake_run), \
                 patch.object(runner.shutil, "copytree"), \
                 redirect_stdout(output), redirect_stderr(output):
                try:
                    runner.main()
                except (RuntimeError, ValueError, AssertionError):
                    pass
                else:
                    raise AssertionError("failed admission was reported as success")
            assert "HERMES_ALIVE_INSTALL_ADMISSION_NOT_READY_NO_RUNTIME_WRITE" in output.getvalue()
            assert not any(command[-1] == "install-runtime" for command in calls)

        # A timed-out installer is neither success nor evidence that its output
        # vanished. Keep the captured failure evidence and stop before hooks.
        calls = []
        def timed_out(command, **kwargs):
            calls.append(command)
            if command[-1] == "--enable":
                raise subprocess.TimeoutExpired(command, 600, output=b"fixture install in progress",
                                                stderr=b"fixture transport interrupted")
            stdout = str(core / "hermes_cli" / "__init__.py") if "-c" in command else ""
            return subprocess.CompletedProcess(command, 0, stdout, "")
        output = io.StringIO()
        with patch.object(sys, "argv", [str(path), "--hermes-root", str(core),
                                       "--allow-dependency-install"]), \
             patch.object(runner.subprocess, "run", side_effect=timed_out), \
             patch.object(runner.shutil, "copytree"), \
             redirect_stdout(output), redirect_stderr(output):
            try:
                runner.main()
            except subprocess.TimeoutExpired:
                pass
            else:
                raise AssertionError("timed-out admission was reported as success")
        assert "HERMES_ALIVE_ADMISSION_STEP_TIMEOUT" in output.getvalue()
        assert "fixture transport interrupted" in output.getvalue()
        assert "fixture install in progress" in output.getvalue()
        assert not any(command[-1] == "install-runtime" for command in calls)
    print("HERMES_ALIVE_INSTALL_ADMISSION_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
