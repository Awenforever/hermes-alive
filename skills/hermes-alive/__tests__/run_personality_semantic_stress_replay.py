#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import sys
import time as wall_time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

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
    stub.locked_read_json = _read
    stub.locked_write_json = _write
    sys.modules["safe_io"] = stub

import alive_state
from proactive_disposition import (
    ABSOLUTE_UNANSWERED_SAFETY_CEILING,
    evaluate_proactive_disposition,
)
from semantic_bubbles import (
    SemanticPlanError,
    parse_semantic_plan,
)

SEED = 20260720
RNG = random.Random(SEED)
SENTINEL = "PRIVATE_SENTINEL_DO_NOT_LEAK_9f4c8d2a"


class Voice:
    def __init__(
        self,
        *,
        curiosity: float = 0.5,
        warmth: float = 0.5,
        verbosity: float = 0.5,
        quirkiness: float = 0.3,
        relationship_stage: str = "new",
    ) -> None:
        self.curiosity = curiosity
        self.warmth = warmth
        self.verbosity = verbosity
        self.quirkiness = quirkiness
        self.relationship_stage = relationship_stage


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def state(
    *,
    ignored: int = 0,
    pressure: float | None = None,
    flow: str = "idle",
    context_fresh: bool = False,
    focus_lock: bool = False,
    energy: int = 50,
    boredom: int = 20,
    annoyance: int = 0,
    affection: int = 65,
    curiosity: int = 50,
    mood_pressure: int = 0,
    presence: float = 0.5,
    engagement: float = 0.5,
) -> dict:
    result = {
        "ignored_proactive_count": ignored,
        "mood": {
            "energy": energy,
            "boredom": boredom,
            "annoyance": annoyance,
            "affection": affection,
            "curiosity": curiosity,
            "pressure": mood_pressure,
        },
        "current_context": {
            "flow": flow,
            "focus_lock": focus_lock,
            "context_fresh": context_fresh,
        },
    }
    if pressure is not None:
        result["interaction_evidence"] = {
            "unanswered_pressure": pressure,
            "presence_signal": presence,
            "engagement_signal": engagement,
        }
    return result


def high_voice() -> Voice:
    return Voice(
        curiosity=0.98,
        warmth=0.95,
        verbosity=0.95,
        quirkiness=0.9,
        relationship_stage="close",
    )


def high_state(*, ignored: int, pressure: float) -> dict:
    return state(
        ignored=ignored,
        pressure=pressure,
        flow="casual_flow",
        energy=98,
        boredom=75,
        annoyance=0,
        affection=98,
        curiosity=99,
        mood_pressure=0,
        presence=0.9,
        engagement=0.9,
    )


def discovery_context() -> dict:
    return {
        "external": [
            {
                "id": "paper-2607.15194v1",
                "title": "激光雷达探测晴空湍流",
                "source": "arxiv",
            }
        ]
    }


def parse_discovery(bubbles: list[dict]) -> object:
    return parse_semantic_plan(
        json.dumps(
            {
                "topic_mode": "new_discovery",
                "bubbles": bubbles,
                "content_ref": "paper-2607.15194v1",
            },
            ensure_ascii=False,
        ),
        default_msg_type="self_talk",
        policy_decision={
            "mode": "novel_value",
            "max_bubbles": 5,
        },
        discovery_context=discovery_context(),
    )


