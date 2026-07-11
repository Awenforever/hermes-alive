"""Load Hermes Alive managed configuration without owning Provider secrets.

Marker: HERMES_ALIVE_MANAGED_CONFIG_LOADER_V1
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
    "dream_enabled": "HERMES_DREAM_ENABLED",
    "dream_interval_hours": "HERMES_DREAM_INTERVAL_HOURS",
    "weather_lat": "HERMES_PROACTIVE_LAT",
    "weather_lon": "HERMES_PROACTIVE_LON",
    "emoji_policy": "HERMES_ALIVE_EMOJI_POLICY",
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
