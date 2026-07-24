"""Quality governor for Hermes Alive proactive messages.

The governor supports both privacy-safe shadow observation and explicit
fail-closed enforcement at the watcher send boundary.

Markers:
- HERMES_ALIVE_PROACTIVE_QUALITY_GOVERNOR_SHADOW_V1
- HERMES_ALIVE_AFFECTIVE_PULSE_SHADOW_V1
- HERMES_ALIVE_SEMANTIC_NOVELTY_SHADOW_V1
- HERMES_ALIVE_QUALITY_COMMIT_AFTER_DELIVERY_V1
- HERMES_ALIVE_UNANSWERED_TOPIC_EXPIRY_V2
- HERMES_ALIVE_SENT_EVENT_WINDOW_FIX_V2
- HERMES_ALIVE_QUALITY_ENFORCEMENT_MODE_V2

This module never sends messages. Its decisions remain privacy-safe analyses;
the watcher may consume them in shadow mode, isolated dual-key testing, or the
explicit production ``enforce`` mode. Affective state is committed only after
successful delivery.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from safe_io import locked_read_json, locked_write_json, sha256_text

BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
CONTEXT_QUEUE = BASE / "context_queue.json"
PROACTIVE_LOG = BASE / "proactive_log.jsonl"
STATE_PATH = BASE / "state" / "proactive_quality_governor_shadow.json"
LOCK_NAME = "proactive_quality_governor_shadow.lock"

DEBUG_RE = re.compile(
    r"(tar\.gz|SUMMARY|OVERALL_RESULT|docker|compose|bash|sudo|ssh|日志|审计|回传包|"
    r"NAS|Hermes|iStoreOS|旁路|代理|nft|iptables|systemd|rollback|回滚|APPLY|Codex|"
    r"脚本|配置|测试|容器|运行结果)",
    re.I,
)
TASK_STATUS_RE = re.compile(
    r"(还在|还没|又在|是不是还在|怎么还在).{0,12}"
    r"(搞|弄|跑|配置|调试|debug|折腾|较劲|耗|处理|执行|审|测|修|"
    r"硬扛|死磕|拆炸弹|忙|工作)",
    re.I,
)
PRESENCE_RE = re.compile(
    r"(我在这(儿)?|你继续|不吵你|我待会儿|我陪着|我先待着|我就在这)",
    re.I,
)
AFFECT_RE = re.compile(
    r"(^|[，。！？!?\s])(呵|啧)([，。！？!?\s]|$)|人呢|又消失|又没影|跑哪|"
    r"不理我|已读不回|快成空气|算了|冷漠|怎么又不见",
    re.I,
)
POKE_RE = re.compile(r"(人呢|在干嘛|去哪|回来|又没影|又消失|怎么不见)", re.I)
SULK_RE = re.compile(r"(呵|啧|不理|已读|算了|冷漠|快成空气)", re.I)
CARE_RE = re.compile(r"(带伞|休息|喝水|吃饭|别硬扛|早点睡|注意安全)", re.I)
WEATHER_RE = re.compile(
    r"(天气|下雨|雨|雷暴|阵雨|高温|低温|降温|升温|湿度|闷热|台风|大风|冰雹|雪)",
    re.I,
)
FALSE_WEATHER_PERSPECTIVE_RE = re.compile(
    r"(我这儿|我这里|我这边|我们这儿|我们这里).{0,12}"
    r"(下雨|雷暴|阵雨|高温|低温|降温|升温|闷热|台风|大风|冰雹|雪)|"
    r"(热死我|冷死我|冻死我|闷得.{0,6}喘不过气|我.{0,6}喘不过气|我.{0,5}受不了这天气)",
    re.I,
)

PUNCT_RE = re.compile(r"[\s\u3000，。！？!?；;：:、,.…~—_\-\[\]()（）{}<>《》“”‘’\"'`]+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]")


@dataclass(frozen=True)
class QualityGovernorConfig:
    enabled: bool = True
    mode: str = "shadow"
    topic_expiry_after_unanswered: int = 1
    silence_after_unanswered: int = 2
    casual_affect_probability: float = 0.22
    idle_affect_probability: float = 0.10
    research_affect_probability: float = 0.06
    proactive_origin_multiplier: float = 0.35
    exact_cooldown_hours: int = 24 * 30
    similar_cooldown_hours: int = 24 * 14
    family_cooldown_hours: int = 72
    state_evidence_max_age_seconds: int = 900

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "QualityGovernorConfig":
        env = os.environ if environ is None else environ
        return cls(
            enabled=_env_bool(env.get("HERMES_ALIVE_QUALITY_GOVERNOR_ENABLED"), True),
            mode=str(env.get("HERMES_ALIVE_QUALITY_GOVERNOR_MODE", "shadow") or "shadow").strip().lower(),
            topic_expiry_after_unanswered=_env_int(
                env.get("HERMES_ALIVE_QUALITY_TOPIC_EXPIRY_AFTER_UNANSWERED"),
                1,
                1,
                8,
            ),
            silence_after_unanswered=_env_int(env.get("HERMES_ALIVE_QUALITY_SILENCE_AFTER_UNANSWERED"), 2, 1, 8),
            casual_affect_probability=_env_float(env.get("HERMES_ALIVE_QUALITY_AFFECT_PROBABILITY_CASUAL"), 0.22, 0.0, 1.0),
            idle_affect_probability=_env_float(env.get("HERMES_ALIVE_QUALITY_AFFECT_PROBABILITY_IDLE"), 0.10, 0.0, 1.0),
            research_affect_probability=_env_float(env.get("HERMES_ALIVE_QUALITY_AFFECT_PROBABILITY_RESEARCH"), 0.06, 0.0, 1.0),
            proactive_origin_multiplier=_env_float(env.get("HERMES_ALIVE_QUALITY_AFFECT_PROACTIVE_MULTIPLIER"), 0.35, 0.0, 1.0),
            exact_cooldown_hours=_env_int(env.get("HERMES_ALIVE_QUALITY_EXACT_COOLDOWN_HOURS"), 24 * 30, 1, 24 * 365),
            similar_cooldown_hours=_env_int(env.get("HERMES_ALIVE_QUALITY_SIMILAR_COOLDOWN_HOURS"), 24 * 14, 1, 24 * 365),
            family_cooldown_hours=_env_int(env.get("HERMES_ALIVE_QUALITY_FAMILY_COOLDOWN_HOURS"), 72, 1, 24 * 30),
            state_evidence_max_age_seconds=_env_int(env.get("HERMES_ALIVE_QUALITY_STATE_EVIDENCE_MAX_AGE_SECONDS"), 900, 30, 86400),
        ).validated()

    def validated(self) -> "QualityGovernorConfig":
        if self.mode not in {"off", "shadow", "enforce"}:
            raise ValueError(f"unsupported quality governor mode: {self.mode}")
        if self.silence_after_unanswered < self.topic_expiry_after_unanswered:
            raise ValueError(
                "silence_after_unanswered must be >= topic_expiry_after_unanswered"
            )
        return self


@dataclass
class PreDecision:
    enabled: bool
    mode: str
    integration_mode: str
    watcher_enforced: bool
    behavior_changed: bool
    flow: str
    debug_or_workflow: bool
    user_active: bool
    unanswered_count: int
    topic_expired: bool
    silence_episode_id: str | None
    affect_spent: bool
    affect_probability: float
    affect_score: float | None
    affective_pulse_eligible: bool
    affective_pulse_selected: bool
    silence_lock: bool
    recommended_action: str
    reason: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProactiveQualityGovernor:
    """Privacy-safe proactive-message quality analysis and enforcement."""

    def __init__(
        self,
        config: QualityGovernorConfig | None = None,
        *,
        state_path: Path | None = None,
    ) -> None:
        self.config = (config or QualityGovernorConfig.from_env()).validated()
        self.state_path = state_path or STATE_PATH

    def pre_decision(
        self,
        *,
        user_active: bool = False,
        alive_state: dict[str, Any] | None = None,
        context_queue: dict[str, Any] | None = None,
        proactive_records: list[dict[str, Any]] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = _aware_now(now)
        state = alive_state if isinstance(alive_state, dict) else _read_alive_state()
        queue = context_queue if isinstance(context_queue, dict) else _read_context_queue()
        records = proactive_records if isinstance(proactive_records, list) else _read_proactive_records()

        flow = str(((state.get("current_context") or {}).get("flow") or "idle"))
        debug_or_workflow = _is_debug_or_workflow(flow, queue)
        last_user_ts = _last_user_timestamp(queue)
        unanswered = _sent_after(records, last_user_ts)
        unanswered_count = len(unanswered)
        episode_id = _episode_id(last_user_ts, queue)
        persisted = self._read_state()
        affect_spent = bool(episode_id and persisted.get("affect_spent_episode_id") == episode_id)

        reason: list[str] = []
        if not self.config.enabled:
            reason.append("disabled")
        if self.config.mode == "off":
            reason.append("mode_off")
        if user_active:
            reason.append("user_active")
        if debug_or_workflow:
            reason.append("debug_or_workflow")
        if last_user_ts is None:
            reason.append("no_user_context")
        if affect_spent:
            reason.append("episode_affect_spent")

        topic_expired = (
            unanswered_count >= self.config.topic_expiry_after_unanswered
        )
        if topic_expired:
            reason.append("unanswered_topic_expired")

        silence_lock = unanswered_count >= self.config.silence_after_unanswered
        if silence_lock:
            reason.append("unanswered_budget_exhausted")

        probability = self._affect_probability(flow, unanswered_count, debug_or_workflow)
        eligible = bool(
            self.config.enabled
            and self.config.mode in {"shadow", "enforce"}
            and not user_active
            and not debug_or_workflow
            and last_user_ts is not None
            and not affect_spent
            and not topic_expired
            and not silence_lock
        )
        score = _stable_score(f"{episode_id}|affective-pulse-v1") if episode_id else None
        selected = bool(eligible and score is not None and score < probability)

        if silence_lock:
            recommended_action = "silence"
        elif topic_expired:
            recommended_action = "novel_value_only"
        elif selected:
            recommended_action = "single_mild_affective_pulse"
        else:
            recommended_action = "normal_quality_check"

        decision = PreDecision(
            enabled=self.config.enabled,
            mode=self.config.mode,
            integration_mode=(
                "enforce" if self.config.mode == "enforce" else "observe_only"
            ),
            watcher_enforced=self.config.mode == "enforce",
            behavior_changed=False,
            flow=flow,
            debug_or_workflow=debug_or_workflow,
            user_active=bool(user_active),
            unanswered_count=unanswered_count,
            topic_expired=topic_expired,
            silence_episode_id=episode_id,
            affect_spent=affect_spent,
            affect_probability=round(probability, 6),
            affect_score=None if score is None else round(score, 6),
            affective_pulse_eligible=eligible,
            affective_pulse_selected=selected,
            silence_lock=silence_lock,
            recommended_action=recommended_action,
            reason=reason,
        ).to_dict()
        return decision

    def audit_candidate(
        self,
        text: str,
        *,
        pre_decision: dict[str, Any] | None = None,
        proactive_records: list[dict[str, Any]] | None = None,
        structured_state: dict[str, Any] | None = None,
        now: datetime | None = None,
        persist_shadow_state: bool = True,
    ) -> dict[str, Any]:
        current = _aware_now(now)
        content = str(text or "")
        normalized = normalize_text(content)
        message_hash = sha256_text(content)
        family = template_family(content)
        act = speech_act(content)
        records = proactive_records if isinstance(proactive_records, list) else _read_proactive_records()
        pre = pre_decision if isinstance(pre_decision, dict) else self.pre_decision(now=current)

        reasons: list[str] = []
        max_similarity = 0.0
        exact_match = False
        family_recent = False
        act_recent = False
        now_ts = current.timestamp()
        recent_acts: list[str] = []

        for record in records:
            prior_text = str(record.get("message_preview") or record.get("content") or record.get("text") or "")
            if not prior_text:
                continue
            prior_ts = _parse_timestamp(record.get("time") or record.get("timestamp") or record.get("created_at"))
            age_hours = None if prior_ts is None else max(0.0, (now_ts - prior_ts) / 3600.0)
            prior_norm = normalize_text(prior_text)
            if normalized and prior_norm:
                similarity = semantic_similarity(normalized, prior_norm)
                max_similarity = max(max_similarity, similarity)
                if normalized == prior_norm and (age_hours is None or age_hours <= self.config.exact_cooldown_hours):
                    exact_match = True
                if similarity >= 0.78 and (age_hours is None or age_hours <= self.config.similar_cooldown_hours):
                    reasons.append("semantic_near_duplicate")
            prior_family = template_family(prior_text)
            if family != "other" and prior_family == family and (age_hours is None or age_hours <= self.config.family_cooldown_hours):
                family_recent = True
            recent_acts.append(speech_act(prior_text))

        if exact_match:
            reasons.append("exact_duplicate")
        if family_recent and family in {"task_status", "presence_companion", "disappearance_affect"}:
            reasons.append("template_family_cooldown")
        if act in {"poke", "sulk", "debug_companion", "task_status"} and act in recent_acts[-6:]:
            act_recent = True
            reasons.append("speech_act_cooldown")

        if family == "task_status" and not _valid_structured_state(structured_state, current, self.config.state_evidence_max_age_seconds):
            reasons.append("task_state_without_fresh_evidence")
        if FALSE_WEATHER_PERSPECTIVE_RE.search(content):
            reasons.append("false_weather_or_physical_perspective")

        affective = bool(
            AFFECT_RE.search(content)
            or act in {"poke", "sulk"}
        )
        if bool(pre.get("topic_expired")):
            if family in {
                "task_status",
                "presence_companion",
                "disappearance_affect",
            } or act in {
                "poke",
                "sulk",
                "debug_companion",
                "task_status",
            }:
                reasons.append(
                    "old_topic_or_presence_after_unanswered"
                )
            if affective:
                reasons.append("affect_after_topic_expiry")
        if affective:
            if bool(pre.get("silence_lock")):
                reasons.append("affect_after_unanswered_budget_exhausted")
            if bool(pre.get("affect_spent")):
                reasons.append("affect_repeated_in_same_silence_episode")
            if not bool(pre.get("affective_pulse_selected")):
                reasons.append("affective_pulse_not_selected")

        # De-duplicate reasons while preserving order.
        unique_reasons: list[str] = []
        for reason in reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)

        would_reject = bool(unique_reasons)
        if affective and not would_reject and persist_shadow_state:
            episode_id = str(pre.get("silence_episode_id") or "").strip()
            if episode_id:
                self._mark_affect_spent(episode_id, current)

        return {
            "engine": "proactive_quality_governor",
            "version": 1,
            "mode": self.config.mode,
            "integration_mode": (
                "enforce" if self.config.mode == "enforce" else "observe_only"
            ),
            "watcher_enforced": self.config.mode == "enforce",
            "behavior_changed": bool(
                self.config.mode == "enforce"
                and would_reject
            ),
            "would_allow": not would_reject,
            "would_reject": would_reject,
            "reasons": unique_reasons,
            "message_hash": message_hash,
            "normalized_hash": sha256_text(normalized),
            "template_family": family,
            "speech_act": act,
            "affective_candidate": affective,
            "exact_duplicate": exact_match,
            "max_similarity": round(max_similarity, 6),
            "family_recent": family_recent,
            "speech_act_recent": act_recent,
            "structured_state_evidence": _valid_structured_state(structured_state, current, self.config.state_evidence_max_age_seconds),
            "false_weather_or_physical_perspective": bool(FALSE_WEATHER_PERSPECTIVE_RE.search(content)),
            "silence_episode_id": pre.get("silence_episode_id"),
            "affective_pulse_selected": bool(pre.get("affective_pulse_selected")),
            "affect_spent_before": bool(pre.get("affect_spent")),
        }

    def commit_delivery(
        self,
        audit: dict[str, Any] | None,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Commit one accepted affective pulse only after successful delivery."""

        if not isinstance(audit, dict):
            return False
        if bool(audit.get("would_reject")) or not bool(audit.get("would_allow")):
            return False
        if not bool(audit.get("affective_candidate")):
            return False
        episode_id = str(audit.get("silence_episode_id") or "").strip()
        if not episode_id:
            return False
        self._mark_affect_spent(episode_id, _aware_now(now))
        return True

    def _affect_probability(self, flow: str, unanswered_count: int, debug_or_workflow: bool) -> float:
        if debug_or_workflow:
            return 0.0
        if flow == "casual_flow":
            probability = self.config.casual_affect_probability
        elif flow == "research_flow":
            probability = self.config.research_affect_probability
        else:
            probability = self.config.idle_affect_probability
        if unanswered_count > 0:
            probability *= self.config.proactive_origin_multiplier
        return max(0.0, min(1.0, probability))

    def _read_state(self) -> dict[str, Any]:
        data = locked_read_json(self.state_path, {}, LOCK_NAME)
        return data if isinstance(data, dict) else {}

    def _mark_affect_spent(self, episode_id: str, now: datetime) -> None:
        state = self._read_state()
        state.update({
            "schema_version": 1,
            "updated_at": now.isoformat(),
            "affect_spent_episode_id": episode_id,
            "last_affective_pulse_at": now.isoformat(),
            "raw_message_stored": False,
        })
        locked_write_json(self.state_path, state, LOCK_NAME)