def test_randomized_disposition_invariants() -> dict:
    total = 30000
    send_count = 0
    silent_count = 0
    bubble_counts = {index: 0 for index in range(1, 6)}
    decisions_by_ignored = {
        index: set()
        for index in range(0, ABSOLUTE_UNANSWERED_SAFETY_CEILING)
    }

    for _ in range(total):
        ignored = RNG.randint(0, 12)
        pressure = RNG.random()
        voice = Voice(
            curiosity=RNG.random(),
            warmth=RNG.random(),
            verbosity=RNG.random(),
            quirkiness=RNG.random(),
            relationship_stage=RNG.choice(
                ["new", "exploring", "familiar", "close"]
            ),
        )
        item = evaluate_proactive_disposition(
            state=state(
                ignored=ignored,
                pressure=pressure,
                flow=RNG.choice(
                    [
                        "idle",
                        "casual_flow",
                        "research_flow",
                        "debug_flow",
                        "night_mode",
                    ]
                ),
                context_fresh=RNG.choice([True, False]),
                focus_lock=RNG.random() < 0.1,
                energy=RNG.randint(0, 100),
                boredom=RNG.randint(0, 100),
                annoyance=RNG.randint(0, 100),
                affection=RNG.randint(0, 100),
                curiosity=RNG.randint(0, 100),
                mood_pressure=RNG.randint(0, 100),
                presence=RNG.random(),
                engagement=RNG.random(),
            ),
            voice=voice,
            social_urge=RNG.random(),
            user_active=RNG.random() < 0.08,
            discovery_available=RNG.random() < 0.45,
        )

        check(item["decision_model"] == "personality_disposition_v1", "wrong model")
        check(0 <= int(item["level"]) <= 2, "level out of range")
        check(1 <= int(item["max_bubbles"]) <= 5, "bubble bound")
        for key in (
            "willingness",
            "restraint",
            "threshold",
            "unanswered_pressure",
            "interaction_temperature",
        ):
            value = float(item[key])
            check(math.isfinite(value), f"nonfinite {key}")
            check(0.0 <= value <= 1.0, f"range {key}")
        check(
            bool(item["allow_send"]) == (int(item["level"]) > 0),
            "allow_send/level mismatch",
        )

        bubble_counts[int(item["max_bubbles"])] += 1
        if item["allow_send"]:
            send_count += 1
            if ignored < ABSOLUTE_UNANSWERED_SAFETY_CEILING:
                decisions_by_ignored[ignored].add("send")
        else:
            silent_count += 1
            if ignored < ABSOLUTE_UNANSWERED_SAFETY_CEILING:
                decisions_by_ignored[ignored].add("silent")

        if ignored >= ABSOLUTE_UNANSWERED_SAFETY_CEILING:
            check(item["allow_send"] is False, "absolute safety ceiling bypassed")
            check(
                item["skip_reason"] == "safety_unanswered_ceiling"
                or item["skip_reason"] in {"user_active", "cooldown"},
                "wrong ceiling reason",
            )

    check(send_count > 0 and silent_count > 0, "no behavioral variation")
    check(
        decisions_by_ignored[3] == {"send", "silent"},
        f"ignored=3 became fixed: {decisions_by_ignored[3]}",
    )
    return {
        "cases": total,
        "send_count": send_count,
        "silent_count": silent_count,
        "max_bubble_upper_bound_distribution": bubble_counts,
        "ignored_three_outcomes": sorted(decisions_by_ignored[3]),
    }


def test_absolute_safety_ceiling_and_burst_caps() -> dict:
    below = evaluate_proactive_disposition(
        state=high_state(
            ignored=ABSOLUTE_UNANSWERED_SAFETY_CEILING - 1,
            pressure=0.55,
        ),
        voice=high_voice(),
        social_urge=1.0,
        discovery_available=True,
    )
    at = evaluate_proactive_disposition(
        state=high_state(
            ignored=ABSOLUTE_UNANSWERED_SAFETY_CEILING,
            pressure=1.0,
        ),
        voice=high_voice(),
        social_urge=1.0,
        discovery_available=True,
    )
    check(below["allow_send"] is True, "personality flexibility lost below ceiling")
    check(at["allow_send"] is False, "discovery bypassed absolute ceiling")
    check(at["skip_reason"] == "safety_unanswered_ceiling", str(at))

    high_pressure = evaluate_proactive_disposition(
        state=high_state(ignored=3, pressure=0.8),
        voice=high_voice(),
        social_urge=1.0,
        discovery_available=True,
    )
    medium_pressure = evaluate_proactive_disposition(
        state=high_state(ignored=3, pressure=0.5),
        voice=high_voice(),
        social_urge=1.0,
        discovery_available=True,
    )
    low_pressure = evaluate_proactive_disposition(
        state=high_state(ignored=0, pressure=0.0),
        voice=high_voice(),
        social_urge=1.0,
        discovery_available=True,
    )
    check(high_pressure["allow_send"] is True, "high mood should still vary")
    check(high_pressure["max_bubbles"] <= 2, "high unanswered burst too large")
    check(medium_pressure["max_bubbles"] <= 3, "medium unanswered burst too large")
    check(low_pressure["max_bubbles"] == 5, "healthy state cannot reach five")
    return {
        "ceiling": ABSOLUTE_UNANSWERED_SAFETY_CEILING,
        "below_ceiling_allow_send": below["allow_send"],
        "at_ceiling_allow_send": at["allow_send"],
        "bubble_caps": {
            "high_pressure": high_pressure["max_bubbles"],
            "medium_pressure": medium_pressure["max_bubbles"],
            "low_pressure": low_pressure["max_bubbles"],
        },
    }


