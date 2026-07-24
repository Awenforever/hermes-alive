"""Persistent send limits for Hermes Alive proactive messages.

Supports quiet hours, minimum spacing (cooldown), and social_urge dynamic cooldown.
"""

from __future__ import annotations

import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path
from typing import Callable

_HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")
_SHARED_DIR = os.getenv("HERMES_ALIVE_SHARED_DIR", os.path.join(os.getenv("HERMES_HOME", "/opt/data"), "hermes_alive_shared"))
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)

from safe_io import locked_read_json, locked_write_json

logger = logging.getLogger(__name__)

HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")
DEFAULT_STATE_PATH = Path(os.path.join(HERMES_HOME, "hermes_alive_shared", "cooldown.json"))
COOLDOWN_LOCK_NAME = "cooldown.lock"


class CooldownManager:
    """Applies quiet hours, minimum spacing, and social_urge dynamic cooldown."""

    def __init__(self, state_path: Path | None = None, now_fn: Callable[[], datetime] | None = None) -> None:
        self.state_path = state_path or DEFAULT_STATE_PATH
        self.now_fn = now_fn or datetime.now
        self.last_sent: datetime | None = None
        self.daily_count = 0
        self.day = self.now_fn().date().isoformat()
        self.type_counts: dict[str, int] = defaultdict(int)
        self._mood_cooldown: int | None = None  # set by set_mood_cooldown()
        self._load()
        self._reset_if_new_day()

    def set_mood_cooldown(self, social_urge: float | None) -> None:
        """Set cooldown based on the independent social_urge dimension.

        cooldown = max(30, 120 - social_urge * 90)
        At social_urge=0.0 → 120min, at 1.0 → 30min.
        Call before can_send() each tick.
        """
        if social_urge is None:
            self._mood_cooldown = None
            return
        urge = max(0.0, min(1.0, float(social_urge)))
        self._mood_cooldown = max(30, int(120 - urge * 90))

    def can_send(self, msg_type: str) -> tuple[bool, str]:
        _ = msg_type  # unused but kept for signature compatibility
        self._reset_if_new_day()
        if self.is_quiet_hours():
            return False, "quiet_hours"
        if self.last_sent is not None:
            effective = self._mood_cooldown or _env_int("HERMES_PROACTIVE_COOLDOWN_MINUTES", 90)
            elapsed = (self.now_fn() - self.last_sent).total_seconds() / 60
            if elapsed < effective:
                return False, "cooldown"
        return True, "ok"

    def record_send(self, msg_type: str) -> None:
        self._reset_if_new_day()
        self.last_sent = self.now_fn()
        self.daily_count += 1
        self.type_counts[msg_type] += 1
        self._save()

    def status(self) -> dict:
        self._reset_if_new_day()
        return {
            "state_path": str(self.state_path),
            "last_sent": self.last_sent.isoformat() if self.last_sent else None,
            "daily_count": self.daily_count,
            "day": self.day,
            "type_counts": dict(self.type_counts),
            "quiet_hours": self.is_quiet_hours(),
            "mood_cooldown": self._mood_cooldown,
        }

    def is_quiet_hours(self) -> bool:
        now = self.now_fn().time()
        start = _env_time("HERMES_PROACTIVE_QUIET_START", time(0, 30))
        end = _env_time("HERMES_PROACTIVE_QUIET_END", time(8, 30))
        if start <= end:
            return start <= now < end
        return now >= start or now < end

    def _reset_if_new_day(self) -> None:
        today = self.now_fn().date().isoformat()
        if self.day != today:
            self.day = today
            self.daily_count = 0
            self.type_counts = defaultdict(int)
            self._save()

    def _load(self) -> None:
        data = locked_read_json(self.state_path, {}, COOLDOWN_LOCK_NAME)
        if not isinstance(data, dict):
            return
        self.day = str(data.get("day") or self.day)
        try:
            self.daily_count = int(data.get("daily_count") or 0)
        except (TypeError, ValueError):
            self.daily_count = 0
        default_type_counts: dict[str, int] = {}
        for k, v in data.get("type_counts", {}).items():
            try:
                default_type_counts[str(k)] = int(v)
            except (TypeError, ValueError):
                default_type_counts[str(k)] = 0
        self.type_counts = defaultdict(int, default_type_counts)
        raw_last_sent = data.get("last_sent")
        if raw_last_sent:
            try:
                self.last_sent = datetime.fromisoformat(raw_last_sent)
            except ValueError:
                self.last_sent = None

    def _save(self) -> None:
        data = {
            "last_sent": self.last_sent.isoformat() if self.last_sent else None,
            "daily_count": self.daily_count,
            "day": self.day,
            "type_counts": dict(self.type_counts),
        }
        locked_write_json(self.state_path, data, COOLDOWN_LOCK_NAME)


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value >= 0 else default


def _env_time(name: str, default: time) -> time:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        hour, minute = raw.split(":", 1)
        return time(int(hour), int(minute))
    except (TypeError, ValueError):
        return default
