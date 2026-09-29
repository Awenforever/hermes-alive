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
        control = json.loads((state / "control.json").read_text(encoding="utf-8"))
        assert control["enabled_override"] is True
        assert command(module, "status")["enabled"] is True

        assert command(module, "disable")["enabled"] is False
        assert (state / "enabled").read_text(encoding="utf-8") == "false\n"
        config = json.loads((state / "config/hermes-alive.json").read_text(encoding="utf-8"))
        assert config["values"]["enabled"] is False
        control = json.loads((state / "control.json").read_text(encoding="utf-8"))
        assert control["enabled_override"] is False
        assert command(module, "status")["enabled"] is False

        installed = command(module, "install-runtime")
        hook = home / "hooks" / "hermes-alive"
        assert Path(installed["hook"]) == hook
        assert (hook / "HOOK.yaml").is_file()
        assert (hook / "proactive_watcher.py").is_file()
        assert Path(installed["source"]) == home / "skills" / "hermes-alive"
        assert Path(installed["manifest"]).is_file()
        manifest = json.loads(Path(installed["manifest"]).read_text(encoding="utf-8"))
        assert manifest["manifest_version"] == 1
        assert manifest["hook_hashes"]

        state_marker = state / "preferences" / "keep.json"
        state_marker.parent.mkdir(parents=True, exist_ok=True)
        state_marker.write_text('{"preserved": true}\n', encoding="utf-8")
        removed = command(module, "uninstall-runtime")
        assert removed["hook_removed"] is True
        assert removed["runtime_source_removed"] is True
        assert removed["user_state_preserved"] is True
        assert state_marker.read_text(encoding="utf-8") == '{"preserved": true}\n'
        assert (state / "config" / "hermes-alive.json").is_file()

    print("HERMES_ALIVE_PLUGIN_CLI_PORTABLE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
