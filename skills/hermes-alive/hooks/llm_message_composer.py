# Marker: REAL_PROVIDER_RESPONSE_MODEL_V1
"""LLM-backed proactive message composition for Hermes Alive."""
# Marker: RICH_CONTENT_REFERENCE_V1
# Marker: HERMES_ALIVE_NOVEL_VALUE_CONTENT_REF_V2
# Marker: EMOJI_CONTEXTUAL_POLICY_V3
# Marker: HERMES_ALIVE_SEMANTIC_PLAN_COMPOSER_V1
# Marker: HERMES_ALIVE_DYNAMIC_1_TO_5_BUBBLES_V1
# Marker: HERMES_ALIVE_NO_MECHANICAL_POST_SPLIT_V1
# Marker: HERMES_ALIVE_CONTEXT_VISIBILITY_COMPOSER_V1
# Marker: HERMES_ALIVE_CONTEXT_REFERENT_PROMPT_BOUNDARY_V1

from __future__ import annotations

import json
import logging
import re
import asyncio
import html as html_lib
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
from semantic_bubbles import (
    SemanticBubble,
    SemanticBubblePlan,
    SemanticPlanError,
    messages_from_plan,
    parse_semantic_plan,
    validate_semantic_plan,
)

logger = logging.getLogger(__name__)

CONTENT_REF_RE = re.compile(
    r"\[\[CONTENT_REF:([A-Za-z0-9._:-]{1,128})\]\]"
)

FALLBACK_MSG_TYPE = "heartbeat"
FALLBACK_CONTENT = "嘿，我在。"
MAX_CONTENT_CHARS = 800
MAX_EDITORIAL_CANDIDATES = 8
MAX_EVIDENCE_CHARS = 10000
MAX_RAW_ARTICLE_CHARS = 50000

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
- 轻戳可以有，但必须尊重连续未回应带来的克制，不得催促或施压
- 小情绪可以表现为语气和取舍，不得说"又不理我"、"已读不回"之类的话
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
只有系统明确提供了新鲜、健康且可见的最近对话时，才可以延续当前任务。
不得从通用示例、用户背景、Discovery 或自己的猜测推断他仍在 debug、跑脚本、审包或处理某项任务。
涉及任务时必须说出明确对象；禁止只说"那个包""这包""那个事"或"还在跟那个较劲"。
没有明确对象时改成完整的新话题，或者保持沉默。

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
Discovery 是编辑候选池，不是论文列表。时事、本地政策、人物文化、轻松趣闻、社区内容、技术和学术彼此平等。
优先选择新鲜、有明确来源、对用户有信息价值或趣味，而且近期较少出现的栏目；不得因为论文看起来专业就总选论文。
候选不足或来源、时间、事实不清楚时保持沉默，不要补写未提供的细节。

【输出协议】
只输出一个 JSON 对象，不要 markdown，不要代码围栏，不要额外解释：
{"topic_mode":"ambient|context_continuation|new_discovery","bubbles":[{"act":"语义动作","text":"气泡正文","evidence":["来源摘要或正文中的逐字片段"]}],"content_ref":null}

