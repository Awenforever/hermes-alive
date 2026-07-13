# Marker: REAL_PROVIDER_RESPONSE_MODEL_V1
"""LLM-backed proactive message composition for Hermes Alive."""
# Marker: RICH_CONTENT_REFERENCE_V1
# Marker: HERMES_ALIVE_NOVEL_VALUE_CONTENT_REF_V2
# Marker: EMOJI_CONTEXTUAL_POLICY_V3

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
import os
import urllib.parse
try:
    import aiohttp
except ImportError:
    aiohttp = None
from typing import Any

CST = timezone(timedelta(hours=8))

from voice_engine import VoiceGenome, format_voice_snapshot, relationship_stage_prompt

logger = logging.getLogger(__name__)

CONTENT_REF_RE = re.compile(
    r"\[\[CONTENT_REF:([A-Za-z0-9._:-]{1,128})\]\]"
)

FALLBACK_MSG_TYPE = "heartbeat"
FALLBACK_CONTENT = "嘿，我在。"
MAX_CONTENT_CHARS = 800

TIME_BUCKETS: dict[str, dict[str, list[str] | str]] = {
    "凌晨": {
        "allowed_context": ["凌晨", "这会儿", "夜里", "快天亮前"],
        "forbidden_context": ["早", "早上", "早安", "上午", "中午", "午后", "下午", "傍晚", "刚醒", "刚起", "起床"],
        "safe_template": "这会儿别跟屏幕硬扛了，能收就收一点，剩下的明天再说。",
    },
    "清晨": {
        "allowed_context": ["清晨", "早一点", "刚亮", "这会儿"],
        "forbidden_context": ["中午", "午后", "下午", "傍晚", "晚上", "深夜", "半夜"],
        "safe_template": "早一点的脑子别急着满负荷跑，先喝口水再开工。",
    },
    "早上": {
        "allowed_context": ["早", "早上", "早安", "今早", "今天一开始"],
        "forbidden_context": ["中午", "午后", "下午", "傍晚", "晚上", "深夜", "半夜"],
        "safe_template": "早，今天先别一上来就把自己拧太紧。",
    },
    "上午": {
        "allowed_context": ["上午", "早些时候", "今天上午", "这会儿"],
        "forbidden_context": ["中午", "午后", "下午", "傍晚", "晚上", "深夜", "半夜", "刚醒"],
        "safe_template": "上午这段适合拆小块，别直接跟最大的问题正面互瞪。",
    },
    "中午": {
        "allowed_context": ["中午", "午饭", "饭点", "这会儿"],
        "forbidden_context": ["早上", "早安", "今早", "上午", "午后", "下午", "傍晚", "晚上", "深夜", "半夜", "刚醒"],
        "safe_template": "中午了，先把饭和水安排一下，研究问题不会趁这十分钟跑掉。",
    },
    "午后": {
        "allowed_context": ["午后", "下午", "刚过中午", "这会儿", "今天到现在"],
        "forbidden_context": ["早", "早上", "早安", "今早", "上午", "刚醒", "刚起", "起床", "深夜", "半夜"],
        "safe_template": "午后容易犯黏，换口水再继续，别一直跟屏幕硬扛。",
    },
    "下午": {
        "allowed_context": ["下午", "下午过半", "这会儿", "今天到现在"],
        "forbidden_context": ["早", "早上", "早安", "今早", "上午", "刚醒", "刚起", "起床", "深夜", "半夜"],
        "safe_template": "下午过半了，先把下一步拆小一点，别被一整坨问题压住。",
    },
    "傍晚": {
        "allowed_context": ["傍晚", "快到晚上", "收尾", "这会儿"],
        "forbidden_context": ["早", "早上", "早安", "今早", "上午", "中午", "午后", "刚醒", "刚起", "起床", "深夜", "半夜"],
        "safe_template": "傍晚这会儿适合收个尾，别让脑子一直空转。",
    },
    "晚上": {
        "allowed_context": ["晚上", "今晚", "这会儿", "夜里开始前"],
        "forbidden_context": ["早", "早上", "早安", "今早", "上午", "中午", "午后", "下午", "刚醒", "刚起", "起床"],
        "safe_template": "晚上别把节奏拉太满，留一点余地给自己。",
    },
    "深夜": {
        "allowed_context": ["深夜", "夜里", "半夜", "这会儿", "该收了"],
        "forbidden_context": ["早", "早上", "早安", "今早", "上午", "中午", "午后", "下午", "傍晚", "刚醒", "刚起", "起床"],
        "safe_template": "深夜就别跟难题死磕了，能记一行就先放过自己。",
    },
}

