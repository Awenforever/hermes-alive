# Hermes Alive persistent state engine.
# Marker: ALIVE_STATE_ENGINE_V1
# Marker: HERMES_ALIVE_CONTEXT_FRESHNESS_V2
# Marker: HERMES_ALIVE_SENT_EVENT_WINDOW_FIX_V2
# Marker: HERMES_ALIVE_INTERACTION_EVIDENCE_V1
# Marker: HERMES_ALIVE_ORDINARY_INBOUND_NOT_DIRECT_RESET_V1
# Marker: HERMES_ALIVE_CONTINUE_CONTEXT_EXCLUSION_V1

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from safe_io import locked_read_json, locked_write_json

CST = timezone(timedelta(hours=8))
BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
STATE_DIR = BASE / "state"
STATE_PATH = STATE_DIR / "alive_state.json"
CONTEXT_QUEUE = BASE / "context_queue.json"
PROACTIVE_LOG = BASE / "proactive_log.jsonl"
VOICE_STATE = BASE / "voice_state.json"

LOCK_NAME = "alive_state.lock"
MAX_RECENT = 12

DEBUG_RE = re.compile(
    r"(tar\.gz|SUMMARY|OVERALL_RESULT|docker|compose|bash|sudo|ssh|日志|审计|回传包|"
    r"NAS|Hermes|iStoreOS|旁路|代理|nft|iptables|systemd|rollback|回滚|APPLY|Codex)",
    re.I,
)
RESEARCH_RE = re.compile(
    r"(论文|实验|科研|遥感|火灾|烟雾|甲烷|燃烧|弱浮力|微重力|落塔|模型|数据|JSTARS|PPT|图表|审稿|参考文献)",
    re.I,
)
CASUAL_RE = re.compile(r"(哈哈|笑死|人呢|在干嘛|困|累|晚安|早|好玩|离谱|无语|想你|发呆)", re.I)
NEWS_RE = re.compile(r"(新闻|看到|链接|论文|专利|项目|工具|repo|GitHub|图片|模拟器|发布|开源)", re.I)
POKE_RE = re.compile(r"(人呢|在干嘛|还活着|去哪了|回来)", re.I)
SULK_RE = re.compile(r"(呵|不理|已读|又消失|算了|冷漠)", re.I)
CARE_RE = re.compile(r"(睡|熬夜|喝水|吃饭|休息|别硬扛|别死磕)", re.I)
DEBUG_COMPANION_RE = re.compile(r"(日志|审包|tar\.gz|docker|脚本|回传包|不插嘴|拆炸弹|生产)", re.I)


def now_iso() -> str:
    return datetime.now(CST).isoformat()


def _empty_state() -> dict[str, Any]:
    ts = now_iso()
    return {
        "schema_version": 2,
        "last_updated_at": ts,
        "last_user_reply_at": None,
        "last_proactive_at": None,
        "ignored_proactive_count": 0,
        "interaction_evidence": {
            "unanswered_pressure": 0.0,
            "presence_signal": 0.0,
            "engagement_signal": 0.5,
            "last_inbound_kind": "none",
            "last_inbound_at": None,
            "last_reply_quality": 0.0,
            "observed_proactive_count_since_inbound": 0,
        },
        "recent_openers": [],
        "recent_speech_acts": [],
        "mood": {
            "energy": 50,
            "boredom": 20,
            "annoyance": 0,
            "affection": 65,
            "curiosity": 50,
            "pressure": 0,
        },
        "current_context": {
            "flow": "idle",
            "focus_lock": False,
        },
        "derived": {
            "debug_signal_count": 0,
            "research_signal_count": 0,
            "casual_signal_count": 0,
            "source": "alive_state_engine_v1",
        },
    }


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Some context queues store epoch seconds.
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        pass
    try:
        # Support ISO strings with Z or offset.
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _iso_from_ts(ts: float | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, CST).isoformat()
    except Exception:
        return None


