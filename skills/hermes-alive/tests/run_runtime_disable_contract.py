#!/usr/bin/env python3
"""Focused regression for the Hermes Alive runtime enable/disable contract."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
MANAGED_MODULE = HOOKS / "managed_config.py"
LIFECYCLE = ROOT / "scripts/hermes-alive-lifecycle.py"


def load_managed_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MANAGED_MODULE)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load managed_config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_managed_master_switch_authority() -> None:
    with tempfile.TemporaryDirectory(prefix="alive-managed-disable-") as raw:
        shared = Path(raw)
        config = shared / "config/hermes-alive.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {"values": {"enabled": False, "llm_enabled": False}}
            ),
            encoding="utf-8",
        )

        keys = (
            "HERMES_ALIVE_SHARED_DIR",
            "HERMES_PROACTIVE_PLATFORM_ENABLED",
            "HERMES_PROACTIVE_LLM_ENABLED",
        )
        previous = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
            os.environ["HERMES_PROACTIVE_LLM_ENABLED"] = "true"

            module = load_managed_module("managed_disable_contract_false")
            loaded = module.load_managed_env(overwrite=False)

            assert os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] == "false"
            assert loaded["HERMES_PROACTIVE_PLATFORM_ENABLED"] == "false"
            assert os.environ["HERMES_PROACTIVE_LLM_ENABLED"] == "true"
            assert "HERMES_PROACTIVE_LLM_ENABLED" not in loaded

            payload = json.loads(config.read_text(encoding="utf-8"))
            payload["values"]["enabled"] = True
            config.write_text(json.dumps(payload), encoding="utf-8")
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "false"

            module = load_managed_module("managed_disable_contract_true")
            loaded = module.load_managed_env(overwrite=False)

            assert os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] == "true"
            assert loaded["HERMES_PROACTIVE_PLATFORM_ENABLED"] == "true"
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def test_lifecycle_control_sync() -> None:
    with tempfile.TemporaryDirectory(prefix="alive-lifecycle-control-") as raw:
        home = Path(raw)
        fake_cli = home / "hermes"
        fake_cli.write_text(
            """#!/usr/bin/env bash
set -Eeuo pipefail
if [ "${1:-}" = "config" ] && [ "${2:-}" = "path" ]; then
  printf '%s\\n' "${HERMES_HOME}/config.yaml"
  exit 0
fi
if [ "${1:-}" = "setup" ] && [ "${2:-}" = "model" ]; then
  exit 0
fi
exit 2
""",
            encoding="utf-8",
        )
        fake_cli.chmod(0o700)
        (home / "config.yaml").write_text(
            "model: deepseek/runtime-disable-contract-test\n",
            encoding="utf-8",
        )

        # Marker: HERMES_ALIVE_TEST_LIFECYCLE_ENV_ISOLATION_V1
        # The full suite intentionally exports a shared directory for its own
        # tests. This focused subprocess must not inherit that path because its
        # temporary HERMES_HOME is different and lifecycle correctly rejects a
        # shared directory outside that home.
        env = dict(os.environ)
        for key in (
            "HERMES_ALIVE_SHARED_DIR",
            "HERMES_HOOK_DIR",
            "HERMES_HOOKS_DIR",
            "HERMES_ALIVE_ROOT",
        ):
            env.pop(key, None)
        env.update(
            {
                "HOME": str(home),
                "HERMES_HOME": str(home),
                "HERMES_ALIVE_SHARED_DIR": str(
                    home / "hermes_alive_shared"
                ),
                "HERMES_CLI": str(fake_cli),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        common = [
            sys.executable,
            str(LIFECYCLE),
            "configure",
            "--hermes-home",
            str(home),
            "--non-interactive",
            "--skip-weather",
        ]

        enabled = subprocess.run(
            common + ["--enable"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert enabled.returncode == 0, enabled.stdout

        shared = home / "hermes_alive_shared"
        managed = json.loads(
            (shared / "config/hermes-alive.json").read_text(encoding="utf-8")
        )
        control = json.loads(
            (shared / "control.json").read_text(encoding="utf-8")
        )
        assert managed["values"]["enabled"] is True
        assert control["enabled_override"] is True
        assert control["reason"] == "lifecycle configure --enable"

        disabled = subprocess.run(
            common + ["--disable"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert disabled.returncode == 0, disabled.stdout

        managed = json.loads(
            (shared / "config/hermes-alive.json").read_text(encoding="utf-8")
        )
        control = json.loads(
            (shared / "control.json").read_text(encoding="utf-8")
        )
        assert managed["values"]["enabled"] is False
        assert control["enabled_override"] is False
        assert control["reason"] == "lifecycle configure --disable"


def test_real_handler_gate() -> None:
    with tempfile.TemporaryDirectory(prefix="alive-handler-disable-") as raw:
        shared = Path(raw)
        config = shared / "config/hermes-alive.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps({"values": {"enabled": False}}),
            encoding="utf-8",
        )

        code = """
import os
import sys
sys.path.insert(0, os.environ["HERMES_TEST_HOOKS"])
import handler
assert os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] == "false"
assert handler._env_enabled() is False
print("HANDLER_RUNTIME_DISABLE_GATE=PASS")
"""
        env = {
            **os.environ,
            "HERMES_ALIVE_SHARED_DIR": str(shared),
            "HERMES_HOOK_DIR": str(HOOKS),
            "HERMES_TEST_HOOKS": str(HOOKS),
            "HERMES_PROACTIVE_PLATFORM_ENABLED": "true",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        result = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout
        assert "HANDLER_RUNTIME_DISABLE_GATE=PASS" in result.stdout


def main() -> int:
    test_managed_master_switch_authority()
    test_lifecycle_control_sync()
    test_real_handler_gate()
    print("HERMES_ALIVE_RUNTIME_DISABLE_CONTRACT_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
