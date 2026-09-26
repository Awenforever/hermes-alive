#!/usr/bin/env python3
"""Production Circadian + Dynamic Sleep/Quiet enforcement contracts V1."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
SCRIPTS = ROOT / "scripts"
import sys
for path in (HOOKS, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ["HERMES_HOOK_DIR"] = str(HOOKS)

from circadian_engine import CircadianConfig, CircadianEngine  # noqa: E402
from circadian_sleep_quiet_policy import (  # noqa: E402
    evaluate_sleep_quiet_live,
    evaluate_sleep_quiet_policy,
)
from isolated_enforcement import enforcement_gate  # noqa: E402
from managed_config import load_managed_env, managed_config_path  # noqa: E402
from proactive_watcher import ProactivePlatformWatcher  # noqa: E402

TZ = timezone(timedelta(hours=8))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def live_env() -> dict[str, str | None]:
    keys = {
        "HERMES_ALIVE_CIRCADIAN_ENABLED": "true",
        "HERMES_ALIVE_CIRCADIAN_MODE": "live",
        "HERMES_ALIVE_QUALITY_GOVERNOR_MODE": "off",
        "HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE": None,
        "HERMES_ALIVE_RUNTIME_SCOPE": None,
    }
    previous = {k: os.environ.get(k) for k in keys}
    for k, v in keys.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return previous


def shadow_env() -> dict[str, str | None]:
    previous = live_env()
    os.environ["HERMES_ALIVE_CIRCADIAN_MODE"] = "shadow"
    return previous


def restore_env(previous: dict[str, str | None]) -> None:
    for k, v in previous.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def decision(*, phase: str, mode: str = "live", integrity: bool = True, hard_exempt: bool = False) -> dict[str, Any]:
    protected = phase in {"asleep", "light_sleep"}
    return {
        "engine": "circadian",
        "enabled": True,
        "mode": mode,
        "shadow_only": mode == "shadow",
        "message_class": "proactive_social",
        "hard_exempt": hard_exempt,
        "phase": phase,
        "deep_sleep_core": phase == "asleep",
        "state_integrity_ok": integrity,
        "would_allow_proactive": hard_exempt or not protected,
        "would_block_proactive": (not hard_exempt) and protected,
        "reason": "dynamic_sleep_window" if protected else "awake",
        "planned_sleep_at": None,
        "planned_wake_at": None,
        "sleep_debt_minutes": 0,
    }


class FakeCircadian:
    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value
        self.calls = 0

    def shadow_decision(self, *, message_class: str):
        self.calls += 1
        out = dict(self.value)
        out["message_class"] = message_class
        return out


class DummyAdapter:
    def __init__(self, *, success: bool = True) -> None:
        self.contents: list[str] = []
        self.success = success

    async def send(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None):
        self.contents.append(content)
        return SimpleNamespace(
            success=self.success,
            error=None if self.success else "synthetic delivery failure",
        )


class FakeCooldown:
    def __init__(self, *, allowed: bool = True, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason
        self.records: list[str] = []
        self.attempts: list[str] = []

    def set_mood_cooldown(self, social_urge: float | None) -> None:
        pass

    def can_send(self, msg_type: str):
        return self.allowed, self.reason

    def record_send(self, msg_type: str) -> None:
        self.records.append(msg_type)

    def record_attempt(self, msg_type: str) -> None:
        self.attempts.append(msg_type)


async def install_tick_stubs(
    watcher: ProactivePlatformWatcher,
    adapter: DummyAdapter,
    *,
    circadian: dict[str, Any],
    cooldown: FakeCooldown | None = None,
) -> dict[str, Any]:
    state = {"compose_calls": 0}
    watcher._circadian_engine = FakeCircadian(circadian)

    async def process_control(self, adapter_obj, chat_id, tick_id):
        return False

    def resolve(self):
        return adapter, "human-peer"

    def control(self):
        return {"enabled_override": True}

    def voice(self):
        return None

    def inactive(self):
        return False

    def policy(self, **kwargs: Any):
        return None

    def cooldown_fn(self):
        return cooldown

    async def none_async(self, *args: Any, **kwargs: Any):
        return None

    async def compose(self, voice=None, discovery_context=None, policy_decision=None):
        state["compose_calls"] += 1
        return [("casual", "production-enforcement-test", "test-model")]

    def no_delivery(self):
        return None

    def no_interest(self, *args: Any, **kwargs: Any):
        return False

    def no_topic(self):
        return None

    def no_quality_pre(self, *, user_active: bool):
        return None

    def no_quality_audits(self, messages, pre):
        return []

    def keep_quality(self, messages, audits, pre):
        return list(messages), None

    def no_quality_commit(self, *args: Any, **kwargs: Any):
        return None

    watcher._process_control_queue = MethodType(process_control, watcher)
    watcher._resolve_adapter_and_chat_id = MethodType(resolve, watcher)
    watcher._control = MethodType(control, watcher)
    watcher._voice_state = MethodType(voice, watcher)
    watcher._user_active_recently = MethodType(inactive, watcher)
    watcher._evaluate_interruption_policy = MethodType(policy, watcher)
    watcher._cooldown = MethodType(cooldown_fn, watcher)
    watcher._check_discovery = MethodType(none_async, watcher)
    watcher._check_dream = MethodType(none_async, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    watcher._content_delivery = MethodType(no_delivery, watcher)
    watcher._record_interest_delivery = MethodType(no_interest, watcher)
    watcher._topic_dedup = MethodType(no_topic, watcher)
    watcher._proactive_quality_shadow_decision = MethodType(no_quality_pre, watcher)
    watcher._quality_candidate_shadow_audits = MethodType(no_quality_audits, watcher)
    watcher._apply_quality_enforcement = MethodType(keep_quality, watcher)
    watcher._commit_quality_delivery = MethodType(no_quality_commit, watcher)
    return state


def test_live_sleep_policy_blocks_protected_phase_outside_legacy_quiet() -> None:
    result = evaluate_sleep_quiet_live(
        decision(phase="asleep"),
        now=datetime(2026, 7, 12, 18, 0, tzinfo=TZ),
        environ={"TZ": "Asia/Singapore", "HERMES_PROACTIVE_QUIET_START": "23:00", "HERMES_PROACTIVE_QUIET_END": "07:00"},
    )
    check(result["integration_mode"] == "enforce", "live policy not enforce")
    check(result["watcher_enforced"] is True, "live policy not watcher enforced")
    check(result["would_block_dynamic"] is True, "protected phase did not block")
    check(result["legacy_would_allow"] is True, "legacy comparison expected allow")
    check(result["comparison"] == "dynamic_more_protective", "dynamic authority comparison wrong")


def test_live_awake_supersedes_fixed_quiet() -> None:
    result = evaluate_sleep_quiet_live(
        decision(phase="forced_awake"),
        now=datetime(2026, 7, 13, 1, 0, tzinfo=TZ),
        environ={"TZ": "Asia/Singapore", "HERMES_PROACTIVE_QUIET_START": "23:00", "HERMES_PROACTIVE_QUIET_END": "07:00"},
    )
    check(result["would_allow_dynamic"] is True, "forced awake should dynamically allow")
    check(result["legacy_would_block"] is True, "legacy quiet expected block")
    check(result["legacy_override"] is True, "live dynamic awake did not supersede fixed quiet")
    check(result["authoritative_source"] == "circadian_dynamic", "wrong authority source")


def test_live_unknown_and_invalid_state_fail_closed() -> None:
    unknown = evaluate_sleep_quiet_live(decision(phase="future_phase"))
    invalid = evaluate_sleep_quiet_live(decision(phase="awake", integrity=False))
    check(unknown["would_block_dynamic"] is True and unknown["fail_closed"] is True, "unknown live phase failed open")
    check(invalid["would_block_dynamic"] is True and invalid["dynamic_reason"] == "state_invalid_fail_closed", "invalid live state failed open")


def test_live_hard_exempt_bypasses_sleep() -> None:
    result = evaluate_sleep_quiet_live(
        decision(phase="asleep", hard_exempt=True),
        message_class="control_command",
    )
    check(result["hard_exempt"] is True, "hard exemption missing")
    check(result["would_allow_dynamic"] is True, "hard exemption blocked")


def test_shadow_dispatch_remains_observe_only_and_unknown_fail_open() -> None:
    result = evaluate_sleep_quiet_policy(decision(phase="future_phase", mode="shadow"))
    check(result["integration_mode"] == "observe_only", "shadow dispatch changed mode")
    check(result["watcher_enforced"] is False, "shadow dispatch enforced")
    check(result["would_allow_dynamic"] is True, "shadow unknown changed legacy fail-open behavior")
    check(result["dynamic_reason"] == "unknown_phase_fail_open", "shadow unknown reason changed")


def test_corrupt_persistent_state_is_live_fail_closed_and_not_overwritten() -> None:
    root = Path(tempfile.mkdtemp(prefix="circadian-live-corrupt-"))
    state = root / "circadian_state.json"
    sentinel = "{BROKEN-CIRCADIAN-SENTINEL"
    state.write_text(sentinel, encoding="utf-8")
    cfg = CircadianConfig.from_mapping({"mode": "live", "timezone": "Asia/Singapore"})
    engine = CircadianEngine(config=cfg, state_path=state, now_fn=lambda: datetime(2026, 7, 12, 18, 0, tzinfo=TZ))
    result = engine.shadow_decision(message_class="proactive_social")
    check(engine.state_integrity_ok is False, "corrupt state integrity not detected")
    check(result["would_block_proactive"] is True and result["fail_closed"] is True, "corrupt live state failed open")
    check(result["reason"] == "state_invalid_fail_closed", "corrupt live reason wrong")
    check(state.read_text(encoding="utf-8") == sentinel, "corrupt evidence was overwritten")


def test_watcher_live_sleep_blocks_before_compose() -> None:
    previous = live_env()
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        logs: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda name, **extra: logs.append((name, extra))
        state = asyncio.run(install_tick_stubs(watcher, adapter, circadian=decision(phase="asleep")))
        result = asyncio.run(watcher._tick_impl("live-sleep-block"))
        check(result is False, "live sleeping watcher returned send")
        check(state["compose_calls"] == 0, "composer ran before live sleep block")
        check(adapter.contents == [], "adapter sent during live sleep block")
        check(any(name == "circadian_sleep_quiet_enforcement" and extra["enforcement"]["block"] for name, extra in logs), "live sleep enforcement log missing")
        check(any(name == "skip" and extra.get("reason") in {"deep_sleep_core", "dynamic_sleep_window"} for name, extra in logs), "live sleep skip reason missing")
    finally:
        restore_env(previous)


def test_watcher_live_awake_overrides_legacy_quiet_and_sends() -> None:
    previous = live_env()
    try:
        adapter = DummyAdapter()
        cooldown = FakeCooldown(allowed=False, reason="quiet_hours")
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        logs: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda name, **extra: logs.append((name, extra))
        state = asyncio.run(install_tick_stubs(watcher, adapter, circadian=decision(phase="forced_awake"), cooldown=cooldown))
        result = asyncio.run(watcher._tick_impl("live-awake-override"))
        check(result is True, "live awake did not override legacy quiet")
        check(state["compose_calls"] == 1, "composer did not run after live awake override")
        check(adapter.contents == ["production-enforcement-test"], "expected single send missing")
        check(cooldown.records == ["casual"], "send was not committed to cooldown")
        check(any(name == "circadian_live_legacy_quiet_override" and extra["enforcement"]["override"] for name, extra in logs), "production quiet override evidence missing")
    finally:
        restore_env(previous)


def test_watcher_shadow_never_uses_production_enforcement() -> None:
    previous = shadow_env()
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        logs: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda name, **extra: logs.append((name, extra))
        asyncio.run(install_tick_stubs(watcher, adapter, circadian=decision(phase="asleep", mode="shadow"), cooldown=None))
        result = asyncio.run(watcher._tick_impl("shadow-still-observe"))
        check(result is True, "shadow mode unexpectedly blocked")
        check(any(name == "circadian_shadow" for name, _ in logs), "shadow circadian log missing")
        check(any(name == "sleep_quiet_policy_shadow" for name, _ in logs), "shadow sleep log missing")
        check(not any(name == "circadian_sleep_quiet_enforcement" for name, _ in logs), "production enforcement ran in shadow")
    finally:
        restore_env(previous)


def test_failed_delivery_records_backoff_without_counting_send() -> None:
    previous = live_env()
    try:
        adapter = DummyAdapter(success=False)
        cooldown = FakeCooldown()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        watcher._log = lambda name, **extra: None
        asyncio.run(
            install_tick_stubs(
                watcher,
                adapter,
                circadian=decision(phase="forced_awake"),
                cooldown=cooldown,
            )
        )
        result = asyncio.run(watcher._tick_impl("failed-delivery-backoff"))
        check(result is False, "failed delivery was reported as sent")
        check(cooldown.records == [], "failed delivery incremented successful-send cooldown")
        check(cooldown.attempts == ["casual"], "failed delivery did not persist attempt backoff")
        check(adapter.contents == ["production-enforcement-test"], "delivery retried inside one tick")
    finally:
        restore_env(previous)


def test_engine_unavailable_live_is_watcher_fail_closed() -> None:
    previous = live_env()
    try:
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        watcher._circadian_engine = False
        result = watcher._circadian_shadow_decision(message_class="proactive_social")
        check(isinstance(result, dict), "live unavailable engine returned no decision")
        check(result["would_block_proactive"] is True and result["fail_closed"] is True, "unavailable live engine failed open")
        sleep = watcher._sleep_quiet_policy_shadow_decision(result, message_class="proactive_social")
        enforce = watcher._circadian_sleep_precompose_enforcement(sleep)
        check(enforce is not None and enforce["block"] is True, "unavailable live engine did not block precompose")
    finally:
        restore_env(previous)


def test_isolated_test_guard_remains_test_only() -> None:
    check(enforcement_gate({"HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE": "live", "HERMES_ALIVE_RUNTIME_SCOPE": "production"})["enabled"] is False, "production-like isolated helper became active")
    check(enforcement_gate({"HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE": "isolated", "HERMES_ALIVE_RUNTIME_SCOPE": "isolated_test"})["enabled"] is True, "isolated test guard regressed")


def test_managed_enforcement_modes_override_stale_container_env() -> None:
    shared = Path(tempfile.mkdtemp(prefix="managed-enforcement-authority-"))
    keys = [
        "HERMES_ALIVE_SHARED_DIR",
        "HERMES_ALIVE_CIRCADIAN_ENABLED",
        "HERMES_ALIVE_CIRCADIAN_MODE",
        "HERMES_ALIVE_QUALITY_GOVERNOR_MODE",
    ]
    previous = {k: os.environ.get(k) for k in keys}
    try:
        os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
        os.environ["HERMES_ALIVE_CIRCADIAN_ENABLED"] = "false"
        os.environ["HERMES_ALIVE_CIRCADIAN_MODE"] = "shadow"
        os.environ["HERMES_ALIVE_QUALITY_GOVERNOR_MODE"] = "shadow"
        path = managed_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"values": {
            "circadian_enabled": True,
            "circadian_mode": "live",
            "quality_governor_mode": "enforce",
        }}), encoding="utf-8")
        loaded = load_managed_env(overwrite=False)
        check(loaded["HERMES_ALIVE_CIRCADIAN_ENABLED"] == "true", "managed circadian enabled did not override stale env")
        check(loaded["HERMES_ALIVE_CIRCADIAN_MODE"] == "live", "managed circadian live did not override stale env")
        check(loaded["HERMES_ALIVE_QUALITY_GOVERNOR_MODE"] == "enforce", "managed quality enforce did not override stale env")
        check(os.environ["HERMES_ALIVE_CIRCADIAN_MODE"] == "live", "effective circadian env not authoritative")
        handler_source = (HOOKS / "handler.py").read_text(encoding="utf-8")
        startup_body = handler_source.split("async def _startup", 1)[1]
        check(
            "_refresh_managed_env()" in startup_body,
            "gateway startup does not refresh authoritative managed config",
        )
    finally:
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_lifecycle_zero_touch_default_is_live() -> None:
    text = (SCRIPTS / "hermes-alive-lifecycle.py").read_text(encoding="utf-8")
    check('"circadian_mode": "live"' in text, "fresh lifecycle default is not live")
    check('choices=("off", "shadow", "live")' in text, "lifecycle no longer supports explicit mode choices")


def main() -> int:
    tests = [
        test_live_sleep_policy_blocks_protected_phase_outside_legacy_quiet,
        test_live_awake_supersedes_fixed_quiet,
        test_live_unknown_and_invalid_state_fail_closed,
        test_live_hard_exempt_bypasses_sleep,
        test_shadow_dispatch_remains_observe_only_and_unknown_fail_open,
        test_corrupt_persistent_state_is_live_fail_closed_and_not_overwritten,
        test_watcher_live_sleep_blocks_before_compose,
        test_watcher_live_awake_overrides_legacy_quiet_and_sends,
        test_failed_delivery_records_backoff_without_counting_send,
        test_watcher_shadow_never_uses_production_enforcement,
        test_engine_unavailable_live_is_watcher_fail_closed,
        test_isolated_test_guard_remains_test_only,
        test_managed_enforcement_modes_override_stale_container_env,
        test_lifecycle_zero_touch_default_is_live,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"PRODUCTION_ENFORCEMENT_PASS {test.__name__}")
        except Exception as exc:
            item = f"{test.__name__}:{type(exc).__name__}:{exc}"
            failures.append(item)
            print(f"PRODUCTION_ENFORCEMENT_FAIL {item}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_PRODUCTION_ENFORCEMENT_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_PRODUCTION_ENFORCEMENT_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