def _read_context_queue() -> dict[str, Any]:
    return locked_read_json(CONTEXT_QUEUE, {}, "context_queue.lock")


def _context_messages() -> list[dict[str, Any]]:
    data = _read_context_queue()
    messages = data.get("messages")
    return messages if isinstance(messages, list) else []


def _read_proactive_records(limit: int = 80) -> list[dict[str, Any]]:
    """Return the latest sent events rather than the latest raw log lines."""
    if not PROACTIVE_LOG.exists():
        return []
    records: list[dict[str, Any]] = []
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
        if not isinstance(item, dict):
            continue
        if (
            item.get("decision") == "sent"
            and str(item.get("msg_type") or "") != "test"
        ):
            records.append(item)
            if len(records) >= limit:
                break
    records.reverse()
    return records


def _message_content(message: dict[str, Any]) -> str:
    return str(
        message.get("content_snippet")
        or message.get("content")
        or message.get("text")
        or ""
    ).strip()


def _is_control_message(text: str) -> bool:
    return str(text or "").strip().startswith("/")


def _latest_real_user_message(
    messages: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, float | None, str]:
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = _message_content(msg)
        if not content or _is_control_message(content):
            continue
        ts = _parse_ts(
            msg.get("timestamp")
            or msg.get("time")
            or msg.get("created_at")
        )
        if ts is not None:
            return msg, ts, content
    return None, None, ""


def _last_user_ts(messages: list[dict[str, Any]]) -> float | None:
    _, timestamp, _ = _latest_real_user_message(messages)
    return timestamp


def _last_proactive_ts(records: list[dict[str, Any]]) -> float | None:
    for rec in reversed(records):
        ts = _parse_ts(rec.get("time") or rec.get("timestamp") or rec.get("created_at"))
        if ts is not None:
            return ts
    return None


def _sent_after(records: list[dict[str, Any]], ts: float | None) -> list[dict[str, Any]]:
    if ts is None:
        return []
    out: list[dict[str, Any]] = []
    for rec in records:
        rts = _parse_ts(rec.get("time") or rec.get("timestamp") or rec.get("created_at"))
        if rts is not None and rts > ts:
            out.append(rec)
    return out


def _message_texts(messages: list[dict[str, Any]], limit: int = 12) -> list[str]:
    texts: list[str] = []
    for msg in messages[-limit:]:
        if not isinstance(msg, dict):
            continue
        text = str(
            msg.get("content_snippet")
            or msg.get("content")
            or msg.get("text")
            or ""
        ).strip()
        if text:
            texts.append(text)
    return texts


def _latest_user_episode(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float | None]:
    latest_index: int | None = None
    latest_ts: float | None = None
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        latest_index = index
        latest_ts = _parse_ts(
            message.get("timestamp")
            or message.get("time")
            or message.get("created_at")
        )
        break
    if latest_index is None:
        return [], None
    return messages[latest_index:], latest_ts


def _flow_max_age_seconds() -> int:
    try:
        value = int(
            os.getenv(
                "HERMES_ALIVE_CONTEXT_FLOW_MAX_AGE_SECONDS",
                "3600",
            )
        )
    except Exception:
        value = 3600
    return max(60, min(86400, value))


