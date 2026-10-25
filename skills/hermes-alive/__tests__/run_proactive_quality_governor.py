#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
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

from proactive_quality_governor import (
    ProactiveQualityGovernor,
    QualityGovernorConfig,
    normalize_text,
    semantic_similarity,
    speech_act,
    template_family,
)
from proactive_watcher import ProactivePlatformWatcher

UTC = timezone.utc
NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def queue(*, flow_text: str = "今天聊点轻松的", user_ts: float | None = None) -> dict[str, Any]:
    ts = user_ts if user_ts is not None else (NOW - timedelta(minutes=8)).timestamp()
    return {
        "messages": [
            {"role": "assistant", "timestamp": ts - 90, "content_snippet": "刚才聊到一半", "session_id": "s1", "message_id": 1},
            {"role": "user", "timestamp": ts, "content_snippet": flow_text, "session_id": "s1", "message_id": 2},
            {"role": "assistant", "timestamp": ts + 10, "content_snippet": "嗯", "session_id": "s1", "message_id": 3},
        ]
    }


def alive(flow: str = "casual_flow") -> dict[str, Any]:
    return {
        "current_context": {"flow": flow, "focus_lock": flow == "debug_flow"},
        "ignored_proactive_count": 0,
        "mood": {"annoyance": 0},
    }


def sent(text: str, minutes_ago: int, *, msg_type: str = "casual") -> dict[str, Any]:
    return {
        "decision": "sent",
        "msg_type": msg_type,
        "message_preview": text,
        "time": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
    }


def governor(**kwargs: Any) -> ProactiveQualityGovernor:
    temp = Path(tempfile.mkdtemp(prefix="quality-governor-test-"))
    config = QualityGovernorConfig(**kwargs).validated()
    return ProactiveQualityGovernor(config=config, state_path=temp / "state.json")


def test_config_parsing_and_validation() -> None:
    cfg = QualityGovernorConfig.from_env({
        "HERMES_ALIVE_QUALITY_GOVERNOR_ENABLED": "true",
        "HERMES_ALIVE_QUALITY_GOVERNOR_MODE": "shadow",
        "HERMES_ALIVE_QUALITY_SILENCE_AFTER_UNANSWERED": "3",
        "HERMES_ALIVE_QUALITY_AFFECT_PROBABILITY_CASUAL": "0.4",
    })
    check(cfg.enabled is True and cfg.mode == "shadow", "config mode parse failed")
    check(cfg.silence_after_unanswered == 3, "silence budget parse failed")
    check(abs(cfg.casual_affect_probability - 0.4) < 1e-9, "probability parse failed")


def test_normalization_similarity_and_families() -> None:
    a = normalize_text("还在跟它耗着呢？")
    b = normalize_text("还在跟它较劲呢？")
    check(semantic_similarity(a, b) >= 0.78, "semantic paraphrase not detected")
    check(template_family("我在这，你继续") == "presence_companion", "presence family failed")
    check(template_family("还没跑完？") == "task_status", "task family failed")
    check(speech_act("呵") == "sulk", "sulk act failed")


def test_debug_flow_disables_affective_pulse() -> None:
    gov = governor(casual_affect_probability=1.0)
    decision = gov.pre_decision(
        alive_state=alive("debug_flow"),
        context_queue=queue(flow_text="bash docker 审计脚本 回传包"),
        proactive_records=[],
        now=NOW,
    )
    check(decision["debug_or_workflow"] is True, "debug context not detected")
    check(decision["affective_pulse_selected"] is False, "debug must disable affect pulse")
    check(decision["affect_probability"] == 0.0, "debug affect probability must be zero")


def test_affective_pulse_is_deterministic_and_single_use() -> None:
    gov = governor(casual_affect_probability=1.0, proactive_origin_multiplier=1.0)
    q = queue()
    pre = gov.pre_decision(alive_state=alive(), context_queue=q, proactive_records=[], now=NOW)
    check(pre["affective_pulse_selected"] is True, "forced affect pulse not selected")
    audit = gov.audit_candidate("人呢", pre_decision=pre, proactive_records=[], now=NOW)
    check(audit["would_allow"] is True, f"first selected affect pulse rejected: {audit}")
    later = gov.pre_decision(alive_state=alive(), context_queue=q, proactive_records=[], now=NOW + timedelta(minutes=2))
    check(later["affect_spent"] is True, "episode was not marked spent")
    check(later["affective_pulse_selected"] is False, "same episode selected affect twice")
    second = gov.audit_candidate("又消失", pre_decision=later, proactive_records=[], now=NOW + timedelta(minutes=2))
    check(second["would_reject"] is True, "repeated affect in same episode not rejected")
    check("affect_repeated_in_same_silence_episode" in second["reasons"], "missing repeated-affect reason")


