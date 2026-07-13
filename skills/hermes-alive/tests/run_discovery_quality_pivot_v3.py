#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
import sys
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

RUNTIME = Path(tempfile.mkdtemp(prefix="hermes-alive-pivot-v3-"))
os.environ["HERMES_ALIVE_SHARED_DIR"] = str(RUNTIME)
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)
os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
os.environ["HERMES_ALIVE_QUALITY_GOVERNOR_MODE"] = "enforce"
os.environ["HERMES_ALIVE_CONTEXT_FLOW_MAX_AGE_SECONDS"] = "3600"

import alive_state
import proactive_quality_governor as quality_module
import llm_message_composer
from interruption_policy import InterruptionPolicy
from proactive_quality_governor import (
    ProactiveQualityGovernor,
    QualityGovernorConfig,
    speech_act,
    template_family,
)
from proactive_watcher import ProactivePlatformWatcher
from safe_io import sha256_text


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sent_record(at: datetime, text: str = "在吗") -> dict[str, Any]:
    return {
        "decision": "sent",
        "msg_type": "casual",
        "message_preview": text,
        "time": at.isoformat(),
    }


def test_sent_event_window_counts_events_not_raw_lines() -> None:
    path = RUNTIME / "proactive_log.jsonl"
    base = datetime.now(timezone.utc) - timedelta(hours=2)
    rows: list[dict[str, Any]] = [sent_record(base, "第一条")]
    rows.extend(
        {"decision": "policy", "tick_id": f"n-{index}"}
        for index in range(300)
    )
    rows.append(sent_record(base + timedelta(minutes=30), "第二条"))
    rows.extend(
        {"decision": "compose", "tick_id": f"m-{index}"}
        for index in range(300)
    )
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    quality_module.PROACTIVE_LOG = path
    alive_state.PROACTIVE_LOG = path
    q_records = quality_module._read_proactive_records(limit=10)
    a_records = alive_state._read_proactive_records(limit=10)
    check(len(q_records) == 2, f"quality sent-event scan lost records: {len(q_records)}")
    check(len(a_records) == 2, f"alive sent-event scan lost records: {len(a_records)}")


def test_task_state_phrases_are_caught() -> None:
    samples = [
        "还在debug？",
        "还在硬扛？",
        "还在拆炸弹？",
        "是不是还在工作？",
    ]
    gov = ProactiveQualityGovernor(
        config=QualityGovernorConfig(mode="enforce"),
        state_path=RUNTIME / "quality-state.json",
    )
    pre = {
        "mode": "enforce",
        "silence_lock": False,
        "silence_episode_id": "episode",
        "affective_pulse_selected": False,
        "affect_spent": False,
    }
    for text in samples:
        check(template_family(text) == "task_status", f"family missed: {text}")
        check(speech_act(text) == "task_status", f"speech act missed: {text}")
        audit = gov.audit_candidate(
            text,
            pre_decision=pre,
            proactive_records=[],
            structured_state=None,
            persist_shadow_state=False,
        )
        check(
            "task_state_without_fresh_evidence" in audit["reasons"],
            f"unsupported task claim allowed: {text} -> {audit}",
        )


def test_topic_expiry_blocks_old_presence_and_affect() -> None:
    gov = ProactiveQualityGovernor(
        config=QualityGovernorConfig(mode="enforce"),
        state_path=RUNTIME / "quality-topic-expiry-state.json",
    )
    pre = {
        "mode": "enforce",
        "topic_expired": True,
        "silence_lock": False,
        "silence_episode_id": "episode",
        "affective_pulse_selected": False,
        "affect_spent": False,
    }
    samples = [
        "人呢？",
        "又不理我。",
        "还在debug？",
    ]
    for text in samples:
        audit = gov.audit_candidate(
            text,
            pre_decision=pre,
            proactive_records=[],
            structured_state=None,
            persist_shadow_state=False,
        )
        check(
            "old_topic_or_presence_after_unanswered"
            in audit["reasons"],
            f"expired-topic message allowed: {text} -> {audit}",
        )


def test_system_prompt_matches_unanswered_contract() -> None:
    prompt = llm_message_composer.SYSTEM_PROMPT
    forbidden = [
        "已读不回是吧",
        "你又在硬扛",
        "这轮像在拆炸弹",
    ]
    for value in forbidden:
        check(value not in prompt, f"legacy prompt encouragement remains: {value}")
    required = [
        "一次未回应就表示旧话题已经结束",
        "没有合格条目就保持沉默",
        "不得说他\"还在 debug\"",
    ]
    for value in required:
        check(value in prompt, f"new prompt contract missing: {value}")