def _classify_flow(
    messages: list[dict[str, Any]],
) -> tuple[str, bool, dict[str, Any]]:
    episode, latest_user_ts = _latest_user_episode(messages)
    now_ts = time.time()
    age_seconds = (
        None
        if latest_user_ts is None
        else max(0.0, now_ts - latest_user_ts)
    )
    context_fresh = bool(
        latest_user_ts is not None
        and age_seconds is not None
        and age_seconds <= _flow_max_age_seconds()
    )

    texts = _message_texts(episode if context_fresh else [], 12)
    blob = "\n".join(texts)
    debug_count = len(DEBUG_RE.findall(blob))
    research_count = len(RESEARCH_RE.findall(blob))
    casual_count = len(CASUAL_RE.findall(blob))

    signals: dict[str, Any] = {
        "debug": debug_count,
        "research": research_count,
        "casual": casual_count,
        "context_fresh": context_fresh,
        "evidence_age_seconds": (
            None if age_seconds is None else int(age_seconds)
        ),
        "evidence_observed_at": _iso_from_ts(latest_user_ts),
    }

    hour = datetime.now(CST).hour
    if debug_count >= 3:
        return "debug_flow", True, signals
    if research_count >= 2:
        return "research_flow", False, signals
    if hour in (0, 1, 2, 3, 4, 5):
        return "night_mode", False, signals
    if casual_count >= 2:
        return "casual_flow", False, signals
    return "idle", False, signals


def _opener(text: str) -> str:
    s = re.sub(r"\s+", "", text.strip())
    if not s:
        return ""
    for p in ["刚看到", "刚醒", "看到个新闻", "看到个论文", "人呢", "呵", "算了", "晚上好", "早"]:
        if s.startswith(p):
            return p
    if len(s) <= 8:
        return s
    return s[:6]


def _speech_act(text: str) -> str:
    s = text.strip()
    if not s:
        return "silent_marker"
    if POKE_RE.search(s):
        return "poke"
    if SULK_RE.search(s):
        return "sulk"
    if DEBUG_COMPANION_RE.search(s):
        return "debug_companion"
    if CARE_RE.search(s):
        return "care"
    if RESEARCH_RE.search(s):
        return "research_ping"
    if NEWS_RE.search(s):
        return "news_reaction"
    if len(s) > 130:
        return "long_rambling"
    if re.search(r"(突然想到|我突然|发呆|有点空|想起)", s):
        return "self_talk"
    return "self_talk"


def _recent_openers(records: list[dict[str, Any]]) -> list[str]:
    vals: list[str] = []
    for rec in records[-MAX_RECENT:]:
        text = str(rec.get("message_preview") or rec.get("content") or rec.get("text") or "").strip()
        op = _opener(text)
        if op:
            vals.append(op)
    return vals[-MAX_RECENT:]


def _recent_speech_acts(records: list[dict[str, Any]]) -> list[str]:
    vals: list[str] = []
    for rec in records[-MAX_RECENT:]:
        text = str(rec.get("message_preview") or rec.get("content") or rec.get("text") or "").strip()
        vals.append(_speech_act(text))
    return vals[-MAX_RECENT:]



def _reply_quality(text: str) -> float:
    value = str(text or "").strip()
    if not value:
        return 0.0
    length = len(value)
    quality = 0.18
    if length >= 4:
        quality += 0.10
    if length >= 12:
        quality += 0.16
    if length >= 40:
        quality += 0.14
    if re.search(r"[?？]|为什么|怎么|如何|你觉得|我觉得|可以|继续|帮我", value):
        quality += 0.18
    if re.search(r"^(嗯|哦|行|好|知道了|收到)[。.!！]?$", value):
        quality = min(quality, 0.24)
    return max(0.0, min(1.0, quality))


def _elapsed_seconds(prev: dict[str, Any]) -> float:
    previous = _parse_ts(prev.get("last_updated_at"))
    if previous is None:
        return 0.0
    return max(0.0, time.time() - previous)


