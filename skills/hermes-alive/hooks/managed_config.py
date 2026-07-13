"""Load Hermes Alive managed configuration without owning Provider secrets.

Marker: HERMES_ALIVE_MANAGED_CONFIG_LOADER_V1
Marker: HERMES_ALIVE_CIRCADIAN_MANAGED_CONFIG_V1
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

MANAGED_ENV_KEYS = {
    "enabled": "HERMES_PROACTIVE_PLATFORM_ENABLED",
    "weixin_chat_id": "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
    "timezone": "TZ",
    "quiet_start": "HERMES_PROACTIVE_QUIET_START",
    "quiet_end": "HERMES_PROACTIVE_QUIET_END",
    "cooldown_minutes": "HERMES_PROACTIVE_COOLDOWN_MINUTES",
    "platform_interval_seconds": "HERMES_PROACTIVE_PLATFORM_INTERVAL_SECONDS",
    "llm_enabled": "HERMES_PROACTIVE_LLM_ENABLED",
    "llm_model": "HERMES_PROACTIVE_LLM_MODEL",
    "llm_fallback_model": "HERMES_PROACTIVE_LLM_FALLBACK_MODEL",
    "discovery_enabled": "HERMES_PROACTIVE_DISCOVERY_ENABLED",
    "discovery_interval_seconds": "HERMES_PROACTIVE_DISCOVERY_INTERVAL_SECONDS",
    "quality_governor_mode": "HERMES_ALIVE_QUALITY_GOVERNOR_MODE",
    "quality_topic_expiry_after_unanswered": "HERMES_ALIVE_QUALITY_TOPIC_EXPIRY_AFTER_UNANSWERED",
    "quality_silence_after_unanswered": "HERMES_ALIVE_QUALITY_SILENCE_AFTER_UNANSWERED",
    "context_flow_max_age_seconds": "HERMES_ALIVE_CONTEXT_FLOW_MAX_AGE_SECONDS",
    "dream_enabled": "HERMES_DREAM_ENABLED",
    "dream_interval_hours": "HERMES_DREAM_INTERVAL_HOURS",
    "weather_enabled": "HERMES_PROACTIVE_WEATHER_ENABLED",
    "weather_lat": "HERMES_PROACTIVE_LAT",
    "weather_lon": "HERMES_PROACTIVE_LON",
    "weather_location_name": "HERMES_PROACTIVE_WEATHER_LOCATION_NAME",
    "weather_country_code": "HERMES_PROACTIVE_WEATHER_COUNTRY_CODE",
    "weather_admin1": "HERMES_PROACTIVE_WEATHER_ADMIN1",
    "weather_admin2": "HERMES_PROACTIVE_WEATHER_ADMIN2",
    "weather_admin3": "HERMES_PROACTIVE_WEATHER_ADMIN3",
    "weather_timezone": "HERMES_PROACTIVE_WEATHER_TIMEZONE",
    "weather_location_confirmed": "HERMES_PROACTIVE_WEATHER_LOCATION_CONFIRMED",
    "weather_location_source": "HERMES_PROACTIVE_WEATHER_LOCATION_SOURCE",
    "weather_location_precision": "HERMES_PROACTIVE_WEATHER_LOCATION_PRECISION",
    "emoji_policy": "HERMES_ALIVE_EMOJI_POLICY",
    "circadian_enabled": "HERMES_ALIVE_CIRCADIAN_ENABLED",
    "circadian_mode": "HERMES_ALIVE_CIRCADIAN_MODE",
    "chronotype": "HERMES_ALIVE_CIRCADIAN_CHRONOTYPE",
    "circadian_timezone": "HERMES_ALIVE_CIRCADIAN_TIMEZONE",
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


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def managed_config_path() -> Path:
    shared = Path(
        os.getenv(
            "HERMES_ALIVE_SHARED_DIR",
            "/opt/data/hermes_alive_shared",
        )
    )
    return shared / "config" / "hermes-alive.json"


def load_managed_env(*, overwrite: bool = False) -> dict[str, str]:
    path = managed_config_path()
    if not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    values = payload.get("values", {}) if isinstance(payload, dict) else {}
    if not isinstance(values, dict):
        return {}

    loaded: dict[str, str] = {}
    for key, env_name in MANAGED_ENV_KEYS.items():
        value = values.get(key)
        if value is None:
            continue
        text = _text(value)
        if overwrite or not os.getenv(env_name):
            os.environ[env_name] = text
            loaded[env_name] = text

    # Weixin QR credentials identify the bot account, while inbound DM
    # sessions and context tokens are keyed by the human peer. Normalize the
    # proactive target only when the persisted runtime evidence makes the
    # choice unambiguous.
    try:
        from weixin_peer import normalize_weixin_chat_env

        before = os.getenv(
            "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
            "",
        ).strip()
        resolved, _reason = normalize_weixin_chat_env()
        if resolved and resolved != before:
            loaded[
                "HERMES_PROACTIVE_WEIXIN_CHAT_ID"
            ] = resolved
    except Exception:
        # Managed configuration must remain import-safe.
        pass

    return loaded