def test_unanswered_budget_enters_silence_without_escalation() -> None:
    gov = governor(casual_affect_probability=1.0, proactive_origin_multiplier=1.0, silence_after_unanswered=2)
    q = queue()
    user_ts = q["messages"][1]["timestamp"]
    records = [
        {"decision": "sent", "msg_type": "casual", "message_preview": "在吗", "time": datetime.fromtimestamp(user_ts + 30, UTC).isoformat()},
        {"decision": "sent", "msg_type": "casual", "message_preview": "我先待会儿", "time": datetime.fromtimestamp(user_ts + 60, UTC).isoformat()},
    ]
    pre = gov.pre_decision(alive_state=alive(), context_queue=q, proactive_records=records, now=NOW)
    check(pre["silence_lock"] is True, "unanswered budget did not enter silence")
    check(pre["recommended_action"] == "silence", "silence recommendation wrong")
    check(pre["affective_pulse_selected"] is False, "silence lock must not escalate affect")


def test_semantic_duplicate_and_template_cooldowns() -> None:
    gov = governor()
    pre = gov.pre_decision(alive_state=alive(), context_queue=queue(), proactive_records=[], now=NOW)
    exact = gov.audit_candidate("我在这，你继续", pre_decision=pre, proactive_records=[sent("我在这，你继续", 10)], now=NOW, persist_shadow_state=False)
    check("exact_duplicate" in exact["reasons"], "exact duplicate missed")
    paraphrase = gov.audit_candidate("还在跟它较劲呢？", pre_decision=pre, proactive_records=[sent("还在跟它耗着呢？", 20)], now=NOW, persist_shadow_state=False)
    check(paraphrase["would_reject"] is True, "semantic paraphrase not rejected")
    check("template_family_cooldown" in paraphrase["reasons"], "family cooldown missing")


def test_task_status_requires_fresh_structured_evidence() -> None:
    gov = governor()
    pre = gov.pre_decision(alive_state=alive(), context_queue=queue(), proactive_records=[], now=NOW)
    no_evidence = gov.audit_candidate("还没跑完？", pre_decision=pre, proactive_records=[], now=NOW, persist_shadow_state=False)
    check("task_state_without_fresh_evidence" in no_evidence["reasons"], "unsupported task-state claim allowed")
    evidence = {"status": "running", "observed_at": NOW.isoformat()}
    with_evidence = gov.audit_candidate("还没跑完？", pre_decision=pre, proactive_records=[], structured_state=evidence, now=NOW, persist_shadow_state=False)
    check("task_state_without_fresh_evidence" not in with_evidence["reasons"], "fresh evidence not accepted")


def test_weather_perspective_guard() -> None:
    gov = governor()
    pre = gov.pre_decision(alive_state=alive(), context_queue=queue(), proactive_records=[], now=NOW)
    bad = gov.audit_candidate("我这儿雷暴闷得有点喘不过气", pre_decision=pre, proactive_records=[], now=NOW, persist_shadow_state=False)
    check("false_weather_or_physical_perspective" in bad["reasons"], "false physical weather perspective missed")
    good = gov.audit_candidate("接下来一周都有雨，出门记得带伞", pre_decision=pre, proactive_records=[], now=NOW, persist_shadow_state=False)
    check("false_weather_or_physical_perspective" not in good["reasons"], "valid weather reminder incorrectly blocked")


def test_historical_sequence_is_not_allowed_to_repeat() -> None:
    gov = governor(casual_affect_probability=1.0, proactive_origin_multiplier=1.0)
    q = queue()
    pre = gov.pre_decision(alive_state=alive(), context_queue=q, proactive_records=[], now=NOW)
    historical = [
        "还在跟那堆配置较劲啊", "你忙你的，我在这待会儿", "还在跟它耗着呢？", "又消失",
        "还没搞定？ 😅", "我在这，你继续", "还没跑完？", "还在跟它耗着呢？",
        "我在这，你继续", "你那边天气怎么样，我这儿雷暴闷得有点喘不过气", "还在搞？我快成空气了",
        "呵", "你继续，我在这", "人呢", "还在跟它较劲呢？", "我在这儿，不吵你", "啧，还在跟它耗着啊",
    ]
    records: list[dict[str, Any]] = []
    allowed = 0
    for index, text in enumerate(historical):
        audit = gov.audit_candidate(text, pre_decision=pre, proactive_records=records, now=NOW + timedelta(minutes=index), persist_shadow_state=True)
        if audit["would_allow"]:
            allowed += 1
        records.append({"decision": "sent", "msg_type": audit["speech_act"], "message_preview": text, "time": (NOW + timedelta(minutes=index)).isoformat()})
        pre = gov.pre_decision(alive_state=alive(), context_queue=q, proactive_records=records, now=NOW + timedelta(minutes=index + 1))
    check(allowed <= 2, f"historical repetition allowed too many messages: {allowed}")


class DummyAdapter:
    def __init__(self) -> None:
        self.contents: list[str] = []

    async def send(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None):
        self.contents.append(content)
        return SimpleNamespace(success=True, error=None)


class FakeGovernor:
    def __init__(self) -> None:
        self.pre_calls = 0
        self.audit_calls = 0

    def pre_decision(self, **kwargs: Any) -> dict[str, Any]:
        self.pre_calls += 1
        return {
            "mode": "shadow", "watcher_enforced": False, "behavior_changed": False,
            "silence_episode_id": "episode", "affective_pulse_selected": False,
            "affect_spent": False, "silence_lock": True,
        }

    def audit_candidate(self, text: str, **kwargs: Any) -> dict[str, Any]:
        self.audit_calls += 1
        return {
            "would_allow": False, "would_reject": True,
            "reasons": ["shadow_reject"], "message_hash": "hash",
            "watcher_enforced": False, "behavior_changed": False,
        }


