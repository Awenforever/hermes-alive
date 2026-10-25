#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import tempfile
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

# proactive_watcher bootstraps imports from HERMES_HOOK_DIR. Point it at
# this exact candidate tree so an installed /opt/data hook cannot shadow
# the code under test.
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)

import proactive_watcher as watcher_module
from circadian_engine import CircadianConfig, load_circadian_config
from managed_config import load_managed_env, managed_config_path
from proactive_watcher import ProactivePlatformWatcher


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def preserve_env(names: list[str]):
    return {name: os.environ.get(name) for name in names}


def restore_env(previous: dict[str, str | None]) -> None:
    for name, value in previous.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def test_env_config_mapping() -> None:
    names = [
        "HERMES_ALIVE_CIRCADIAN_ENABLED",
        "HERMES_ALIVE_CIRCADIAN_MODE",
        "HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME",
        "HERMES_ALIVE_CIRCADIAN_BASE_WAKE_TIME",
        "HERMES_ALIVE_CIRCADIAN_IDEAL_SLEEP_MINUTES",
        "HERMES_ALIVE_CIRCADIAN_EXPLICIT_USER_PREFERENCE_WEIGHT",
        "HERMES_ALIVE_CIRCADIAN_USER_CAN_DELAY_SLEEP",
        "HERMES_ALIVE_CIRCADIAN_TIMEZONE",
        "TZ",
    ]
    previous = preserve_env(names)
    try:
        os.environ["HERMES_ALIVE_CIRCADIAN_ENABLED"] = "true"
        os.environ["HERMES_ALIVE_CIRCADIAN_MODE"] = "shadow"
        os.environ["HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME"] = "23:20"
        os.environ["HERMES_ALIVE_CIRCADIAN_BASE_WAKE_TIME"] = "07:15"
        os.environ["HERMES_ALIVE_CIRCADIAN_IDEAL_SLEEP_MINUTES"] = "495"
        os.environ["HERMES_ALIVE_CIRCADIAN_EXPLICIT_USER_PREFERENCE_WEIGHT"] = "0.8"
        os.environ["HERMES_ALIVE_CIRCADIAN_USER_CAN_DELAY_SLEEP"] = "false"
        os.environ["HERMES_ALIVE_CIRCADIAN_TIMEZONE"] = "Asia/Singapore"
        config = load_circadian_config()
        check(config.enabled is True, "enabled env not loaded")
        check(config.mode == "shadow", "mode env not loaded")
        check(config.base_sleep_time == "23:20", "sleep env not loaded")
        check(config.base_wake_time == "07:15", "wake env not loaded")
        check(config.ideal_sleep_minutes == 495, "integer env not parsed")
        check(abs(config.explicit_user_preference_weight - 0.8) < 1e-9, "float env not parsed")
        check(config.user_can_delay_sleep is False, "bool env not parsed")
    finally:
        restore_env(previous)


def test_managed_config_to_env() -> None:
    shared = Path(tempfile.mkdtemp(prefix="circadian-managed-"))
    names = [
        "HERMES_ALIVE_SHARED_DIR",
        "HERMES_ALIVE_CIRCADIAN_ENABLED",
        "HERMES_ALIVE_CIRCADIAN_MODE",
        "HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME",
        "HERMES_ALIVE_CIRCADIAN_BASE_WAKE_TIME",
        "HERMES_ALIVE_CIRCADIAN_MAX_USER_DELAY_MINUTES",
    ]
    previous = preserve_env(names)
    try:
        os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
        path = managed_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"values": {
            "circadian_enabled": True,
            "circadian_mode": "shadow",
            "base_sleep_time": "23:00",
            "base_wake_time": "07:00",
            "max_user_delay_minutes": 150,
        }}), encoding="utf-8")
        loaded = load_managed_env(overwrite=True)
        check(loaded["HERMES_ALIVE_CIRCADIAN_ENABLED"] == "true", "managed enabled missing")
        check(loaded["HERMES_ALIVE_CIRCADIAN_MODE"] == "shadow", "managed mode missing")
        check(loaded["HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME"] == "23:00", "managed sleep missing")
        check(loaded["HERMES_ALIVE_CIRCADIAN_MAX_USER_DELAY_MINUTES"] == "150", "managed int missing")
        cfg = CircadianConfig.from_env()
        check(cfg.base_wake_time == "07:00", "managed env not consumable")
    finally:
        restore_env(previous)


