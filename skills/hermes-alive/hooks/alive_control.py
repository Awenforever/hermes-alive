#!/usr/bin/env python3
"""Hermes Alive safe control surface.

Commands:
  alive_control.py status
  alive_control.py enable
  alive_control.py disable
  alive_control.py test

This script controls the gateway watcher through $HERMES_HOME/hermes_alive_shared/control.json.
It also reads $HERMES_HOME/.env for accurate status display.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")
_SHARED_DIR = os.getenv("HERMES_ALIVE_SHARED_DIR", os.path.join(os.getenv("HERMES_HOME", "/opt/data"), "hermes_alive_shared"))
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

from safe_io import locked_read_json, locked_write_json, append_jsonl, read_json, atomic_write_text

HERMES_HOME = Path(os.getenv("HERMES_HOME", "/opt/data"))
BASE = HERMES_HOME / "hermes_alive_shared"
ENV_FILE = HERMES_HOME / ".env"
CONTROL = BASE / "control.json"
QUEUE = BASE / "control_queue.jsonl"
COOLDOWN = BASE / "cooldown.json"
PROACTIVE_LOG = BASE / "proactive_log.jsonl"
LOCK = BASE / "locks" / "proactive_watcher.lock"

def read_env_file() -> dict[str, str]:
    result = {}
    if not ENV_FILE.exists():
        return result
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip()
    return result

def load_control() -> dict:
    data = locked_read_json(CONTROL, {}, "control.lock")
    if not isinstance(data, dict):
        data = {}
    data.setdefault("enabled_override", None)
    data.setdefault("updated_at", None)
    data.setdefault("reason", None)
    return data

def save_control(data: dict) -> None:
    data["updated_at"] = datetime.now().astimezone().isoformat()
    locked_write_json(CONTROL, data, "control.lock")

def recent_log_lines(n: int = 5):
    if not PROACTIVE_LOG.exists():
        return []
    out = []
    for line in PROACTIVE_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append(line)
    return out

def status() -> int:
    env = read_env_file()
    control = load_control()
    queue_size = QUEUE.stat().st_size if QUEUE.exists() else 0
    payload = {
        "env_file": str(ENV_FILE),
        "env_enabled": env.get("HERMES_PROACTIVE_PLATFORM_ENABLED"),
        "env_discovery_enabled": env.get("HERMES_PROACTIVE_DISCOVERY_ENABLED"),
        "env_discovery_work_dir": env.get("HERMES_DISCOVERY_WORK_DIR"),
        "control": control,
        "cooldown": read_json(COOLDOWN, {}),
        "watcher_lock_path": str(LOCK),
        "watcher_lock_exists": LOCK.exists(),
        "control_queue_path": str(QUEUE),
        "control_queue_size": queue_size,
        "proactive_log": str(PROACTIVE_LOG),
        "recent_log": recent_log_lines(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

def enable() -> int:
    data = load_control()
    data["enabled_override"] = True
    data["reason"] = "manual enable via alive_control.py"
    save_control(data)
    print("Hermes Alive proactive sending enabled by control override.")
    return 0

def disable() -> int:
    data = load_control()
    data["enabled_override"] = False
    data["reason"] = "manual disable via alive_control.py"
    save_control(data)
    print("Hermes Alive proactive sending disabled by control override.")
    return 0

def test() -> int:
    append_jsonl(QUEUE, {
        "type": "test",
        "created_at": datetime.now().astimezone().isoformat(),
        "message": "Hermes Alive 主动推送测试。"
    }, "control_queue.lock")
    print("Queued one /alive test request. Enable Hermes Alive only when you intentionally want it sent.")
    return 0

def clear_test_queue() -> int:
    atomic_write_text(QUEUE, "")
    print("Cleared Hermes Alive control queue.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["status", "enable", "disable", "test", "clear-test-queue"])
    args = parser.parse_args()
    return {
        "status": status,
        "enable": enable,
        "disable": disable,
        "test": test,
        "clear-test-queue": clear_test_queue,
    }[args.command]()

if __name__ == "__main__":
    raise SystemExit(main())
