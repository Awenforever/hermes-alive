#!/usr/bin/env python3
"""Latest-state, authority, policy, capability and privacy authorization tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ActionAuthority,
    ActionAuthorizationError,
    ActionCandidate,
    ActionKind,
    AgendaAuthority,
    AgendaItemKind,
    AgendaProjection,
    AgendaProposal,
    AgendaState,
    AssessmentBasis,
    AutonomyPolicyProjection,
    CognitionCycleCoordinator,
    CycleCandidate,
    DecisionDimensions,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    ExplorationPolicy,
    OutcomeProjection,
    PolicyContext,
    SelectionProposal,
    SendTimeAuthorizer,
    SideEffect,
)
from alive_kernel_testkit import install_terminal_route  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-action-authorization-") as directory:
        root = Path(directory)
        journal = ExperienceJournal(root / "kernel.sqlite3")
        coordinator = CognitionCycleCoordinator(journal)
        agenda = AgendaProjection(journal, content_vault=coordinator.vault)
        evidence = EventEnvelope(
            event_id="evidence:authorization",
            event_type="discovery.observed",
            source="test.fixture",
            actor="system:test",
            subject="user:test",
            payload={"content_stored": False},
        )
        journal.append(evidence)
        delegation = EventEnvelope(
            event_id="delegation:authorization",
            event_type="conversation.inbound",
            source="test.channel",
            actor="user:test",
            subject="user:test",
            payload={"retained_content": False},
        )
        journal.append(delegation)
        proposal = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:test",
            details={"summary": "RAW_AUTHORIZATION_AGENDA_SENTINEL"},
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_ids=(evidence.event_id, delegation.event_id),
            confidence=0.9,
            item_id="agenda:authorization",
        )
        assert agenda.apply(
            agenda.append_proposal(proposal, actor="user:test")
        ).outcome == "active"

        def score(value: float, reason: str) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (evidence.event_id,), reason
            )

        candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=DecisionDimensions(
                score(0.9, "useful"),
                score(0.5, "bounded"),
                score(0.8, "novel"),
                score(0.9, "grounded"),
                score(0.2, "brief"),
                score(0.1, "low risk"),
            ),
            agenda_item_id=proposal.item_id,
            content_id="authorization-content",
            candidate_id="authorization-candidate",
        )
        cycle = coordinator.plan_safe_silence(
            cycle_id="authorization-cycle",
            subject="user:test",
            candidates=(
                CycleCandidate(
                    candidate,
                    {
                        "schema_version": 1,
                        "capability": "hermes.channel.send",
                        "operation": {
                            "text": "RAW_AUTHORIZATION_CONTENT_SENTINEL",
                            "format": "markdown",
                        },
                    },
                    "authorization topic",
                    "authorization source",
                ),
            ),
            policy_context=PolicyContext(can_interrupt=True),
            causation_id=evidence.event_id,
        )
        selection = coordinator.deliberation.append_selection(
            SelectionProposal(
                cycle.selection.frame_id,
                candidate.candidate_id,
                "provider/actual-model",
                "RAW_AUTHORIZATION_RATIONALE_SENTINEL",
            ),
            actor="system:test-model",
            subject="user:test",
            selection_id="authorization-selection",
            exploration_gate_event_id=cycle.exploration_event_id,
        )
        assert coordinator.deliberation.apply(selection).outcome == "validated"
        route_binding_id = install_terminal_route(
            journal, subject="user:test", content_vault=coordinator.vault
        )
        authorizer = SendTimeAuthorizer(
            journal,
            content_vault=coordinator.vault,
            route_binding_id=route_binding_id,
        )
        current = datetime.now(timezone.utc)
        missing_policy = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-policy-missing",
            now=current,
        )
        assert not missing_policy.authorized
        assert "autonomy_policy_missing" in missing_policy.reasons
        autonomy = AutonomyPolicyProjection(journal)
        active_policy = autonomy.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=0,
            enabled=True,
            context=PolicyContext(can_interrupt=True),
            operation_id="authorization-policy-active",
        )
        assert autonomy.apply(active_policy).outcome == "recorded"
        current = datetime.now(timezone.utc)
        allowed = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-allowed",
            now=current,
        )
        assert allowed.authorized and allowed.reasons == ()
        assert allowed.valid_until is not None and allowed.valid_until > current
        assert journal.read(event_type="action.attempted") == []
        assert authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-allowed",
            now=current,
        ) == allowed
        expired = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-allowed",
            now=allowed.valid_until,
        )
        assert not expired.authorized and "permit_expired" in expired.reasons
        outcomes = OutcomeProjection(journal, content_vault=coordinator.vault)
        expired_attempt_event = EventEnvelope(
            event_id="action.attempt:authorization-expired",
            event_type="action.attempted",
            source="alive.outcomes",
            actor="system:test-executor",
            subject="user:test",
            causation_id=allowed.event_id,
            occurred_at=allowed.valid_until,
            observed_at=allowed.valid_until,
            payload={
                "attempt_id": "authorization-expired",
                "authorization_event_id": allowed.event_id,
                "selection_event_id": selection.event.event_id,
                "candidate_id": candidate.candidate_id,
                "executor": "hermes.channel.send",
                "idempotency_key": "authorization-expired",
            },
        )
        expired_attempt = journal.append(expired_attempt_event)
        assert (
            outcomes.apply(expired_attempt).reason
            == "authorization_invalid_or_expired"
        )
        attempt = outcomes.append_attempt(
            authorization_event_id=allowed.event_id,
            selection_event_id=selection.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="authorization-valid-attempt",
            actor="system:test-executor",
            subject="user:test",
            attempt_id="authorization-valid-attempt",
        )
        assert outcomes.apply(attempt).outcome == "recorded"
        stored_attempt = outcomes.attempts(clearance="private")[-1]
        assert stored_attempt.authorization_event_id == allowed.event_id
        assert journal.read(event_type="delivery.succeeded") == []

        capability_denied = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.tool.execute",
            operation_id="authorization-wrong-capability",
            now=current,
        )
        assert not capability_denied.authorized
        assert "capability_mismatch" in capability_denied.reasons
        quiet_policy = autonomy.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=1,
            enabled=True,
            context=PolicyContext(can_interrupt=False),
            operation_id="authorization-policy-quiet",
        )
        assert autonomy.apply(quiet_policy).outcome == "recorded"
        try:
            authorizer.evaluate(
                selection_event_id=selection.event.event_id,
                subject="user:test",
                capability="hermes.channel.send",
                operation_id="authorization-allowed",
                now=current,
            )
        except ActionAuthorizationError as exc:
            assert "different semantics" in str(exc)
        else:
            raise AssertionError("authorization operation changed semantics")
        quiet_denied = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-quiet-window",
            now=current,
        )
        assert not quiet_denied.authorized
        assert "current_policy_rejected" in quiet_denied.reasons
        resumed_policy = autonomy.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=2,
            enabled=True,
            context=PolicyContext(can_interrupt=True),
            operation_id="authorization-policy-resumed",
        )
        assert autonomy.apply(resumed_policy).outcome == "recorded"

        observed_proposal = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:test",
            details={"summary": "observed but not delegated"},
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(evidence.event_id,),
            confidence=0.9,
            item_id="agenda:not-delegated",
        )
        assert agenda.apply(
            agenda.append_proposal(observed_proposal, actor="system:test")
        ).outcome == "active"
        observed_candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=candidate.dimensions,
            agenda_item_id=observed_proposal.item_id,
            content_id="authorization-content:not-delegated",
            candidate_id="authorization-candidate:not-delegated",
        )
        observed_cycle = coordinator.plan_safe_silence(
            cycle_id="authorization-not-delegated-cycle",
            subject="user:test",
            candidates=(
                CycleCandidate(
                    observed_candidate,
                    {
                        "schema_version": 1,
                        "capability": "hermes.channel.send",
                        "operation": {
                            "text": "observed proposal",
                            "format": "plain",
                        },
                        "chat_id": "model-selected-destination",
                    },
                    "observed topic",
                    "observed source",
                ),
            ),
            policy_context=PolicyContext(can_interrupt=True),
            causation_id=evidence.event_id,
        )
        observed_selection = coordinator.deliberation.append_selection(
            SelectionProposal(
                observed_cycle.selection.frame_id,
                observed_candidate.candidate_id,
                "provider/actual-model",
                "eligible is not delegated",
            ),
            actor="system:test-model",
            subject="user:test",
            selection_id="authorization-selection:not-delegated",
            exploration_gate_event_id=observed_cycle.exploration_event_id,
        )
        assert coordinator.deliberation.apply(observed_selection).outcome == "validated"
        unproven = authorizer.evaluate(
            selection_event_id=observed_selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-unproven-delegation",
            now=current,
        )
        assert not unproven.authorized
        assert "user_delegation_unproven" in unproven.reasons
        assert "action_contract_invalid" in unproven.reasons

        critical_candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.SYSTEM_CRITICAL,
            dimensions=candidate.dimensions,
            content_id="authorization-content:critical",
            candidate_id="authorization-candidate:critical",
        )
        critical_cycle = coordinator.plan_safe_silence(
            cycle_id="authorization-critical-cycle",
            subject="user:test",
            candidates=(
                CycleCandidate(
                    critical_candidate,
                    {
                        "schema_version": 1,
                        "capability": "hermes.channel.send",
                        "operation": {
                            "text": "unproven critical claim",
                            "format": "plain",
                        },
                    },
                    "critical topic",
                    "critical source",
                ),
            ),
            policy_context=PolicyContext(can_interrupt=True),
            causation_id=evidence.event_id,
        )
        critical_selection = coordinator.deliberation.append_selection(
            SelectionProposal(
                critical_cycle.selection.frame_id,
                critical_candidate.candidate_id,
                "provider/actual-model",
                "candidate label cannot grant critical authority",
            ),
            actor="system:test-model",
            subject="user:test",
            selection_id="authorization-selection:critical",
            exploration_gate_event_id=critical_cycle.exploration_event_id,
        )
        assert coordinator.deliberation.apply(critical_selection).outcome == "validated"
        critical_denied = authorizer.evaluate(
            selection_event_id=critical_selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-unproven-critical",
            now=current,
        )
        assert not critical_denied.authorized
        assert "system_critical_authority_unimplemented" in critical_denied.reasons

        transition = agenda.append_transition(
            proposal.item_id,
            AgendaState.COMPLETED,
            actor="system:test",
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_id=evidence.event_id,
            reason="opportunity ended",
            operation_id="agenda-transition:authorization-complete",
        )
        assert agenda.apply(transition).outcome == "transitioned"
        agenda_denied = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-closed-agenda",
            now=current,
        )
        assert not agenda_denied.authorized
        assert "agenda_not_active" in agenda_denied.reasons

        refreshed, _gate = coordinator.exploration.append_evaluation(
            cycle.selection.frame_id,
            ExplorationPolicy(),
            actor="system:test",
            subject="user:test",
            evaluation_id="authorization-refreshed-gate",
        )
        assert coordinator.exploration.apply(refreshed).outcome == "recorded"
        stale_gate = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-stale-gate",
            now=current,
        )
        assert not stale_gate.authorized
        assert "exploration_gate_stale" in stale_gate.reasons

        # An otherwise active agenda with erased authority content fails closed.
        agenda.content_vault.erase_item("agenda:agenda:not-delegated")
        erased_authority = authorizer.evaluate(
            selection_event_id=observed_selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-erased-authority",
            now=current,
        )
        assert not erased_authority.authorized
        assert "agenda_content_unavailable" in erased_authority.reasons

        authorizer.host.revoke_route(route_binding_id, observed_at=current)
        revoked_route = authorizer.evaluate(
            selection_event_id=selection.event.event_id,
            subject="user:test",
            capability="hermes.channel.send",
            operation_id="authorization-route-revoked",
            now=current,
        )
        assert not revoked_route.authorized
        assert "route_binding_revoked" in revoked_route.reasons

        raw = (root / "kernel.sqlite3").read_bytes()
        wal = root / "kernel.sqlite3-wal"
        if wal.exists():
            raw += wal.read_bytes()
        for forbidden in (
            b"RAW_AUTHORIZATION_AGENDA_SENTINEL",
            b"RAW_AUTHORIZATION_CONTENT_SENTINEL",
            b"RAW_AUTHORIZATION_RATIONALE_SENTINEL",
        ):
            assert forbidden not in raw

    print("HERMES_ALIVE_KERNEL_ACTION_AUTHORIZATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
