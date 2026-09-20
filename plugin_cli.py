"""Profile-aware installer and status CLI for Hermes Alive."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
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


def _config_file() -> Path:
    return _shared_target() / "config" / "hermes-alive.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _read_config() -> dict:
    try:
        value = json.loads(_config_file().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _set_enabled(enabled: bool) -> None:
    config = _read_config()
    values = config.get("values") if isinstance(config.get("values"), dict) else {}
    values["enabled"] = enabled
    config["values"] = values
    config.setdefault("schema_version", 1)
    _atomic_write(
        _config_file(),
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _atomic_write(_enabled_file(), "true\n" if enabled else "false\n")


def _effective_enabled() -> bool:
    marker = _enabled_file()
    if marker.is_file():
        try:
            return marker.read_text(encoding="utf-8").strip().lower() in {
                "1", "true", "yes", "on", "enabled",
            }
        except OSError:
            return False
    values = _read_config().get("values")
    return bool(values.get("enabled", False)) if isinstance(values, dict) else False


def alive_command(args: argparse.Namespace) -> int:
    action = getattr(args, "alive_action", None)
    if action == "install-runtime":
        return _install_runtime()
    if action == "enable":
        _set_enabled(True)
        print(json.dumps({"ok": True, "enabled": True, "restart_required": True}))
        return 0
    if action == "disable":
        _set_enabled(False)
        print(json.dumps({"ok": True, "enabled": False, "restart_required": True}))
        return 0
    if action in {None, "status"}:
        print(
            json.dumps(
                {
                    "ok": True,
                    "hermes_home": str(_home()),
                    "hook_installed": (_hook_target() / "HOOK.yaml").is_file(),
                    "enabled": _effective_enabled(),
                    "state_root": str(_shared_target()),
                },
                indent=2,
            )
        )
        return 0
    print(f"Unknown action: {action}")
    return 2
