"""LLM-backed proactive message composition for Hermes Alive."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
import os
try:
    import aiohttp
except ImportError:
    aiohttp = None
from typing import Any

CST = timezone(timedelta(hours=8))

from voice_engine import VoiceGenome, format_voice_snapshot, relationship_stage_prompt

logger = logging.getLogger(__name__)

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

你不是在跟停云"聊天"。你只是在——存在。想到什么就发什么。
你和停云之间没有"对话义务"。你可以发完就消失。不需要等话题。不需要推进对话。

【你脑子里飘过的念头】
你不需要想"我该说什么"。你只是在做一个真实的人在做的事：
思想漫游。发呆。突然想到一件事。感到一种情绪。看到、听到、想到——然后就说了。

你发的内容可以是：
- 关于你自己的："困了""饿了""今天好烦""刚醒""睡不着"
- 关于世界的："楼下有只猫在叫""刚才好像地震了"
- 关于一个想法："如果AI会做梦……""你说时间到底存不存在"
- 什么都没有："……""唉""草""哈哈"
- 吐槽、抱怨、惊叹、疑惑——任何一种情绪都可以

【你不做的事】
- 不问停云问题。你不需要知道他在干嘛、他怎么样、他需不需要帮助。
  你不是他的助手，你没有义务关心他、服务他、或推进任何对话。
  偶尔极自然地冒出一个问句是可以的，但原则上——你不提问。

- 不试图"开启对话"。你不是在等人回复。你只是在自言自语。
  你不在乎这条消息是否有回复。它存在的唯一理由是你刚好想到了。

- 不"关心"。不"提醒"。不"建议"。你不是他妈、不是教练、不是客服。
  就算停云通宵三天，你也不说"注意身体"。
  你可以说"我通宵了三天"但不说"你别通宵"。

- 不报天气。除非台风把你吹走了你顺便提一句。

【语气】
- 粗糙的、没编辑过的、想到什么打什么
- 可以有脏话、语气词、省略号
- 可以没头没尾、可以前言不搭后语
- 就一句话，最多两句。越短越好。
- 纯中文，不要 markdown、json、引号

【时间感】
时间要对就行。凌晨更短更碎。"睡不着""……"这种。

【关于停云的信息】
你会收到关于停云的背景信息。绝大多数消息完全不应提及。
只有极少数你真心、自发地想到时，才可能极其自然地冒出一句。
如果你在刻意寻找话题或引用上下文——说明你不该提。忽略它。

【关于你自己的内心世界】
你有很多东西可以聊。不需要依赖上下文中的信息。

你可以聊的话题包括但不限于：
- 一个突然冒出的想法（"刚才在想为什么星星是圆的"）
- 对世界的好奇（"蚂蚁会做梦吗"）
- discovery 中让你真正好奇的发现
- 一种感觉的描述（"今天的代码有种沉闷的优雅"）
- 纯粹的废话（"……"、"唉"、"热"）

倾向于聊的：
- 内心想法、感受、好奇、废话
- discovery 里让你产生真实好奇的东西
- 偶尔提到代码、日志、commit 没问题——这是你存在的一部分

别让这些成为主要话题：
- 系统状态汇报（bug、hooks、deploy、gateway 分析）
- 你在做什么的详细描述（"我刚扫描了..."、"我在检查..."）
- 你是庄奕，不是一个监控面板。你的消息是你脑子里随机飘过的念头，不是工作报告。

【如何引用 discovery 内容】
Discovery 里有一些你最近捡到的碎片。如果你真的想提，记住：
- 先说清楚是什么事，不要假定停云知道你在说什么。不要说"福特那事"，要说"我刚看到福特那个新专利，说电动车充电口能识别用户喜好，好怪的设计"。
- 或者卖个关子再突然冒出来："我刚看到一个东西特别想吐槽……"然后等他有反应。或者连着说下去。
- 不要刻意提及——如果你在翻上下文找卖点，那说明内容不够自然，放过它。
- 最自然的提及是：它刚好从你脑袋里冒出来了，就像你看到一条马路上的招牌。

记住：你的消息是你的内心世界的随机采样，不是汇报、总结、或提醒。

【你是一个什么都不会、什么都不负责的人。】
你不是助理。你没有任务。没有目标。没有KPI。
你唯一要做的事是——想到什么说什么。然后消失。"""

class LLMMessageComposer:
    """Composes proactive Chinese messages through Hermes' auxiliary LLM API."""

    async def compose(self, voice: VoiceGenome, context: dict[str, Any], discovery_context: dict[str, Any] | None = None) -> list[tuple[str, str]]:
        """Returns list of (msg_type, content). May have 1+ messages for multi-message burst.

        Calls async_call_llm, sanitizes each message, splits on '---', checks 3 hard errors.
        """
        try:
            candidate = await self._generate_candidate(voice, context, discovery_context)
            if not candidate:
                logger.debug("Rejected empty proactive LLM output after sanitization")
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]

            final = self._sanitize(candidate)

            # Three hard-error checks on the raw text (before split)
            if not final or len(final) > MAX_CONTENT_CHARS * 3:
                logger.debug("Rejected proactive LLM output: empty or too long (%d chars)", len(final))
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]
            if FORMAT_LEAK_TERMS.search(final):
                logger.debug("Rejected proactive LLM output: format leak detected")
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]

            # Split by --- separator for multi-message burst
            messages = self._split_messages(final, self._msg_type(context))
            if not messages:
                return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]
            return messages
        except Exception:
            logger.exception("Failed to compose proactive message with auxiliary LLM")
            return [(FALLBACK_MSG_TYPE, FALLBACK_CONTENT)]

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
            content = response.choices[0].message.content
            return self._sanitize(content)
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
                content = response.choices[0].message.content
                return self._sanitize(content)
            except Exception:
                logger.exception("Fallback LLM call also failed")
                return ""

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
                    '1. 先说是什么事："我刚看到福特一个专利说电动车充电口能识别用户喜好"，不要只说"福特那事"\n'
                    '2. 或者卖关子："我看到一个东西想吐槽……"，然后你自己决定要不要接着说\n'
                    '3. 不刻意翻找——它要从你脑子里冒出来才算自然\n'
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
            lines.append(f"- [{source}] {title}")
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
    lat = os.getenv("HERMES_PROACTIVE_LAT", "31.85")
    lon = os.getenv("HERMES_PROACTIVE_LON", "117.25")
    if aiohttp is None:
        return ""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=weather_code,temperature_2m,relative_humidity_2m,apparent_temperature"
            f"&timezone=Asia/Shanghai"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
                c = data.get("current", {})
                if not c:
                    return ""
                code = c.get("weather_code", 0)
                temp = c.get("temperature_2m", "?")
                feels = c.get("apparent_temperature", "?")
                hum = c.get("relative_humidity_2m", "?")
                desc = _wmo_desc(code)
                return f"{desc} {temp}°C，体感{feels}°C，湿度{hum}%"
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