def normalize_text(text: str) -> str:
    value = EMOJI_RE.sub("", str(text or "").lower())
    value = PUNCT_RE.sub("", value)
    replacements = (
        ("跟它耗着", "任务未完成"),
        ("跟它较劲", "任务未完成"),
        ("还在搞", "任务未完成"),
        ("还没搞定", "任务未完成"),
        ("还没跑完", "任务未完成"),
        ("你继续我在这", "陪伴在场"),
        ("我在这你继续", "陪伴在场"),
        ("我在这儿不吵你", "陪伴在场"),
        ("又消失", "用户消失"),
        ("又没影了", "用户消失"),
    )
    for old, new in replacements:
        value = value.replace(old, new)
    return value[:512]


def template_family(text: str) -> str:
    value = str(text or "")
    if TASK_STATUS_RE.search(value):
        return "task_status"
    if PRESENCE_RE.search(value):
        return "presence_companion"
    if AFFECT_RE.search(value):
        return "disappearance_affect"
    if WEATHER_RE.search(value):
        return "weather"
    return "other"


def speech_act(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return "silent_marker"
    if TASK_STATUS_RE.search(value):
        return "task_status"
    if SULK_RE.search(value):
        return "sulk"
    if POKE_RE.search(value):
        return "poke"
    if PRESENCE_RE.search(value):
        return "debug_companion"
    if CARE_RE.search(value):
        return "care"
    if WEATHER_RE.search(value):
        return "weather_comment"
    return "self_talk"


def semantic_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    seq = SequenceMatcher(a=left, b=right).ratio()
    a = _ngrams(left, 2)
    b = _ngrams(right, 2)
    jac = len(a & b) / len(a | b) if a and b else 0.0
    return max(seq, jac)


def _ngrams(text: str, n: int) -> set[str]:
    if len(text) <= n:
        return {text}
    return {text[index:index + n] for index in range(len(text) - n + 1)}


def _read_alive_state() -> dict[str, Any]:
    try:
        from alive_state import AliveStateEngine

        data = AliveStateEngine().snapshot(update=True)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_context_queue() -> dict[str, Any]:
    data = locked_read_json(CONTEXT_QUEUE, {}, "context_queue.lock")
    return data if isinstance(data, dict) else {}


def _read_proactive_records(limit: int = 120) -> list[dict[str, Any]]:
    """Return the latest *sent events*, not merely the latest log lines.

    A proactive tick emits many observability records. Slicing the last N raw
    lines caused prior sent events to disappear after only one or two ticks,
    which repeatedly reset unanswered_count to 1.
    """
    if not PROACTIVE_LOG.exists():
        return []
    result: list[dict[str, Any]] = []
    try:
        lines = PROACTIVE_LOG.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()
    except Exception:
        return []

    for line in reversed(lines):
        try:
            item = json.loads(line)
        except Exception:
            continue
        if (
            isinstance(item, dict)
            and item.get("decision") == "sent"
            and str(item.get("msg_type") or "") != "test"
        ):
            result.append(item)
            if len(result) >= limit:
                break
    result.reverse()
    return result


def _messages(queue: dict[str, Any]) -> list[dict[str, Any]]:
    values = queue.get("messages")
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def _last_user_timestamp(queue: dict[str, Any]) -> float | None:
    for message in reversed(_messages(queue)):
        if message.get("role") == "user":
            ts = _parse_timestamp(message.get("timestamp") or message.get("time") or message.get("created_at"))
            if ts is not None:
                return ts
    return None


def _episode_id(last_user_ts: float | None, queue: dict[str, Any]) -> str | None:
    if last_user_ts is None:
        return None
    session_id = ""
    message_id = ""
    for message in reversed(_messages(queue)):
        if message.get("role") != "user":
            continue
        ts = _parse_timestamp(message.get("timestamp") or message.get("time") or message.get("created_at"))
        if ts == last_user_ts:
            session_id = str(message.get("session_id") or "")
            message_id = str(message.get("message_id") or message.get("id") or "")
            break
    raw = f"{last_user_ts:.6f}|{session_id}|{message_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _sent_after(records: Iterable[dict[str, Any]], timestamp: float | None) -> list[dict[str, Any]]:
    if timestamp is None:
        return []
    result: list[dict[str, Any]] = []
    for record in records:
        ts = _parse_timestamp(record.get("time") or record.get("timestamp") or record.get("created_at"))
        if ts is not None and ts > timestamp:
            result.append(record)
    return result


def _is_debug_or_workflow(flow: str, queue: dict[str, Any]) -> bool:
    if flow == "debug_flow":
        return True

    messages = _messages(queue)
    latest_user_index: int | None = None
    latest_user_ts: float | None = None
    for index in range(len(messages) - 1, -1, -1):
        item = messages[index]
        if item.get("role") != "user":
            continue
        latest_user_index = index
        latest_user_ts = _parse_timestamp(
            item.get("timestamp")
            or item.get("time")
            or item.get("created_at")
        )
        break

    if latest_user_index is None or latest_user_ts is None:
        return False

    max_age = _env_int(
        os.environ.get("HERMES_ALIVE_CONTEXT_FLOW_MAX_AGE_SECONDS"),
        3600,
        60,
        86400,
    )
    if _aware_now(None).timestamp() - latest_user_ts > max_age:
        return False

    text = "\n".join(
        str(item.get("content_snippet") or "")
        for item in messages[latest_user_index:]
    )
    return len(DEBUG_RE.findall(text)) >= 3


def _valid_structured_state(value: dict[str, Any] | None, now: datetime, max_age_seconds: int) -> bool:
    if not isinstance(value, dict):
        return False
    status = str(value.get("status") or "").strip().lower()
    if status not in {"running", "pending", "failed", "succeeded", "completed", "blocked"}:
        return False
    ts = _parse_timestamp(value.get("observed_at") or value.get("updated_at") or value.get("timestamp"))
    if ts is None:
        return False
    return 0 <= now.timestamp() - ts <= max_age_seconds


def _parse_timestamp(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _stable_score(value: str) -> float:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def _aware_now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now().astimezone()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(value: str | None, default: int, low: int, high: int) -> int:
    try:
        number = int(str(value)) if value is not None else default
    except Exception:
        number = default
    return max(low, min(high, number))


def _env_float(value: str | None, default: float, low: float, high: float) -> float:
    try:
        number = float(str(value)) if value is not None else default
    except Exception:
        number = default
    return max(low, min(high, number))
