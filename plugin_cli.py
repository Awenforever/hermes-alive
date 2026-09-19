"""Profile-aware installer and status CLI for Hermes Alive."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _home() -> Path:
    from hermes_constants import get_hermes_home

    return get_hermes_home()


def _source() -> Path:
    return Path(__file__).resolve().parent / "skills" / "hermes-alive"


def _hook_target() -> Path:
    return _home() / "hooks" / "hermes-alive"


def _shared_target() -> Path:
    return _home() / "plugin-data" / "hermes-alive" / "runtime"


def register_cli(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="alive_action")
    actions.add_parser("status", help="Show installation and enablement state")
    actions.add_parser("install-runtime", help="Install or refresh the profile-scoped gateway hook")
    actions.add_parser("enable", help="Enable proactive delivery")
    actions.add_parser("disable", help="Disable proactive delivery")
    parser.set_defaults(func=alive_command)


def _replace_tree(source: Path, target: Path, backup_root: Path) -> str | None:
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name(f".{target.name}.stage")
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(source, stage)
    backup = None
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_root / stamp
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        target.replace(backup_path)
        backup = str(backup_path)
    stage.replace(target)
    return backup


def _install_runtime() -> int:
    source = _source()
    hook_backup = _replace_tree(
        source / "hooks",
        _hook_target(),
        _home() / "plugin-data" / "hermes-alive" / "hook-backups",
    )
    shared = _shared_target()
    shared.mkdir(parents=True, exist_ok=True)
    marker = shared / "install.json"
    marker.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": str(source),
                "hook": str(_hook_target()),
                "installed_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "hook": str(_hook_target()), "backup": hook_backup}))
    return 0


def _enabled_file() -> Path:
    return _shared_target() / "enabled"


def alive_command(args: argparse.Namespace) -> int:
    action = getattr(args, "alive_action", None)
    if action == "install-runtime":
        return _install_runtime()
    if action == "enable":
        _enabled_file().parent.mkdir(parents=True, exist_ok=True)
        _enabled_file().write_text("enabled\n", encoding="utf-8")
        print(json.dumps({"ok": True, "enabled": True, "restart_required": True}))
        return 0
    if action == "disable":
        _enabled_file().unlink(missing_ok=True)
        print(json.dumps({"ok": True, "enabled": False, "restart_required": True}))
        return 0
    if action in {None, "status"}:
        print(
            json.dumps(
                {
                    "ok": True,
                    "hermes_home": str(_home()),
                    "hook_installed": (_hook_target() / "HOOK.yaml").is_file(),
                    "enabled": _enabled_file().is_file(),
                    "state_root": str(_shared_target()),
                },
                indent=2,
            )
        )
        return 0
    print(f"Unknown action: {action}")
    return 2
