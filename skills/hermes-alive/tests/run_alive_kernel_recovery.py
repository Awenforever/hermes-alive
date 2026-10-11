#!/usr/bin/env python3
"""Crash-gap and ordered startup recovery contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
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
    DispatchOutbox,
    DispatchOutboxError,
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
        assert report.dispatches_reconciled == 1
        assert report.dispatch_outcomes_reconciled == 0
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

        outbox = DispatchOutbox(journal, content_vault=vault)
        assert outbox.counts() == {"pending": 1}
        lease_now = report.completed_at
        with ThreadPoolExecutor(max_workers=8) as pool:
            leases = list(
                pool.map(
                    lambda index: outbox.acquire(
                        worker_id=f"worker-{index}", now=lease_now
                    ),
                    range(8),
                )
            )
        claimed = [value for value in leases if value is not None]
        assert len(claimed) == 1
        first_lease = claimed[0]
        assert outbox.load_content(
            first_lease,
            clearance=Sensitivity.RESTRICTED,
            now=lease_now,
        ) == {"message": "encrypted causal recovery candidate"}
        assert "worker-" not in journal.path.read_bytes().decode(
            "utf-8", errors="ignore"
        )

        # A crashed owner loses the row after lease expiry; its token cannot
        # read or mutate the replacement lease.
        second_lease = outbox.acquire(
            worker_id="recovery-worker",
            now=first_lease.lease_until,
        )
        assert second_lease is not None
        assert second_lease.generation == first_lease.generation + 1
        try:
            outbox.load_content(
                first_lease,
                clearance=Sensitivity.RESTRICTED,
                now=first_lease.lease_until,
            )
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError("stale dispatch lease retained access")
        assert outbox.release(second_lease, now=first_lease.lease_until) == "pending"
        third_lease = outbox.acquire(
            worker_id="result-worker",
            now=first_lease.lease_until,
        )
        assert third_lease is not None
        result_payload = {
            "dispatch_id": third_lease.dispatch_id,
            "attempt_id": third_lease.attempt_id,
            "idempotency_key": third_lease.idempotency_key,
            "capability": third_lease.capability,
            "outcome": "delivery_succeeded",
        }
        forged_result = EventEnvelope(
            event_id="delivery:causal-recovery-forged",
            event_type="delivery.succeeded",
            source="test.channel",
            actor="system:test-channel",
            subject=causal_subject,
            occurred_at=first_lease.lease_until,
            observed_at=first_lease.lease_until,
            sensitivity=Sensitivity.RESTRICTED,
            payload=result_payload,
        )
        journal.append(forged_result)
        try:
            outbox.acknowledge(
                third_lease,
                result_event_id=forged_result.event_id,
                now=first_lease.lease_until,
            )
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError("unauthenticated dispatch result was accepted")
        inconsistent_payload = dict(result_payload)
        inconsistent_payload["outcome"] = "task_completed"
        inconsistent_payload["integrity_authenticator"] = (
            outbox.protector.authenticate_json(
                "dispatch.result.v1", inconsistent_payload
            )
        )
        inconsistent_result = EventEnvelope(
            event_id="delivery:causal-recovery-inconsistent",
            event_type="delivery.succeeded",
            source="test.channel",
            actor="system:test-channel",
            subject=causal_subject,
            occurred_at=first_lease.lease_until,
            observed_at=first_lease.lease_until,
            sensitivity=Sensitivity.RESTRICTED,
            payload=inconsistent_payload,
        )
        journal.append(inconsistent_result)
        try:
            outbox.acknowledge(
                third_lease,
                result_event_id=inconsistent_result.event_id,
                now=first_lease.lease_until,
            )
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError("inconsistent signed dispatch result was accepted")
        result_payload["integrity_authenticator"] = outbox.protector.authenticate_json(
            "dispatch.result.v1", result_payload
        )
        result_event = EventEnvelope(
            event_id="delivery:causal-recovery",
            event_type="delivery.succeeded",
            source="test.channel",
            actor="system:test-channel",
            subject=causal_subject,
            occurred_at=first_lease.lease_until,
            observed_at=first_lease.lease_until,
            sensitivity=Sensitivity.RESTRICTED,
            payload=result_payload,
        )
        journal.append(result_event)
        outbox.acknowledge(
            third_lease,
            result_event_id=result_event.event_id,
            now=first_lease.lease_until,
        )
        assert outbox.counts() == {"acknowledged": 1}
        # Lose the operational outbox after transport success but before the
        # outcome projection is written. The signed result in the journal must
        # prevent a duplicate dispatch during reconstruction.
        lost_outbox = sqlite3.connect(journal.path)
        try:
            lost_outbox.execute("DELETE FROM dispatch_outbox_v1")
            lost_outbox.commit()
        finally:
            lost_outbox.close()
        try:
            vault.resolve_json(doomed.content_id)
        except ContentErasedError:
            pass
        else:
            raise AssertionError("pending erasure was not resumed")

        again = KernelRecoverySupervisor(shared).recover(batch_size=1)
        assert again is not None
        assert again.erasures_resumed == 0
        assert again.dispatches_reconciled == 1
        assert again.dispatch_outcomes_reconciled == 1
        observed = OutcomeProjection(
            journal, content_vault=vault
        ).outcomes(
            "attempt:causal-recovery", clearance=Sensitivity.RESTRICTED
        )
        assert len(observed) == 1
        assert observed[0].kind.value == "delivery_succeeded"
        assert DispatchOutbox(journal, content_vault=vault).counts() == {
            "acknowledged": 1
        }
        assert DispatchOutbox(journal, content_vault=vault).acquire(
            worker_id="must-not-redeliver",
            now=first_lease.lease_until,
        ) is None
        assert outbox.reconcile_outcomes() == 0
        assert all(
            item.checkpoint_after >= again.target_sequence
            for item in again.projections
        )
        caught_up = KernelRecoverySupervisor(shared).recover(batch_size=1)
        assert caught_up is not None
        assert caught_up.dispatches_reconciled == 0
        assert caught_up.dispatch_outcomes_reconciled == 0
        assert all(
            item.checkpoint_after >= caught_up.target_sequence
            for item in caught_up.projections
        )
        settled = KernelRecoverySupervisor(shared).recover(batch_size=1)
        assert settled is not None
        assert all(
            item.decisions == 0 and item.batches == 0
            for item in settled.projections
        )

        database = (kernel / "experience.sqlite3").read_bytes()
        wal = kernel / "experience.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        assert b"encrypted recovery candidate" not in database
        assert b"erase after restart sentinel" not in database
        assert b"worker-" not in database
        assert first_lease.token.encode("utf-8") not in database
        assert second_lease.token.encode("utf-8") not in database
        assert third_lease.token.encode("utf-8") not in database
        assert journal.get(retention_consent.event.event_id) is not None
        assert journal.get(learning_consent.event.event_id) is not None

    print("HERMES_ALIVE_KERNEL_RECOVERY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
