#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
SCRIPTS = ROOT / "scripts"
import sys
for path in (HOOKS, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ["HERMES_HOOK_DIR"] = str(HOOKS)

from circadian_sleep_quiet_policy import (
    evaluate_sleep_quiet_shadow,
    fixed_quiet_hours_snapshot,
)
from proactive_watcher import ProactivePlatformWatcher


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def base_decision(**overrides: Any) -> dict[str, Any]:
    decision = {
        "enabled": True,
        "mode": "shadow",
        "phase": "awake",
        "hard_exempt": False,
        "deep_sleep_core": False,
        "planned_sleep_at": "2026-07-12T23:00:00+08:00",
        "planned_wake_at": "2026-07-13T07:00:00+08:00",
        "sleep_debt_minutes": 0,
    }
    decision.update(overrides)
    return decision


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, 12, hour, minute, tzinfo=ZoneInfo("Asia/Singapore"))


def quiet_env(start: str = "00:30", end: str = "08:30") -> dict[str, str]:
    return {
        "TZ": "Asia/Singapore",
        "HERMES_PROACTIVE_QUIET_START": start,
        "HERMES_PROACTIVE_QUIET_END": end,
    }


def test_fixed_quiet_cross_midnight_and_same_day() -> None:
    cross = quiet_env("23:00", "07:00")
    check(fixed_quiet_hours_snapshot(now=at(23, 30), environ=cross)["in_quiet_hours"] is True, "late cross-midnight quiet missed")
    check(fixed_quiet_hours_snapshot(now=at(6, 30), environ=cross)["in_quiet_hours"] is True, "early cross-midnight quiet missed")
    check(fixed_quiet_hours_snapshot(now=at(12, 0), environ=cross)["in_quiet_hours"] is False, "daytime incorrectly quiet")
    same = quiet_env("13:00", "14:00")
    snapshot = fixed_quiet_hours_snapshot(now=at(13, 30), environ=same)
    check(snapshot["in_quiet_hours"] is True and snapshot["crosses_midnight"] is False, "same-day quiet failed")


def test_invalid_fixed_quiet_falls_back_safely() -> None:
    snapshot = fixed_quiet_hours_snapshot(now=at(1, 0), environ=quiet_env("99:99", "bad"))
    check(snapshot["configured_valid"] is False, "invalid quiet config not marked")
    check(snapshot["fallback_used"] is True, "fallback marker missing")
    check(snapshot["start"] == "00:30" and snapshot["end"] == "08:30", "fallback values wrong")
    check(snapshot["in_quiet_hours"] is True, "fallback quiet evaluation wrong")


def test_asleep_outside_legacy_quiet_is_more_protective() -> None:
    result = evaluate_sleep_quiet_shadow(
        base_decision(phase="asleep"),
        now=at(22, 0),
        environ=quiet_env(),
    )
    check(result["would_block_dynamic"] is True, "asleep should be dynamically protected")
    check(result["legacy_would_allow"] is True, "legacy should allow outside fixed quiet")
    check(result["comparison"] == "dynamic_more_protective", "comparison wrong")


def test_forced_awake_inside_legacy_quiet_is_more_permissive() -> None:
    result = evaluate_sleep_quiet_shadow(
        base_decision(phase="forced_awake"),
        now=at(1, 0),
        environ=quiet_env(),
    )
    check(result["would_allow_dynamic"] is True, "forced awake should allow in dynamic shadow")
    check(result["legacy_would_block"] is True, "legacy quiet should still block")
    check(result["dynamic_reason"] == "user_forced_awake", "forced-awake reason missing")
    check(result["comparison"] == "dynamic_more_permissive", "comparison wrong")


def test_winding_down_and_drowsy_are_protected() -> None:
    for phase in ("winding_down", "drowsy"):
        result = evaluate_sleep_quiet_shadow(base_decision(phase=phase), now=at(22, 0), environ=quiet_env())
        check(result["would_block_dynamic"] is True, f"{phase} should be protected")
        check(result["dynamic_reason"] == "sleep_protection_transition", f"{phase} reason wrong")


