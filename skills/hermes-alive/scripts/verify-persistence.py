#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
from pathlib import Path

MARKER = "HERMES_ENV_AWARE_PERSISTENCE_VERIFY_V1"

def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", "/opt/data")).resolve()

def in_container() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore")
        if any(x in cgroup.lower() for x in ["docker", "containerd", "kubepods", "podman", "lxc"]):
            return True
    except Exception:
        pass
    return False

def in_wsl() -> bool:
    try:
        txt = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
        return "microsoft" in txt or "wsl" in txt
    except Exception:
        return "microsoft" in platform.release().lower()

def mount_points() -> set[str]:
    pts: set[str] = set()
    try:
        for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pts.add(parts[4].replace("\\040", " "))
    except Exception:
        pass
    return pts

def is_mount_or_under_mount(path: Path) -> bool:
    pts = mount_points()
    s = str(path)
    if s in pts:
        return True
    return any(str(p) in pts for p in path.parents)

def main() -> int:
    hh = hermes_home()
    container = in_container()
    wsl = in_wsl()
    problems: list[str] = []
    warnings: list[str] = []

    if not hh.exists():
        problems.append(f"HERMES_HOME missing: {hh}")
    if hh.exists() and not os.access(str(hh), os.R_OK | os.W_OK):
        problems.append(f"HERMES_HOME not readable/writable: {hh}")

    if container:
        if str(hh) != "/opt/data":
            warnings.append(f"Docker environment detected but HERMES_HOME is not /opt/data: {hh}")
        if not is_mount_or_under_mount(hh):
            problems.append(f"Docker environment detected but HERMES_HOME does not appear to be on a mount: {hh}")
    else:
        warnings.append("Docker/container environment not detected; Docker volume persistence check not required.")

    result = {
        "ok": not problems,
        "marker": MARKER,
        "environment": {
            "container": container,
            "wsl": wsl,
            "platform": platform.platform(),
            "hermes_home": str(hh),
            "hermes_home_exists": hh.exists(),
            "hermes_home_read_write": hh.exists() and os.access(str(hh), os.R_OK | os.W_OK),
            "hermes_home_on_mount_or_under_mount": is_mount_or_under_mount(hh) if hh.exists() else False,
        },
        "problems": problems,
        "warnings": warnings,
        "policy": {
            "bare_wsl_linux": "no Docker volume requirement",
            "docker": "HERMES_HOME should be persistent mounted data root, normally /opt/data",
            "uninstall_default": "preserve user/runtime data",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not problems else 2

if __name__ == "__main__":
    raise SystemExit(main())
