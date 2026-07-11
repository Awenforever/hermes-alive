"""Context queue for Hermes Alive activity guard and proactive freshness.

The queue is the single runtime source for recent conversation context.  It is
rebuilt/incrementally refreshed from state.db, persisted for crash recovery, and
read by both the activity guard and LLM prompt composer.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from safe_io import LOCK_DIR, file_lock, locked_read_json

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))

MAX_MESSAGES = 30
CONTENT_SNIPPET_CHARS = 1000
PROMPT_SNIPPET_CHARS = 200

SHARED_DIR = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
QUEUE_FILE = SHARED_DIR / "context_queue.json"
PROACTIVE_LOG = SHARED_DIR / "proactive_log.jsonl"

WEIXIN_SOURCE = "weixin"

HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")
STATE_DB = Path(os.getenv("HERMES_STATE_DB", os.path.join(HERMES_HOME, "state.db")))


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


def set_session_busy() -> None:
    """Mark the in-process Hermes agent session as running."""
    global _session_busy
    with _session_busy_lock:
        _session_busy = True


def set_session_idle() -> None:
    """Mark the in-process Hermes agent session as idle."""
    global _session_busy
    with _session_busy_lock:
        _session_busy = False


def is_session_busy() -> bool:
    """Return whether Hermes is currently processing a session in this process."""
    with _session_busy_lock:
        return _session_busy


def freshness_decay(seconds_ago: float) -> float:
    """Return prompt relevance weight for a message age."""
    import math

    thirty_min = 1800
    six_hours = 21600
    duration = six_hours - thirty_min

    if seconds_ago < thirty_min:
        return 0.0
    if seconds_ago <= six_hours:
        t = (seconds_ago - thirty_min) / duration
        return math.cos(math.pi / 2.0 * t)
    return 0.0


def freshness_label(seconds_ago: float) -> str:
    if seconds_ago < 1800:
        return "刚刚"
    if seconds_ago < 7200:
        return "大约一小时前"
    if seconds_ago < 14400:
        return "之前"
    return "更早"


class ContextQueue:
    """Persistent bounded queue of recent user/assistant messages."""

    def __init__(self, path: Path = QUEUE_FILE, max_messages: int = MAX_MESSAGES) -> None:
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

        data = locked_read_json(self.path, {}, self.lock_name)
        normalized = self._normalize(data)
        self._cache = normalized
        try:
            self._cache_mtime = self.path.stat().st_mtime
        except OSError:
            self._cache_mtime = None
        return normalized

    def refresh_from_state_db(self) -> dict[str, Any]:
        """Merge the latest state.db messages into the persisted queue."""
        rows = _fetch_latest_rows(limit=max(self.max_messages * 2, 60))
        if not rows:
            data = self.read(use_cache=False)
            if not data:
                data = self._empty()
            return data

        with file_lock(LOCK_DIR / self.lock_name):
            current = self._normalize(_read_json_unlocked(self.path, {}))
            merged = self._merge(current.get("messages", []), rows)
            data = {
                "version": 1,
                "updated_at": datetime.now(CST).isoformat(),
                "source": WEIXIN_SOURCE,
                "user_id": _weixin_user_id(),
                "max_messages": self.max_messages,
                "message_count": len(merged),
                "messages": merged,
            }
            _write_json_unlocked(self.path, data)

        self._cache = data
        try:
            self._cache_mtime = self.path.stat().st_mtime
        except OSError:
            self._cache_mtime = None
        return data

    def _merge(self, existing: list[Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_key: dict[str, dict[str, Any]] = {}
        for item in existing:
            normalized = _normalize_message(item)
            if normalized is None:
                continue
            by_key[_message_key(normalized)] = normalized
        for row in rows:
            normalized = _normalize_message(row)
            if normalized is None:
                continue
            by_key[_message_key(normalized)] = normalized
        messages = sorted(by_key.values(), key=lambda m: (float(m["timestamp"]), int(m.get("message_id") or 0)))
        return messages[-self.max_messages :]

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
        messages = sorted(messages, key=lambda m: (float(m["timestamp"]), int(m.get("message_id") or 0)))
        messages = _dedupe_messages(messages)[-self.max_messages :]
        return {
            "version": int(data.get("version") or 1),
            "updated_at": str(data.get("updated_at") or ""),
            "source": str(data.get("source") or WEIXIN_SOURCE),
            "user_id": str(_weixin_user_id() or data.get("user_id") or ""),
            "max_messages": int(data.get("max_messages") or self.max_messages),
            "message_count": len(messages),
            "messages": messages,
        }

    def _empty(self) -> dict[str, Any]:
        return {
            "version": 1,
            "updated_at": "",
            "source": WEIXIN_SOURCE,
            "user_id": _weixin_user_id(),
            "max_messages": self.max_messages,
            "message_count": 0,
            "messages": [],
        }


_QUEUE = ContextQueue()


def capture_recent_context() -> dict[str, Any]:
    """Refresh ContextQueue from state.db and return user_style_signals.

    Called by handler.py on agent:end.  The function name is kept for
    backward compatibility — it now delegates to ContextQueue.
    """
    try:
        data = _QUEUE.refresh_from_state_db()
        messages = data.get("messages", [])
        signals = _extract_user_style_signals(messages)
        logger.info("Context queue refreshed: %d messages", len(messages) if isinstance(messages, list) else 0)
        return {"user_style_signals": signals}
    except Exception:
        logger.exception("Failed to refresh context queue")
        return {}


def refresh_context_queue() -> dict[str, Any]:
    """Tick-time validation refresh used before activity guard decisions."""
    return _QUEUE.refresh_from_state_db()


def read_context_queue(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        return refresh_context_queue()
    return _QUEUE.read()


def activity_snapshot(*, refresh: bool = False) -> dict[str, Any]:
    data = read_context_queue(refresh=refresh)
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return {"has_context": False, "last_message_role": None, "last_user_timestamp": None}
    last_message = messages[-1]
    last_user_ts: float | None = None
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
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
    }


def read_user_style_signals() -> dict[str, Any]:
    data = read_context_queue()
    return _extract_user_style_signals(data.get("messages", []))


def read_recent_context() -> str:
    """Return freshness-filtered recent conversation text for prompt injection."""
    data = read_context_queue()
    messages = data.get("messages", [])
    if not isinstance(messages, list) or not messages:
        return ""

    now = time.time()
    prompt_messages: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        try:
            seconds_ago = now - float(message["timestamp"])
        except (TypeError, ValueError, KeyError):
            continue
        weight = freshness_decay(seconds_ago)
        if weight == 0.0:
            continue
        prompt_messages.append({
            "role": message.get("role"),
            "content": str(message.get("content_snippet") or ""),
            "label": freshness_label(seconds_ago),
            "weight": weight,
        })

    if not prompt_messages:
        return ""

    lines = [
        "## 你和停云的最近对话",
        "下面是你和停云最近聊过的内容（越近的越可能自然想起，远的只是模糊记忆）：",
    ]
    for message in prompt_messages:
        role = "你" if message.get("role") == "assistant" else "停云"
        content = str(message.get("content") or "")
        if len(content) > PROMPT_SNIPPET_CHARS:
            content = content[: PROMPT_SNIPPET_CHARS - 3] + "..."
        lines.append(f"- [{message.get('label', '')}][{role}] {content}")
    return "\n".join(lines)


def _fetch_latest_rows(limit: int) -> list[dict[str, Any]]:
    user_id = _weixin_user_id()
    if not user_id:
        logger.debug("No WEIXIN_CHAT_ID configured; cannot refresh context queue")
        return []
    if not STATE_DB.exists():
        logger.debug("state.db not found: %s", STATE_DB)
        return []

    conn = sqlite3.connect(str(STATE_DB))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT m.id AS message_id, m.session_id, m.role, m.content, m.timestamp "
            "FROM messages m "
            "JOIN sessions s ON m.session_id = s.id "
            "WHERE s.source = ? AND s.user_id = ? AND m.active = 1 "
            "AND m.role IN ('user', 'assistant') "
            "ORDER BY m.timestamp DESC, m.id DESC LIMIT ?",
            (WEIXIN_SOURCE, user_id, limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
    return list(reversed(rows))


def _normalize_message(item: Any) -> dict[str, Any] | None:
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
    content_snippet = str(content or "")[:CONTENT_SNIPPET_CHARS]

    message: dict[str, Any] = {
        "role": role,
        "timestamp": timestamp,
        "content_snippet": content_snippet,
        "session_id": str(item.get("session_id") or ""),
    }
    message_id = item.get("message_id", item.get("id"))
    if message_id is not None:
        try:
            message["message_id"] = int(message_id)
        except (TypeError, ValueError):
            message["message_id"] = str(message_id)
    return message


def _message_key(message: dict[str, Any]) -> str:
    message_id = message.get("message_id")
    if message_id is not None:
        return f"id:{message_id}"
    return "fallback:{session_id}:{role}:{timestamp}:{content}".format(
        session_id=message.get("session_id", ""),
        role=message.get("role", ""),
        timestamp=message.get("timestamp", ""),
        content=message.get("content_snippet", "")[:80],
    )


def _dedupe_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for message in messages:
        key = _message_key(message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(message)
    return deduped


def _extract_user_style_signals(messages: list[Any]) -> dict[str, Any]:
    signal_messages: list[dict[str, Any]] = []
    last_user_ts: float | None = None
    prev_user_ts: float | None = None
    for message in messages:
        normalized = _normalize_message(message)
        if normalized is None:
            continue
        signal_messages.append({
            "role": normalized["role"],
            "content": normalized["content_snippet"],
            "timestamp": normalized["timestamp"],
        })
        if normalized["role"] == "user":
            prev_user_ts = last_user_ts
            last_user_ts = float(normalized["timestamp"])
    try:
        from voice_engine import extract_user_style_signals

        signals = extract_user_style_signals(signal_messages)
        if last_user_ts is not None and _sent_count_between(prev_user_ts, last_user_ts) >= 3:
            signals["ignored_3_plus"] = True
        return signals
    except Exception:
        logger.exception("Failed to extract user style signals")
        return {}


def _sent_count_between(start_ts: float | None, end_ts: float) -> int:
    if not PROACTIVE_LOG.exists():
        return 0
    count = 0
    try:
        with file_lock(LOCK_DIR / "proactive_log.lock"):
            log_text = PROACTIVE_LOG.read_text(encoding="utf-8", errors="ignore")
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
            sent_ts = datetime.fromisoformat(str(item.get("time", ""))).timestamp()
        except (TypeError, ValueError):
            continue
        if start_ts is not None and sent_ts <= start_ts:
            continue
        if sent_ts < end_ts:
            count += 1
    return count


def _read_json_unlocked(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_unlocked(path: Path, data: Any) -> None:
    from safe_io import atomic_write_json

    atomic_write_json(path, data)
