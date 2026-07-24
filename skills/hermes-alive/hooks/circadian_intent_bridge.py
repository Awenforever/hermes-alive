"""Deterministic user-intent bridge for the Hermes Alive Circadian Engine.

This module reads the latest *user* message from the local context queue,
recognises a small explicit sleep/wake intent vocabulary, and applies only
shadow-state events. It never sends messages and never changes watcher policy.

Markers:
- HERMES_ALIVE_CIRCADIAN_INTENT_BRIDGE_SHADOW_V1
- HERMES_ALIVE_CIRCADIAN_INTENT_DEDUP_V1
- HERMES_ALIVE_CIRCADIAN_INTENT_PRIVACY_V1
"""

from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from circadian_engine import CircadianEngine, load_circadian_config
from safe_io import append_jsonl, locked_read_json, locked_write_json

SCHEMA_VERSION = 1
DEFAULT_SHARED_DIR = "/opt/data/hermes_alive_shared"
DEFAULT_MAX_MESSAGE_AGE_SECONDS = 2 * 60 * 60
BRIDGE_STATE_NAME = "circadian_intent_bridge_state.json"
BRIDGE_LOG_NAME = "circadian_intent_shadow.jsonl"
BRIDGE_LOCK_NAME = "circadian_intent_bridge_state.lock"


@dataclass(frozen=True)
class IntentMatch:
    intent: str
    engine_event: str | None
    confidence: float
    rule_id: str
    actionable: bool
    delay_minutes: int | None = None
    target: str = "hermes"

    def public(self) -> dict[str, Any]:
        return asdict(self)


_NO_MATCH = IntentMatch(
    intent="none",
    engine_event=None,
    confidence=0.0,
    rule_id="no_match",
    actionable=False,
    target="none",
)

_SLEEP_QUERY_RE = re.compile(
    r"^(?:你)?(?:睡了没|睡了吗|睡着了吗|睡着没|在睡吗|还醒着吗|还没睡吗)[啊呀呢嘛么？?]*$"
)
_WAKE_QUERY_RE = re.compile(
    r"^(?:你)?(?:醒了吗|醒了没|醒着吗|起了吗|起来了吗)[啊呀呢嘛么？?]*$"
)
_WAKE_ACTION_RE = re.compile(
    r"^(?:喂[,， ]*)?(?:醒醒|快醒醒|起床了|该起床了|起来啦|起来了|别睡了|不许睡了|醒过来)[啊呀呢嘛么！!。]*$"
)
_DELAY_RE = re.compile(
    r"(?:先别睡|别睡(?:了)?|不许睡(?:了)?|晚点(?:再)?睡|等我(?:一会儿?|一下|会儿?)再睡|"
    r"再陪我(?:(?:\d+(?:\.\d+)?)(?:小时|钟头|分钟|分)|半个?小时|一会儿?|一下|会儿?|聊(?:一会儿?|一下|会儿?)?)|"
    r"陪我(?:聊(?:一会儿?|一下|会儿?)?|熬夜)|你(?:今天|今晚)?陪我熬夜|今天别睡|今晚别睡)"
)
_GO_SLEEP_RE = re.compile(
    r"^(?:你)?(?:先)?(?:去睡吧|睡觉吧|睡吧|早点睡|快去睡|该睡了|休息吧|先休息吧|先睡吧|去休息吧|"
    r"可以睡了|该休息了)[啊呀呢嘛么～~！!。]*$"
)
_GOODNIGHT_RE = re.compile(r"^(?:晚安|晚安啦|晚安呀|晚安咯|晚安哦|晚安喽)[～~！!。]*$")
_USER_SLEEP_RE = re.compile(
    r"^(?:我|本人)(?:要|准备|先|去|该)?(?:睡了|睡觉了|休息了|去睡了|去睡觉了|先睡了)[啊呀呢嘛么～~！!。]*$"
)
_USER_BUSY_RE = re.compile(
    r"^(?:我)?(?:还在忙|在忙|先忙|继续忙|忙着呢|正忙着|还要忙一会儿?)[啊呀呢嘛么～~！!。]*$"
)
_USER_LATE_RE = re.compile(
    r"^(?:我)?(?:今天|今晚|今夜)?(?:要|准备|打算|可能)?熬夜[啊呀呢嘛么～~！!。]*$"
)
_CODE_CONTEXT_RE = re.compile(
    r"(?:函数|变量|字段|配置|源码|代码|测试|报错|异常|日志|命令|脚本|regex|pattern|event|intent|sleep_now|wake_up)"
)
_DURATION_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>小时|钟头|分钟|分)")


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text or ""))
    value = value.replace("\u200b", "").strip().lower()
    value = re.sub(r"\s+", "", value)
    value = value.replace("？", "?").replace("！", "!")
    return value[:1000]