def test_hard_exempt_classes_bypass_sleep_and_quiet() -> None:
    for message_class in ("control_command", "system_error", "email_watchdog", "explicit_reminder"):
        result = evaluate_sleep_quiet_shadow(
            base_decision(phase="asleep"),
            message_class=message_class,
            now=at(1, 0),
            environ=quiet_env(),
        )
        check(result["hard_exempt"] is True, f"{message_class} not exempt")
        check(result["would_allow_dynamic"] is True, f"{message_class} dynamically blocked")
        check(result["legacy_would_allow"] is True, f"{message_class} legacy comparison blocked")
        check(result["comparison"] == "hard_exempt_bypass", f"{message_class} comparison wrong")


def test_disabled_off_and_unknown_phase_fail_open() -> None:
    disabled = evaluate_sleep_quiet_shadow(base_decision(enabled=False, phase="asleep"), now=at(1), environ=quiet_env())
    off = evaluate_sleep_quiet_shadow(base_decision(mode="off", phase="asleep"), now=at(1), environ=quiet_env())
    unknown = evaluate_sleep_quiet_shadow(base_decision(phase="future_phase"), now=at(22), environ=quiet_env())
    check(disabled["would_allow_dynamic"] is True and disabled["dynamic_reason"] == "circadian_disabled", "disabled fail-open wrong")
    check(off["would_allow_dynamic"] is True and off["dynamic_reason"] == "circadian_mode_off", "off fail-open wrong")
    check(unknown["would_allow_dynamic"] is True and unknown["dynamic_reason"] == "unknown_phase_fail_open", "unknown fail-open wrong")


class DummyAdapter:
    async def send(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None):
        return SimpleNamespace(success=True, error=None)


class FakeCircadian:
    def __init__(self, decision: dict[str, Any] | None = None) -> None:
        self.calls = 0
        self.decision = decision or base_decision(phase="asleep")

    def shadow_decision(self, *, message_class: str):
        self.calls += 1
        result = dict(self.decision)
        result["message_class"] = message_class
        return result


class QuietCooldown:
    def set_mood_cooldown(self, social_urge: float | None) -> None:
        pass

    def can_send(self, msg_type: str):
        return False, "quiet_hours"


