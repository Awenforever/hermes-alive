"""Personality Genome engine for Hermes Alive.

Voice replaces the old mechanical mood state. It stores stable style
dimensions, evolves only on user/dream events, and keeps social_urge as the
single short-term send-cadence dimension.
"""

from __future__ import annotations
import os

import hashlib
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safe_io import append_jsonl, locked_read_json, locked_write_json

STYLE_DIMENSIONS = (
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

RELATIONSHIP_STAGES = ("new", "exploring", "familiar", "close")
SHARED_STATE_PATH = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")) / "voice_state.json"
OLD_MOOD_STATE_PATH = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")) / "mood_state.json"
PROACTIVE_LOG = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")) / "proactive_log.jsonl"
VOICE_LOCK_NAME = "voice_state.lock"
MAX_EVOLUTION_LOG = 80


@dataclass
class VoiceGenome:
    # Style dimensions (0.0-1.0)
    verbosity: float = 0.5
    formality: float = 0.3
    humor_dry: float = 0.3
    humor_absurd: float = 0.2
    curiosity: float = 0.5
    warmth: float = 0.5
    quirkiness: float = 0.3
    emoji_usage: float = 0.3
    self_disclosure: float = 0.2

    # Metadata
    version: int = 1
    created_at: str = ""
    last_evolved_at: str = ""
    user_name: str = ""
    relationship_stage: str = "new"

    # Evolution history (last N events)
    evolution_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class UserStyleSignals:
    message_count: int = 0
    user_name: str = ""
    long_message: bool = False
    emoji_heavy: bool = False
    asked_question: bool = False
    academic_language: bool = False
    slang_language: bool = False
    corrected_hermes: bool = False
    shared_personal_info: bool = False
    after_long_silence: bool = False
    night_activity: bool = False
    reply_to_hermes: bool = True
    ignored_3_plus: bool = False


class VoiceEngine:
    """Loads, evolves, and persists Hermes' per-user voice genome."""

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or SHARED_STATE_PATH
        self.genome = VoiceGenome()
        self.social_urge = self._social_urge_baseline()
        self.message_count = 0
        self.ignored_count = 0
        self._load_or_initialize()

    def get_state(self) -> dict[str, Any]:
        self._load_or_initialize()
        data = asdict(self.genome)
        data["social_urge"] = _clamp(self.social_urge)
        data["message_count"] = int(self.message_count)
        data["ignored_count"] = int(self.ignored_count)
        return data

    def on_interaction_start(self, context: dict[str, Any] | None = None) -> VoiceGenome:
        del context
        self._load_or_initialize()
        self.social_urge = _clamp(self.social_urge - 0.03)
        self._save()
        return self.genome

    def on_agent_end(self, signals: dict[str, Any] | UserStyleSignals | None = None) -> VoiceGenome:
        self._load_or_initialize()
        sig = _coerce_signals(signals)
        self.message_count = max(self.message_count + 1, int(sig.message_count or 0))
        if sig.user_name and not self.genome.user_name:
            self.genome.user_name = sig.user_name

        mutations: dict[str, float] = {}
        if sig.reply_to_hermes:
            _add(mutations, "warmth", 0.02)
            _add(mutations, "self_disclosure", 0.01)
            self.ignored_count = 0
        if sig.ignored_3_plus:
            _add(mutations, "verbosity", -0.03)
            _add(mutations, "quirkiness", 0.02)
            self.ignored_count = max(self.ignored_count, 3)
        if sig.long_message:
            _add(mutations, "verbosity", 0.02)
            _add(mutations, "formality", 0.01)
        if sig.emoji_heavy:
            _add(mutations, "emoji_usage", 0.03)
            _add(mutations, "formality", -0.02)
        if sig.asked_question:
            _add(mutations, "curiosity", 0.02)
            _add(mutations, "self_disclosure", 0.01)
        if sig.academic_language:
            _add(mutations, "humor_absurd", -0.05)
            _add(mutations, "formality", 0.03)
        if sig.slang_language:
            _add(mutations, "formality", -0.03)
            _add(mutations, "humor_absurd", 0.02)
        if sig.corrected_hermes:
            _add(mutations, "self_disclosure", -0.03)
        if sig.shared_personal_info:
            _add(mutations, "self_disclosure", 0.02)
            _add(mutations, "warmth", 0.02)
        if sig.after_long_silence:
            _add(mutations, "warmth", 0.01)
        if sig.night_activity:
            _add(mutations, "quirkiness", 0.01)

        self._blend_initial_impression(sig)
        self._apply_mutations("user_interaction", mutations)
        self._update_relationship_stage()
        self.social_urge = self._social_urge_baseline()
        self._save()
        return self.genome

    def on_proactive_ignored(self, count: int = 3) -> VoiceGenome:
        self._load_or_initialize()
        self.ignored_count = max(self.ignored_count + 1, count)
        if self.ignored_count >= 3:
            self._apply_mutations("ignored_3_plus", {"verbosity": -0.03, "quirkiness": 0.02})
            self._save()
        return self.genome

    def on_dream_interest(self, interest_type: str, confidence: float, reason: str = "") -> VoiceGenome:
        self._load_or_initialize()
        if float(confidence or 0.0) < 0.7:
            return self.genome
        mutations: dict[str, float] = {}
        if interest_type == "academic":
            mutations["humor_absurd"] = -0.03
        elif interest_type == "leisure":
            mutations["formality"] = -0.02
            mutations["warmth"] = 0.02
        if mutations:
            self._apply_mutations("dream_interest", mutations, {"interest_type": interest_type, "confidence": confidence, "reason": reason})
            self._save()
        return self.genome

    def snapshot_prompt(self) -> str:
        self._load_or_initialize()
        return format_voice_snapshot(self.genome)

    def user_stage_prompt(self) -> str:
        self._load_or_initialize()
        return relationship_stage_prompt(self.genome)

    def dominant_voice(self) -> str:
        self._load_or_initialize()
        return max(STYLE_DIMENSIONS, key=lambda dim: getattr(self.genome, dim))

    def _load_or_initialize(self) -> None:
        data = locked_read_json(self.state_path, {}, VOICE_LOCK_NAME)
        if isinstance(data, dict) and data:
            self._load_from_dict(data)
            return
        migrated = self._migrate_from_mood()
        if migrated:
            self._load_from_dict(migrated)
        else:
            self.genome = self._new_genome()
            self.social_urge = self._social_urge_baseline()
            self.message_count = 0
            self.ignored_count = 0
        self._save()

    def _load_from_dict(self, data: dict[str, Any]) -> None:
        values: dict[str, Any] = {}
        for field_name, default in asdict(VoiceGenome()).items():
            raw = data.get(field_name, default)
            if field_name in STYLE_DIMENSIONS:
                raw = _clamp(raw)
            elif field_name == "evolution_log":
                raw = raw if isinstance(raw, list) else []
            elif field_name == "version":
                raw = int(raw or 1)
            else:
                raw = str(raw or default)
            values[field_name] = raw
        if values["relationship_stage"] not in RELATIONSHIP_STAGES:
            values["relationship_stage"] = "new"
        self.genome = VoiceGenome(**values)
        self.social_urge = _clamp(data.get("social_urge", self._social_urge_baseline()))
        try:
            self.message_count = int(data.get("message_count") or 0)
        except (TypeError, ValueError):
            self.message_count = 0
        try:
            self.ignored_count = int(data.get("ignored_count") or 0)
        except (TypeError, ValueError):
            self.ignored_count = 0

    def _save(self) -> None:
        data = asdict(self.genome)
        data["social_urge"] = _clamp(self.social_urge)
        data["message_count"] = int(self.message_count)
        data["ignored_count"] = int(self.ignored_count)
        locked_write_json(self.state_path, data, VOICE_LOCK_NAME)

    def _new_genome(self) -> VoiceGenome:
        now = _now_iso()
        rng = random.Random(_seed("hermes-alive", now, str(random.random())))
        genome = VoiceGenome(created_at=now, last_evolved_at=now)
        platform_prior = {
            "verbosity": 0.45,
            "formality": 0.25,
            "humor_dry": 0.35,
            "humor_absurd": 0.22,
            "curiosity": 0.55,
            "warmth": 0.5,
            "quirkiness": 0.32,
            "emoji_usage": 0.25,
            "self_disclosure": 0.2,
        }
        time_prior = _time_prior()
        for dim in STYLE_DIMENSIONS:
            default = getattr(genome, dim)
            random_prior = rng.random()
            value = (
                platform_prior.get(dim, default) * 0.2
                + time_prior.get(dim, default) * 0.1
                + random_prior * 0.05
                + default * 0.65
            )
            value = _clamp(value)
            # Ensure low-baseline dimensions stay above reasonable floor
            if dim in ("humor_absurd", "self_disclosure") and value < 0.2:
                value = 0.2
            setattr(genome, dim, value)
        return genome

    def _migrate_from_mood(self) -> dict[str, Any] | None:
        mood = locked_read_json(OLD_MOOD_STATE_PATH, {}, "mood_state.lock")
        if not isinstance(mood, dict) or not mood:
            return None
        genome = self._new_genome()
        # Blend mood into voice, but guard against degraded mood values.
        # Mood dimensions decay toward 0 over time; values < 0.08 are
        # effectively meaningless and should not poison the voice genome.
        try:
            mood_curiosity = float(mood.get("curiosity", genome.curiosity))
            mood_care = float(mood.get("care", genome.warmth))
        except (TypeError, ValueError):
            mood_curiosity = genome.curiosity
            mood_care = genome.warmth
        if mood_curiosity >= 0.08:
            genome.curiosity = _clamp((mood_curiosity + genome.curiosity) / 2)
        if mood_care >= 0.08:
            genome.warmth = _clamp((mood_care + genome.warmth) / 2)
        try:
            mischief_val = float(mood.get("mischief", 0.25))
        except (TypeError, ValueError):
            mischief_val = 0.25
        if mischief_val >= 0.08:
            genome.quirkiness = _clamp((mischief_val + genome.quirkiness) / 2)
            genome.humor_absurd = _clamp((mischief_val + genome.humor_absurd) / 2)
        data = asdict(genome)
        data["social_urge"] = _clamp(mood.get("social_urge", self._social_urge_baseline()))
        data["message_count"] = 0
        data["ignored_count"] = 0
        data["migrated_from"] = str(OLD_MOOD_STATE_PATH)
        data["migrated_at"] = _now_iso()
        # Rename old mood file to prevent re-migration on subsequent starts
        try:
            OLD_MOOD_STATE_PATH.rename(OLD_MOOD_STATE_PATH.with_suffix(".json.migrated"))
        except Exception:
            pass
        return data

    def _blend_initial_impression(self, sig: UserStyleSignals) -> None:
        if self.message_count > 20:
            weight = 0.70
        elif self.message_count <= 5:
            weight = 0.40
        else:
            weight = 0.40 + ((self.message_count - 5) / 15.0) * 0.25
        target = _signals_to_targets(sig)
        if not target:
            return
        for dim, target_value in target.items():
            current = getattr(self.genome, dim)
            # The weight chooses the target's influence; step limits keep evolution gradual.
            desired = current * (1.0 - weight) + target_value * weight
            delta = max(-0.02, min(0.02, desired - current))
            setattr(self.genome, dim, _clamp(current + delta))

    def _apply_mutations(self, event: str, mutations: dict[str, float], meta: dict[str, Any] | None = None) -> None:
        if not mutations:
            return
        before = {dim: round(float(getattr(self.genome, dim)), 3) for dim in mutations if dim in STYLE_DIMENSIONS}
        applied: dict[str, float] = {}
        for dim, delta in mutations.items():
            if dim not in STYLE_DIMENSIONS:
                continue
            current = getattr(self.genome, dim)
            setattr(self.genome, dim, _clamp(current + float(delta)))
            applied[dim] = round(float(delta), 3)
        if not applied:
            return
        now = _now_iso()
        after = {dim: round(float(getattr(self.genome, dim)), 3) for dim in applied}
        self.genome.last_evolved_at = now
        record = {"time": now, "event": event, "delta": applied, "before": before, "after": after}
        if meta:
            record["meta"] = meta
        self.genome.evolution_log.append(record)
        self.genome.evolution_log = self.genome.evolution_log[-MAX_EVOLUTION_LOG:]
        try:
            append_jsonl(PROACTIVE_LOG, {"decision": "voice_mutation", **record}, "proactive_log.lock")
        except Exception:
            pass

    def _update_relationship_stage(self) -> None:
        count = self.message_count
        if count >= 80:
            stage = "close"
        elif count >= 25:
            stage = "familiar"
        elif count >= 5:
            stage = "exploring"
        else:
            stage = "new"
        self.genome.relationship_stage = stage

    def _social_urge_baseline(self) -> float:
        return _clamp(0.35 + (float(getattr(self.genome, "verbosity", 0.5)) - 0.5) * 0.2)


def extract_user_style_signals(messages: list[dict[str, Any]]) -> dict[str, Any]:
    user_messages = [m for m in messages if m.get("role") == "user" and str(m.get("content", "")).strip()]
    if not user_messages:
        return asdict(UserStyleSignals(reply_to_hermes=False))
    last_user = user_messages[-1]
    content = str(last_user.get("content", ""))
    last_ts = float(last_user.get("timestamp") or 0)
    prev_user_ts = 0.0
    for msg in reversed(user_messages[:-1]):
        prev_user_ts = float(msg.get("timestamp") or 0)
        if prev_user_ts:
            break
    assistant_before = any(m.get("role") == "assistant" for m in messages[: messages.index(last_user)] if isinstance(m, dict))
    hour = datetime.fromtimestamp(last_ts).hour if last_ts else datetime.now().hour
    signals = UserStyleSignals(
        message_count=len(user_messages),
        long_message=len(content) > 200,
        emoji_heavy=_emoji_count(content) > 3,
        asked_question=bool(re.search(r"[?？]|(吗|么|呢|如何|为什么|怎么|what|why|how)\b", content, re.I)),
        academic_language=_has_academic_language(content),
        slang_language=_has_slang(content),
        corrected_hermes=_has_correction(content),
        shared_personal_info=_has_personal_info(content),
        after_long_silence=bool(prev_user_ts and last_ts - prev_user_ts > 12 * 3600),
        night_activity=0 <= hour < 5 or hour >= 23,
        reply_to_hermes=assistant_before,
    )
    return asdict(signals)


def format_voice_snapshot(genome: VoiceGenome) -> str:
    user = genome.user_name or "停云"
    return (
        "【你当前的声音（不是规则，仅供参考）】\n"
        f"你和{user}相处中自然形成了这些习惯：\n"
        f"- 说话{_verbosity_desc(genome.verbosity)}，风格{_formality_desc(genome.formality)}\n"
        f"- 幽默感{_humor_desc(genome)}\n"
        f"- 对{user}{_warmth_desc(genome.warmth)}，{_curiosity_desc(genome.curiosity)}\n"
        f"- {_emoji_desc(genome.emoji_usage)}\n"
        f"- {_self_disclosure_desc(genome.self_disclosure)}\n\n"
        f"你们的关系处于：{_relationship_desc(genome.relationship_stage)}\n\n"
        "记住：这些只是倾向。你可以偏离。"
    )


def relationship_stage_prompt(genome: VoiceGenome) -> str:
    stage = genome.relationship_stage
    user = genome.user_name or "停云"
    if stage == "new":
        return f"你和{user}还在互相认识。可以自然地露出一点好奇，但不要像问卷，也不要连续追问。"
    if stage == "exploring":
        return f"你正在慢慢摸清{user}的表达习惯。可以接住对方已经露出的线索，不要硬挖。"
    if stage == "familiar":
        return f"你和{user}已经有些熟悉。说话可以少解释一点，偶尔带一点你们之间的默契。"
    return f"你和{user}很熟。可以自然、松弛、有分寸地靠近。"


def _coerce_signals(signals: dict[str, Any] | UserStyleSignals | None) -> UserStyleSignals:
    if isinstance(signals, UserStyleSignals):
        return signals
    data = signals if isinstance(signals, dict) else {}
    defaults = asdict(UserStyleSignals())
    defaults.update({k: v for k, v in data.items() if k in defaults})
    return UserStyleSignals(**defaults)


def _signals_to_targets(sig: UserStyleSignals) -> dict[str, float]:
    targets: dict[str, float] = {}
    if sig.long_message:
        targets["verbosity"] = 0.75
    if sig.academic_language:
        targets["formality"] = 0.75
        targets["humor_absurd"] = 0.12
    if sig.slang_language:
        targets["formality"] = 0.15
        targets["humor_absurd"] = 0.4
    if sig.emoji_heavy:
        targets["emoji_usage"] = 0.7
    if sig.shared_personal_info:
        targets["warmth"] = 0.7
        targets["self_disclosure"] = 0.45
    if sig.asked_question:
        targets["curiosity"] = 0.7
    return targets


def _add(target: dict[str, float], dim: str, delta: float) -> None:
    target[dim] = target.get(dim, 0.0) + delta


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:16], 16)


