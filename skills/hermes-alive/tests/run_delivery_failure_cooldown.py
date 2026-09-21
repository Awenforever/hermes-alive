#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from cooldown_manager import CooldownManager


def main() -> int:
    previous = os.environ.get("HERMES_PROACTIVE_COOLDOWN_MINUTES")
    os.environ["HERMES_PROACTIVE_COOLDOWN_MINUTES"] = "120"
    try:
        with tempfile.TemporaryDirectory(prefix="alive-failure-cooldown-") as raw:
            now = [datetime(2026, 9, 21, 12, 0, 0)]
            path = Path(raw) / "cooldown.json"
            manager = CooldownManager(path, now_fn=lambda: now[0])
            manager.record_attempt("self_talk")
            allowed, reason = manager.can_send("proactive")
            assert allowed is False and reason == "cooldown_after_failure"
            assert manager.daily_count == 0

            restored = CooldownManager(path, now_fn=lambda: now[0])
            allowed, reason = restored.can_send("proactive")
            assert allowed is False and reason == "cooldown_after_failure"
            now[0] += timedelta(minutes=121)
            assert restored.can_send("proactive") == (True, "ok")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_COOLDOWN_MINUTES", None)
        else:
            os.environ["HERMES_PROACTIVE_COOLDOWN_MINUTES"] = previous
    print("HERMES_ALIVE_DELIVERY_FAILURE_COOLDOWN_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
