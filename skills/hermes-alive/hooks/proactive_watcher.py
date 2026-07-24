# Marker: WATCHER_REAL_PROVIDER_MODEL_V1
# Marker: RICH_CONTENT_LOGICAL_SENT_V1
# Marker: RICH_CONTENT_MODEL_ATTRIBUTION_V2

"""Gateway-native proactive platform watcher for Hermes Alive."""
# Marker: RICH_CONTENT_DELIVERY_V1
# Marker: RICH_CONTENT_METADATA_V1
# Marker: RICH_CONTENT_REFERENCE_V1
# Marker: HERMES_ALIVE_CIRCADIAN_WATCHER_SHADOW_V1
# Marker: HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_POLICY_SHADOW_V1
# Marker: HERMES_ALIVE_PROACTIVE_QUALITY_GOVERNOR_SHADOW_V1
# Marker: HERMES_ALIVE_ISOLATED_DELIVERY_ENFORCEMENT_V1
# Marker: HERMES_ALIVE_DISCOVERY_REFRESH_DECOUPLING_V2
# Marker: HERMES_ALIVE_UNANSWERED_DISCOVERY_PIVOT_V2
# Marker: HERMES_ALIVE_QUALITY_LIVE_ENFORCEMENT_V2
# Marker: HERMES_ALIVE_CONTENT_REF_VALIDATION_V3
# Marker: HERMES_ALIVE_QUALITY_OBSERVABILITY_V3
# Marker: HERMES_ALIVE_QUALITY_FAIL_CLOSED_RUNTIME_V3
# Marker: HERMES_ALIVE_QUALITY_AUDIT_ALIGNMENT_V3
# Marker: HERMES_ALIVE_THREE_STAGE_ACTIVITY_GUARD_V1
# Marker: HERMES_ALIVE_CONTEXT_VISIBILITY_OBSERVABILITY_V1
# Marker: HERMES_ALIVE_CONTEXT_GUARD_FAIL_CLOSED_V1
# Marker: HERMES_ALIVE_PER_OUTBOUND_ACTIVITY_GUARD_V1
# Marker: HERMES_ALIVE_DISCOVERY_TOPIC_DEDUP_V1
# Marker: HERMES_ALIVE_TOPIC_RESERVATION_SEND_GUARD_V1

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
        self._topic_dedup_engine: Any | None = None
        self._circadian_engine: Any | None = None
        self._proactive_quality_governor: Any | None = None
        self._last_activity_snapshot: dict[str, Any] = {}
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
        self._log_activity_guard(
            tick_id,
            stage="pre_discovery",
            user_active=user_active,
        )

        quality_pre_decision = self._proactive_quality_shadow_decision(
            user_active=user_active,
        )
        if quality_pre_decision is not None:
            self._log(
                "proactive_quality_shadow",
                tick_id=tick_id,
                integration_mode=str(
                    quality_pre_decision.get("integration_mode")
                    or "observe_only"
                ),
                watcher_enforced=bool(
                    quality_pre_decision.get("watcher_enforced")
                ),
                behavior_changed=bool(
                    quality_pre_decision.get("behavior_changed")
                ),
                quality_governor=quality_pre_decision,
            )

        enforcement_pre = self._quality_precompose_enforcement(
            sleep_quiet_decision,
            quality_pre_decision,
        )
        if enforcement_pre is not None and bool(enforcement_pre.get("enabled")):
            self._log(
                str(
                    enforcement_pre.get("log_event")
                    or "quality_precompose_enforcement"
                ),
                tick_id=tick_id,
                enforcement=enforcement_pre,
            )
            if bool(enforcement_pre.get("block")):
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason=str(
                        (
                            enforcement_pre.get("reasons")
                            or ["quality_enforcement_block"]
                        )[0]
                    ),
                    quality_enforcement=True,
                )
                return False

        policy_decision = self._evaluate_interruption_policy(
            voice=voice,
            user_active=user_active,
            discovery_available=False,
            cooldown_allowed=True,
            cooldown_reason=None,
        )
        deferred_for_discovery = False
        if policy_decision is not None:
            self._log(
                "policy",
                tick_id=tick_id,
                policy_stage="pre_discovery",
                interruption_policy=policy_decision,
            )
            if not bool(policy_decision.get("allow_send", True)):
                skip_reason = str(
                    policy_decision.get("skip_reason")
                    or "interruption_policy_silent"
                )
                deferred_for_discovery = (
                    skip_reason == "unanswered_no_novel_value"
                )
                if not deferred_for_discovery:
                    self._log(
                        "skip",
                        tick_id=tick_id,
                        reason=skip_reason,
                        interruption_policy=policy_decision,
                    )
                    return False
                self._log(
                    "policy_deferred",
                    tick_id=tick_id,
                    reason=skip_reason,
                    interruption_policy=policy_decision,
                )

        if user_active:
            self._log(
                "skip",
                tick_id=tick_id,
                reason="user_active_pre_discovery",
                interruption_policy=policy_decision,
            )
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
                        voice=voice,
                        user_active=user_active,
                        discovery_available=False,
                        cooldown_allowed=False,
                        cooldown_reason=reason,
                    )
                    self._log("skip", tick_id=tick_id, reason=reason, quiet_hours=(reason == "quiet_hours"), interruption_policy=cooldown_policy)
                    return False

        import random

        # Discovery refresh is independent from whether the current
        # conversational policy allows immediate sharing. This prevents a
        # stale debug/pressure flow from starving the background discovery
        # cache forever.
        discovery_context = await self._check_discovery()
        discovery_available = self._external_discovery_available(
            discovery_context
        )
        if discovery_context is not None:
            self._log_discovery(tick_id, discovery_context)

        user_active_after_discovery = self._user_active_recently()
        self._log_activity_guard(
            tick_id,
            stage="post_discovery_pre_compose",
            user_active=user_active_after_discovery,
        )
        if user_active_after_discovery:
            self._log(
                "skip",
                tick_id=tick_id,
                reason="user_active_after_discovery",
            )
            return False

        final_policy = self._evaluate_interruption_policy(
            voice=voice,
            user_active=user_active,
            discovery_available=discovery_available,
            cooldown_allowed=True,
            cooldown_reason=None,
        )
        if final_policy is not None:
            policy_decision = final_policy
            self._log(
                "policy",
                tick_id=tick_id,
                policy_stage="post_discovery",
                interruption_policy=policy_decision,
            )
            if not bool(policy_decision.get("allow_send", True)):
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason=str(
                        policy_decision.get("skip_reason")
                        or "interruption_policy_silent"
                    ),
                    interruption_policy=policy_decision,
                )
                return False

        compose_discovery_context = (
            discovery_context
            if policy_decision is None
            or bool(policy_decision.get("allow_content_share", True))
            else None
        )
        if (
            discovery_context is not None
            and compose_discovery_context is None
        ):
            self._log(
                "policy",
                tick_id=tick_id,
                reason="content_share_deferred_but_discovery_refreshed",
                interruption_policy=policy_decision,
            )

        await self._check_dream()
        messages = await self._compose_message(
            voice,
            compose_discovery_context,
            policy_decision=policy_decision,
        )

        user_active_before_send = self._user_active_recently()
        self._log_activity_guard(
            tick_id,
            stage="post_compose_pre_send",
            user_active=user_active_before_send,
        )
        if user_active_before_send:
            self._log(
                "skip",
                tick_id=tick_id,
                reason="user_active_before_send",
            )
            return False

        try:
            semantic_plan = dict(
                getattr(
                    self._llm_message_composer,
                    "last_semantic_plan",
                    {},
                )
                or {}
            )
        except Exception:
            semantic_plan = {}
        if semantic_plan:
            self._log(
                "semantic_bubble_plan",
                tick_id=tick_id,
                semantic_plan=semantic_plan,
            )
        content_ref_generated_by = (
            self._content_reference_generated_by(
                messages,
            )
        )
        messages, content_ref = (
            self._extract_content_reference(
                messages,
            )
        )
        if (
            isinstance(policy_decision, dict)
            and policy_decision.get("mode") == "novel_value"
        ):
            if not content_ref:
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason="novel_value_missing_content_ref",
                    interruption_policy=policy_decision,
                )
                return False
            if not self._content_reference_matches_discovery(
                content_ref,
                compose_discovery_context,
            ):
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason="novel_value_invalid_content_ref",
                    interruption_policy=policy_decision,
                )
                return False
        messages = self._enforce_policy_messages(
            messages,
            policy_decision,
        )

        delivery = self._content_delivery()
        delivery_plan: Any | None = None
        rich_payload: Any | None = None
        selected_delivery_item: dict[str, Any] | None = None
        topic_reservation: dict[str, Any] | None = None
        if delivery is not None:
            try:
                delivery_plan = delivery.plan(
                    messages,
                    compose_discovery_context,
                    policy_decision,
                    content_ref=content_ref,
                    content_generated_by=(
                        content_ref_generated_by
                    ),
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
                    rich_generated_by=(
                        rich_payload.generated_by
                        if rich_payload is not None
                        else None
                    ),
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
        for audit_index, audit in enumerate(
            quality_candidate_audits,
            start=1,
        ):
            self._log(
                "proactive_quality_candidate_shadow",
                tick_id=tick_id,
                audit_index=audit_index,
                integration_mode=str(
                    audit.get("integration_mode")
                    or "observe_only"
                ),
                watcher_enforced=bool(
                    audit.get("watcher_enforced")
                ),
                behavior_changed=bool(
                    audit.get("behavior_changed")
                ),
                quality_candidate=audit,
            )

        messages, quality_filter = self._apply_quality_enforcement(
            messages,
            quality_candidate_audits,
            quality_pre_decision,
        )
        if quality_filter is not None and bool(
            quality_filter.get("enabled")
        ):
            self._log(
                str(
                    quality_filter.get("log_event")
                    or "quality_candidate_enforcement"
                ),
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

        if isinstance(selected_delivery_item, dict):
            guard = self._topic_dedup()
            should_guard = bool(
                rich_payload is not None
                or content_ref
                or (
                    delivery_plan is not None
                    and int(getattr(delivery_plan, "evidence_score", 0)) >= 20
                )
            )
            if guard is not None and should_guard:
                decision = guard.reserve(
                    selected_delivery_item,
                    tick_id=tick_id,
                )
                topic_reservation = decision.to_dict()
                self._log(
                    "topic_dedup_reservation",
                    tick_id=tick_id,
                    allowed=decision.allowed,
                    reason=decision.reason,
                    canonical_url_hash=decision.identity.get("canonical_url_hash"),
                    topic_signature=decision.identity.get("topic_signature"),
                    topic_unit_id=decision.identity.get("topic_unit_id"),
                    age_seconds=decision.age_seconds,
                )
                if decision.blocked:
                    self._log(
                        "skip",
                        tick_id=tick_id,
                        reason="discovery_topic_recently_delivered",
                        topic_reason=decision.reason,
                        canonical_url_hash=decision.identity.get("canonical_url_hash"),
                        topic_signature=decision.identity.get("topic_signature"),
                    )
                    return False

        msg_count = len(messages)
        sent_messages: list[tuple[str, str, str]] = []
        delivery_interrupted_by_activity = False
        for msg_index, (msg_type, content, generated_by) in enumerate(messages, start=1):
            user_active_each_send = self._user_active_recently()
            self._log_activity_guard(
                tick_id,
                stage="pre_text_send",
                user_active=user_active_each_send,
                msg_index=msg_index,
                msg_count=msg_count,
            )
            if user_active_each_send:
                delivery_interrupted_by_activity = True
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason="user_active_before_text_send",
                    msg_type=msg_type,
                    msg_index=msg_index,
                    msg_count=msg_count,
                )
                break

            if topic_reservation is not None and isinstance(selected_delivery_item, dict):
                guard = self._topic_dedup()
                validation = (
                    guard.validate_reservation(
                        selected_delivery_item,
                        reservation_id=str(topic_reservation.get("reservation_id") or ""),
                    )
                    if guard is not None
                    else None
                )
                if validation is None or validation.blocked:
                    delivery_interrupted_by_activity = True
                    self._log(
                        "skip",
                        tick_id=tick_id,
                        reason="topic_reservation_invalid_before_text_send",
                        topic_reason=(validation.reason if validation is not None else "guard_unavailable"),
                        msg_index=msg_index,
                        msg_count=msg_count,
                    )
                    break

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
            self._commit_quality_delivery(
                content,
                quality_candidate_audits,
                quality_pre_decision,
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
            and not delivery_interrupted_by_activity
        ):
            user_active_before_rich = self._user_active_recently()
            self._log_activity_guard(
                tick_id,
                stage="pre_rich_send",
                user_active=user_active_before_rich,
            )
            rich_allowed = not user_active_before_rich
            if user_active_before_rich:
                delivery_interrupted_by_activity = True
                self._log(
                    "skip",
                    tick_id=tick_id,
                    reason="user_active_before_rich_send",
                    rich_kind=getattr(rich_payload, "kind", None),
                )

            if (
                rich_allowed
                and topic_reservation is not None
                and isinstance(selected_delivery_item, dict)
            ):
                guard = self._topic_dedup()
                validation = (
                    guard.validate_reservation(
                        selected_delivery_item,
                        reservation_id=str(
                            topic_reservation.get("reservation_id") or ""
                        ),
                    )
                    if guard is not None
                    else None
                )
                if validation is None or validation.blocked:
                    rich_allowed = False
                    delivery_interrupted_by_activity = True
                    self._log(
                        "skip",
                        tick_id=tick_id,
                        reason="topic_reservation_invalid_before_rich_send",
                        topic_reason=(
                            validation.reason
                            if validation is not None
                            else "guard_unavailable"
                        ),
                        rich_kind=getattr(rich_payload, "kind", None),
                    )

            if rich_allowed:
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

        if (
            rich_success
            and not sent_messages
            and rich_payload is not None
        ):
            self._record_rich_delivery_sent(
                tick_id,
                rich_payload,
                rich_outcome,
            )

        sent_any = bool(sent_messages) or rich_success

        if topic_reservation is not None and isinstance(selected_delivery_item, dict):
            guard = self._topic_dedup()
            reservation_id = str(topic_reservation.get("reservation_id") or "")
            if guard is not None:
                if sent_any:
                    committed = guard.commit_delivery(
                        selected_delivery_item,
                        tick_id=tick_id,
                        reservation_id=reservation_id,
                    )
                    self._log(
                        "topic_dedup_committed",
                        tick_id=tick_id,
                        reason=committed.reason,
                        canonical_url_hash=committed.identity.get("canonical_url_hash"),
                        topic_signature=committed.identity.get("topic_signature"),
                        topic_unit_id=committed.identity.get("topic_unit_id"),
                    )
                else:
                    guard.release(reservation_id=reservation_id)
                    self._log(
                        "topic_dedup_released",
                        tick_id=tick_id,
                        reason="no_delivery_succeeded",
                        canonical_url_hash=topic_reservation.get("canonical_url_hash"),
                        topic_signature=topic_reservation.get("topic_signature"),
                    )

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

    def _log_activity_guard(
        self,
        tick_id: str,
        *,
        stage: str,
        user_active: bool,
        msg_index: int | None = None,
        msg_count: int | None = None,
    ) -> None:
        snapshot = dict(self._last_activity_snapshot or {})
        safe_fields = {
            "stage": stage,
            "user_active": bool(user_active),
            "context_queue_sha256": snapshot.get("queue_sha256"),
            "context_queue_updated_at": snapshot.get("updated_at"),
            "context_queue_message_count": snapshot.get("message_count"),
            "context_queue_distinct_session_count": snapshot.get(
                "distinct_session_count"
            ),
            "context_queue_user_message_count": snapshot.get(
                "user_message_count"
            ),
            "context_queue_assistant_message_count": snapshot.get(
                "assistant_message_count"
            ),
            "context_queue_db_lag_seconds": snapshot.get(
                "queue_db_lag_seconds"
            ),
            "context_queue_matches_db": snapshot.get("queue_matches_db"),
            "context_queue_healthy": snapshot.get("queue_healthy"),
            "latest_context_role": snapshot.get("last_message_role"),
            "latest_context_age_seconds": snapshot.get(
                "latest_context_age_seconds"
            ),
            "session_busy_boolean": snapshot.get("session_busy"),
            "busy_lease_count": snapshot.get("busy_lease_count"),
            "activity_guard_reason_code": snapshot.get(
                "activity_guard_reason_code"
            ),
            "msg_index": msg_index,
            "msg_count": msg_count,
        }
        self._log(
            "activity_guard",
            tick_id=tick_id,
            activity_guard=safe_fields,
        )

    def _evaluate_interruption_policy(
        self,
        *,
        voice: Any | None,
        user_active: bool,
        discovery_available: bool,
        cooldown_allowed: bool,
        cooldown_reason: str | None,
    ) -> dict[str, Any] | None:
        # INTERRUPTION_POLICY_V1
        # HERMES_ALIVE_PERSONALITY_DISPOSITION_INTEGRATION_V1
        policy = self._policy()
        if policy is None:
            return None
        try:
            return policy.evaluate(
                voice=voice,
                social_urge=self._extract_social_urge(voice),
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

    def _quality_enforcement_requested(self) -> bool:
        return (
            str(
                os.getenv(
                    "HERMES_ALIVE_QUALITY_GOVERNOR_MODE",
                    "shadow",
                )
                or "shadow"
            )
            .strip()
            .lower()
            == "enforce"
        )

    def _quality_governor(self) -> Any | None:
        # HERMES_ALIVE_PROACTIVE_QUALITY_GOVERNOR_SHADOW_V1
        if self._proactive_quality_governor is None:
            try:
                from proactive_quality_governor import ProactiveQualityGovernor

                self._proactive_quality_governor = ProactiveQualityGovernor()
            except Exception:
                logger.exception(
                    "Failed to initialize proactive quality governor"
                )
                self._proactive_quality_governor = False
        return (
            None
            if self._proactive_quality_governor is False
            else self._proactive_quality_governor
        )

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
            live = (
                str(decision.get("mode") or "").strip().lower()
                == "enforce"
            )
            decision["watcher_enforced"] = live
            decision["integration_mode"] = (
                "enforce" if live else "observe_only"
            )
            decision["behavior_changed"] = False
            return decision
        except Exception:
            logger.exception(
                "Proactive quality governor pre-decision failed"
            )
            return None

    def _quality_rejection_placeholder(
        self,
        message: tuple[str, str, str],
        *,
        reason: str,
        enforcement_enabled: bool,
        live: bool,
    ) -> dict[str, Any]:
        msg_type, content, generated_by = message
        return {
            "engine": "proactive_quality_governor",
            "version": 1,
            "mode": "enforce" if live else "shadow",
            "integration_mode": (
                "enforce"
                if live
                else (
                    "isolated_enforcement_candidate"
                    if enforcement_enabled
                    else "observe_only"
                )
            ),
            "watcher_enforced": bool(enforcement_enabled),
            "behavior_changed": bool(enforcement_enabled),
            "would_allow": False,
            "would_reject": True,
            "reasons": [str(reason)],
            "message_hash": sha256_text(content),
            "msg_type": str(msg_type),
            "generated_by": str(generated_by),
            "audit_placeholder": True,
        }

    def _quality_candidate_shadow_audits(
        self,
        messages: list[tuple[str, str, str]],
        pre_decision: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        live = self._quality_live_enforcement_enabled(
            pre_decision
        )
        enforcement_enabled = (
            live or self._isolated_enforcement_enabled()
        )
        governor = self._quality_governor()

        if governor is None or not isinstance(pre_decision, dict):
            if not enforcement_enabled:
                return []
            reason = (
                "quality_governor_unavailable"
                if governor is None
                else "quality_predecision_missing"
            )
            return [
                self._quality_rejection_placeholder(
                    message,
                    reason=reason,
                    enforcement_enabled=True,
                    live=live,
                )
                for message in messages
            ]

        audits: list[dict[str, Any]] = []
        for message in messages:
            msg_type, content, generated_by = message
            try:
                audit = governor.audit_candidate(
                    content,
                    pre_decision=pre_decision,
                    structured_state=None,
                    persist_shadow_state=not enforcement_enabled,
                )
                if not isinstance(audit, dict):
                    raise TypeError(
                        "quality audit did not return a dictionary"
                    )
                audit = dict(audit)
                audit["msg_type"] = str(msg_type)
                audit["generated_by"] = str(generated_by)
                audit["watcher_enforced"] = bool(
                    enforcement_enabled
                )
                audit["integration_mode"] = (
                    "enforce"
                    if live
                    else (
                        "isolated_enforcement_candidate"
                        if enforcement_enabled
                        else "observe_only"
                    )
                )
                audit["behavior_changed"] = bool(
                    enforcement_enabled
                    and (
                        bool(audit.get("would_reject"))
                        or not bool(audit.get("would_allow"))
                    )
                )
                audits.append(audit)
            except Exception:
                logger.exception(
                    "Proactive quality candidate audit failed"
                )
                if enforcement_enabled:
                    audits.append(
                        self._quality_rejection_placeholder(
                            message,
                            reason="quality_candidate_audit_failed",
                            enforcement_enabled=True,
                            live=live,
                        )
                    )
        return audits

    def _quality_live_enforcement_enabled(
        self,
        pre_decision: dict[str, Any] | None = None,
    ) -> bool:
        # The explicit managed/env contract remains authoritative even when
        # the governor cannot initialize or produce a pre-decision. Enforce
        # mode must never silently degrade to observe-only.
        if self._quality_enforcement_requested():
            return True
        if isinstance(pre_decision, dict):
            return (
                str(pre_decision.get("mode") or "").strip().lower()
                == "enforce"
            )
        governor = self._quality_governor()
        config = getattr(governor, "config", None)
        return (
            str(getattr(config, "mode", "") or "").strip().lower()
            == "enforce"
        )

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

    def _quality_precompose_enforcement(
        self,
        sleep_quiet_decision: dict[str, Any] | None,
        quality_pre_decision: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if self._quality_live_enforcement_enabled(
            quality_pre_decision
        ):
            reasons: list[str] = []
            if not isinstance(quality_pre_decision, dict):
                reasons.append("quality_predecision_missing")
            elif (
                str(
                    quality_pre_decision.get("mode") or ""
                ).strip().lower()
                != "enforce"
            ):
                reasons.append("quality_mode_mismatch")
            elif bool(
                quality_pre_decision.get("silence_lock")
            ):
                reasons.append("quality_silence_lock")
            return {
                "enabled": True,
                "mode": "enforce",
                "stage": "precompose",
                "block": bool(reasons),
                "allow": not bool(reasons),
                "reasons": reasons,
                "watcher_enforced": bool(reasons),
                "behavior_changed": bool(reasons),
                "log_event": "quality_precompose_enforcement",
            }

        try:
            from isolated_enforcement import precompose_enforcement

            decision = precompose_enforcement(
                sleep_quiet_decision,
                quality_pre_decision,
            )
            if not isinstance(decision, dict):
                return None
            result = dict(decision)
            result["log_event"] = (
                "isolated_enforcement_precompose"
            )
            return result
        except Exception:
            logger.exception("Quality precompose enforcement failed")
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

    def _apply_quality_enforcement(
        self,
        messages: list[tuple[str, str, str]],
        audits: list[dict[str, Any]],
        pre_decision: dict[str, Any] | None,
    ) -> tuple[
        list[tuple[str, str, str]],
        dict[str, Any] | None,
    ]:
        original = list(messages)
        if self._quality_live_enforcement_enabled(pre_decision):
            kept: list[tuple[str, str, str]] = []
            reason_counts: dict[str, int] = {}
            missing = 0
            rejected = 0
            for index, message in enumerate(original):
                if index >= len(audits):
                    missing += 1
                    rejected += 1
                    reason_counts["quality_audit_missing"] = (
                        reason_counts.get(
                            "quality_audit_missing",
                            0,
                        )
                        + 1
                    )
                    continue
                audit = audits[index]
                expected_hash = sha256_text(message[1])
                audit_hash = str(
                    audit.get("message_hash") or ""
                )
                if audit_hash != expected_hash:
                    rejected += 1
                    reason_counts["quality_audit_mismatch"] = (
                        reason_counts.get(
                            "quality_audit_mismatch",
                            0,
                        )
                        + 1
                    )
                    continue
                allowed = bool(audit.get("would_allow")) and not bool(
                    audit.get("would_reject")
                )
                if allowed:
                    kept.append(message)
                    continue
                rejected += 1
                reasons = audit.get("reasons")
                if not isinstance(reasons, list) or not reasons:
                    reasons = ["quality_candidate_rejected"]
                for reason in reasons:
                    key = str(
                        reason or "quality_candidate_rejected"
                    )
                    reason_counts[key] = (
                        reason_counts.get(key, 0) + 1
                    )
            return kept, {
                "enabled": True,
                "mode": "enforce",
                "stage": "candidate_filter",
                "original_count": len(original),
                "allowed_count": len(kept),
                "rejected_count": rejected,
                "missing_audit_count": missing,
                "rejection_reasons": reason_counts,
                "watcher_enforced": bool(rejected),
                "behavior_changed": bool(rejected),
                "log_event": "quality_candidate_enforcement",
            }

        try:
            from isolated_enforcement import filter_quality_candidates

            filtered, decision = filter_quality_candidates(
                original,
                audits,
            )
            if not isinstance(decision, dict):
                return list(filtered), None
            result = dict(decision)
            result["log_event"] = (
                "isolated_enforcement_candidate_filter"
            )
            return list(filtered), result
        except Exception:
            logger.exception("Quality candidate enforcement failed")
            return original, None

    def _commit_quality_delivery(
        self,
        content: str,
        audits: list[dict[str, Any]],
        pre_decision: dict[str, Any] | None,
    ) -> bool:
        if not (
            self._quality_live_enforcement_enabled(pre_decision)
            or self._isolated_enforcement_enabled()
        ):
            return False
        message_hash = sha256_text(content)
        audit = next(
            (
                item
                for item in audits
                if isinstance(item, dict)
                and str(item.get("message_hash") or "")
                == message_hash
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
            logger.exception("Failed to commit quality delivery")
            return False

    def _rich_delivery_logical_content(
        self,
        rich_payload: Any,
    ) -> str:
        # RICH_CONTENT_LOGICAL_SENT_V1
        for attribute in (
            "text",
            "title",
            "url",
            "image_url",
            "content_item_id",
            "source",
            "kind",
        ):
            value = str(
                getattr(rich_payload, attribute, "")
                or ""
            ).strip()
            if value:
                return value
        return "rich_content"

    def _record_rich_delivery_sent(
        self,
        tick_id: str,
        rich_payload: Any,
        rich_outcome: Any,
    ) -> None:
        # One rich payload may become multiple transport bubbles.
        # Record exactly one logical proactive send so unanswered
        # budgeting and semantic cooldowns advance correctly.
        logical_content = (
            self._rich_delivery_logical_content(
                rich_payload,
            )
        )
        generated_by = str(
            getattr(
                rich_payload,
                "generated_by",
                "hermes",
            )
            or "hermes"
        ).strip() or "hermes"
        self._log(
            "sent",
            tick_id=tick_id,
            reason="rich_proactive",
            msg_type="content_share",
            msg_index=1,
            msg_count=1,
            generated_by=generated_by,
            message_hash=sha256_text(
                logical_content,
            ),
            message_preview=redact_preview(
                logical_content,
            ),
            adapter_result="ok",
            logical_delivery=True,
            rich_kind=str(
                getattr(
                    rich_payload,
                    "kind",
                    "rich",
                )
                or "rich"
            ),
            delivery_mode=str(
                getattr(
                    rich_outcome,
                    "mode",
                    "rich",
                )
                or "rich"
            ),
            content_item_id=str(
                getattr(
                    rich_payload,
                    "content_item_id",
                    "",
                )
                or ""
            ),
        )

    def _content_reference_generated_by(
        self,
        messages: list[tuple[str, str, str]],
    ) -> str | None:
        # RICH_CONTENT_MODEL_ATTRIBUTION_V2
        for msg_type, content, generated_by in messages:
            if msg_type != "__content_ref__":
                continue
            if not str(content or "").strip():
                continue
            resolved = str(
                generated_by or "hermes"
            ).strip()
            return resolved or "hermes"
        return None

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

    def _topic_dedup(self) -> Any | None:
        if self._topic_dedup_engine is None:
            try:
                from topic_dedup import TopicDedupStore
                self._topic_dedup_engine = TopicDedupStore(BASE)
            except Exception:
                logger.exception("Failed to initialize topic dedup store")
                self._topic_dedup_engine = False
        return (
            None
            if self._topic_dedup_engine is False
            else self._topic_dedup_engine
        )

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
            if llm_result is not None:
                if len(llm_result) == 0:
                    rejection = str(
                        getattr(
                            self._llm_message_composer,
                            "last_rejection_reason",
                            "",
                        )
                        or ""
                    ).strip()
                    if rejection:
                        self._log(
                            "compose_rejected",
                            reason=rejection,
                        )
                    return []
                # Check if LLM result is actually a fallback
                msg_type, content = llm_result[0]
                if not self._is_llm_fallback(msg_type, content):
                    resolved_model = self._llm_model_name()
                    try:
                        actual_model = str(
                            getattr(
                                self._llm_message_composer,
                                "last_resolved_model",
                                "",
                            )
                            or ""
                        ).strip()
                    except Exception:
                        actual_model = ""
                    if actual_model:
                        resolved_model = actual_model
                    return [
                        (
                            m_type,
                            m_content,
                            resolved_model,
                        )
                        for m_type, m_content in llm_result
                    ]
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

    @staticmethod
    def _external_discovery_available(
        discovery_context: dict[str, Any] | None,
    ) -> bool:
        if not isinstance(discovery_context, dict):
            return False
        external = discovery_context.get("external")
        return bool(
            isinstance(external, list)
            and any(isinstance(item, dict) for item in external)
        )

    @staticmethod
    def _content_reference_matches_discovery(
        content_ref: str | None,
        discovery_context: dict[str, Any] | None,
    ) -> bool:
        """Verify a reference against the actual external Discovery set.

        The LLM composer already validates its marker, but the watcher is the
        final send boundary and must not trust alternate/future composers.
        """
        value = str(content_ref or "").strip()
        if not value or not isinstance(discovery_context, dict):
            return False
        external = discovery_context.get("external")
        if not isinstance(external, list):
            return False
        return any(
            isinstance(item, dict)
            and str(item.get("id") or "").strip() == value
            for item in external
        )

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
        """Fail closed unless Hermes is idle and the effective queue is healthy.

        This combines the in-process flag, shared cross-process activity
        leases, a rebuilt cross-session queue, and the latest effective role.
        """
        try:
            from context_tracker import activity_snapshot, is_session_busy

            if is_session_busy():
                self._last_activity_snapshot = {
                    "session_busy": True,
                    "queue_healthy": False,
                    "activity_guard_reason_code": "shared_or_local_session_busy",
                }
                logger.debug(
                    "Activity guard: shared/local session busy, suppressing"
                )
                return True

            snapshot = activity_snapshot(refresh=True)
            self._last_activity_snapshot = dict(snapshot)

            if bool(snapshot.get("session_busy")):
                self._last_activity_snapshot[
                    "activity_guard_reason_code"
                ] = "activity_snapshot_busy"
                return True

            if not bool(snapshot.get("queue_healthy", False)):
                self._last_activity_snapshot[
                    "activity_guard_reason_code"
                ] = "context_queue_unhealthy"
                logger.warning(
                    "Activity guard: context queue unhealthy, suppressing"
                )
                return True

            if not snapshot.get("has_context"):
                self._last_activity_snapshot[
                    "activity_guard_reason_code"
                ] = "no_context_allow_new_topic"
                return False

            last_role = snapshot.get("last_message_role")
            if last_role != "assistant":
                self._last_activity_snapshot[
                    "activity_guard_reason_code"
                ] = "latest_effective_role_not_assistant"
                return True

            last_msg_ts = snapshot.get("last_message_timestamp")
            if last_msg_ts is None:
                self._last_activity_snapshot[
                    "activity_guard_reason_code"
                ] = "latest_effective_timestamp_missing"
                return True

            seconds_since_last = time.time() - float(last_msg_ts)
            self._last_activity_snapshot[
                "latest_context_age_seconds"
            ] = max(0.0, seconds_since_last)
            if seconds_since_last < 1800:
                self._last_activity_snapshot[
                    "activity_guard_reason_code"
                ] = "latest_assistant_under_activity_window"
                return True

            self._last_activity_snapshot[
                "activity_guard_reason_code"
            ] = "idle_and_queue_healthy"
            return False
        except Exception:
            logger.exception("_user_active_recently failed")
            self._last_activity_snapshot = {
                "session_busy": True,
                "queue_healthy": False,
                "activity_guard_reason_code": "activity_guard_exception",
            }
            return True


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
        """Log compose context without raw conversation text."""
        voice_snapshot: dict[str, float] = {}
        if voice is not None:
            try:
                from voice_engine import STYLE_DIMENSIONS
                voice_snapshot = {
                    dim: round(
                        float(getattr(voice, dim, 0.0)),
                        2,
                    )
                    for dim in STYLE_DIMENSIONS
                }
                engine = self._voice()
                if engine is not None:
                    voice_snapshot["social_urge"] = round(
                        float(
                            getattr(
                                engine,
                                "social_urge",
                                0.0,
                            )
                        ),
                        2,
                    )
            except Exception:
                pass

        had_discovery = discovery_context is not None
        external_n = (
            len(discovery_context.get("external", []) or [])
            if had_discovery
            else 0
        )
        local_n = (
            len(discovery_context.get("local", []) or [])
            if had_discovery
            else 0
        )

        context_snapshot: dict[str, Any] = {}
        rejection_reason = ""
        try:
            context_snapshot = dict(
                getattr(
                    self._llm_message_composer,
                    "last_context_snapshot",
                    {},
                )
                or {}
            )
            rejection_reason = str(
                getattr(
                    self._llm_message_composer,
                    "last_rejection_reason",
                    "",
                )
                or ""
            )
        except Exception:
            context_snapshot = {}

        self._log(
            "compose",
            tick_id=tick_id,
            model=generated_by,
            msg_type=msg_type,
            voice=voice_snapshot,
            had_discovery=had_discovery,
            discovery_items=external_n + local_n,
            context_queue_sha256=context_snapshot.get(
                "queue_sha256"
            ),
            context_queue_updated_at=context_snapshot.get(
                "queue_updated_at"
            ),
            context_queue_message_count=context_snapshot.get(
                "queue_message_count"
            ),
            context_queue_distinct_session_count=context_snapshot.get(
                "queue_distinct_session_count"
            ),
            context_queue_db_lag_seconds=context_snapshot.get(
                "queue_db_lag_seconds"
            ),
            context_prompt_eligible_count=context_snapshot.get(
                "context_prompt_eligible_count"
            ),
            context_prompt_hash=context_snapshot.get(
                "context_prompt_hash"
            ),
            latest_context_role=context_snapshot.get(
                "latest_context_role"
            ),
            latest_context_age_seconds=context_snapshot.get(
                "latest_context_age_seconds"
            ),
            session_busy_boolean=context_snapshot.get(
                "session_busy_boolean"
            ),
            referent_anchor_count=context_snapshot.get(
                "referent_anchor_count"
            ),
            rejection_reason=rejection_reason or None,
        )


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}

def _redact_chat(chat_id: str) -> str:
    if len(chat_id) <= 8:
        return "<redacted>"
    return chat_id[:4] + "..." + chat_id[-4:]