def test_disabled_and_off_fail_open() -> None:
    for values, reason in [
        ({"enabled": False, "mode": "shadow"}, "disabled"),
        ({"enabled": True, "mode": "off"}, "mode_off"),
    ]:
        shared = Path(tempfile.mkdtemp(prefix="circadian-off-"))
        engine = __import__("circadian_engine").CircadianEngine(
            config=values,
            state_path=shared / "state.json",
        )
        decision = engine.shadow_decision(message_class="proactive_social")
        check(decision["would_allow_proactive"] is True, "disabled/off must fail open")
        check(decision["reason"] == reason, f"wrong fail-open reason: {decision}")


class DummyAdapter:
    async def send(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None):
        return SimpleNamespace(success=True, error=None)


class FakeCircadian:
    def __init__(self) -> None:
        self.calls = 0

    def shadow_decision(self, *, message_class: str):
        self.calls += 1
        return {
            "engine": "circadian",
            "mode": "shadow",
            "message_class": message_class,
            "would_allow_proactive": False,
            "would_block_proactive": True,
            "reason": "deep_sleep_core",
        }


async def _install_tick_stubs(watcher: ProactivePlatformWatcher, *, control_sent: bool = False) -> dict[str, Any]:
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

    def cooldown(self):
        return None

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
    watcher._cooldown = MethodType(cooldown, watcher)
    watcher._check_discovery = MethodType(discovery, watcher)
    watcher._check_dream = MethodType(dream, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    return state


def test_watcher_observes_but_does_not_enforce() -> None:
    previous = preserve_env(["HERMES_PROACTIVE_PLATFORM_ENABLED"])
    try:
        os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        fake = FakeCircadian()
        watcher._circadian_engine = fake
        records: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: records.append((decision, extra))
        state = asyncio.run(_install_tick_stubs(watcher))
        result = asyncio.run(watcher._tick_impl("shadow-test"))
        check(result is False, "empty delivery should return false")
        check(fake.calls == 1, "circadian decision not evaluated")
        check(state["compose_called"] is True, "shadow decision incorrectly blocked watcher")
        rows = [extra for decision, extra in records if decision == "circadian_shadow"]
        check(len(rows) == 1, "circadian observability record missing")
        check(rows[0]["behavior_changed"] is False, "shadow must declare no behavior change")
        check(rows[0]["circadian"]["watcher_enforced"] is False, "decision enforcement marker wrong")
    finally:
        restore_env(previous)


def test_control_queue_bypasses_circadian() -> None:
    previous = preserve_env(["HERMES_PROACTIVE_PLATFORM_ENABLED"])
    try:
        os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        fake = FakeCircadian()
        watcher._circadian_engine = fake
        watcher._log = lambda decision, **extra: None
        asyncio.run(_install_tick_stubs(watcher, control_sent=True))
        result = asyncio.run(watcher._tick_impl("control-test"))
        check(result is True, "control send should terminate tick successfully")
        check(fake.calls == 0, "control queue must bypass circadian social decision")
    finally:
        restore_env(previous)


def test_invalid_config_fails_open() -> None:
    names = [
        "HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME",
        "HERMES_ALIVE_CIRCADIAN_MODE",
    ]
    previous = preserve_env(names)
    try:
        os.environ["HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME"] = "99:99"
        os.environ["HERMES_ALIVE_CIRCADIAN_MODE"] = "shadow"
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        decision = watcher._circadian_shadow_decision(message_class="proactive_social")
        check(decision is None, "invalid config must fail open")
    finally:
        restore_env(previous)


def test_shadow_observability_has_no_secret_fields() -> None:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    watcher._circadian_engine = FakeCircadian()
    decision = watcher._circadian_shadow_decision(message_class="proactive_social")
    payload = json.dumps(decision, ensure_ascii=False).lower()
    for token in ("api_key", "access_token", "refresh_token", "password", "cookie"):
        check(token not in payload, f"secret field leaked: {token}")


def main() -> int:
    tests = [
        test_env_config_mapping,
        test_managed_config_to_env,
        test_disabled_and_off_fail_open,
        test_watcher_observes_but_does_not_enforce,
        test_control_queue_bypasses_circadian,
        test_invalid_config_fails_open,
        test_shadow_observability_has_no_secret_fields,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"CIRCADIAN_SHADOW_PASS {test.__name__}")
        except Exception as exc:
            failures.append(f"{test.__name__}:{type(exc).__name__}:{exc}")
            print(f"CIRCADIAN_SHADOW_FAIL {failures[-1]}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_CIRCADIAN_SHADOW_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_CIRCADIAN_SHADOW_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