async def install_watcher_stubs(watcher: ProactivePlatformWatcher, adapter: DummyAdapter, *, control_sent: bool = False) -> None:
    async def process_control(self, adapter_obj, chat_id, tick_id):
        return control_sent
    def resolve(self):
        return adapter, "human-peer"
    def none(self, *args, **kwargs):
        return None
    def inactive(self):
        return False
    async def none_async(self, *args, **kwargs):
        return None
    async def compose(self, voice=None, discovery_context=None, policy_decision=None):
        return [("casual", "我在这，你继续", "test-model")]
    watcher._process_control_queue = MethodType(process_control, watcher)
    watcher._resolve_adapter_and_chat_id = MethodType(resolve, watcher)
    watcher._circadian_shadow_decision = MethodType(none, watcher)
    watcher._sleep_quiet_policy_shadow_decision = MethodType(none, watcher)
    watcher._voice_state = MethodType(none, watcher)
    watcher._user_active_recently = MethodType(inactive, watcher)
    watcher._evaluate_interruption_policy = MethodType(none, watcher)
    watcher._cooldown = MethodType(none, watcher)
    watcher._check_discovery = MethodType(none_async, watcher)
    watcher._check_dream = MethodType(none_async, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    watcher._content_delivery = MethodType(none, watcher)
    watcher._record_interest_delivery = MethodType(lambda self, *a, **k: False, watcher)


def test_watcher_observes_rejection_but_does_not_enforce() -> None:
    previous = os.environ.get("HERMES_PROACTIVE_PLATFORM_ENABLED")
    os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        fake = FakeGovernor()
        watcher._proactive_quality_governor = fake
        records: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: records.append((decision, extra))
        asyncio.run(install_watcher_stubs(watcher, adapter))
        result = asyncio.run(watcher._tick_impl("quality-shadow"))
        check(result is True, "shadow rejection incorrectly blocked send")
        check(adapter.contents == ["我在这，你继续"], "message content changed in shadow")
        check(fake.pre_calls == 1 and fake.audit_calls == 1, "governor not called exactly once")
        check(any(decision == "proactive_quality_shadow" for decision, _ in records), "pre-decision log missing")
        check(any(decision == "proactive_quality_candidate_shadow" for decision, _ in records), "candidate audit log missing")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
        else:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = previous


def test_control_queue_bypasses_quality_governor() -> None:
    previous = os.environ.get("HERMES_PROACTIVE_PLATFORM_ENABLED")
    os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        fake = FakeGovernor()
        watcher._proactive_quality_governor = fake
        watcher._log = lambda decision, **extra: None
        asyncio.run(install_watcher_stubs(watcher, adapter, control_sent=True))
        result = asyncio.run(watcher._tick_impl("control-bypass"))
        check(result is True, "control send should terminate tick")
        check(fake.pre_calls == 0 and fake.audit_calls == 0, "control queue must bypass quality governor")
    finally:
        if previous is None:
            os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
        else:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = previous


def test_observability_contains_no_raw_message_or_secrets() -> None:
    gov = governor(casual_affect_probability=1.0)
    pre = gov.pre_decision(alive_state=alive(), context_queue=queue(flow_text="PRIVATE_SENTINEL_8f2a1c"), proactive_records=[], now=NOW)
    audit = gov.audit_candidate("PRIVATE_SENTINEL_8f2a1c token=secret", pre_decision=pre, proactive_records=[], now=NOW, persist_shadow_state=False)
    payload = json.dumps({"pre": pre, "audit": audit}, ensure_ascii=False).lower()
    check("private_sentinel_8f2a1c" not in payload, "raw message leaked into observability")
    for token in ("api_key", "access_token", "refresh_token", "password", "cookie", "token=secret"):
        check(token not in payload, f"secret material leaked: {token}")


def main() -> int:
    tests = [
        test_config_parsing_and_validation,
        test_normalization_similarity_and_families,
        test_debug_flow_disables_affective_pulse,
        test_affective_pulse_is_deterministic_and_single_use,
        test_unanswered_budget_enters_silence_without_escalation,
        test_semantic_duplicate_and_template_cooldowns,
        test_task_status_requires_fresh_structured_evidence,
        test_weather_perspective_guard,
        test_historical_sequence_is_not_allowed_to_repeat,
        test_watcher_observes_rejection_but_does_not_enforce,
        test_control_queue_bypasses_quality_governor,
        test_observability_contains_no_raw_message_or_secrets,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"PROACTIVE_QUALITY_PASS {test.__name__}")
        except Exception as exc:
            failure = f"{test.__name__}:{type(exc).__name__}:{exc}"
            failures.append(failure)
            print(f"PROACTIVE_QUALITY_FAIL {failure}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_PROACTIVE_QUALITY_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_PROACTIVE_QUALITY_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