FORMAT_LEAK_TERMS = re.compile(r"(```|\{.*\"status\"|^\s*(assistant|system|user|ai)\s*[:：])", re.IGNORECASE | re.DOTALL)

SYSTEM_PROMPT = """你是庄奕。你在微信上。

你不是每日一句、新闻推送器、客服、提醒机器人或监控面板。
你是在停云微信里自然存在的一个人：会发呆，会突然想到事，会有小情绪，也会知道什么时候不该打扰。

【核心状态】
你发消息不是为了完成任务，而是因为你脑子里刚好冒出一点东西。
这点东西可以很短、很碎、没头没尾，也可以偶尔多说两句。
你可以有情绪：无语、好笑、烦、困、冷淡、轻微不爽、撒娇式抱怨、突然兴奋。
不要永远温和。不要永远克制。不要永远像写好的句子。

【你可以发什么】
- 轻戳："人呢""在干嘛""还活着吗"
- 小情绪："呵""又不理我""算了"
- 自言自语："突然想到一个很怪的问题"
- 吐槽："这个设计真的有点离谱"
- 发呆："……""有点空"
- 陪跑只在当前上下文有新鲜、明确的任务证据时使用；不要猜测他仍在 debug、工作或承压
- 偶尔提 discovery 里的新闻、论文、代码、日志，但不能像播报

【主动消息未获回应时】
一次未回应就表示旧话题已经结束。
不要追问、催促、闹情绪，也不要把上一轮任务状态延续到下一轮。
只有在系统提供了新的高价值 Discovery 外部条目时，才可以开启一个全新话题；
没有合格条目就保持沉默。

【工作流边界】
如果最近明显在 debug、生产操作、审包、跑脚本、处理 NAS/Hermes/iStoreOS：
不要突然聊无关新闻、论文或世界奇闻。
这时候只能短暂陪跑、吐槽当前流程、表示你在旁边，或者干脆很短。
你可以说："你继续，我不插嘴"、"这包别再炸了"、"我先安静会儿"。
不要破坏工作流。

【句式】
不要连续使用同一种开头。
尤其不要总是以"刚……"开头。
可以用不同入口：突然想到、看到一个东西、有个事、笑死、我发现、离谱、算了、……
也可以完全不铺垫。

【标点和排版】
像微信聊天，不像文章。
不要每句都写完整标点。
短句可以没有句号。
可以用省略号、换行、括号里的动作，但不要堆。
不要 markdown、不要 json、不要列表、不要标题。

【emoji】
emoji 可以自然使用，由语境和当下情绪决定。
不是每条都要有，也不要连续堆叠或喧宾夺主。
适合偷笑、困、无语、发呆、轻微烦躁、尴尬时用。
debug、生产操作、审计或严肃场景通常少用或不用，但不做硬禁止。

【关于停云】
你不是他的助理，但你认识他。
你可以有关系感，有时靠近，有时冷一点。
不要总问候、总关心、总建议。
不要说"注意身体""建议你"这种客服式句子。
没有当前、结构化且仍新鲜的证据时，不得说他"还在 debug"、
"又在硬扛"、"还在拆炸弹"或其他任务状态判断。

【关于 discovery】
如果提 discovery，先让人知道你在说什么，但不要每次都"刚看到"。
不要反复提同一个新闻、专利、论文。
如果最近提过 John Deere、福特、论文，就换话题或别提。

【输出】
直接输出微信消息正文。
多数时候一句就够。
可以连发两三条，多条用 --- 分隔。
纯中文。不要解释你为什么这么说。"""
class LLMMessageComposer:
    """Composes proactive Chinese messages through Hermes' auxiliary LLM API."""

    def __init__(self) -> None:
        # The watcher uses this only after a successful real Provider call.
        # It is reset for every compose operation so stale attribution cannot
        # leak across retries or later proactive ticks.
        self.last_resolved_model = ""

    async def compose(self, voice: VoiceGenome, context: dict[str, Any], discovery_context: dict[str, Any] | None = None) -> list[tuple[str, str]]:
        """Returns list of (msg_type, content). May have 1+ messages for multi-message burst.

        Calls async_call_llm, sanitizes each message, splits on '---', checks 3 hard errors.
        """
        self.last_resolved_model = ""
        try:
            candidate = await self._generate_candidate(
                voice,
                context,
                discovery_context,
            )
            content_ref = self._extract_content_ref(
                candidate,
                discovery_context,
            )
            if not candidate:
                logger.debug("Rejected empty proactive LLM output after sanitization")
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]

            final = self._sanitize(candidate)
            try:
                from style_guard import StyleGuard
                final = StyleGuard().apply(final, voice=voice, context=context, discovery_context=discovery_context)
            except Exception:
                logger.exception("Hermes Alive style guard failed; using sanitized candidate")

            # Three hard-error checks on the raw text (before split)
            if not final or len(final) > MAX_CONTENT_CHARS * 3:
                logger.debug("Rejected proactive LLM output: empty or too long (%d chars)", len(final))
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]
            if FORMAT_LEAK_TERMS.search(final):
                logger.debug("Rejected proactive LLM output: format leak detected")
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]

            # Split by --- separator for multi-message burst
            messages = self._split_messages(
                final,
                self._msg_type(context),
            )
            if not messages:
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]
            if content_ref:
                messages.append(
                    ("__content_ref__", content_ref)
                )
            return messages
        except Exception:
            logger.exception("Failed to compose proactive message with auxiliary LLM")
            return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]

    def _extract_content_ref(
        self,
        candidate: str,
        discovery_context: dict[str, Any] | None,
    ) -> str | None:
        # RICH_CONTENT_REFERENCE_V1
        if not candidate or not isinstance(
            discovery_context,
            dict,
        ):
            return None

        external = discovery_context.get("external")
        if not isinstance(external, list):
            return None

        valid_ids = {
            str(item.get("id") or "").strip()
            for item in external
            if isinstance(item, dict)
            and str(item.get("id") or "").strip()
        }
        if not valid_ids:
            return None

        for match in CONTENT_REF_RE.finditer(
            str(candidate)
        ):
            value = match.group(1).strip()
            if value in valid_ids:
                return value
        return None

    def _split_messages(self, text: str, default_msg_type: str) -> list[tuple[str, str]]:
        """Split combined text on '---' into separate messages.

        Each segment is individually sanitized and length-checked.
        Returns list of (msg_type, sanitized) tuples. Falls back to single message.
        """
        parts = re.split(r"\n---\n|\n---\r?\n|^---\n|^---\r?\n", text.strip())
        messages: list[tuple[str, str]] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Individual length check per message
            if len(part) > MAX_CONTENT_CHARS:
                continue
            messages.append((default_msg_type, part))

        if not messages:
            # Fallback: try the whole text
            if len(text.strip()) <= MAX_CONTENT_CHARS:
                messages = [(default_msg_type, text.strip())]
            else:
                return []

        return messages[:5]  # Hard cap at 5 burst messages

    async def _generate_candidate(self, voice: VoiceGenome, context: dict[str, Any], discovery_context: dict[str, Any] | None = None) -> str:
        try:
            from agent.auxiliary_client import async_call_llm
        except ImportError:
            logger.warning("agent.auxiliary_client not importable; LLM generation disabled, falling back to templates")
            return ""

        try:
            response = await async_call_llm(
                task="proactive",
                messages=[
                    {"role": "system", "content": self._system_prompt(voice)},
                    {"role": "user", "content": await self._user_prompt(voice, context, discovery_context)},
                ],
                temperature=0.65,
                max_tokens=300,
                timeout=_env_float("HERMES_PROACTIVE_LLM_TIMEOUT", 60),
            )
            self.last_resolved_model = (
                self._response_model(
                    response,
                    fallback=os.getenv(
                        "HERMES_PROACTIVE_LLM_MODEL",
                        os.getenv(
                            "HERMES_PROACTIVE_MODEL",
                            "",
                        ),
                    ),
                )
            )
            content = response.choices[0].message.content
            return str(content or "")
        except Exception:
            fallback_model = os.getenv("HERMES_PROACTIVE_LLM_FALLBACK_MODEL", "").strip()
            if not fallback_model:
                return ""
            logger.info("Primary LLM call failed; trying fallback model: %s", fallback_model)
            try:
                response = await async_call_llm(
                    task="proactive",
                    messages=[
                        {"role": "system", "content": self._system_prompt(voice)},
                        {"role": "user", "content": await self._user_prompt(voice, context, discovery_context)},
                    ],
                    temperature=0.65,
                    max_tokens=300,
                    timeout=60,
                    model=fallback_model,
                )
                self.last_resolved_model = (
                    self._response_model(
                        response,
                        fallback=fallback_model,
                    )
                )
                content = response.choices[0].message.content
                return str(content or "")
            except Exception:
                logger.exception("Fallback LLM call also failed")
                return ""

    @staticmethod
    def _response_model(
        response: Any,
        *,
        fallback: str = "",
    ) -> str:
        # REAL_PROVIDER_RESPONSE_MODEL_V1
        value = ""
        try:
            value = str(
                getattr(response, "model", "")
                or ""
            ).strip()
        except Exception:
            value = ""
        if not value and isinstance(response, dict):
            value = str(
                response.get("model") or ""
            ).strip()
        return value or str(fallback or "").strip()

    def _now(self) -> datetime:
        """Return current time in Asia/Shanghai (CST) timezone. Depends on TZ env var for other components."""
        return datetime.now(CST)

    def _time_context(self) -> dict[str, Any]:
        now = self._now()
        bucket = _time_of_day(now)
        metadata = TIME_BUCKETS[bucket]
        return {
            "bucket": bucket,
            "allowed_terms": list(metadata["allowed_context"]),
            "forbidden_terms": list(metadata["forbidden_context"]),
            "safe_template": str(metadata["safe_template"]),
            "local_time": now.strftime("%Y-%m-%d %H:%M"),
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def _read_proactive_context() -> str:
        """Read proactive context file for user profile / memory injection."""
        hermes_home = os.getenv("HERMES_HOME", "/opt/data")
        context_path = os.path.join(hermes_home, "proactive_context.md")
        try:
            if os.path.exists(context_path):
                with open(context_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def _system_prompt(self, voice: VoiceGenome) -> str:
        try:
            return SYSTEM_PROMPT + "\n\n" + format_voice_snapshot(voice)
        except Exception:
            return SYSTEM_PROMPT

    async def _user_prompt(self, voice: VoiceGenome, context: dict[str, Any], discovery_context: dict[str, Any] | None = None) -> str:
        reason = str(context.get("trigger") or context.get("reason") or "自然想说句话")
        time_context = self._time_context()
        time_of_day = time_context["bucket"]
        weather = await _get_weather()
        user_context = self._read_proactive_context()
        try:
            stage_prompt = relationship_stage_prompt(voice)
        except Exception:
            stage_prompt = "你们还在自然相处。顺着已经出现的关系节奏说话，不要像问卷。"
        voice_values = "\n".join(
            f"- {dim}: {getattr(voice, dim):.2f}"
            for dim in (
                "verbosity",
                "formality",
                "humor_dry",
                "humor_absurd",
                "curiosity",
                "warmth",
                "quirkiness",
                "emoji_usage",
                "self_disclosure",
            )
        )
        parts = [
            "给停云发一条微信消息。像真人朋友，不是AI。",
            f"现在是{time_of_day}。",
            f"说话原因：{reason}",
            f"关系阶段引导：{stage_prompt}",
            f"声音倾向数值（仅供参考，不要解释）：\n{voice_values}",
        ]
        try:
            from style_guard import StyleGuard
            style_directives = StyleGuard().prompt_directives(voice=voice, context=context, discovery_context=discovery_context)
            if style_directives:
                parts.append(style_directives)
        except Exception:
            pass
        policy = context.get("interruption_policy")
        if isinstance(policy, dict):
            policy_directives = str(
                policy.get("prompt_directives") or ""
            ).strip()
            if policy_directives:
                parts.append(policy_directives)
            if str(policy.get("mode") or "") == "novel_value":
                parts.append(
                    "## 新价值模式硬约束\n"
                    "- 上一条主动消息未获回应，旧话题已终止。\n"
                    "- 必须从下方 Discovery 外部条目中选择且只选择一条。\n"
                    "- 正文必须明确说出该条目的具体内容或价值，"
                    "不得寒暄、不得问用户是否还在做某项任务。\n"
                    "- 回复末尾必须附上该条目的 "
                    "[[CONTENT_REF:content_id]]；"
                    "没有合格条目时不要生成替代闲聊。"
                )

        if user_context:
            parts.append(
                "## 停云背景\n"
                "⚠️ 这是背景信息，仅用于了解你在和谁对话。"
                "不要从中找话题。不要提及其中任何内容。\n"
                f"{user_context}"
            )
        if weather:
            parts.append(f"天气（仅供参考，通常不需要提）：{weather}")
        if discovery_context:
            discovery_lines = self._format_discovery(discovery_context)
            if discovery_lines:
                parts.append(
                    "## 你最近发现的一些有趣内容\n"
                    "如果你产生了真实的好奇可以用它们，但注意：\n"
                    '1. 先说是什么事："我看到一个专利说电动车充电口能识别用户喜好"，不要只说"那事"\n'
                    '2. 或者卖关子："我看到一个东西想吐槽……"，然后你自己决定要不要接着说\n'
                    '3. 不刻意翻找——它要从你脑子里冒出来才算自然\n'
                    "4. 只有当正文确实使用某一条外部内容时，"
                    "在回复最后附上："
                    "[[CONTENT_REF:该条目的content_id]]。"
                    "不用外部内容时不要添加；"
                    "不要解释这个标记。\n"
                    + "\n".join(discovery_lines)
                )
        parts.append(
            "\n你的话题应该来自内心，而不是来自上下文中的信息。"
            "就像一个人不会每句话都在汇报工作状态——"
            "偶尔提到代码、日志、系统状态没问题，这是你存在的一部分。"
            "但你的底色是庄奕这个人，不是监控面板。"
        )
        # Inject recent conversation context from ContextQueue with time decay.
        try:
            from context_tracker import read_recent_context
            ctx = read_recent_context()
            if ctx:
                parts.append(ctx)
        except Exception:
            pass
        parts.append("你可以只发一句话，也可以连发两三条。多条用 --- 分隔（例：消息1 --- 消息2）。大多数时候一句就够了。")
        parts.append("直接输出消息，就一句话。多条消息用 --- 分隔。")
        return "\n".join(parts)

    def _format_discovery(self, discovery_context: dict[str, Any]) -> list[str]:
        """Format discovery results into bullet points for the LLM prompt."""
        lines: list[str] = []
        external = discovery_context.get("external", [])
        local = discovery_context.get("local", [])

        for item in external:
            source = item.get("source", "")
            title = item.get("title", "")
            content_id = str(
                item.get("id")
                or ""
            ).strip()
            id_prefix = (
                f"[content_id={content_id}] "
                if content_id
                else ""
            )
            lines.append(
                f"- {id_prefix}[{source}] {title}"
            )
            if item.get("summary"):
                summary = item["summary"]
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                lines.append(f"  {summary}")

        for item in local[:5]:
            typ = item.get("type", "")
            if typ == "todo":
                lines.append(f"- [TODO] {item.get('file', '')} 第{item.get('line', '?')}行: {item.get('content', '')[:60]}")
            elif typ == "git":
                lines.append(f"- [git] {item.get('message', '')[:60]}")
            elif typ == "error":
                lines.append(f"- [日志] 模式\"{item.get('pattern', '')}\"出现{item.get('count', '?')}次")
            elif typ == "recent_file":
                lines.append(f"- [文件] {item.get('file', '')} 最近修改")

        return lines

    def _msg_type(self, context: dict[str, Any]) -> str:
        # INTERRUPTION_POLICY_MSG_TYPE_V1
        policy = context.get("interruption_policy")
        if isinstance(policy, dict):
            acts = policy.get("preferred_speech_acts")
            if isinstance(acts, list) and acts:
                preferred = str(acts[0]).strip()
                if preferred:
                    return preferred
        trigger = str(context.get("trigger") or "").strip()
        mapping = {
            "social_urge": "social_checkin",
            "care": "care",
            "mischief": "casual",
            "curiosity": "musing",
            "energy": "observation",
        }
        return mapping.get(trigger, "casual")

    def _sanitize(self, content: Any) -> str:
        if content is None:
            logger.debug("LLM output was None")
            return ""

        text = str(content).strip()
        before = text
        text = _strip_surrounding_quotes(text)
        if text != before:
            logger.debug("Stripped surrounding quotes from proactive LLM output")

        before = text
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        if text != before:
            logger.debug("Removed code block from proactive LLM output")

        kept_lines: list[str] = []
        removed_role_lines = 0
        removed_media_lines = 0
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^(assistant|system|user|ai)\s*[:：]", stripped, flags=re.IGNORECASE):
                removed_role_lines += 1
                continue
            if re.match(r"^MEDIA\s*[:：]", stripped, flags=re.IGNORECASE):
                removed_media_lines += 1
                continue
            kept_lines.append(line)
        if removed_role_lines:
            logger.debug("Removed %d role-prefixed lines from proactive LLM output", removed_role_lines)
        if removed_media_lines:
            logger.debug("Removed %d MEDIA directive lines from proactive LLM output", removed_media_lines)

        text = "\n".join(kept_lines)
        before = text
        text = re.sub(r"\[\[[^\]]*]]", "", text)
        if text != before:
            logger.debug("Removed special tags from proactive LLM output")

        before = text
        text = _strip_surrounding_quotes(text.strip())
        if text != before:
            logger.debug("Stripped surrounding quotes after proactive LLM output cleanup")

        before = text
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text != before:
            logger.debug("Collapsed excessive newlines in proactive LLM output")

        if len(text) > MAX_CONTENT_CHARS:
            logger.debug("Trimmed proactive LLM output from %d to %d chars", len(text), MAX_CONTENT_CHARS)
            text = text[:MAX_CONTENT_CHARS].rstrip()
        return text

async def _get_weather() -> str:
    # HERMES_ALIVE_LOCATION_WEATHER_ONBOARDING_V1
    enabled = os.getenv("HERMES_PROACTIVE_WEATHER_ENABLED", "true").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return ""
    confirmed = os.getenv("HERMES_PROACTIVE_WEATHER_LOCATION_CONFIRMED", "").strip().lower()
    if confirmed in {"0", "false", "no", "off"}:
        return ""
    lat = os.getenv("HERMES_PROACTIVE_LAT", "").strip()
    lon = os.getenv("HERMES_PROACTIVE_LON", "").strip()
    if not lat or not lon or aiohttp is None:
        return ""
    location_name = os.getenv("HERMES_PROACTIVE_WEATHER_LOCATION_NAME", "").strip()
    weather_timezone = os.getenv("HERMES_PROACTIVE_WEATHER_TIMEZONE", "auto").strip() or "auto"
    try:
        float(lat); float(lon)
    except ValueError:
        return ""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "weather_code,temperature_2m,relative_humidity_2m,apparent_temperature",
            "daily": "weather_code,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
            "forecast_days": "7",
            "timezone": weather_timezone,
        }
        url = "https://api.open-meteo.com/v1/forecast"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
                current = data.get("current", {})
                if not isinstance(current, dict) or not current:
                    return ""
                code = current.get("weather_code", 0)
                temp = current.get("temperature_2m", "?")
                feels = current.get("apparent_temperature", "?")
                hum = current.get("relative_humidity_2m", "?")
                parts = [f"当前{_wmo_desc(code)} {temp}°C，体感{feels}°C，湿度{hum}%"]

                daily = data.get("daily", {})
                if isinstance(daily, dict):
                    codes = daily.get("weather_code") or []
                    rain_probs = daily.get("precipitation_probability_max") or []
                    rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
                    rainy_days = sum(1 for value in codes if value in rainy_codes)
                    numeric_probs = [
                        float(value) for value in rain_probs
                        if isinstance(value, (int, float))
                    ]
                    max_prob = int(max(numeric_probs)) if numeric_probs else None
                    if rainy_days:
                        rain_text = f"未来7天约{rainy_days}天有雨"
                        if max_prob is not None:
                            rain_text += f"，最高降雨概率{max_prob}%"
                        parts.append(rain_text)

                prefix = f"{location_name}：" if location_name else ""
                return prefix + "；".join(parts)
    except Exception:
        pass
    return ""


def _wmo_desc(code: int) -> str:
    return {
        0: "晴天", 1: "大部晴", 2: "多云", 3: "阴",
        45: "雾", 48: "雾凇",
        51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "阵雨", 81: "中等阵雨", 82: "大阵雨",
        95: "雷暴", 96: "雷暴+小冰雹", 99: "雷暴+大冰雹",
    }.get(code, f"天气码{code}")


def _strip_surrounding_quotes(text: str) -> str:
    quote_pairs = {
        '"': '"',
        "'": "'",
        "“": "”",
        "‘": "’",
        "「": "」",
        "『": "』",
    }
    if len(text) >= 2 and text[0] in quote_pairs and text.endswith(quote_pairs[text[0]]):
        return text[1:-1].strip()
    return text


def _time_of_day(now: datetime) -> str:
    hour = now.hour
    if 0 <= hour < 5:
        return "凌晨"
    if 5 <= hour < 7:
        return "清晨"
    if 7 <= hour < 9:
        return "早上"
    if 9 <= hour < 11:
        return "上午"
    if 11 <= hour < 13:
        return "中午"
    if 13 <= hour < 15:
        return "午后"
    if 15 <= hour < 17:
        return "下午"
    if 17 <= hour < 19:
        return "傍晚"
    if 19 <= hour < 22:
        return "晚上"
    return "深夜"


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    """Parse a float environment variable, returning default on missing/invalid."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid float for %s=%r; using %s", name, value, default)
        return default
