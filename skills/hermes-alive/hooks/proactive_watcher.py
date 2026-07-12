
"""Gateway-native proactive platform watcher for Hermes Alive."""
# Marker: RICH_CONTENT_DELIVERY_V1
# Marker: RICH_CONTENT_METADATA_V1
# Marker: RICH_CONTENT_REFERENCE_V1
# Marker: HERMES_ALIVE_CIRCADIAN_WATCHER_SHADOW_V1
# Marker: HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_POLICY_SHADOW_V1
# Marker: HERMES_ALIVE_PROACTIVE_QUALITY_GOVERNOR_SHADOW_V1
# Marker: HERMES_ALIVE_ISOLATED_DELIVERY_ENFORCEMENT_V1

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
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
from weixin_peer import (
    adapter_context_token_present,
    resolve_weixin_peer,
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
        self._interruption_policy: Any | None = None
        self._content_delivery_engine: Any | None = None
        self._circadian_engine: Any | None = None
        self._proactive_quality_governor: Any | None = None
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

        circadian_decision = self._circadian_shadow_decision(
            message_class="proactive_social",
        )
        if circadian_decision is not None:
            self._log(
                "circadian_shadow",
                tick_id=tick_id,
                integration_mode="observe_only",
                behavior_changed=False,
                circadian=circadian_decision,
            )

        sleep_quiet_decision = self._sleep_quiet_policy_shadow_decision(
            circadian_decision,
            message_class="proactive_social",
        )
        if sleep_quiet_decision is not None:
            self._log(
                "sleep_quiet_policy_shadow",
                tick_id=tick_id,
                integration_mode="observe_only",
                behavior_changed=False,
                sleep_quiet_policy=sleep_quiet_decision,
            )

        voice = self._voice_state()

        # ── Interruption policy: decide if/how Alive may speak ──
        user_active = self._user_active_recently()

        quality_pre_decision = self._proactive_quality_shadow_decision(
            user_active=user_active,
        )
        if quality_pre_decision is not None:
            self._log(
                "proactive_quality_shadow",
                tick_id=tick_id,
                integration_mode="observe_only",
                behavior_changed=False,
                quality_governor=quality_pre_decision,
            )

        enforcement_pre = self._isolated_precompose_enforcement(
            sleep_quiet_decision,
            quality_pre_decision,
        )
        if enforcement_pre is not None and bool(enforcement_pre.get("enabled")):
            self._log(
                "isolated_enforcement_precompose",
                tick_id=tick_id,
                enforcement=enforcement_pre,
            )
            if bool(enforcement_pre.get("block")):
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason=str((enforcement_pre.get("reasons") or ["isolated_enforcement_block"])[0]),
                    isolated_enforcement=True,
                )
                return False

        policy_decision = self._evaluate_interruption_policy(
            user_active=user_active,
            discovery_available=False,
            cooldown_allowed=True,
            cooldown_reason=None,
        )
        if policy_decision is not None:
            self._log("policy", tick_id=tick_id, interruption_policy=policy_decision)
            if not bool(policy_decision.get("allow_send", True)):
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason=str(policy_decision.get("skip_reason") or "interruption_policy_silent"),
                    interruption_policy=policy_decision,
                )
                return False

        if user_active and not (policy_decision and bool(policy_decision.get("allow_when_user_active", False))):
            self._log("skip", tick_id=tick_id, reason="user_active", interruption_policy=policy_decision)
            return False

        cooldown = self._cooldown()
        if cooldown is not None:
            # Set voice-linked cooldown before checking
            social_urge = self._extract_social_urge(voice)
            cooldown.set_mood_cooldown(social_urge)
            allowed, reason = cooldown.can_send("proactive")
            if not allowed:
                quiet_override = self._isolated_legacy_quiet_override(
                    sleep_quiet_decision,
                ) if reason == "quiet_hours" else None
                if quiet_override is not None and bool(quiet_override.get("override")):
                    self._log(
                        "isolated_enforcement_legacy_quiet_override",
                        tick_id=tick_id,
                        enforcement=quiet_override,
                    )
                else:
                    cooldown_policy = self._evaluate_interruption_policy(
                        user_active=user_active,
                        discovery_available=False,
                        cooldown_allowed=False,
                        cooldown_reason=reason,
                    )
                    self._log("skip", tick_id=tick_id, reason=reason, quiet_hours=(reason == "quiet_hours"), interruption_policy=cooldown_policy)
                    return False

        import random
        if policy_decision is not None and not bool(policy_decision.get("allow_content_share", True)):
            discovery_context = None
            self._log("policy", tick_id=tick_id, reason="content_share_disabled", interruption_policy=policy_decision)
        else:
            discovery_context = await self._check_discovery()
        if discovery_context is not None:
            self._log_discovery(tick_id, discovery_context)
        await self._check_dream()
        messages = await self._compose_message(
            voice,
            discovery_context,
            policy_decision=policy_decision,
        )
        messages, content_ref = (
            self._extract_content_reference(
                messages,
            )
        )
        messages = self._enforce_policy_messages(
            messages,
            policy_decision,
        )

        delivery = self._content_delivery()
        delivery_plan: Any | None = None
        rich_payload: Any | None = None
        selected_delivery_item: dict[str, Any] | None = None
        if delivery is not None:
            try:
                delivery_plan = delivery.plan(
                    messages,
                    discovery_context,
                    policy_decision,
                    content_ref=content_ref,
                )
                messages = delivery_plan.text_messages
                rich_payload = delivery_plan.rich_payload
                selected_delivery_item = delivery_plan.selected_item
                self._log(
                    "delivery_plan",
                    tick_id=tick_id,
                    text_units=len(messages),
                    rich_kind=(
                        rich_payload.kind
                        if rich_payload is not None
                        else None
                    ),
                    evidence_score=delivery_plan.evidence_score,
                    max_units=delivery_plan.max_units,
                    content_ref=content_ref,
                )
            except Exception:
                logger.exception(
                    "Failed to build rich-content delivery plan"
                )
                delivery_plan = None
                rich_payload = None
                selected_delivery_item = None

        quality_candidate_audits = self._quality_candidate_shadow_audits(
            messages,
            quality_pre_decision,
        )
        for audit_index, audit in enumerate(quality_candidate_audits, start=1):
            self._log(
                "proactive_quality_candidate_shadow",
                tick_id=tick_id,
                audit_index=audit_index,
                integration_mode="observe_only",
                behavior_changed=False,
                quality_candidate=audit,
            )

        messages, quality_filter = self._apply_isolated_quality_enforcement(
            messages,
            quality_candidate_audits,
        )
        if quality_filter is not None and bool(quality_filter.get("enabled")):
            self._log(
                "isolated_enforcement_candidate_filter",
                tick_id=tick_id,
                enforcement=quality_filter,
            )

        if not messages and rich_payload is None:
            self._log(
                "skip",
                tick_id=tick_id,
                reason="empty_delivery_plan",
            )
            return False

        msg_count = len(messages)
        sent_messages: list[tuple[str, str, str]] = []
        for msg_index, (msg_type, content, generated_by) in enumerate(messages, start=1):
            self._log_compose(tick_id, voice, discovery_context, msg_type, generated_by)

            metadata = self._metadata(generated_by)
            if delivery is not None:
                outcome = await delivery.send_text(
                    adapter,
                    chat_id,
                    content,
                    metadata=metadata,
                )
                if not outcome.success:
                    self._log(
                        "error",
                        tick_id=tick_id,
                        reason="adapter_send_failed",
                        error=outcome.error or "send_result_unsuccessful",
                        msg_type=msg_type,
                        msg_index=msg_index,
                        msg_count=msg_count,
                    )
                    continue
            else:
                try:
                    result = await adapter.send(
                        chat_id,
                        content,
                        metadata=metadata,
                    )
                    if getattr(result, "success", True) is False:
                        self._log(
                            "error",
                            tick_id=tick_id,
                            reason="adapter_send_unsuccessful",
                            error=str(
                                getattr(result, "error", "")
                                or "send_result_unsuccessful"
                            ),
                            msg_type=msg_type,
                            msg_index=msg_index,
                            msg_count=msg_count,
                        )
                        continue
                except Exception as exc:
                    self._log(
                        "error",
                        tick_id=tick_id,
                        reason="adapter_send_failed",
                        error=type(exc).__name__,
                        msg_type=msg_type,
                        msg_index=msg_index,
                        msg_count=msg_count,
                    )
                    logger.exception(
                        "Failed to send proactive platform message"
                    )
                    continue

            sent_messages.append((msg_type, content, generated_by))
            self._commit_isolated_quality_delivery(
                content,
                quality_candidate_audits,
            )

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

        rich_outcome: Any | None = None
        if (
            delivery is not None
            and rich_payload is not None
        ):
            rich_metadata = self._metadata(
                rich_payload.generated_by
            )
            rich_outcome = await delivery.send_rich(
                adapter,
                chat_id,
                rich_payload,
                metadata=rich_metadata,
            )
            self._log(
                "rich_delivery"
                if rich_outcome.success
                else "rich_delivery_error",
                tick_id=tick_id,
                rich_kind=rich_outcome.kind,
                delivery_mode=rich_outcome.mode,
                content_delivered=rich_outcome.content_delivered,
                fallback_used=rich_outcome.fallback_used,
                error=rich_outcome.error,
                content_item_id=rich_payload.content_item_id,
                generated_by=rich_payload.generated_by,
            )

        rich_success = bool(
            rich_outcome is not None
            and rich_outcome.success
        )
        sent_any = bool(sent_messages) or rich_success

        if sent_any and cooldown is not None:
            cooldown_type = (
                sent_messages[0][0]
                if sent_messages
                else str(
                    getattr(rich_payload, "kind", "proactive")
                )
            )
            cooldown.record_send(cooldown_type)

        if (
            rich_outcome is not None
            and rich_outcome.content_delivered
            and isinstance(selected_delivery_item, dict)
        ):
            self._record_interest_delivery(
                discovery_context,
                tick_id,
                sent_messages,
                delivered_item=selected_delivery_item,
            )
        elif sent_messages:
            self._record_interest_delivery(
                discovery_context,
                tick_id,
                sent_messages,
            )

        return sent_any

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
        """Resolve the first adapter and a canonical platform chat target.

        Weixin QR credentials identify the bot account, while inbound DM
        sessions and context tokens are keyed by the human peer. Resolve the
        configured value to a context-bearing peer when runtime evidence is
        unambiguous; never guess between multiple peers.
        """
        weixin_adapter: Any | None = None

        for key, adapter in self.adapters.items():
            key_value = getattr(key, "value", key)

            if str(key_value) == "weixin":
                weixin_adapter = adapter
                continue

            platform = str(key_value).upper()
            chat_id = os.getenv(
                f"HERMES_PROACTIVE_{platform}_CHAT_ID",
                "",
            ).strip()

            if chat_id:
                logger.debug(
                    "Found adapter for platform=%s with configured chat_id",
                    key_value,
                )
                return adapter, chat_id

        if weixin_adapter is not None:
            configured = os.getenv(
                CHAT_ID_ENV,
                "",
            ).strip()

            resolved, reason = resolve_weixin_peer(
                configured,
                account_id=str(
                    getattr(
                        weixin_adapter,
                        "_account_id",
                        "",
                    )
                    or ""
                ),
            )

            if resolved:
                token_present = (
                    adapter_context_token_present(
                        weixin_adapter,
                        resolved,
                    )
                )

                self._log(
                    "peer_resolution",
                    reason="weixin_peer_resolution",
                    configured_chat_hash=(
                        sha256_text(configured)
                        if configured
                        else None
                    ),
                    resolved_chat_hash=sha256_text(
                        resolved
                    ),
                    chat_resolution=reason,
                    context_token_present=token_present,
                )

                logger.debug(
                    "Resolved Weixin proactive target mode=%s token=%s",
                    reason,
                    token_present,
                )
                return weixin_adapter, resolved

        logger.warning(
            "No adapter with a configured "
            "HERMES_PROACTIVE_{PLATFORM}_CHAT_ID found"
        )
        return None, None

    async def _process_control_queue(
        self,
        adapter: Any,
        chat_id: str,
        tick_id: str,
    ) -> bool:
        if not QUEUE.exists():
            return False

        from safe_io import LOCK_DIR

        queue_lock = (
            LOCK_DIR
            / "control_queue_process.lock"
        )

        with file_lock(queue_lock):
            try:
                lines = QUEUE.read_text(
                    encoding="utf-8"
                ).splitlines()
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

                if (
                    item.get("type") == "test"
                    and not sent_any
                ):
                    content = str(
                        item.get("message")
                        or "Hermes Alive 主动推送测试。"
                    )
                    generated_by = str(
                        item.get("generated_by")
                        or "hermes"
                    )

                    try:
                        result = await adapter.send(
                            chat_id,
                            content,
                            metadata=self._metadata(
                                generated_by
                            ),
                        )
                    except Exception as exc:
                        self._log(
                            "error",
                            tick_id=tick_id,
                            reason=(
                                "alive_test_send_exception"
                            ),
                            error=type(exc).__name__,
                        )
                        remaining.append(line)
                        continue

                    if (
                        getattr(
                            result,
                            "success",
                            True,
                        )
                        is False
                    ):
                        self._log(
                            "error",
                            tick_id=tick_id,
                            reason=(
                                "alive_test_send_unsuccessful"
                            ),
                            error=str(
                                getattr(
                                    result,
                                    "error",
                                    "",
                                )
                                or "send_result_unsuccessful"
                            ),
                            adapter_result_type=type(
                                result
                            ).__name__,
                        )
                        remaining.append(line)
                        continue

                    self._log(
                        "sent",
                        tick_id=tick_id,
                        reason="alive_test",
                        msg_type="test",
                        generated_by=generated_by,
                        message_hash=sha256_text(
                            content
                        ),
                        message_preview=redact_preview(
                            content
                        ),
                        adapter_result="ok",
                        adapter_result_type=type(
                            result
                        ).__name__,
                    )
                    sent_any = True
                else:
                    remaining.append(line)

            locked_write_json(
                BASE / "control_queue_state.json",
                {
                    "last_processed_at":
                        datetime.now()
                        .astimezone()
                        .isoformat()
                },
                "control_queue.lock",
            )
            atomic_write_text(
                QUEUE,
                "\n".join(remaining)
                + ("\n" if remaining else ""),
            )
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

    def _policy(self) -> Any | None:
        if self._interruption_policy is None:
            try:
                from interruption_policy import InterruptionPolicy
                self._interruption_policy = InterruptionPolicy()
            except Exception:
                logger.exception("Failed to initialize interruption policy")
                self._interruption_policy = False
        return None if self._interruption_policy is False else self._interruption_policy

    def _evaluate_interruption_policy(
        self,
        *,
        user_active: bool,
        discovery_available: bool,
        cooldown_allowed: bool,
        cooldown_reason: str | None,
    ) -> dict[str, Any] | None:
        # INTERRUPTION_POLICY_V1
        policy = self._policy()
        if policy is None:
            return None
        try:
            return policy.evaluate(
                user_active=user_active,
                discovery_available=discovery_available,
                cooldown_allowed=cooldown_allowed,
                cooldown_reason=cooldown_reason,
            )
        except Exception:
            logger.exception("Interruption policy failed")
            return None

    def _circadian(self) -> Any | None:
        # HERMES_ALIVE_CIRCADIAN_WATCHER_SHADOW_V1
        if self._circadian_engine is None:
            try:
                from circadian_engine import CircadianEngine, load_circadian_config

                self._circadian_engine = CircadianEngine(
                    config=load_circadian_config(),
                )
            except Exception:
                logger.exception("Failed to initialize circadian engine")
                self._circadian_engine = False
        return None if self._circadian_engine is False else self._circadian_engine

    def _circadian_shadow_decision(
        self,
        *,
        message_class: str,
    ) -> dict[str, Any] | None:
        engine = self._circadian()
        if engine is None:
            return None
        try:
            decision = engine.shadow_decision(
                message_class=message_class,
            )
            if not isinstance(decision, dict):
                return None
            # This integration phase is observability-only even when a
            # malformed external configuration says live. The decision is
            # recorded, never enforced here.
            decision = dict(decision)
            decision["watcher_enforced"] = False
            decision["integration_mode"] = "observe_only"
            return decision
        except Exception:
            logger.exception("Circadian shadow decision failed")
            return None

    def _sleep_quiet_policy_shadow_decision(
        self,
        circadian_decision: dict[str, Any] | None,
        *,
        message_class: str,
    ) -> dict[str, Any] | None:
        # HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_POLICY_SHADOW_V1
        if not isinstance(circadian_decision, dict):
            return None
        try:
            from circadian_sleep_quiet_policy import evaluate_sleep_quiet_shadow

            decision = evaluate_sleep_quiet_shadow(
                circadian_decision,
                message_class=message_class,
            )
            if not isinstance(decision, dict):
                return None
            # This phase is comparison-only. Existing CooldownManager quiet
            # hours remain authoritative and this decision is never enforced.
            decision = dict(decision)
            decision["watcher_enforced"] = False
            decision["integration_mode"] = "observe_only"
            decision["behavior_changed"] = False
            return decision
        except Exception:
            logger.exception("Circadian sleep/quiet shadow decision failed")
            return None

    def _quality_governor(self) -> Any | None:
        # HERMES_ALIVE_PROACTIVE_QUALITY_GOVERNOR_SHADOW_V1
        if self._proactive_quality_governor is None:
            try:
                from proactive_quality_governor import ProactiveQualityGovernor

                self._proactive_quality_governor = ProactiveQualityGovernor()
            except Exception:
                logger.exception("Failed to initialize proactive quality governor")
                self._proactive_quality_governor = False
        return None if self._proactive_quality_governor is False else self._proactive_quality_governor

    def _proactive_quality_shadow_decision(
        self,
        *,
        user_active: bool,
    ) -> dict[str, Any] | None:
        governor = self._quality_governor()
        if governor is None:
            return None
        try:
            decision = governor.pre_decision(user_active=user_active)
            if not isinstance(decision, dict):
                return None
            decision = dict(decision)
            decision["watcher_enforced"] = False
            decision["integration_mode"] = "observe_only"
            decision["behavior_changed"] = False
            return decision
        except Exception:
            logger.exception("Proactive quality governor pre-decision failed")
            return None

    def _quality_candidate_shadow_audits(
        self,
        messages: list[tuple[str, str, str]],
        pre_decision: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        governor = self._quality_governor()
        if governor is None or not isinstance(pre_decision, dict):
            return []
        audits: list[dict[str, Any]] = []
        for msg_type, content, generated_by in messages:
            try:
                enforcement_enabled = self._isolated_enforcement_enabled()
                audit = governor.audit_candidate(
                    content,
                    pre_decision=pre_decision,
                    structured_state=None,
                    persist_shadow_state=not enforcement_enabled,
                )
                if not isinstance(audit, dict):
                    continue
                audit = dict(audit)
                audit["msg_type"] = str(msg_type)
                audit["generated_by"] = str(generated_by)
                audit["watcher_enforced"] = False
                audit["integration_mode"] = (
                    "isolated_enforcement_candidate"
                    if enforcement_enabled
                    else "observe_only"
                )
                audit["behavior_changed"] = False
                audits.append(audit)
            except Exception:
                logger.exception("Proactive quality candidate audit failed")
        return audits

    def _isolated_enforcement_gate(self) -> dict[str, Any] | None:
        try:
            from isolated_enforcement import enforcement_gate

            gate = enforcement_gate()
            return gate if isinstance(gate, dict) else None
        except Exception:
            logger.exception("Isolated enforcement gate failed")
            return None

    def _isolated_enforcement_enabled(self) -> bool:
        gate = self._isolated_enforcement_gate()
        return bool(gate and gate.get("enabled"))

    def _isolated_precompose_enforcement(
        self,
        sleep_quiet_decision: dict[str, Any] | None,
        quality_pre_decision: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        try:
            from isolated_enforcement import precompose_enforcement

            decision = precompose_enforcement(
                sleep_quiet_decision,
                quality_pre_decision,
            )
            return decision if isinstance(decision, dict) else None
        except Exception:
            logger.exception("Isolated precompose enforcement failed")
            return None

    def _isolated_legacy_quiet_override(
        self,
        sleep_quiet_decision: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        try:
            from isolated_enforcement import should_override_legacy_quiet

            decision = should_override_legacy_quiet(
                sleep_quiet_decision,
            )
            return decision if isinstance(decision, dict) else None
        except Exception:
            logger.exception("Isolated legacy quiet override failed")
            return None

    def _apply_isolated_quality_enforcement(
        self,
        messages: list[tuple[str, str, str]],
        audits: list[dict[str, Any]],
    ) -> tuple[list[tuple[str, str, str]], dict[str, Any] | None]:
        try:
            from isolated_enforcement import filter_quality_candidates

            filtered, decision = filter_quality_candidates(messages, audits)
            return list(filtered), decision if isinstance(decision, dict) else None
        except Exception:
            logger.exception("Isolated candidate enforcement failed")
            return messages, None

    def _commit_isolated_quality_delivery(
        self,
        content: str,
        audits: list[dict[str, Any]],
    ) -> bool:
        if not self._isolated_enforcement_enabled():
            return False
        message_hash = sha256_text(content)
        audit = next(
            (
                item
                for item in audits
                if isinstance(item, dict)
                and str(item.get("message_hash") or "") == message_hash
                and bool(item.get("would_allow"))
                and not bool(item.get("would_reject"))
            ),
            None,
        )
        if audit is None:
            return False
        governor = self._quality_governor()
        if governor is None:
            return False
        try:
            commit = getattr(governor, "commit_delivery", None)
            return bool(commit and commit(audit))
        except Exception:
            logger.exception("Failed to commit isolated quality delivery")
            return False

    def _extract_content_reference(
        self,
        messages: list[tuple[str, str, str]],
    ) -> tuple[
        list[tuple[str, str, str]],
        str | None,
    ]:
        # RICH_CONTENT_REFERENCE_V1
        visible: list[tuple[str, str, str]] = []
        content_ref: str | None = None

        for msg_type, content, generated_by in messages:
            if msg_type == "__content_ref__":
                candidate = str(
                    content or ""
                ).strip()
                if candidate and content_ref is None:
                    content_ref = candidate
                continue
            visible.append(
                (
                    msg_type,
                    content,
                    generated_by,
                )
            )

        return visible, content_ref

    def _content_delivery_evidence_score(
        self,
        item: dict[str, Any],
        sent_messages: list[tuple[str, str, str]],
    ) -> int:
        # INTEREST_LEARNING_DELIVERY_EVIDENCE_V1
        combined = "\n".join(str(message[1]) for message in sent_messages).lower()
        url = str(item.get("url") or "").strip().lower()
        title = str(item.get("title") or "").strip().lower()
        source = str(item.get("source") or "").strip().lower()

        if url and url in combined:
            return 100
        if title and len(title) >= 5 and title in combined:
            return 90

        score = 0
        ascii_tokens = [
            token for token in re.findall(r"[a-z0-9+#.]{3,}", title)
            if token not in {"with", "from", "that", "this", "the", "and", "for"}
        ]
        for token in set(ascii_tokens):
            if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", combined):
                score += 12

        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", title))
        bigrams = {chinese[index:index + 2] for index in range(max(0, len(chinese) - 1))}
        matched_bigrams = sum(1 for pair in bigrams if pair in combined)
        score += min(48, matched_bigrams * 8)

        if source and source in combined:
            score += 10

        content_types = {str(message[0]) for message in sent_messages}
        if content_types & {"news_reaction", "research_ping", "memory_recall"}:
            score += 10
        return score

    def _record_interest_delivery(
        self,
        discovery_context: dict[str, Any] | None,
        tick_id: str,
        sent_messages: list[tuple[str, str, str]],
        delivered_item: dict[str, Any] | None = None,
    ) -> bool:
        # INTEREST_LEARNING_DELIVERY_EVIDENCE_V1
        # RICH_CONTENT_DELIVERY_V1
        if isinstance(delivered_item, dict):
            try:
                from interest_learning import InterestLearningEngine
                normalized = InterestLearningEngine().record_delivery(
                    delivered_item,
                    tick_id=tick_id,
                )
                self._log(
                    "content_delivery",
                    tick_id=tick_id,
                    content_item_id=normalized.get("id"),
                    content_source=normalized.get("source"),
                    content_tags=normalized.get("tags"),
                    evidence_score="structured_delivery",
                )
                return True
            except Exception:
                logger.exception(
                    "Failed to record structured content delivery"
                )
                return False

        if not isinstance(discovery_context, dict) or not sent_messages:
            return False
        external = discovery_context.get("external")
        if not isinstance(external, list) or not external:
            return False

        candidates: list[tuple[int, dict[str, Any]]] = []
        for item in external:
            if isinstance(item, dict):
                candidates.append((self._content_delivery_evidence_score(item, sent_messages), item))
        if not candidates:
            return False

        score, item = max(candidates, key=lambda value: value[0])
        if score < 20:
            self._log(
                "content_delivery_skipped",
                tick_id=tick_id,
                reason="no_delivery_evidence",
                evidence_score=score,
            )
            return False

        try:
            from interest_learning import InterestLearningEngine
            normalized = InterestLearningEngine().record_delivery(item, tick_id=tick_id)
            self._log(
                "content_delivery",
                tick_id=tick_id,
                content_item_id=normalized.get("id"),
                content_source=normalized.get("source"),
                content_tags=normalized.get("tags"),
                evidence_score=score,
            )
            return True
        except Exception:
            logger.exception("Failed to record interest-learning delivery")
            return False

    def _content_delivery(self) -> Any | None:
        # RICH_CONTENT_DELIVERY_V1
        if self._content_delivery_engine is None:
            try:
                from content_delivery import ContentDeliveryEngine
                self._content_delivery_engine = ContentDeliveryEngine()
            except Exception:
                logger.exception(
                    "Failed to initialize content delivery engine"
                )
                self._content_delivery_engine = False
        return (
            None
            if self._content_delivery_engine is False
            else self._content_delivery_engine
        )

    def _policy_fallback_message(self, policy_decision: dict[str, Any] | None) -> str:
        # INTERRUPTION_POLICY_ENFORCEMENT_V1
        # EMOJI_SOFT_POLICY_V1: emoji is guided by context, never hard-stripped.
        if not isinstance(policy_decision, dict):
            return "嘿，我在"
        if not bool(policy_decision.get("allow_send", True)):
            return ""
        try:
            level = int(policy_decision.get("level", 2))
        except Exception:
            level = 2
        acts = policy_decision.get("preferred_speech_acts")
        preferred = [str(x) for x in acts] if isinstance(acts, list) else []
        if level <= 0:
            return ""
        if level == 1:
            if "debug_companion" in preferred:
                return "你继续，我不插嘴"
            if "care" in preferred:
                return "这会儿先别把自己拧太紧"
            return "我在"
        if level >= 3:
            if "sulk" in preferred:
                return "呵，又不理我"
            if "poke" in preferred:
                return "人呢"
            return "算了你忙"
        return "嘿，我在"

    def _enforce_policy_messages(
        self,
        messages: list[tuple[str, str, str]],
        policy_decision: dict[str, Any] | None,
    ) -> list[tuple[str, str, str]]:
        # INTERRUPTION_POLICY_ENFORCEMENT_V1
        if not isinstance(policy_decision, dict):
            return messages[:5]
        if not bool(policy_decision.get("allow_send", True)):
            return []

        try:
            max_bubbles = int(policy_decision.get("max_bubbles", 1))
        except Exception:
            max_bubbles = 1
        max_bubbles = max(1, min(5, max_bubbles))
        allow_emoji = bool(policy_decision.get("allow_emoji", True))  # compatibility metadata only
        allow_content_share = bool(policy_decision.get("allow_content_share", True))

        emoji_re = re.compile(
            "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]"
        )
        url_re = re.compile(r"https?://\S+", re.I)

        out: list[tuple[str, str, str]] = []
        for msg_type, content, generated_by in messages:
            cleaned = str(content).strip()
            if not cleaned:
                continue
            if not allow_content_share and (url_re.search(cleaned) or re.search(r"^\s*链接\s*[:：]", cleaned)):
                continue
            if cleaned:
                out.append((msg_type, cleaned, generated_by))
            if len(out) >= max_bubbles:
                break
        return out

    async def _compose_message(self, voice: Any | None = None, discovery_context: dict[str, Any] | None = None, policy_decision: dict[str, Any] | None = None) -> list[tuple[str, str, str]]:
        default_voice = self._voice_state_or_default(voice)
        if self._feature_enabled(LLM_ENABLED_ENV):
            llm_result = await self._compose_llm_message(default_voice, discovery_context, policy_decision=policy_decision)
            if llm_result is not None and len(llm_result) > 0:
                # Check if LLM result is actually a fallback
                msg_type, content = llm_result[0]
                if not self._is_llm_fallback(msg_type, content):
                    return [(m_type, m_content, self._llm_model_name()) for m_type, m_content in llm_result]
                logger.debug("LLM composer returned fallback; using heartbeat")
        fallback_content = self._policy_fallback_message(policy_decision)
        if not fallback_content:
            return []
        return [("heartbeat", fallback_content, "hermes")]

    async def _compose_llm_message(self, voice: Any, discovery_context: dict[str, Any] | None = None, policy_decision: dict[str, Any] | None = None) -> list[tuple[str, str]] | None:
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
            compose_context = {"trigger": self._dominant_voice(voice)}
            if policy_decision is not None:
                compose_context["interruption_policy"] = policy_decision
            return await self._llm_message_composer.compose(voice, context=compose_context, discovery_context=discovery_context)
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
        """Return True when Alive should suppress proactive sending.

        Allow only when all three activity-guard conditions are true:
        session is idle, the latest Weixin message is from Hermes, and that
        Hermes message is at least 30 minutes old.
        """
        try:
            from context_tracker import activity_snapshot, is_session_busy

            if is_session_busy():
                logger.debug("Activity guard: session busy, suppressing")
                return True

            snapshot = activity_snapshot(refresh=True)
            if not snapshot.get("has_context"):
                logger.debug("Activity guard: no conversation context, allowing")
                return False

            last_role = snapshot.get("last_message_role")
            if last_role != "assistant":
                logger.debug("Activity guard: last message role is %r, suppressing", last_role)
                return True

            last_msg_ts = snapshot.get("last_message_timestamp")
            if last_msg_ts is None:
                logger.debug("Activity guard: Hermes last-message timestamp missing, suppressing")
                return True

            seconds_since_last = time.time() - float(last_msg_ts)
            if seconds_since_last < 1800:
                logger.debug("Activity guard: Hermes last message %.0fs ago (< 1800s), suppressing", seconds_since_last)
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
        # RICH_CONTENT_METADATA_V1
        resolved = str(generated_by or "hermes").strip() or "hermes"
        if resolved == "hermes":
            return dict(SYSTEM_METADATA)

        metadata = dict(SYSTEM_METADATA)
        metadata.update({
            "actor": "model",
            "source": "model",
            "message_origin": "model",
            "origin": "model",
            "model_name": resolved,
            "resolved_model": resolved,
            "routed_model": resolved,
            "model": resolved,
        })
        metadata["is_system"] = False
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