def test_context_flow_uses_latest_fresh_user_episode() -> None:
    now = time.time()
    old = [
        {
            "role": "user",
            "timestamp": now - 7200,
            "content_snippet": "docker bash 审计脚本 回传包",
        },
        {
            "role": "assistant",
            "timestamp": now - 7190,
            "content_snippet": "继续检查 docker 日志",
        },
    ]
    flow, lock, signals = alive_state._classify_flow(old)
    check(flow != "debug_flow" and lock is False, f"stale debug survived: {flow}")
    check(signals["context_fresh"] is False, "stale context marked fresh")

    new_episode = old + [
        {
            "role": "user",
            "timestamp": now,
            "content_snippet": "这是一条测试消息",
        },
        {
            "role": "assistant",
            "timestamp": now + 1,
            "content_snippet": "收到",
        },
    ]
    flow, lock, signals = alive_state._classify_flow(new_episode)
    check(flow != "debug_flow" and lock is False, f"old episode leaked: {flow}")
    check(signals["context_fresh"] is True, "latest user episode not fresh")


def state(*, ignored: int, fresh: bool = True) -> dict[str, Any]:
    return {
        "current_context": {
            "flow": "debug_flow",
            "focus_lock": True,
            "context_fresh": fresh,
        },
        "ignored_proactive_count": ignored,
        "mood": {
            "annoyance": 0,
            "pressure": 85,
            "energy": 50,
        },
    }


def test_interruption_policy_pivots_after_one_unanswered() -> None:
    policy = InterruptionPolicy(state_engine=None)

    first = policy.evaluate(
        state=state(ignored=0, fresh=True),
        discovery_available=False,
    )
    check(first["mode"] == "ambient", f"fresh first check-in changed: {first}")

    no_value = policy.evaluate(
        state=state(ignored=1, fresh=True),
        discovery_available=False,
    )
    check(no_value["allow_send"] is False, f"unanswered fallback spoke: {no_value}")
    check(
        no_value["skip_reason"] == "unanswered_no_novel_value",
        f"wrong unanswered skip reason: {no_value}",
    )

    pivot = policy.evaluate(
        state=state(ignored=1, fresh=True),
        discovery_available=True,
    )
    check(pivot["mode"] == "novel_value", f"no discovery pivot: {pivot}")
    check(pivot["allow_new_topic"] is True, f"new topic blocked: {pivot}")
    check(pivot["allow_content_share"] is True, f"content share blocked: {pivot}")

    exhausted = policy.evaluate(
        state=state(ignored=2, fresh=True),
        discovery_available=True,
    )
    check(exhausted["allow_send"] is False, f"two unanswered still spoke: {exhausted}")
    check(
        exhausted["skip_reason"] == "unanswered_budget_exhausted",
        f"wrong silence lock: {exhausted}",
    )


