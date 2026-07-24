#!/usr/bin/env python3
"""Contract tests for Circadian Intent & State Bridge Shadow V1."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from circadian_engine import CircadianConfig, CircadianEngine  # noqa: E402
from circadian_intent_bridge import (  # noqa: E402
    CircadianIntentBridge,
    process_latest_user_intent_shadow,
    recognize_circadian_intent,
)
import handler  # noqa: E402

TZ = timezone(timedelta(hours=8), name="Asia/Singapore")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def message(text: str, ts: float, message_id: int = 1) -> dict:
    return {
        "role": "user",
        "timestamp": ts,
        "content_snippet": text,
        "session_id": "test-session",
        "message_id": message_id,
    }


def engine_factory(root: Path, now: datetime, *, mode: str = "shadow"):
    cfg = CircadianConfig.from_mapping(
        {
            "timezone": "Asia/Singapore",
            "mode": mode,
            "daily_sleep_variance_minutes": 0,
            "daily_wake_variance_minutes": 0,
        }
    )

    def make() -> CircadianEngine:
        return CircadianEngine(
            config=cfg,
            state_path=root / "circadian_state.json",
            now_fn=lambda: now,
        )

    return make


def bridge_at(now: datetime, *, mode: str = "shadow"):
    root = Path(tempfile.mkdtemp(prefix="circadian-intent-"))
    bridge = CircadianIntentBridge(
        state_path=root / "bridge_state.json",
        log_path=root / "bridge_log.jsonl",
        engine_factory=engine_factory(root, now, mode=mode),
        now_fn=lambda: now.timestamp(),
    )
    return bridge, root


def test_recognizer_explicit_actions() -> None:
    cases = [
        ("晚安", "goodnight", "goodnight", None),
        ("你先睡吧", "go_sleep", "go_sleep", None),
        ("再陪我一会儿", "delay_sleep", "stay_with_me", 30),
        ("再陪我1小时", "delay_sleep", "stay_with_me", 60),
        ("醒醒", "wake", "wake", None),
    ]
    for text, intent, event, delay in cases:
        match = recognize_circadian_intent(text)
        check(match.intent == intent, f"wrong intent for {text}: {match}")
        check(match.engine_event == event, f"wrong event for {text}: {match}")
        check(match.actionable is True, f"action must be true for {text}")
        check(match.delay_minutes == delay, f"wrong delay for {text}: {match.delay_minutes}")


def test_recognizer_observations_and_queries() -> None:
    cases = [
        ("你睡了吗", "sleep_status_query"),
        ("你醒了吗", "wake_status_query"),
        ("我去睡了", "user_sleeping"),
        ("我还在忙", "user_busy"),
        ("我今晚熬夜", "user_late_night"),
    ]
    for text, intent in cases:
        match = recognize_circadian_intent(text)
        check(match.intent == intent, f"wrong observation/query for {text}: {match}")
        check(match.actionable is False, f"observation/query mutated state for {text}")
        check(match.engine_event is None, f"unexpected event for {text}")


def test_recognizer_false_positive_guards() -> None:
    for text in [
        "这个 sleep_now 函数报错了",
        "wake_up 字段应该怎么配",
        "我去睡了以后你继续跑测试",
        "天气不错，早点睡对身体好，但我还不睡",
        "睡眠状态机的代码需要修改",
    ]:
        match = recognize_circadian_intent(text)
        check(match.intent == "none", f"false positive for {text}: {match}")


def test_fresh_action_updates_shadow_state() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    bridge, root = bridge_at(now)
    result = bridge.process_queue({"messages": [message("晚安", now.timestamp(), 11)]})
    check(result["state_event_applied"] is True, "fresh goodnight was not applied")
    check(result["resulting_phase"] == "winding_down", f"wrong phase: {result}")
    check(result["delivery_enforced"] is False, "bridge enforced delivery")
    check(result["watcher_behavior_changed"] is False, "watcher behaviour changed")
    state = json.loads((root / "circadian_state.json").read_text(encoding="utf-8"))
    check(state["last_event"] == "goodnight", "engine event missing")


def test_duplicate_message_applies_once() -> None:
    now = datetime(2026, 7, 12, 22, 55, tzinfo=TZ)
    bridge, root = bridge_at(now)
    queue = {"messages": [message("再陪我1小时", now.timestamp(), 12)]}
    first = bridge.process_queue(queue)
    state1 = json.loads((root / "circadian_state.json").read_text(encoding="utf-8"))
    second = bridge.process_queue(queue)
    state2 = json.loads((root / "circadian_state.json").read_text(encoding="utf-8"))
    check(first["state_event_applied"] is True, "first delay not applied")
    check(second["duplicate"] is True, "duplicate not detected")
    check(second["processed"] is False, "duplicate should not process")
    check(state1["planned_sleep_at"] == state2["planned_sleep_at"], "duplicate extended sleep twice")
    check(state1["user_delay_minutes_today"] == state2["user_delay_minutes_today"], "duplicate delay accumulated")


def test_stale_message_is_recorded_but_not_applied() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    bridge, root = bridge_at(now)
    stale = now - timedelta(hours=3)
    result = bridge.process_queue({"messages": [message("晚安", stale.timestamp(), 13)]})
    check(result["reason"] == "stale_message", f"stale reason wrong: {result}")
    check(result["state_event_applied"] is False, "stale event applied")
    check(not (root / "circadian_state.json").exists(), "stale event created engine state")


def test_queries_and_user_observations_do_not_mutate_engine() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    for index, text in enumerate(["你睡了吗", "我去睡了", "我还在忙", "我今晚熬夜"], 20):
        bridge, root = bridge_at(now)
        result = bridge.process_queue({"messages": [message(text, now.timestamp(), index)]})
        check(result["processed"] is True, f"message not processed: {text}")
        check(result["state_event_applied"] is False, f"observation mutated state: {text}")
        check(not (root / "circadian_state.json").exists(), f"engine state created for {text}")


def test_non_shadow_mode_never_activates_bridge() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    bridge, root = bridge_at(now, mode="live")
    result = bridge.process_queue({"messages": [message("晚安", now.timestamp(), 30)]})
    check(result["reason"] == "shadow_mode_required", f"live mode was not rejected: {result}")
    check(result["state_event_applied"] is False, "live mode applied shadow bridge")
    check(not (root / "circadian_state.json").exists(), "live mode created engine state")


def test_privacy_records_store_no_raw_message() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    bridge, root = bridge_at(now)
    secret_text = "晚安 PRIVATE_SENTINEL_8f2a1c"
    result = bridge.process_queue({"messages": [message(secret_text, now.timestamp(), 31)]})
    payload = json.dumps(result, ensure_ascii=False)
    ledger = (root / "bridge_state.json").read_text(encoding="utf-8")
    log = (root / "bridge_log.jsonl").read_text(encoding="utf-8")
    for stored in (payload, ledger, log):
        check(secret_text not in stored, "raw message leaked")
        check("PRIVATE_SENTINEL_8f2a1c" not in stored, "private sentinel leaked")
    check(result["raw_message_stored"] is False, "privacy marker missing")


def test_handler_calls_shadow_bridge_and_preserves_boundary() -> None:
    original = sys.modules.get("circadian_intent_bridge")
    fake = ModuleType("circadian_intent_bridge")
    fake.process_latest_user_intent_shadow = lambda: {
        "intent": "go_sleep",
        "state_event_applied": True,
        "reason": "shadow_state_event_applied",
        "delivery_enforced": False,
        "watcher_behavior_changed": False,
    }
    sys.modules["circadian_intent_bridge"] = fake
    try:
        result = handler._process_circadian_intent_shadow()
        check(result["state_event_applied"] is True, "handler did not call bridge")
        check(result["delivery_enforced"] is False, "handler crossed delivery boundary")
        check(result["watcher_behavior_changed"] is False, "handler changed watcher behaviour")
    finally:
        if original is None:
            sys.modules.pop("circadian_intent_bridge", None)
        else:
            sys.modules["circadian_intent_bridge"] = original


def test_public_entry_reads_local_context_queue() -> None:
    now = time.time()
    original = sys.modules.get("context_tracker")
    fake = ModuleType("context_tracker")
    fake.read_context_queue = lambda refresh=False: {"messages": [message("你睡了吗", now, 41)]}
    sys.modules["context_tracker"] = fake
    try:
        result = process_latest_user_intent_shadow()
        check(result["intent"] == "sleep_status_query", f"public entry failed: {result}")
        check(result["state_event_applied"] is False, "query mutated state")
    finally:
        if original is None:
            sys.modules.pop("context_tracker", None)
        else:
            sys.modules["context_tracker"] = original


def main() -> int:
    tests = [
        test_recognizer_explicit_actions,
        test_recognizer_observations_and_queries,
        test_recognizer_false_positive_guards,
        test_fresh_action_updates_shadow_state,
        test_duplicate_message_applies_once,
        test_stale_message_is_recorded_but_not_applied,
        test_queries_and_user_observations_do_not_mutate_engine,
        test_non_shadow_mode_never_activates_bridge,
        test_privacy_records_store_no_raw_message,
        test_handler_calls_shadow_bridge_and_preserves_boundary,
        test_public_entry_reads_local_context_queue,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"CIRCADIAN_INTENT_PASS {test.__name__}")
        except Exception as exc:
            failures.append(f"{test.__name__}:{type(exc).__name__}:{exc}")
            print(f"CIRCADIAN_INTENT_FAIL {failures[-1]}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_CIRCADIAN_INTENT_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_CIRCADIAN_INTENT_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
