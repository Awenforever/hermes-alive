#!/usr/bin/env python3
"""Evidence-aware editorial review contracts."""

from __future__ import annotations

import asyncio
import json
import os
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


def test_evidence_failure_invokes_independent_rewriter() -> None:
    composer = LLMMessageComposer()
    candidate = json.dumps(
        {
            "topic_mode": "new_discovery",
            "bubbles": [
                {
                    "act": "fact",
                    "text": "这条事实的证据是模型编造的。",
                    "evidence": ["This sentence does not exist in the source."],
                }
            ],
            "content_ref": "story-1",
        },
        ensure_ascii=False,
    )
    called = False

    async def fake_call(**kwargs):
        nonlocal called
        called = True
        prompt = kwargs["messages"][-1]["content"]
        assert "确定性证据校验已发现" in prompt
        return response(
            {
                "pass": False,
                "dimensions": {
                    **PASS_DIMENSIONS,
                    "factual_grounding": False,
                },
                "issues": ["原候选没有逐字证据"],
                "replacement_plan": json.loads(CANDIDATE),
            }
        )

    review = asyncio.run(
        composer._review_editorial_candidate(
            fake_call,
            candidate,
            {"external": [ITEM]},
            preferred_model="deepseek-flash",
        )
    )
    assert called is True
    assert review["pass"] is False
    assert review["replacement_plan"] == json.loads(CANDIDATE)
    assert any("absent" in issue for issue in review["issues"])


def test_llm_route_retries_empty_primary_before_fallback() -> None:
    composer = LLMMessageComposer()
    calls: list[str] = []

    async def fake_call(**kwargs):
        model = str(kwargs.get("model") or "")
        calls.append(model)
        if len(calls) == 1:
            return SimpleNamespace(
                model=model,
                choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
            )
        return SimpleNamespace(
            model=model,
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
        )

    old = os.environ.get("HERMES_PROACTIVE_LLM_ROUTE_ATTEMPTS")
    os.environ["HERMES_PROACTIVE_LLM_ROUTE_ATTEMPTS"] = "2"
    try:
        content, model = asyncio.run(
            composer._call_routed_llm(
                fake_call,
                task="proactive",
                messages=[],
                temperature=0.0,
                max_tokens=10,
                preferred_model="deepseek-flash",
            )
        )
    finally:
        if old is None:
            os.environ.pop("HERMES_PROACTIVE_LLM_ROUTE_ATTEMPTS", None)
        else:
            os.environ["HERMES_PROACTIVE_LLM_ROUTE_ATTEMPTS"] = old
    assert content == "ok"
    assert model == "deepseek-flash"
    assert calls == ["deepseek-flash", "deepseek-flash"]


def test_reviewer_rewrites_each_source_only_once_before_reselection() -> None:
    used: set[str] = set()
    first = {"replacement_plan": {"content_ref": "story-1", "bubbles": []}}
    second = {"replacement_plan": {"content_ref": "story-2", "bubbles": []}}
    assert LLMMessageComposer._take_fresh_replacement(first, used) is not None
    assert LLMMessageComposer._take_fresh_replacement(first, used) is None
    assert LLMMessageComposer._take_fresh_replacement(second, used) is not None
    assert used == {"story-1", "story-2"}


def test_failed_sources_are_removed_before_reselection() -> None:
    context = {
        "external": [
            {"id": "story-1", "title": "weak"},
            {"id": "story-2", "title": "strong"},
        ],
        "local": [{"id": "memory-1"}],
    }
    filtered = LLMMessageComposer._without_content_refs(context, {"story-1"})
    assert filtered is not context
    assert [item["id"] for item in filtered["external"]] == ["story-2"]
    assert filtered["local"] == context["local"]
    assert len(context["external"]) == 2


def test_title_only_candidates_are_not_selectable() -> None:
    assert LLMMessageComposer._has_source_evidence(
        {"title": "Headline without evidence", "summary": ""}
    ) is False
    assert LLMMessageComposer._has_source_evidence(
        {"title": "Headline", "summary": "A concrete summary with enough source evidence to verify."}
    ) is True


def test_missing_reference_is_recovered_only_from_unique_exact_evidence() -> None:
    composer = LLMMessageComposer()
    parsed = json.loads(CANDIDATE)
    parsed["content_ref"] = None
    repaired, changed = composer._repair_unambiguous_content_ref(
        json.dumps(parsed, ensure_ascii=False),
        {"external": [ITEM]},
    )
    assert changed is True
    assert json.loads(repaired)["content_ref"] == "story-1"

    duplicate = dict(ITEM)
    duplicate["id"] = "story-2"
    unchanged, changed = composer._repair_unambiguous_content_ref(
        json.dumps(parsed, ensure_ascii=False),
        {"external": [ITEM, duplicate]},
    )
    assert changed is False
    assert json.loads(unchanged)["content_ref"] is None


def test_recovery_generation_is_locked_to_one_ranked_source() -> None:
    context = {
        "external": [
            {"id": "story-1", "summary": "first ranked evidence source is available"},
            {"id": "story-2", "summary": "second ranked evidence source is available"},
        ]
    }
    locked, locked_ref = LLMMessageComposer._next_source_context(
        context,
        {"story-1"},
    )
    assert locked_ref == "story-2"
    assert [item["id"] for item in locked["external"]] == ["story-2"]
    draft = json.dumps({"bubbles": [], "content_ref": None})
    bound = LLMMessageComposer._bind_locked_content_ref(draft, locked_ref)
    assert json.loads(bound)["content_ref"] == "story-2"


def test_structured_plan_is_extracted_from_model_wrapping() -> None:
    wrapped = "下面是结果：\n```json\n" + CANDIDATE + "\n```\n请查收。"
    normalized = LLMMessageComposer._normalize_json_candidate(wrapped)
    assert json.loads(normalized) == json.loads(CANDIDATE)


def main() -> int:
    tests = [
        test_all_dimensions_are_required,
        test_valid_reference_and_full_contract_pass,
        test_invalid_reference_fails_before_model_call,
        test_prompt_contains_retrieved_evidence_and_metadata_only_boundary,
        test_long_article_keeps_title_relevant_middle_passage,
        test_distinct_facts_may_share_the_fact_act,
        test_title_only_evidence_is_rejected,
        test_evidence_failure_invokes_independent_rewriter,
        test_llm_route_retries_empty_primary_before_fallback,
        test_reviewer_rewrites_each_source_only_once_before_reselection,
        test_failed_sources_are_removed_before_reselection,
        test_title_only_candidates_are_not_selectable,
        test_missing_reference_is_recovered_only_from_unique_exact_evidence,
        test_recovery_generation_is_locked_to_one_ranked_source,
        test_structured_plan_is_extracted_from_model_wrapping,
    ]
    for test in tests:
        test()
        print(f"EDITORIAL_QUALITY_CONTRACT_PASS {test.__name__}")
    print("HERMES_ALIVE_EDITORIAL_QUALITY_CONTRACT_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
