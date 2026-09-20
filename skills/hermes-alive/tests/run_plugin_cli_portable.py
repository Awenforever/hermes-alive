#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import types
from argparse import Namespace
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "plugin_cli.py"


def command(module, action: str) -> dict:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = module.alive_command(Namespace(alive_action=action))
    assert rc == 0
    return json.loads(output.getvalue())


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-plugin-cli-") as raw:
        home = Path(raw) / "profile"
        constants = types.ModuleType("hermes_constants")
        constants.get_hermes_home = lambda: home
        sys.modules["hermes_constants"] = constants
        spec = importlib.util.spec_from_file_location("alive_plugin_cli_test", CLI)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert command(module, "enable")["enabled"] is True
        state = home / "plugin-data" / "hermes-alive" / "runtime"
        assert (state / "enabled").read_text(encoding="utf-8") == "true\n"
        config = json.loads((state / "config/hermes-alive.json").read_text(encoding="utf-8"))
        assert config["values"]["enabled"] is True
        assert command(module, "status")["enabled"] is True

        assert command(module, "disable")["enabled"] is False
        assert (state / "enabled").read_text(encoding="utf-8") == "false\n"
        config = json.loads((state / "config/hermes-alive.json").read_text(encoding="utf-8"))
        assert config["values"]["enabled"] is False
        assert command(module, "status")["enabled"] is False

        installed = command(module, "install-runtime")
        hook = home / "hooks" / "hermes-alive"
        assert Path(installed["hook"]) == hook
        assert (hook / "HOOK.yaml").is_file()
        assert (hook / "proactive_watcher.py").is_file()

    print("HERMES_ALIVE_PLUGIN_CLI_PORTABLE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
