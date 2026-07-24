"""Context queue, activity leases, and prompt visibility for Hermes Alive.

The queue is rebuilt from state.db and shared across sessions.  The activity
lease file extends the in-process busy flag across hook processes so the
proactive watcher fails closed while Hermes or a subagent is still working.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from safe_io import LOCK_DIR, file_lock, locked_read_json

# Marker: HERMES_ALIVE_CONTEXT_VISIBILITY_V1
# Marker: HERMES_ALIVE_CROSS_PROCESS_ACTIVITY_LEASE_V1
# Marker: HERMES_ALIVE_EFFECTIVE_CONVERSATION_QUEUE_V1
# Marker: HERMES_ALIVE_PROMPT_CONTEXT_SNAPSHOT_V1

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))

MAX_MESSAGES = 30
FETCH_MULTIPLIER = 12
CONTENT_SNIPPET_CHARS = 1000
PROMPT_SNIPPET_CHARS = 240
PROMPT_MAX_MESSAGES = 12
PROMPT_MAX_AGE_SECONDS = 21600.0
SAME_ROLE_COLLAPSE_SECONDS = 120.0
ACTIVITY_LEASE_TTL_SECONDS = float(
    os.getenv("HERMES_ALIVE_ACTIVITY_LEASE_TTL_SECONDS", "43200")
)

SHARED_DIR = Path(
    os.getenv(
        "HERMES_ALIVE_SHARED_DIR",
        "/opt/data/hermes_alive_shared",
    )
)
QUEUE_FILE = SHARED_DIR / "context_queue.json"
ACTIVITY_FILE = SHARED_DIR / "activity_leases.json"
PROACTIVE_LOG = SHARED_DIR / "proactive_log.jsonl"

WEIXIN_SOURCE = "weixin"

HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")
STATE_DB = Path(
    os.getenv(
        "HERMES_STATE_DB",
        os.path.join(HERMES_HOME, "state.db"),
    )
)

CONTROL_MESSAGE_RE = re.compile(r"^\s*/\S+")
REFERENT_ANCHOR_RE = re.compile(
    r"("
    r"[A-Za-z0-9_.-]+\.(?:tar\.gz|zip|sh|py|md|json|yaml|yml)"
    r"|hermes-[A-Za-z0-9_.-]+"
    r"|v\d+(?:[._-]\d+)+"
    r"|[A-Fa-f0-9]{12,64}"
    r")"
)


def _weixin_user_id() -> str:
    try:
        from weixin_peer import resolve_weixin_peer

        resolved, _reason = resolve_weixin_peer(
            os.getenv(
                "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
                "",
            )
        )
        return resolved
    except Exception:
        return os.getenv(
            "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
            "",
        ).strip()


_session_busy = False
_session_busy_lock = threading.Lock()


def _context_value(context: Any, names: tuple[str, ...]) -> str:
    if not isinstance(context, dict):
        return ""
    for name in names:
        value = context.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    for nested_name in (
        "session",
        "message",
        "request",
        "metadata",
        "context",
        "event",
    ):
        nested = context.get(nested_name)
        if isinstance(nested, dict):
            value = _context_value(nested, names)
            if value:
                return value
    return ""


def _activity_lease_key(context: Any = None) -> tuple[str, bool]:
    raw = _context_value(
        context,
        (
            "session_id",
            "sessionId",
            "conversation_id",
            "conversationId",
            "thread_id",
            "threadId",
        ),
    )
    if raw:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return f"session:{digest}", True
    return f"pid:{os.getpid()}", False


def _prune_leases(
    leases: Any,
    *,
    now: float | None = None,
) -> dict[str, dict[str, Any]]:
    current = time.time() if now is None else float(now)
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(leases, dict):
        return result
    for key, value in leases.items():
        if not isinstance(value, dict):
            continue
        try:
            updated_at = float(value.get("updated_at") or 0.0)
        except (TypeError, ValueError):
            continue
        if updated_at <= 0.0:
            continue
        if current - updated_at > ACTIVITY_LEASE_TTL_SECONDS:
            continue
        result[str(key)] = dict(value)
    return result


def _read_activity_state() -> dict[str, Any]:
    data = locked_read_json(
        ACTIVITY_FILE,
        {},
        "activity_leases.lock",
    )
    if not isinstance(data, dict):
        data = {}
    leases = _prune_leases(data.get("leases"))
    return {
        "version": 1,
        "updated_at": str(data.get("updated_at") or ""),
        "leases": leases,
    }


def _write_activity_state(data: dict[str, Any]) -> None:
    from safe_io import atomic_write_json

    atomic_write_json(ACTIVITY_FILE, data)


def set_session_busy(context: dict[str, Any] | None = None) -> None:
    """Mark a session busy in-process and through a shared cross-process lease."""
    global _session_busy
    with _session_busy_lock:
        _session_busy = True

    key, stable = _activity_lease_key(context)
    now = time.time()
    with file_lock(LOCK_DIR / "activity_leases.lock"):
        current = _read_json_unlocked(ACTIVITY_FILE, {})
        leases = _prune_leases(
            current.get("leases")
            if isinstance(current, dict)
            else {},
            now=now,
        )
        existing = leases.get(key, {})
        depth = 1
        if not stable:
            try:
                depth = max(0, int(existing.get("depth") or 0)) + 1
            except (TypeError, ValueError):
                depth = 1
        leases[key] = {
            "updated_at": now,
            "started_at": float(existing.get("started_at") or now),
            "pid": os.getpid(),
            "stable_session_key": stable,
            "depth": depth,
        }
        _write_json_unlocked(
            ACTIVITY_FILE,
            {
                "version": 1,
                "updated_at": datetime.now(CST).isoformat(),
                "leases": leases,
            },
        )


def set_session_idle(context: dict[str, Any] | None = None) -> None:
    """Release the matching cross-process activity lease."""
    global _session_busy
    with _session_busy_lock:
        _session_busy = False

    key, stable = _activity_lease_key(context)
    now = time.time()
    with file_lock(LOCK_DIR / "activity_leases.lock"):
        current = _read_json_unlocked(ACTIVITY_FILE, {})
        leases = _prune_leases(
            current.get("leases")
            if isinstance(current, dict)
            else {},
            now=now,
        )
        existing = leases.get(key)
        if isinstance(existing, dict) and not stable:
            try:
                depth = max(0, int(existing.get("depth") or 0) - 1)
            except (TypeError, ValueError):
                depth = 0
            if depth > 0:
                existing["depth"] = depth
                existing["updated_at"] = now
                leases[key] = existing
            else:
                leases.pop(key, None)
        else:
            leases.pop(key, None)
        _write_json_unlocked(
            ACTIVITY_FILE,
            {
                "version": 1,
                "updated_at": datetime.now(CST).isoformat(),
                "leases": leases,
            },
        )


def activity_lease_snapshot() -> dict[str, Any]:
    state = _read_activity_state()
    leases = state.get("leases", {})
    return {
        "busy": bool(leases),
        "lease_count": len(leases) if isinstance(leases, dict) else 0,
        "updated_at": state.get("updated_at"),
        "lease_key_hashes": sorted(
            hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:12]
            for key in (leases.keys() if isinstance(leases, dict) else [])
        ),
    }


def is_session_busy() -> bool:
    """Return True if this process or any shared activity lease is busy."""
    with _session_busy_lock:
        local_busy = _session_busy
    if local_busy:
        return True
    return bool(activity_lease_snapshot().get("busy"))


def freshness_decay(seconds_ago: float) -> float:
    """Return prompt relevance for messages from now through six hours."""
    age = max(0.0, float(seconds_ago))
    if age > PROMPT_MAX_AGE_SECONDS:
        return 0.0
    return math.cos(
        math.pi / 2.0 * (age / PROMPT_MAX_AGE_SECONDS)
    )


def freshness_label(seconds_ago: float) -> str:
    if seconds_ago < 1800:
        return "刚刚"
    if seconds_ago < 7200:
        return "大约一小时前"
    if seconds_ago < 14400:
        return "之前"
    return "更早"


def _sort_key(message: dict[str, Any]) -> tuple[float, str]:
    return (
        float(message.get("timestamp") or 0.0),
        str(message.get("message_id") or ""),
    )


class ContextQueue:
    """Persistent queue of recent effective user/assistant turns."""

    def __init__(
        self,
        path: Path = QUEUE_FILE,
        max_messages: int = MAX_MESSAGES,
    ) -> None:
        self.path = path
        self.max_messages = max_messages
        self.lock_name = "context_queue.lock"
        self._cache: dict[str, Any] | None = None
        self._cache_mtime: float | None = None

    def read(self, *, use_cache: bool = True) -> dict[str, Any]:
        if use_cache and self._cache is not None:
            try:
                mtime = self.path.stat().st_mtime
            except OSError:
                mtime = None
            if mtime == self._cache_mtime:
                return self._cache

        data = locked_read_json(
            self.path,
            {},
            self.lock_name,
        )
        normalized = self._normalize(data)
        self._cache = normalized
        try:
            self._cache_mtime = self.path.stat().st_mtime
        except OSError:
            self._cache_mtime = None
        return normalized

    def refresh_from_state_db(self) -> dict[str, Any]:
        """Rebuild the queue from the latest effective state.db turns."""
        rows = _fetch_latest_rows(
            limit=max(
                self.max_messages * FETCH_MULTIPLIER,
                180,
            )
        )
        rebuilt = self._build_effective(rows)
        data = {
            "version": 2,
            "updated_at": datetime.now(CST).isoformat(),
            "source": WEIXIN_SOURCE,
            "user_id": _weixin_user_id(),
            "max_messages": self.max_messages,
            "message_count": len(rebuilt),
            "messages": rebuilt,
        }
        with file_lock(LOCK_DIR / self.lock_name):
            _write_json_unlocked(self.path, data)

        self._cache = data
        try:
            self._cache_mtime = self.path.stat().st_mtime
        except OSError:
            self._cache_mtime = None
        return data

    def expected_from_state_db(self) -> list[dict[str, Any]]:
        rows = _fetch_latest_rows(
            limit=max(
                self.max_messages * FETCH_MULTIPLIER,
                180,
            )
        )
        return self._build_effective(rows)

    def _build_effective(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized = [
            message
            for message in (
                _normalize_message(row)
                for row in rows
            )
            if message is not None
        ]
        normalized = _dedupe_messages(
            sorted(normalized, key=_sort_key)
        )
        collapsed = _collapse_consecutive_messages(normalized)
        return collapsed[-self.max_messages :]

    def _normalize(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return self._empty()
        raw_messages = data.get("messages", [])
        messages: list[dict[str, Any]] = []
        if isinstance(raw_messages, list):
            for item in raw_messages:
                normalized = _normalize_message(item)
                if normalized is not None:
                    messages.append(normalized)
        messages = _collapse_consecutive_messages(
            _dedupe_messages(
                sorted(messages, key=_sort_key)
            )
        )[-self.max_messages :]
        return {
            "version": int(data.get("version") or 2),
            "updated_at": str(data.get("updated_at") or ""),
            "source": str(data.get("source") or WEIXIN_SOURCE),
            "user_id": str(
                _weixin_user_id()
                or data.get("user_id")
                or ""
            ),
            "max_messages": int(
                data.get("max_messages")
                or self.max_messages
            ),
            "message_count": len(messages),
            "messages": messages,
        }

    def _empty(self) -> dict[str, Any]:
        return {
            "version": 2,
            "updated_at": "",
            "source": WEIXIN_SOURCE,
            "user_id": _weixin_user_id(),
            "max_messages": self.max_messages,
            "message_count": 0,
            "messages": [],
        }


_QUEUE = ContextQueue()


def capture_recent_context() -> dict[str, Any]:
    """Refresh the queue and return user-style signals."""
    try:
        data = _QUEUE.refresh_from_state_db()
        messages = data.get("messages", [])
        signals = _extract_user_style_signals(messages)
        logger.info(
            "Context queue rebuilt: %d effective messages",
            len(messages) if isinstance(messages, list) else 0,
        )
        return {"user_style_signals": signals}
    except Exception:
        logger.exception("Failed to refresh context queue")
        return {}


def refresh_context_queue() -> dict[str, Any]:
    """Tick-time rebuild before activity and compose decisions."""
    return _QUEUE.refresh_from_state_db()


def read_context_queue(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        return refresh_context_queue()
    return _QUEUE.read()


def _queue_sha256(data: dict[str, Any]) -> str:
    payload = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _message_signature(message: dict[str, Any]) -> tuple[Any, ...]:
    return (
        message.get("role"),
        float(message.get("timestamp") or 0.0),
        message.get("session_id"),
        message.get("message_id"),
        hashlib.sha256(
            str(message.get("content_snippet") or "").encode("utf-8")
        ).hexdigest(),
    )


def _queue_health(data: dict[str, Any]) -> dict[str, Any]:
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    expected = _QUEUE.expected_from_state_db()
    actual_signatures = [
        _message_signature(message)
        for message in messages
        if isinstance(message, dict)
    ]
    expected_signatures = [
        _message_signature(message)
        for message in expected
    ]
    matches = actual_signatures == expected_signatures

    latest_actual = (
        float(messages[-1]["timestamp"])
        if messages
        else None
    )
    latest_expected = (
        float(expected[-1]["timestamp"])
        if expected
        else None
    )
    lag_seconds = None
    if latest_actual is not None and latest_expected is not None:
        lag_seconds = latest_expected - latest_actual

    user_count = sum(
        int(message.get("role") == "user")
        for message in messages
        if isinstance(message, dict)
    )
    assistant_count = sum(
        int(message.get("role") == "assistant")
        for message in messages
        if isinstance(message, dict)
    )
    healthy = matches and (
        not messages
        or user_count > 0
    )
    return {
        "queue_healthy": healthy,
        "queue_matches_db": matches,
        "queue_db_lag_seconds": lag_seconds,
        "expected_message_count": len(expected),
        "user_message_count": user_count,
        "assistant_message_count": assistant_count,
        "distinct_session_count": len(
            {
                str(message.get("session_id") or "")
                for message in messages
                if isinstance(message, dict)
                and str(message.get("session_id") or "")
            }
        ),
    }


def activity_snapshot(*, refresh: bool = False) -> dict[str, Any]:
    data = read_context_queue(refresh=refresh)
    messages = data.get("messages", [])
    health = _queue_health(data)
    lease = activity_lease_snapshot()

    if not isinstance(messages, list) or not messages:
        return {
            "has_context": False,
            "last_message_role": None,
            "last_message_timestamp": None,
            "last_user_timestamp": None,
            "message_count": 0,
            "updated_at": data.get("updated_at"),
            "queue_sha256": _queue_sha256(data),
            "session_busy": bool(lease.get("busy")),
            "busy_lease_count": int(lease.get("lease_count") or 0),
            **health,
        }

    last_message = messages[-1]
    last_user_ts: float | None = None
    for message in reversed(messages):
        if (
            isinstance(message, dict)
            and message.get("role") == "user"
        ):
            try:
                last_user_ts = float(message["timestamp"])
            except (TypeError, ValueError, KeyError):
                last_user_ts = None
            break
    return {
        "has_context": True,
        "last_message_role": last_message.get("role"),
        "last_message_timestamp": last_message.get("timestamp"),
        "last_user_timestamp": last_user_ts,
        "message_count": len(messages),
        "updated_at": data.get("updated_at"),
        "queue_sha256": _queue_sha256(data),
        "session_busy": bool(lease.get("busy")),
        "busy_lease_count": int(lease.get("lease_count") or 0),
        **health,
    }


def read_user_style_signals() -> dict[str, Any]:
    data = read_context_queue()
    return _extract_user_style_signals(
        data.get("messages", [])
    )


def build_prompt_context(
    *,
    refresh: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    data = read_context_queue(refresh=refresh)
    health = _queue_health(data)
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    reference = time.time() if now is None else float(now)
    prompt_messages: list[dict[str, Any]] = []
    anchors: set[str] = set()

    for message in messages:
        if not isinstance(message, dict):
            continue
        try:
            seconds_ago = reference - float(message["timestamp"])
        except (TypeError, ValueError, KeyError):
            continue
        if seconds_ago < -5.0:
            continue
        weight = freshness_decay(max(0.0, seconds_ago))
        if weight <= 0.0:
            continue
        content = str(message.get("content_snippet") or "").strip()
        if not content:
            continue
        for match in REFERENT_ANCHOR_RE.findall(content):
            anchors.add(str(match).strip().lower())
        prompt_messages.append(
            {
                "role": message.get("role"),
                "content": content,
                "timestamp": float(message["timestamp"]),
                "label": freshness_label(max(0.0, seconds_ago)),
                "weight": weight,
            }
        )

    prompt_messages = prompt_messages[-PROMPT_MAX_MESSAGES:]
    hash_rows = [
        {
            "role": message["role"],
            "timestamp": message["timestamp"],
            "content_hash": hashlib.sha256(
                message["content"].encode("utf-8")
            ).hexdigest(),
        }
        for message in prompt_messages
    ]
    prompt_hash = hashlib.sha256(
        json.dumps(
            hash_rows,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    latest = messages[-1] if messages else None
    latest_ts = (
        float(latest.get("timestamp"))
        if isinstance(latest, dict)
        and latest.get("timestamp") is not None
        else None
    )
    metadata = {
        "queue_sha256": _queue_sha256(data),
        "queue_updated_at": data.get("updated_at"),
        "queue_message_count": len(messages),
        "queue_distinct_session_count": health.get(
            "distinct_session_count",
            0,
        ),
        "queue_user_message_count": health.get(
            "user_message_count",
            0,
        ),
        "queue_assistant_message_count": health.get(
            "assistant_message_count",
            0,
        ),
        "queue_matches_db": health.get(
            "queue_matches_db",
            False,
        ),
        "queue_healthy": health.get(
            "queue_healthy",
            False,
        ),
        "queue_db_lag_seconds": health.get(
            "queue_db_lag_seconds",
        ),
        "latest_context_role": (
            latest.get("role")
            if isinstance(latest, dict)
            else None
        ),
        "latest_context_timestamp": latest_ts,
        "latest_context_age_seconds": (
            max(0.0, reference - latest_ts)
            if latest_ts is not None
            else None
        ),
        "context_prompt_eligible_count": len(prompt_messages),
        "context_prompt_hash": prompt_hash,
        "referent_anchor_count": len(anchors),
        "referent_anchor_hash": hashlib.sha256(
            "\n".join(sorted(anchors)).encode("utf-8")
        ).hexdigest(),
        "session_busy_boolean": is_session_busy(),
    }

    text = ""
    if prompt_messages:
        lines = [
            "## 你和停云的最近有效对话",
            "这些内容来自跨 session 队列。只能基于明确可见的信息延续话题；"
            "不确定对象时必须说出具体对象或改成新话题。",
        ]
        for message in prompt_messages:
            role = (
                "你"
                if message.get("role") == "assistant"
                else "停云"
            )
            content = str(message.get("content") or "")
            if len(content) > PROMPT_SNIPPET_CHARS:
                content = (
                    content[: PROMPT_SNIPPET_CHARS - 3]
                    + "..."
                )
            lines.append(
                f"- [{message.get('label', '')}][{role}] {content}"
            )
        text = "\n".join(lines)

    return {
        "text": text,
        "metadata": metadata,
        "referent_anchors": sorted(anchors),
    }


def prompt_context_snapshot(
    *,
    refresh: bool = False,
) -> dict[str, Any]:
    return dict(
        build_prompt_context(
            refresh=refresh,
        ).get("metadata")
        or {}
    )


def read_recent_context(
    *,
    refresh: bool = False,
) -> str:
    """Return recent effective conversation text for prompt injection."""
    return str(
        build_prompt_context(
            refresh=refresh,
        ).get("text")
        or ""
    )


def _fetch_latest_rows(limit: int) -> list[dict[str, Any]]:
    user_id = _weixin_user_id()
    if not user_id:
        logger.debug(
            "No WEIXIN_CHAT_ID configured; cannot refresh context queue"
        )
        return []
    if not STATE_DB.exists():
        logger.debug("state.db not found: %s", STATE_DB)
        return []

    conn = sqlite3.connect(str(STATE_DB))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT m.id AS message_id, m.session_id, "
            "m.role, m.content, m.timestamp "
            "FROM messages m "
            "JOIN sessions s ON m.session_id = s.id "
            "WHERE s.source = ? AND s.user_id = ? "
            "AND m.active = 1 "
            "AND m.role IN ('user', 'assistant') "
            "AND TRIM(COALESCE(m.content, '')) <> '' "
            "ORDER BY m.timestamp DESC, m.id DESC LIMIT ?",
            (WEIXIN_SOURCE, user_id, limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
    return list(reversed(rows))


def _normalize_message(
    item: Any,
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    role = item.get("role")
    if role not in {"user", "assistant"}:
        return None
    try:
        timestamp = float(item["timestamp"])
    except (TypeError, ValueError, KeyError):
        return None

    content = item.get("content_snippet")
    if content is None:
        content = item.get("content")
    content_snippet = str(content or "").strip()
    if not content_snippet:
        return None
    if (
        role == "user"
        and CONTROL_MESSAGE_RE.match(content_snippet)
    ):
        return None
    content_snippet = content_snippet[:CONTENT_SNIPPET_CHARS]

    message: dict[str, Any] = {
        "role": role,
        "timestamp": timestamp,
        "content_snippet": content_snippet,
        "session_id": str(item.get("session_id") or ""),
    }
    message_id = item.get(
        "message_id",
        item.get("id"),
    )
    if message_id is not None:
        try:
            message["message_id"] = int(message_id)
        except (TypeError, ValueError):
            message["message_id"] = str(message_id)
    return message


def _collapse_consecutive_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    for message in messages:
        if not collapsed:
            collapsed.append(dict(message))
            continue
        previous = collapsed[-1]
        same_stream = (
            previous.get("role") == message.get("role")
            and previous.get("session_id")
            == message.get("session_id")
        )
        gap = (
            float(message.get("timestamp") or 0.0)
            - float(previous.get("timestamp") or 0.0)
        )
        if same_stream and 0.0 <= gap <= SAME_ROLE_COLLAPSE_SECONDS:
            previous_text = str(
                previous.get("content_snippet") or ""
            )
            current_text = str(
                message.get("content_snippet") or ""
            )
            if current_text not in previous_text:
                joined = (
                    f"{previous_text}\n{current_text}"
                    if previous_text
                    else current_text
                )
                previous["content_snippet"] = joined[
                    :CONTENT_SNIPPET_CHARS
                ]
            previous["timestamp"] = message.get("timestamp")
            previous["message_id"] = message.get(
                "message_id",
                previous.get("message_id"),
            )
            continue
        collapsed.append(dict(message))
    return collapsed


def _message_key(message: dict[str, Any]) -> str:
    message_id = message.get("message_id")
    if message_id is not None:
        return f"id:{message_id}"
    return (
        "fallback:{session_id}:{role}:{timestamp}:{content}"
    ).format(
        session_id=message.get("session_id", ""),
        role=message.get("role", ""),
        timestamp=message.get("timestamp", ""),
        content=message.get(
            "content_snippet",
            "",
        )[:80],
    )


def _dedupe_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for message in messages:
        key = _message_key(message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(message)
    return deduped


def _extract_user_style_signals(
    messages: list[Any],
) -> dict[str, Any]:
    signal_messages: list[dict[str, Any]] = []
    last_user_ts: float | None = None
    prev_user_ts: float | None = None
    for message in messages:
        normalized = _normalize_message(message)
        if normalized is None:
            continue
        signal_messages.append(
            {
                "role": normalized["role"],
                "content": normalized["content_snippet"],
                "timestamp": normalized["timestamp"],
            }
        )
        if normalized["role"] == "user":
            prev_user_ts = last_user_ts
            last_user_ts = float(normalized["timestamp"])
    try:
        from voice_engine import extract_user_style_signals

        signals = extract_user_style_signals(
            signal_messages
        )
        if (
            last_user_ts is not None
            and _sent_count_between(
                prev_user_ts,
                last_user_ts,
            )
            >= 3
        ):
            signals["ignored_3_plus"] = True
        return signals
    except Exception:
        logger.exception(
            "Failed to extract user style signals"
        )
        return {}


def _sent_count_between(
    start_ts: float | None,
    end_ts: float,
) -> int:
    if not PROACTIVE_LOG.exists():
        return 0
    count = 0
    try:
        with file_lock(
            LOCK_DIR / "proactive_log.lock"
        ):
            log_text = PROACTIVE_LOG.read_text(
                encoding="utf-8",
                errors="ignore",
            )
    except Exception:
        return 0
    for line in log_text.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("decision") != "sent":
            continue
        try:
            sent_ts = datetime.fromisoformat(
                str(item.get("time", ""))
            ).timestamp()
        except (TypeError, ValueError):
            continue
        if start_ts is not None and sent_ts <= start_ts:
            continue
        if sent_ts < end_ts:
            count += 1
    return count


def _read_json_unlocked(
    path: Path,
    default: Any,
) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return default


def _write_json_unlocked(
    path: Path,
    data: Any,
) -> None:
    from safe_io import atomic_write_json

    atomic_write_json(path, data)