def _duration_minutes(text: str) -> int | None:
    if "半小时" in text or "半个小时" in text:
        return 30
    match = _DURATION_RE.search(text)
    if not match:
        if re.search(r"一会儿?|一下|会儿", text):
            return 30
        return None
    value = float(match.group("num"))
    unit = match.group("unit")
    minutes = int(round(value * 60)) if unit in {"小时", "钟头"} else int(round(value))
    return max(1, min(minutes, 300))


def recognize_circadian_intent(text: str) -> IntentMatch:
    """Recognise explicit user-facing circadian intent without an LLM.

    The recogniser intentionally prefers false negatives over false positives.
    Statements about the user's own sleep or work are observations, not commands
    to mutate Hermes' circadian state.
    """

    normalized = _normalize(text)
    if not normalized or len(normalized) > 240:
        return _NO_MATCH
    if _CODE_CONTEXT_RE.search(normalized):
        return _NO_MATCH

    if _SLEEP_QUERY_RE.fullmatch(normalized):
        return IntentMatch("sleep_status_query", None, 0.98, "sleep_status_query_v1", False)
    if _WAKE_QUERY_RE.fullmatch(normalized):
        return IntentMatch("wake_status_query", None, 0.98, "wake_status_query_v1", False)
    if _WAKE_ACTION_RE.fullmatch(normalized):
        return IntentMatch("wake", "wake", 0.99, "explicit_wake_v1", True)
    if _DELAY_RE.search(normalized):
        return IntentMatch(
            "delay_sleep",
            "stay_with_me",
            0.98,
            "explicit_delay_sleep_v1",
            True,
            delay_minutes=_duration_minutes(normalized) or 30,
        )
    if _USER_SLEEP_RE.fullmatch(normalized):
        return IntentMatch("user_sleeping", None, 0.99, "user_sleep_observation_v1", False, target="user")
    if _USER_BUSY_RE.fullmatch(normalized):
        return IntentMatch("user_busy", None, 0.97, "user_busy_observation_v1", False, target="user")
    if _USER_LATE_RE.fullmatch(normalized):
        return IntentMatch("user_late_night", None, 0.96, "user_late_observation_v1", False, target="user")
    if _GOODNIGHT_RE.fullmatch(normalized):
        return IntentMatch("goodnight", "goodnight", 0.97, "standalone_goodnight_v1", True)
    if _GO_SLEEP_RE.fullmatch(normalized):
        return IntentMatch("go_sleep", "go_sleep", 0.99, "explicit_go_sleep_v1", True)
    return _NO_MATCH


def _message_key(message: dict[str, Any]) -> str:
    message_id = message.get("message_id", message.get("id"))
    if message_id is not None and str(message_id).strip():
        source = f"message_id:{message_id}"
    else:
        source = "|".join(
            [
                str(message.get("session_id") or ""),
                str(message.get("timestamp") or ""),
                str(message.get("content_snippet") or message.get("content") or ""),
            ]
        )
    return hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest()


def _latest_user(messages: Any) -> dict[str, Any] | None:
    if not isinstance(messages, list):
        return None
    for item in reversed(messages):
        if isinstance(item, dict) and item.get("role") == "user":
            return item
    return None