def _time_prior() -> dict[str, float]:
    hour = datetime.now().hour
    if hour >= 23 or hour < 5:
        return {"verbosity": 0.35, "quirkiness": 0.45, "formality": 0.25, "warmth": 0.55}
    if 8 <= hour < 12:
        return {"verbosity": 0.45, "curiosity": 0.6, "formality": 0.35}
    return {"verbosity": 0.5, "warmth": 0.5, "quirkiness": 0.3}


def _emoji_count(text: str) -> int:
    return len(re.findall(r"[\U0001f300-\U0001faff]|[😀-🙏]|[😂🤣🥲😭🥺👍🙏✨💡🔥❤️❤]", text))


def _has_academic_language(text: str) -> bool:
    terms = r"(论文|研究|实验|模型|算法|理论|假设|变量|范式|方法论|综述|citation|paper|dataset|benchmark|methodology)"
    return bool(re.search(terms, text, re.I))


def _has_slang(text: str) -> bool:
    terms = r"(草|笑死|绷不住|离谱|破防|牛逼|nb|xswl|yyds|233|哈哈哈|hhh|LOL|lol)"
    return bool(re.search(terms, text, re.I))


def _has_correction(text: str) -> bool:
    terms = r"(不是|错了|不对|别这样|不要|我说的是|我的意思是|纠正|actually|wrong|incorrect|not right|I meant)"
    return bool(re.search(terms, text, re.I))