def _derive_interaction_evidence(
    *,
    prev: dict[str, Any],
    raw_ignored: int,
    last_user_ts: float | None,
    last_user_text: str,
) -> dict[str, Any]:
    previous = prev.get("interaction_evidence")
    if not isinstance(previous, dict):
        previous = {}

    try:
        fallback = min(
            1.0,
            int(prev.get("ignored_proactive_count") or 0) / 4.0,
        )
        pressure = max(
            0.0,
            min(
                1.0,
                float(previous.get("unanswered_pressure", fallback)),
            ),
        )
    except Exception:
        pressure = 0.0

    elapsed = _elapsed_seconds(prev)
    if elapsed > 0:
        pressure *= 0.5 ** (elapsed / (18.0 * 3600.0))

    try:
        observed = max(
            0,
            int(
                previous.get(
                    "observed_proactive_count_since_inbound",
                    0,
                )
            ),
        )
    except Exception:
        observed = 0

    previous_inbound_ts = _parse_ts(previous.get("last_inbound_at"))
    new_inbound = bool(
        last_user_ts is not None
        and (
            previous_inbound_ts is None
            or last_user_ts > previous_inbound_ts
        )
    )

    reply_quality = 0.0
    if new_inbound:
        reply_quality = _reply_quality(last_user_text)
        pressure *= max(0.30, 0.92 - 0.55 * reply_quality)
        observed = 0

    new_unanswered_events = max(0, raw_ignored - observed)
    if new_unanswered_events:
        pressure = min(
            1.0,
            pressure
            + 0.17 * new_unanswered_events
            + 0.025 * max(0, new_unanswered_events - 1),
        )

    try:
        old_presence = float(previous.get("presence_signal", 0.0))
    except Exception:
        old_presence = 0.0
    try:
        old_engagement = float(previous.get("engagement_signal", 0.5))
    except Exception:
        old_engagement = 0.5

    presence = (
        1.0
        if new_inbound
        else max(0.0, min(1.0, old_presence * 0.96))
    )
    engagement = (
        reply_quality
        if new_inbound
        else max(0.0, min(1.0, old_engagement * 0.985))
    )

    return {
        "unanswered_pressure": round(
            max(0.0, min(1.0, pressure)),
            4,
        ),
        "presence_signal": round(presence, 4),
        "engagement_signal": round(engagement, 4),
        "last_inbound_kind": (
            "ordinary_user_message"
            if new_inbound
            else str(previous.get("last_inbound_kind") or "none")
        ),
        "last_inbound_at": (
            _iso_from_ts(last_user_ts)
            if new_inbound
            else previous.get("last_inbound_at")
        ),
        "last_reply_quality": round(
            reply_quality
            if new_inbound
            else float(
                previous.get("last_reply_quality", 0.0)
                or 0.0
            ),
            4,
        ),
        "observed_proactive_count_since_inbound": int(raw_ignored),
        "new_inbound_evidence": bool(new_inbound),
        "direct_reset_applied": False,
    }

def _derive_mood(
    *,
    prev: dict[str, Any],
    ignored: int,
    unanswered_pressure: float,
    reply_quality: float,
    flow: str,
    focus_lock: bool,
    user_replied_after_ignored: bool,
) -> dict[str, int]:
    mood = dict(_empty_state()["mood"])
    prev_mood = prev.get("mood") if isinstance(prev.get("mood"), dict) else {}
    for key in mood:
        try:
            mood[key] = _clamp(float(prev_mood.get(key, mood[key])))
        except Exception:
            pass

    # Natural drift toward baseline.
    baseline = _empty_state()["mood"]
    for key, base in baseline.items():
        mood[key] = _clamp(mood[key] * 0.75 + base * 0.25)

    evidence = max(0.0, min(1.0, float(unanswered_pressure)))
    if evidence > 0:
        mood["annoyance"] = _clamp(
            mood["annoyance"] + 32 * evidence
        )
        mood["boredom"] = _clamp(
            mood["boredom"] + 25 * evidence
        )
        mood["affection"] = _clamp(
            mood["affection"] - 8 * evidence
        )
    if user_replied_after_ignored:
        quality = max(0.0, min(1.0, float(reply_quality)))
        mood["annoyance"] = _clamp(
            mood["annoyance"] - (6 + 18 * quality)
        )
        mood["affection"] = _clamp(
            mood["affection"] + (3 + 9 * quality)
        )
        mood["boredom"] = _clamp(
            mood["boredom"] - (4 + 10 * quality)
        )

    if flow == "debug_flow":
        mood["pressure"] = _clamp(max(mood["pressure"], 76))
        mood["energy"] = _clamp(mood["energy"] - 10)
        mood["curiosity"] = _clamp(mood["curiosity"] - 5)
    elif flow == "research_flow":
        mood["curiosity"] = _clamp(max(mood["curiosity"], 74))
        mood["pressure"] = _clamp(max(mood["pressure"], 35))
    elif flow == "night_mode":
        mood["energy"] = _clamp(min(mood["energy"], 35))
        mood["pressure"] = _clamp(max(mood["pressure"], 45))
    elif flow == "casual_flow":
        mood["affection"] = _clamp(max(mood["affection"], 70))
        mood["boredom"] = _clamp(mood["boredom"] - 8)
    elif flow == "idle":
        mood["boredom"] = _clamp(mood["boredom"] + 6)

    if focus_lock:
        mood["pressure"] = _clamp(max(mood["pressure"], 80))
    return mood


