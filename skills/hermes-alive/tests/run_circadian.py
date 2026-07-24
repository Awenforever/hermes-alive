#!/usr/bin/env python3
"""Deterministic contract tests for Circadian Engine Core V1."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from circadian_engine import (  # noqa: E402
    CircadianConfig,
    CircadianEngine,
    HARD_EXEMPT_CLASSES,
)

TZ = timezone(timedelta(hours=8), name="Asia/Singapore")


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def engine_at(now: datetime, **config_values):
    temp = Path(tempfile.mkdtemp(prefix="circadian-test-"))
    state = temp / "circadian_state.json"
    cfg = CircadianConfig.from_mapping(
        {
            "timezone": "Asia/Singapore",
            "daily_sleep_variance_minutes": 0,
            "daily_wake_variance_minutes": 0,
            **config_values,
        }
    )
    return CircadianEngine(config=cfg, state_path=state, now_fn=lambda: now), state


def test_deterministic_plan() -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=TZ)
    engine, state_path = engine_at(now)
    first = engine.snapshot()
    second = CircadianEngine(config=engine.config, state_path=state_path, now_fn=lambda: now).snapshot()
    check(first["daily_seed"] == second["daily_seed"], "daily seed drifted")
    check(first["planned_sleep_at"] == second["planned_sleep_at"], "sleep plan drifted")
    check(first["planned_wake_at"] == second["planned_wake_at"], "wake plan drifted")
    check(first["planned_sleep_at"].startswith("2026-07-12T23:00"), "default sleep anchor wrong")
    check(first["planned_wake_at"].startswith("2026-07-13T07:00"), "default wake anchor wrong")


def test_morning_cycle_date() -> None:
    now = datetime(2026, 7, 13, 6, 30, tzinfo=TZ)
    engine, _ = engine_at(now)
    state = engine.snapshot()
    check(state["schedule_date"] == "2026-07-12", "morning should belong to prior sleep cycle")


def test_winding_down_and_sleep() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    engine, _ = engine_at(now)
    state = engine.apply_event("goodnight", at=now)
    check(state["phase"] == "winding_down", "goodnight must start winding_down")
    later = now + timedelta(minutes=9)
    state = engine.snapshot(now=later)
    check(state["phase"] in {"asleep", "light_sleep"}, "pending sleep did not transition")
    check(state["actual_sleep_at"] is not None, "actual sleep fact missing")


def test_user_delay_and_bounds() -> None:
    now = datetime(2026, 7, 12, 22, 55, tzinfo=TZ)
    engine, _ = engine_at(now)
    state = engine.apply_event("keep_awake", at=now, delay_minutes=300)
    delayed = datetime.fromisoformat(state["planned_sleep_at"])
    check(state["phase"] == "forced_awake", "keep_awake phase wrong")
    check(delayed <= datetime(2026, 7, 13, 3, 0, tzinfo=TZ), "exceptional latest bound exceeded")
    wake = datetime.fromisoformat(state["planned_wake_at"])
    check((wake - delayed).total_seconds() >= 360 * 60, "minimum sleep violated")


def test_early_wake_creates_debt() -> None:
    now = datetime(2026, 7, 12, 23, 0, tzinfo=TZ)
    engine, _ = engine_at(now)
    engine.apply_event("sleep_now", at=now)
    engine.snapshot(now=now + timedelta(minutes=2))
    state = engine.apply_event("wake", at=datetime(2026, 7, 13, 4, 0, tzinfo=TZ))
    check(int(state["sleep_debt_minutes"]) >= 170, "early wake debt not accumulated")
    check(state["phase"] == "forced_awake", "forced wake phase wrong")


def test_shadow_and_hard_exemptions() -> None:
    now = datetime(2026, 7, 13, 1, 30, tzinfo=TZ)
    engine, _ = engine_at(now)
    normal = engine.shadow_decision(message_class="proactive_social", now=now)
    check(normal["shadow_only"] is True, "default mode must be shadow")
    check(normal["would_block_proactive"] is True, "sleeping social proactive should be blocked in decision")
    for category in HARD_EXEMPT_CLASSES:
        decision = engine.shadow_decision(message_class=category, now=now)
        check(decision["would_allow_proactive"] is True, f"hard exemption failed: {category}")
        check(decision["reason"] == "hard_exempt", f"hard exemption reason failed: {category}")


def test_learning_limits_and_decay() -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=TZ)
    engine, _ = engine_at(now)
    state = engine.apply_learning_signal(
        sleep_offset_minutes=120,
        signal="single_late_interaction",
        at=now,
    )
    check(0 < int(state["learned_sleep_offset_minutes"]) <= 10, "single signal exceeded daily limit")
    again = engine.apply_learning_signal(
        sleep_offset_minutes=120,
        signal="repeated_interaction",
        at=now,
    )
    check(int(again["learned_sleep_offset_minutes"]) <= 10, "same-day learning limit failed")
    engine.state.setdefault("learning", {})["last_decay_at"] = now.isoformat()
    engine.state["learned_sleep_offset_minutes"] = 20
    engine._save_state()
    decayed = engine.decay_learned_offsets(at=now + timedelta(days=14))
    check(decayed["learned_sleep_offset_minutes"] == 10, "weekly decay wrong")


def test_explicit_preference_has_higher_weight() -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=TZ)
    engine, _ = engine_at(now)
    state = engine.apply_learning_signal(
        sleep_offset_minutes=60,
        signal="explicit_user_preference",
        at=now,
    )
    check(int(state["learned_sleep_offset_minutes"]) == 40, "explicit preference should use weekly cap")


def test_persistence_and_prompt_facts() -> None:
    now = datetime(2026, 7, 12, 22, 50, tzinfo=TZ)
    engine, state_path = engine_at(now)
    first = engine.apply_event("goodnight", at=now)
    restored = CircadianEngine(config=engine.config, state_path=state_path, now_fn=lambda: now)
    second = restored.snapshot(update=False)
    check(first["pending_sleep_at"] == second["pending_sleep_at"], "pending transition not persisted")
    facts = restored.prompt_context(now=now)
    check(facts["facts_owned_by_engine"] is True, "prompt facts ownership marker missing")
    check("actual_sleep_at" in facts and "sleep_debt_minutes" in facts, "prompt facts incomplete")


def test_state_schema_and_no_secrets() -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=TZ)
    engine, state_path = engine_at(now)
    state = engine.snapshot()
    check(state["schema_version"] == 1, "state schema version wrong")
    payload = state_path.read_text(encoding="utf-8").lower()
    for token in ("api_key", "token", "password", "cookie"):
        check(token not in payload, f"state unexpectedly contains secret field: {token}")


def main() -> int:
    tests = [
        test_deterministic_plan,
        test_morning_cycle_date,
        test_winding_down_and_sleep,
        test_user_delay_and_bounds,
        test_early_wake_creates_debt,
        test_shadow_and_hard_exemptions,
        test_learning_limits_and_decay,
        test_explicit_preference_has_higher_weight,
        test_persistence_and_prompt_facts,
        test_state_schema_and_no_secrets,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"CIRCADIAN_PASS {test.__name__}")
        except Exception as exc:
            failures.append(f"{test.__name__}:{type(exc).__name__}:{exc}")
            print(f"CIRCADIAN_FAIL {failures[-1]}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_CIRCADIAN_CORE_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_CIRCADIAN_CORE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
