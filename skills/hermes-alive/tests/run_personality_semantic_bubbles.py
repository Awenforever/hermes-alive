#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(ROOT))

try:
    import safe_io  # noqa: F401
except ModuleNotFoundError:
    stub = types.ModuleType("safe_io")
    def _read(path, default, lock_name):
        del path, lock_name
        return default
    def _write(path, value, lock_name):
        del path, value, lock_name
    def _append(path, value):
        del path, value
    stub.locked_read_json = _read
    stub.locked_write_json = _write
    stub.append_jsonl = _append
    sys.modules["safe_io"] = stub

import alive_state
from interruption_policy import InterruptionPolicy
from proactive_disposition import evaluate_proactive_disposition
from semantic_bubbles import (
    SemanticPlanError,
    parse_semantic_plan,
)
from voice_engine import VoiceGenome
import llm_message_composer


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def base_state(
    *,
    ignored: int = 0,
    unanswered_pressure: float | None = None,
    flow: str = "idle",
    mood: dict | None = None,
) -> dict:
    state = {
        "ignored_proactive_count": ignored,
        "mood": {
            "energy": 50,
            "boredom": 20,
            "annoyance": 0,
            "affection": 65,
            "curiosity": 50,
            "pressure": 0,
        },
        "current_context": {
            "flow": flow,
            "focus_lock": False,
            "context_fresh": True,
        },
    }
    if mood:
        state["mood"].update(mood)
    if unanswered_pressure is not None:
        state["interaction_evidence"] = {
            "unanswered_pressure": unanswered_pressure,
            "presence_signal": 0.5,
            "engagement_signal": 0.5,
        }
    return state


def voice(**values) -> VoiceGenome:
    item = VoiceGenome()
    for key, value in values.items():
        setattr(item, key, value)
    return item


def test_same_ignored_count_can_produce_different_behavior() -> None:
    low = evaluate_proactive_disposition(
        state=base_state(
            ignored=3,
            unanswered_pressure=0.82,
            mood={
                "energy": 20,
                "annoyance": 70,
                "pressure": 65,
                "affection": 30,
                "curiosity": 20,
            },
        ),
        voice=voice(
            curiosity=0.2,
            warmth=0.25,
            verbosity=0.25,
            quirkiness=0.1,
            relationship_stage="new",
        ),
        social_urge=0.15,
        discovery_available=True,
    )
    high = evaluate_proactive_disposition(
        state=base_state(
            ignored=3,
            unanswered_pressure=0.55,
            flow="casual_flow",
            mood={
                "energy": 90,
                "annoyance": 5,
                "pressure": 0,
                "affection": 90,
                "curiosity": 95,
                "boredom": 65,
            },
        ),
        voice=voice(
            curiosity=0.95,
            warmth=0.9,
            verbosity=0.8,
            quirkiness=0.8,
            relationship_stage="close",
        ),
        social_urge=0.95,
        discovery_available=True,
    )
    check(low["allow_send"] is False, f"low mood spoke: {low}")
    check(high["allow_send"] is True, f"high mood stayed silent: {high}")
    check(
        low["decision_model"] == high["decision_model"]
        == "personality_disposition_v1",
        "wrong decision model",
    )


def test_ignored_count_is_evidence_not_direct_switch() -> None:
    policy = InterruptionPolicy(state_engine=None)
    low = policy.evaluate(
        state=base_state(
            ignored=3,
            unanswered_pressure=0.8,
            mood={"annoyance": 70, "pressure": 60, "energy": 20},
        ),
        voice=voice(curiosity=0.2, warmth=0.2),
        social_urge=0.1,
        discovery_available=True,
    )
    high = policy.evaluate(
        state=base_state(
            ignored=3,
            unanswered_pressure=0.45,
            flow="casual_flow",
            mood={
                "annoyance": 0,
                "pressure": 0,
                "energy": 95,
                "affection": 95,
                "curiosity": 95,
            },
        ),
        voice=voice(
            curiosity=0.95,
            warmth=0.95,
            verbosity=0.85,
            quirkiness=0.8,
            relationship_stage="close",
        ),
        social_urge=0.98,
        discovery_available=True,
    )
    check(low["allow_send"] is False, str(low))
    check(high["allow_send"] is True, str(high))
    check(
        "disposition" in high
        and high["disposition"]["unanswered_pressure"] > 0,
        "missing evidence metadata",
    )


