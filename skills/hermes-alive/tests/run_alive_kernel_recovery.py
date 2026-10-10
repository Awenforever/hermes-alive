#!/usr/bin/env python3
"""Crash-gap and ordered startup recovery contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ConsolidationPolicyProjection,
    ContentErasedError,
    ContentVault,
    EventEnvelope,
    ExperienceJournal,
    KernelRecoverySupervisor,
    MemoryAuthority,
    MemoryKind,
    MemoryProjection,
    MemoryProposal,
    MemoryReview,
    MemoryState,
    RetentionDirection,
    RetentionProjection,
    Sensitivity,
    recover_kernel_state,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-recovery-") as directory:
        shared = Path(directory)
        assert recover_kernel_state(shared) is None
        assert not (shared / "kernel").exists()

        kernel = shared / "kernel"
        journal = ExperienceJournal(kernel / "experience.sqlite3")
        vault = ContentVault(
            kernel / "content-vault", backup_root=kernel / "content-backups"
        )
        subject = "user:recovery"

        retention = RetentionProjection(journal, content_vault=vault)
        retention_consent = retention.append_consent(
            subject=subject,
            enabled=True,
            retention_days=30,
            directions=(RetentionDirection.INBOUND,),
            sensitivity=Sensitivity.RESTRICTED,
            actor=subject,
            operation_id="crash-gap",
        )
        # Simulate a crash after journal append but before projection.apply().
        assert retention.policy(subject) is None

        learning = ConsolidationPolicyProjection(journal)
        learning_consent = learning.append_consent(
            subject=subject,
            actor=subject,
            enabled=True,
            operation_id="crash-gap",
        )
        assert learning.policy(subject) is None

        evidence = EventEnvelope(
            event_id="conversation:recovery-evidence",
            event_type="conversation.inbound",
            source="hermes.hook",
            actor=subject,
            subject=subject,
            sensitivity=Sensitivity.RESTRICTED,
            payload={"raw_content_stored": False},
        )
        journal.append(evidence)
        memory = MemoryProjection(journal, content_vault=vault)
        proposal = MemoryProposal(
            proposal_id="memory-recovery-candidate",
            kind=MemoryKind.FACT,
            subject=subject,
            predicate="profile.recovery",
            value={"sentinel": "encrypted recovery candidate"},
            authority=MemoryAuthority.MODEL_INFERENCE,
            source_event_ids=(evidence.event_id,),
            confidence=0.8,
            importance=0.5,
            sensitivity=Sensitivity.RESTRICTED,
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        )
        memory.append_proposal(proposal, actor="system:alive-consolidator")
        memory.append_review(
            proposal.proposal_id,
            review=MemoryReview.ACCEPT,
            subject=subject,
            actor=subject,
            operation_id="crash-gap",
        )
        assert memory.get(
            proposal.proposal_id, clearance=Sensitivity.RESTRICTED
        ) is None

        doomed = vault.put_json(
            {"text": "erase after restart sentinel"},
            subject=subject,
            purpose="conversation.inbound",
            sensitivity=Sensitivity.RESTRICTED,
            retention_until=datetime.now(timezone.utc) + timedelta(days=1),
            content_id="experience:pending-erasure",
        )
        retention.append_erasure_request(
            subject=subject, actor=subject, operation_id="crash-gap"
        )

        report = KernelRecoverySupervisor(shared).recover(batch_size=1)
        assert report is not None
        assert report.erasures_resumed == 1
        assert report.target_sequence <= report.final_sequence
        assert {item.name for item in report.projections} == {
            "retention",
            "consolidation-consent",
            "memory",
            "agenda",
            "deliberation",
            "outcomes",
            "reflection",
            "preference-learning",
            "exploration",
        }
        assert all(
            item.checkpoint_after >= report.target_sequence
            for item in report.projections
        )
        assert RetentionProjection(journal, content_vault=vault).policy(subject) is not None
        assert ConsolidationPolicyProjection(journal).policy(subject) is not None
        recovered = MemoryProjection(journal, content_vault=vault).get(
            proposal.proposal_id, clearance=Sensitivity.RESTRICTED
        )
        assert recovered is not None and recovered.state is MemoryState.ACTIVE
        try:
            vault.resolve_json(doomed.content_id)
        except ContentErasedError:
            pass
        else:
            raise AssertionError("pending erasure was not resumed")

        again = KernelRecoverySupervisor(shared).recover(batch_size=1)
        assert again is not None
        assert again.erasures_resumed == 0
        assert all(item.decisions == 0 and item.batches == 0 for item in again.projections)

        database = (kernel / "experience.sqlite3").read_bytes()
        wal = kernel / "experience.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        assert b"encrypted recovery candidate" not in database
        assert b"erase after restart sentinel" not in database
        assert journal.get(retention_consent.event.event_id) is not None
        assert journal.get(learning_consent.event.event_id) is not None

    print("HERMES_ALIVE_KERNEL_RECOVERY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
