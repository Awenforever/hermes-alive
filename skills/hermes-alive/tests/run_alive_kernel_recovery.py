#!/usr/bin/env python3
"""Crash-gap and ordered startup recovery contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ActionAuthority,
    ActionCandidate,
    ActionKind,
    AgendaAuthority,
    AgendaItemKind,
    AgendaProjection,
    AgendaProposal,
    AssessmentBasis,
    CognitionCycleCoordinator,
    ConsolidationPolicyProjection,
    ContentErasedError,
    ContentVault,
    CycleCandidate,
    DecisionDimensions,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    KernelRecoverySupervisor,
    MemoryAuthority,
    MemoryKind,
    MemoryProjection,
    MemoryProposal,
    MemoryReview,
    MemoryState,
    OutcomeProjection,
    PolicyContext,
    RetentionDirection,
    RetentionProjection,
    Sensitivity,
    SelectionProposal,
    SendTimeAuthorizer,
    SideEffect,
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

        causal_subject = "user:causal-recovery"
        causal_evidence = EventEnvelope(
            event_id="conversation:causal-recovery-evidence",
            event_type="conversation.inbound",
            source="test.channel",
            actor=causal_subject,
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            payload={"raw_content_stored": False},
        )
        journal.append(causal_evidence)
        agenda = AgendaProjection(journal, content_vault=vault)
        agenda_proposal = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject=causal_subject,
            details={"summary": "causal recovery agenda"},
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_ids=(causal_evidence.event_id,),
            confidence=0.9,
            sensitivity=Sensitivity.RESTRICTED,
            item_id="agenda:causal-recovery",
        )
        assert agenda.apply(
            agenda.append_proposal(agenda_proposal, actor=causal_subject)
        ).outcome == "active"

        def score(value: float) -> DimensionAssessment:
            return DimensionAssessment(
                value,
                AssessmentBasis.MEASURED,
                (causal_evidence.event_id,),
                "recovery evidence",
            )

        candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=DecisionDimensions(
                score(0.9), score(0.5), score(0.8),
                score(0.9), score(0.2), score(0.1),
            ),
            agenda_item_id=agenda_proposal.item_id,
            content_id="causal-recovery-content",
            candidate_id="candidate:causal-recovery",
        )
        coordinator = CognitionCycleCoordinator(journal, content_vault=vault)
        cycle = coordinator.plan_safe_silence(
            cycle_id="causal-recovery",
            subject=causal_subject,
            candidates=(
                CycleCandidate(
                    candidate,
                    {"message": "encrypted causal recovery candidate"},
                    "recovery topic",
                    "recovery source",
                ),
            ),
            policy_context=PolicyContext(can_interrupt=True),
            sensitivity=Sensitivity.RESTRICTED,
            causation_id=causal_evidence.event_id,
        )
        selection = coordinator.deliberation.append_selection(
            SelectionProposal(
                cycle.selection.frame_id,
                candidate.candidate_id,
                "provider/recovery-model",
                "causal recovery selection",
            ),
            actor="system:test-model",
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            selection_id="selection:causal-recovery",
            exploration_gate_event_id=cycle.exploration_event_id,
        )
        assert coordinator.deliberation.apply(selection).outcome == "validated"
        authorization = SendTimeAuthorizer(
            journal, content_vault=vault
        ).evaluate(
            selection_event_id=selection.event.event_id,
            subject=causal_subject,
            capability="hermes.channel.send",
            current_policy=PolicyContext(can_interrupt=True),
            operation_id="causal-recovery",
        )
        assert authorization.authorized
        outcomes = OutcomeProjection(journal, content_vault=vault)
        attempt = outcomes.append_attempt(
            authorization_event_id=authorization.event_id,
            selection_event_id=selection.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="causal-recovery",
            actor="system:test-executor",
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            attempt_id="attempt:causal-recovery",
        )
        assert outcomes.apply(attempt).outcome == "recorded"

        # Simulate loss of every derived causal projection while retaining the
        # journal and encrypted vault. Recovery must rebuild in dependency order.
        connection = sqlite3.connect(journal.path)
        try:
            connection.executescript(
                """
                PRAGMA foreign_keys=OFF;
                DELETE FROM action_outcomes_v1;
                DELETE FROM action_attempts_v1;
                DELETE FROM outcome_projection_decisions_v1;
                DELETE FROM deliberation_selections_v1;
                DELETE FROM exploration_evaluations_v1;
                DELETE FROM exploration_annotations_v1;
                DELETE FROM exploration_decisions_v1;
                DELETE FROM deliberation_audit_v1;
                DELETE FROM deliberation_frames_v1;
                DELETE FROM agenda_transitions_v1;
                DELETE FROM agenda_sources_v1;
                DELETE FROM agenda_decisions_v1;
                DELETE FROM agenda_items_v1;
                DELETE FROM consumer_checkpoints
                WHERE consumer_name IN (
                  'alive-agenda-v1', 'alive-deliberation-frames-v1',
                  'alive-deliberation-v1', 'alive-exploration-v1',
                  'alive-outcomes-v1'
                );
                PRAGMA foreign_keys=ON;
                """
            )
            connection.commit()
        finally:
            connection.close()

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
            "deliberation-frames",
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
        recovered_attempts = OutcomeProjection(
            journal, content_vault=vault
        ).attempts(clearance=Sensitivity.RESTRICTED)
        assert len(recovered_attempts) == 1
        assert recovered_attempts[0].authorization_event_id == authorization.event_id
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
    CycleCandidate,
    DecisionDimensions,
    DimensionAssessment,