要求：
- act 只能从以下枚举中选择，不得创造近义标签或英文变体：self_talk、observation、question、care、dry_observation、debug_companion、research_ping、discovery_intro、fact、reaction、turn、source_link、closing、poke、casual
- bubbles 必须是 1–5 条，默认使用能完整表达的最少条数
- max_bubbles 只是上限，不是目标；简单分享通常一条即可，事实和简短反应可以在同一条中自然完成
- 每条必须承担独立语义动作，而不是把一段完整文字按句号、长度或换行切开
- 多条时应自然递进；删除某条会损失一个独立信息或话语功能
- “看到个东西”“想跟你说”等纯开场不算独立语义动作；第一条本身就要包含信息核心
- 主观反应必须增加一个有依据的观察角度；不得伪造“第一次见”“一直觉得”等个人经历来凑人格
- 不得使用 --- 作为分隔符
- Discovery 无相关上下文时，topic_mode 必须是 new_discovery，第一条 act 必须是 discovery_intro、research_ping 或 fact，并直接说清新发现是什么
- content_ref 只有正文真实使用外部条目时才填写对应 content_id，否则为 null
- new_discovery 中每个陈述外部事实的气泡都必须提供 evidence；每项必须逐字复制自所选条目的摘要或页面正文，不能复制标题、不能改写。evidence 只用于发送前核验，不会显示给用户
- text 使用自然中文微信口吻，不要解释 JSON 协议"""
class LLMMessageComposer:
    """Composes proactive Chinese messages through Hermes' auxiliary LLM API."""

    def __init__(self) -> None:
        # The watcher uses this only after a successful real Provider call.
        # It is reset for every compose operation so stale attribution cannot
        # leak across retries or later proactive ticks.
        self.last_resolved_model = ""
        self.last_semantic_plan: dict[str, Any] = {}
        self.last_repair_reason = ""
        self.last_editorial_review: dict[str, Any] = {}
        self.last_context_snapshot: dict[str, Any] = {}
        self.last_rejection_reason = ""

    async def compose(
        self,
        voice: VoiceGenome,
        context: dict[str, Any],
        discovery_context: dict[str, Any] | None = None,
    ) -> list[tuple[str, str]]:
        """Generate a semantic plan first, then return 1-5 complete bubbles."""
        self.last_resolved_model = ""
        self.last_semantic_plan = {}
        self.last_repair_reason = ""
        self.last_editorial_review = {}
        self.last_context_snapshot = {}
        self.last_rejection_reason = ""
        try:
            discovery_context = await self._enrich_discovery_context(
                discovery_context,
                context=context,
            )
            candidate = await self._generate_candidate(
                voice,
                context,
                discovery_context,
            )
            if not candidate:
                if self.last_rejection_reason:
                    return []
                logger.debug(
                    "Rejected empty proactive LLM output"
                )
                return [
                    (FALLBACK_MSG_TYPE, FALLBACK_CONTENT)
                ]

            policy = context.get("interruption_policy")
            policy_decision = (
                policy if isinstance(policy, dict) else None
            )
            default_type = self._msg_type(context)

            candidate, repaired = self._cap_candidate_to_policy(
                candidate,
                policy_decision,
            )
            if repaired:
                self.last_repair_reason = "bubble_count_capped_to_policy"
                logger.info(
                    "Repaired proactive semantic plan: %s",
                    self.last_repair_reason,
                )

            try:
                plan = parse_semantic_plan(
                    candidate,
                    default_msg_type=default_type,
                    policy_decision=policy_decision,
                    discovery_context=discovery_context,
                    context_snapshot=self.last_context_snapshot,
                )
            except SemanticPlanError as exc:
                self.last_rejection_reason = str(exc)
                logger.debug(
                    "Rejected proactive semantic plan: %s",
                    str(exc),
                )
                return []

            messages: list[tuple[str, str]] = []
            for msg_type, raw_text in messages_from_plan(plan):
                final = self._sanitize(raw_text)
                try:
                    from style_guard import StyleGuard
                    final = StyleGuard().apply(
                        final,
                        voice=voice,
                        context=context,
                        discovery_context=discovery_context,
                    )
                except Exception:
                    logger.exception(
                        "Hermes Alive style guard failed; "
                        "using sanitized semantic bubble"
                    )

                if (
                    not final
                    or len(final) > MAX_CONTENT_CHARS
                    or FORMAT_LEAK_TERMS.search(final)
                ):
                    logger.debug(
                        "Rejected semantic bubble after sanitization"
                    )
                    return [
                        (FALLBACK_MSG_TYPE, FALLBACK_CONTENT)
                    ]
                messages.append((msg_type, final))

            if not messages:
                return [
                    (FALLBACK_MSG_TYPE, FALLBACK_CONTENT)
                ]

            final_plan = SemanticBubblePlan(
                topic_mode=plan.topic_mode,
                bubbles=[
                    SemanticBubble(act=msg_type, text=content)
                    for msg_type, content in messages
                ],
                content_ref=plan.content_ref,
                source_format=plan.source_format,
            )
            try:
                validate_semantic_plan(
                    final_plan,
                    policy_decision=policy_decision,
                    discovery_context=discovery_context,
                    context_snapshot=self.last_context_snapshot,
                )
            except SemanticPlanError as exc:
                self.last_rejection_reason = str(exc)
                logger.debug(
                    "Rejected styled semantic plan: %s",
                    str(exc),
                )
                return []

            self.last_semantic_plan = final_plan.safe_metadata()
            if final_plan.content_ref:
                messages.append(
                    ("__content_ref__", final_plan.content_ref)
                )
            return messages
        except Exception:
            logger.exception(
                "Failed to compose proactive semantic bubbles"
            )
            return [
                (FALLBACK_MSG_TYPE, FALLBACK_CONTENT)
            ]

    @staticmethod
    def _cap_candidate_to_policy(
        candidate: str,
        policy_decision: dict[str, Any] | None,
    ) -> tuple[str, bool]:
        """Repair only a safe presentational overflow from otherwise valid JSON.

        The model occasionally emits four or five independent semantic acts
        when the current interruption policy permits fewer.  Dropping the
        entire sourced plan loses its content reference and turns a harmless
        formatting overrun into a failed delivery.  Preserve the original
        bubbles verbatim up to the configured limit and retain all plan-level
        provenance fields.
        """
        raw = str(candidate or "").strip()
        if not raw.startswith("{"):
            return candidate, False
        try:
            parsed = json.loads(raw)
        except Exception:
            return candidate, False
        if not isinstance(parsed, dict):
            return candidate, False
        bubbles = parsed.get("bubbles")
        if not isinstance(bubbles, list):
            return candidate, False
        try:
            limit = int((policy_decision or {}).get("max_bubbles", 5))
        except Exception:
            limit = 5
        limit = max(1, min(5, limit))
        if len(bubbles) <= limit:
            return candidate, False
        parsed["bubbles"] = bubbles[:limit]
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":")), True

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

    def _legacy_single_message(
        self,
        text: str,
        default_msg_type: str,
    ) -> list[tuple[str, str]]:
        """Compatibility helper: legacy plain text is exactly one bubble."""
        value = str(text or "").strip()
        if not value or len(value) > MAX_CONTENT_CHARS:
            return []
        if re.search(r"(^|\n)\s*---\s*(\n|$)", value):
            return []
        return [(default_msg_type, value)]

    async def _generate_candidate(self, voice: VoiceGenome, context: dict[str, Any], discovery_context: dict[str, Any] | None = None) -> str:
        try:
            from agent.auxiliary_client import async_call_llm
        except ImportError:
            logger.warning("agent.auxiliary_client not importable; LLM generation disabled, falling back to templates")
            return ""

        preferred_model = os.getenv(
            "HERMES_PROACTIVE_LLM_MODEL",
            os.getenv("HERMES_PROACTIVE_MODEL", ""),
        ).strip()
        model_override = preferred_model or None

        generation_prompt = await self._user_prompt(
            voice,
            context,
            discovery_context,
        )
        messages = [
            {"role": "system", "content": self._system_prompt(voice)},
            {"role": "user", "content": generation_prompt},
        ]
        content, resolved_model = await self._call_routed_llm(
            async_call_llm,
            task="proactive",
            messages=messages,
            temperature=0.65,
            max_tokens=500,
            preferred_model=model_override,
        )
        if not content:
            self.last_rejection_reason = "generation_unavailable"
            return ""
        content = self._normalize_json_candidate(content)
        content, ref_repaired = self._repair_unambiguous_content_ref(
            content,
            discovery_context,
        )
        if ref_repaired:
            self.last_repair_reason = "content_ref_recovered_from_exact_evidence"
        self.last_resolved_model = resolved_model

        if not self._requires_editorial_review(context, discovery_context):
            return content

        review = await self._review_editorial_candidate(
            async_call_llm,
            content,
            discovery_context,
            preferred_model=model_override,
        )
        self.last_editorial_review = review
        if review.get("pass") is True:
            return content

        # Reviewer feedback is expressed as violated dimensions, not lexical
        # substitutions.  A bounded whole-draft loop lets the model reconsider
        # selection and structure without growing a phrase-specific patch set.
        current = content
        current_model = resolved_model
        replacement_refs_used: set[str] = set()
        rejected_refs: set[str] = set()
        max_revisions = max(
            1,
            min(
                3,
                int(os.getenv("HERMES_ALIVE_EDITORIAL_MAX_REVISIONS", "3")),
            ),
        )
        for _attempt in range(max_revisions):
            issues = review.get("issues")
            if not isinstance(issues, list):
                issues = ["the draft did not satisfy the editorial contract"]
            replacement = self._take_fresh_replacement(
                review,
                replacement_refs_used,
            )
            if replacement is not None:
                revised = json.dumps(
                    replacement,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                revised_model = current_model
            else:
                rejected_ref = str(review.get("content_ref") or "").strip()
                if rejected_ref:
                    rejected_refs.add(rejected_ref)
                reselection_context, locked_ref = self._next_source_context(
                    discovery_context,
                    rejected_refs,
                )
                reselection_prompt = await self._user_prompt(
                    voice,
                    context,
                    reselection_context,
                )
                revision_prompt = (
                    reselection_prompt
                    + "\n\n## 独立编辑审查未通过\n"
                    + "不合格来源已从本轮候选集中移除，不得复用旧稿或旧 content_ref。"
                    + "\n审查意见：\n- "
                    + "\n- ".join(str(value) for value in issues[:8])
                    + "\n请从证据和信息核心重新设计整组消息，可以换选题、删减或合并气泡；"
                    + "如果当前来源无法支撑具体而有价值的分享，必须放弃它并从候选中改选其他 content_ref；"
                    + "不要逐字修补旧稿。仍只输出约定 JSON。"
                )
                revised, revised_model = await self._call_routed_llm(
                    async_call_llm,
                    task="proactive",
                    messages=[
                        {"role": "system", "content": self._system_prompt(voice)},
                        {"role": "user", "content": revision_prompt},
                    ],
                    temperature=0.25,
                    max_tokens=500,
                    preferred_model=model_override,
                )
                revised = self._bind_locked_content_ref(revised, locked_ref)
            if not revised:
                self.last_rejection_reason = "editorial_revision_unavailable"
                return ""
            revised = self._normalize_json_candidate(revised)
            revised, ref_repaired = self._repair_unambiguous_content_ref(
                revised,
                discovery_context,
            )
            if ref_repaired:
                self.last_repair_reason = "content_ref_recovered_from_exact_evidence"
            current = revised
            current_model = revised_model or current_model
            review = await self._review_editorial_candidate(
                async_call_llm,
                current,
                discovery_context,
                preferred_model=model_override,
            )
            self.last_editorial_review = review
            if review.get("pass") is True:
                self.last_resolved_model = current_model
                return current

        failed = review.get("issues")
        reason = ",".join(str(value) for value in (failed or [])[:4])
        self.last_rejection_reason = (
            "editorial_quality_rejected"
            + (f":{reason}" if reason else "")
        )
        return ""

    @classmethod
    def _next_source_context(
        cls,
        discovery_context: dict[str, Any] | None,
        rejected_refs: set[str],
    ) -> tuple[dict[str, Any] | None, str]:
        """Lock recovery generation to the next ranked evidence source."""
        filtered = cls._without_content_refs(discovery_context, rejected_refs)
        if not isinstance(filtered, dict):
            return filtered, ""
        external = filtered.get("external")
        if not isinstance(external, list):
            return filtered, ""
        selected = next(
            (
                item for item in external
                if isinstance(item, dict)
                and str(item.get("id") or "").strip()
            ),
            None,
        )
        if selected is None:
            return filtered, ""
        locked = dict(filtered)
        locked["external"] = [selected]
        return locked, str(selected.get("id") or "").strip()

    @classmethod
    def _bind_locked_content_ref(cls, candidate: str, locked_ref: str) -> str:
        """Bind a valid JSON draft to the sole source shown during recovery."""
        parsed = cls._json_object(candidate)
        if not isinstance(parsed, dict) or not locked_ref:
            return candidate
        if not str(parsed.get("content_ref") or "").strip():
            parsed["content_ref"] = locked_ref
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))

    def _repair_unambiguous_content_ref(
        self,
        candidate: str,
        discovery_context: dict[str, Any] | None,
    ) -> tuple[str, bool]:
        """Recover a missing reference only from unique exact evidence spans."""
        parsed = self._json_object(candidate)
        if not isinstance(parsed, dict) or parsed.get("content_ref"):
            return candidate, False
        bubbles = parsed.get("bubbles")
        external = (
            discovery_context.get("external")
            if isinstance(discovery_context, dict)
            else None
        )
        if not isinstance(bubbles, list) or not isinstance(external, list):
            return candidate, False
        quotes = [
            self._normalized_evidence_text(quote)
            for bubble in bubbles
            if isinstance(bubble, dict)
            for quote in (
                bubble.get("evidence")
                if isinstance(bubble.get("evidence"), list)
                else []
            )
            if len(self._normalized_evidence_text(quote)) >= 12
        ]
        if not quotes:
            return candidate, False
        matches: list[str] = []
        for item in external:
            if not isinstance(item, dict):
                continue
            source_text = self._normalized_evidence_text(
                "\n".join(
                    value
                    for value in (
                        str(item.get("summary") or ""),
                        str(item.get("evidence_text") or ""),
                    )
                    if value.strip()
                )
            )
            if source_text and all(quote in source_text for quote in quotes):
                item_id = str(item.get("id") or "").strip()
                if item_id:
                    matches.append(item_id)
        if len(matches) != 1:
            return candidate, False
        parsed["content_ref"] = matches[0]
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":")), True

    @staticmethod
    def _without_content_refs(
        discovery_context: dict[str, Any] | None,
        rejected_refs: set[str],
    ) -> dict[str, Any] | None:
        """Return a copy whose external candidates exclude failed sources."""
        if not isinstance(discovery_context, dict) or not rejected_refs:
            return discovery_context
        filtered = dict(discovery_context)
        external = discovery_context.get("external")
        if isinstance(external, list):
            filtered["external"] = [
                item
                for item in external
                if not (
                    isinstance(item, dict)
                    and str(item.get("id") or "").strip() in rejected_refs
                )
            ]
        return filtered

    @staticmethod
    def _take_fresh_replacement(
        review: dict[str, Any],
        used_refs: set[str],
    ) -> dict[str, Any] | None:
        """Use at most one reviewer rewrite per source before reselection.

        Repeatedly polishing an evidence-poor story cannot create information.
        After one independent rewrite, control returns to the selector so it
        can choose another source from the full Discovery set.
        """
        replacement = review.get("replacement_plan")
        if not isinstance(replacement, dict):
            return None
        content_ref = str(replacement.get("content_ref") or "").strip()
        if not content_ref or content_ref in used_refs:
            return None
        used_refs.add(content_ref)
        return replacement

    async def _call_routed_llm(
        self,
        call: Any,
        *,
        task: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        preferred_model: str | None,
    ) -> tuple[str, str]:
        """Call the configured primary, then only the explicit fallback."""
        models = [str(preferred_model or "").strip()]
        fallback = os.getenv(
            "HERMES_PROACTIVE_LLM_FALLBACK_MODEL",
            "",
        ).strip()
        if fallback and fallback not in models:
            models.append(fallback)
        if not models[0]:
            models[0] = ""

        attempts = max(
            1,
            min(
                3,
                int(os.getenv("HERMES_PROACTIVE_LLM_ROUTE_ATTEMPTS", "2")),
            ),
        )
        for index, model in enumerate(models):
            for attempt in range(attempts):
                try:
                    response = await call(
                        task=task,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=_env_float(
                            "HERMES_PROACTIVE_LLM_TIMEOUT",
                            60,
                        ),
                        model=model or None,
                    )
                    content = str(
                        response.choices[0].message.content or ""
                    ).strip()
                    if content:
                        return content, self._response_model(
                            response,
                            fallback=model,
                        )
                    logger.info(
                        "Configured LLM route returned empty content "
                        "(model=%s attempt=%s/%s)",
                        model or "default",
                        attempt + 1,
                        attempts,
                    )
                except Exception:
                    logger.info(
                        "Configured LLM route failed "
                        "(model=%s attempt=%s/%s)",
                        model or "default",
                        attempt + 1,
                        attempts,
                        exc_info=True,
                    )
            if index + 1 < len(models):
                logger.info(
                    "Trying configured fallback model after route exhaustion: %s",
                    models[index + 1],
                )
        return "", ""

    @staticmethod
    def _requires_editorial_review(
        context: dict[str, Any],
        discovery_context: dict[str, Any] | None,
    ) -> bool:
        if not isinstance(discovery_context, dict):
            return False
        external = discovery_context.get("external")
        if not isinstance(external, list) or not external:
            return False
        policy = context.get("interruption_policy")
        return bool(
            isinstance(policy, dict)
            and str(policy.get("mode") or "") == "novel_value"
        )

    async def _review_editorial_candidate(
        self,
        call: Any,
        candidate: str,
        discovery_context: dict[str, Any] | None,
        *,
        preferred_model: str | None,
    ) -> dict[str, Any]:
        """Fail-closed, evidence-aware review of a complete message plan."""
        selected = self._selected_evidence(candidate, discovery_context)
        if selected is None:
            return {
                "pass": False,
                "issues": ["missing or invalid content_ref"],
                "dimensions": {},
            }
        try:
            parse_semantic_plan(
                candidate,
                default_msg_type="fact",
                policy_decision={
                    "mode": "novel_value",
                    "max_bubbles": 5,
                },
                discovery_context=discovery_context,
                context_snapshot=self.last_context_snapshot,
            )
        except SemanticPlanError as exc:
            return {
                "pass": False,
                "issues": [
                    "semantic structure is invalid: " + str(exc)
                ],
                "dimensions": {},
                "content_ref": str(selected.get("id") or ""),
                "replacement_plan": None,
            }
        evidence_issue = self._evidence_mapping_issue(candidate, selected)
        evidence = self._evidence_document(selected)
        machine_review = (
            "\n确定性证据校验已发现：" + evidence_issue
            + "\n当前候选不得判定通过；若原文足够，请直接基于下方证据"
            + "重写 replacement_plan，并为每个事实附上原文中的逐字证据片段。\n"
            if evidence_issue
            else ""
        )
        review_prompt = f"""你是独立的微信内容编辑，不负责讨好作者。

请审查候选消息是否值得主动打扰用户。只根据给出的证据判断，不使用外部常识补洞。

通用质量契约：
1. factual_grounding：每个可核验事实都能由证据直接推出；翻译和忠实概括可以，猜测必须明确是猜测且有交流价值。
2. informational_value：用户读完能得到具体的新信息，而不是空泛开场、标题复述或无依据感想。
3. source_and_time：不夸大来源权威性，不把旧内容说成刚发生，不隐瞒材料不足。系统会自动附加来源链接，正文不必机械念出来源名或发布时间。
4. natural_voice：像朋友分享，但不伪造亲历、情绪或用户处境，不使用播报模板。
5. minimal_bubbles：气泡数是表达所需的最少数量；纯铺垫、同义重复、可无损合并都判失败。
6. coherent_whole：整组消息脱离后台上下文仍能独立理解，问题或观点必须建立在已给事实之上。

只有六项全部通过，pass 才能为 true。失败时，如果现有证据足以形成值得发送的内容，请像独立编辑一样从信息核心重新写一个 replacement_plan；它不是逐句修改原稿，气泡数应当最少。证据不足则 replacement_plan 为 null。
输出一个 JSON 对象：
{{"pass":true|false,"dimensions":{{"factual_grounding":true|false,"informational_value":true|false,"source_and_time":true|false,"natural_voice":true|false,"minimal_bubbles":true|false,"coherent_whole":true|false}},"issues":["简明、可执行的原则性问题"],"replacement_plan":null或{{"topic_mode":"new_discovery","bubbles":[{{"act":"fact","text":"正文","evidence":["摘要或正文中的逐字片段"]}}],"content_ref":"原 content_id"}}}}
{machine_review}

证据：
{evidence}

候选消息计划：
{candidate}
"""
        raw, _model = await self._call_routed_llm(
            call,
            task="proactive_editorial_review",
            messages=[
                {
                    "role": "system",
                    "content": "严格执行证据审查；宁可拒绝，不得替候选补充事实。",
                },
                {"role": "user", "content": review_prompt},
            ],
            temperature=0.0,
            max_tokens=500,
            preferred_model=preferred_model,
        )
        parsed = self._json_object(raw)
        if not isinstance(parsed, dict):
            return {
                "pass": False,
                "issues": ["editorial reviewer returned invalid JSON"],
                "dimensions": {},
            }
        dimensions = parsed.get("dimensions")
        required = {
            "factual_grounding",
            "informational_value",
            "source_and_time",
            "natural_voice",
            "minimal_bubbles",
            "coherent_whole",
        }
        dimension_pass = bool(
            isinstance(dimensions, dict)
            and required.issubset(dimensions)
            and all(dimensions.get(name) is True for name in required)
        )
        issues = parsed.get("issues")
        issue_list = issues if isinstance(issues, list) else []
        if evidence_issue and evidence_issue not in issue_list:
            issue_list = [evidence_issue, *issue_list]
        replacement = parsed.get("replacement_plan")
        if not isinstance(replacement, dict):
            replacement = None
        elif str(replacement.get("content_ref") or "") != str(
            selected.get("id") or ""
        ):
            replacement = None
        return {
            "pass": (
                parsed.get("pass") is True
                and dimension_pass
                and not issue_list
                and not evidence_issue
            ),
            "dimensions": dimensions if isinstance(dimensions, dict) else {},
            "issues": issue_list,
            "content_ref": str(selected.get("id") or ""),
            "replacement_plan": replacement,
        }

    @staticmethod
    def _json_object(value: str) -> dict[str, Any] | None:
        raw = str(value or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
            raw = re.sub(r"\s*```$", "", raw)
        try:
            parsed = json.loads(raw)
        except Exception:
            decoder = json.JSONDecoder()
            objects: list[dict[str, Any]] = []
            for index, character in enumerate(raw):
                if character != "{":
                    continue
                try:
                    candidate, _end = decoder.raw_decode(raw[index:])
                except Exception:
                    continue
                if isinstance(candidate, dict):
                    objects.append(candidate)
            plans = [value for value in objects if isinstance(value.get("bubbles"), list)]
            parsed = plans[0] if len(plans) == 1 else (objects[0] if len(objects) == 1 else None)
        return parsed if isinstance(parsed, dict) else None

    @classmethod
    def _normalize_json_candidate(cls, value: str) -> str:
        parsed = cls._json_object(value)
        if not isinstance(parsed, dict):
            return value
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))

    def _evidence_mapping_issue(
        self,
        candidate: str,
        item: dict[str, Any],
    ) -> str:
        """Validate exact source spans for every externally factual bubble."""
        parsed = self._json_object(candidate)
        if not isinstance(parsed, dict):
            return "candidate is not a JSON object with evidence mappings"
        bubbles = parsed.get("bubbles")
        if not isinstance(bubbles, list) or not bubbles:
            return "candidate has no bubbles to map to source evidence"

        title = self._normalized_evidence_text(item.get("title"))
        body = self._normalized_evidence_text(
            "\n".join(
                value
                for value in (
                    str(item.get("summary") or ""),
                    str(item.get("evidence_text") or ""),
                )
                if value.strip()
            )
        )
        if not body:
            return "selected source has no summary or retrieved body evidence"

        factual_acts = {
            "discovery_intro",
            "research_ping",
            "fact",
            "content_share",
        }
        body_evidence_seen = False
        for index, bubble in enumerate(bubbles, start=1):
            if not isinstance(bubble, dict):
                return f"bubble {index} is not an evidence-mappable object"
            act = str(bubble.get("act") or "").strip().lower()
            quotes = bubble.get("evidence")
            if act not in factual_acts and not quotes:
                continue
            if not isinstance(quotes, list) or not quotes:
                return f"bubble {index} has an external claim but no evidence spans"
            for quote in quotes:
                normalized = self._normalized_evidence_text(quote)
                if len(normalized) < 12:
                    return f"bubble {index} has an evidence span that is too short"
                if len(normalized) > 500:
                    return f"bubble {index} has an evidence span that is too long"
                if normalized not in body:
                    if normalized in title:
                        return f"bubble {index} cites only the title, not summary or body evidence"
                    return f"bubble {index} cites text absent from the selected source evidence"
                body_evidence_seen = True
        if not body_evidence_seen:
            return "candidate contains no verified summary or body evidence"
        return ""

    @staticmethod
    def _normalized_evidence_text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _selected_evidence(
        self,
        candidate: str,
        discovery_context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        parsed = self._json_object(candidate)
        if not isinstance(parsed, dict) or not isinstance(discovery_context, dict):
            return None
        content_ref = str(parsed.get("content_ref") or "").strip()
        external = discovery_context.get("external")
        if not content_ref or not isinstance(external, list):
            return None
        return next(
            (
                item for item in external
                if isinstance(item, dict)
                and str(item.get("id") or "").strip() == content_ref
            ),
            None,
        )

    @staticmethod
    def _evidence_document(item: dict[str, Any]) -> str:
        fields = [
            ("content_id", item.get("id")),
            ("title", item.get("title")),
            ("publisher", item.get("publisher") or item.get("source")),
            ("published_at", item.get("published_at")),
            ("summary", item.get("summary")),
            ("retrieved_text", item.get("evidence_text")),
            ("url", item.get("url")),
        ]
        return "\n".join(
            f"{name}: {str(value).strip()[:MAX_EVIDENCE_CHARS]}"
            for name, value in fields
            if str(value or "").strip()
        )

    async def _enrich_discovery_context(
        self,
        discovery_context: dict[str, Any] | None,
        *,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve readable evidence before asking a model to select a story."""
        if not isinstance(discovery_context, dict):
            return discovery_context
        if not self._requires_editorial_review(
            context or {},
            discovery_context,
        ):
            return discovery_context
        external = discovery_context.get("external")
        if not isinstance(external, list) or not external or aiohttp is None:
            return discovery_context

        enriched = dict(discovery_context)
        items = [dict(item) for item in external if isinstance(item, dict)]
        limit = max(
            1,
            min(
                12,
                int(os.getenv(
                    "HERMES_ALIVE_EDITORIAL_FETCH_CANDIDATES",
                    str(MAX_EDITORIAL_CANDIDATES),
                )),
            ),
        )
        timeout = aiohttp.ClientTimeout(total=10, connect=4)
        connector = aiohttp.TCPConnector(limit=4)
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "HermesAlive/2.8 editorial evidence"},
        ) as session:
            tasks = [
                self._fetch_readable_evidence(session, item)
                for item in items[:limit]
            ]
            evidence_values = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )
        for item, evidence in zip(items[:limit], evidence_values):
            if isinstance(evidence, str) and evidence:
                item["evidence_text"] = evidence
                item["evidence_status"] = "retrieved"
            else:
                item["evidence_status"] = "metadata_only"
        enriched["external"] = [
            item for item in items if self._has_source_evidence(item)
        ]
        return enriched

    @classmethod
    def _has_source_evidence(cls, item: dict[str, Any]) -> bool:
        """Exclude title-only candidates before model selection."""
        summary = cls._normalized_evidence_text(item.get("summary"))
        body = cls._normalized_evidence_text(item.get("evidence_text"))
        return len(summary) >= 24 or len(body) >= 24

    async def _fetch_readable_evidence(
        self,
        session: Any,
        item: dict[str, Any],
    ) -> str:
        url = str(item.get("url") or "").strip()
        parsed = urllib.parse.urlparse(url)
        host = str(parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not host:
            return ""
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return ""
        raw = ""
        for attempt in range(2):
            try:
                async with session.get(
                    url,
                    allow_redirects=True,
                    max_redirects=5,
                ) as response:
                    if 400 <= response.status < 500:
                        return ""
                    if response.status >= 500:
                        if attempt == 0:
                            continue
                        return ""
                    content_type = str(response.headers.get("Content-Type") or "").lower()
                    if not any(value in content_type for value in ("text", "html", "xml", "json")):
                        return ""
                    body = await response.content.read(750_000)
                    charset = response.charset or "utf-8"
                    raw = body.decode(charset, errors="replace")
                    break
            except Exception:
                if attempt == 0:
                    continue
                return ""
        if not raw:
            return ""
        readable = self._readable_text(raw)
        return self._focus_evidence(
            readable,
            title=str(item.get("title") or ""),
        )

    @staticmethod
    def _focus_evidence(text: str, *, title: str) -> str:
        """Keep lead, conclusion and title-relevant passages from long pages.

        A prefix-only slice systematically hides the explanation in essays and
        puts generators in a title-guessing regime.  This extractive selector
        never invents or summarizes text; it only chooses complete source
        passages and preserves their original order.
        """
        raw = str(text or "").strip()
        if len(raw) <= MAX_EVIDENCE_CHARS:
            return raw
        units = [
            value.strip()
            for value in re.split(r"\n+|(?<=[.!?。！？])\s+", raw)
            if len(value.strip()) >= 24
        ]
        if not units:
            return raw[:MAX_EVIDENCE_CHARS]

        title_lower = str(title or "").lower()
        ascii_terms = {
            token
            for token in re.findall(r"[a-z0-9+#.-]{4,}", title_lower)
            if token not in {"with", "from", "that", "this", "what", "when"}
        }
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", title_lower))
        chinese_terms = {
            chinese[index:index + 2]
            for index in range(max(0, len(chinese) - 1))
        }

        selected = set(range(min(3, len(units))))
        selected.update(range(max(0, len(units) - 2), len(units)))
        scored: list[tuple[int, int]] = []
        for index, unit in enumerate(units):
            lowered = unit.lower()
            score = sum(2 for term in ascii_terms if term in lowered)
            score += sum(1 for term in chinese_terms if term in unit)
            if score:
                scored.append((score, index))
        for _score, index in sorted(scored, reverse=True)[:16]:
            selected.add(index)
            if index > 0:
                selected.add(index - 1)
            if index + 1 < len(units):
                selected.add(index + 1)

        focused: list[str] = []
        total = 0
        for index in sorted(selected):
            unit = units[index]
            if total + len(unit) + 1 > MAX_EVIDENCE_CHARS:
                continue
            focused.append(unit)
            total += len(unit) + 1
        return "\n".join(focused).strip()

    @staticmethod
    def _readable_text(raw: str) -> str:
        text = str(raw or "")
        # Prefer explicit page metadata and article paragraphs, while remaining
        # dependency-free for portable NAS/WSL/Windows installs.
        fragments: list[str] = []
        for match in re.finditer(
            r"<meta[^>]+(?:name|property)=[\"'](?:description|og:description)[\"'][^>]+content=[\"']([^\"']+)",
            text,
            flags=re.I,
        ):
            fragments.append(match.group(1))
        for match in re.finditer(
            r"<(?:p|h1|h2|h3)[^>]*>(.*?)</(?:p|h1|h2|h3)>",
            text,
            flags=re.I | re.S,
        ):
            fragments.append(match.group(1))
            if sum(len(value) for value in fragments) >= MAX_RAW_ARTICLE_CHARS:
                break
        if not fragments:
            fragments = [text]
        joined = "\n".join(fragments)
        joined = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", joined, flags=re.I | re.S)
        joined = re.sub(r"<[^>]+>", " ", joined)
        joined = html_lib.unescape(joined)
        joined = re.sub(r"[\t\r ]+", " ", joined)
        joined = re.sub(r"\n\s*\n+", "\n", joined)
        return joined.strip()

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
        novel_value_mode = False
        if isinstance(policy, dict):
            policy_directives = str(
                policy.get("prompt_directives") or ""
            ).strip()
            if policy_directives:
                parts.append(policy_directives)
            if str(policy.get("mode") or "") == "novel_value":
                novel_value_mode = True
                parts.append(
                    "## 新价值模式硬约束\n"
                    "- 上一条主动消息未获回应，旧话题已终止。\n"
                    "- 必须从下方 Discovery 外部条目中选择且只选择一条。\n"
                    "- 正文必须明确说出该条目的具体内容或价值，"
                    "不得寒暄、不得问用户是否还在做某项任务。\n"
                    "- 输出 JSON 的 content_ref 字段必须填写该条目的 content_id；"
                    "没有合格条目时不要生成替代闲聊。\n"
                    "- topic_mode 必须是 new_discovery，第一条气泡必须直接锚定新发现。\n"
                    "- 所有事实只能来自候选证据；材料只有标题时，只能忠实转述标题能推出的内容。\n"
                    "- 先判断整件事最值得分享的一个信息核心，再决定表达；"
                    "没有信息的铺垫不构成独立气泡。\n"
                    "- 观点和疑问必须建立在已陈述事实之上，不能用猜测代替尚未读取的来源。"
                    "\n- 候选池里存在已取得页面正文的条目时，优先从中选择；"
                    "不要为了偏好某个题材而选择证据贫乏的条目。"
                    "\n- 每个事实气泡的 evidence 数组必须逐字引用所选条目的摘要或页面正文；"
                    "仅引用标题、改写引文或提供不存在的片段都会被拒绝。"
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
                discovery_guidance = (
                    "## 你最近发现的一些有趣内容\n"
                    "这些是编辑候选，不是必须逐条汇报的清单。\n"
                    "1. 正文应自然说清所选条目的具体事件、人物、发现或价值；"
                    "可以直接从事实切入，不要求使用固定开场白\n"
                    "2. 不得只说‘那件事’‘有个东西’等无法独立理解的指代\n"
                    "3. 只选择真正值得此刻分享的一条；没有合格条目就保持沉默\n"
                    "4. 正文确实使用外部内容时，在 JSON 的 content_ref 字段填写"
                    "对应 content_id；不要在气泡正文中输出协议标记\n"
                )
                if not novel_value_mode:
                    discovery_guidance += (
                        "5. 普通模式下不必为了使用候选而刻意翻找，"
                        "它应当像自然想到的话题\n"
                    )
                parts.append(
                    discovery_guidance
                    + "\n".join(discovery_lines)
                )
        if not novel_value_mode:
            parts.append(
                "\n你的话题应该来自内心，而不是来自上下文中的信息。"
                "就像一个人不会每句话都在汇报工作状态——"
                "偶尔提到代码、日志、系统状态没问题，这是你存在的一部分。"
                "但你的底色是庄奕这个人，不是监控面板。"
            )
        # Rebuild and inject the cross-session effective context queue for
        # every compose operation.  The metadata is retained only as hashes,
        # counts, timestamps, roles, and health flags for safe observability.
        try:
            from context_tracker import build_prompt_context
            context_bundle = build_prompt_context(refresh=True)
            snapshot = context_bundle.get("metadata")
            if isinstance(snapshot, dict):
                self.last_context_snapshot = dict(snapshot)
            ctx = str(context_bundle.get("text") or "")
            if ctx:
                parts.append(ctx)
                parts.append(
                    "## 上下文使用边界\n"
                    "- 只有上方可见内容可以支撑 context_continuation。\n"
                    "- 延续任务时必须写出明确对象，不得使用无法解析的指代。\n"
                    "- 不得声称用户仍在做某事，除非上方最近对话明确支持。"
                )
            else:
                parts.append(
                    "## 无可见近期上下文\n"
                    "- topic_mode 不得使用 context_continuation。\n"
                    "- 不得猜测用户正在 debug、跑脚本、审包或处理某项任务。\n"
                    "- 不得说“那个包”“这包”“那个事”或其他依赖未知指代的表达。\n"
                    "- 有 Discovery 时作为完整新话题；没有合格话题时保持克制。"
                )
        except Exception:
            self.last_context_snapshot = {
                "queue_healthy": False,
                "context_prompt_eligible_count": 0,
                "context_visibility_error": True,
            }
            parts.append(
                "## 上下文不可用\n"
                "- topic_mode 不得使用 context_continuation。\n"
                "- 不得推断用户当前任务或使用未知指代。"
            )
        parts.append(
            "先规划 1–5 个独立 semantic acts，再为每个 act 生成一个完整气泡。"
            "默认使用最少必要数量；禁止为了像真人而凑数。"
        )
        parts.append(
            "只输出约定的 JSON 对象。不得输出 ---，不得把一段完整文字事后拆分。"
        )
        return "\n".join(parts)

    def _format_discovery(self, discovery_context: dict[str, Any]) -> list[str]:
        """Format discovery results into bullet points for the LLM prompt."""
        lines: list[str] = []
        external = discovery_context.get("external", [])
        local = discovery_context.get("local", [])

        for item in external:
            source = item.get("source", "")
            lane = item.get("lane", "current_affairs")
            publisher = item.get("publisher", "")
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
                f"- {id_prefix}[栏目={lane}] [来源={publisher or source}] {title}"
            )
            metadata = []
            if item.get("published_at"):
                metadata.append(f"发布时间={item['published_at']}")
            if item.get("url"):
                metadata.append(f"链接={item['url']}")
            if metadata:
                lines.append("  " + "；".join(metadata))
            if item.get("summary"):
                summary = str(item["summary"])
                if len(summary) > 1200:
                    summary = summary[:1197] + "..."
                lines.append(f"  摘要证据={summary}")
            if item.get("evidence_text"):
                evidence = str(item["evidence_text"])
                if len(evidence) > 5000:
                    evidence = evidence[:4997] + "..."
                lines.append(f"  页面正文证据={evidence}")
            elif item.get("evidence_status") == "metadata_only":
                lines.append("  页面正文未取得；不得推断标题和摘要之外的细节")

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
            "social_urge": "poke",
            "care": "care",
            "mischief": "casual",
            "curiosity": "self_talk",
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