def test_ordinary_inbound_reduces_but_does_not_reset_pressure() -> None:
    previous = {
        "last_updated_at": alive_state.now_iso(),
        "ignored_proactive_count": 3,
        "interaction_evidence": {
            "unanswered_pressure": 0.8,
            "presence_signal": 0.2,
            "engagement_signal": 0.2,
            "last_inbound_at": "2026-07-20T09:00:00+08:00",
            "last_reply_quality": 0.2,
            "observed_proactive_count_since_inbound": 3,
        },
    }
    evidence = alive_state._derive_interaction_evidence(
        prev=previous,
        raw_ignored=0,
        last_user_ts=1784512980.0,
        last_user_text="嗯",
    )
    check(evidence["direct_reset_applied"] is False, str(evidence))
    check(
        0.0 < evidence["unanswered_pressure"] < 0.8,
        str(evidence),
    )


def test_continue_is_not_relationship_evidence() -> None:
    messages = [
        {
            "role": "user",
            "timestamp": 100.0,
            "content": "/continue",
        },
    ]
    check(alive_state._last_user_ts(messages) is None, "continue updated context")
    messages.append(
        {
            "role": "user",
            "timestamp": 200.0,
            "content": "普通消息",
        }
    )
    check(alive_state._last_user_ts(messages) == 200.0, "ordinary inbound missing")


def plan_payload(count: int) -> str:
    acts = [
        "self_talk",
        "observation",
        "question",
        "reaction",
        "closing",
    ]
    bubbles = [
        {
            "act": acts[index],
            "text": f"这是第{index + 1}个独立语义动作，内容{index + 1}",
        }
        for index in range(count)
    ]
    return json.dumps(
        {
            "topic_mode": "ambient",
            "bubbles": bubbles,
            "content_ref": None,
        },
        ensure_ascii=False,
    )


def test_dynamic_one_to_five_bubbles() -> None:
    for count in range(1, 6):
        plan = parse_semantic_plan(
            plan_payload(count),
            default_msg_type="self_talk",
            policy_decision={"max_bubbles": 5},
        )
        check(len(plan.bubbles) == count, f"{count}: {plan}")


def test_above_five_is_rejected() -> None:
    payload = json.loads(plan_payload(5))
    payload["bubbles"].append(
        {"act": "fact", "text": "第六个语义动作不应通过"}
    )
    try:
        parse_semantic_plan(
            json.dumps(payload, ensure_ascii=False),
            default_msg_type="self_talk",
            policy_decision={"max_bubbles": 5},
        )
    except SemanticPlanError as exc:
        check(str(exc) == "bubble_count_above_five", str(exc))
    else:
        raise AssertionError("six bubbles accepted")


def test_legacy_text_is_one_bubble_not_mechanical_split() -> None:
    plan = parse_semantic_plan(
        "第一句。第二句。第三句。",
        default_msg_type="self_talk",
        policy_decision={"max_bubbles": 5},
    )
    check(len(plan.bubbles) == 1, str(plan))
    try:
        parse_semantic_plan(
            "第一条\n---\n第二条",
            default_msg_type="self_talk",
            policy_decision={"max_bubbles": 5},
        )
    except SemanticPlanError as exc:
        check(str(exc) == "legacy_separator_output_rejected", str(exc))
    else:
        raise AssertionError("legacy separator was mechanically split")


def discovery_context() -> dict:
    return {
        "external": [
            {
                "id": "paper-1",
                "title": "晴空湍流激光雷达研究",
                "source": "arxiv",
            }
        ]
    }


