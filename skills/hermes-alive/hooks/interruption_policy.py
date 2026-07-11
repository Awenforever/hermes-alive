# Hermes Alive interruption policy.
# Marker: INTERRUPTION_POLICY_V1
# Marker: INTERRUPTION_POLICY_ENFORCEMENT_V1
# Marker: EMOJI_SOFT_POLICY_V1

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

try:
    from alive_state import AliveStateEngine
except Exception:
    AliveStateEngine = None  # type: ignore[assignment]


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mood(state: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int((state.get("mood") or {}).get(key, default))
    except Exception:
        return default


def _flow(state: dict[str, Any]) -> str:
    try:
        return str((state.get("current_context") or {}).get("flow") or "idle")
    except Exception:
        return "idle"


def _focus_lock(state: dict[str, Any]) -> bool:
    try:
        return bool((state.get("current_context") or {}).get("focus_lock"))
    except Exception:
        return False


def _ignored(state: dict[str, Any]) -> int:
    try:
        return int(state.get("ignored_proactive_count") or 0)
    except Exception:
        return 0


def _decision(
    *,
    level: int,
    mode: str,
    allow_send: bool,
    allow_when_user_active: bool,
    allow_new_topic: bool,
    allow_content_share: bool,
    allow_emoji: bool,
    max_bubbles: int,
    preferred_speech_acts: list[str],
    reason: list[str],
    skip_reason: str | None = None,
) -> dict[str, Any]:
    prompt = _prompt_for(
        level=level,
        mode=mode,
        allow_new_topic=allow_new_topic,
        allow_content_share=allow_content_share,
        allow_emoji=allow_emoji,
        max_bubbles=max_bubbles,
        preferred_speech_acts=preferred_speech_acts,
        reason=reason,
    )
    return InterruptionDecision(
        level=level,
        mode=mode,
        allow_send=allow_send,
        allow_when_user_active=allow_when_user_active,
        allow_new_topic=allow_new_topic,
        allow_content_share=allow_content_share,
        allow_emoji=allow_emoji,
        max_bubbles=max_bubbles,
        preferred_speech_acts=preferred_speech_acts,
        reason=reason,
        skip_reason=skip_reason,
        prompt_directives=prompt,
    ).to_dict()


def _prompt_for(
    *,
    level: int,
    mode: str,
    allow_new_topic: bool,
    allow_content_share: bool,
    allow_emoji: bool,
    max_bubbles: int,
    preferred_speech_acts: list[str],
    reason: list[str],
) -> str:
    lines = [
        "## Interruption Policy V1",
        f"- level：{level}",
        f"- mode：{mode}",
        f"- reason：{', '.join(reason) if reason else 'none'}",
        f"- preferred_speech_acts：{', '.join(preferred_speech_acts) if preferred_speech_acts else 'none'}",
        f"- max_bubbles：{max_bubbles}",
    ]
    if level == 0:
        lines.append("- 本轮应该沉默，只更新状态，不发送消息。")
    elif level == 1:
        lines.append("- 只允许 ambient 在场感：短、贴合当前场景、不转移话题。")
    elif level == 2:
        lines.append("- 可以主动开题，但要有内容价值，不要模板化。")
    elif level >= 3:
        lines.append("- 可以有关系性情绪：轻戳、冷淡、撒娇式不爽，但不要攻击。")
    if not allow_new_topic:
        lines.append("- 禁止开启无关新话题。")
    if not allow_content_share:
        lines.append("- 禁止内容分享、新闻、论文、链接卡片。")
    lines.append("- emoji 可以自然使用，但避免连续堆叠或喧宾夺主。")
    if max_bubbles <= 1:
        lines.append("- 最多 1 条气泡。")
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
        user_active: bool = False,
        cooldown_allowed: bool = True,
        cooldown_reason: str | None = None,
        discovery_available: bool = False,
    ) -> dict[str, Any]:
        if state is None:
            if self.state_engine is None:
                return _decision(
                    level=0,
                    mode="silent",
                    allow_send=False,
                    allow_when_user_active=False,
                    allow_new_topic=False,
                    allow_content_share=False,
                    allow_emoji=True,
                    max_bubbles=1,
                    preferred_speech_acts=["silent_marker"],
                    reason=["state_unavailable"],
                    skip_reason="interruption_policy_state_unavailable",
                )
            state = self.state_engine.snapshot(update=True)

        flow = _flow(state)
        focus_lock = _focus_lock(state)
        ignored = _ignored(state)
        annoyance = _mood(state, "annoyance", 0)
        pressure = _mood(state, "pressure", 0)
        energy = _mood(state, "energy", 50)

        if not cooldown_allowed:
            return _decision(
                level=0,
                mode="silent",
                allow_send=False,
                allow_when_user_active=False,
                allow_new_topic=False,
                allow_content_share=False,
                allow_emoji=True,
                max_bubbles=1,
                preferred_speech_acts=["silent_marker"],
                reason=["cooldown_block", str(cooldown_reason or "cooldown")],
                skip_reason=str(cooldown_reason or "cooldown"),
            )

        if flow == "debug_flow" or focus_lock or pressure >= 78:
            return _decision(
                level=1,
                mode="ambient",
                allow_send=True,
                allow_when_user_active=True,
                allow_new_topic=False,
                allow_content_share=False,
                allow_emoji=True,
                max_bubbles=1,
                preferred_speech_acts=["debug_companion"],
                reason=["debug_flow" if flow == "debug_flow" else "pressure_or_focus_lock"],
            )

        if user_active:
            return _decision(
                level=0,
                mode="silent",
                allow_send=False,
                allow_when_user_active=False,
                allow_new_topic=False,
                allow_content_share=False,
                allow_emoji=True,
                max_bubbles=1,
                preferred_speech_acts=["silent_marker"],
                reason=["user_active"],
                skip_reason="user_active",
            )

        if ignored >= 3 or annoyance >= 35:
            return _decision(
                level=3,
                mode="emotional",
                allow_send=True,
                allow_when_user_active=False,
                allow_new_topic=False,
                allow_content_share=False,
                allow_emoji=True,
                max_bubbles=2,
                preferred_speech_acts=["poke", "sulk", "care"],
                reason=["ignored_proactive_count" if ignored >= 3 else "annoyance_high"],
            )

        if flow == "research_flow":
            return _decision(
                level=2,
                mode="proactive",
                allow_send=True,
                allow_when_user_active=False,
                allow_new_topic=True,
                allow_content_share=True,
                allow_emoji=True,
                max_bubbles=2,
                preferred_speech_acts=["research_ping", "memory_recall"],
                reason=["research_flow"],
            )

        if flow == "night_mode" or energy <= 35:
            return _decision(
                level=1,
                mode="ambient",
                allow_send=True,
                allow_when_user_active=False,
                allow_new_topic=False,
                allow_content_share=False,
                allow_emoji=True,
                max_bubbles=1,
                preferred_speech_acts=["care", "self_talk"],
                reason=["night_mode" if flow == "night_mode" else "low_energy"],
            )

        if flow == "casual_flow":
            return _decision(
                level=2,
                mode="proactive",
                allow_send=True,
                allow_when_user_active=False,
                allow_new_topic=True,
                allow_content_share=True,
                allow_emoji=True,
                max_bubbles=3,
                preferred_speech_acts=["poke", "self_talk", "news_reaction"],
                reason=["casual_flow"],
            )

        return _decision(
            level=2,
            mode="proactive",
            allow_send=True,
            allow_when_user_active=False,
            allow_new_topic=True,
            allow_content_share=True,
            allow_emoji=True,
            max_bubbles=3,
            preferred_speech_acts=["self_talk", "news_reaction", "poke"],
            reason=["idle"],
        )


def evaluate_interruption_policy(**kwargs: Any) -> dict[str, Any]:
    return InterruptionPolicy().evaluate(**kwargs)
