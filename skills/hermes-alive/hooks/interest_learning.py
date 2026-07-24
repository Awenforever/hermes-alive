# Hermes Alive interest and feedback learning.
# Marker: INTEREST_LEARNING_ENGINE_V1
# Marker: INTEREST_LEARNING_ATTRIBUTION_V1
# Marker: INTEREST_LEARNING_TAG_BOUNDARY_V1
# Marker: INTEREST_LEARNING_LOG_BOUND_V1
# Marker: INTEREST_LEARNING_IGNORED_ATTRIBUTION_V1
# Marker: INTEREST_LEARNING_FEEDBACK_PHRASE_V2
# Marker: RICH_CONTENT_ITEM_FIELDS_V1

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safe_io import LOCK_DIR, atomic_write_text, file_lock, locked_read_json, locked_write_json
from topic_dedup import TopicDedupStore, item_identity

DEFAULT_BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))

TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "llm", "agent", "模型", "人工智能", "机器学习", "深度学习", "transformer"),
    "remote_sensing": ("remote sensing", "satellite", "遥感", "卫星", "sentinel", "landsat"),
    "fire_smoke": ("smoke", "fire", "wildfire", "烟雾", "火灾", "消防", "燃烧"),
    "combustion_microgravity": ("combustion", "flame", "microgravity", "low gravity", "甲烷", "火焰", "微重力", "弱浮力", "落塔"),
    "open_source": ("open source", "github", "repo", "开源", "仓库"),
    "programming": ("python", "rust", "golang", "javascript", "代码", "编程", "软件开发"),
    "productivity_tools": ("tool", "workflow", "automation", "工具", "工作流", "自动化"),
    "hardware": ("hardware", "nas", "gpu", "camera", "硬件", "显卡", "相机", "服务器"),
    "games": ("game", "simulator", "游戏", "模拟器"),
    "automotive": ("car", "automotive", "vehicle", "汽车", "新能源车", "车辆"),
    "finance": ("stock", "market", "crypto", "finance", "股票", "市场", "加密货币", "金融"),
}

POSITIVE_STRONG = re.compile(
    r"(多推|多来点|挺有意思|很有意思|这个方向可以|这类可以|喜欢这个|"
    r"继续推|可以多发|这个不错|这篇不错|这类不错|这种不错)",
    re.I,
)
NEGATIVE_STRONG = re.compile(
    r"(没兴趣|不感兴趣|少推|别再推|不要再推|别推|不想看|"
    r"这个无聊|这篇无聊|这类无聊|这种无聊|这种不用发)",
    re.I,
)
ASK_LINK = re.compile(
    r"(链接呢|发链接|给我链接|原文链接|原文在哪|网址|出处|"
    r"send\s+(?:me\s+)?(?:the\s+)?link|link\s+please|original\s+source)",
    re.I,
)
ASK_DETAIL = re.compile(
    r"(展开说|详细说|具体讲讲|多说点|讲讲这个|讲讲这篇|这个为什么|这篇为什么|"
    r"这个怎么回事|刚才那个|刚才那篇|刚才那个项目|细节呢)",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _item_key(item: dict[str, Any]) -> str:
    # HERMES_ALIVE_CANONICAL_ITEM_ID_V1
    return item_identity(item)["content_identity"][:20]


def _text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "summary", "description", "interesting_reason", "source")
    ).lower()


def _topic_pattern_matches(text: str, pattern: str) -> bool:
    # INTEREST_LEARNING_TAG_BOUNDARY_V1
    candidate = str(pattern or "").strip().lower()
    if not candidate:
        return False
    if re.fullmatch(r"[a-z0-9+.# -]+", candidate):
        escaped = re.escape(candidate).replace(r"\ ", r"\s+")
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    return candidate in text


def infer_tags_from_text(text: str) -> list[str]:
    lower = str(text or "").lower()
    tags: list[str] = []
    for topic, patterns in TOPIC_PATTERNS.items():
        if any(_topic_pattern_matches(lower, pattern) for pattern in patterns):
            tags.append(topic)
    return tags


def infer_tags(item: dict[str, Any]) -> list[str]:
    existing = item.get("tags")
    tags = [str(x).strip() for x in existing] if isinstance(existing, list) else []
    tags.extend(infer_tags_from_text(_text(item)))
    return list(dict.fromkeys(x for x in tags if x))