def _timestamp(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CircadianIntentBridge:
    """Apply fresh, de-duplicated, explicit intents to shadow circadian state."""

    def __init__(
        self,
        *,
        shared_dir: Path | None = None,
        state_path: Path | None = None,
        log_path: Path | None = None,
        engine_factory: Callable[[], CircadianEngine] | None = None,
        now_fn: Callable[[], float] | None = None,
        max_message_age_seconds: int = DEFAULT_MAX_MESSAGE_AGE_SECONDS,
    ) -> None:
        import os

        root = shared_dir or Path(os.getenv("HERMES_ALIVE_SHARED_DIR", DEFAULT_SHARED_DIR))
        self.state_path = state_path or root / BRIDGE_STATE_NAME
        self.log_path = log_path or root / BRIDGE_LOG_NAME
        self.engine_factory = engine_factory or self._default_engine
        self.now_fn = now_fn or time.time
        self.max_message_age_seconds = max(60, int(max_message_age_seconds))

    @staticmethod
    def _default_engine() -> CircadianEngine:
        return CircadianEngine(config=load_circadian_config())

    def _read_state(self) -> dict[str, Any]:
        data = locked_read_json(self.state_path, {}, BRIDGE_LOCK_NAME)
        return data if isinstance(data, dict) else {}

    def _write_state(self, data: dict[str, Any]) -> None:
        locked_write_json(self.state_path, data, BRIDGE_LOCK_NAME)

    def process_queue(self, queue_data: dict[str, Any] | None) -> dict[str, Any]:
        base: dict[str, Any] = {
            "bridge": "circadian_intent",
            "schema_version": SCHEMA_VERSION,
            "integration_mode": "shadow_state_only",
            "delivery_enforced": False,
            "watcher_behavior_changed": False,
            "message_sent": False,
            "raw_message_stored": False,
        }
        latest = _latest_user((queue_data or {}).get("messages"))
        if latest is None:
            return {**base, "processed": False, "reason": "no_user_message"}

        key = _message_key(latest)
        previous = self._read_state()
        if previous.get("last_processed_message_key") == key:
            return {
                **base,
                "processed": False,
                "duplicate": True,
                "reason": "already_processed",
                "message_key": key,
            }

        message_ts = _timestamp(latest.get("timestamp"))
        now_ts = float(self.now_fn())
        age = None if message_ts is None else max(0.0, now_ts - message_ts)
        text = str(latest.get("content_snippet") or latest.get("content") or "")
        match = recognize_circadian_intent(text)

        result: dict[str, Any] = {
            **base,
            "processed": True,
            "duplicate": False,
            "message_key": key,
            "message_age_seconds": None if age is None else int(age),
            "intent": match.intent,
            "rule_id": match.rule_id,
            "confidence": match.confidence,
            "actionable": match.actionable,
            "target": match.target,
            "engine_event": match.engine_event,
            "delay_minutes": match.delay_minutes,
            "state_event_applied": False,
            "reason": "recognised" if match.intent != "none" else "no_match",
        }

        if message_ts is None or age is None:
            result.update(actionable=False, reason="invalid_message_timestamp")
        elif age > self.max_message_age_seconds:
            result.update(actionable=False, reason="stale_message")
        elif match.actionable and match.engine_event:
            engine = self.engine_factory()
            cfg = engine.config
            if not cfg.enabled:
                result["reason"] = "circadian_disabled"
            elif cfg.mode != "shadow":
                # This phase must never become a live enforcement path merely
                # because an external config accidentally says "live".
                result["reason"] = "shadow_mode_required"
            else:
                at = datetime.fromtimestamp(message_ts, tz=engine.tz)
                state = engine.apply_event(
                    match.engine_event,
                    at=at,
                    delay_minutes=match.delay_minutes,
                )
                result.update(
                    state_event_applied=True,
                    reason="shadow_state_event_applied",
                    resulting_phase=state.get("phase"),
                    planned_sleep_at=state.get("planned_sleep_at"),
                    planned_wake_at=state.get("planned_wake_at"),
                    sleep_debt_minutes=int(state.get("sleep_debt_minutes") or 0),
                )

        ledger = {
            "schema_version": SCHEMA_VERSION,
            "last_processed_message_key": key,
            "last_processed_at": datetime.fromtimestamp(now_ts).astimezone().isoformat(),
            "last_message_timestamp": message_ts,
            "last_intent": result.get("intent"),
            "last_rule_id": result.get("rule_id"),
            "last_state_event_applied": bool(result.get("state_event_applied")),
            "last_reason": result.get("reason"),
            "raw_message_stored": False,
        }
        self._write_state(ledger)
        append_jsonl(self.log_path, result, "circadian_intent_shadow.lock")
        return result


def process_latest_user_intent_shadow() -> dict[str, Any]:
    """Refresh-free handler entry point used immediately after context capture."""

    try:
        from context_tracker import read_context_queue

        queue = read_context_queue(refresh=False)
        return CircadianIntentBridge().process_queue(queue)
    except Exception as exc:
        return {
            "bridge": "circadian_intent",
            "schema_version": SCHEMA_VERSION,
            "integration_mode": "shadow_state_only",
            "delivery_enforced": False,
            "watcher_behavior_changed": False,
            "message_sent": False,
            "processed": False,
            "reason": "bridge_error",
            "error_type": type(exc).__name__,
            "raw_message_stored": False,
        }
