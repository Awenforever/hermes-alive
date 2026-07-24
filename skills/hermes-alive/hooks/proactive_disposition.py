# Hermes Alive personality and emotion driven proactive disposition.
# Marker: HERMES_ALIVE_PROACTIVE_DISPOSITION_V1
# Marker: HERMES_ALIVE_IGNORED_COUNT_EVIDENCE_NOT_SWITCH_V1
# Marker: HERMES_ALIVE_ABSOLUTE_UNANSWERED_SAFETY_CEILING_V1
# Marker: HERMES_ALIVE_UNANSWERED_BUBBLE_CAP_V1

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ABSOLUTE_UNANSWERED_SAFETY_CEILING = 8


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except Exception:
        number = 0.0
    return max(low, min(high, number))


def _mood(state: dict[str, Any], key: str, default: float) -> float:
    try:
        return _clamp(float((state.get("mood") or {}).get(key, default)) / 100.0)
    except Exception:
        return _clamp(default / 100.0)


def _voice_value(voice: Any, key: str, default: float) -> float:
    try:
        return _clamp(getattr(voice, key))
    except Exception:
        return _clamp(default)


def _relationship_stage(voice: Any) -> str:
    try:
        value = str(getattr(voice, "relationship_stage") or "new").strip().lower()
    except Exception:
        value = "new"
    return value if value in {"new", "exploring", "familiar", "close"} else "new"


def _flow(state: dict[str, Any]) -> str:
    try:
        return str((state.get("current_context") or {}).get("flow") or "idle")
    except Exception:
        return "idle"


def _context_fresh(state: dict[str, Any]) -> bool:
    try:
        value = (state.get("current_context") or {}).get("context_fresh")
        return True if value is None else bool(value)
    except Exception:
        return False


def _focus_lock(state: dict[str, Any]) -> bool:
    try:
        return bool((state.get("current_context") or {}).get("focus_lock"))
    except Exception:
        return False


def _ignored_raw(state: dict[str, Any]) -> int:
    try:
        return max(0, int(state.get("ignored_proactive_count") or 0))
    except Exception:
        return 0


def _unanswered_pressure(state: dict[str, Any], ignored_raw: int) -> float:
    evidence = state.get("interaction_evidence")
    if isinstance(evidence, dict):
        value = evidence.get("unanswered_pressure")
        if value is not None:
            return _clamp(value)
    return _clamp(ignored_raw / 4.0)


def _interaction_temperature(state: dict[str, Any]) -> float:
    evidence = state.get("interaction_evidence")
    if not isinstance(evidence, dict):
        return 0.5
    engagement = _clamp(evidence.get("engagement_signal", 0.5))
    presence = _clamp(evidence.get("presence_signal", 0.5))
    return _clamp(engagement * 0.65 + presence * 0.35)


@dataclass
class ProactiveDisposition:
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
    willingness: float
    restraint: float
    threshold: float
    unanswered_pressure: float
    interaction_temperature: float
    decision_model: str = "personality_disposition_v1"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["willingness"] = round(self.willingness, 4)
        payload["restraint"] = round(self.restraint, 4)
        payload["threshold"] = round(self.threshold, 4)
        payload["unanswered_pressure"] = round(self.unanswered_pressure, 4)
        payload["interaction_temperature"] = round(self.interaction_temperature, 4)
        return payload


def _silent(
    *,
    reason: list[str],
    skip_reason: str,
    willingness: float,
    restraint: float,
    threshold: float,
    unanswered_pressure: float,
    interaction_temperature: float,
) -> ProactiveDisposition:
    return ProactiveDisposition(
        level=0,
        mode="silent",
        allow_send=False,
        allow_when_user_active=False,
        allow_new_topic=False,
        allow_content_share=False,
        allow_emoji=True,
        max_bubbles=1,
        preferred_speech_acts=["silent_marker"],
        reason=reason,
        skip_reason=skip_reason,
        willingness=willingness,
        restraint=restraint,
        threshold=threshold,
        unanswered_pressure=unanswered_pressure,
        interaction_temperature=interaction_temperature,
    )


def _max_bubbles(
    *,
    willingness: float,
    verbosity: float,
    curiosity: float,
    discovery_available: bool,
    relationship_stage: str,
    quirkiness: float,
) -> int:
    # This is only an upper bound. The semantic planner must still choose the
    # minimum number of bubbles needed for the actual speech acts.
    count = 1
    if willingness >= 0.52:
        count += 1
    if verbosity >= 0.62:
        count += 1
    if discovery_available and curiosity >= 0.62:
        count += 1
    if (
        willingness >= 0.78
        and relationship_stage in {"familiar", "close"}
        and quirkiness >= 0.55
    ):
        count += 1
    return max(1, min(5, count))