def infer_content_type(item: dict[str, Any]) -> str:
    value = str(item.get("content_type") or "").strip().lower()
    if value:
        return value
    source = str(item.get("source") or "").lower()
    text = _text(item)
    if source == "arxiv" or any(x in text for x in ("paper", "论文", "research")):
        return "paper"
    if source in ("github", "github_trending") or "github.com/" in str(item.get("url") or ""):
        return "repository"
    if any(x in source for x in ("bilibili", "youtube")):
        return "video"
    if any(x in text for x in ("tool", "工具", "software", "软件")):
        return "tool"
    return "article"


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    # RICH_CONTENT_ITEM_FIELDS_V1
    out = dict(item)
    out["id"] = str(out.get("id") or _item_key(out))
    out["source"] = str(out.get("source") or "unknown")
    out["title"] = str(out.get("title") or "").strip()
    out["url"] = str(
        out.get("url")
        or out.get("link")
        or out.get("href")
        or ""
    ).strip()
    out["summary"] = str(
        out.get("summary")
        or out.get("description")
        or ""
    ).strip()
    out["image_url"] = str(
        out.get("image_url")
        or out.get("thumbnail_url")
        or out.get("thumbnail")
        or out.get("image")
        or ""
    ).strip()
    out["file_path"] = str(
        out.get("file_path")
        or out.get("local_path")
        or ""
    ).strip()
    out["content_type"] = infer_content_type(out)
    out["tags"] = infer_tags(out)
    out.update(item_identity(out))
    return out


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _target_is_recent(item: dict[str, Any], max_hours: float = 24.0) -> bool:
    delivered = _parse_datetime(item.get("delivered_at"))
    if delivered is None:
        return False
    age = datetime.now(timezone.utc) - delivered.astimezone(timezone.utc)
    return -300 <= age.total_seconds() <= max_hours * 3600


def _content_was_unanswered(
    item: dict[str, Any],
    state: dict[str, Any],
    max_hours: float = 72.0,
) -> bool:
    # INTEREST_LEARNING_IGNORED_ATTRIBUTION_V1
    delivered_at = _parse_datetime(item.get("delivered_at"))
    if delivered_at is None:
        return False

    delivered_utc = delivered_at.astimezone(timezone.utc)
    age_seconds = (
        datetime.now(timezone.utc) - delivered_utc
    ).total_seconds()
    if age_seconds < -300 or age_seconds > max_hours * 3600:
        return False

    last_user_reply = _parse_datetime(state.get("last_user_reply_at"))
    if last_user_reply is None:
        return True

    return delivered_utc > last_user_reply.astimezone(timezone.utc)


def _append_bounded_jsonl(
    path: Path,
    record: dict[str, Any],
    lock_name: str,
    max_lines: int,
) -> None:
    # INTEREST_LEARNING_LOG_BOUND_V1
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(record)
    payload.setdefault("time", _now())
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lock = LOCK_DIR / lock_name
    with file_lock(lock):
        try:
            existing = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            existing = []
        keep = max(0, int(max_lines) - 1)
        existing = existing[-keep:] if keep else []
        atomic_write_text(path, "\n".join(existing + [line]) + "\n")


def _default_profile() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": _now(),
        "topics": {},
        "sources": {},
        "content_types": {},
        "processed_feedback_keys": [],
        "processed_implicit_keys": [],
        "last_delivered_item": None,
    }


