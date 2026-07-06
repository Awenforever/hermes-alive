
"""Hermes Alive hook event dispatcher."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
# Hermes Alive import path bootstrap
_HOOK_DIR = os.getenv("HERMES_HOOK_DIR", "/opt/data/hooks/hermes-alive")
_SHARED_DIR = os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")
for _p in (_HOOK_DIR, _SHARED_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pathlib import Path


logger = logging.getLogger(__name__)
_watcher_task: asyncio.Task | None = None

async def handle(event_type: str, context: dict):
    logger.warning("[Hermes Alive] handle() called, event=%s", event_type)
    if event_type == "gateway:startup":
        await _startup(context)
    elif event_type == "session:start":
        await _on_session_start(context)
    elif event_type == "agent:end":
        await _on_agent_end(context)
    else:
        logger.warning("Hermes Alive: unknown event type %s", event_type)

async def _startup(context: dict):
    global _watcher_task
    if not _env_enabled():
        logger.warning("Hermes Alive: env disabled")
        return

    if _watcher_task is not None and not _watcher_task.done():
        logger.warning("Hermes Alive: watcher already running in this process; skip duplicate startup")
        return

    try:
        from proactive_watcher import ProactivePlatformWatcher
    except ImportError as e:
        logger.warning("Hermes Alive: watcher import failed: %s", e)
        return

    try:
        from gateway.run import _gateway_runner_ref
    except ImportError as e:
        logger.warning("Hermes Alive: gateway import failed: %s", e)
        return

    runner = _gateway_runner_ref()
    if runner is None:
        logger.warning("Hermes Alive: no runner")
        return

    _watcher_task = asyncio.create_task(
        ProactivePlatformWatcher(runner.adapters, runner.config).run(),
        name="hermes-alive-watcher",
    )

    def _done(task: asyncio.Task):
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            logger.warning("Hermes Alive watcher cancelled")
            return
        if exc:
            logger.exception("Hermes Alive watcher died", exc_info=exc)
        else:
            logger.warning("Hermes Alive watcher exited")

    _watcher_task.add_done_callback(_done)
    logger.warning("Hermes Alive: watcher task created")

async def _on_session_start(context: dict):
    try:
        from context_tracker import set_session_busy
        set_session_busy()
        logger.debug("Hermes Alive activity guard marked session busy")
    except Exception:
        logger.exception("Failed to mark session busy")

    try:
        from safe_io import atomic_write_text
        from voice_engine import VoiceEngine
        engine = VoiceEngine()
        engine.on_interaction_start(context if isinstance(context, dict) else {})
        voice_file = Path(_SHARED_DIR) / "current_voice.txt"
        atomic_write_text(voice_file, engine.snapshot_prompt())
        logger.info("Voice touched on session start: stage=%s", engine.genome.relationship_stage)
    except Exception:
        logger.exception("Failed to update voice on session start")

async def _on_agent_end(context: dict):
    try:
        from context_tracker import set_session_idle
        set_session_idle()
        logger.debug("Hermes Alive activity guard marked session idle")
    except Exception:
        logger.exception("Failed to mark session idle")

    # Capture recent conversation context for proactive injection
    captured = {}
    try:
        from context_tracker import capture_recent_context
        captured = capture_recent_context()
    except Exception:
        logger.exception("Failed to capture recent context on agent end")

    try:
        from safe_io import atomic_write_text
        from voice_engine import VoiceEngine
        signals = {}
        if isinstance(captured, dict):
            signals = captured.get("user_style_signals", {}) if isinstance(captured.get("user_style_signals"), dict) else {}
        engine = VoiceEngine()
        engine.on_agent_end(signals)
        voice_file = Path(_SHARED_DIR) / "current_voice.txt"
        atomic_write_text(voice_file, engine.snapshot_prompt())
        logger.info("Voice evolved on agent end: stage=%s message_count=%s", engine.genome.relationship_stage, engine.message_count)
    except Exception:
        logger.exception("Failed to evolve voice on agent end")

def _env_enabled() -> bool:
    return os.getenv("HERMES_PROACTIVE_PLATFORM_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
