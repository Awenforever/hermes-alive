# Hermes Alive v1.2 style guard.
# Marker: STYLE_GUARD_CONTENT_CONTEXT_V1
# Marker: EMOJI_CONTEXTUAL_POLICY_V2
#
# V1.2 extends v1.1:
# - Keep opener de-duplication, casual punctuation, and contextual emoji.
# - Prevent content-sharing messages from being empty reactions.
# - If a vague discovery/news reaction is generated, append detail/link bubbles
#   from discovery_context when available.
#
# It does not send messages, does not call network APIs, and only reads shared state.

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from alive_state import AliveStateEngine
except Exception:
    AliveStateEngine = None  # type: ignore[assignment]


BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
PROACTIVE_LOG = BASE / "proactive_log.jsonl"
CONTEXT_QUEUE = BASE / "context_queue.json"
VOICE_STATE = BASE / "voice_state.json"

EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]")
DEBUG_RE = re.compile(
    r"(tar\.gz|SUMMARY|OVERALL_RESULT|docker|compose|bash|sudo|ssh|日志|审计|回传包|"
    r"NAS|Hermes|iStoreOS|UGLINK|旁路|代理|nft|iptables|systemd|rollback|回滚|APPLY|Codex)",
    re.I,
)
JUST_PREFIX_RE = re.compile(r"^\s*刚")
SHARE_RE = re.compile(r"(看到|新闻|论文|专利|项目|工具|repo|GitHub|链接|图片|模拟器|被夸|发布|开源)", re.I)
VAGUE_RE = re.compile(r"(有点离谱|挺离谱|离谱|挺酷|有点酷|感觉挺酷|有意思|心动|好怪|怪的|想吐槽|笑死)", re.I)
DETAIL_RE = re.compile(r"(离谱的是|有意思的是|重点是|妙在|怪在|夸张的是|因为|不是.+而是|链接：|https?://|为什么)", re.I)


class StyleGuard:
    def prompt_directives(self, voice: Any | None = None, context: dict[str, Any] | None = None, discovery_context: dict[str, Any] | None = None) -> str:
        del context
        recent = _recent_sent_messages(12)
        sent_since_user = _sent_since_last_user_count()
        just_count = sum(1 for m in recent if JUST_PREFIX_RE.search(m))
        emoji_count = sum(1 for m in recent if EMOJI_RE.search(m))
        debug_flow = _debug_flow()
        recent_preview = "\n".join(f"- {m[:80]}" for m in recent[-6:])
        discovery_hint = _discovery_hint(discovery_context)

        emoji_usage = _float_attr(voice, "emoji_usage", _voice_state_value("emoji_usage", 0.3))
        verbosity = _float_attr(voice, "verbosity", _voice_state_value("verbosity", 0.5))

        lines = [
            "## 本次主动搭话风格约束 V1.2",
            "这部分比上面的普通倾向更具体，必须优先遵守。",
            "",
            "【反重复】",
            "- 不要像模板。最近已经很容易出现“刚……”开头，本次优先避免以“刚”开头。",
            "- 不要连续复用同一个具体话题、新闻、论文、专利或同一种句式。",
            "",
            "【内容型分享】",
            "- 如果你提新闻/论文/专利/项目/工具/repo/图片/链接，不能只说“有点离谱/挺酷/有点意思”。",
            "- 必须讲清楚离谱、有趣或值得看的点。至少包含：它是什么 + 为什么值得提。",
            "- 内容型分享可以拆成 2-3 条微信气泡，用 --- 分隔。第一条像真人吐槽，第二条补清楚原因，第三条可选链接。",
            "- 如果没有足够细节，就别分享这个内容，换成轻戳/自言自语/沉默感。",
            "",
            "【标点】",
            "- 像微信聊天，不像文章。不要每句话都补全句号。",
            "- 短句可以没有结尾标点。可以用省略号、换行、括号动作，但不要堆。",
            "",
            "【emoji】",
            "- emoji 可以自然使用；根据语境决定是否使用，避免连续堆叠或喧宾夺主。",
            "- debug、生产操作、审计或严肃场景通常可以少用或不用，但不做硬禁止。",
            "",
            "【情绪和关系】",
            "- 如果你发过主动消息但停云没回，可以有一点小情绪：轻戳、冷淡、阴阳一句、装作无所谓。",
            "- 可以说：人呢、呵、又消失、在干嘛、已读不回是吧。不要攻击，不要长篇控诉。",
            "",
        ]

        alive_state_hint = _alive_state_directives()
        if alive_state_hint:
            lines.extend([
                "【Alive 状态】",
                alive_state_hint,
                "",
            ])

        if discovery_hint:
            lines.extend([
                "【这次可用内容线索】",
                discovery_hint,
                "- 如果用上面的内容，必须讲清楚为什么值得看；有链接就带链接。",
                "",
            ])

        if debug_flow:
            lines.extend([
                "【当前像 debug/运维工作流】",
                "- 不要突然开无关新闻/论文话题。",
                "- 只允许短的 ambient 陪跑、吐槽当前流程、或者一句很轻的在场感。",
                "",
            ])

        if sent_since_user >= 2:
            lines.extend([
                f"【未回应状态】你最近已有 {sent_since_user} 条主动消息没有得到停云回应。",
                "- 本次不要继续像新闻播报。",
                "- 优先选择很短的 poke/sulk：'人呢'、'呵'、'又不理我'、'算了'。",
                "",
            ])

        if just_count >= 3:
            lines.append(f"- 最近 {len(recent)} 条主动消息里有 {just_count} 条以“刚”开头，本次禁止以“刚”开头。")
        if emoji_usage >= 0.25 and emoji_count == 0:
            lines.append("- 最近主动消息没有 emoji；如果语气自然，可以适当使用，不要为了带而带。")
        if verbosity >= 0.65:
            lines.append("- 你可以偶尔多说一点，尤其内容型分享可以拆成多条气泡。")
        else:
            lines.append("- 普通闲聊短一点；内容型分享宁可多一条气泡，也别没头没尾。")

        if recent_preview:
            lines.extend(["", "【最近主动消息，避免重复这些开头和话题】", recent_preview])

        return "\n".join(lines)

    def apply(self, text: str, voice: Any | None = None, context: dict[str, Any] | None = None, discovery_context: dict[str, Any] | None = None) -> str:
        del context
        if not isinstance(text, str):
            return ""
        raw = text.strip()
        if not raw:
            return ""

        parts = _split_burst(raw)
        recent = _recent_sent_messages(12)
        debug_flow = _debug_flow()
        emoji_usage = _float_attr(voice, "emoji_usage", _voice_state_value("emoji_usage", 0.3))
        processed: list[str] = []
        for idx, part in enumerate(parts):
            segment = part.strip()
            if not segment:
                continue
            segment = _dedupe_just_opener(segment, recent)
            segment = _casualize_punctuation(segment)
            segment = _maybe_add_emoji(segment, recent, emoji_usage, debug_flow, idx)
            expanded = _maybe_expand_content_share(segment, discovery_context, debug_flow)
            processed.extend(expanded if expanded else [segment])

        return "\n---\n".join(p for p in processed if p.strip()) if processed else raw


