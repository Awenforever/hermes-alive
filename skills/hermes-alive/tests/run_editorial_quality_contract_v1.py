#!/usr/bin/env python3
"""Evidence-aware editorial review contracts."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))

from llm_message_composer import LLMMessageComposer  # noqa: E402
from semantic_bubbles import parse_semantic_plan  # noqa: E402


def response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        model="deepseek-flash",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(payload, ensure_ascii=False)
                )
            )
        ],
    )


ITEM = {
    "id": "story-1",
    "title": "A small shelter found homes for 40 cats",
    "summary": "The shelter reported 40 adoptions during 2026.",
    "publisher": "Example News",
    "published_at": "2026-09-26T08:00:00Z",
    "url": "https://example.com/story",
    "evidence_text": "The shelter reported 40 adoptions during 2026.",
}

CANDIDATE = json.dumps(
    {
        "topic_mode": "new_discovery",
        "bubbles": [
            {
                "act": "fact",
                "text": "这家小型收容所说，他们在 2026 年已经为 40 只猫找到了领养家庭",
                "evidence": [
                    "The shelter reported 40 adoptions during 2026."
                ],
            }
        ],
        "content_ref": "story-1",
    },
    ensure_ascii=False,
)


PASS_DIMENSIONS = {
    "factual_grounding": True,
    "informational_value": True,
    "source_and_time": True,
    "natural_voice": True,
    "minimal_bubbles": True,
    "coherent_whole": True,
}


def test_all_dimensions_are_required() -> None:
    composer = LLMMessageComposer()

    async def fake_call(**_kwargs):
        dimensions = dict(PASS_DIMENSIONS)
        dimensions["minimal_bubbles"] = False
        return response(
            {
                "pass": True,
                "dimensions": dimensions,
                "issues": ["two bubbles can be merged"],
            }
        )

    review = asyncio.run(
        composer._review_editorial_candidate(
            fake_call,
            CANDIDATE,
            {"external": [ITEM]},
            preferred_model="deepseek-flash",
        )
    )
    assert review["pass"] is False


def test_valid_reference_and_full_contract_pass() -> None:
    composer = LLMMessageComposer()

    async def fake_call(**_kwargs):
        return response(
            {
                "pass": True,
                "dimensions": PASS_DIMENSIONS,
                "issues": [],
            }
        )

    review = asyncio.run(
        composer._review_editorial_candidate(
            fake_call,
            CANDIDATE,
            {"external": [ITEM]},
            preferred_model="deepseek-flash",
        )
    )
    assert review["pass"] is True
    assert review["content_ref"] == "story-1"


def test_invalid_reference_fails_before_model_call() -> None:
    composer = LLMMessageComposer()
    called = False

    async def fake_call(**_kwargs):
        nonlocal called
        called = True
        return response({})

    candidate = CANDIDATE.replace("story-1", "invented-story")
    review = asyncio.run(
        composer._review_editorial_candidate(
            fake_call,
            candidate,
            {"external": [ITEM]},
            preferred_model="deepseek-flash",
        )
    )
    assert review["pass"] is False
    assert called is False


def test_prompt_contains_retrieved_evidence_and_metadata_only_boundary() -> None:
    composer = LLMMessageComposer()
    lines = composer._format_discovery(
        {
            "external": [
                ITEM,
                {
                    "id": "story-2",
                    "title": "Metadata only",
                    "source": "rss",
                    "evidence_status": "metadata_only",
                },
            ]
        }
    )
    rendered = "\n".join(lines)
    assert "页面正文证据=" in rendered
    assert "不得推断标题和摘要之外的细节" in rendered


def test_long_article_keeps_title_relevant_middle_passage() -> None:
    filler = "unrelated historical background " * 30
    lines = [f"{index} {filler}" for index in range(30)]
    lines[17] = (
        "Google Play billing changes made Conversations difficult to sustain, "
        "so the Android client is now free."
    )
    focused = LLMMessageComposer._focus_evidence(
        "\n".join(lines),
        title="Why Conversations Is Now Free on Google Play",
    )
    assert "billing changes" in focused
    assert len(focused) <= 10000


def test_distinct_facts_may_share_the_fact_act() -> None:
    plan = parse_semantic_plan(
        json.dumps(
            {
                "topic_mode": "new_discovery",
                "bubbles": [
                    {"act": "fact", "text": "第一条独立事实，说明事件本身。"},
                    {"act": "fact", "text": "第二条独立事实，说明事件的结果。"},
                ],
                "content_ref": "story-1",
            },
            ensure_ascii=False,
        ),
        default_msg_type="fact",
        policy_decision={"mode": "novel_value", "max_bubbles": 3},
        discovery_context={"external": [ITEM]},
        context_snapshot={},
    )
    assert len(plan.bubbles) == 2


def test_title_only_evidence_is_rejected() -> None:
    composer = LLMMessageComposer()
    candidate = json.dumps(
        {
            "topic_mode": "new_discovery",
            "bubbles": [
                {
                    "act": "fact",
                    "text": "一个只翻译标题的事实。",
                    "evidence": [ITEM["title"]],
                }
            ],
            "content_ref": "story-1",
        },
        ensure_ascii=False,
    )
    issue = composer._evidence_mapping_issue(candidate, ITEM)
    assert "only the title" in issue


def main() -> int:
    tests = [
        test_all_dimensions_are_required,
        test_valid_reference_and_full_contract_pass,
        test_invalid_reference_fails_before_model_call,
        test_prompt_contains_retrieved_evidence_and_metadata_only_boundary,
        test_long_article_keeps_title_relevant_middle_passage,
        test_distinct_facts_may_share_the_fact_act,
        test_title_only_evidence_is_rejected,
    ]
    for test in tests:
        test()
        print(f"EDITORIAL_QUALITY_CONTRACT_PASS {test.__name__}")
    print("HERMES_ALIVE_EDITORIAL_QUALITY_CONTRACT_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