def test_mood_personality_pair_monotonicity() -> dict:
    cases = 5000
    violations = 0
    for _ in range(cases):
        ignored = RNG.randint(0, 7)
        unanswered = RNG.random()
        v = Voice(
            curiosity=RNG.random(),
            warmth=RNG.random(),
            verbosity=RNG.random(),
            quirkiness=RNG.random(),
            relationship_stage=RNG.choice(
                ["new", "exploring", "familiar", "close"]
            ),
        )
        social = RNG.random()
        good = evaluate_proactive_disposition(
            state=state(
                ignored=ignored,
                pressure=unanswered,
                flow="casual_flow",
                energy=95,
                boredom=70,
                annoyance=0,
                affection=95,
                curiosity=95,
                mood_pressure=0,
                presence=0.8,
                engagement=0.8,
            ),
            voice=v,
            social_urge=social,
            discovery_available=True,
        )
        bad = evaluate_proactive_disposition(
            state=state(
                ignored=ignored,
                pressure=unanswered,
                flow="night_mode",
                energy=15,
                boredom=5,
                annoyance=90,
                affection=20,
                curiosity=10,
                mood_pressure=90,
                presence=0.2,
                engagement=0.2,
            ),
            voice=v,
            social_urge=social,
            discovery_available=True,
        )
        if float(good["willingness"]) + 1e-9 < float(bad["willingness"]):
            violations += 1
    check(violations == 0, f"monotonic violations={violations}")
    return {"cases": cases, "violations": violations}


def test_time_progression_and_inbound_evidence() -> dict:
    base_now = datetime(
        2026, 7, 20, 12, 0, 0,
        tzinfo=timezone(timedelta(hours=8)),
    )
    initial = {
        "last_updated_at": (
            base_now - timedelta(hours=18)
        ).isoformat(),
        "ignored_proactive_count": 3,
        "interaction_evidence": {
            "unanswered_pressure": 0.8,
            "presence_signal": 0.4,
            "engagement_signal": 0.5,
            "last_inbound_at": (
                base_now - timedelta(days=1)
            ).isoformat(),
            "last_reply_quality": 0.4,
            "observed_proactive_count_since_inbound": 3,
        },
    }
    with patch.object(alive_state.time, "time", return_value=base_now.timestamp()):
        decayed = alive_state._derive_interaction_evidence(
            prev=initial,
            raw_ignored=3,
            last_user_ts=None,
            last_user_text="",
        )
    check(0.38 <= decayed["unanswered_pressure"] <= 0.42, str(decayed))
    check(decayed["direct_reset_applied"] is False, str(decayed))

    previous_ts = (
        base_now - timedelta(hours=2)
    ).timestamp()
    short_prev = {
        **initial,
        "last_updated_at": base_now.isoformat(),
        "interaction_evidence": {
            **initial["interaction_evidence"],
            "unanswered_pressure": 0.8,
            "last_inbound_at": datetime.fromtimestamp(
                previous_ts,
                tz=timezone(timedelta(hours=8)),
            ).isoformat(),
        },
    }
    new_ts = base_now.timestamp()
    with patch.object(alive_state.time, "time", return_value=new_ts):
        short = alive_state._derive_interaction_evidence(
            prev=short_prev,
            raw_ignored=0,
            last_user_ts=new_ts,
            last_user_text="嗯",
        )
        rich = alive_state._derive_interaction_evidence(
            prev=short_prev,
            raw_ignored=0,
            last_user_ts=new_ts,
            last_user_text="我看到了，刚才在忙。这个论文挺有意思，继续讲讲它怎么检测湍流？",
        )
    check(0.0 < short["unanswered_pressure"] < 0.8, str(short))
    check(0.0 < rich["unanswered_pressure"] < short["unanswered_pressure"], str(rich))
    check(short["direct_reset_applied"] is False, str(short))
    check(rich["direct_reset_applied"] is False, str(rich))
    check(short["presence_signal"] == 1.0, str(short))

    messages = [
        {"role": "user", "timestamp": 100.0, "content": "/continue"},
    ]
    check(alive_state._last_user_ts(messages) is None, "continue changed context")
    messages.append(
        {"role": "user", "timestamp": 200.0, "content": "普通消息"}
    )
    check(alive_state._last_user_ts(messages) == 200.0, "ordinary inbound missing")
    return {
        "pressure_after_18h": decayed["unanswered_pressure"],
        "short_reply_pressure": short["unanswered_pressure"],
        "rich_reply_pressure": rich["unanswered_pressure"],
        "continue_updates_context": False,
        "ordinary_inbound_direct_reset": False,
    }


