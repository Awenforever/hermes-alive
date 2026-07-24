# Hermes Alive semantic bubble planning and validation.
# Marker: HERMES_ALIVE_SEMANTIC_BUBBLE_PLAN_V1
# Marker: HERMES_ALIVE_DYNAMIC_1_TO_5_BUBBLES_V1
# Marker: HERMES_ALIVE_NO_POST_GENERATION_MECHANICAL_SPLIT_V1
# Marker: HERMES_ALIVE_DISCOVERY_LIVED_EXPERIENCE_GUARD_V1
# Marker: HERMES_ALIVE_DEICTIC_REFERENT_GROUNDING_V1
# Marker: HERMES_ALIVE_CONTEXT_CONTINUATION_VISIBILITY_GATE_V1

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any

MAX_BUBBLES = 5
MAX_BUBBLE_CHARS = 800

ALLOWED_ACTS = {
    "self_talk",
    "observation",
    "question",
    "care",
    "dry_observation",
    "debug_companion",
    "research_ping",
    "discovery_intro",
    "fact",
    "reaction",
    "turn",
    "source_link",
    "closing",
    "poke",
    "casual",
}

DISCOVERY_FIRST_ACTS = {
    "discovery_intro",
    "research_ping",
    "fact",
}

NEW_TOPIC_ANCHORS = (
    "看到",
    "发现",
    "有篇",
    "有个研究",
    "有项研究",
    "有个论文",
    "一篇论文",
    "这篇论文",
    "这个研究",
    "这项研究",
    "有个项目",
    "有个工具",
    "开源",
    "论文",
    "研究",
    "消息",
)

UNSUPPORTED_CONTINUATION_PATTERNS = (
    r"你之前",
    r"还记得",
    r"接着上次",
    r"继续说",
    r"又想到你",
    r"想到你也",
    r"你坐飞机",
    r"你以后",
    r"你上次",
)

# New Discovery content must not manufacture embodied human experience for
# Hermes or assume the user shared that experience.  This is intentionally
# scoped to new_discovery; genuine context continuation is handled separately.
UNSUPPORTED_LIVED_EXPERIENCE_PATTERNS = (
    r"(坐飞机|飞长途|坐航班).{0,16}(被颠醒|遭罪|受罪|真烦|很烦|折腾)",
    r"(我|我们|咱们).{0,10}(坐飞机|飞长途|被颠醒|遇到过|经历过)",
    r"(上次|以前|之前).{0,10}(坐飞机|航班|飞行|颠簸)",
    r"(少遭点罪|少受点罪)",
)


VAGUE_DEICTIC_PATTERNS = (
    r"那个包",
    r"这包",
    r"那包",
    r"那个事",
    r"那件事",
    r"还在弄那个",
    r"还在搞那个",
    r"还在跟[^，。！？\n]{0,24}较劲",
)

EXPLICIT_REFERENT_PATTERNS = (
    r"[A-Za-z0-9_.-]+\.(?:tar\.gz|zip|sh|py|md|json|yaml|yml)",
    r"hermes-[A-Za-z0-9_.-]+",
    r"v\d+(?:[._-]\d+)+",
    r"[A-Fa-f0-9]{12,64}",
    r"[“「『《][^”」』》\n]{2,60}[”」』》]",
)

TASK_STATUS_ASSUMPTION_PATTERNS = (
    r"还在.{0,20}(弄|搞|跑|审|改|修|较劲|折腾)",
    r"又在.{0,20}(弄|搞|跑|审|改|修|较劲|折腾)",
    r"还没.{0,20}(跑完|改完|修完|弄完|搞定)",
)

SEPARATOR_RE = re.compile(r"(^|\n)\s*---\s*(\n|$)")


class SemanticPlanError(ValueError):
    pass


@dataclass
class SemanticBubble:
    act: str
    text: str


@dataclass
class SemanticBubblePlan:
    topic_mode: str
    bubbles: list[SemanticBubble]
    content_ref: str | None
    source_format: str

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "topic_mode": self.topic_mode,
            "bubble_count": len(self.bubbles),
            "acts": [bubble.act for bubble in self.bubbles],
            "content_ref_present": bool(self.content_ref),
            "source_format": self.source_format,
            "text_lengths": [len(bubble.text) for bubble in self.bubbles],
        }


def _strip_fence(text: str) -> str:
    value = str(text or "").strip()
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            value = "\n".join(lines[1:-1]).strip()
    return value


