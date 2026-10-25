#!/usr/bin/env python3
"""Consent, encrypted capture, disable, erasure and recovery contracts."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ContentErasedError, ContentReference, EventEnvelope, RetentionProjection,
    Sensitivity, ShadowKernelBridge,
)
from alive_kernel.retention_command import handle_memory_command  # noqa: E402
from alive_kernel.retention_command import resume_retention_maintenance  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-retention-") as directory:
        shared = Path(directory)
        context = {
            "platform": "weixin", "user_id": "retention-user",
            "chat_id": "retention-chat", "session_id": "retention-session-1",
            "message": "private retained inbound sentinel",
        }
        bridge = ShadowKernelBridge(shared)
        structural = bridge.observe_hook("agent:start", context)
        assert structural is not None
        assert structural.event.payload["erasable_content_stored"] is False
        assert structural.event.payload["content_retention_status"] == "not_authorized"

        assert handle_memory_command(shared, {"args": "pending"}) is None
        missing = handle_memory_command(shared, {"args": "alive retain on 30 both"})
        assert missing and missing["decision"] == "handled"
        assert "未更改" in missing["message"]
        status = handle_memory_command(shared, {
            "user_id": "retention-user", "args": "alive status",
        })
        assert status and "默认关闭" in status["message"]

        enabled = handle_memory_command(shared, {
            "user_id": "retention-user", "args": "alive retain on 2 both",
        })
        assert enabled and "明确授权" in enabled["message"]
        subject = bridge.protector.pseudonym("user", "retention-user")
        assert subject is not None
        policy = bridge.retention.policy(subject)
        assert policy is not None and policy.enabled and policy.retention_days == 2
        forged = EventEnvelope(
            event_id="retention.consent:forged-model",
            event_type="retention.consent_changed", source="model.output",
            actor=subject, subject=subject, sensitivity=Sensitivity.PRIVATE,
            payload={
                "enabled": True, "retention_days": 365,
                "directions": ["inbound", "outbound"],
                "content_sensitivity": "restricted", "raw_command_stored": False,
            },
        )
        bridge.journal.append(forged)
        forged_decision = bridge.retention.apply(
            bridge.journal.get(forged.event_id)
        )
        assert forged_decision.reason == "consent_authority_invalid"
        assert bridge.retention.policy(subject) == policy

        retained_context = {
            **context,
            "session_id": "retention-session-2",
            "message": "second private retained inbound sentinel",
        }
        inbound = bridge.observe_hook("agent:start", retained_context)
        assert inbound is not None
        assert inbound.event.sensitivity is Sensitivity.RESTRICTED
        assert inbound.event.payload["erasable_content_stored"] is True
        inbound_ref = ContentReference.from_event_payload(inbound.event.payload["content"])
        inbound_content = bridge.content_vault.resolve_json(
            inbound_ref.content_id, expected_subject=subject,
            expected_purpose="conversation.inbound",
            expected_sensitivity=Sensitivity.RESTRICTED,
        )
        assert inbound_content["text"] == retained_context["message"]

        outbound_context = {
            **retained_context,
            "response": "private retained outbound sentinel",
            "model": "private-model-name",
            "provider": "private-provider-name",
        }
        outbound = bridge.observe_hook("agent:end", outbound_context)
        assert outbound is not None and outbound.event.causation_id == inbound.event.event_id
        outbound_ref = ContentReference.from_event_payload(outbound.event.payload["content"])
        assert bridge.content_vault.resolve_json(
            outbound_ref.content_id, expected_subject=subject,
            expected_purpose="conversation.outbound",
            expected_sensitivity=Sensitivity.RESTRICTED,
        )["text"] == outbound_context["response"]
        vault_bytes = b"".join(
            path.read_bytes()
            for root in (
                shared / "kernel" / "content-vault",
                shared / "kernel" / "content-backups",
            )
            if root.exists()
            for path in root.rglob("*")
            if path.is_file()
        )
        assert b"second private retained inbound sentinel" not in vault_bytes
        assert b"private retained outbound sentinel" not in vault_bytes

        disabled = handle_memory_command(shared, {
            "user_id": "retention-user", "args": "alive retain off",
        })
        assert disabled and "停止新增" in disabled["message"]
        not_retained = bridge.observe_hook("agent:start", {
            **context, "session_id": "retention-session-3",
            "message": "disabled content must never enter the vault",
        })
        assert not_retained is not None
        assert not_retained.event.payload["erasable_content_stored"] is False

        forgotten = handle_memory_command(shared, {
            "user_id": "retention-user", "args": "alive forget",
        })
        assert forgotten and "擦除已完成" in forgotten["message"]
        for reference in (inbound_ref, outbound_ref):
            try:
                bridge.content_vault.resolve_json(reference.content_id)
            except ContentErasedError:
                pass
            else:
                raise AssertionError("forgotten conversation content remained readable")

        # Re-enable, retain one item, then simulate a crash after the durable
        # request but before execution. Gateway startup must finish the erasure.
        handle_memory_command(shared, {
            "user_id": "retention-user", "args": "alive retain on 1 inbound",
        })
        pending_context = {
            **context, "session_id": "retention-session-4",
            "message": "pending erasure recovery sentinel",
        }
        pending = bridge.observe_hook("agent:start", pending_context)
        assert pending is not None and pending.event.payload["erasable_content_stored"] is True
        pending_ref = ContentReference.from_event_payload(pending.event.payload["content"])
        request = bridge.retention.append_erasure_request(
            subject=subject, actor=subject, operation_id="interrupted-test"
        )
        assert bridge.journal.get(
            bridge.retention.completion_event_id(request.event.event_id)
        ) is None
        maintenance = resume_retention_maintenance(shared)
        assert maintenance["erasures_resumed"] == 1
        restarted = ShadowKernelBridge(shared)
        completion = restarted.journal.get(
            restarted.retention.completion_event_id(request.event.event_id)
        )
        assert completion is not None
        try:
            restarted.content_vault.resolve_json(pending_ref.content_id)
        except ContentErasedError:
            pass
        else:
            raise AssertionError("pending erasure was not resumed")

        before = restarted.retention.policy(subject)
        restarted.retention.rebuild(batch_size=3)
        assert restarted.retention.policy(subject) == before

        database = (shared / "kernel" / "experience.sqlite3").read_bytes()
        wal = shared / "kernel" / "experience.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        for forbidden in (
            b"private retained inbound sentinel",
            b"private retained outbound sentinel",
            b"disabled content must never enter the vault",
            b"pending erasure recovery sentinel",
            b"private-model-name",
            b"private-provider-name",
            b"alive retain on 2 both",
        ):
            assert forbidden not in database

    print("HERMES_ALIVE_KERNEL_RETENTION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
