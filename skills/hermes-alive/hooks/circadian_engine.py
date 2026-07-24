"""Deterministic, persistent circadian state for Hermes Alive.

The engine owns sleep facts and shadow decisions. It never sends messages and
never changes watcher behaviour by itself.

Markers:
- HERMES_ALIVE_CIRCADIAN_ENGINE_CORE_V1
- HERMES_ALIVE_CIRCADIAN_SHADOW_DECISION_V1
- HERMES_ALIVE_CIRCADIAN_STATE_SCHEMA_V1
- HERMES_ALIVE_CIRCADIAN_MANAGED_ENV_V1
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from safe_io import locked_read_json, locked_write_json
except Exception:  # pragma: no cover - standalone import fallback
    locked_read_json = None  # type: ignore[assignment]
    locked_write_json = None  # type: ignore[assignment]

SCHEMA_VERSION = 1
STATE_LOCK_NAME = "circadian_state.lock"
DEFAULT_TIMEZONE = "Asia/Singapore"
DEFAULT_SHARED_DIR = "/opt/data/hermes_alive_shared"
VALID_PHASES = {
    "awake",
    "winding_down",
    "drowsy",
    "asleep",
    "light_sleep",
    "forced_awake",
    "sleep_deprived",
    "overslept",
    "recovering",
}
HARD_EXEMPT_CLASSES = {
    "system_error",
    "service_alert",
    "security_alert",
    "control_command",
    "explicit_reminder",
    "email_watchdog",
    "business_critical",
}

CIRCADIAN_ENV_KEYS = {
    "enabled": "HERMES_ALIVE_CIRCADIAN_ENABLED",
    "mode": "HERMES_ALIVE_CIRCADIAN_MODE",
    "chronotype": "HERMES_ALIVE_CIRCADIAN_CHRONOTYPE",
    "timezone": "HERMES_ALIVE_CIRCADIAN_TIMEZONE",
    "base_sleep_time": "HERMES_ALIVE_CIRCADIAN_BASE_SLEEP_TIME",
    "base_wake_time": "HERMES_ALIVE_CIRCADIAN_BASE_WAKE_TIME",
    "learned_sleep_offset_minutes": "HERMES_ALIVE_CIRCADIAN_LEARNED_SLEEP_OFFSET_MINUTES",
    "learned_wake_offset_minutes": "HERMES_ALIVE_CIRCADIAN_LEARNED_WAKE_OFFSET_MINUTES",
    "normal_sleep_earliest": "HERMES_ALIVE_CIRCADIAN_NORMAL_SLEEP_EARLIEST",
    "normal_sleep_latest": "HERMES_ALIVE_CIRCADIAN_NORMAL_SLEEP_LATEST",
    "exceptional_sleep_latest": "HERMES_ALIVE_CIRCADIAN_EXCEPTIONAL_SLEEP_LATEST",
    "normal_wake_earliest": "HERMES_ALIVE_CIRCADIAN_NORMAL_WAKE_EARLIEST",
    "normal_wake_latest": "HERMES_ALIVE_CIRCADIAN_NORMAL_WAKE_LATEST",
    "ideal_sleep_minutes": "HERMES_ALIVE_CIRCADIAN_IDEAL_SLEEP_MINUTES",
    "minimum_sleep_minutes": "HERMES_ALIVE_CIRCADIAN_MINIMUM_SLEEP_MINUTES",
    "deep_sleep_core_minutes": "HERMES_ALIVE_CIRCADIAN_DEEP_SLEEP_CORE_MINUTES",
    "daily_sleep_variance_minutes": "HERMES_ALIVE_CIRCADIAN_DAILY_SLEEP_VARIANCE_MINUTES",
    "daily_wake_variance_minutes": "HERMES_ALIVE_CIRCADIAN_DAILY_WAKE_VARIANCE_MINUTES",
    "max_learning_minutes_per_day": "HERMES_ALIVE_CIRCADIAN_MAX_LEARNING_MINUTES_PER_DAY",
    "max_learning_minutes_per_week": "HERMES_ALIVE_CIRCADIAN_MAX_LEARNING_MINUTES_PER_WEEK",
    "explicit_user_preference_weight": "HERMES_ALIVE_CIRCADIAN_EXPLICIT_USER_PREFERENCE_WEIGHT",
    "repeated_interaction_weight": "HERMES_ALIVE_CIRCADIAN_REPEATED_INTERACTION_WEIGHT",
    "single_late_interaction_weight": "HERMES_ALIVE_CIRCADIAN_SINGLE_LATE_INTERACTION_WEIGHT",
    "learned_offset_decay_enabled": "HERMES_ALIVE_CIRCADIAN_LEARNED_OFFSET_DECAY_ENABLED",
    "learned_offset_decay_minutes_per_week": "HERMES_ALIVE_CIRCADIAN_LEARNED_OFFSET_DECAY_MINUTES_PER_WEEK",
    "user_can_delay_sleep": "HERMES_ALIVE_CIRCADIAN_USER_CAN_DELAY_SLEEP",
    "max_user_delay_minutes": "HERMES_ALIVE_CIRCADIAN_MAX_USER_DELAY_MINUTES",
    "user_can_wake_early": "HERMES_ALIVE_CIRCADIAN_USER_CAN_WAKE_EARLY",
    "sleep_transition_message_probability": "HERMES_ALIVE_CIRCADIAN_SLEEP_TRANSITION_MESSAGE_PROBABILITY",
    "wake_transition_message_probability": "HERMES_ALIVE_CIRCADIAN_WAKE_TRANSITION_MESSAGE_PROBABILITY",
    "sleep_debt_recovery_enabled": "HERMES_ALIVE_CIRCADIAN_SLEEP_DEBT_RECOVERY_ENABLED",
}


@dataclass(frozen=True)
class CircadianConfig:
    enabled: bool = True
    mode: str = "shadow"
    chronotype: str = "adaptive"
    timezone: str = DEFAULT_TIMEZONE
    base_sleep_time: str = "23:00"
    base_wake_time: str = "07:00"
    learned_sleep_offset_minutes: int = 0
    learned_wake_offset_minutes: int = 0
    normal_sleep_earliest: str = "22:00"
    normal_sleep_latest: str = "01:30"
    exceptional_sleep_latest: str = "03:00"
    normal_wake_earliest: str = "06:00"
    normal_wake_latest: str = "09:30"
    ideal_sleep_minutes: int = 480
    minimum_sleep_minutes: int = 360
    deep_sleep_core_minutes: int = 180
    daily_sleep_variance_minutes: int = 30
    daily_wake_variance_minutes: int = 35
    max_learning_minutes_per_day: int = 10
    max_learning_minutes_per_week: int = 40
    explicit_user_preference_weight: float = 1.0
    repeated_interaction_weight: float = 0.35
    single_late_interaction_weight: float = 0.05
    learned_offset_decay_enabled: bool = True
    learned_offset_decay_minutes_per_week: int = 5
    user_can_delay_sleep: bool = True
    max_user_delay_minutes: int = 150
    user_can_wake_early: bool = True
    sleep_transition_message_probability: float = 0.45
    wake_transition_message_probability: float = 0.30
    sleep_debt_recovery_enabled: bool = True

    @classmethod
    def from_env(
        cls,
        environ: dict[str, str] | None = None,
    ) -> "CircadianConfig":
        source = os.environ if environ is None else environ
        values: dict[str, Any] = {}
        for field_name, env_name in CIRCADIAN_ENV_KEYS.items():
            value = source.get(env_name)
            if value is not None and str(value).strip() != "":
                values[field_name] = value
        if "timezone" not in values:
            fallback_timezone = source.get("TZ")
            if fallback_timezone:
                values["timezone"] = fallback_timezone
        return cls.from_mapping(values)

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None) -> "CircadianConfig":
        raw = values if isinstance(values, dict) else {}
        fields = cls.__dataclass_fields__
        payload: dict[str, Any] = {}
        for name, field in fields.items():
            if name not in raw:
                continue
            value = raw[name]
            default = field.default
            try:
                if isinstance(default, bool):
                    payload[name] = _as_bool(value, default)
                elif isinstance(default, int) and not isinstance(default, bool):
                    payload[name] = int(value)
                elif isinstance(default, float):
                    payload[name] = float(value)
                else:
                    payload[name] = str(value)
            except (TypeError, ValueError):
                continue
        cfg = cls(**payload)
        return cfg.validated()

    def validated(self) -> "CircadianConfig":
        mode = self.mode.strip().lower()
        if mode not in {"off", "shadow", "live"}:
            mode = "shadow"
        timezone_name = self.timezone.strip() or DEFAULT_TIMEZONE
        _zone(timezone_name)
        for value in (
            self.base_sleep_time,
            self.base_wake_time,
            self.normal_sleep_earliest,
            self.normal_sleep_latest,
            self.exceptional_sleep_latest,
            self.normal_wake_earliest,
            self.normal_wake_latest,
        ):
            _parse_hhmm(value)
        payload = asdict(self)
        payload.update(
            {
                "mode": mode,
                "timezone": timezone_name,
                "ideal_sleep_minutes": _clamp_int(self.ideal_sleep_minutes, 360, 600),
                "minimum_sleep_minutes": _clamp_int(self.minimum_sleep_minutes, 240, 540),
                "deep_sleep_core_minutes": _clamp_int(self.deep_sleep_core_minutes, 60, 360),
                "daily_sleep_variance_minutes": _clamp_int(self.daily_sleep_variance_minutes, 0, 90),
                "daily_wake_variance_minutes": _clamp_int(self.daily_wake_variance_minutes, 0, 90),
                "max_learning_minutes_per_day": _clamp_int(self.max_learning_minutes_per_day, 0, 60),
                "max_learning_minutes_per_week": _clamp_int(self.max_learning_minutes_per_week, 0, 180),
                "learned_offset_decay_minutes_per_week": _clamp_int(self.learned_offset_decay_minutes_per_week, 0, 60),
                "max_user_delay_minutes": _clamp_int(self.max_user_delay_minutes, 0, 300),
                "sleep_transition_message_probability": _clamp_float(self.sleep_transition_message_probability, 0.0, 1.0),
                "wake_transition_message_probability": _clamp_float(self.wake_transition_message_probability, 0.0, 1.0),
            }
        )
        if payload["minimum_sleep_minutes"] > payload["ideal_sleep_minutes"]:
            payload["minimum_sleep_minutes"] = payload["ideal_sleep_minutes"]
        return CircadianConfig(**payload)


class CircadianEngine:
    """Persistent circadian planner and state machine.

    The engine is intentionally side-effect free outside its state file. In
    shadow mode, :meth:`shadow_decision` reports what would happen but never
    blocks or sends anything.
    """

    def __init__(
        self,
        *,
        config: CircadianConfig | dict[str, Any] | None = None,
        state_path: Path | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = (
            config.validated()
            if isinstance(config, CircadianConfig)
            else CircadianConfig.from_mapping(config)
        )
        self.tz = _zone(self.config.timezone)
        self.now_fn = now_fn or (lambda: datetime.now(self.tz))
        shared = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", DEFAULT_SHARED_DIR))
        self.state_path = state_path or shared / "circadian_state.json"
        self.state = self._load_state()

    def snapshot(self, *, update: bool = True, now: datetime | None = None) -> dict[str, Any]:
        current = self._local(now or self.now_fn())
        if update:
            self._ensure_plan(current)
            self._advance_phase(current)
            self._save_state()
        return _deep_copy(self.state)

    def ensure_plan(self, now: datetime | None = None) -> dict[str, Any]:
        current = self._local(now or self.now_fn())
        self._ensure_plan(current)
        self._save_state()
        return _deep_copy(self.state)

    def apply_event(
        self,
        event: str,
        *,
        at: datetime | None = None,
        delay_minutes: int | None = None,
    ) -> dict[str, Any]:
        current = self._local(at or self.now_fn())
        self._ensure_plan(current)
        normalized = str(event or "").strip().lower()
        self.state["last_user_interaction_at"] = current.isoformat()
        self.state["last_event"] = normalized

        if normalized in {"goodnight", "sleep_now", "go_sleep"}:
            pending = current + timedelta(minutes=8 if normalized == "goodnight" else 1)
            self.state.update(
                {
                    "phase": "winding_down",
                    "pending_sleep_at": pending.isoformat(),
                    "kept_awake_by_user": False,
                    "last_transition_at": current.isoformat(),
                    "last_transition_message": "sleep_requested",
                }
            )
        elif normalized in {"keep_awake", "delay_sleep", "stay_with_me"}:
            if self.config.user_can_delay_sleep:
                requested = delay_minutes if delay_minutes is not None else 30
                applied = _clamp_int(requested, 1, self.config.max_user_delay_minutes)
                planned = _parse_iso(self.state.get("planned_sleep_at"), self.tz) or current
                exceptional = _sleep_bound_datetime(
                    current.date(), self.config.exceptional_sleep_latest, self.tz
                )
                delayed = min(max(planned, current) + timedelta(minutes=applied), exceptional)
                self.state.update(
                    {
                        "phase": "forced_awake",
                        "planned_sleep_at": delayed.isoformat(),
                        "pending_sleep_at": None,
                        "kept_awake_by_user": True,
                        "user_delay_minutes_today": int(self.state.get("user_delay_minutes_today") or 0)
                        + max(0, int((delayed - planned).total_seconds() // 60)),
                        "last_transition_at": current.isoformat(),
                        "last_transition_message": "sleep_delayed_by_user",
                    }
                )
                self._enforce_minimum_sleep()
        elif normalized in {"wake", "wake_up", "get_up"}:
            if self.config.user_can_wake_early:
                self._record_wake(current, forced=True)
        elif normalized in {"interaction", "late_interaction"}:
            self.state["last_user_interaction_at"] = current.isoformat()
        else:
            raise ValueError(f"unsupported circadian event: {event}")

        self._advance_phase(current)
        self._save_state()
        return _deep_copy(self.state)

    def apply_learning_signal(
        self,
        *,
        sleep_offset_minutes: int = 0,
        wake_offset_minutes: int = 0,
        signal: str = "single_late_interaction",
        at: datetime | None = None,
    ) -> dict[str, Any]:
        current = self._local(at or self.now_fn())
        self._ensure_plan(current)
        signal_name = str(signal or "single_late_interaction").strip().lower()
        weight = {
            "explicit_user_preference": self.config.explicit_user_preference_weight,
            "repeated_interaction": self.config.repeated_interaction_weight,
            "single_late_interaction": self.config.single_late_interaction_weight,
        }.get(signal_name, self.config.single_late_interaction_weight)

        day_key = current.date().isoformat()
        week_key = f"{current.isocalendar().year}-W{current.isocalendar().week:02d}"
        learning = self.state.setdefault("learning", {})
        if not isinstance(learning, dict):
            learning = {}
            self.state["learning"] = learning
        if learning.get("day") != day_key:
            learning["day"] = day_key
            learning["day_minutes"] = 0
        if learning.get("week") != week_key:
            learning["week"] = week_key
            learning["week_minutes"] = 0

        day_used = abs(int(learning.get("day_minutes") or 0))
        week_used = abs(int(learning.get("week_minutes") or 0))
        day_remaining = max(0, self.config.max_learning_minutes_per_day - day_used)
        week_remaining = max(0, self.config.max_learning_minutes_per_week - week_used)
        allowance = min(day_remaining, week_remaining)
        if signal_name == "explicit_user_preference":
            allowance = min(
                max(allowance, min(60, self.config.max_learning_minutes_per_week)),
                max(0, self.config.max_learning_minutes_per_week - week_used),
            )

        sleep_delta = _weighted_delta(sleep_offset_minutes, weight, allowance)
        remaining = max(0, allowance - abs(sleep_delta))
        wake_delta = _weighted_delta(wake_offset_minutes, weight, remaining)

        current_sleep = int(self.state.get("learned_sleep_offset_minutes") or 0)
        current_wake = int(self.state.get("learned_wake_offset_minutes") or 0)
        sleep_limit = _sleep_learning_limits(self.config)
        wake_limit = _wake_learning_limits(self.config)
        new_sleep = _clamp_int(current_sleep + sleep_delta, sleep_limit[0], sleep_limit[1])
        new_wake = _clamp_int(current_wake + wake_delta, wake_limit[0], wake_limit[1])
        applied = abs(new_sleep - current_sleep) + abs(new_wake - current_wake)
        learning["day_minutes"] = int(learning.get("day_minutes") or 0) + applied
        learning["week_minutes"] = int(learning.get("week_minutes") or 0) + applied
        learning["last_signal"] = signal_name
        learning["last_signal_at"] = current.isoformat()
        self.state["learned_sleep_offset_minutes"] = new_sleep
        self.state["learned_wake_offset_minutes"] = new_wake
        self._save_state()
        return _deep_copy(self.state)

    def decay_learned_offsets(self, *, at: datetime | None = None) -> dict[str, Any]:
        current = self._local(at or self.now_fn())
        if not self.config.learned_offset_decay_enabled:
            return self.snapshot(update=False)
        learning = self.state.setdefault("learning", {})
        last = _parse_iso(learning.get("last_decay_at"), self.tz)
        if last is None:
            learning["last_decay_at"] = current.isoformat()
            self._save_state()
            return _deep_copy(self.state)
        weeks = int((current - last).total_seconds() // (7 * 86400))
        if weeks <= 0:
            return _deep_copy(self.state)
        amount = weeks * self.config.learned_offset_decay_minutes_per_week
        for key in ("learned_sleep_offset_minutes", "learned_wake_offset_minutes"):
            value = int(self.state.get(key) or 0)
            self.state[key] = _toward_zero(value, amount)
        learning["last_decay_at"] = (last + timedelta(days=7 * weeks)).isoformat()
        self._save_state()
        return _deep_copy(self.state)

    def shadow_decision(
        self,
        *,
        message_class: str = "proactive_social",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current = self._local(now or self.now_fn())
        state = self.snapshot(update=True, now=current)
        category = str(message_class or "proactive_social").strip().lower()
        hard_exempt = category in HARD_EXEMPT_CLASSES
        asleep = state.get("phase") in {"asleep", "light_sleep"}
        in_deep_core = self._in_deep_sleep_core(current)
        configured_active = bool(self.config.enabled) and self.config.mode != "off"
        would_allow = (not configured_active) or hard_exempt or not asleep
        reason = (
            "disabled"
            if not self.config.enabled
            else "mode_off"
            if self.config.mode == "off"
            else "hard_exempt"
            if hard_exempt
            else "deep_sleep_core"
            if in_deep_core
            else "dynamic_sleep_window"
            if asleep
            else "awake"
        )
        return {
            "engine": "circadian",
            "schema_version": SCHEMA_VERSION,
            "enabled": bool(self.config.enabled),
            "mode": self.config.mode,
            "shadow_only": self.config.mode == "shadow",
            "message_class": category,
            "hard_exempt": hard_exempt,
            "phase": state.get("phase"),
            "dynamic_sleep_window": asleep,
            "deep_sleep_core": in_deep_core,
            "would_allow_proactive": would_allow,
            "would_block_proactive": not would_allow,
            "reason": reason,
            "planned_sleep_at": state.get("planned_sleep_at"),
            "planned_wake_at": state.get("planned_wake_at"),
            "sleep_debt_minutes": int(state.get("sleep_debt_minutes") or 0),
        }

    def prompt_context(self, *, now: datetime | None = None) -> dict[str, Any]:
        state = self.snapshot(update=True, now=now)
        return {
            "phase": state.get("phase"),
            "planned_sleep_at": state.get("planned_sleep_at"),
            "planned_wake_at": state.get("planned_wake_at"),
            "actual_sleep_at": state.get("actual_sleep_at"),
            "actual_wake_at": state.get("actual_wake_at"),
            "sleep_debt_minutes": int(state.get("sleep_debt_minutes") or 0),
            "kept_awake_by_user": bool(state.get("kept_awake_by_user")),
            "facts_owned_by_engine": True,
        }

    def _local(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self.tz)
        return value.astimezone(self.tz)

    def _load_state(self) -> dict[str, Any]:
        default = self._empty_state()
        if locked_read_json is not None:
            loaded = locked_read_json(self.state_path, default, STATE_LOCK_NAME)
        else:  # pragma: no cover
            try:
                import json

                loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                loaded = default
        if not isinstance(loaded, dict):
            loaded = default
        state = default
        state.update(loaded)
        if int(state.get("schema_version") or 0) != SCHEMA_VERSION:
            state = self._migrate_state(state)
        phase = str(state.get("phase") or "awake")
        state["phase"] = phase if phase in VALID_PHASES else "awake"
        return state

    def _empty_state(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "phase": "awake",
            "schedule_date": None,
            "planned_sleep_at": None,
            "planned_wake_at": None,
            "actual_sleep_at": None,
            "actual_wake_at": None,
            "pending_sleep_at": None,
            "sleep_debt_minutes": 0,
            "kept_awake_by_user": False,
            "last_user_interaction_at": None,
            "last_transition_message": None,
            "last_transition_at": None,
            "last_event": None,
            "daily_seed": None,
            "base_sleep_time": self.config.base_sleep_time,
            "base_wake_time": self.config.base_wake_time,
            "learned_sleep_offset_minutes": self.config.learned_sleep_offset_minutes,
            "learned_wake_offset_minutes": self.config.learned_wake_offset_minutes,
            "user_delay_minutes_today": 0,
            "learning": {},
            "history": [],
        }

    def _migrate_state(self, state: dict[str, Any]) -> dict[str, Any]:
        migrated = self._empty_state()
        for key in migrated:
            if key in state:
                migrated[key] = state[key]
        migrated["schema_version"] = SCHEMA_VERSION
        return migrated

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if locked_write_json is not None:
            locked_write_json(self.state_path, self.state, STATE_LOCK_NAME)
            return
        import json  # pragma: no cover

        temp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.state_path)

    def _ensure_plan(self, current: datetime) -> None:
        schedule_date = self._schedule_date_for(current)
        if self.state.get("schedule_date") == schedule_date.isoformat():
            return
        self._archive_previous(current)
        sleep_at, wake_at, seed = self._build_plan(schedule_date)
        self.state.update(
            {
                "schema_version": SCHEMA_VERSION,
                "phase": self._daytime_phase(),
                "schedule_date": schedule_date.isoformat(),
                "planned_sleep_at": sleep_at.isoformat(),
                "planned_wake_at": wake_at.isoformat(),
                "actual_sleep_at": None,
                "actual_wake_at": None,
                "pending_sleep_at": None,
                "kept_awake_by_user": False,
                "last_transition_message": "daily_plan_created",
                "last_transition_at": current.isoformat(),
                "daily_seed": seed,
                "base_sleep_time": self.config.base_sleep_time,
                "base_wake_time": self.config.base_wake_time,
                "user_delay_minutes_today": 0,
            }
        )

    def _schedule_date_for(self, current: datetime) -> date:
        # Before noon, the active sleep cycle started the previous evening.
        return current.date() - timedelta(days=1) if current.hour < 12 else current.date()

    def _build_plan(self, schedule_date: date) -> tuple[datetime, datetime, int]:
        seed = _stable_seed(
            schedule_date.isoformat(),
            self.config.base_sleep_time,
            self.config.base_wake_time,
            str(self.state.get("learned_sleep_offset_minutes") or 0),
            str(self.state.get("learned_wake_offset_minutes") or 0),
        )
        sleep_jitter = _bounded_jitter(seed, self.config.daily_sleep_variance_minutes, "sleep")
        wake_jitter = _bounded_jitter(seed, self.config.daily_wake_variance_minutes, "wake")
        sleep_offset = int(self.state.get("learned_sleep_offset_minutes") or 0)
        wake_offset = int(self.state.get("learned_wake_offset_minutes") or 0)
        debt = max(0, int(self.state.get("sleep_debt_minutes") or 0))
        sleep_recovery = min(30, debt // 8) if self.config.sleep_debt_recovery_enabled else 0
        wake_recovery = min(45, debt // 6) if self.config.sleep_debt_recovery_enabled else 0

        sleep_min = _sleep_timeline_minutes(self.config.base_sleep_time)
        sleep_min += sleep_offset + sleep_jitter - sleep_recovery
        earliest = _sleep_timeline_minutes(self.config.normal_sleep_earliest)
        latest = _sleep_timeline_minutes(self.config.normal_sleep_latest)
        sleep_min = _clamp_int(sleep_min, earliest, latest)

        wake_min = _parse_hhmm(self.config.base_wake_time)
        wake_min += wake_offset + wake_jitter + wake_recovery
        wake_min = _clamp_int(
            wake_min,
            _parse_hhmm(self.config.normal_wake_earliest),
            _parse_hhmm(self.config.normal_wake_latest),
        )

        sleep_date = schedule_date if sleep_min < 1440 else schedule_date + timedelta(days=1)
        sleep_clock = sleep_min % 1440
        sleep_at = datetime.combine(sleep_date, _minutes_to_time(sleep_clock), self.tz)
        wake_at = datetime.combine(schedule_date + timedelta(days=1), _minutes_to_time(wake_min), self.tz)
        minimum_wake = sleep_at + timedelta(minutes=self.config.minimum_sleep_minutes)
        if wake_at < minimum_wake:
            wake_at = minimum_wake
        return sleep_at, wake_at, seed

    def _advance_phase(self, current: datetime) -> None:
        pending = _parse_iso(self.state.get("pending_sleep_at"), self.tz)
        actual_sleep = _parse_iso(self.state.get("actual_sleep_at"), self.tz)
        actual_wake = _parse_iso(self.state.get("actual_wake_at"), self.tz)
        planned_sleep = _parse_iso(self.state.get("planned_sleep_at"), self.tz)
        planned_wake = _parse_iso(self.state.get("planned_wake_at"), self.tz)

        if pending and actual_sleep is None:
            if current < pending:
                self.state["phase"] = "winding_down"
                return
            actual_sleep = pending
            self.state["actual_sleep_at"] = actual_sleep.isoformat()
            self.state["pending_sleep_at"] = None
            self.state["phase"] = "asleep"
            self.state["last_transition_at"] = current.isoformat()
            self.state["last_transition_message"] = "fell_asleep"

        if actual_sleep and actual_wake is None:
            if planned_wake and current >= planned_wake:
                self._record_wake(current, forced=False)
                return
            self.state["phase"] = "asleep" if self._in_deep_sleep_core(current) else "light_sleep"
            return

        if actual_wake:
            if self.state.get("last_transition_message") == "forced_wake":
                self.state["phase"] = "forced_awake"
                return
            planned = _parse_iso(self.state.get("planned_wake_at"), self.tz)
            if planned and actual_wake > planned + timedelta(minutes=30):
                self.state["phase"] = "overslept"
            elif int(self.state.get("sleep_debt_minutes") or 0) >= 90:
                self.state["phase"] = "sleep_deprived"
            elif int(self.state.get("sleep_debt_minutes") or 0) > 0:
                self.state["phase"] = "recovering"
            else:
                self.state["phase"] = "awake"
            return

        if planned_sleep:
            delta = (planned_sleep - current).total_seconds() / 60
            if self.state.get("phase") == "forced_awake" and current < planned_sleep:
                return
            if delta <= 0:
                self.state["actual_sleep_at"] = planned_sleep.isoformat()
                self.state["phase"] = "asleep" if self._in_deep_sleep_core(current) else "light_sleep"
                self.state["last_transition_at"] = current.isoformat()
                self.state["last_transition_message"] = "planned_sleep_started"
            elif delta <= 20:
                self.state["phase"] = "drowsy"
            elif delta <= 60:
                self.state["phase"] = "winding_down"
            else:
                self.state["phase"] = self._daytime_phase()

    def _record_wake(self, current: datetime, *, forced: bool) -> None:
        actual_sleep = _parse_iso(self.state.get("actual_sleep_at"), self.tz)
        planned_wake = _parse_iso(self.state.get("planned_wake_at"), self.tz)
        if actual_sleep is None:
            actual_sleep = _parse_iso(self.state.get("planned_sleep_at"), self.tz)
            if actual_sleep and actual_sleep > current:
                actual_sleep = current
            self.state["actual_sleep_at"] = actual_sleep.isoformat() if actual_sleep else None
        slept = 0
        if actual_sleep is not None:
            slept = max(0, int((current - actual_sleep).total_seconds() // 60))
        debt_delta = max(0, self.config.ideal_sleep_minutes - slept)
        previous_debt = max(0, int(self.state.get("sleep_debt_minutes") or 0))
        recovery = max(0, slept - self.config.ideal_sleep_minutes)
        self.state["sleep_debt_minutes"] = max(0, previous_debt + debt_delta - recovery)
        self.state["actual_wake_at"] = current.isoformat()
        self.state["pending_sleep_at"] = None
        self.state["phase"] = "forced_awake" if forced else (
            "overslept" if planned_wake and current > planned_wake + timedelta(minutes=30) else
            "sleep_deprived" if self.state["sleep_debt_minutes"] >= 90 else
            "recovering" if self.state["sleep_debt_minutes"] > 0 else "awake"
        )
        self.state["last_transition_at"] = current.isoformat()
        self.state["last_transition_message"] = "forced_wake" if forced else "woke_up"

    def _in_deep_sleep_core(self, current: datetime) -> bool:
        sleep_at = _parse_iso(self.state.get("actual_sleep_at"), self.tz) or _parse_iso(
            self.state.get("planned_sleep_at"), self.tz
        )
        if sleep_at is None:
            return False
        core_start = sleep_at + timedelta(minutes=45)
        core_end = core_start + timedelta(minutes=self.config.deep_sleep_core_minutes)
        return core_start <= current < core_end

    def _enforce_minimum_sleep(self) -> None:
        sleep_at = _parse_iso(self.state.get("planned_sleep_at"), self.tz)
        wake_at = _parse_iso(self.state.get("planned_wake_at"), self.tz)
        if sleep_at is None or wake_at is None:
            return
        minimum_wake = sleep_at + timedelta(minutes=self.config.minimum_sleep_minutes)
        if wake_at < minimum_wake:
            latest_wake = datetime.combine(
                wake_at.date(), _minutes_to_time(_parse_hhmm(self.config.normal_wake_latest)), self.tz
            )
            self.state["planned_wake_at"] = min(minimum_wake, latest_wake).isoformat()

    def _archive_previous(self, current: datetime) -> None:
        previous_date = self.state.get("schedule_date")
        if not previous_date:
            return
        history = self.state.setdefault("history", [])
        if not isinstance(history, list):
            history = []
            self.state["history"] = history
        history.append(
            {
                "schedule_date": previous_date,
                "planned_sleep_at": self.state.get("planned_sleep_at"),
                "planned_wake_at": self.state.get("planned_wake_at"),
                "actual_sleep_at": self.state.get("actual_sleep_at"),
                "actual_wake_at": self.state.get("actual_wake_at"),
                "sleep_debt_minutes": int(self.state.get("sleep_debt_minutes") or 0),
                "kept_awake_by_user": bool(self.state.get("kept_awake_by_user")),
                "archived_at": current.isoformat(),
            }
        )
        del history[:-14]

    def _daytime_phase(self) -> str:
        debt = int(self.state.get("sleep_debt_minutes") or 0)
        if debt >= 90:
            return "sleep_deprived"
        if debt > 0:
            return "recovering"
        return "awake"


def load_circadian_config(
    values: dict[str, Any] | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> CircadianConfig:
    if values is None:
        return CircadianConfig.from_env(environ)
    environment_config = CircadianConfig.from_env(environ)
    merged = asdict(environment_config)
    merged.update(values)
    return CircadianConfig.from_mapping(merged)


def _zone(name: str) -> timezone | ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == DEFAULT_TIMEZONE:
            return timezone(timedelta(hours=8), name=DEFAULT_TIMEZONE)
        raise ValueError(f"unknown timezone: {name}")


def _parse_hhmm(value: str) -> int:
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"invalid HH:MM value: {value}")
    hour = int(parts[0])
    minute = int(parts[1])
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"invalid HH:MM value: {value}")
    return hour * 60 + minute


def _sleep_timeline_minutes(value: str) -> int:
    minutes = _parse_hhmm(value)
    return minutes + 1440 if minutes < 12 * 60 else minutes


def _sleep_bound_datetime(day: date, value: str, tz: timezone | ZoneInfo) -> datetime:
    minutes = _sleep_timeline_minutes(value)
    target_day = day if minutes < 1440 else day + timedelta(days=1)
    return datetime.combine(target_day, _minutes_to_time(minutes % 1440), tz)


def _minutes_to_time(minutes: int) -> time:
    value = minutes % 1440
    return time(value // 60, value % 60)


def _stable_seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _bounded_jitter(seed: int, variance: int, label: str) -> int:
    if variance <= 0:
        return 0
    local = _stable_seed(str(seed), label)
    return int(local % (2 * variance + 1)) - variance


def _parse_iso(value: Any, tz: timezone | ZoneInfo) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _weighted_delta(requested: int, weight: float, allowance: int) -> int:
    if allowance <= 0 or requested == 0:
        return 0
    magnitude = min(allowance, max(1, int(round(abs(requested) * max(0.0, weight)))))
    return magnitude if requested > 0 else -magnitude


def _toward_zero(value: int, amount: int) -> int:
    if value > 0:
        return max(0, value - amount)
    if value < 0:
        return min(0, value + amount)
    return 0


def _sleep_learning_limits(config: CircadianConfig) -> tuple[int, int]:
    base = _sleep_timeline_minutes(config.base_sleep_time)
    earliest = _sleep_timeline_minutes(config.normal_sleep_earliest)
    latest = _sleep_timeline_minutes(config.normal_sleep_latest)
    return earliest - base, latest - base


def _wake_learning_limits(config: CircadianConfig) -> tuple[int, int]:
    base = _parse_hhmm(config.base_wake_time)
    earliest = _parse_hhmm(config.normal_wake_earliest)
    latest = _parse_hhmm(config.normal_wake_latest)
    return earliest - base, latest - base


def _deep_copy(value: dict[str, Any]) -> dict[str, Any]:
    import json

    return json.loads(json.dumps(value, ensure_ascii=False))
