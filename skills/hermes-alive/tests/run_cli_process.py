#!/usr/bin/env python3
"""Actual synthetic child execution, not installed Hermes or delivery qualification."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.cli_process import CliProcessUncertain, OperatorCliProcess
from alive_kernel.cli_send_contract import compile_text_cli_plan


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    script = Path(__file__).resolve().parent / "fixtures" / "cli-process-fixture.py"
    executable = Path(sys.executable).resolve()
    with tempfile.TemporaryDirectory(prefix="alive-process-") as directory:
        home = Path(directory).resolve()
        body = "合成正文\n\n第二段"
        plan = compile_text_cli_plan(
            {"schema_version": 1, "capability": "hermes.channel.send",
             "operation": {"text": body, "format": "markdown"}},
            {"platform": "test", "profile": "fixture", "chat_id": "chat", "thread_id": None},
            profile_id="fixture", hermes_home=home, observe_profile_home=lambda: home,
            extract_media=lambda text: ([], text), resolve_target=lambda p, r: (r, None, None))
        environment = {k: v for k, v in os.environ.items()
                       if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}}
        environment.update(HERMES_HOME=str(home), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        pins = {executable: digest(executable), script: digest(script)}
        launcher = OperatorCliProcess((str(executable), "-B", str(script), "success"),
                                      home, "fixture", home, environment, pins, 5)
        assert body not in repr(launcher) and str(home) not in repr(launcher)
        # Copies, not references to mutable caller configuration.
        environment["HERMES_HOME"] = "other"
        pins[script] = "0" * 64
        stdout, code = launcher(plan)
        assert code == 0 and json.loads(stdout)["body"] == body
        for mode in ("timeout", "overflow", "invalid_utf8"):
            limited = replace(launcher, prefix=(*launcher.prefix[:-1], mode), timeout_seconds=0.2 if mode == "timeout" else 5)
            try:
                limited(plan)
            except CliProcessUncertain:
                pass
            else:
                raise AssertionError("ambiguous process produced a normal observation")
        for changed_launcher, changed_plan in (
            (launcher, replace(plan, profile_id="other")),
            (launcher, replace(plan, arguments=("config", "set", "other"))),
            (replace(launcher, artifact_pins={**dict(launcher.artifact_pins), script: "0" * 64}), plan),
        ):
            try:
                changed_launcher(changed_plan)
            except ValueError:
                pass
            else:
                raise AssertionError("changed binding launched")
        try:
            replace(launcher, environment={**dict(launcher.environment), "hermes_home": "other"})
        except ValueError:
            pass
        else:
            raise AssertionError("ambiguous Windows environment was accepted")
    print("HERMES_ALIVE_CLI_PROCESS_OK")


if __name__ == "__main__":
    main()