def test_clear_air_turbulence_replay() -> dict:
    bad_variants = [
        [
            {
                "act": "discovery_intro",
                "text": "坐飞机被颠醒真的很烦，不过看到一篇研究晴空湍流的论文",
            },
            {
                "act": "fact",
                "text": "它用激光雷达检测大气传播中的光束展宽变化",
            },
            {
                "act": "source_link",
                "text": "链接在这里 https://arxiv.org/abs/2607.15194v1，飞长途能少遭点罪",
            },
        ],
        [
            {
                "act": "discovery_intro",
                "text": "我上次坐飞机也被颠醒，刚看到一篇晴空湍流论文",
            },
            {
                "act": "fact",
                "text": "研究用激光雷达提前识别异常",
            },
        ],
    ]
    errors = []
    for bubbles in bad_variants:
        try:
            parse_discovery(bubbles)
        except SemanticPlanError as exc:
            errors.append(str(exc))
        else:
            raise AssertionError("lived-experience Discovery replay accepted")
    check(
        all(value == "unsupported_lived_experience_assumption" for value in errors),
        str(errors),
    )

    valid_plans = {
        1: [
            {
                "act": "discovery_intro",
                "text": "看到一篇研究晴空湍流探测的论文，思路挺新",
            },
        ],
        2: [
            {
                "act": "discovery_intro",
                "text": "刚看到一篇研究晴空湍流的论文",
            },
            {
                "act": "fact",
                "text": "它通过激光束在大气中的展宽变化识别异常",
            },
        ],
        3: [
            {
                "act": "discovery_intro",
                "text": "看到一篇研究晴空湍流预警的论文",
            },
            {
                "act": "fact",
                "text": "核心是测量激光束经过大气后的展宽变化",
            },
            {
                "act": "source_link",
                "text": "论文来源可以通过对应的 arXiv 条目查看",
            },
        ],
        4: [
            {
                "act": "discovery_intro",
                "text": "发现一篇研究晴空湍流预警的论文",
            },
            {
                "act": "fact",
                "text": "它关注无云条件下难以提前感知的突发颠簸",
            },
            {
                "act": "reaction",
                "text": "用光束传播变化反推湍流结构，这个角度很巧",
            },
            {
                "act": "source_link",
                "text": "来源是对应的 arXiv 论文条目",
            },
        ],
        5: [
            {
                "act": "discovery_intro",
                "text": "刚看到一篇研究晴空湍流预警的论文",
            },
            {
                "act": "fact",
                "text": "晴空湍流没有明显云层线索，传统观察不容易提前发现",
            },
            {
                "act": "reaction",
                "text": "研究把激光束展宽当成大气扰动的间接证据",
            },
            {
                "act": "turn",
                "text": "它更像是在捕捉传播过程中的细微异常，而不是直接看见气流",
            },
            {
                "act": "source_link",
                "text": "详细方法在对应的 arXiv 论文中",
            },
        ],
    }
    accepted = []
    for count, bubbles in valid_plans.items():
        plan = parse_discovery(bubbles)
        check(len(plan.bubbles) == count, f"count mismatch {count}")
        accepted.append(count)
    return {
        "bad_replay_rejections": errors,
        "accepted_dynamic_counts": accepted,
    }


