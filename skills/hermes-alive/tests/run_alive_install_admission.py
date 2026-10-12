#!/usr/bin/env python3
"""Opt-in real Hermes package/dependency admission in a disposable profile.

Run only inside a disposable test container/environment. This may download
dependencies into Hermes-managed generations; it never launches a gateway.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-root", type=Path)
    parser.add_argument("--allow-dependency-install", action="store_true")
    args = parser.parse_args()
    if args.hermes_root is None or not args.allow_dependency_install:
        print("HERMES_ALIVE_INSTALL_ADMISSION_SKIPPED=requires_disposable_runtime_and_explicit_consent")
        return 0
    core = args.hermes_root.resolve(strict=True)
    source = Path(__file__).resolve().parents[3]
    if not (core / "hermes_cli" / "main.py").is_file():
        raise ValueError("Hermes source root is required")
    with tempfile.TemporaryDirectory(prefix="alive-install-admission-") as directory:
        root = Path(directory)
        profile = root / "profile"
        package = root / "package"
        shutil.copytree(source, package, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        env = dict(os.environ, HERMES_HOME=str(profile), PYTHONPATH=str(core),
                   PYTHONDONTWRITEBYTECODE="1", HERMES_PROACTIVE_PLATFORM_ENABLED="false")
        # Fail rather than accidentally using a caller's old image checkout.
        def run(command, *, cwd=core):
            # These commands contain only disposable fixture paths and public
            # installation arguments, never credentials or retained user text.
            print("HERMES_ALIVE_ADMISSION_STEP_START=" + json.dumps(command), flush=True)
            try:
                result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                        text=True, timeout=600)
            except subprocess.TimeoutExpired as error:
                for stream in (error.stdout, error.stderr):
                    if stream:
                        text = stream.decode("utf-8", errors="replace") if isinstance(stream, bytes) else stream
                        print(text[-12000:], file=sys.stderr, flush=True)
                print("HERMES_ALIVE_ADMISSION_STEP_TIMEOUT", file=sys.stderr, flush=True)
                raise
            print(result.stdout, end="", flush=True)
            if result.returncode:
                print(result.stderr[-12000:], file=sys.stderr, flush=True)
                raise RuntimeError(f"admission command failed: exit={result.returncode}")
            print("HERMES_ALIVE_ADMISSION_STEP_FINISHED", flush=True)
            return result.stdout
        location = run([sys.executable, "-B", "-c",
                        "import hermes_cli; print(hermes_cli.__file__)"])
        assert str(core / "hermes_cli") in location
        for command in (
            ["git", "init", "--quiet"], ["git", "add", "."],
            ["git", "-c", "user.name=Alive admission fixture", "-c",
             "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "fixture"],
        ):
            run(command, cwd=package)
        cli = [sys.executable, "-B", "-m", "hermes_cli.main"]
        try:
            run(cli + ["plugins", "install", package.as_uri(), "--force", "--yes-deps", "--enable"])
        except RuntimeError:
            assert not (profile / "hooks" / "hermes-alive").exists()
            print("HERMES_ALIVE_INSTALL_ADMISSION_FAILED_CLOSED_OK", flush=True)
            raise
        # Hermes can report package placement with a zero exit status even
        # when dependency admission refuses enablement. A loaded CLI, not a
        # success banner, is the prerequisite for runtime installation.
        try:
            initial_state = json.loads(run(cli + ["alive", "status"]))
            assert initial_state["ok"] is True
            assert initial_state["hermes_home"] == str(profile)
            assert initial_state["hook_installed"] is False
            assert initial_state["enabled"] is False
        except (RuntimeError, ValueError, KeyError, AssertionError):
            assert not (profile / "hooks" / "hermes-alive").exists()
            print("HERMES_ALIVE_INSTALL_ADMISSION_NOT_READY_NO_RUNTIME_WRITE", flush=True)
            raise
        sentinel = profile / "plugin-data" / "hermes-alive" / "runtime" / "admission-fixture.json"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text('{"synthetic_user_state":true}\n', encoding="utf-8")
        expected = sentinel.read_bytes()
        # Ask Hermes for its committed environment. Never resolve dependencies
        # ourselves or assume the bootstrap interpreter is the runtime one.
        managed = json.loads(run([sys.executable, "-B", "-c",
            "import json,sys; from pathlib import Path; "
            "from pm.environments import selected_venv,venv_command; "
            "r=Path(sys.argv[1]); print(json.dumps(venv_command(r,selected_venv(r),['-B'])))",
            str(core)]))
        assert isinstance(managed, list) and managed and all(isinstance(item, str) for item in managed)
        cli = managed + ["-m", "hermes_cli.main"]
        fixture = Path(__file__).with_name("admission_state_fixture.py")
        baseline = root / "durable-state-baseline.json"
        def durable(mode):
            run(managed + [str(fixture), mode, "--profile", str(profile),
                           "--expected", str(baseline)])
        for index in range(2):
            run(cli + ["alive", "install-runtime"])
            assert sentinel.read_bytes() == expected
            assert (profile / "hooks" / "hermes-alive" / "handler.py").is_file()
            durable("create" if index == 0 else "check")
        # Same-revision package refresh is deliberately not called an upgrade
        # from an earlier release. It still must not discard installed state.
        run(cli + ["plugins", "install", package.as_uri(), "--force", "--yes-deps", "--enable"])
        run(cli + ["alive", "install-runtime"])
        durable("check")
        state = json.loads(run(cli + ["alive", "status"]))
        assert state["hook_installed"] is True
        assert state["enabled"] is False
        run(cli + ["alive", "uninstall-runtime"])
        assert not (profile / "hooks" / "hermes-alive").exists()
        assert sentinel.read_bytes() == expected
        run(cli + ["plugins", "remove", "hermes-alive"])
        assert not (profile / "plugins" / "hermes-alive").exists()
        assert sentinel.read_bytes() == expected
        run(cli + ["plugins", "install", package.as_uri(), "--force", "--yes-deps", "--enable"])
        run(cli + ["alive", "install-runtime"])
        assert sentinel.read_bytes() == expected
        assert (profile / "hooks" / "hermes-alive" / "handler.py").is_file()
        durable("check")
    print("HERMES_ALIVE_INSTALL_ADMISSION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
