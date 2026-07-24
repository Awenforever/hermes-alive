"""Observe-only sleep and quiet policy for Hermes Alive.

This module compares the deterministic Circadian Engine decision with the
legacy fixed quiet-hours gate. It never blocks, sends, or mutates delivery.

Markers:
- HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_POLICY_SHADOW_V1
- HERMES_ALIVE_CIRCADIAN_DYNAMIC_QUIET_COMPARE_V1
- HERMES_ALIVE_CIRCADIAN_HARD_EXEMPT_BOUNDARY_V1
"""

from __future__ import annotations

import os
from datetime import datetime, time
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Asia/Singapore"
DEFAULT_QUIET_START = "00:30"
DEFAULT_QUIET_END = "08:30"

SLEEP_PROTECTED_PHASES = {
    "winding_down",
    "drowsy",
    "asleep",
    "light_sleep",
}

KNOWN_AWAKE_PHASES = {
    "awake",
    "forced_awake",
    "sleep_deprived",
    "overslept",
    "recovering",
}

HARD_EXEMPT_CLASSES = {
    "system_error",
    "service_alert",
    "security_alert",
    "control_command",
    "explicit_reminder",
    "email_watchdog",
    "business_critical",
}


def evaluate_sleep_quiet_shadow(
    circadian_decision: Mapping[str, Any] | None,
    *,
    message_class: str = "proactive_social",
    now: datetime | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a privacy-safe, observe-only dynamic sleep/quiet decision."""

    env = os.environ if environ is None else environ
    category = str(message_class or "proactive_social").strip().lower()
    circadian = dict(circadian_decision) if isinstance(circadian_decision, Mapping) else {}
    timezone_name = str(
        circadian.get("timezone")
        or env.get("HERMES_ALIVE_CIRCADIAN_TIMEZONE")
        or env.get("TZ")
        or DEFAULT_TIMEZONE
    ).strip() or DEFAULT_TIMEZONE
    current = _local_now(now, timezone_name)
    legacy = fixed_quiet_hours_snapshot(now=current, environ=env, timezone_name=timezone_name)

    enabled = bool(circadian.get("enabled", True))
    mode = str(circadian.get("mode") or "shadow").strip().lower()
    phase = str(circadian.get("phase") or "unknown").strip().lower()
    hard_exempt = bool(circadian.get("hard_exempt")) or category in HARD_EXEMPT_CLASSES

    if not enabled:
        dynamic_allow = True
        reason = "circadian_disabled"
    elif mode == "off":
        dynamic_allow = True
        reason = "circadian_mode_off"
    elif hard_exempt:
        dynamic_allow = True
        reason = "hard_exempt"
    elif phase in SLEEP_PROTECTED_PHASES:
        dynamic_allow = False
        reason = (
            "deep_sleep_core"
            if bool(circadian.get("deep_sleep_core"))
            else "sleep_protection_transition"
            if phase in {"winding_down", "drowsy"}
            else "dynamic_sleep_window"
        )
    elif phase == "forced_awake":
        dynamic_allow = True
        reason = "user_forced_awake"
    elif phase in KNOWN_AWAKE_PHASES:
        dynamic_allow = True
        reason = "awake"
    else:
        # This phase is shadow-only. Unknown state must not become an
        # accidental delivery block before isolated enforcement exists.
        dynamic_allow = True
        reason = "unknown_phase_fail_open"

    legacy_in_quiet = bool(legacy["in_quiet_hours"])
    legacy_allow = hard_exempt or not legacy_in_quiet
    comparison = _comparison(
        dynamic_allow=dynamic_allow,
        legacy_allow=legacy_allow,
        hard_exempt=hard_exempt,
    )

    return {
        "engine": "circadian_sleep_quiet_policy",
        "schema_version": 1,
        "mode": "shadow",
        "shadow_only": True,
        "integration_mode": "observe_only",
        "watcher_enforced": False,
        "behavior_changed": False,
        "message_class": category,
        "phase": phase,
        "hard_exempt": hard_exempt,
        "sleep_protected_phase": phase in SLEEP_PROTECTED_PHASES,
        "deep_sleep_core": bool(circadian.get("deep_sleep_core")),
        "would_allow_dynamic": dynamic_allow,
        "would_block_dynamic": not dynamic_allow,
        "dynamic_reason": reason,
        "legacy_fixed_quiet": legacy,
        "legacy_would_allow": legacy_allow,
        "legacy_would_block": not legacy_allow,
        "comparison": comparison,
        "planned_sleep_at": circadian.get("planned_sleep_at"),
        "planned_wake_at": circadian.get("planned_wake_at"),
        "sleep_debt_minutes": _safe_nonnegative_int(circadian.get("sleep_debt_minutes")),
        "raw_message_stored": False,
    }


def fixed_quiet_hours_snapshot(
    *,
    now: datetime | None = None,
    environ: Mapping[str, str] | None = None,
    timezone_name: str | None = None,
) -> dict[str, Any]:
    """Mirror the legacy fixed quiet-hours calculation without mutating it."""

    env = os.environ if environ is None else environ
    tz_name = str(
        timezone_name
        or env.get("HERMES_ALIVE_CIRCADIAN_TIMEZONE")
        or env.get("TZ")
        or DEFAULT_TIMEZONE
    ).strip() or DEFAULT_TIMEZONE
    current = _local_now(now, tz_name)

    raw_start = str(env.get("HERMES_PROACTIVE_QUIET_START") or DEFAULT_QUIET_START).strip()
    raw_end = str(env.get("HERMES_PROACTIVE_QUIET_END") or DEFAULT_QUIET_END).strip()
    start, start_valid = _parse_clock(raw_start, DEFAULT_QUIET_START)
    end, end_valid = _parse_clock(raw_end, DEFAULT_QUIET_END)
    current_clock = current.timetz().replace(tzinfo=None)
    if start <= end:
        in_quiet = start <= current_clock < end
        crosses_midnight = False
    else:
        in_quiet = current_clock >= start or current_clock < end
        crosses_midnight = True

    return {
        "start": start.strftime("%H:%M"),
        "end": end.strftime("%H:%M"),
        "configured_valid": bool(start_valid and end_valid),
        "fallback_used": not bool(start_valid and end_valid),
        "crosses_midnight": crosses_midnight,
        "in_quiet_hours": in_quiet,
        "timezone": tz_name,
        "evaluated_local_minute": current.strftime("%H:%M"),
    }


def _comparison(*, dynamic_allow: bool, legacy_allow: bool, hard_exempt: bool) -> str:
    if hard_exempt:
        return "hard_exempt_bypass"
    if dynamic_allow and legacy_allow:
        return "aligned_allow"
    if not dynamic_allow and not legacy_allow:
        return "aligned_block"
    if not dynamic_allow and legacy_allow:
        return "dynamic_more_protective"
    return "dynamic_more_permissive"


def _local_now(value: datetime | None, timezone_name: str) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    current = value or datetime.now(zone)
    if current.tzinfo is None:
        return current.replace(tzinfo=zone)
    return current.astimezone(zone)


def _parse_clock(raw: str, fallback: str) -> tuple[time, bool]:
    def parse(value: str) -> time:
        hour_text, minute_text = value.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("clock out of range")
        return time(hour, minute)

    try:
        return parse(raw), True
    except (TypeError, ValueError, AttributeError):
        return parse(fallback), False


def _safe_nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