def evaluate_proactive_disposition(
    *,
    state: dict[str, Any],
    voice: Any | None = None,
    social_urge: float | None = None,
    user_active: bool = False,
    cooldown_allowed: bool = True,
    cooldown_reason: str | None = None,
    discovery_available: bool = False,
) -> dict[str, Any]:
    ignored_raw = _ignored_raw(state)
    unanswered = _unanswered_pressure(state, ignored_raw)
    interaction_temperature = _interaction_temperature(state)

    flow = _flow(state)
    focus_lock = _focus_lock(state)
    context_fresh = _context_fresh(state)

    energy = _mood(state, "energy", 50)
    boredom = _mood(state, "boredom", 20)
    annoyance = _mood(state, "annoyance", 0)
    affection = _mood(state, "affection", 65)
    mood_curiosity = _mood(state, "curiosity", 50)
    pressure = _mood(state, "pressure", 0)

    voice_curiosity = _voice_value(voice, "curiosity", 0.5)
    warmth = _voice_value(voice, "warmth", 0.5)
    verbosity = _voice_value(voice, "verbosity", 0.5)
    quirkiness = _voice_value(voice, "quirkiness", 0.3)
    relationship_stage = _relationship_stage(voice)
    social = _clamp(
        social_urge
        if social_urge is not None
        else (voice_curiosity * 0.55 + warmth * 0.45)
    )

    base = (
        0.12
        + 0.26 * social
        + 0.11 * voice_curiosity
        + 0.07 * warmth
        + 0.04 * quirkiness
        + 0.09 * mood_curiosity
        + 0.07 * affection
        + 0.05 * boredom
        + 0.06 * interaction_temperature
    )

    if flow == "research_flow":
        base += 0.11
    elif flow == "casual_flow":
        base += 0.08
    elif flow == "debug_flow":
        base -= 0.08
    elif flow == "night_mode":
        base -= 0.06

    if discovery_available:
        base += 0.35 + 0.06 * voice_curiosity

    restraint = (
        0.33 * unanswered
        + 0.15 * annoyance
        + 0.17 * pressure
        + 0.10 * (1.0 - energy)
        + (0.10 if focus_lock else 0.0)
        + (0.06 if flow == "night_mode" else 0.0)
    )
    willingness = _clamp(base - restraint)
    threshold = _clamp(0.40 + 0.11 * unanswered - 0.05 * social, 0.30, 0.62)

    if not cooldown_allowed:
        return _silent(
            reason=["cooldown_block", str(cooldown_reason or "cooldown")],
            skip_reason=str(cooldown_reason or "cooldown"),
            willingness=willingness,
            restraint=restraint,
            threshold=threshold,
            unanswered_pressure=unanswered,
            interaction_temperature=interaction_temperature,
        ).to_dict()

    # Hard safety ceiling only. Personality and discovery may vary normal
    # behavior below this point, but they must never justify endless
    # persistence after repeated non-response.
    if ignored_raw >= ABSOLUTE_UNANSWERED_SAFETY_CEILING:
        reason = ["safety_unanswered_ceiling"]
        if discovery_available:
            reason.append("discovery_deferred_after_persistent_nonresponse")
        return _silent(
            reason=reason,
            skip_reason="safety_unanswered_ceiling",
            willingness=willingness,
            restraint=restraint,
            threshold=threshold,
            unanswered_pressure=unanswered,
            interaction_temperature=interaction_temperature,
        ).to_dict()

    if (
        context_fresh
        and (flow == "debug_flow" or focus_lock or pressure >= 0.78)
        and unanswered <= 0.05
    ):
        return ProactiveDisposition(
            level=1,
            mode="ambient",
            allow_send=True,
            allow_when_user_active=True,
            allow_new_topic=False,
            allow_content_share=False,
            allow_emoji=True,
            max_bubbles=1,
            preferred_speech_acts=["debug_companion"],
            reason=["fresh_active_workflow", "personality_disposition"],
            skip_reason=None,
            willingness=max(willingness, threshold),
            restraint=restraint,
            threshold=threshold,
            unanswered_pressure=unanswered,
            interaction_temperature=interaction_temperature,
        ).to_dict()

    if user_active:
        return _silent(
            reason=["user_active"],
            skip_reason="user_active",
            willingness=willingness,
            restraint=restraint,
            threshold=threshold,
            unanswered_pressure=unanswered,
            interaction_temperature=interaction_temperature,
        ).to_dict()

    if unanswered <= 0.05 and (
        flow == "night_mode" or energy <= 0.35
    ):
        return ProactiveDisposition(
            level=1,
            mode="ambient",
            allow_send=True,
            allow_when_user_active=False,
            allow_new_topic=False,
            allow_content_share=False,
            allow_emoji=True,
            max_bubbles=1,
            preferred_speech_acts=["care", "self_talk"],
            reason=[
                "night_mode"
                if flow == "night_mode"
                else "low_energy"
            ],
            skip_reason=None,
            willingness=max(willingness, threshold),
            restraint=restraint,
            threshold=threshold,
            unanswered_pressure=unanswered,
            interaction_temperature=interaction_temperature,
        ).to_dict()

    if willingness < threshold:
        reason = ["personality_restraint"]
        if unanswered > 0:
            reason.append("unanswered_evidence")
        if annoyance >= 0.35:
            reason.append("annoyance_high")
        if pressure >= 0.65:
            reason.append("pressure_high")
        if discovery_available:
            reason.append("discovery_not_enough_to_interrupt")
        if ignored_raw >= 2:
            skip_reason = "unanswered_budget_exhausted"
        elif ignored_raw >= 1 and not discovery_available:
            skip_reason = "unanswered_no_novel_value"
        else:
            skip_reason = "personality_disposition_silent"
        return _silent(
            reason=reason,
            skip_reason=skip_reason,
            willingness=willingness,
            restraint=restraint,
            threshold=threshold,
            unanswered_pressure=unanswered,
            interaction_temperature=interaction_temperature,
        ).to_dict()

    max_bubbles = _max_bubbles(
        willingness=willingness,
        verbosity=verbosity,
        curiosity=max(voice_curiosity, mood_curiosity),
        discovery_available=discovery_available,
        relationship_stage=relationship_stage,
        quirkiness=quirkiness,
    )

    if unanswered > 0.0 and discovery_available:
        mode = "novel_value"
        level = 2
        allow_new_topic = True
        allow_content_share = True
        preferred = ["discovery_intro", "fact", "reaction", "source_link"]
        reason = [
            "unanswered_evidence",
            "fresh_discovery_available",
            "personality_willingness_above_threshold",
        ]
    elif flow == "research_flow":
        mode = "proactive"
        level = 2
        allow_new_topic = True
        allow_content_share = True
        preferred = ["research_ping", "fact", "question", "source_link"]
        reason = ["research_flow", "personality_willingness_above_threshold"]
    elif flow == "night_mode" or energy <= 0.35:
        mode = "ambient"
        level = 1
        allow_new_topic = False
        allow_content_share = False
        preferred = ["self_talk", "care"]
        max_bubbles = 1
        reason = ["night_mode" if flow == "night_mode" else "low_energy"]
    elif annoyance >= 0.35:
        mode = "reserved"
        level = 1
        allow_new_topic = bool(discovery_available)
        allow_content_share = bool(discovery_available)
        preferred = ["dry_observation", "self_talk", "discovery_intro"]
        max_bubbles = min(max_bubbles, 2)
        reason = ["annoyance_present", "still_willing_to_speak"]
    else:
        mode = "proactive"
        level = 2
        allow_new_topic = True
        allow_content_share = True
        preferred = ["self_talk", "observation", "question", "discovery_intro"]
        if flow == "casual_flow":
            max_bubbles = max(3, max_bubbles)
            reason = [
                "casual_flow",
                "personality_willingness_above_threshold",
            ]
        else:
            reason = ["personality_willingness_above_threshold"]

    # Unanswered pressure limits burst size even when personality still
    # chooses to speak. This is an upper bound, not a required bubble count.
    if unanswered >= 0.75:
        max_bubbles = min(max_bubbles, 2)
    elif unanswered >= 0.45:
        max_bubbles = min(max_bubbles, 3)

    return ProactiveDisposition(
        level=level,
        mode=mode,
        allow_send=True,
        allow_when_user_active=False,
        allow_new_topic=allow_new_topic,
        allow_content_share=allow_content_share,
        allow_emoji=True,
        max_bubbles=max_bubbles,
        preferred_speech_acts=preferred,
        reason=reason,
        skip_reason=None,
        willingness=willingness,
        restraint=restraint,
        threshold=threshold,
        unanswered_pressure=unanswered,
        interaction_temperature=interaction_temperature,
    ).to_dict()
