#!/usr/bin/env python3
"""Joint deterministic replay for Circadian, Sleep/Quiet, Quality and Weather shadow layers.

Markers:
- HERMES_ALIVE_CIRCADIAN_JOINT_SHADOW_REPLAY_V1
- HERMES_ALIVE_JOINT_REPLAY_PRIVACY_BOUNDARY_V1
- HERMES_ALIVE_JOINT_REPLAY_NO_ENFORCEMENT_V1
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
SCRIPTS = ROOT / "scripts"
for path in (HOOKS, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Keep every replay artifact in a private throw-away tree.
RUNTIME = Path(tempfile.mkdtemp(prefix="hermes-alive-joint-shadow-"))
os.environ["HERMES_ALIVE_SHARED_DIR"] = str(RUNTIME)
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)

from circadian_engine import CircadianConfig, CircadianEngine
from circadian_intent_bridge import CircadianIntentBridge
from circadian_sleep_quiet_policy import evaluate_sleep_quiet_shadow
from location_weather_profile import LocationCandidate, profile_values, safe_location_summary
from proactive_quality_governor import ProactiveQualityGovernor, QualityGovernorConfig
from proactive_watcher import ProactivePlatformWatcher

TZ = timezone(timedelta(hours=8), name="Asia/Singapore")
QUIET_ENV = {
    "TZ": "Asia/Singapore",
    "HERMES_ALIVE_CIRCADIAN_TIMEZONE": "Asia/Singapore",
    "HERMES_PROACTIVE_QUIET_START": "23:00",
    "HERMES_PROACTIVE_QUIET_END": "07:00",
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def set(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value

    def timestamp(self) -> float:
        return self.value.timestamp()


class Scenario:
    def __init__(self, now: datetime, *, name: str) -> None:
        self.root = Path(tempfile.mkdtemp(prefix=f"joint-{name}-", dir=RUNTIME))
        self.clock = Clock(now)
        self.config = CircadianConfig.from_mapping({
            "timezone": "Asia/Singapore",
            "mode": "shadow",
            "daily_sleep_variance_minutes": 0,
            "daily_wake_variance_minutes": 0,
            "base_sleep_time": "23:00",
            "base_wake_time": "07:00",
        })

    def engine(self) -> CircadianEngine:
        return CircadianEngine(
            config=self.config,
            state_path=self.root / "circadian_state.json",
            now_fn=self.clock.now,
        )

    def bridge(self) -> CircadianIntentBridge:
        return CircadianIntentBridge(
            state_path=self.root / "intent_state.json",
            log_path=self.root / "intent_log.jsonl",
            engine_factory=self.engine,
            now_fn=self.clock.timestamp,
        )

    def user(self, text: str, *, message_id: int) -> dict[str, Any]:
        return {
            "role": "user",
            "timestamp": self.clock.timestamp(),
            "content_snippet": text,
            "session_id": f"scenario-{self.root.name}",
            "message_id": message_id,
        }

    def apply(self, text: str, *, message_id: int) -> dict[str, Any]:
        return self.bridge().process_queue({"messages": [self.user(text, message_id=message_id)]})

    def decisions(self, *, message_class: str = "proactive_social") -> tuple[dict[str, Any], dict[str, Any]]:
        circadian = self.engine().shadow_decision(message_class=message_class, now=self.clock.now())
        quiet = evaluate_sleep_quiet_shadow(
            circadian,
            message_class=message_class,
            now=self.clock.now(),
            environ=QUIET_ENV,
        )
        return circadian, quiet


def alive(flow: str = "casual_flow") -> dict[str, Any]:
    return {
        "current_context": {"flow": flow, "focus_lock": flow == "debug_flow"},
        "ignored_proactive_count": 0,
        "mood": {"annoyance": 0},
    }


def context_queue(now: datetime, text: str = "刚才聊到一半") -> dict[str, Any]:
    ts = now.timestamp()
    return {
        "messages": [
            {"role": "user", "timestamp": ts - 600, "content_snippet": text, "session_id": "joint", "message_id": 1},
            {"role": "assistant", "timestamp": ts - 590, "content_snippet": "嗯", "session_id": "joint", "message_id": 2},
        ]
    }


def sent(text: str, at: datetime, *, msg_type: str = "casual") -> dict[str, Any]:
    return {
        "decision": "sent",
        "msg_type": msg_type,
        "message_preview": text,
        "time": at.isoformat(),
    }


def test_goodnight_flows_into_dynamic_sleep_protection() -> None:
    s = Scenario(datetime(2026, 7, 12, 22, 50, tzinfo=TZ), name="goodnight")
    result = s.apply("晚安", message_id=1)
    check(result["state_event_applied"] is True, "goodnight bridge event missing")
    check(result["resulting_phase"] == "winding_down", "goodnight did not start winding down")
    circadian, quiet = s.decisions()
    check(circadian["phase"] == "winding_down", "circadian phase mismatch")
    check(quiet["would_block_dynamic"] is True, "winding down should be protected")
    check(quiet["comparison"] == "dynamic_more_protective", "pre-quiet protection comparison wrong")
    check(quiet["watcher_enforced"] is False and quiet["behavior_changed"] is False, "shadow boundary crossed")


def test_sleep_transition_and_hard_exemption() -> None:
    s = Scenario(datetime(2026, 7, 12, 22, 50, tzinfo=TZ), name="sleep")
    s.apply("晚安", message_id=1)
    s.clock.set(datetime(2026, 7, 12, 22, 59, tzinfo=TZ))
    circadian, quiet = s.decisions()
    check(circadian["phase"] in {"asleep", "light_sleep"}, f"sleep transition missing: {circadian['phase']}")
    check(quiet["would_block_dynamic"] is True, "sleep should block social in shadow")
    exempt_circadian, exempt_quiet = s.decisions(message_class="email_watchdog")
    check(exempt_circadian["hard_exempt"] is True, "Email Watchdog exemption lost")
    check(exempt_quiet["would_allow_dynamic"] is True, "Email Watchdog dynamically blocked")
    check(exempt_quiet["comparison"] == "hard_exempt_bypass", "hard exemption comparison wrong")


def test_user_delay_temporarily_overrides_sleep_but_not_legacy_gate() -> None:
    s = Scenario(datetime(2026, 7, 12, 22, 50, tzinfo=TZ), name="delay")
    result = s.apply("再陪我1小时", message_id=1)
    check(result["state_event_applied"] is True, "delay intent not applied")
    check(result["resulting_phase"] == "forced_awake", "delay did not create forced_awake")
    s.clock.set(datetime(2026, 7, 12, 23, 30, tzinfo=TZ))
    circadian, quiet = s.decisions()
    check(circadian["phase"] == "forced_awake", f"forced awake lost early: {circadian['phase']}")
    check(quiet["would_allow_dynamic"] is True, "dynamic policy ignored user delay")
    check(quiet["legacy_would_block"] is True, "legacy quiet comparison should remain blocking")
    check(quiet["comparison"] == "dynamic_more_permissive", "delay comparison wrong")
    check(quiet["watcher_enforced"] is False, "shadow delay changed delivery")


def test_forced_wake_creates_debt_and_allows_dynamic_reply() -> None:
    s = Scenario(datetime(2026, 7, 12, 22, 50, tzinfo=TZ), name="wake")
    s.apply("晚安", message_id=1)
    s.clock.set(datetime(2026, 7, 13, 1, 30, tzinfo=TZ))
    result = s.apply("醒醒", message_id=2)
    check(result["state_event_applied"] is True, "wake intent not applied")
    check(result["resulting_phase"] == "forced_awake", "wake did not create forced_awake")
    check(result["sleep_debt_minutes"] > 0, "early wake did not create sleep debt")
    _, quiet = s.decisions()
    check(quiet["would_allow_dynamic"] is True, "forced wake should allow dynamic reply")
    check(quiet["legacy_would_block"] is True, "legacy quiet should remain authoritative in shadow")


def test_user_observation_does_not_mutate_hermes_sleep() -> None:
    s = Scenario(datetime(2026, 7, 12, 22, 40, tzinfo=TZ), name="observation")
    before = s.engine().snapshot()
    result = s.apply("我还在忙", message_id=1)
    after = s.engine().snapshot()
    check(result["intent"] == "user_busy", "user-busy observation not recognized")
    check(result["state_event_applied"] is False, "user observation mutated Hermes state")
    check(before["planned_sleep_at"] == after["planned_sleep_at"], "observation changed sleep plan")


def test_learning_is_slow_and_bounded() -> None:
    s = Scenario(datetime(2026, 7, 13, 23, 40, tzinfo=TZ), name="learning")
    engine = s.engine()
    first = engine.apply_learning_signal(
        sleep_offset_minutes=90,
        signal="repeated_interaction",
        at=s.clock.now(),
    )
    first_offset = int(first["learned_sleep_offset_minutes"])
    check(0 < first_offset <= 10, f"single signal learned too quickly: {first_offset}")
    for day in range(1, 5):
        when = datetime(2026, 7, 13 + day, 23, 40, tzinfo=TZ)
        engine.apply_learning_signal(
            sleep_offset_minutes=90,
            signal="repeated_interaction",
            at=when,
        )
    final = engine.snapshot(update=False)
    check(int(final["learned_sleep_offset_minutes"]) <= 40, "weekly learning cap exceeded")
    check(int(final["learned_sleep_offset_minutes"]) < 90, "habit jumped directly to observation")


def test_affective_pulse_is_single_and_then_decays_to_silence() -> None:
    now = datetime(2026, 7, 12, 15, 0, tzinfo=TZ)
    root = Path(tempfile.mkdtemp(prefix="joint-quality-", dir=RUNTIME))
    governor = ProactiveQualityGovernor(
        QualityGovernorConfig(
            casual_affect_probability=1.0,
            proactive_origin_multiplier=1.0,
            silence_after_unanswered=2,
        ).validated(),
        state_path=root / "quality_state.json",
    )
    queue = context_queue(now)
    pre = governor.pre_decision(
        alive_state=alive(),
        context_queue=queue,
        proactive_records=[],
        now=now,
    )
    check(pre["affective_pulse_selected"] is True, "eligible casual silence pulse not selected")
    first = governor.audit_candidate("人呢", pre_decision=pre, proactive_records=[], now=now)
    check(first["would_allow"] is True, f"first mild affect rejected: {first}")
    later = governor.pre_decision(
        alive_state=alive(),
        context_queue=queue,
        proactive_records=[sent("人呢", now + timedelta(minutes=1))],
        now=now + timedelta(minutes=2),
    )
    second = governor.audit_candidate(
        "又消失",
        pre_decision=later,
        proactive_records=[sent("人呢", now + timedelta(minutes=1))],
        now=now + timedelta(minutes=2),
    )
    check(second["would_reject"] is True, "same silence episode repeated affect")
    records = [
        sent("人呢", now + timedelta(minutes=1)),
        sent("我在这", now + timedelta(minutes=2)),
    ]
    exhausted = governor.pre_decision(
        alive_state=alive(),
        context_queue=queue,
        proactive_records=records,
        now=now + timedelta(minutes=3),
    )
    check(exhausted["silence_lock"] is True, "unanswered budget did not enter silence")
    check(exhausted["recommended_action"] == "silence", "budget exhaustion escalated instead of silencing")
    check(exhausted["affective_pulse_selected"] is False, "silence lock selected another affect pulse")


def test_debug_silence_is_not_interpreted_as_rejection() -> None:
    now = datetime(2026, 7, 12, 15, 0, tzinfo=TZ)
    root = Path(tempfile.mkdtemp(prefix="joint-debug-", dir=RUNTIME))
    governor = ProactiveQualityGovernor(
        QualityGovernorConfig(casual_affect_probability=1.0).validated(),
        state_path=root / "quality_state.json",
    )
    pre = governor.pre_decision(
        alive_state=alive("debug_flow"),
        context_queue=context_queue(now, "bash docker 审计脚本 回传包"),
        proactive_records=[],
        now=now,
    )
    check(pre["debug_or_workflow"] is True, "debug flow not detected")
    check(pre["affective_pulse_selected"] is False, "debug silence triggered emotion")
    audit = governor.audit_candidate(
        "还没跑完？",
        pre_decision=pre,
        proactive_records=[],
        now=now,
        persist_shadow_state=False,
    )
    check("task_state_without_fresh_evidence" in audit["reasons"], "unsupported task-state claim escaped")


def test_historical_repetition_is_collapsed() -> None:
    now = datetime(2026, 7, 12, 15, 0, tzinfo=TZ)
    root = Path(tempfile.mkdtemp(prefix="joint-history-", dir=RUNTIME))
    governor = ProactiveQualityGovernor(
        QualityGovernorConfig(
            casual_affect_probability=1.0,
            proactive_origin_multiplier=1.0,
        ).validated(),
        state_path=root / "quality_state.json",
    )
    queue = context_queue(now)
    pre = governor.pre_decision(alive_state=alive(), context_queue=queue, proactive_records=[], now=now)
    historical = [
        "还在跟那堆配置较劲啊", "你忙你的，我在这待会儿", "还在跟它耗着呢？", "又消失",
        "还没搞定？ 😅", "我在这，你继续", "还没跑完？", "还在跟它耗着呢？",
        "我在这，你继续", "你那边天气怎么样，我这儿雷暴闷得有点喘不过气", "还在搞？我快成空气了",
        "呵", "你继续，我在这", "人呢", "还在跟它较劲呢？", "我在这儿，不吵你", "啧，还在跟它耗着啊",
    ]
    records: list[dict[str, Any]] = []
    allowed = 0
    false_weather_seen = False
    for index, text in enumerate(historical):
        at = now + timedelta(minutes=index)
        audit = governor.audit_candidate(
            text,
            pre_decision=pre,
            proactive_records=records,
            now=at,
            persist_shadow_state=True,
        )
        allowed += int(bool(audit["would_allow"]))
        false_weather_seen = false_weather_seen or "false_weather_or_physical_perspective" in audit["reasons"]
        records.append(sent(text, at, msg_type=str(audit["speech_act"])))
        pre = governor.pre_decision(
            alive_state=alive(),
            context_queue=queue,
            proactive_records=records,
            now=at + timedelta(minutes=1),
        )
    check(allowed <= 2, f"historical replay allowed too many candidates: {allowed}")
    check(false_weather_seen, "false weather perspective was not detected")


def test_confirmed_district_weather_uses_nonphysical_perspective() -> None:
    candidate = LocationCandidate(
        country_code="SG",
        admin1="Singapore",
        admin2="Tampines",
        admin3="Tampines East",
        locality="Tampines East",
        latitude=1.3521,
        longitude=103.9440,
        timezone="Asia/Singapore",
        source="user_confirmed",
        precision="district",
        confidence=1.0,
    )
    values = profile_values(candidate, confirmed=True)
    summary = safe_location_summary(values)
    check(summary["weather_location_confirmed"] is True, "district profile not confirmed")
    check(summary["weather_admin2"] == "Tampines", "district-equivalent location lost")
    check("weather_lat" in summary and "weather_lon" in summary, "confirmed coordinates missing")
    governor = ProactiveQualityGovernor(
        QualityGovernorConfig().validated(),
        state_path=RUNTIME / "weather-quality-state.json",
    )
    now = datetime(2026, 7, 12, 15, 0, tzinfo=TZ)
    pre = governor.pre_decision(
        alive_state=alive(),
        context_queue=context_queue(now),
        proactive_records=[],
        now=now,
    )
    good = governor.audit_candidate(
        "淡滨尼接下来几天可能都有雨，出门记得带伞",
        pre_decision=pre,
        proactive_records=[],
        now=now,
        persist_shadow_state=False,
    )
    bad = governor.audit_candidate(
        "我这儿雷暴闷得喘不过气",
        pre_decision=pre,
        proactive_records=[],
        now=now,
        persist_shadow_state=False,
    )
    check("false_weather_or_physical_perspective" not in good["reasons"], "valid local weather reminder rejected")
    check("false_weather_or_physical_perspective" in bad["reasons"], "physical weather perspective allowed")


class DummyAdapter:
    def __init__(self) -> None:
        self.contents: list[str] = []

    async def send(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None):
        self.contents.append(content)
        return SimpleNamespace(success=True, error=None)


async def install_watcher_stubs(watcher: ProactivePlatformWatcher, adapter: DummyAdapter) -> None:
    async def control(self, adapter_obj, chat_id, tick_id):
        return False

    def resolve(self):
        return adapter, "human-peer"

    def none(self, *args, **kwargs):
        return None

    def inactive(self):
        return False

    def policy(self, **kwargs):
        return {
            "allow_send": True,
            "allow_when_user_active": False,
            "allow_content_share": False,
        }

    async def none_async(self, *args, **kwargs):
        return None

    async def compose(self, voice=None, discovery_context=None, policy_decision=None):
        return [("casual", "我这儿雷暴闷得喘不过气", "joint-test-model")]

    watcher._process_control_queue = MethodType(control, watcher)
    watcher._resolve_adapter_and_chat_id = MethodType(resolve, watcher)
    watcher._voice_state = MethodType(none, watcher)
    watcher._user_active_recently = MethodType(inactive, watcher)
    watcher._evaluate_interruption_policy = MethodType(policy, watcher)
    watcher._cooldown = MethodType(none, watcher)
    watcher._check_discovery = MethodType(none_async, watcher)
    watcher._check_dream = MethodType(none_async, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    watcher._content_delivery = MethodType(none, watcher)
    watcher._record_interest_delivery = MethodType(lambda self, *a, **k: False, watcher)


def test_watcher_records_all_shadow_rejections_but_does_not_enforce() -> None:
    previous = os.environ.get("HERMES_PROACTIVE_PLATFORM_ENABLED")
    os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
    try:
        now = datetime(2026, 7, 13, 1, 0, tzinfo=TZ)
        scenario = Scenario(now, name="watcher")
        engine = scenario.engine()
        engine.apply_event("sleep_now", at=now - timedelta(hours=1))
        # Advance the stored engine into asleep/light_sleep at the replay time.
        engine.snapshot(now=now)

        quality_root = Path(tempfile.mkdtemp(prefix="joint-watcher-quality-", dir=RUNTIME))
        governor = ProactiveQualityGovernor(
            QualityGovernorConfig(casual_affect_probability=0.0).validated(),
            state_path=quality_root / "quality_state.json",
        )

        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        watcher._circadian_engine = engine
        watcher._proactive_quality_governor = governor
        records: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: records.append((decision, extra))
        asyncio.run(install_watcher_stubs(watcher, adapter))
        result = asyncio.run(watcher._tick_impl("joint-shadow"))

        check(result is True, "watcher did not complete shadow delivery")
        check(adapter.contents == ["我这儿雷暴闷得喘不过气"], "shadow unexpectedly enforced rejection")
        decisions = [name for name, _ in records]
        check("circadian_shadow" in decisions, "circadian shadow log missing")
        check("sleep_quiet_policy_shadow" in decisions, "sleep/quiet shadow log missing")
        check("proactive_quality_shadow" in decisions, "quality pre-decision log missing")
        audits = [extra["quality_candidate"] for name, extra in records if name == "proactive_quality_candidate_shadow"]
        check(len(audits) == 1, "quality candidate audit missing")
        check(audits[0]["would_reject"] is True, "bad weather candidate not shadow-rejected")
        check(audits[0]["watcher_enforced"] is False, "quality shadow enforced candidate")
        check(any(name == "sent" for name, _ in records), "legacy send path changed")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
        else:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = previous


def test_replay_artifacts_store_no_raw_private_sentinel() -> None:
    sentinel = "PRIVATE_JOINT_SENTINEL_51d3aa"
    s = Scenario(datetime(2026, 7, 12, 22, 50, tzinfo=TZ), name="privacy")
    result = s.apply(f"晚安 {sentinel}", message_id=99)
    check(result["raw_message_stored"] is False, "bridge privacy marker missing")
    for path in s.root.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            check(sentinel not in text, f"private sentinel leaked to {path.name}")
    check(result["delivery_enforced"] is False, "privacy replay crossed enforcement boundary")


def main() -> int:
    tests = [
        test_goodnight_flows_into_dynamic_sleep_protection,
        test_sleep_transition_and_hard_exemption,
        test_user_delay_temporarily_overrides_sleep_but_not_legacy_gate,
        test_forced_wake_creates_debt_and_allows_dynamic_reply,
        test_user_observation_does_not_mutate_hermes_sleep,
        test_learning_is_slow_and_bounded,
        test_affective_pulse_is_single_and_then_decays_to_silence,
        test_debug_silence_is_not_interpreted_as_rejection,
        test_historical_repetition_is_collapsed,
        test_confirmed_district_weather_uses_nonphysical_perspective,
        test_watcher_records_all_shadow_rejections_but_does_not_enforce,
        test_replay_artifacts_store_no_raw_private_sentinel,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"JOINT_SHADOW_REPLAY_PASS {test.__name__}")
        except Exception as exc:
            failures.append(f"{test.__name__}:{type(exc).__name__}:{exc}")
            print(f"JOINT_SHADOW_REPLAY_FAIL {failures[-1]}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_JOINT_SHADOW_REPLAY_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_JOINT_SHADOW_REPLAY_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