class InterestLearningEngine:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base = Path(base_dir) if base_dir is not None else DEFAULT_BASE
        self.preferences_dir = self.base / "preferences"
        self.profile_path = self.preferences_dir / "interest_profile.json"
        self.feedback_log_path = self.preferences_dir / "feedback_log.jsonl"
        self.content_seen_path = self.base / "content_seen.jsonl"
        self.content_items_path = self.base / "content_items.jsonl"
        self.context_queue_path = self.base / "context_queue.json"
        self.alive_state_path = self.base / "state" / "alive_state.json"
        self.topic_dedup = TopicDedupStore(self.base)
        self._ensure_files()

    def _ensure_files(self) -> None:
        self.preferences_dir.mkdir(parents=True, exist_ok=True)
        if not self.profile_path.exists():
            locked_write_json(self.profile_path, _default_profile(), "interest_profile.lock")
        for path in (self.feedback_log_path, self.content_seen_path, self.content_items_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

    def read_profile(self) -> dict[str, Any]:
        data = locked_read_json(self.profile_path, {}, "interest_profile.lock")
        if not isinstance(data, dict) or not data:
            return _default_profile()
        profile = _default_profile()
        profile.update(data)
        for key in ("topics", "sources", "content_types"):
            if not isinstance(profile.get(key), dict):
                profile[key] = {}
        for key in ("processed_feedback_keys", "processed_implicit_keys"):
            if not isinstance(profile.get(key), list):
                profile[key] = []
        return profile

    def write_profile(self, profile: dict[str, Any]) -> None:
        profile["updated_at"] = _now()
        profile["processed_feedback_keys"] = list(profile.get("processed_feedback_keys") or [])[-300:]
        profile["processed_implicit_keys"] = list(profile.get("processed_implicit_keys") or [])[-300:]
        locked_write_json(self.profile_path, profile, "interest_profile.lock")

    def _update_dimension(
        self,
        profile: dict[str, Any],
        section: str,
        key: str,
        delta: float,
        evidence_type: str,
    ) -> None:
        if not key:
            return
        bucket = profile.setdefault(section, {})
        current = bucket.get(key)
        if not isinstance(current, dict):
            current = {"weight": 0.0, "evidence": 0, "last_evidence": None}
        current["weight"] = round(_clamp(float(current.get("weight", 0.0)) + delta), 4)
        current["evidence"] = int(current.get("evidence", 0)) + 1
        current["last_evidence"] = evidence_type
        current["updated_at"] = _now()
        bucket[key] = current

    def record_feedback(
        self,
        text: str,
        *,
        target_item: dict[str, Any] | None = None,
        message_key: str | None = None,
    ) -> dict[str, Any] | None:
        # INTEREST_LEARNING_ATTRIBUTION_V1
        content = str(text or "").strip()
        if not content:
            return None

        signal = ""
        delta = 0.0
        if NEGATIVE_STRONG.search(content):
            signal, delta = "explicit_negative", -0.45
        elif POSITIVE_STRONG.search(content):
            signal, delta = "explicit_positive", 0.45
        elif ASK_LINK.search(content):
            signal, delta = "ask_link", 0.14
        elif ASK_DETAIL.search(content):
            signal, delta = "ask_detail", 0.12
        else:
            return None

        profile = self.read_profile()
        key = message_key or hashlib.sha256(content.encode("utf-8")).hexdigest()[:20]
        if key in profile["processed_feedback_keys"]:
            return None

        raw_target = target_item or profile.get("last_delivered_item") or {}
        item = normalize_item(raw_target)
        target_recent = _target_is_recent(raw_target)
        explicit_tags = infer_tags_from_text(content)
        target_tags = list(item.get("tags") or [])

        weak_signal = signal in {"ask_link", "ask_detail"}
        if weak_signal and not target_recent:
            return None

        if explicit_tags:
            tags = explicit_tags
            linked_to_target = target_recent and bool(set(explicit_tags) & set(target_tags))
        else:
            if not target_recent or not target_tags:
                return None
            tags = target_tags
            linked_to_target = True

        for tag in tags:
            self._update_dimension(profile, "topics", tag, delta, signal)

        source = str(item.get("source") or "") if linked_to_target else ""
        content_type = str(item.get("content_type") or "") if linked_to_target else ""
        if source and source != "unknown":
            self._update_dimension(profile, "sources", source, delta * 0.5, signal)
        if content_type:
            self._update_dimension(profile, "content_types", content_type, delta * 0.4, signal)

        profile["processed_feedback_keys"].append(key)
        self.write_profile(profile)

        record = {
            "event": signal,
            "message_key": key,
            "text_preview": content[:120],
            "item_id": item.get("id") if linked_to_target else None,
            "topics": tags,
            "source": source,
            "content_type": content_type,
            "delta": delta,
            "feedback_scope": "target_item" if linked_to_target else "explicit_topic",
        }
        _append_bounded_jsonl(
            self.feedback_log_path,
            record,
            "feedback_log.lock",
            3000,
        )
        return record

    def sync_feedback_from_context(self) -> int:
        data = locked_read_json(self.context_queue_path, {}, "context_queue.lock")
        messages = data.get("messages") if isinstance(data, dict) else []
        if not isinstance(messages, list):
            messages = []

        applied = 0
        for msg in messages[-30:]:
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            text = str(msg.get("content_snippet") or msg.get("content") or msg.get("text") or "").strip()
            timestamp = str(msg.get("timestamp") or msg.get("time") or "")
            key = hashlib.sha256(f"{timestamp}|{text}".encode("utf-8")).hexdigest()[:20]
            if self.record_feedback(text, message_key=key) is not None:
                applied += 1

        state = locked_read_json(self.alive_state_path, {}, "alive_state.lock")
        if isinstance(state, dict):
            try:
                ignored = int(state.get("ignored_proactive_count") or 0)
            except Exception:
                ignored = 0
            if ignored >= 3:
                self.record_repeated_ignored(ignored, state=state)
        return applied

    def record_repeated_ignored(
        self,
        ignored_count: int,
        *,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        # INTEREST_LEARNING_IGNORED_ATTRIBUTION_V1
        if int(ignored_count) < 3:
            return None

        profile = self.read_profile()
        raw_item = profile.get("last_delivered_item")
        if not isinstance(raw_item, dict) or not raw_item:
            return None

        if state is None:
            loaded_state = locked_read_json(
                self.alive_state_path,
                {},
                "alive_state.lock",
            )
            state = loaded_state if isinstance(loaded_state, dict) else {}

        if not _content_was_unanswered(raw_item, state):
            return None

        item = normalize_item(raw_item)
        if not item.get("id"):
            return None

        reply_marker = str(
            state.get("last_user_reply_at") or "no-user-reply"
        )
        key = f"ignored-sequence:{item['id']}:{reply_marker}"
        if key in profile["processed_implicit_keys"]:
            return None

        delta = -0.05
        for tag in item.get("tags") or []:
            self._update_dimension(
                profile,
                "topics",
                str(tag),
                delta,
                "repeated_ignored",
            )

        profile["processed_implicit_keys"].append(key)
        self.write_profile(profile)

        record = {
            "event": "repeated_ignored",
            "message_key": key,
            "item_id": item.get("id"),
            "topics": item.get("tags") or [],
            "delta": delta,
            "ignored_count": int(ignored_count),
            "delivered_at": raw_item.get("delivered_at"),
            "last_user_reply_at": state.get("last_user_reply_at"),
            "attribution": "unanswered_content_sequence",
        }
        _append_bounded_jsonl(
            self.feedback_log_path,
            record,
            "feedback_log.lock",
            3000,
        )
        return record

    def record_delivery(self, item: dict[str, Any], *, tick_id: str | None = None) -> dict[str, Any]:
        normalized = normalize_item(item)
        # Idempotent safety net for delivery paths outside the watcher reservation.
        self.topic_dedup.commit_delivery(normalized, tick_id=tick_id)
        normalized["delivered_at"] = _now()
        _append_bounded_jsonl(
            self.content_seen_path,
            {
                "event": "delivered",
                "item_id": normalized["id"],
                "url": normalized.get("url"),
                "source": normalized.get("source"),
                "content_type": normalized.get("content_type"),
                "tags": normalized.get("tags"),
                "tick_id": tick_id,
                "delivered_at": normalized["delivered_at"],
            },
            "content_seen.lock",
            5000,
        )
        _append_bounded_jsonl(
            self.content_items_path,
            {"event": "delivered", **normalized, "tick_id": tick_id},
            "content_items.lock",
            5000,
        )
        profile = self.read_profile()
        profile["last_delivered_item"] = normalized
        self.write_profile(profile)
        return normalized

    def record_ranked_item(self, item: dict[str, Any]) -> None:
        normalized = normalize_item(item)
        _append_bounded_jsonl(
            self.content_items_path,
            {"event": "ranked", **normalized},
            "content_items.lock",
            5000,
        )

    def _seen_ids(self) -> set[str]:
        ids: set[str] = set()
        try:
            lines = self.content_seen_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return ids
        for line in lines[-5000:]:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict) and item.get("event") == "delivered" and item.get("item_id"):
                ids.add(str(item["item_id"]))
        return ids

    def was_seen(self, item: dict[str, Any]) -> bool:
        try:
            return self.topic_dedup.check(
                normalize_item(item),
                include_reservations=True,
            ).blocked
        except Exception:
            return normalize_item(item)["id"] in self._seen_ids()

    def _recent_tag_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        try:
            lines = self.content_seen_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return counts
        for line in lines[-30:]:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if not isinstance(item, dict) or item.get("event") != "delivered":
                continue
            tags = item.get("tags")
            if isinstance(tags, list):
                for tag in tags:
                    counts[str(tag)] = counts.get(str(tag), 0) + 1
        return counts

    def rank_item(self, item: dict[str, Any], base_score: float) -> dict[str, Any]:
        normalized = normalize_item(item)
        profile = self.read_profile()
        tag_weights = [
            float((profile.get("topics") or {}).get(tag, {}).get("weight", 0.0))
            for tag in normalized.get("tags") or []
        ]
        topic_interest = sum(tag_weights) / len(tag_weights) if tag_weights else 0.0
        source_interest = float(
            (profile.get("sources") or {}).get(normalized["source"], {}).get("weight", 0.0)
        )
        type_interest = float(
            (profile.get("content_types") or {}).get(normalized["content_type"], {}).get("weight", 0.0)
        )

        recent_counts = self._recent_tag_counts()
        fatigue_count = sum(recent_counts.get(tag, 0) for tag in normalized.get("tags") or [])
        fatigue_penalty = min(0.25, fatigue_count * 0.03)

        interest_score = 0.35 * topic_interest + 0.15 * source_interest + 0.10 * type_interest
        final_score = max(0.0, min(1.5, float(base_score) + interest_score - fatigue_penalty))

        normalized.update(
            {
                "base_score": round(float(base_score), 4),
                "interest_score": round(interest_score, 4),
                "fatigue_penalty": round(fatigue_penalty, 4),
                "final_score": round(final_score, 4),
                "score": round(final_score, 4),
            }
        )
        return normalized