def _user_replied_after_prev_ignored(prev: dict[str, Any], last_user_ts: float | None) -> bool:
    if last_user_ts is None:
        return False
    try:
        prev_ignored = int(prev.get("ignored_proactive_count") or 0)
    except Exception:
        prev_ignored = 0
    prev_last_proactive_ts = _parse_ts(prev.get("last_proactive_at"))
    return bool(prev_ignored > 0 and prev_last_proactive_ts is not None and last_user_ts > prev_last_proactive_ts)


class AliveStateEngine:
    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or STATE_PATH

    def read(self) -> dict[str, Any]:
        data = locked_read_json(self.state_path, {}, LOCK_NAME)
        if not isinstance(data, dict) or not data:
            return _empty_state()
        state = _empty_state()
        state.update(data)
        if not isinstance(state.get("mood"), dict):
            state["mood"] = _empty_state()["mood"]
        if not isinstance(state.get("current_context"), dict):
            state["current_context"] = _empty_state()["current_context"]
        if not isinstance(state.get("interaction_evidence"), dict):
            state["interaction_evidence"] = _empty_state()["interaction_evidence"]
        return state

    def snapshot(self, *, update: bool = True) -> dict[str, Any]:
        prev = self.read()
        messages = _context_messages()
        records = _read_proactive_records()
        _, last_user_ts, last_user_text = _latest_real_user_message(
            messages
        )
        last_proactive_ts = _last_proactive_ts(records)
        ignored_records = _sent_after(records, last_user_ts)
        ignored = len(ignored_records)
        flow, focus_lock, signals = _classify_flow(messages)
        recovered = _user_replied_after_prev_ignored(
            prev,
            last_user_ts,
        )
        interaction_evidence = _derive_interaction_evidence(
            prev=prev,
            raw_ignored=ignored,
            last_user_ts=last_user_ts,
            last_user_text=last_user_text,
        )

        state = _empty_state()
        state["last_updated_at"] = now_iso()
        state["last_user_reply_at"] = _iso_from_ts(last_user_ts)
        state["last_proactive_at"] = _iso_from_ts(last_proactive_ts)
        state["ignored_proactive_count"] = ignored
        state["interaction_evidence"] = interaction_evidence
        state["recent_openers"] = _recent_openers(records)
        state["recent_speech_acts"] = _recent_speech_acts(records)
        state["mood"] = _derive_mood(
            prev=prev,
            ignored=ignored,
            unanswered_pressure=float(
                interaction_evidence.get("unanswered_pressure")
                or 0.0
            ),
            reply_quality=float(
                interaction_evidence.get("last_reply_quality")
                or 0.0
            ),
            flow=flow,
            focus_lock=focus_lock,
            user_replied_after_ignored=recovered,
        )
        state["current_context"] = {
            "flow": flow,
            "focus_lock": bool(focus_lock),
            "context_fresh": bool(signals.get("context_fresh")),
            "evidence_observed_at": signals.get("evidence_observed_at"),
            "evidence_age_seconds": signals.get("evidence_age_seconds"),
        }
        state["derived"] = {
            "debug_signal_count": signals["debug"],
            "research_signal_count": signals["research"],
            "casual_signal_count": signals["casual"],
            "context_fresh": bool(signals.get("context_fresh")),
            "evidence_age_seconds": signals.get("evidence_age_seconds"),
            "user_replied_after_ignored": recovered,
            "ordinary_inbound_direct_reset": False,
            "unanswered_pressure": interaction_evidence.get(
                "unanswered_pressure"
            ),
            "reply_quality": interaction_evidence.get(
                "last_reply_quality"
            ),
            "source": "alive_state_engine_v3",
        }

        if update:
            self.write(state)
        return state

    def write(self, state: dict[str, Any]) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        locked_write_json(self.state_path, state, LOCK_NAME)

    def prompt_directives(self, *, update: bool = True) -> str:
        state = self.snapshot(update=update)
        mood = state.get("mood", {})
        ctx = state.get("current_context", {})
        ignored = int(state.get("ignored_proactive_count") or 0)
        evidence = (
            state.get("interaction_evidence")
            if isinstance(state.get("interaction_evidence"), dict)
            else {}
        )
        unanswered_pressure = float(
            evidence.get("unanswered_pressure") or 0.0
        )
        reply_quality = float(
            evidence.get("last_reply_quality") or 0.0
        )
        acts = state.get("recent_speech_acts") or []
        openers = state.get("recent_openers") or []
        flow = str(ctx.get("flow") or "idle")
        focus_lock = bool(ctx.get("focus_lock"))

        lines = [
            "## Alive 状态 V1",
            f"- 当前场景：{flow}",
            f"- focus_lock：{'true' if focus_lock else 'false'}",
            f"- ignored_proactive_count（原始观测）：{ignored}",
            f"- unanswered_pressure（关系证据，不是开关）：{unanswered_pressure:.3f}",
            f"- last_reply_quality：{reply_quality:.3f}",
            "- 普通入站是新证据，不会机械清零关系状态。",
            "- /continue 与其他控制命令不更新关系 context token。",
            "- mood："
            + f" energy={mood.get('energy', 50)}, boredom={mood.get('boredom', 20)}, "
            + f"annoyance={mood.get('annoyance', 0)}, affection={mood.get('affection', 65)}, "
            + f"curiosity={mood.get('curiosity', 50)}, pressure={mood.get('pressure', 0)}",
        ]

        if openers:
            lines.append("- 最近开头：" + " / ".join(str(x) for x in openers[-6:]))
        if acts:
            lines.append("- 最近 speech_act：" + " / ".join(str(x) for x in acts[-6:]))

        if unanswered_pressure > 0:
            lines.append(
                "- 存在未回应证据。是否说话由人格、情绪、关系温度、"
                "时间与新话题价值共同决定，禁止使用固定次数开关。"
            )
        if ignored >= 1:
            lines.append(
                "- 旧主动话题不得追问或施压。若开启新话题，必须有独立价值。"
            )
        elif flow == "debug_flow":
            lines.append(
                "- 当前 debug/运维证据仍新鲜，只允许一次简短陪跑；"
                "不得把该状态延续到无人回应后的下一轮。"
            )
        elif flow == "research_flow":
            lines.append("- 当前更适合 research_ping 或简短科研联想，不要泛泛闲聊。")
        elif flow == "night_mode":
            lines.append("- 当前偏深夜状态，语气可以困一点、轻一点，不要高强度打扰。")
        elif flow == "idle":
            lines.append("- 当前偏 idle，可以主动一点，但要避免模板化。")

        return "\n".join(lines)


def read_alive_state(update: bool = False) -> dict[str, Any]:
    return AliveStateEngine().snapshot(update=update)