def _norm(text: str) -> str:
    value = re.sub(r"\s+", "", str(text or "")).lower()
    value = re.sub(r"[，。！？；：,.!?;:'\"“”‘’（）()【】\[\]…—-]+", "", value)
    return value


def _bigrams(text: str) -> set[str]:
    value = _norm(text)
    if len(value) < 2:
        return {value} if value else set()
    return {value[index:index + 2] for index in range(len(value) - 1)}


def _similarity(left: str, right: str) -> float:
    a = _bigrams(left)
    b = _bigrams(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _valid_content_ids(discovery_context: dict[str, Any] | None) -> set[str]:
    if not isinstance(discovery_context, dict):
        return set()
    external = discovery_context.get("external")
    if not isinstance(external, list):
        return set()
    return {
        str(item.get("id") or "").strip()
        for item in external
        if isinstance(item, dict)
        and str(item.get("id") or "").strip()
    }


def _policy_max(policy_decision: dict[str, Any] | None) -> int:
    try:
        value = int((policy_decision or {}).get("max_bubbles", MAX_BUBBLES))
    except Exception:
        value = MAX_BUBBLES
    return max(1, min(MAX_BUBBLES, value))


def _default_topic_mode(
    policy_decision: dict[str, Any] | None,
    discovery_context: dict[str, Any] | None,
) -> str:
    mode = str((policy_decision or {}).get("mode") or "").strip()
    if mode == "novel_value" or _valid_content_ids(discovery_context):
        return "new_discovery"
    return "ambient"


def _parse_json(value: str) -> dict[str, Any] | None:
    candidate = _strip_fence(value)
    if not candidate.startswith("{"):
        return None
    try:
        parsed = json.loads(candidate)
    except Exception as exc:
        raise SemanticPlanError("invalid_semantic_plan_json") from exc
    if not isinstance(parsed, dict):
        raise SemanticPlanError("semantic_plan_not_object")
    return parsed


def parse_semantic_plan(
    candidate: str,
    *,
    default_msg_type: str,
    policy_decision: dict[str, Any] | None = None,
    discovery_context: dict[str, Any] | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> SemanticBubblePlan:
    raw = str(candidate or "").strip()
    if not raw:
        raise SemanticPlanError("empty_candidate")

    parsed = _parse_json(raw)
    if parsed is None:
        # Backward compatibility is intentionally one bubble only. We never
        # split legacy text on punctuation, line length, newline, or ---.
        if SEPARATOR_RE.search(raw):
            raise SemanticPlanError("legacy_separator_output_rejected")
        plan = SemanticBubblePlan(
            topic_mode=_default_topic_mode(policy_decision, discovery_context),
            bubbles=[
                SemanticBubble(
                    act=str(default_msg_type or "self_talk"),
                    text=raw,
                )
            ],
            content_ref=None,
            source_format="legacy_single",
        )
        validate_semantic_plan(
            plan,
            policy_decision=policy_decision,
            discovery_context=discovery_context,
            context_snapshot=context_snapshot,
        )
        return plan

    topic_mode = str(
        parsed.get("topic_mode")
        or _default_topic_mode(policy_decision, discovery_context)
    ).strip().lower()
    if topic_mode not in {
        "ambient",
        "context_continuation",
        "new_discovery",
    }:
        raise SemanticPlanError("invalid_topic_mode")

    raw_bubbles = parsed.get("bubbles")
    if not isinstance(raw_bubbles, list):
        raise SemanticPlanError("bubbles_not_list")

    bubbles: list[SemanticBubble] = []
    for raw_bubble in raw_bubbles:
        if not isinstance(raw_bubble, dict):
            raise SemanticPlanError("bubble_not_object")
        act = str(
            raw_bubble.get("act")
            or default_msg_type
            or "self_talk"
        ).strip().lower()
        text = str(raw_bubble.get("text") or "").strip()
        if act not in ALLOWED_ACTS:
            raise SemanticPlanError("unsupported_semantic_act")
        bubbles.append(SemanticBubble(act=act, text=text))

    content_ref = parsed.get("content_ref")
    if content_ref is not None:
        content_ref = str(content_ref).strip() or None

    plan = SemanticBubblePlan(
        topic_mode=topic_mode,
        bubbles=bubbles,
        content_ref=content_ref,
        source_format="semantic_json",
    )
    validate_semantic_plan(
        plan,
        policy_decision=policy_decision,
        discovery_context=discovery_context,
        context_snapshot=context_snapshot,
    )
    return plan


def validate_semantic_plan(
    plan: SemanticBubblePlan,
    *,
    policy_decision: dict[str, Any] | None = None,
    discovery_context: dict[str, Any] | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> None:
    count = len(plan.bubbles)
    max_allowed = _policy_max(policy_decision)

    if count < 1:
        raise SemanticPlanError("no_bubbles")
    if count > MAX_BUBBLES:
        raise SemanticPlanError("bubble_count_above_five")
    if count > max_allowed:
        raise SemanticPlanError("bubble_count_above_policy_limit")

    seen: list[str] = []
    acts: list[str] = []
    for bubble in plan.bubbles:
        text = str(bubble.text or "").strip()
        if len(text) < 2:
            raise SemanticPlanError("bubble_too_short")
        if len(text) > MAX_BUBBLE_CHARS:
            raise SemanticPlanError("bubble_too_long")
        normalized = _norm(text)
        if not normalized:
            raise SemanticPlanError("bubble_empty_after_normalization")
        for prior in seen:
            if normalized == prior or _similarity(normalized, prior) >= 0.82:
                raise SemanticPlanError("cross_bubble_semantic_duplicate")
        seen.append(normalized)
        acts.append(bubble.act)

    if count > 1 and len(set(acts)) == 1:
        raise SemanticPlanError("multi_bubble_same_semantic_act")

    snapshot = (
        context_snapshot
        if isinstance(context_snapshot, dict)
        else {}
    )
    visible_count = int(
        snapshot.get("context_prompt_eligible_count") or 0
    )
    queue_healthy = bool(snapshot.get("queue_healthy", False))

    if (
        plan.topic_mode == "context_continuation"
        and (visible_count < 1 or not queue_healthy)
    ):
        raise SemanticPlanError(
            "context_continuation_without_visible_healthy_context"
        )

    combined_text = "\n".join(
        bubble.text for bubble in plan.bubbles
    )
    has_vague_deictic = any(
        re.search(pattern, combined_text)
        for pattern in VAGUE_DEICTIC_PATTERNS
    )
    has_explicit_referent = any(
        re.search(pattern, combined_text)
        for pattern in EXPLICIT_REFERENT_PATTERNS
    )
    if has_vague_deictic and not has_explicit_referent:
        raise SemanticPlanError(
            "ungrounded_deictic_reference"
        )

    has_task_status_assumption = any(
        re.search(pattern, combined_text)
        for pattern in TASK_STATUS_ASSUMPTION_PATTERNS
    )
    if (
        has_task_status_assumption
        and (
            plan.topic_mode != "context_continuation"
            or visible_count < 1
            or not queue_healthy
            or not has_explicit_referent
        )
    ):
        raise SemanticPlanError(
            "unsupported_task_status_assumption"
        )

    valid_ids = _valid_content_ids(discovery_context)
    policy_mode = str((policy_decision or {}).get("mode") or "")
    requires_discovery = policy_mode == "novel_value"

    if plan.content_ref and plan.content_ref not in valid_ids:
        raise SemanticPlanError("invalid_content_ref")
    if requires_discovery and not plan.content_ref:
        raise SemanticPlanError("novel_value_missing_content_ref")

    if plan.topic_mode == "new_discovery":
        first = plan.bubbles[0]
        if first.act not in DISCOVERY_FIRST_ACTS:
            raise SemanticPlanError("new_discovery_missing_intro_act")
        if not any(anchor in first.text for anchor in NEW_TOPIC_ANCHORS):
            raise SemanticPlanError("new_discovery_missing_topic_anchor")
        combined = "\n".join(bubble.text for bubble in plan.bubbles)
        for pattern in UNSUPPORTED_CONTINUATION_PATTERNS:
            if re.search(pattern, combined):
                raise SemanticPlanError(
                    "unsupported_personal_or_continuation_assumption"
                )
        for pattern in UNSUPPORTED_LIVED_EXPERIENCE_PATTERNS:
            if re.search(pattern, combined):
                raise SemanticPlanError(
                    "unsupported_lived_experience_assumption"
                )


def messages_from_plan(
    plan: SemanticBubblePlan,
) -> list[tuple[str, str]]:
    return [(bubble.act, bubble.text) for bubble in plan.bubbles]
