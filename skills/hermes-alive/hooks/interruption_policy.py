# Hermes Alive interruption policy.
# Marker: INTERRUPTION_POLICY_V1
# Marker: INTERRUPTION_POLICY_ENFORCEMENT_V1
# Marker: EMOJI_SOFT_POLICY_V1
# Marker: HERMES_ALIVE_UNANSWERED_DISCOVERY_PIVOT_V2
# Marker: HERMES_ALIVE_CONTEXT_FRESHNESS_V2
# Marker: HERMES_ALIVE_PERSONALITY_DISPOSITION_INTEGRATION_V1

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

try:
    from alive_state import AliveStateEngine
except Exception:
    AliveStateEngine = None  # type: ignore[assignment]

from proactive_disposition import evaluate_proactive_disposition


@dataclass
class InterruptionDecision:
    level: int
    mode: str
    allow_send: bool
    allow_when_user_active: bool
    allow_new_topic: bool
    allow_content_share: bool
    allow_emoji: bool
    max_bubbles: int
    preferred_speech_acts: list[str]
    reason: list[str]
    skip_reason: str | None
    prompt_directives: str
    disposition: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _prompt_for(disposition: dict[str, Any]) -> str:
    level = int(disposition.get("level") or 0)
    mode = str(disposition.get("mode") or "silent")
    reason = disposition.get("reason")
    if not isinstance(reason, list):
        reason = []
    acts = disposition.get("preferred_speech_acts")
    if not isinstance(acts, list):
        acts = []
    max_bubbles = max(
        1,
        min(5, int(disposition.get("max_bubbles") or 1)),
    )

    lines = [
        "## Personality Disposition V1",
        f"- level：{level}",
        f"- mode：{mode}",
        f"- reason：{', '.join(str(item) for item in reason) if reason else 'none'}",
        f"- preferred_speech_acts：{', '.join(str(item) for item in acts) if acts else 'none'}",
        f"- bubble_upper_bound：{max_bubbles}",
        f"- willingness：{float(disposition.get('willingness') or 0.0):.3f}",
        f"- restraint：{float(disposition.get('restraint') or 0.0):.3f}",
        f"- unanswered_pressure：{float(disposition.get('unanswered_pressure') or 0.0):.3f}",
        "- 未回复次数只是关系证据，不是固定开关。",
        "- 普通入站只更新互动证据，不应被描述为机械清零。",
        "- 气泡数量必须按语义需要在 1–5 条内选择，默认使用最少必要数量。",
        "- 必须先规划独立 semantic acts，再分别生成气泡；禁止把一段完整文本事后切开。",
    ]

    if level == 0:
        lines.append("- 本轮保持沉默，只更新状态。")
    elif mode == "novel_value":
        lines.extend([
            "- 旧话题已经结束。本轮只能开启一个新的、有明确价值的 Discovery 话题。",
            "- 第一条气泡必须直接锚定新发现，不得假装延续用户经历或共同回忆。",
            "- 每条气泡必须承担不同的话语功能；不需要多条时只发一条。",
        ])
    elif level == 1:
        lines.append("- 表达应克制、短、贴合当前状态，不制造压力。")
    else:
        lines.append("- 可以主动开题，但人格与情绪只影响倾向，不能绕过安全频控。")

    if not bool(disposition.get("allow_new_topic", False)):
        lines.append("- 禁止开启无关新话题。")
    if not bool(disposition.get("allow_content_share", False)):
        lines.append("- 禁止内容分享、新闻、论文和链接。")
    lines.append("- emoji 可以自然使用，但不要堆叠。")
    return "\n".join(lines)


class InterruptionPolicy:
    def __init__(self, state_engine: Any | None = None) -> None:
        if state_engine is not None:
            self.state_engine = state_engine
        elif AliveStateEngine is not None:
            self.state_engine = AliveStateEngine()
        else:
            self.state_engine = None

    def evaluate(
        self,
        *,
        state: dict[str, Any] | None = None,
        voice: Any | None = None,
        social_urge: float | None = None,
        user_active: bool = False,
        cooldown_allowed: bool = True,
        cooldown_reason: str | None = None,
        discovery_available: bool = False,
    ) -> dict[str, Any]:
        if state is None:
            if self.state_engine is None:
                state = {
                    "ignored_proactive_count": 0,
                    "mood": {},
                    "current_context": {
                        "flow": "idle",
                        "focus_lock": False,
                        "context_fresh": False,
                    },
                    "interaction_evidence": {
                        "unanswered_pressure": 1.0,
                        "presence_signal": 0.0,
                        "engagement_signal": 0.0,
                    },
                }
            else:
                state = self.state_engine.snapshot(update=True)

        disposition = evaluate_proactive_disposition(
            state=state,
            voice=voice,
            social_urge=social_urge,
            user_active=user_active,
            cooldown_allowed=cooldown_allowed,
            cooldown_reason=cooldown_reason,
            discovery_available=discovery_available,
        )
        prompt = _prompt_for(disposition)

        return InterruptionDecision(
            level=int(disposition.get("level") or 0),
            mode=str(disposition.get("mode") or "silent"),
            allow_send=bool(disposition.get("allow_send")),
            allow_when_user_active=bool(
                disposition.get("allow_when_user_active")
            ),
            allow_new_topic=bool(
                disposition.get("allow_new_topic")
            ),
            allow_content_share=bool(
                disposition.get("allow_content_share")
            ),
            allow_emoji=bool(
                disposition.get("allow_emoji", True)
            ),
            max_bubbles=max(
                1,
                min(5, int(disposition.get("max_bubbles") or 1)),
            ),
            preferred_speech_acts=[
                str(item)
                for item in (
                    disposition.get("preferred_speech_acts")
                    or []
                )
            ],
            reason=[
                str(item)
                for item in (disposition.get("reason") or [])
            ],
            skip_reason=(
                str(disposition.get("skip_reason"))
                if disposition.get("skip_reason")
                else None
            ),
            prompt_directives=prompt,
            disposition=dict(disposition),
        ).to_dict()


def evaluate_interruption_policy(**kwargs: Any) -> dict[str, Any]:
    return InterruptionPolicy().evaluate(**kwargs)
