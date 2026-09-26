#!/usr/bin/env python3
"""One-shot discovery uses a durable wake marker and consumes it once."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"

with tempfile.TemporaryDirectory(prefix="alive-discovery-control-") as temporary:
    shared = Path(temporary) / "runtime"
    os.environ["HERMES_HOME"] = str(Path(temporary) / "home")
    os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
    sys.path.insert(0, str(HOOKS))

    import alive_control
    import proactive_watcher

    class Config:
        proactive_platform_enabled = True

    assert alive_control.discover() == 0
    assert alive_control.DISCOVERY_REQUEST.is_file()
    control = json.loads(alive_control.CONTROL.read_text(encoding="utf-8"))
    assert control["discovery_once"] is True

    watcher = proactive_watcher.ProactivePlatformWatcher({}, Config())
    assert watcher._discovery_once_pending() is True
    assert watcher._consume_discovery_once() is True
    assert watcher._discovery_once_pending() is False
    assert not alive_control.DISCOVERY_REQUEST.exists()
    control = json.loads(alive_control.CONTROL.read_text(encoding="utf-8"))
    assert control["discovery_once"] is False
    assert watcher._consume_discovery_once() is False

print("HERMES_ALIVE_DISCOVERY_ONCE_CONTROL_RESULT=PASS")
