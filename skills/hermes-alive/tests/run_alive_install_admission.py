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
            result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                    text=True, timeout=600)
            print(result.stdout, end="", flush=True)
            if result.returncode:
                print(result.stderr[-12000:], file=sys.stderr, flush=True)
                raise RuntimeError(f"admission command failed: exit={result.returncode}")
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
        for _ in range(2):
            run(cli + ["alive", "install-runtime"])
            assert sentinel.read_bytes() == expected
            assert (profile / "hooks" / "hermes-alive" / "handler.py").is_file()
        state = json.loads(run(cli + ["alive", "status"]))
        assert state["hook_installed"] is True
        run(cli + ["alive", "uninstall-runtime"])
        assert not (profile / "hooks" / "hermes-alive").exists()
        assert sentinel.read_bytes() == expected
        run(cli + ["alive", "install-runtime"])
        assert sentinel.read_bytes() == expected
        assert (profile / "hooks" / "hermes-alive" / "handler.py").is_file()
    print("HERMES_ALIVE_INSTALL_ADMISSION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