def test_discovery_requires_new_topic_boundary() -> None:
    bad = {
        "topic_mode": "new_discovery",
        "bubbles": [
            {
                "act": "self_talk",
                "text": "突然想到坐飞机被颠醒真的很烦",
            },
            {
                "act": "fact",
                "text": "激光雷达可以检测晴空湍流",
            },
        ],
        "content_ref": "paper-1",
    }
    try:
        parse_semantic_plan(
            json.dumps(bad, ensure_ascii=False),
            default_msg_type="self_talk",
            policy_decision={
                "mode": "novel_value",
                "max_bubbles": 5,
            },
            discovery_context=discovery_context(),
        )
    except SemanticPlanError as exc:
        check(
            str(exc) in {
                "new_discovery_missing_intro_act",
                "new_discovery_missing_topic_anchor",
            },
            str(exc),
        )
    else:
        raise AssertionError("unsupported discovery opener accepted")

    good = {
        "topic_mode": "new_discovery",
        "bubbles": [
            {
                "act": "discovery_intro",
                "text": "看到一篇研究晴空湍流的论文",
            },
            {
                "act": "fact",
                "text": "它用激光雷达观察光束展宽来提前识别异常",
            },
            {
                "act": "source_link",
                "text": "论文链接我放在这里",
            },
        ],
        "content_ref": "paper-1",
    }
    plan = parse_semantic_plan(
        json.dumps(good, ensure_ascii=False),
        default_msg_type="self_talk",
        policy_decision={
            "mode": "novel_value",
            "max_bubbles": 5,
        },
        discovery_context=discovery_context(),
    )
    check(len(plan.bubbles) == 3, str(plan))


def test_cross_bubble_duplicate_is_rejected() -> None:
    payload = {
        "topic_mode": "ambient",
        "bubbles": [
            {"act": "self_talk", "text": "这个设计确实很有意思"},
            {"act": "reaction", "text": "这个设计确实很有意思！"},
        ],
        "content_ref": None,
    }
    try:
        parse_semantic_plan(
            json.dumps(payload, ensure_ascii=False),
            default_msg_type="self_talk",
            policy_decision={"max_bubbles": 5},
        )
    except SemanticPlanError as exc:
        check(str(exc) == "cross_bubble_semantic_duplicate", str(exc))
    else:
        raise AssertionError("duplicate bubbles accepted")


def test_policy_limit_is_respected() -> None:
    try:
        parse_semantic_plan(
            plan_payload(3),
            default_msg_type="self_talk",
            policy_decision={"max_bubbles": 2},
        )
    except SemanticPlanError as exc:
        check(str(exc) == "bubble_count_above_policy_limit", str(exc))
    else:
        raise AssertionError("policy bubble limit ignored")


def test_composer_contract_has_no_separator_instruction() -> None:
    prompt = llm_message_composer.SYSTEM_PROMPT
    check("多条用 ---" not in prompt, "separator instruction remains")
    check("用 --- 分隔" not in prompt, "separator instruction remains")
    check("1–5" in prompt, "1-5 contract missing")
    check("semantic" in prompt.lower() or "语义" in prompt, "semantic contract missing")


TESTS = [
    test_same_ignored_count_can_produce_different_behavior,
    test_ignored_count_is_evidence_not_direct_switch,
    test_ordinary_inbound_reduces_but_does_not_reset_pressure,
    test_continue_is_not_relationship_evidence,
    test_dynamic_one_to_five_bubbles,
    test_above_five_is_rejected,
    test_legacy_text_is_one_bubble_not_mechanical_split,
    test_discovery_requires_new_topic_boundary,
    test_cross_bubble_duplicate_is_rejected,
    test_policy_limit_is_respected,
    test_composer_contract_has_no_separator_instruction,
]


def main() -> None:
    failures = []
    for test in TESTS:
        try:
            test()
            print(f"PERSONALITY_SEMANTIC_PASS {test.__name__}")
        except Exception as exc:
            failures.append(
                {
                    "test": test.__name__,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(
                f"PERSONALITY_SEMANTIC_FAIL "
                f"{test.__name__}: {type(exc).__name__}: {exc}"
            )
    print(json.dumps(
        {"tests": len(TESTS), "failures": failures},
        ensure_ascii=False,
    ))
    if failures:
        raise SystemExit(1)
    print("HERMES_ALIVE_PERSONALITY_SEMANTIC_RESULT=PASS")


if __name__ == "__main__":
    main()
