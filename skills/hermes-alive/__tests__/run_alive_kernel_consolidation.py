#!/usr/bin/env python3
"""Consent, evidence and human-review contracts for memory consolidation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ConsolidationCandidate,
    ConsolidationPolicyProjection,
    ConsolidationService,
    ConsolidationValidationError,
    EventEnvelope,
    MemoryKind,
    MemoryProjection,
    MemoryReview,
    MemoryState,
    ProjectionDecisionKind,
    Sensitivity,
    ShadowKernelBridge,
)
from alive_kernel.retention_command import handle_memory_command  # noqa: E402


def rejected(callable_) -> None:
    try:
        callable_()
    except ConsolidationValidationError:
        return
    raise AssertionError("unsafe consolidation request was accepted")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-consolidation-") as directory:
        shared = Path(directory)
        bridge = ShadowKernelBridge(shared)
        subject = bridge.protector.pseudonym("user", "learning-user")
        other = bridge.protector.pseudonym("user", "other-user")
        assert subject and other
        service = ConsolidationService(
            bridge.journal, content_vault=bridge.content_vault
        )

        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        absent = ConsolidationCandidate(
            subject=subject,
            kind=MemoryKind.PREFERENCE,
            predicate="communication.detail",
            value={"preference": "concise but complete private sentinel"},
            evidence_event_ids=("missing-evidence",),
            confidence=0.82,
            importance=0.6,
            expires_at=expiry,
            model="provider/test-model",
            candidate_id="candidate-1",
        )
        rejected(lambda: service.propose(absent))

        forged = EventEnvelope(
            event_id="consolidation.consent:forged",
            event_type="consolidation.consent_changed",
            source="model.output",
            actor=subject,
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            payload={"enabled": True, "raw_command_stored": False},
        )
        bridge.journal.append(forged)
        forged_record = bridge.journal.get(forged.event_id)
        assert forged_record is not None
        assert service.policy_projection.apply(forged_record) == "rejected"
        assert service.policy_projection.policy(subject) is None

        learning = handle_memory_command(
            shared, {"user_id": "learning-user", "args": "alive learn on"}
        )
        assert learning and "长期记忆候选" in learning["message"]
        rejected(lambda: service.propose(absent))

        retained = handle_memory_command(
            shared,
            {"user_id": "learning-user", "args": "alive retain on 30 inbound"},
        )
        assert retained and "明确授权" in retained["message"]
        inbound = bridge.observe_hook(
            "agent:start",
            {
                "platform": "weixin",
                "user_id": "learning-user",
                "chat_id": "learning-chat",
                "session_id": "learning-session",
                "message": "private evidence sentinel: concise but complete",
            },
        )
        assert inbound is not None

        candidate = ConsolidationCandidate(
            subject=subject,
            kind=MemoryKind.PREFERENCE,
            predicate="communication.detail",
            value={"preference": "concise but complete private sentinel"},
            evidence_event_ids=(inbound.event.event_id,),
            confidence=0.82,
            importance=0.6,
            expires_at=expiry,
            model="provider/test-model",
            candidate_id="candidate-1",
        )
        decision = service.propose(candidate)
        assert decision.decision is ProjectionDecisionKind.PROPOSED
        memory = MemoryProjection(bridge.journal, content_vault=bridge.content_vault)
        record = memory.get("candidate-1", clearance=Sensitivity.RESTRICTED)
        assert record is not None and record.state is MemoryState.PROPOSED

        listing = handle_memory_command(
            shared, {"user_id": "learning-user", "args": "alive proposals"}
        )
        assert listing and "candidate-1" in listing["message"]
        accepted = handle_memory_command(
            shared, {"user_id": "learning-user", "args": "alive accept candidate-1"}
        )
        assert accepted and "已接受" in accepted["message"]
        active = memory.get("candidate-1", clearance=Sensitivity.RESTRICTED)
        assert active is not None and active.state is MemoryState.ACTIVE

        # A forged review cannot cross either the command source or subject boundary.
        forged_review = EventEnvelope(
            event_id="memory.review:forged",
            event_type="memory.reviewed",
            source="model.output",
            actor=other,
            subject=other,
            sensitivity=Sensitivity.PRIVATE,
            payload={
                "memory_id": "candidate-1",
                "review": MemoryReview.RETRACT.value,
                "raw_command_stored": False,
            },
        )
        bridge.journal.append(forged_review)
        forged_review_record = bridge.journal.get(forged_review.event_id)
        assert forged_review_record is not None
        assert memory.apply(forged_review_record).decision is ProjectionDecisionKind.REJECTED
        assert memory.get(
            "candidate-1", clearance=Sensitivity.RESTRICTED
        ).state is MemoryState.ACTIVE

        # A candidate ID is a semantic idempotency key, never an overwrite handle.
        changed = ConsolidationCandidate(
            subject=subject,
            kind=MemoryKind.PREFERENCE,
            predicate="communication.detail",
            value={"preference": "different value"},
            evidence_event_ids=(inbound.event.event_id,),
            confidence=0.82,
            importance=0.6,
            expires_at=expiry,
            model="provider/test-model",
            candidate_id="candidate-1",
        )
        rejected(lambda: service.propose(changed))
        rejected(
            lambda: service.propose(
                ConsolidationCandidate(
                    subject=other,
                    kind=MemoryKind.FACT,
                    predicate="profile.fact",
                    value="cross-subject",
                    evidence_event_ids=(inbound.event.event_id,),
                    confidence=0.7,
                    importance=0.5,
                    expires_at=expiry,
                    model="provider/test-model",
                    candidate_id="candidate-cross-subject",
                )
            )
        )
        try:
            ConsolidationCandidate(
                subject=subject,
                kind=MemoryKind.COMMITMENT,
                predicate="unsafe.commitment",
                value={"condition": "never"},
                evidence_event_ids=(inbound.event.event_id,),
                confidence=0.9,
                importance=0.9,
                expires_at=expiry,
                model="provider/test-model",
            )
        except ConsolidationValidationError:
            pass
        else:
            raise AssertionError("model-created commitment was accepted")

        stopped = handle_memory_command(
            shared, {"user_id": "learning-user", "args": "alive learn off"}
        )
        assert stopped and "停止" in stopped["message"]
        second = ConsolidationCandidate(
            subject=subject,
            kind=MemoryKind.FACT,
            predicate="profile.note",
            value="must remain blocked",
            evidence_event_ids=(inbound.event.event_id,),
            confidence=0.7,
            importance=0.5,
            expires_at=expiry,
            model="provider/test-model",
            candidate_id="candidate-2",
        )
        rejected(lambda: service.propose(second))

        before = service.policy_projection.policy(subject)
        service.policy_projection.rebuild(batch_size=2)
        assert service.policy_projection.policy(subject) == before
        memory.rebuild(batch_size=2)
        rebuilt = memory.get("candidate-1", clearance=Sensitivity.RESTRICTED)
        assert rebuilt is not None and rebuilt.state is MemoryState.ACTIVE

        database = (shared / "kernel" / "experience.sqlite3").read_bytes()
        wal = shared / "kernel" / "experience.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        assert b"private evidence sentinel" not in database
        assert b"concise but complete private sentinel" not in database

        forgotten = handle_memory_command(
            shared, {"user_id": "learning-user", "args": "alive forget"}
        )
        assert forgotten and "擦除已完成" in forgotten["message"]
        unavailable = memory.get("candidate-1", clearance=Sensitivity.RESTRICTED)
        assert unavailable is not None
        assert unavailable.value is None and unavailable.state is MemoryState.RETRACTED

    print("HERMES_ALIVE_KERNEL_CONSOLIDATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