async def install_tick_stubs(
    watcher: ProactivePlatformWatcher,
    *,
    control_sent: bool = False,
    cooldown: Any | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {"compose_called": False}

    async def process_control(self, adapter, chat_id, tick_id):
        return control_sent

    def resolve(self):
        return DummyAdapter(), "human-peer"

    def voice_state(self):
        return None

    def user_active(self):
        return False

    def policy(self, **kwargs):
        return None

    def cooldown_fn(self):
        return cooldown

    async def discovery(self):
        return None

    async def dream(self):
        return None

    async def compose(self, voice=None, discovery_context=None, policy_decision=None):
        state["compose_called"] = True
        return []

    watcher._process_control_queue = MethodType(process_control, watcher)
    watcher._resolve_adapter_and_chat_id = MethodType(resolve, watcher)
    watcher._voice_state = MethodType(voice_state, watcher)
    watcher._user_active_recently = MethodType(user_active, watcher)
    watcher._evaluate_interruption_policy = MethodType(policy, watcher)
    watcher._cooldown = MethodType(cooldown_fn, watcher)
    watcher._check_discovery = MethodType(discovery, watcher)
    watcher._check_dream = MethodType(dream, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    return state


def test_watcher_logs_shadow_but_does_not_enforce() -> None:
    previous = os.environ.get("HERMES_PROACTIVE_PLATFORM_ENABLED")
    os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
    try:
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        fake = FakeCircadian(base_decision(phase="asleep"))
        watcher._circadian_engine = fake
        records: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: records.append((decision, extra))
        state = asyncio.run(install_tick_stubs(watcher))
        result = asyncio.run(watcher._tick_impl("sleep-quiet-shadow"))
        check(result is False, "empty delivery should return false")
        check(fake.calls == 1, "circadian should be evaluated once")
        check(state["compose_called"] is True, "shadow policy incorrectly enforced")
        rows = [extra for decision, extra in records if decision == "sleep_quiet_policy_shadow"]
        check(len(rows) == 1, "sleep/quiet shadow record missing")
        payload = rows[0]["sleep_quiet_policy"]
        check(payload["would_block_dynamic"] is True, "expected dynamic block observation")
        check(payload["watcher_enforced"] is False and payload["behavior_changed"] is False, "shadow boundary wrong")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
        else:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = previous


def test_control_queue_bypasses_sleep_quiet_shadow() -> None:
    previous = os.environ.get("HERMES_PROACTIVE_PLATFORM_ENABLED")
    os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
    try:
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        fake = FakeCircadian()
        watcher._circadian_engine = fake
        records: list[str] = []
        watcher._log = lambda decision, **extra: records.append(decision)
        asyncio.run(install_tick_stubs(watcher, control_sent=True))
        result = asyncio.run(watcher._tick_impl("control-bypass"))
        check(result is True, "control send should end tick")
        check(fake.calls == 0, "control queue must bypass circadian")
        check("sleep_quiet_policy_shadow" not in records, "control queue entered social sleep policy")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
        else:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = previous


def test_legacy_quiet_remains_authoritative() -> None:
    previous = os.environ.get("HERMES_PROACTIVE_PLATFORM_ENABLED")
    os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
    try:
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        watcher._circadian_engine = FakeCircadian(base_decision(phase="forced_awake"))
        records: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: records.append((decision, extra))
        state = asyncio.run(install_tick_stubs(watcher, cooldown=QuietCooldown()))
        result = asyncio.run(watcher._tick_impl("legacy-authoritative"))
        check(result is False, "legacy quiet should stop tick")
        check(state["compose_called"] is False, "compose ran despite legacy quiet")
        check(any(d == "sleep_quiet_policy_shadow" for d, _ in records), "shadow comparison missing")
        skips = [e for d, e in records if d == "skip"]
        check(any(e.get("reason") == "quiet_hours" for e in skips), "legacy quiet skip missing")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
        else:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = previous


def test_invalid_shadow_policy_fails_open_in_watcher() -> None:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    result = watcher._sleep_quiet_policy_shadow_decision(None, message_class="proactive_social")
    check(result is None, "missing circadian decision should fail open")


def test_observability_contains_no_secrets_or_raw_message() -> None:
    result = evaluate_sleep_quiet_shadow(base_decision(phase="asleep"), now=at(1), environ=quiet_env())
    payload = json.dumps(result, ensure_ascii=False).lower()
    for token in ("api_key", "access_token", "refresh_token", "password", "cookie", "raw_message_body"):
        check(token not in payload, f"sensitive field leaked: {token}")
    check(result["raw_message_stored"] is False, "privacy marker wrong")


def main() -> int:
    tests = [
        test_fixed_quiet_cross_midnight_and_same_day,
        test_invalid_fixed_quiet_falls_back_safely,
        test_asleep_outside_legacy_quiet_is_more_protective,
        test_forced_awake_inside_legacy_quiet_is_more_permissive,
        test_winding_down_and_drowsy_are_protected,
        test_hard_exempt_classes_bypass_sleep_and_quiet,
        test_disabled_off_and_unknown_phase_fail_open,
        test_watcher_logs_shadow_but_does_not_enforce,
        test_control_queue_bypasses_sleep_quiet_shadow,
        test_legacy_quiet_remains_authoritative,
        test_invalid_shadow_policy_fails_open_in_watcher,
        test_observability_contains_no_secrets_or_raw_message,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"CIRCADIAN_SLEEP_QUIET_PASS {test.__name__}")
        except Exception as exc:
            failures.append(f"{test.__name__}:{type(exc).__name__}:{exc}")
            print(f"CIRCADIAN_SLEEP_QUIET_FAIL {failures[-1]}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