class DummyAdapter:
    def __init__(self) -> None:
        self.contents: list[str] = []

    async def send(
        self,
        chat_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        self.contents.append(content)
        return SimpleNamespace(success=True, error=None)


class FakeGovernor:
    def __init__(self, *, allow: bool = True) -> None:
        self.allow = allow
        self.config = SimpleNamespace(mode="enforce")
        self.commits: list[dict[str, Any]] = []

    def audit_candidate(self, content: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "would_allow": self.allow,
            "would_reject": not self.allow,
            "reasons": [] if self.allow else ["forced_reject"],
            "message_hash": sha256_text(content),
            "affective_candidate": False,
            "silence_episode_id": None,
        }

    def commit_delivery(self, audit: dict[str, Any]) -> bool:
        self.commits.append(dict(audit))
        return True


async def install_watcher_stubs(
    watcher: ProactivePlatformWatcher,
    adapter: DummyAdapter,
    *,
    include_ref: bool,
    ref_value: str = "item-1",
) -> dict[str, Any]:
    trace = {
        "policy_discovery_values": [],
        "discovery_calls": 0,
    }

    async def process_control(self, adapter_obj, chat_id, tick_id):
        return False

    def resolve(self):
        return adapter, "human-peer"

    def no_shadow(self, *args: Any, **kwargs: Any):
        return None

    def quality_pre(self, *, user_active: bool):
        return {
            "mode": "enforce",
            "integration_mode": "enforce",
            "watcher_enforced": True,
            "silence_lock": False,
            "unanswered_count": 1,
            "topic_expired": True,
            "recommended_action": "novel_value_only",
        }

    def inactive(self):
        return False

    def policy(self, **kwargs: Any):
        available = bool(kwargs.get("discovery_available"))
        trace["policy_discovery_values"].append(available)
        if available:
            return {
                "level": 2,
                "mode": "novel_value",
                "allow_send": True,
                "allow_when_user_active": False,
                "allow_new_topic": True,
                "allow_content_share": True,
                "allow_emoji": True,
                "max_bubbles": 2,
                "preferred_speech_acts": ["content_share"],
                "reason": ["fresh_discovery_available"],
                "skip_reason": None,
                "prompt_directives": "use discovery",
            }
        return {
            "level": 0,
            "mode": "silent",
            "allow_send": False,
            "allow_when_user_active": False,
            "allow_new_topic": False,
            "allow_content_share": False,
            "allow_emoji": True,
            "max_bubbles": 1,
            "preferred_speech_acts": ["silent_marker"],
            "reason": ["unanswered_topic_expired"],
            "skip_reason": "unanswered_no_novel_value",
            "prompt_directives": "silent",
        }

    async def discovery(self):
        trace["discovery_calls"] += 1
        return {
            "external": [
                {
                    "id": "item-1",
                    "title": "一个新的研究发现",
                    "source": "arxiv",
                    "url": "https://example.invalid/item-1",
                }
            ],
            "local": [],
        }

    async def dream(self):
        return None

    async def compose(self, voice=None, discovery_context=None, policy_decision=None):
        messages = [
            ("content_share", "看到一个新的研究发现。", "test-model"),
        ]
        if include_ref:
            messages.append(
                ("__content_ref__", ref_value, "test-model")
            )
        return messages

    def no_cooldown(self):
        return None

    def no_voice(self):
        return None

    def no_delivery(self):
        return None

    watcher._process_control_queue = MethodType(process_control, watcher)
    watcher._resolve_adapter_and_chat_id = MethodType(resolve, watcher)
    watcher._circadian_shadow_decision = MethodType(no_shadow, watcher)
    watcher._sleep_quiet_policy_shadow_decision = MethodType(no_shadow, watcher)
    watcher._proactive_quality_shadow_decision = MethodType(quality_pre, watcher)
    watcher._voice_state = MethodType(no_voice, watcher)
    watcher._user_active_recently = MethodType(inactive, watcher)
    watcher._evaluate_interruption_policy = MethodType(policy, watcher)
    watcher._cooldown = MethodType(no_cooldown, watcher)
    watcher._check_discovery = MethodType(discovery, watcher)
    watcher._check_dream = MethodType(dream, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    watcher._content_delivery = MethodType(no_delivery, watcher)
    watcher._record_interest_delivery = MethodType(
        lambda self, *args, **kwargs: False,
        watcher,
    )
    watcher._proactive_quality_governor = FakeGovernor(allow=True)
    watcher._log = lambda *args, **kwargs: None
    return trace


def test_watcher_refreshes_discovery_then_sends_only_referenced_value() -> None:
    adapter = DummyAdapter()
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    trace = asyncio.run(
        install_watcher_stubs(watcher, adapter, include_ref=True)
    )
    result = asyncio.run(watcher._tick_impl("pivot-success"))
    check(result is True, "referenced discovery pivot did not send")
    check(trace["discovery_calls"] == 1, "discovery did not run")
    check(
        trace["policy_discovery_values"] == [False, True],
        f"policy was not re-evaluated after discovery: {trace}",
    )
    check(
        adapter.contents == ["看到一个新的研究发现。"],
        f"unexpected sent content: {adapter.contents}",
    )


def test_watcher_refuses_generic_fallback_without_content_ref() -> None:
    adapter = DummyAdapter()
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    trace = asyncio.run(
        install_watcher_stubs(watcher, adapter, include_ref=False)
    )
    result = asyncio.run(watcher._tick_impl("pivot-no-ref"))
    check(result is False, "generic fallback sent without content ref")
    check(trace["discovery_calls"] == 1, "discovery refresh was skipped")
    check(adapter.contents == [], "unreferenced message reached adapter")


def test_watcher_rejects_content_ref_outside_discovery_set() -> None:
    adapter = DummyAdapter()
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    trace = asyncio.run(
        install_watcher_stubs(
            watcher,
            adapter,
            include_ref=True,
            ref_value="not-a-real-item",
        )
    )
    result = asyncio.run(watcher._tick_impl("pivot-invalid-ref"))
    check(result is False, "invalid discovery reference was sent")
    check(trace["discovery_calls"] == 1, "discovery refresh was skipped")
    check(adapter.contents == [], "invalid reference reached adapter")


def test_live_quality_filter_is_fail_closed() -> None:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    pre = {"mode": "enforce"}
    messages = [
        ("debug_companion", "还在debug？", "test-model"),
        ("content_share", "一个有依据的新发现", "test-model"),
    ]
    audits = [
        {
            "would_allow": False,
            "would_reject": True,
            "reasons": ["task_state_without_fresh_evidence"],
            "message_hash": sha256_text(messages[0][1]),
        },
        {
            "would_allow": True,
            "would_reject": False,
            "reasons": [],
            "message_hash": sha256_text(messages[1][1]),
        },
    ]
    kept, decision = watcher._apply_quality_enforcement(
        messages,
        audits,
        pre,
    )
    check(kept == [messages[1]], f"live filter kept rejected message: {kept}")
    check(decision and decision["rejected_count"] == 1, f"bad filter decision: {decision}")

    kept, decision = watcher._apply_quality_enforcement(
        [messages[0]],
        [],
        pre,
    )
    check(kept == [], "missing audit was not fail-closed")
    check(decision and decision["missing_audit_count"] == 1, f"missing audit unreported: {decision}")



def test_live_precompose_fails_closed_without_quality_decision() -> None:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    watcher._proactive_quality_governor = False
    decision = watcher._quality_precompose_enforcement(
        None,
        None,
    )
    check(decision is not None, "missing fail-closed decision")
    check(decision["enabled"] is True, f"enforce disabled: {decision}")
    check(decision["block"] is True, f"missing decision allowed: {decision}")
    check(
        "quality_predecision_missing" in decision["reasons"],
        f"missing fail-closed reason: {decision}",
    )


def test_candidate_audit_failure_preserves_alignment() -> None:
    class FlakyGovernor:
        def __init__(self) -> None:
            self.config = SimpleNamespace(mode="enforce")
            self.calls = 0

        def audit_candidate(self, content: str, **_: Any) -> dict[str, Any]:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("injected audit failure")
            return {
                "would_allow": True,
                "would_reject": False,
                "reasons": [],
                "message_hash": sha256_text(content),
            }

    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    watcher._proactive_quality_governor = FlakyGovernor()
    messages = [
        ("debug_companion", "还在debug？", "test-model"),
        ("content_share", "一个有依据的新发现", "test-model"),
    ]
    pre = {"mode": "enforce"}
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        audits = watcher._quality_candidate_shadow_audits(
            messages,
            pre,
        )
    finally:
        logging.disable(previous_disable)
    check(len(audits) == 2, f"audit alignment lost: {audits}")
    check(
        audits[0]["message_hash"] == sha256_text(messages[0][1]),
        f"first audit hash mismatch: {audits[0]}",
    )
    check(
        audits[0]["would_reject"] is True,
        f"failed first audit was not rejected: {audits[0]}",
    )
    check(
        audits[1]["message_hash"] == sha256_text(messages[1][1]),
        f"second audit hash mismatch: {audits[1]}",
    )
    check(
        audits[1]["would_allow"] is True,
        f"second allowed audit was lost: {audits[1]}",
    )

    kept, decision = watcher._apply_quality_enforcement(
        messages,
        audits,
        pre,
    )
    check(kept == [messages[1]], f"misaligned message escaped: {kept}")
    check(
        decision and decision["rejected_count"] == 1,
        f"bad alignment decision: {decision}",
    )


def test_live_filter_rejects_audit_hash_mismatch() -> None:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    message = ("content_share", "真实候选正文", "test-model")
    audits = [
        {
            "would_allow": True,
            "would_reject": False,
            "reasons": [],
            "message_hash": sha256_text("另一条消息"),
        }
    ]
    kept, decision = watcher._apply_quality_enforcement(
        [message],
        audits,
        {"mode": "enforce"},
    )
    check(kept == [], "hash错配审计仍然放行")
    check(
        decision
        and decision["rejection_reasons"].get(
            "quality_audit_mismatch"
        )
        == 1,
        f"hash错配未记录: {decision}",
    )

def main() -> int:
    tests = [
        test_sent_event_window_counts_events_not_raw_lines,
        test_task_state_phrases_are_caught,
        test_topic_expiry_blocks_old_presence_and_affect,
        test_system_prompt_matches_unanswered_contract,
        test_context_flow_uses_latest_fresh_user_episode,
        test_interruption_policy_pivots_after_one_unanswered,
        test_watcher_refreshes_discovery_then_sends_only_referenced_value,
        test_watcher_refuses_generic_fallback_without_content_ref,
        test_watcher_rejects_content_ref_outside_discovery_set,
        test_live_quality_filter_is_fail_closed,
        test_live_precompose_fails_closed_without_quality_decision,
        test_candidate_audit_failure_preserves_alignment,
        test_live_filter_rejects_audit_hash_mismatch,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"DISCOVERY_PIVOT_V3_PASS {test.__name__}")
        except Exception as exc:
            failure = f"{test.__name__}:{type(exc).__name__}:{exc}"
            failures.append(failure)
            print(f"DISCOVERY_PIVOT_V3_FAIL {failure}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_DISCOVERY_PIVOT_V3_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_DISCOVERY_PIVOT_V3_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
