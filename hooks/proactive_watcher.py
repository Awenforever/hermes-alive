
"""Gateway-native proactive platform watcher for Hermes Alive."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
# Hermes Alive import path bootstrap
_HOOK_DIR = os.getenv("HERMES_HOOK_DIR", "/opt/data/hooks/hermes-alive")
_SHARED_DIR = os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")
for _p in (_HOOK_DIR, _SHARED_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


from safe_io import (
    append_jsonl,
    locked_read_json,
    locked_write_json,
    try_file_lock,
    sha256_text,
    redact_preview,
    atomic_write_text,
    file_lock,
)

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 300.0
ENABLED_ENV = "HERMES_PROACTIVE_PLATFORM_ENABLED"
CHAT_ID_ENV = "HERMES_PROACTIVE_WEIXIN_CHAT_ID"
INTERVAL_ENV = "HERMES_PROACTIVE_PLATFORM_INTERVAL_SECONDS"
VOICE_ENABLED_ENV = "VOICE_ENABLED"
COOLDOWN_ENABLED_ENV = "COOLDOWN_ENABLED"
LLM_ENABLED_ENV = "HERMES_PROACTIVE_LLM_ENABLED"
LLM_MODEL_ENV = "HERMES_PROACTIVE_LLM_MODEL"
DISCOVERY_ENABLED_ENV = "HERMES_PROACTIVE_DISCOVERY_ENABLED"

BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
WATCHER_LOCK = BASE / "locks" / "proactive_watcher.lock"
PROACTIVE_LOG = BASE / "proactive_log.jsonl"
CONTROL = BASE / "control.json"
QUEUE = BASE / "control_queue.jsonl"

SYSTEM_METADATA: dict[str, Any] = {
    "is_system": True,
    "actor": "system",
    "source": "system",
    "message_origin": "system",
    "origin": "system",
    "model_name": "hermes",
    "resolved_model": "hermes",
    "routed_model": "hermes",
    "model": "hermes",
}

class ProactivePlatformWatcher:
    """Send proactive messages through live gateway adapters."""

    def __init__(self, adapters: Mapping[Any, Any], config: Any) -> None:
        self.adapters = adapters
        self.config = config
        self._voice_engine: Any | None = None
        self._cooldown_manager: Any | None = None
        self._llm_message_composer: Any | None = None
        self._discovery_engine: Any | None = None
        self._dream_engine: Any | None = None
        self.watcher_id = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.started_at = datetime.now().astimezone().isoformat()

    async def run(self) -> None:
        with try_file_lock(WATCHER_LOCK) as acquired:
            if not acquired:
                logger.warning("Hermes Alive watcher already running; singleton lock unavailable")
                self._log("skip", reason="watcher_lock_unavailable")
                return
            from log_rotate import rotate_proactive_log
            rotate_proactive_log(BASE)
            self._log("start", reason="watcher_started")
            logger.info("Proactive platform watcher started id=%s", self.watcher_id)
            try:
                while True:
                    await self.tick()
                    await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                self._log("stop", reason="watcher_cancelled")
                raise
            except Exception as exc:
                self._log("error", reason="watcher_crashed", error=type(exc).__name__)
                logger.exception("Proactive platform watcher crashed")
                raise

    async def tick(self) -> bool:
        tick_id = uuid.uuid4().hex[:12]
        try:
            return await self._tick_impl(tick_id)
        except Exception as exc:
            self._log("error", tick_id=tick_id, reason="tick_exception", error=type(exc).__name__)
            logger.exception("Hermes Alive tick failed")
            return False

    async def _tick_impl(self, tick_id: str) -> bool:
        if not self.enabled:
            self._log("skip", tick_id=tick_id, reason="disabled")
            return False

        # Resolve adapter and chat_id: try weixin first, then any available platform
        adapter, chat_id = self._resolve_adapter_and_chat_id()
        if adapter is None or not chat_id:
            self._log("skip", tick_id=tick_id, reason="adapter_or_chat_id_unavailable")
            return False

        control_sent = await self._process_control_queue(adapter, chat_id, tick_id)
        if control_sent:
            return True

        voice = self._voice_state()

        # ── Activity check: suppress unless Hermes is idle and conversation is quiet ──
        if self._user_active_recently():
            self._log("skip", tick_id=tick_id, reason="user_active")
            return False

        cooldown = self._cooldown()
        if cooldown is not None:
            # Set voice-linked cooldown before checking
            social_urge = self._extract_social_urge(voice)
            cooldown.set_mood_cooldown(social_urge)
            allowed, reason = cooldown.can_send("proactive")
            if not allowed:
                self._log("skip", tick_id=tick_id, reason=reason, quiet_hours=(reason == "quiet_hours"))
                return False

        import random
        discovery_context = await self._check_discovery()
        if discovery_context is not None:
            self._log_discovery(tick_id, discovery_context)
        await self._check_dream()
        messages = await self._compose_message(voice, discovery_context)
        if not messages:
            self._log("skip", tick_id=tick_id, reason="empty_messages")
            return False

        msg_count = len(messages)
        for msg_index, (msg_type, content, generated_by) in enumerate(messages, start=1):
            self._log_compose(tick_id, voice, discovery_context, msg_type, generated_by)

            metadata = self._metadata(generated_by)
            try:
                await adapter.send(chat_id, content, metadata=metadata)
            except Exception as exc:
                self._log("error", tick_id=tick_id, reason="adapter_send_failed", error=type(exc).__name__, msg_type=msg_type, msg_index=msg_index, msg_count=msg_count)
                logger.exception("Failed to send proactive platform heartbeat")
                continue

            # Only record cooldown once (on the first message)
            if msg_index == 1 and cooldown is not None:
                cooldown.record_send(msg_type)

            self._log(
                "sent",
                tick_id=tick_id,
                reason="normal_proactive",
                msg_type=msg_type,
                msg_index=msg_index,
                msg_count=msg_count,
                generated_by=generated_by,
                message_hash=sha256_text(content),
                message_preview=redact_preview(content),
                adapter_result="ok",
            )
            logger.info("Sent proactive platform heartbeat to chat %s [%d/%d]", _redact_chat(chat_id), msg_index, msg_count)

            # Delay between messages (not after the last one)
            if msg_index < msg_count:
                await asyncio.sleep(random.uniform(2, 5))

        return True

    @property
    def enabled(self) -> bool:
        control = self._control()
        override = control.get("enabled_override")
        if override is False:
            return False
        if override is True:
            return True
        return _truthy(os.getenv(ENABLED_ENV))

    @property
    def chat_id(self) -> str | None:
        """Find the first available chat_id from any platform.

        Iterates over all configured adapters and checks for corresponding
        HERMES_PROACTIVE_{PLATFORM}_CHAT_ID env vars. Weixin takes priority
        if both exist.
        """
        # Weixin always takes priority
        weixin_candidate = os.getenv(CHAT_ID_ENV)
        if weixin_candidate:
            weixin_candidate = weixin_candidate.strip()
            if weixin_candidate:
                return weixin_candidate
        # Fall back to other platforms
        for key, _adapter in self.adapters.items():
            platform = str(getattr(key, "value", key)).upper()
            value = os.getenv(f"HERMES_PROACTIVE_{platform}_CHAT_ID", "").strip()
            if value:
                return value
        return None

    @property
    def interval_seconds(self) -> float:
        raw = os.getenv(INTERVAL_ENV)
        if raw is None or not raw.strip():
            return DEFAULT_INTERVAL_SECONDS
        try:
            interval = float(raw)
        except ValueError:
            return DEFAULT_INTERVAL_SECONDS
        return interval if interval > 0 else DEFAULT_INTERVAL_SECONDS

    def _control(self) -> dict[str, Any]:
        data = locked_read_json(CONTROL, {}, "control.lock")
        return data if isinstance(data, dict) else {}

    def _resolve_adapter_and_chat_id(self) -> tuple[Any | None, str | None]:
        """Resolve the first available adapter with a matching chat_id.

        Weixin takes priority if both a weixin adapter exists and
        HERMES_PROACTIVE_WEIXIN_CHAT_ID is set. Otherwise, iterate all
        adapters in order, looking for HERMES_PROACTIVE_{PLATFORM}_CHAT_ID.
        """
        weixin_adapter: Any | None = None
        for key, adapter in self.adapters.items():
            key_value = getattr(key, "value", key)
            if key_value == "weixin":
                weixin_adapter = adapter
                continue
            # Non-weixin platform: check env var
            platform = str(key_value).upper()
            chat_id = os.getenv(f"HERMES_PROACTIVE_{platform}_CHAT_ID", "").strip()
            if chat_id:
                logger.debug("Found adapter for platform=%s with configured chat_id", key_value)
                return adapter, chat_id

        # Try weixin last, so it overrides if both are available
        if weixin_adapter is not None:
            chat_id = os.getenv("HERMES_PROACTIVE_WEIXIN_CHAT_ID", "").strip()
            if chat_id:
                logger.debug("Found weixin adapter with configured chat_id")
                return weixin_adapter, chat_id

        logger.warning("No adapter with a configured HERMES_PROACTIVE_{PLATFORM}_CHAT_ID found")
        return None, None

    async def _process_control_queue(self, adapter: Any, chat_id: str, tick_id: str) -> bool:
        if not QUEUE.exists():
            return False
        from safe_io import LOCK_DIR
        queue_lock = LOCK_DIR / "control_queue_process.lock"
        with file_lock(queue_lock):
            try:
                lines = QUEUE.read_text(encoding="utf-8").splitlines()
            except Exception:
                return False
            if not lines:
                return False
            remaining: list[str] = []
            sent_any = False
            for line in lines:
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if item.get("type") == "test" and not sent_any:
                    content = str(item.get("message") or "Hermes Alive 主动推送测试。")
                    try:
                        await adapter.send(chat_id, content, metadata=self._metadata(item.get("generated_by", "hermes")))
                        self._log("sent", tick_id=tick_id, reason="alive_test", msg_type="test", generated_by=item.get("generated_by", "hermes"), message_hash=sha256_text(content), message_preview=redact_preview(content), adapter_result="ok")
                        sent_any = True
                    except Exception as exc:
                        self._log("error", tick_id=tick_id, reason="alive_test_send_failed", error=type(exc).__name__)
                        remaining.append(line)
                else:
                    remaining.append(line)
            locked_write_json(BASE / "control_queue_state.json", {"last_processed_at": datetime.now().astimezone().isoformat()}, "control_queue.lock")
            atomic_write_text(QUEUE, "\n".join(remaining) + ("\n" if remaining else ""))
        return sent_any

    def _heartbeat_message(self) -> str:
        return "Hermes proactive platform heartbeat."

    def _voice(self) -> Any | None:
        if not self._feature_enabled(VOICE_ENABLED_ENV):
            return None
        if self._voice_engine is None:
            try:
                from voice_engine import VoiceEngine
                self._voice_engine = VoiceEngine()
            except Exception:
                logger.exception("Failed to initialize voice engine")
                self._voice_engine = False
        return None if self._voice_engine is False else self._voice_engine

    def _cooldown(self) -> Any | None:
        if not self._feature_enabled(COOLDOWN_ENABLED_ENV):
            return None
        if self._cooldown_manager is None:
            try:
                from cooldown_manager import CooldownManager
                self._cooldown_manager = CooldownManager()
            except Exception:
                logger.exception("Failed to initialize cooldown manager")
                self._cooldown_manager = False
        return None if self._cooldown_manager is False else self._cooldown_manager

    async def _compose_message(self, voice: Any | None = None, discovery_context: dict[str, Any] | None = None) -> list[tuple[str, str, str]]:
        default_voice = self._voice_state_or_default(voice)
        if self._feature_enabled(LLM_ENABLED_ENV):
            llm_result = await self._compose_llm_message(default_voice, discovery_context)
            if llm_result is not None and len(llm_result) > 0:
                # Check if LLM result is actually a fallback
                msg_type, content = llm_result[0]
                if not self._is_llm_fallback(msg_type, content):
                    return [(m_type, m_content, self._llm_model_name()) for m_type, m_content in llm_result]
                logger.debug("LLM composer returned fallback; using heartbeat")
        return [("heartbeat", self._heartbeat_message(), "hermes")]

    async def _compose_llm_message(self, voice: Any, discovery_context: dict[str, Any] | None = None) -> list[tuple[str, str]] | None:
        if self._llm_message_composer is None:
            try:
                from llm_message_composer import LLMMessageComposer
                self._llm_message_composer = LLMMessageComposer()
            except Exception:
                logger.exception("Failed to initialize LLM message composer")
                self._llm_message_composer = False
        if self._llm_message_composer is False:
            return None
        try:
            return await self._llm_message_composer.compose(voice, context={"trigger": self._dominant_voice(voice)}, discovery_context=discovery_context)
        except Exception:
            logger.exception("LLM message composer failed")
            self._llm_message_composer = False
            return None

    async def _check_discovery(self) -> dict[str, Any] | None:
        if not self._feature_enabled(DISCOVERY_ENABLED_ENV):
            return None
        if self._discovery_engine is None:
            try:
                from discovery import DiscoveryEngine
                self._discovery_engine = DiscoveryEngine()
            except Exception:
                logger.exception("Failed to initialize discovery engine")
                self._discovery_engine = False
                return None
        if self._discovery_engine is False:
            return None
        engine = self._discovery_engine
        if engine.should_run():
            try:
                logger.debug("Running discovery engine")
                await engine.collect()
            except Exception:
                logger.exception("Discovery engine collection failed")
                return None
        if engine.has_fresh():
            return engine.get_recent()
        return None

    def _voice_state(self) -> Any | None:
        engine = self._voice()
        if engine is None:
            return None
        try:
            return engine.genome
        except Exception:
            return None

    def _voice_state_or_default(self, voice: Any | None) -> Any:
        if voice is not None:
            return voice
        if not hasattr(self, "_default_voice_genome"):
            from voice_engine import VoiceGenome
            self._default_voice_genome = VoiceGenome()
        return self._default_voice_genome

    def _dominant_voice(self, voice: Any) -> str:
        try:
            from voice_engine import STYLE_DIMENSIONS
            return max(STYLE_DIMENSIONS, key=lambda dim: getattr(voice, dim))
        except Exception:
            return "proactive"

    def _is_llm_fallback(self, msg_type: str, content: str) -> bool:
        try:
            from llm_message_composer import FALLBACK_CONTENT, FALLBACK_MSG_TYPE
            return msg_type == FALLBACK_MSG_TYPE and content == FALLBACK_CONTENT
        except Exception:
            return False

    def _user_active_recently(self) -> bool:
        """Check if proactive message should be suppressed due to recent activity.

        Returns True (suppress) if ANY of:
        - Hermes is currently processing a session
        - The last message is from the user (user is waiting for a reply)
        - The last message (from either side) was < 30 minutes ago

        Only allows proactive messages when the conversation is truly idle:
        no session is running, Hermes sent the last message, and the entire
        conversation has been silent for 30+ minutes.  This prevents Alive from
        interrupting while Hermes is still working on a long task.
        """
        try:
            from context_tracker import activity_snapshot, is_session_busy

            if is_session_busy():
                logger.debug("Activity guard: session busy, suppressing")
                return True

            snapshot = activity_snapshot(refresh=True)
            if not snapshot.get("has_context"):
                return False

            now = time.time()
            last_role = snapshot.get("last_message_role")
            if last_role == "user":
                logger.debug("Activity guard: last message is from user, suppressing")
                return True

            last_msg_ts = snapshot.get("last_message_timestamp")
            if last_msg_ts is not None:
                seconds_since_last = now - float(last_msg_ts)
                if seconds_since_last < 1800:
                    logger.debug("Activity guard: last message %.0fs ago (< 1800s), suppressing", seconds_since_last)
                    return True

            return False
        except Exception:
            logger.exception("_user_active_recently failed")
            return True  # fail-safe: suppress on error

    def _extract_social_urge(self, voice: Any) -> float | None:
        """Extract social_urge value from the voice engine, return None if unavailable."""
        try:
            engine = self._voice()
            value = getattr(engine, "social_urge", None)
            if value is not None:
                return float(value)
            return None
        except Exception:
            return None

    def _feature_enabled(self, env_name: str) -> bool:
        raw = os.getenv(env_name)
        if raw is None:
            return self.enabled
        return _truthy(raw)

    def _llm_model_name(self) -> str:
        return os.getenv(LLM_MODEL_ENV, os.getenv("HERMES_PROACTIVE_MODEL", "deepseek-v4-flash-ascend")).strip() or "deepseek-v4-flash-ascend"

    async def _check_dream(self) -> None:
        """Run dream memory consolidation if interval has elapsed."""
        if self._dream_engine is None:
            try:
                from dream_engine import DreamEngine
                self._dream_engine = DreamEngine()
            except Exception:
                logger.exception("Failed to initialize dream engine")
                self._dream_engine = False
                return
        if self._dream_engine is False:
            return
        engine = self._dream_engine
        if engine.should_run():
            try:
                logger.debug("Running dream consolidation cycle")
                diff = await engine.run_dream_cycle()
                voice_after = {}
                try:
                    from voice_engine import VoiceEngine, STYLE_DIMENSIONS
                    ve = VoiceEngine()
                    voice_after = {dim: round(float(getattr(ve.genome, dim, 0.0)), 2) for dim in STYLE_DIMENSIONS}
                    voice_after["social_urge"] = round(float(ve.social_urge), 2)
                except Exception:
                    pass
                self._log("dream", reason="dream_cycle_complete",
                          ops=len(diff.operations),
                          prunes=len(diff.prune_candidates),
                          summary=diff.summary,
                          voice_after=voice_after)
            except Exception:
                logger.exception("Dream consolidation failed")

    def _metadata(self, generated_by: str) -> dict[str, Any]:
        metadata = dict(SYSTEM_METADATA)
        metadata.update({
            "actor": "model",
            "source": "model",
            "message_origin": "model",
            "origin": "model",
            "model_name": generated_by,
            "resolved_model": generated_by,
            "routed_model": generated_by,
            "model": generated_by,
        })
        metadata["is_system"] = False  # proactive messages are from the model, not the system
        return metadata

    def _log(self, decision: str, **extra: Any) -> None:
        record = {
            "decision": decision,
            "watcher_id": self.watcher_id,
            "pid": os.getpid(),
            "started_at": self.started_at,
        }
        record.update(extra)
        try:
            append_jsonl(PROACTIVE_LOG, record, "proactive_log.lock")
        except Exception:
            logger.exception("Failed to write proactive log entry")

    def _log_discovery(self, tick_id: str, ctx: dict[str, Any]) -> None:
        """Log discovery results: source names and item counts."""
        external = ctx.get("external", []) or []
        local = ctx.get("local", []) or []

        # Count by source
        source_counts: dict[str, int] = {}
        for item in external:
            src = item.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        self._log(
            "discovery",
            tick_id=tick_id,
            external_count=len(external),
            local_count=len(local),
            sources=list(source_counts.keys()),
            source_counts=source_counts,
        )

    def _log_compose(
        self,
        tick_id: str,
        voice: Any,
        discovery_context: dict[str, Any] | None,
        msg_type: str,
        generated_by: str,
    ) -> None:
        """Log compose context: voice snapshot, model, discovery availability, msg type."""
        voice_snapshot: dict[str, float] = {}
        if voice is not None:
            try:
                from voice_engine import STYLE_DIMENSIONS
                voice_snapshot = {dim: round(float(getattr(voice, dim, 0.0)), 2) for dim in STYLE_DIMENSIONS}
                engine = self._voice()
                if engine is not None:
                    voice_snapshot["social_urge"] = round(float(getattr(engine, "social_urge", 0.0)), 2)
            except Exception:
                pass

        had_discovery = discovery_context is not None
        external_n = len(discovery_context.get("external", []) or []) if had_discovery else 0
        local_n = len(discovery_context.get("local", []) or []) if had_discovery else 0

        self._log(
            "compose",
            tick_id=tick_id,
            model=generated_by,
            msg_type=msg_type,
            voice=voice_snapshot,
            had_discovery=had_discovery,
            discovery_items=external_n + local_n,
        )

def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}

def _redact_chat(chat_id: str) -> str:
    if len(chat_id) <= 8:
        return "<redacted>"
    return chat_id[:4] + "..." + chat_id[-4:]