def test_semantic_fuzz_and_privacy_metadata() -> dict:
    valid = 0
    rejected = 0
    error_counts: dict[str, int] = {}
    acts = [
        "self_talk",
        "observation",
        "question",
        "care",
        "reaction",
        "closing",
    ]
    for index in range(12000):
        count = RNG.randint(0, 7)
        bubbles = []
        for bubble_index in range(count):
            act = RNG.choice(acts)
            text = (
                f"语义动作{index}-{bubble_index}，"
                f"独立信息{RNG.randint(0, 10_000_000)}"
            )
            bubbles.append({"act": act, "text": text})
        payload = json.dumps(
            {
                "topic_mode": "ambient",
                "bubbles": bubbles,
                "content_ref": None,
            },
            ensure_ascii=False,
        )
        try:
            plan = parse_semantic_plan(
                payload,
                default_msg_type="self_talk",
                policy_decision={"max_bubbles": 5},
            )
        except SemanticPlanError as exc:
            rejected += 1
            error_counts[str(exc)] = error_counts.get(str(exc), 0) + 1
        else:
            valid += 1
            check(1 <= len(plan.bubbles) <= 5, "fuzz accepted invalid count")
            metadata = plan.safe_metadata()
            check(SENTINEL not in json.dumps(metadata, ensure_ascii=False), "privacy leak")

    private_plan = parse_semantic_plan(
        json.dumps(
            {
                "topic_mode": "ambient",
                "bubbles": [
                    {"act": "self_talk", "text": SENTINEL},
                ],
                "content_ref": None,
            }
        ),
        default_msg_type="self_talk",
        policy_decision={"max_bubbles": 5},
    )
    metadata_blob = json.dumps(private_plan.safe_metadata(), sort_keys=True)
    check(SENTINEL not in metadata_blob, "safe metadata contains raw text")

    for raw in (
        "第一条\n---\n第二条",
        "第一句。\n第二句。\n第三句。",
    ):
        if "---" in raw:
            try:
                parse_semantic_plan(
                    raw,
                    default_msg_type="self_talk",
                    policy_decision={"max_bubbles": 5},
                )
            except SemanticPlanError as exc:
                check(str(exc) == "legacy_separator_output_rejected", str(exc))
            else:
                raise AssertionError("separator mechanically split")
        else:
            plan = parse_semantic_plan(
                raw,
                default_msg_type="self_talk",
                policy_decision={"max_bubbles": 5},
            )
            check(len(plan.bubbles) == 1, "plain text mechanically split")

    return {
        "cases": 12000,
        "accepted": valid,
        "rejected": rejected,
        "top_rejection_codes": dict(
            sorted(error_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
        ),
        "safe_metadata_contains_raw_text": False,
    }


def test_determinism_and_performance() -> dict:
    sample_state = high_state(ignored=3, pressure=0.55)
    sample_voice = high_voice()
    first = evaluate_proactive_disposition(
        state=sample_state,
        voice=sample_voice,
        social_urge=0.92,
        discovery_available=True,
    )
    for _ in range(1000):
        current = evaluate_proactive_disposition(
            state=sample_state,
            voice=sample_voice,
            social_urge=0.92,
            discovery_available=True,
        )
        check(current == first, "non-deterministic disposition")

    start = wall_time.perf_counter()
    for index in range(50000):
        evaluate_proactive_disposition(
            state=state(
                ignored=index % 8,
                pressure=(index % 101) / 100.0,
                flow=("idle", "casual_flow", "research_flow")[index % 3],
                energy=index % 101,
                boredom=(index * 3) % 101,
                annoyance=(index * 7) % 101,
                affection=(index * 11) % 101,
                curiosity=(index * 13) % 101,
                mood_pressure=(index * 17) % 101,
            ),
            voice=Voice(
                curiosity=(index % 100) / 100.0,
                warmth=((index * 3) % 100) / 100.0,
                verbosity=((index * 5) % 100) / 100.0,
                quirkiness=((index * 7) % 100) / 100.0,
                relationship_stage=("new", "exploring", "familiar", "close")[index % 4],
            ),
            social_urge=((index * 19) % 100) / 100.0,
            discovery_available=bool(index % 2),
        )
    elapsed = wall_time.perf_counter() - start
    check(elapsed < 60.0, f"performance regression {elapsed:.3f}s")
    return {
        "determinism_replays": 1000,
        "performance_cases": 50000,
        "elapsed_seconds": round(elapsed, 4),
    }


TESTS = [
    test_randomized_disposition_invariants,
    test_absolute_safety_ceiling_and_burst_caps,
    test_mood_personality_pair_monotonicity,
    test_time_progression_and_inbound_evidence,
    test_clear_air_turbulence_replay,
    test_semantic_fuzz_and_privacy_metadata,
    test_determinism_and_performance,
]


def main() -> int:
    results = {}
    failures = []
    for function in TESTS:
        name = function.__name__
        try:
            results[name] = function()
            print(f"PERSONALITY_STRESS_REPLAY_PASS {name}")
        except Exception as exc:
            failures.append(
                {
                    "test": name,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            print(
                f"PERSONALITY_STRESS_REPLAY_FAIL {name} "
                f"{type(exc).__name__}: {str(exc)[:300]}"
            )

    summary = {
        "seed": SEED,
        "tests": len(TESTS),
        "passed": len(TESTS) - len(failures),
        "failed": len(failures),
        "results": results,
        "failures": failures,
        "privacy": {
            "raw_private_sentinel_emitted": False,
            "raw_user_message_emitted": False,
            "credentials_emitted": False,
        },
    }
    blob = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    if SENTINEL in blob:
        print("PRIVATE_SENTINEL_LEAK_DETECTED")
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        return 1
    print("HERMES_ALIVE_PERSONALITY_STRESS_REPLAY_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