def _split_burst(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n---\n|\n---\r?\n|^---\n|^---\r?\n", text.strip()) if p.strip()]


def _recent_sent_messages(limit: int = 12) -> list[str]:
    if not PROACTIVE_LOG.exists():
        return []
    out: list[str] = []
    try:
        lines = PROACTIVE_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if item.get("decision") != "sent":
            continue
        if str(item.get("msg_type") or "") == "test":
            continue
        preview = str(item.get("message_preview") or "").strip()
        if preview:
            out.append(preview)
    return out[-limit:]


def _context_messages() -> list[dict[str, Any]]:
    if not CONTEXT_QUEUE.exists():
        return []
    try:
        data = json.loads(CONTEXT_QUEUE.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    messages = data.get("messages")
    return messages if isinstance(messages, list) else []


def _sent_since_last_user_count() -> int:
    messages = _context_messages()
    last_user_ts: float | None = None
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            try:
                last_user_ts = float(msg.get("timestamp"))
            except Exception:
                last_user_ts = None
            break
    if last_user_ts is None:
        return 0

    count = 0
    if not PROACTIVE_LOG.exists():
        return 0
    try:
        lines = PROACTIVE_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return 0
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if item.get("decision") != "sent" or str(item.get("msg_type") or "") == "test":
            continue
        try:
            sent_ts = datetime.fromisoformat(str(item.get("time"))).timestamp()
        except Exception:
            continue
        if sent_ts > last_user_ts:
            count += 1
    return count


def _debug_flow() -> bool:
    messages = _context_messages()[-12:]
    if not messages:
        return False
    text = "\n".join(str(m.get("content_snippet") or "") for m in messages if isinstance(m, dict))
    return len(DEBUG_RE.findall(text)) >= 3


def _dedupe_just_opener(text: str, recent: list[str]) -> str:
    recent_just = sum(1 for m in recent if JUST_PREFIX_RE.search(m))
    last_just = bool(recent and JUST_PREFIX_RE.search(recent[-1]))
    if not JUST_PREFIX_RE.search(text):
        return text
    if recent_just < 3 and not last_just:
        return text

    replacements = [
        ("刚看到一个", "看到一个"),
        ("刚看到个", "看到个"),
        ("刚看到", "看到"),
        ("刚醒，", "醒了，"),
        ("刚醒", "醒了"),
        ("刚折腾完", "折腾完"),
        ("刚忙完", "忙完"),
    ]
    for old, new in replacements:
        if text.startswith(old):
            return new + text[len(old):]
    return text[1:].lstrip("，, ") if text.startswith("刚") and len(text) > 1 else text


def _casualize_punctuation(text: str) -> str:
    s = text.strip()
    if not s:
        return s
    s = s.replace("晚上好。刚", "晚上好，刚")
    s = s.replace("早上好。刚", "早上好，刚")
    s = s.replace("。感觉", "，感觉")
    s = s.replace("。有点", "，有点")
    if len(s) <= 90 and s.endswith("。"):
        s = s[:-1]
    if len(s) <= 120 and s.count("。") >= 2:
        s = s.replace("。", "，", 1)
    return s.replace("；", "，").strip()


def _maybe_add_emoji(text: str, recent: list[str], emoji_usage: float, debug_flow: bool, idx: int) -> str:
    if debug_flow or emoji_usage < 0.25 or EMOJI_RE.search(text) or len(text) > 90 or DEBUG_RE.search(text):
        return text
    if sum(1 for m in recent[-8:] if EMOJI_RE.search(m)) >= 1:
        return text
    strong = _strong_emoji(text)
    if strong:
        return f"{text} {strong}"
    return text if _stable_score(text + f"|{idx}") > 0.28 else f"{text} {_fallback_emoji(text)}"


def _strong_emoji(text: str) -> str:
    for pat, emoji in [
        (r"(笑死|哈哈|离谱|绷不住|草)", "😂"),
        (r"(困|睡|熬|累|醒)", "😴"),
        (r"(呵|不理|已读|消失|烦)", "🙄"),
        (r"(安静|发呆|松了|空)", "🫠"),
    ]:
        if re.search(pat, text):
            return emoji
    return ""


def _fallback_emoji(text: str) -> str:
    for pat, emoji in [(r"(怪|神奇|好奇|想到|为什么)", "🤔"), (r"(尴尬|麻了|算了)", "😅")]:
        if re.search(pat, text):
            return emoji
    return "😅"


def _maybe_expand_content_share(text: str, discovery_context: dict[str, Any] | None, debug_flow: bool) -> list[str] | None:
    if debug_flow or "---" in text:
        return None
    if not SHARE_RE.search(text) or not VAGUE_RE.search(text) or DETAIL_RE.search(text):
        return None
    item = _best_discovery_item(discovery_context, text)
    if not item:
        return None
    detail = _detail_bubble(item, text)
    link = _link_bubble(item)
    bubbles = [text]
    if detail:
        bubbles.append(detail)
    if link:
        bubbles.append(link)
    return bubbles if len(bubbles) >= 2 else None


def _best_discovery_item(discovery_context: dict[str, Any] | None, text: str) -> dict[str, Any] | None:
    if not isinstance(discovery_context, dict):
        return None
    candidates: list[dict[str, Any]] = []
    for key in ("external", "items", "news", "papers", "repos"):
        vals = discovery_context.get(key)
        if isinstance(vals, list):
            candidates.extend([v for v in vals if isinstance(v, dict)])
    if not candidates:
        return None

    def score(item: dict[str, Any]) -> int:
        blob = " ".join(str(item.get(k, "")) for k in ("title", "summary", "source", "url", "link"))
        s = 0
        for token in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", text):
            if token and token in blob:
                s += 2
        if item.get("summary"):
            s += 2
        if item.get("url") or item.get("link"):
            s += 1
        return s

    return sorted(candidates, key=score, reverse=True)[0]


def _detail_bubble(item: dict[str, Any], text: str) -> str:
    summary = str(item.get("summary") or item.get("description") or "").strip()
    title = str(item.get("title") or "").strip()
    source = str(item.get("source") or "").strip()
    basis = summary or title
    if not basis:
        return ""
    basis = re.sub(r"\s+", " ", basis)
    if len(basis) > 120:
        basis = basis[:117] + "..."
    if re.search(r"(离谱|吐槽|笑死)", text):
        prefix = "离谱的是"
    elif re.search(r"(酷|有意思|心动|怪)", text):
        prefix = "有意思的是"
    else:
        prefix = "重点是"
    return f"{prefix}，{basis}（{source}）" if source and source not in basis else f"{prefix}，{basis}"


def _link_bubble(item: dict[str, Any]) -> str:
    url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
    return f"链接：{url}" if url and re.match(r"https?://", url) else ""


def _discovery_hint(discovery_context: dict[str, Any] | None) -> str:
    item = _best_discovery_item(discovery_context, "")
    if not item:
        return ""
    title = str(item.get("title") or "").strip()
    summary = str(item.get("summary") or item.get("description") or "").strip()
    url = str(item.get("url") or item.get("link") or "").strip()
    lines = []
    if title:
        lines.append(f"- 标题：{title[:100]}")
    if summary:
        lines.append(f"- 摘要：{summary[:140]}")
    if url:
        lines.append(f"- 链接：{url}")
    return "\n".join(lines)



def _alive_state_directives() -> str:
    # ALIVE_STATE_ENGINE_V1
    engine_cls = AliveStateEngine
    if engine_cls is None:
        return ""
    try:
        return engine_cls().prompt_directives(update=True)
    except Exception:
        return ""


def _stable_score(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _float_attr(obj: Any, name: str, default: float) -> float:
    try:
        return float(getattr(obj, name))
    except Exception:
        return default


def _voice_state_value(name: str, default: float) -> float:
    if not VOICE_STATE.exists():
        return default
    try:
        data = json.loads(VOICE_STATE.read_text(encoding="utf-8", errors="ignore"))
        return float(data.get(name, default))
    except Exception:
        return default