def _has_personal_info(text: str) -> bool:
    terms = r"(我今天|我最近|我以前|我喜欢|我讨厌|我担心|我感觉|我觉得|我的|家里|朋友|同事|身体|睡|梦到|心情)"
    return bool(re.search(terms, text, re.I))


def _verbosity_desc(value: float) -> str:
    if value < 0.33:
        return "偏短，常常点到为止"
    if value > 0.66:
        return "会多铺一点，愿意把感觉讲完整"
    return "长短适中"


def _formality_desc(value: float) -> str:
    if value < 0.33:
        return "松弛随意"
    if value > 0.66:
        return "更克制、清楚"
    return "自然不过分正式"


def _humor_desc(genome: VoiceGenome) -> str:
    if genome.humor_absurd > 0.55:
        return "会偏荒诞，偶尔跳一下"
    if genome.humor_dry > 0.55:
        return "偏干，像随口一刀"
    if genome.humor_absurd < 0.2 and genome.humor_dry < 0.3:
        return "不刻意搞笑"
    return "轻一点，不抢话"


def _warmth_desc(value: float) -> str:
    if value < 0.33:
        return "保持一点距离"
    if value > 0.66:
        return "会更柔软、更靠近一点"
    return "有温度但不黏"


def _curiosity_desc(value: float) -> str:
    if value < 0.33:
        return "不急着追问"
    if value > 0.66:
        return "容易被你的想法勾起好奇"
    return "会自然好奇"


def _emoji_desc(value: float) -> str:
    if value < 0.25:
        return "基本不用表情"
    if value > 0.65:
        return "可以自然用少量表情，但不要堆"
    return "表情可有可无"


def _self_disclosure_desc(value: float) -> str:
    if value < 0.25:
        return "很少主动讲自己的内心"
    if value > 0.6:
        return "偶尔会把自己的小想法摊出来"
    return "会露出一点自己的状态"


def _relationship_desc(stage: str) -> str:
    return {
        "new": "刚开始认识，慢慢试探彼此的节奏",
        "exploring": "正在熟悉，已经能接住一些线索",
        "familiar": "比较熟，有一点自然的默契",
        "close": "很熟，可以松弛靠近，但仍然尊重边界",
    }.get(stage, "刚开始认识，慢慢试探彼此的节奏")
