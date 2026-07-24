"""Isolated-only delivery enforcement helpers for Hermes Alive.

This module turns already validated shadow decisions into delivery controls only
inside an explicitly isolated test runtime. It is intentionally not exposed
through managed configuration.

Markers:
- HERMES_ALIVE_ISOLATED_ENFORCEMENT_V1
- HERMES_ALIVE_ISOLATED_ENFORCEMENT_DUAL_KEY_GUARD_V1
- HERMES_ALIVE_ISOLATED_ENFORCEMENT_NO_PRODUCTION_CONFIG_V1
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

MODE_ENV = "HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE"
SCOPE_ENV = "HERMES_ALIVE_RUNTIME_SCOPE"
REQUIRED_MODE = "isolated"
REQUIRED_SCOPE = "isolated_test"


def enforcement_gate(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    mode = str(env.get(MODE_ENV) or "off").strip().lower()
    scope = str(env.get(SCOPE_ENV) or "unspecified").strip().lower()
    enabled = mode == REQUIRED_MODE and scope == REQUIRED_SCOPE
    reasons: list[str] = []
    if mode != REQUIRED_MODE:
        reasons.append("mode_not_isolated")
    if scope != REQUIRED_SCOPE:
        reasons.append("runtime_scope_not_isolated_test")
    return {
        "engine": "isolated_enforcement",
        "schema_version": 1,
        "enabled": enabled,
        "mode": mode,
        "runtime_scope": scope,
        "required_mode": REQUIRED_MODE,
        "required_scope": REQUIRED_SCOPE,
        "production_safe_default": True,
        "managed_config_exposed": False,
        "reasons": reasons,
        "raw_message_stored": False,
    }


def precompose_enforcement(
    sleep_quiet_decision: Mapping[str, Any] | None,
    quality_pre_decision: Mapping[str, Any] | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    gate = enforcement_gate(environ)
    reasons: list[str] = []
    if gate["enabled"]:
        sleep = dict(sleep_quiet_decision) if isinstance(sleep_quiet_decision, Mapping) else {}
        quality = dict(quality_pre_decision) if isinstance(quality_pre_decision, Mapping) else {}
        if bool(sleep.get("would_block_dynamic")) and not bool(sleep.get("hard_exempt")):
            reasons.append(str(sleep.get("dynamic_reason") or "dynamic_sleep_quiet_block"))
        if bool(quality.get("silence_lock")):
            reasons.append("quality_silence_lock")
    return {
        **gate,
        "stage": "precompose",
        "block": bool(reasons),
        "allow": not bool(reasons),
        "reasons": reasons if gate["enabled"] else gate["reasons"],
        "watcher_enforced": bool(gate["enabled"] and reasons),
        "behavior_changed": bool(gate["enabled"] and reasons),
    }


def should_override_legacy_quiet(
    sleep_quiet_decision: Mapping[str, Any] | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    gate = enforcement_gate(environ)
    sleep = dict(sleep_quiet_decision) if isinstance(sleep_quiet_decision, Mapping) else {}
    override = bool(
        gate["enabled"]
        and sleep
        and bool(sleep.get("would_allow_dynamic"))
        and not bool(sleep.get("would_block_dynamic"))
    )
    return {
        **gate,
        "stage": "legacy_quiet_override",
        "override": override,
        "dynamic_reason": sleep.get("dynamic_reason"),
        "phase": sleep.get("phase"),
        "watcher_enforced": override,
        "behavior_changed": override,
    }


def filter_quality_candidates(
    messages: Sequence[tuple[str, str, str]],
    audits: Sequence[Mapping[str, Any]],
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[list[tuple[str, str, str]], dict[str, Any]]:
    gate = enforcement_gate(environ)
    original = list(messages)
    if not gate["enabled"]:
        return original, {
            **gate,
            "stage": "candidate_filter",
            "original_count": len(original),
            "allowed_count": len(original),
            "rejected_count": 0,
            "missing_audit_count": 0,
            "rejection_reasons": {},
            "watcher_enforced": False,
            "behavior_changed": False,
        }

    kept: list[tuple[str, str, str]] = []
    reason_counts: dict[str, int] = {}
    missing = 0
    rejected = 0
    audit_list = [dict(item) for item in audits if isinstance(item, Mapping)]

    for index, message in enumerate(original):
        if index >= len(audit_list):
            missing += 1
            rejected += 1
            reason_counts["quality_audit_missing"] = reason_counts.get("quality_audit_missing", 0) + 1
            continue
        audit = audit_list[index]
        if bool(audit.get("would_reject")) or not bool(audit.get("would_allow", not bool(audit.get("would_reject")))):
            rejected += 1
            reasons = audit.get("reasons")
            if not isinstance(reasons, list) or not reasons:
                reasons = ["quality_candidate_rejected"]
            for reason in reasons:
                key = str(reason or "quality_candidate_rejected")
                reason_counts[key] = reason_counts.get(key, 0) + 1
            continue
        kept.append(message)

    return kept, {
        **gate,
        "stage": "candidate_filter",
        "original_count": len(original),
        "allowed_count": len(kept),
        "rejected_count": rejected,
        "missing_audit_count": missing,
        "rejection_reasons": reason_counts,
        "watcher_enforced": bool(rejected),
        "behavior_changed": bool(rejected),
    }
