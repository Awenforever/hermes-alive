#!/usr/bin/env python3
"""Hermes Alive lifecycle productization CLI.

Marker: HERMES_ALIVE_LIFECYCLE_V1
Marker: HERMES_ALIVE_ATOMIC_INSTALL_V1
Marker: HERMES_ALIVE_MANAGED_CONFIG_V1
Marker: HERMES_ALIVE_CLEAN_UNINSTALL_V1
Marker: HERMES_ALIVE_GITHUB_SELF_INSTALL_V1
Marker: HERMES_ALIVE_LIFECYCLE_PERMISSION_HARDENING_V1
Marker: HERMES_ALIVE_RUNTIME_PERMISSION_PRESERVATION_V1
Marker: HERMES_ALIVE_INSTALL_TRANSACTION_ROLLBACK_V1
Marker: HERMES_ALIVE_CIRCADIAN_MANAGED_CONFIG_V1
Marker: HERMES_ALIVE_ZERO_TOUCH_ONBOARDING_V1
Marker: HERMES_ALIVE_QUALITY_MANAGED_CONFIG_V2
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except Exception:  # pragma: no cover - Hermes normally ships PyYAML
    yaml = None

SKILL_NAME = "hermes-alive"
HOOK_NAME = "hermes-alive"
MANIFEST_VERSION = 1
CONFIG_VERSION = 4

MANAGED_ENV_KEYS = {
    "enabled": "HERMES_PROACTIVE_PLATFORM_ENABLED",
    "weixin_chat_id": "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
    "timezone": "TZ",
    "quiet_start": "HERMES_PROACTIVE_QUIET_START",
    "quiet_end": "HERMES_PROACTIVE_QUIET_END",
    "cooldown_minutes": "HERMES_PROACTIVE_COOLDOWN_MINUTES",
    "platform_interval_seconds": "HERMES_PROACTIVE_PLATFORM_INTERVAL_SECONDS",
    "llm_enabled": "HERMES_PROACTIVE_LLM_ENABLED",
    "llm_model": "HERMES_PROACTIVE_LLM_MODEL",
    "llm_fallback_model": "HERMES_PROACTIVE_LLM_FALLBACK_MODEL",
    "discovery_enabled": "HERMES_PROACTIVE_DISCOVERY_ENABLED",
    "discovery_interval_seconds": "HERMES_PROACTIVE_DISCOVERY_INTERVAL_SECONDS",
    "dream_enabled": "HERMES_DREAM_ENABLED",
    "dream_interval_hours": "HERMES_DREAM_INTERVAL_HOURS",
    "weather_enabled": "HERMES_PROACTIVE_WEATHER_ENABLED",
    "weather_lat": "HERMES_PROACTIVE_LAT",
    "weather_lon": "HERMES_PROACTIVE_LON",
    "weather_location_name": "HERMES_PROACTIVE_WEATHER_LOCATION_NAME",
    "weather_country_code": "HERMES_PROACTIVE_WEATHER_COUNTRY_CODE",
    "weather_admin1": "HERMES_PROACTIVE_WEATHER_ADMIN1",
    "weather_admin2": "HERMES_PROACTIVE_WEATHER_ADMIN2",
    "weather_admin3": "HERMES_PROACTIVE_WEATHER_ADMIN3",
    "weather_timezone": "HERMES_PROACTIVE_WEATHER_TIMEZONE",
    "weather_location_confirmed": "HERMES_PROACTIVE_WEATHER_LOCATION_CONFIRMED",
    "weather_location_source": "HERMES_PROACTIVE_WEATHER_LOCATION_SOURCE",
    "weather_location_precision": "HERMES_PROACTIVE_WEATHER_LOCATION_PRECISION",
    "emoji_policy": "HERMES_ALIVE_EMOJI_POLICY",
    "circadian_enabled": "HERMES_ALIVE_CIRCADIAN_ENABLED",
    "circadian_mode": "HERMES_ALIVE_CIRCADIAN_MODE",
    "chronotype": "HERMES_ALIVE_CIRCADIAN_CHRONOTYPE",
    "circadian_timezone": "HERMES_ALIVE_CIRCADIAN_TIMEZONE",
    "base_sleep_time": "HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME",
    "base_wake_time": "HERMES_ALIVE_CIRCADIAN_BASE_WAKE_TIME",
    "learned_sleep_offset_minutes": "HERMES_ALIVE_CIRCADIAN_LEARNED_SLEEP_OFFSET_MINUTES",
    "learned_wake_offset_minutes": "HERMES_ALIVE_CIRCADIAN_LEARNED_WAKE_OFFSET_MINUTES",
    "normal_sleep_earliest": "HERMES_ALIVE_CIRCADIAN_NORMAL_SLEEP_EARLIEST",
    "normal_sleep_latest": "HERMES_ALIVE_CIRCADIAN_NORMAL_SLEEP_LATEST",
    "exceptional_sleep_latest": "HERMES_ALIVE_CIRCADIAN_EXCEPTIONAL_SLEEP_LATEST",
    "normal_wake_earliest": "HERMES_ALIVE_CIRCADIAN_NORMAL_WAKE_EARLIEST",
    "normal_wake_latest": "HERMES_ALIVE_CIRCADIAN_NORMAL_WAKE_LATEST",
    "ideal_sleep_minutes": "HERMES_ALIVE_CIRCADIAN_IDEAL_SLEEP_MINUTES",
    "minimum_sleep_minutes": "HERMES_ALIVE_CIRCADIAN_MINIMUM_SLEEP_MINUTES",
    "deep_sleep_core_minutes": "HERMES_ALIVE_CIRCADIAN_DEEP_SLEEP_CORE_MINUTES",
    "daily_sleep_variance_minutes": "HERMES_ALIVE_CIRCADIAN_DAILY_SLEEP_VARIANCE_MINUTES",
    "daily_wake_variance_minutes": "HERMES_ALIVE_CIRCADIAN_DAILY_WAKE_VARIANCE_MINUTES",
    "max_learning_minutes_per_day": "HERMES_ALIVE_CIRCADIAN_MAX_LEARNING_MINUTES_PER_DAY",
    "max_learning_minutes_per_week": "HERMES_ALIVE_CIRCADIAN_MAX_LEARNING_MINUTES_PER_WEEK",
    "explicit_user_preference_weight": "HERMES_ALIVE_CIRCADIAN_EXPLICIT_USER_PREFERENCE_WEIGHT",
    "repeated_interaction_weight": "HERMES_ALIVE_CIRCADIAN_REPEATED_INTERACTION_WEIGHT",
    "single_late_interaction_weight": "HERMES_ALIVE_CIRCADIAN_SINGLE_LATE_INTERACTION_WEIGHT",
    "learned_offset_decay_enabled": "HERMES_ALIVE_CIRCADIAN_LEARNED_OFFSET_DECAY_ENABLED",
    "learned_offset_decay_minutes_per_week": "HERMES_ALIVE_CIRCADIAN_LEARNED_OFFSET_DECAY_MINUTES_PER_WEEK",
    "user_can_delay_sleep": "HERMES_ALIVE_CIRCADIAN_USER_CAN_DELAY_SLEEP",
    "max_user_delay_minutes": "HERMES_ALIVE_CIRCADIAN_MAX_USER_DELAY_MINUTES",
    "user_can_wake_early": "HERMES_ALIVE_CIRCADIAN_USER_CAN_WAKE_EARLY",
    "sleep_transition_message_probability": "HERMES_ALIVE_CIRCADIAN_SLEEP_TRANSITION_MESSAGE_PROBABILITY",
    "wake_transition_message_probability": "HERMES_ALIVE_CIRCADIAN_WAKE_TRANSITION_MESSAGE_PROBABILITY",
    "sleep_debt_recovery_enabled": "HERMES_ALIVE_CIRCADIAN_SLEEP_DEBT_RECOVERY_ENABLED",
}

CIRCADIAN_DEFAULT_VALUES: dict[str, Any] = {
    "circadian_enabled": True,
    "circadian_mode": "shadow",
    "chronotype": "adaptive",
    "base_sleep_time": "23:00",
    "base_wake_time": "07:00",
    "learned_sleep_offset_minutes": 0,
    "learned_wake_offset_minutes": 0,
    "normal_sleep_earliest": "22:00",
    "normal_sleep_latest": "01:30",
    "exceptional_sleep_latest": "03:00",
    "normal_wake_earliest": "06:00",
    "normal_wake_latest": "09:30",
    "ideal_sleep_minutes": 480,
    "minimum_sleep_minutes": 360,
    "deep_sleep_core_minutes": 180,
    "daily_sleep_variance_minutes": 30,
    "daily_wake_variance_minutes": 35,
    "max_learning_minutes_per_day": 10,
    "max_learning_minutes_per_week": 40,
    "explicit_user_preference_weight": 1.0,
    "repeated_interaction_weight": 0.35,
    "single_late_interaction_weight": 0.05,
    "learned_offset_decay_enabled": True,
    "learned_offset_decay_minutes_per_week": 5,
    "user_can_delay_sleep": True,
    "max_user_delay_minutes": 150,
    "user_can_wake_early": True,
    "sleep_transition_message_probability": 0.45,
    "wake_transition_message_probability": 0.30,
    "sleep_debt_recovery_enabled": True,
}

SECRET_NAME_TOKENS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "COOKIE",
)


class LifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    hermes_home: Path
    source_root: Path
    source_target: Path
    hook_target: Path
    shared_dir: Path
    config_file: Path
    manifest_file: Path
    install_dir: Path
    backup_dir: Path
    hub_lock_file: Path


def _now_tag() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime())


def _safe_resolve(path: Path) -> Path:
    return path.expanduser().resolve()


def _must_be_under(path: Path, root: Path, label: str) -> None:
    resolved = _safe_resolve(path)
    root_resolved = _safe_resolve(root)
    if resolved == root_resolved or not resolved.is_relative_to(root_resolved):
        raise LifecycleError(
            f"Unsafe {label}: {resolved} is not a child of {root_resolved}"
        )


def _paths(args: argparse.Namespace) -> Paths:
    source_root = _safe_resolve(
        Path(args.source_root)
        if getattr(args, "source_root", None)
        else Path(__file__).resolve().parents[1]
    )
    hermes_home = _safe_resolve(
        Path(
            getattr(args, "hermes_home", None)
            or os.getenv("HERMES_HOME", "/opt/data")
        )
    )
    source_target = _safe_resolve(
        Path(
            getattr(args, "source_target", None)
            or hermes_home / "skills" / "hermes" / SKILL_NAME
        )
    )
    hook_target = _safe_resolve(
        Path(
            getattr(args, "hook_target", None)
            or hermes_home / "hooks" / HOOK_NAME
        )
    )
    shared_dir = _safe_resolve(
        Path(
            getattr(args, "shared_dir", None)
            or os.getenv(
                "HERMES_ALIVE_SHARED_DIR",
                str(hermes_home / "hermes_alive_shared"),
            )
        )
    )

    _must_be_under(source_target, hermes_home / "skills", "source target")
    _must_be_under(hook_target, hermes_home / "hooks", "hook target")
    _must_be_under(shared_dir, hermes_home, "shared directory")

    install_dir = shared_dir / "install"
    return Paths(
        hermes_home=hermes_home,
        source_root=source_root,
        source_target=source_target,
        hook_target=hook_target,
        shared_dir=shared_dir,
        config_file=shared_dir / "config" / "hermes-alive.json",
        manifest_file=install_dir / "manifest.json",
        install_dir=install_dir,
        backup_dir=install_dir / "backups",
        hub_lock_file=hermes_home / "skills" / ".hub" / "lock.json",
    )


def _ensure_directory(path: Path, mode: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)


def _atomic_write_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    _ensure_directory(path.parent, 0o700)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _iter_tree_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        yield path


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _hash_file(path)
        for path in _iter_tree_files(root)
    }


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        source,
        destination,
        symlinks=False,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    _normalize_permissions(destination)


def _normalize_permissions(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise LifecycleError(f"Symlink is not allowed: {path}")
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            mode = 0o755 if path.parent.name == "scripts" and path.suffix in {"", ".sh", ".py"} else 0o644
            path.chmod(mode)
    root.chmod(0o755)


def _compile_tree(root: Path) -> int:
    count = 0
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        compile(
            path.read_text(encoding="utf-8", errors="strict"),
            str(path),
            "exec",
        )
        count += 1
    return count


def _validate_source_tree(source_root: Path) -> dict[str, Any]:
    required = [
        source_root / "SKILL.md",
        source_root / "hooks" / "HOOK.yaml",
        source_root / "hooks" / "handler.py",
        source_root / "scripts" / "hermes-alive-lifecycle.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise LifecycleError("Missing required source files: " + ", ".join(missing))

    hook_files = sorted(
        path.name
        for path in (source_root / "hooks").glob("*.py")
        if path.name != "__init__.py"
    )
    if not hook_files:
        raise LifecycleError("No hook Python modules found")

    compile_count = _compile_tree(source_root)
    hook_yaml = (source_root / "hooks" / "HOOK.yaml").read_text(
        encoding="utf-8",
        errors="strict",
    )
    for event in ("gateway:startup", "session:start", "agent:end"):
        if event not in hook_yaml:
            raise LifecycleError(f"HOOK.yaml missing event: {event}")

    return {
        "hook_python_files": hook_files,
        "compile_count": compile_count,
        "source_hashes": _tree_manifest(source_root),
    }


def _swap_directory(stage: Path, target: Path, rollback_dir: Path) -> Path | None:
    _ensure_directory(target.parent, 0o755)
    previous: Path | None = None
    if target.exists():
        _ensure_directory(rollback_dir, 0o700)
        previous = rollback_dir / f"{target.name}.previous"
        if previous.exists():
            shutil.rmtree(previous)
        os.replace(target, previous)
    try:
        os.replace(stage, target)
    except Exception:
        if previous is not None and previous.exists() and not target.exists():
            os.replace(previous, target)
        raise
    return previous


def _detect_source_owner(paths: Paths) -> str:
    lock = _read_json(paths.hub_lock_file, {})
    installed = lock.get("installed", {}) if isinstance(lock, dict) else {}
    entry = installed.get(SKILL_NAME) if isinstance(installed, dict) else None
    if isinstance(entry, dict):
        install_path = str(entry.get("install_path") or "")
        expected = str(paths.source_target.relative_to(paths.hermes_home / "skills"))
        if install_path == expected:
            return "hub"
    return "lifecycle"


def _write_manifest(
    paths: Paths,
    *,
    source_owner: str,
    source_hashes: dict[str, str],
    hook_hashes: dict[str, str],
    backup_tag: str,
) -> dict[str, Any]:
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "skill_name": SKILL_NAME,
        "installed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_owner": source_owner,
        "source_root": str(paths.source_target),
        "active_hook": str(paths.hook_target),
        "shared_dir": str(paths.shared_dir),
        "managed_config": str(paths.config_file),
        "backup_tag": backup_tag,
        "source_hashes": source_hashes,
        "hook_hashes": hook_hashes,
    }
    _atomic_write_json(paths.manifest_file, payload)
    return payload


def install(args: argparse.Namespace) -> int:
    paths = _paths(args)
    validation = _validate_source_tree(paths.source_root)
    # Normalize lifecycle-created Hermes directory parents even under umask 000.
    _ensure_directory(paths.hermes_home / "skills", 0o755)
    _ensure_directory(paths.source_target.parent, 0o755)
    _ensure_directory(paths.hermes_home / "hooks", 0o755)
    _ensure_directory(paths.shared_dir, 0o755)
    _ensure_directory(paths.install_dir, 0o700)
    _ensure_directory(paths.backup_dir, 0o700)

    # Do not recursively chmod persisted runtime/learning state. Only normalize
    # lifecycle-owned directory roots created for installation metadata.

    tag = _now_tag()
    source_stage = paths.source_target.parent / f".{SKILL_NAME}.stage-{tag}-{os.getpid()}"
    hook_stage = paths.hook_target.parent / f".{HOOK_NAME}.stage-{tag}-{os.getpid()}"
    rollback_root = paths.backup_dir / tag
    _ensure_directory(rollback_root, 0o700)

    source_owner_before = _detect_source_owner(paths)
    copied_source = paths.source_root != paths.source_target

    source_previous: Path | None = None
    hook_previous: Path | None = None
    source_activated = False
    hook_activated = False

    try:
        if copied_source:
            _copy_tree(paths.source_root, source_stage)
            _validate_source_tree(source_stage)
            source_previous = _swap_directory(
                source_stage,
                paths.source_target,
                rollback_root / "source",
            )
            source_activated = True
        else:
            _normalize_permissions(paths.source_target)

        authoritative_source = paths.source_target
        _copy_tree(authoritative_source / "hooks", hook_stage)
        _compile_tree(hook_stage)
        hook_previous = _swap_directory(
            hook_stage,
            paths.hook_target,
            rollback_root / "hook",
        )
        hook_activated = True

        safe_io = paths.hook_target / "safe_io.py"
        if safe_io.is_file():
            shutil.copy2(safe_io, paths.shared_dir / "safe_io.py")
            os.chmod(paths.shared_dir / "safe_io.py", 0o644)

        template_sources = authoritative_source / "templates" / "sources.yaml"
        target_sources = paths.shared_dir / "sources.yaml"
        if template_sources.is_file() and not target_sources.exists():
            shutil.copy2(template_sources, target_sources)
            os.chmod(target_sources, 0o644)

        source_owner = "lifecycle" if copied_source else source_owner_before
        source_hashes = _tree_manifest(authoritative_source)
        hook_hashes = _tree_manifest(paths.hook_target)
        manifest = _write_manifest(
            paths,
            source_owner=source_owner,
            source_hashes=source_hashes,
            hook_hashes=hook_hashes,
            backup_tag=tag,
        )
        _prune_backups(paths.backup_dir, keep=5)
    except Exception:
        # Restore the previous working source/hook if any post-activation step
        # fails, including manifest/config/template persistence.
        if hook_activated:
            if paths.hook_target.exists():
                shutil.rmtree(paths.hook_target, ignore_errors=True)
            if hook_previous is not None and hook_previous.exists():
                os.replace(hook_previous, paths.hook_target)
        if source_activated:
            if paths.source_target.exists():
                shutil.rmtree(paths.source_target, ignore_errors=True)
            if source_previous is not None and source_previous.exists():
                os.replace(source_previous, paths.source_target)
        raise
    finally:
        if source_stage.exists():
            shutil.rmtree(source_stage, ignore_errors=True)
        if hook_stage.exists():
            shutil.rmtree(hook_stage, ignore_errors=True)

    print("HERMES_ALIVE_LIFECYCLE_INSTALL_OK")
    print(f"source_target={paths.source_target}")
    print(f"active_hook={paths.hook_target}")
    print(f"shared_dir={paths.shared_dir}")
    print(f"source_owner={manifest['source_owner']}")
    print(f"compiled_python_files={validation['compile_count']}")
    print("gateway_restart_required=true")
    return 0


def _prune_backups(root: Path, keep: int) -> None:
    if not root.is_dir():
        return
    entries = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in entries[keep:]:
        shutil.rmtree(path, ignore_errors=True)


def _hermes_cli() -> list[str] | None:
    candidates = [
        os.getenv("HERMES_CLI"),
        "/opt/hermes/.venv/bin/hermes",
        "/opt/hermes/bin/hermes",
        shutil.which("hermes"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return [candidate]
    return None


def _hermes_config_path(cli: list[str], paths: Paths) -> Path:
    result = subprocess.run(
        cli + ["config", "path"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
        check=False,
        env={
            **os.environ,
            "HOME": str(paths.hermes_home),
            "HERMES_HOME": str(paths.hermes_home),
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    for raw in reversed((result.stdout or "").splitlines()):
        value = raw.strip()
        if value.startswith("/") and value.endswith((".yaml", ".yml")):
            return _safe_resolve(Path(value))
    return paths.hermes_home / "config.yaml"


def _model_config_status(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        return {
            "ready": False,
            "reason": "config_file_missing",
            "config_path": str(config_path),
            "provider": "",
            "model": "",
            "base_url_configured": False,
        }
    if yaml is None:
        return {
            "ready": False,
            "reason": "pyyaml_unavailable",
            "config_path": str(config_path),
            "provider": "",
            "model": "",
            "base_url_configured": False,
        }

    try:
        payload = yaml.safe_load(
            config_path.read_text(encoding="utf-8", errors="strict")
        ) or {}
    except Exception as exc:
        return {
            "ready": False,
            "reason": f"config_parse_failed:{type(exc).__name__}",
            "config_path": str(config_path),
            "provider": "",
            "model": "",
            "base_url_configured": False,
        }

    if not isinstance(payload, dict):
        payload = {}

    model_value = payload.get("model")
    provider = ""
    model_name = ""
    base_url = ""

    if isinstance(model_value, str):
        model_name = model_value.strip()
        if "/" in model_name:
            provider = model_name.split("/", 1)[0].strip()
    elif isinstance(model_value, dict):
        provider = str(model_value.get("provider") or "").strip()
        model_name = str(
            model_value.get("default")
            or model_value.get("name")
            or model_value.get("model")
            or ""
        ).strip()
        base_url = str(model_value.get("base_url") or "").strip()

    # Forward-compatible fallback for profiles that store the active model
    # under principal.{provider,model}.
    if not model_name:
        principal = payload.get("principal")
        if isinstance(principal, dict):
            provider = provider or str(principal.get("provider") or "").strip()
            principal_model = principal.get("model")
            if isinstance(principal_model, str):
                model_name = principal_model.strip()
            elif isinstance(principal_model, dict):
                provider = provider or str(
                    principal_model.get("provider") or ""
                ).strip()
                model_name = str(
                    principal_model.get("default")
                    or principal_model.get("name")
                    or principal_model.get("model")
                    or ""
                ).strip()
                base_url = base_url or str(
                    principal_model.get("base_url") or ""
                ).strip()

    ready = bool(model_name)
    return {
        "ready": ready,
        "reason": "model_configured" if ready else "model_not_configured",
        "config_path": str(config_path),
        "provider": provider,
        "model": model_name,
        "base_url_configured": bool(base_url),
    }


def _provider_status(paths: Paths) -> dict[str, Any]:
    cli = _hermes_cli()
    if cli is None:
        return {
            "ready": False,
            "reason": "hermes_cli_missing",
            "setup_command": "hermes setup model",
            "provider": "",
            "model": "",
        }

    config_path = _hermes_config_path(cli, paths)
    status = _model_config_status(config_path)
    status["setup_command"] = " ".join(cli + ["setup", "model"])
    status["config_check_is_readiness_signal"] = False
    return status


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _location_weather_module(source_root: Path):
    module_path = source_root / "hooks" / "location_weather_profile.py"
    if not module_path.is_file():
        raise LifecycleError(f"location onboarding module missing: {module_path}")
    spec = importlib.util.spec_from_file_location(
        "hermes_alive_location_weather_profile", module_path
    )
    if spec is None or spec.loader is None:
        raise LifecycleError("cannot load location onboarding module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _apply_noninteractive_location_args(
    values: dict[str, Any], args: argparse.Namespace, paths: Paths
) -> None:
    """Apply location state without ever reading terminal input."""

    module = _location_weather_module(paths.source_root)

    if args.skip_weather:
        values.update(module.disable_location_onboarding(values))
        return

    if args.weather_location:
        has_structured_fields = any(
            value not in (None, "")
            for value in (
                args.weather_lat,
                args.weather_lon,
                args.weather_country_code,
                args.weather_admin1,
                args.weather_admin2,
                args.weather_admin3,
                args.weather_timezone,
            )
        )
        if has_structured_fields:
            candidate = module.LocationCandidate(
                country_code=str(args.weather_country_code or "").strip().upper(),
                country_name="",
                admin1=str(args.weather_admin1 or "").strip(),
                admin2=str(args.weather_admin2 or "").strip(),
                admin3=str(args.weather_admin3 or "").strip(),
                locality=str(args.weather_location or "").strip(),
                latitude=None if args.weather_lat is None else float(args.weather_lat),
                longitude=None if args.weather_lon is None else float(args.weather_lon),
                timezone=str(args.weather_timezone or args.timezone or "").strip(),
                source="explicit_cli",
                precision=(
                    "district_or_county"
                    if (args.weather_admin2 or args.weather_admin3)
                    else "user_text"
                ),
                confidence=1.0,
            )
            values.update(module.profile_values(candidate, confirmed=True))
            values["weather_onboarding_complete"] = True
        else:
            values.update(
                module.confirm_location_onboarding(
                    values,
                    user_location=str(args.weather_location),
                )
            )
        if args.weather_enabled is False:
            values["weather_enabled"] = False
        return

    if args.weather_location_confirmed is True:
        values.update(module.confirm_location_onboarding(values))
        if args.weather_enabled is False:
            values["weather_enabled"] = False
        return

    if args.weather_location_confirmed is False:
        values["weather_location_confirmed"] = False
        values["weather_enabled"] = False

    if not values.get("weather_location_confirmed") and not values.get(
        "weather_onboarding_complete"
    ):
        values.update(
            module.prepare_location_onboarding(
                values,
                allow_network=bool(args.allow_network_location),
            )
        )


def configure(args: argparse.Namespace) -> int:
    paths = _paths(args)
    provider = _provider_status(paths)

    if args.run_provider_setup and not provider["ready"]:
        cli = _hermes_cli()
        if cli is None:
            raise LifecycleError("Hermes CLI is unavailable; cannot run Provider setup")
        result = subprocess.run(cli + ["setup", "model"], check=False)
        if result.returncode != 0:
            raise LifecycleError(
                f"Provider setup returned {result.returncode}"
            )
        provider = _provider_status(paths)

    if args.provider_check_only:
        print(json.dumps(provider, ensure_ascii=False, indent=2))
        if provider["ready"]:
            print("HERMES_ALIVE_PROVIDER_READY")
            return 0
        print("HERMES_ALIVE_PROVIDER_SETUP_REQUIRED")
        print(f"provider_setup_command={provider['setup_command']}")
        return 2

    current = _read_json(paths.config_file, {})
    values = current.get("values", {}) if isinstance(current, dict) else {}
    if not isinstance(values, dict):
        values = {}

    def assign(name: str, value: Any) -> None:
        if value is not None:
            values[name] = value

    if args.enable:
        assign("enabled", True)
    if args.disable:
        assign("enabled", False)
    assign("weixin_chat_id", args.weixin_chat_id)
    assign("timezone", args.timezone)
    assign("quiet_start", args.quiet_start)
    assign("quiet_end", args.quiet_end)
    assign("cooldown_minutes", args.cooldown_minutes)
    assign("platform_interval_seconds", args.platform_interval_seconds)
    if args.llm_enabled is not None:
        assign("llm_enabled", args.llm_enabled)
    assign("llm_model", args.llm_model)
    assign("llm_fallback_model", args.llm_fallback_model)
    if args.discovery_enabled is not None:
        assign("discovery_enabled", args.discovery_enabled)
    assign("discovery_interval_seconds", args.discovery_interval_seconds)
    assign("quality_governor_mode", args.quality_governor_mode)
    assign(
        "quality_topic_expiry_after_unanswered",
        args.quality_topic_expiry_after_unanswered,
    )
    assign(
        "quality_silence_after_unanswered",
        args.quality_silence_after_unanswered,
    )
    assign(
        "context_flow_max_age_seconds",
        args.context_flow_max_age_seconds,
    )
    if args.dream_enabled is not None:
        assign("dream_enabled", args.dream_enabled)
    assign("dream_interval_hours", args.dream_interval_hours)
    if args.weather_enabled is not None:
        assign("weather_enabled", args.weather_enabled)
    assign("weather_lat", args.weather_lat)
    assign("weather_lon", args.weather_lon)
    assign("weather_location_name", args.weather_location)
    assign("weather_country_code", args.weather_country_code)
    assign("weather_admin1", args.weather_admin1)
    assign("weather_admin2", args.weather_admin2)
    assign("weather_admin3", args.weather_admin3)
    assign("weather_timezone", args.weather_timezone)
    if args.weather_location_confirmed is not None:
        assign("weather_location_confirmed", args.weather_location_confirmed)
    _apply_noninteractive_location_args(values, args, paths)
    if values.get("weather_location_confirmed"):
        values["weather_onboarding_complete"] = True
    assign("emoji_policy", args.emoji_policy)
    if args.circadian_enabled is not None:
        assign("circadian_enabled", args.circadian_enabled)
    assign("circadian_mode", args.circadian_mode)
    assign("chronotype", args.chronotype)
    assign("circadian_timezone", args.circadian_timezone)
    assign("base_sleep_time", args.base_sleep_time)
    assign("base_wake_time", args.base_wake_time)
    assign("learned_sleep_offset_minutes", args.learned_sleep_offset_minutes)
    assign("learned_wake_offset_minutes", args.learned_wake_offset_minutes)
    assign("normal_sleep_earliest", args.normal_sleep_earliest)
    assign("normal_sleep_latest", args.normal_sleep_latest)
    assign("exceptional_sleep_latest", args.exceptional_sleep_latest)
    assign("normal_wake_earliest", args.normal_wake_earliest)
    assign("normal_wake_latest", args.normal_wake_latest)
    assign("ideal_sleep_minutes", args.ideal_sleep_minutes)
    assign("minimum_sleep_minutes", args.minimum_sleep_minutes)
    assign("deep_sleep_core_minutes", args.deep_sleep_core_minutes)
    assign("daily_sleep_variance_minutes", args.daily_sleep_variance_minutes)
    assign("daily_wake_variance_minutes", args.daily_wake_variance_minutes)
    assign("max_learning_minutes_per_day", args.max_learning_minutes_per_day)
    assign("max_learning_minutes_per_week", args.max_learning_minutes_per_week)
    assign("explicit_user_preference_weight", args.explicit_user_preference_weight)
    assign("repeated_interaction_weight", args.repeated_interaction_weight)
    assign("single_late_interaction_weight", args.single_late_interaction_weight)
    if args.learned_offset_decay_enabled is not None:
        assign("learned_offset_decay_enabled", args.learned_offset_decay_enabled)
    assign("learned_offset_decay_minutes_per_week", args.learned_offset_decay_minutes_per_week)
    if args.user_can_delay_sleep is not None:
        assign("user_can_delay_sleep", args.user_can_delay_sleep)
    assign("max_user_delay_minutes", args.max_user_delay_minutes)
    if args.user_can_wake_early is not None:
        assign("user_can_wake_early", args.user_can_wake_early)
    assign("sleep_transition_message_probability", args.sleep_transition_message_probability)
    assign("wake_transition_message_probability", args.wake_transition_message_probability)
    if args.sleep_debt_recovery_enabled is not None:
        assign("sleep_debt_recovery_enabled", args.sleep_debt_recovery_enabled)

    location_module = _location_weather_module(paths.source_root)
    detected_timezone = (
        str(values.get("timezone") or "").strip()
        or location_module.detect_system_timezone()
        or "UTC"
    )

    # Zero-touch defaults: installation must not ask the user to understand
    # timezone names, quiet-hour syntax, or lifecycle CLI options.
    values.setdefault("enabled", False)
    values.setdefault("timezone", detected_timezone)
    values.setdefault("quiet_start", "23:00")
    values.setdefault("quiet_end", "08:00")
    values.setdefault("emoji_policy", "contextual")
    values.setdefault("quality_governor_mode", "enforce")
    values.setdefault(
        "quality_topic_expiry_after_unanswered",
        1,
    )
    values.setdefault(
        "quality_silence_after_unanswered",
        2,
    )
    values.setdefault("context_flow_max_age_seconds", 3600)

    quality_mode = str(
        values.get("quality_governor_mode") or ""
    ).strip().lower()
    if quality_mode not in {"off", "shadow", "enforce"}:
        raise LifecycleError(
            "quality_governor_mode must be off, shadow, or enforce"
        )
    values["quality_governor_mode"] = quality_mode

    try:
        topic_expiry = int(
            values.get("quality_topic_expiry_after_unanswered")
        )
        silence_after = int(
            values.get("quality_silence_after_unanswered")
        )
        context_max_age = int(
            values.get("context_flow_max_age_seconds")
        )
    except (TypeError, ValueError) as exc:
        raise LifecycleError(
            "quality/context thresholds must be integers"
        ) from exc

    if not 1 <= topic_expiry <= 8:
        raise LifecycleError(
            "quality_topic_expiry_after_unanswered must be 1..8"
        )
    if not 1 <= silence_after <= 8:
        raise LifecycleError(
            "quality_silence_after_unanswered must be 1..8"
        )
    if silence_after < topic_expiry:
        raise LifecycleError(
            "quality_silence_after_unanswered must be >= "
            "quality_topic_expiry_after_unanswered"
        )
    if not 60 <= context_max_age <= 86400:
        raise LifecycleError(
            "context_flow_max_age_seconds must be 60..86400"
        )

    values["quality_topic_expiry_after_unanswered"] = (
        topic_expiry
    )
    values["quality_silence_after_unanswered"] = silence_after
    values["context_flow_max_age_seconds"] = context_max_age

    for name, default in CIRCADIAN_DEFAULT_VALUES.items():
        values.setdefault(name, default)
    values.setdefault("circadian_timezone", str(values.get("timezone") or "UTC"))

    # A user-confirmed weather location is a stronger timezone signal than a
    # container default such as UTC. Explicit --timezone still wins.
    if (
        args.timezone is None
        and values.get("weather_location_confirmed")
        and values.get("weather_timezone")
    ):
        values["timezone"] = str(values["weather_timezone"])
        values["circadian_timezone"] = str(values["weather_timezone"])

    payload = {
        "config_version": CONFIG_VERSION,
        "updated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "values": values,
        "provider": {
            "ready_at_last_check": bool(provider.get("ready")),
            "reason": provider.get("reason"),
            "setup_command": provider.get("setup_command"),
        },
    }
    _atomic_write_json(paths.config_file, payload)

    # Marker: HERMES_ALIVE_LIFECYCLE_RUNTIME_CONTROL_SYNC_V1
    # Keep the live watcher control plane synchronized with lifecycle
    # enable/disable operations. This makes --disable effective immediately for
    # an already-running watcher, while managed_config remains authoritative on
    # the next gateway import/start.
    if args.enable or args.disable:
        control_file = paths.shared_dir / "control.json"
        control = _read_json(control_file, {})
        if not isinstance(control, dict):
            control = {}
        control["enabled_override"] = bool(args.enable)
        control["reason"] = (
            "lifecycle configure --enable"
            if args.enable
            else "lifecycle configure --disable"
        )
        control["updated_at_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        )
        _atomic_write_json(control_file, control)

    print("HERMES_ALIVE_MANAGED_CONFIG_OK")
    print(f"managed_config={paths.config_file}")
    print(f"provider_ready={str(bool(provider.get('ready'))).lower()}")
    if not provider.get("ready"):
        print("HERMES_ALIVE_PROVIDER_SETUP_REQUIRED")
        print(f"provider_setup_command={provider['setup_command']}")
    location_confirmation_required = not bool(
        values.get("weather_onboarding_complete")
        or values.get("weather_location_confirmed")
    )
    onboarding = {
        "mode": "zero_touch",
        "timezone": values.get("timezone"),
        "quiet_start": values.get("quiet_start"),
        "quiet_end": values.get("quiet_end"),
        "provider_ready": bool(provider.get("ready")),
        "location_confirmation_required": location_confirmation_required,
        "location_suggestion": values.get("weather_location_name") or "",
        "location_question": (
            location_module.location_confirmation_prompt(values)
            if location_confirmation_required
            else ""
        ),
    }

    print("HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK")
    print(f"weather_enabled={str(bool(values.get('weather_enabled'))).lower()}")
    print(f"weather_location_confirmed={str(bool(values.get('weather_location_confirmed'))).lower()}")
    print(
        "location_confirmation_required="
        f"{str(location_confirmation_required).lower()}"
    )
    if values.get("weather_location_name"):
        print(f"weather_location={values['weather_location_name']}")
    print("onboarding_json=" + json.dumps(onboarding, ensure_ascii=False))
    print("gateway_restart_required=true")
    return 0


def _verify_no_secret_values(payload: Any, path: str = "") -> list[str]:
    failures: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            upper = str(key).upper()
            child = f"{path}.{key}" if path else str(key)
            if any(token in upper for token in SECRET_NAME_TOKENS):
                if value not in (None, "", False):
                    failures.append(child)
            failures.extend(_verify_no_secret_values(value, child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            failures.extend(_verify_no_secret_values(value, f"{path}[{index}]"))
    return failures


def verify(args: argparse.Namespace) -> int:
    paths = _paths(args)
    failures: list[str] = []
    details: dict[str, Any] = {}

    if not paths.source_target.is_dir():
        failures.append(f"source_missing:{paths.source_target}")
    if not paths.hook_target.is_dir():
        failures.append(f"active_hook_missing:{paths.hook_target}")

    if paths.source_target.is_dir():
        try:
            details["source_compile_count"] = _compile_tree(paths.source_target)
        except Exception as exc:
            failures.append(f"source_compile:{type(exc).__name__}:{exc}")

    if paths.hook_target.is_dir():
        try:
            details["hook_compile_count"] = _compile_tree(paths.hook_target)
        except Exception as exc:
            failures.append(f"hook_compile:{type(exc).__name__}:{exc}")

    source_hooks = (
        _tree_manifest(paths.source_target / "hooks")
        if (paths.source_target / "hooks").is_dir()
        else {}
    )
    active_hooks = (
        _tree_manifest(paths.hook_target)
        if paths.hook_target.is_dir()
        else {}
    )
    if source_hooks != active_hooks:
        failures.append("source_active_hook_hash_mismatch")

    manifest = _read_json(paths.manifest_file, {})
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != MANIFEST_VERSION:
        failures.append("manifest_missing_or_invalid")

    config = _read_json(paths.config_file, {})
    secret_paths = _verify_no_secret_values(config)
    if secret_paths:
        failures.append("managed_config_contains_secret_named_values:" + ",".join(secret_paths))

    details.update(
        {
            "source_file_count": len(_tree_manifest(paths.source_target))
            if paths.source_target.is_dir()
            else 0,
            "active_hook_file_count": len(active_hooks),
            "manifest_present": paths.manifest_file.is_file(),
            "managed_config_present": paths.config_file.is_file(),
            "provider": _provider_status(paths),
        }
    )

    print(json.dumps(details, ensure_ascii=False, indent=2))
    if failures:
        for failure in failures:
            print(f"VERIFY_FAIL {failure}")
        print("HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=FAIL")
        return 1

    print("HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS")
    return 0


def status(args: argparse.Namespace) -> int:
    paths = _paths(args)
    payload = {
        "source_installed": paths.source_target.is_dir(),
        "active_hook_installed": paths.hook_target.is_dir(),
        "shared_state_present": paths.shared_dir.is_dir(),
        "managed_config_present": paths.config_file.is_file(),
        "manifest": _read_json(paths.manifest_file, None),
        "provider": _provider_status(paths),
        "gateway_restart_required_after_change": True,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _remove_managed_config(paths: Paths) -> None:
    paths.config_file.unlink(missing_ok=True)
    config_dir = paths.config_file.parent
    if config_dir.is_dir() and not any(config_dir.iterdir()):
        config_dir.rmdir()


def _hub_uninstall(paths: Paths) -> tuple[bool, str]:
    cli = _hermes_cli()
    if cli is None:
        return False, "Hermes CLI missing"
    result = subprocess.run(
        cli + ["skills", "uninstall", SKILL_NAME],
        input="y\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    return result.returncode == 0, result.stdout or ""


def uninstall(args: argparse.Namespace, *, purge: bool) -> int:
    paths = _paths(args)
    manifest = _read_json(paths.manifest_file, {})
    source_owner = (
        manifest.get("source_owner")
        if isinstance(manifest, dict)
        else None
    ) or _detect_source_owner(paths)

    if paths.hook_target.exists():
        shutil.rmtree(paths.hook_target)
    _remove_managed_config(paths)

    source_removed = False
    source_message = ""
    if args.keep_source:
        source_message = "source kept by request"
    elif source_owner == "hub":
        source_removed, source_message = _hub_uninstall(paths)
        if not source_removed:
            raise LifecycleError(
                "Official Hermes skill uninstall failed: "
                + source_message[:800]
            )
    elif paths.source_target.exists():
        shutil.rmtree(paths.source_target)
        source_removed = True
        source_message = "lifecycle-owned source removed"
    else:
        source_removed = True
        source_message = "source already absent"

    if purge and paths.shared_dir.exists():
        shutil.rmtree(paths.shared_dir)
    elif paths.shared_dir.exists():
        tombstone = {
            "uninstalled_at_utc": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(),
            ),
            "state_preserved": True,
            "source_removed": source_removed,
            "source_owner": source_owner,
        }
        _atomic_write_json(paths.install_dir / "uninstalled.json", tombstone)
        paths.manifest_file.unlink(missing_ok=True)

    print(
        "HERMES_ALIVE_LIFECYCLE_PURGE_OK"
        if purge
        else "HERMES_ALIVE_LIFECYCLE_UNINSTALL_OK"
    )
    print(f"active_hook_removed={not paths.hook_target.exists()}")
    print(f"source_removed={source_removed}")
    print(f"source_owner={source_owner}")
    print(f"source_message={source_message.strip()[:500]}")
    print(f"shared_state_preserved={str(not purge).lower()}")
    print("gateway_restart_required=true")
    return 0


def _add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--hermes-home")
    parser.add_argument("--source-root")
    parser.add_argument("--source-target")
    parser.add_argument("--hook-target")
    parser.add_argument("--shared-dir")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hermes Alive lifecycle management"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install")
    _add_common_paths(install_parser)
    install_parser.set_defaults(func=install)

    configure_parser = subparsers.add_parser("configure")
    _add_common_paths(configure_parser)
    configure_parser.add_argument("--non-interactive", action="store_true")
    configure_parser.add_argument("--provider-check-only", action="store_true")
    configure_parser.add_argument("--run-provider-setup", action="store_true")
    enable_group = configure_parser.add_mutually_exclusive_group()
    enable_group.add_argument("--enable", action="store_true")
    enable_group.add_argument("--disable", action="store_true")
    configure_parser.add_argument("--weixin-chat-id")
    configure_parser.add_argument("--timezone")
    configure_parser.add_argument("--quiet-start")
    configure_parser.add_argument("--quiet-end")
    configure_parser.add_argument("--cooldown-minutes", type=int)
    configure_parser.add_argument("--platform-interval-seconds", type=int)
    configure_parser.add_argument(
        "--llm-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--llm-model")
    configure_parser.add_argument("--llm-fallback-model")
    configure_parser.add_argument(
        "--discovery-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--discovery-interval-seconds", type=int)
    configure_parser.add_argument(
        "--quality-governor-mode",
        choices=("off", "shadow", "enforce"),
    )
    configure_parser.add_argument(
        "--quality-topic-expiry-after-unanswered",
        type=int,
    )
    configure_parser.add_argument(
        "--quality-silence-after-unanswered",
        type=int,
    )
    configure_parser.add_argument(
        "--context-flow-max-age-seconds",
        type=int,
    )
    configure_parser.add_argument(
        "--dream-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--dream-interval-hours", type=int)
    configure_parser.add_argument(
        "--weather-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--weather-lat")
    configure_parser.add_argument("--weather-lon")
    configure_parser.add_argument("--weather-location")
    configure_parser.add_argument("--weather-country-code")
    configure_parser.add_argument("--weather-admin1")
    configure_parser.add_argument("--weather-admin2")
    configure_parser.add_argument("--weather-admin3")
    configure_parser.add_argument("--weather-timezone")
    configure_parser.add_argument(
        "--weather-location-confirmed",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--allow-network-location", action="store_true")
    configure_parser.add_argument(
        "--skip-weather",
        action="store_true",
        help="finish onboarding with weather context disabled",
    )
    configure_parser.add_argument(
        "--emoji-policy",
        choices=("contextual", "minimal", "off"),
    )
    configure_parser.add_argument(
        "--circadian-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument(
        "--circadian-mode",
        choices=("off", "shadow", "live"),
    )
    configure_parser.add_argument("--chronotype")
    configure_parser.add_argument("--circadian-timezone")
    configure_parser.add_argument("--base-sleep-time")
    configure_parser.add_argument("--base-wake-time")
    configure_parser.add_argument("--learned-sleep-offset-minutes", type=int)
    configure_parser.add_argument("--learned-wake-offset-minutes", type=int)
    configure_parser.add_argument("--normal-sleep-earliest")
    configure_parser.add_argument("--normal-sleep-latest")
    configure_parser.add_argument("--exceptional-sleep-latest")
    configure_parser.add_argument("--normal-wake-earliest")
    configure_parser.add_argument("--normal-wake-latest")
    configure_parser.add_argument("--ideal-sleep-minutes", type=int)
    configure_parser.add_argument("--minimum-sleep-minutes", type=int)
    configure_parser.add_argument("--deep-sleep-core-minutes", type=int)
    configure_parser.add_argument("--daily-sleep-variance-minutes", type=int)
    configure_parser.add_argument("--daily-wake-variance-minutes", type=int)
    configure_parser.add_argument("--max-learning-minutes-per-day", type=int)
    configure_parser.add_argument("--max-learning-minutes-per-week", type=int)
    configure_parser.add_argument("--explicit-user-preference-weight", type=float)
    configure_parser.add_argument("--repeated-interaction-weight", type=float)
    configure_parser.add_argument("--single-late-interaction-weight", type=float)
    configure_parser.add_argument(
        "--learned-offset-decay-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--learned-offset-decay-minutes-per-week", type=int)
    configure_parser.add_argument(
        "--user-can-delay-sleep",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--max-user-delay-minutes", type=int)
    configure_parser.add_argument(
        "--user-can-wake-early",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.add_argument("--sleep-transition-message-probability", type=float)
    configure_parser.add_argument("--wake-transition-message-probability", type=float)
    configure_parser.add_argument(
        "--sleep-debt-recovery-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    configure_parser.set_defaults(func=configure)

    verify_parser = subparsers.add_parser("verify")
    _add_common_paths(verify_parser)
    verify_parser.set_defaults(func=verify)

    status_parser = subparsers.add_parser("status")
    _add_common_paths(status_parser)
    status_parser.set_defaults(func=status)

    uninstall_parser = subparsers.add_parser("uninstall")
    _add_common_paths(uninstall_parser)
    uninstall_parser.add_argument("--keep-source", action="store_true")
    uninstall_parser.set_defaults(
        func=lambda args: uninstall(args, purge=False)
    )

    purge_parser = subparsers.add_parser("purge")
    _add_common_paths(purge_parser)
    purge_parser.add_argument("--keep-source", action="store_true")
    purge_parser.set_defaults(
        func=lambda args: uninstall(args, purge=True)
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except LifecycleError as exc:
        print(f"HERMES_ALIVE_LIFECYCLE_ERROR={exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            f"HERMES_ALIVE_LIFECYCLE_UNEXPECTED={type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
