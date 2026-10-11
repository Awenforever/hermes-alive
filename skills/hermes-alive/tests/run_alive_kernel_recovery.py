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
    AutonomyPolicyProjection,
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
from alive_kernel_testkit import install_terminal_route  # noqa: E402


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
        route_binding_id = install_terminal_route(
            journal, subject="user:causal-recovery", content_vault=vault
        )

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
                    {
                        "schema_version": 1,
                        "capability": "hermes.channel.send",
                        "operation": {
                            "text": "encrypted causal recovery candidate",
                            "format": "markdown",
                        },
                    },
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
        autonomy = AutonomyPolicyProjection(journal)
        autonomy_event = autonomy.append_update(
            subject=causal_subject,
            actor=causal_subject,
            expected_revision=0,
            enabled=True,
            context=PolicyContext(can_interrupt=True),
            operation_id="causal-recovery",
        )
        assert autonomy.apply(autonomy_event).outcome == "recorded"
        authorization = SendTimeAuthorizer(
            journal, content_vault=vault, route_binding_id=route_binding_id
        ).evaluate(
            selection_event_id=selection.event.event_id,
            subject=causal_subject,
            capability="hermes.channel.send",
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
                DELETE FROM autonomy_policies_v1;
                DELETE FROM autonomy_policy_decisions_v1;
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
                  'alive-autonomy-policy-v1', 'alive-agenda-v1',
                  'alive-deliberation-frames-v1',
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
        assert report.dispatch_evidence_checkpoint_after >= report.target_sequence
        assert report.dispatch_evidence_indexed >= 0
        assert report.target_sequence <= report.final_sequence
        assert {item.name for item in report.projections} == {
            "retention",
            "autonomy-policy",
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
        recovered_policy = AutonomyPolicyProjection(journal).current(causal_subject)
        assert recovered_policy is not None and recovered_policy.enabled
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
            outbox.begin_execution(
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
        execution = outbox.begin_execution(
            third_lease,
            clearance=Sensitivity.RESTRICTED,
            now=first_lease.lease_until,
        )
        assert execution.content == {
            "schema_version": 1,
            "capability": "hermes.channel.send",
            "operation": {
                "text": "encrypted causal recovery candidate",
                "format": "markdown",
            },
        }
        result_payload = {
            "dispatch_id": third_lease.dispatch_id,
            "attempt_id": third_lease.attempt_id,
            "idempotency_key": third_lease.idempotency_key,
            "capability": third_lease.capability,
            "start_event_id": execution.start_event_id,
            "lease_generation": third_lease.generation,
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
            lost_outbox.execute("DELETE FROM dispatch_outbox_v3")
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
        assert (
            caught_up.dispatch_evidence_checkpoint_after
            >= caught_up.target_sequence
        )
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

        # A user pause revokes pending and leased work immediately. Resuming
        # does not resurrect the old authorization; only a newly authorized
        # attempt under the new policy revision becomes dispatchable.
        pause_now = datetime.now(timezone.utc)
        before_pause = SendTimeAuthorizer(
            journal, content_vault=vault, route_binding_id=route_binding_id
        ).evaluate(
            selection_event_id=selection.event.event_id,
            subject=causal_subject,
            capability="hermes.channel.send",
            operation_id="causal-recovery-before-pause",
            now=pause_now,
        )
        assert before_pause.authorized
        pause_attempt = outcomes.append_attempt(
            authorization_event_id=before_pause.event_id,
            selection_event_id=selection.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="causal-recovery-before-pause",
            actor="system:test-executor",
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            attempt_id="attempt:causal-recovery-before-pause",
        )
        assert outcomes.apply(pause_attempt).outcome == "recorded"
        assert outbox.reconcile(now=pause_now) == 1
        paused_lease = outbox.acquire(worker_id="pause-worker", now=pause_now)
        assert paused_lease is not None
        paused = autonomy.append_update(
            subject=causal_subject,
            actor=causal_subject,
            expected_revision=1,
            enabled=False,
            context=PolicyContext(can_interrupt=False),
            operation_id="causal-recovery-pause",
        )
        assert autonomy.apply(paused).outcome == "recorded"
        assert outbox.acquire(worker_id="paused-worker", now=pause_now) is None
        assert outbox.counts() == {"acknowledged": 1, "revoked": 1}
        try:
            outbox.begin_execution(
                paused_lease,
                clearance=Sensitivity.RESTRICTED,
                now=pause_now,
            )
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError("paused autonomy left a lease readable")
        try:
            outbox.release(paused_lease, now=pause_now)
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError("paused autonomy allowed a lease to be requeued")
        resumed = autonomy.append_update(
            subject=causal_subject,
            actor=causal_subject,
            expected_revision=2,
            enabled=True,
            context=PolicyContext(can_interrupt=True),
            operation_id="causal-recovery-resume",
        )
        assert autonomy.apply(resumed).outcome == "recorded"
        assert outbox.acquire(worker_id="must-not-resurrect", now=pause_now) is None
        resume_now = datetime.now(timezone.utc)
        after_resume = SendTimeAuthorizer(
            journal, content_vault=vault, route_binding_id=route_binding_id
        ).evaluate(
            selection_event_id=selection.event.event_id,
            subject=causal_subject,
            capability="hermes.channel.send",
            operation_id="causal-recovery-after-resume",
            now=resume_now,
        )
        assert after_resume.authorized
        resumed_attempt = outcomes.append_attempt(
            authorization_event_id=after_resume.event_id,
            selection_event_id=selection.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="causal-recovery-after-resume",
            actor="system:test-executor",
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            attempt_id="attempt:causal-recovery-after-resume",
        )
        assert outcomes.apply(resumed_attempt).outcome == "recorded"
        assert outbox.reconcile(now=resume_now) == 1
        resumed_lease = outbox.acquire(worker_id="resumed-worker", now=resume_now)
        assert resumed_lease is not None
        execution_now = datetime.now(timezone.utc)
        resumed_execution = outbox.begin_execution(
            resumed_lease,
            clearance=Sensitivity.RESTRICTED,
            now=execution_now,
        )
        assert resumed_execution.content == {
            "schema_version": 1,
            "capability": "hermes.channel.send",
            "operation": {
                "text": "encrypted causal recovery candidate",
                "format": "markdown",
            },
        }
        lost_started = sqlite3.connect(journal.path)
        try:
            lost_started.execute(
                "DELETE FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                (resumed_lease.dispatch_id,),
            )
            lost_started.commit()
        finally:
            lost_started.close()
        assert outbox.reconcile(now=execution_now) == 1
        assert outbox.counts() == {
            "acknowledged": 1,
            "revoked": 1,
            "uncertain": 1,
        }
        assert outbox.acquire(
            worker_id="must-not-repeat-uncertain",
            now=resumed_lease.lease_until,
        ) is None
        late_result_payload = {
            "dispatch_id": resumed_lease.dispatch_id,
            "attempt_id": resumed_lease.attempt_id,
            "idempotency_key": resumed_lease.idempotency_key,
            "capability": resumed_lease.capability,
            "start_event_id": resumed_execution.start_event_id,
            "lease_generation": resumed_lease.generation,
            "outcome": "delivery_succeeded",
        }
        late_result_payload["integrity_authenticator"] = (
            outbox.protector.authenticate_json(
                "dispatch.result.v1", late_result_payload
            )
        )
        late_result = EventEnvelope(
            event_id="delivery:causal-recovery-after-resume",
            event_type="delivery.succeeded",
            source="test.channel",
            actor="system:test-channel",
            subject=causal_subject,
            occurred_at=resumed_lease.lease_until,
            observed_at=resumed_lease.lease_until,
            sensitivity=Sensitivity.RESTRICTED,
            payload=late_result_payload,
        )
        journal.append(late_result)
        assert outbox.reconcile(now=resumed_lease.lease_until) == 0
        assert outbox.reconcile_outcomes() == 1
        assert outbox.counts() == {
            "acknowledged": 2,
            "revoked": 1,
        }

        # Exact crash gap: the durable start event exists, but the process dies
        # before changing the operational row from leased to started. A later
        # claimant must absorb the event and preserve uncertainty, not retry.
        gap_now = datetime.now(timezone.utc)
        gap_authorization = SendTimeAuthorizer(
            journal, content_vault=vault, route_binding_id=route_binding_id
        ).evaluate(
            selection_event_id=selection.event.event_id,
            subject=causal_subject,
            capability="hermes.channel.send",
            operation_id="causal-recovery-start-gap",
            now=gap_now,
        )
        assert gap_authorization.authorized
        gap_attempt = outcomes.append_attempt(
            authorization_event_id=gap_authorization.event_id,
            selection_event_id=selection.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="causal-recovery-start-gap",
            actor="system:test-executor",
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            attempt_id="attempt:causal-recovery-start-gap",
        )
        assert outcomes.apply(gap_attempt).outcome == "recorded"
        gap_claim_time = datetime.now(timezone.utc)
        assert outbox.reconcile(now=gap_claim_time) == 1
        gap_lease = outbox.acquire(worker_id="gap-worker", now=gap_claim_time)
        assert gap_lease is not None
        gap_start_payload = {
            "dispatch_id": gap_lease.dispatch_id,
            "attempt_id": gap_lease.attempt_id,
            "idempotency_key": gap_lease.idempotency_key,
            "capability": gap_lease.capability,
            "policy_event_id": resumed.event.event_id,
            "route_binding_id": route_binding_id,
            "route_binding_event_id": gap_authorization.route_binding_id
            and journal.get(gap_authorization.event_id).event.payload[
                "route_binding_event_id"
            ],
            "host_snapshot_event_id": journal.get(
                gap_authorization.event_id
            ).event.payload["host_snapshot_event_id"],
            "lease_generation": gap_lease.generation,
            "external_result_observed": False,
        }
        gap_start_payload["integrity_authenticator"] = (
            outbox.protector.authenticate_json(
                "dispatch.start.v1", gap_start_payload
            )
        )
        gap_start = EventEnvelope(
            event_id=outbox._start_event_id(
                gap_lease.dispatch_id, gap_lease.generation
            ),
            event_type="dispatch.started",
            source="alive.dispatch",
            actor="system:alive-dispatch",
            subject=causal_subject,
            causation_id=f"action.attempt:{gap_lease.attempt_id}",
            occurred_at=gap_claim_time,
            observed_at=gap_claim_time,
            sensitivity=Sensitivity.RESTRICTED,
            payload=gap_start_payload,
        )
        journal.append(gap_start)
        assert outbox.acquire(
            worker_id="must-not-cross-start-gap",
            now=gap_lease.lease_until,
        ) is None
        assert outbox.counts() == {
            "acknowledged": 2,
            "revoked": 1,
            "uncertain": 1,
        }

        # Route authority is live state too: revocation after authorization
        # invalidates pending work before a worker can cross the start boundary.
        route_revoke_now = datetime.now(timezone.utc)
        route_authorizer = SendTimeAuthorizer(
            journal, content_vault=vault, route_binding_id=route_binding_id
        )
        route_authorization = route_authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject=causal_subject,
            capability="hermes.channel.send",
            operation_id="causal-recovery-route-revoke",
            now=route_revoke_now,
        )
        assert route_authorization.authorized
        route_attempt = outcomes.append_attempt(
            authorization_event_id=route_authorization.event_id,
            selection_event_id=selection.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="causal-recovery-route-revoke",
            actor="system:test-executor",
            subject=causal_subject,
            sensitivity=Sensitivity.RESTRICTED,
            attempt_id="attempt:causal-recovery-route-revoke",
        )
        assert outcomes.apply(route_attempt).outcome == "recorded"
        assert outbox.reconcile(now=route_revoke_now) == 1
        route_authorizer.host.revoke_route(
            route_binding_id, observed_at=route_revoke_now
        )
        assert outbox.acquire(
            worker_id="must-not-use-revoked-route",
            now=route_revoke_now,
        ) is None
        assert outbox.counts() == {
            "acknowledged": 2,
            "revoked": 2,
            "uncertain": 1,
        }

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
        assert paused_lease.token.encode("utf-8") not in database
        assert resumed_lease.token.encode("utf-8") not in database
        assert gap_lease.token.encode("utf-8") not in database
        assert journal.get(retention_consent.event.event_id) is not None
        assert journal.get(learning_consent.event.event_id) is not None

    print("HERMES_ALIVE_KERNEL_RECOVERY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
