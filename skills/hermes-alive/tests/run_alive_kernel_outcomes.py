#!/usr/bin/env python3
"""Causality, evidence, ambiguity, privacy, and replay outcome contracts."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel.deliberation import (  # noqa: E402
    ActionAuthority,
    ActionCandidate,
    ActionKind,
    AssessmentBasis,
    DecisionDimensions,
    DimensionAssessment,
    PolicyContext,
    SelectionProposal,
    SideEffect,
)
from alive_kernel.deliberation_store import DeliberationProjection  # noqa: E402
from alive_kernel.event_store import ExperienceJournal  # noqa: E402
from alive_kernel.events import EventEnvelope, Sensitivity  # noqa: E402
from alive_kernel.evaluation import build_factual_episodes  # noqa: E402
from alive_kernel.outcomes import (  # noqa: E402
    OutcomeContentStatus,
    OutcomeKind,
    OutcomeProjection,
)
from alive_kernel_testkit import (  # noqa: E402
    install_action_authorization,
    install_exploration_gate,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-outcomes-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        deliberation = DeliberationProjection(journal)
        legacy = sqlite3.connect(journal.path)
        try:
            legacy.execute(
                """
                CREATE TABLE action_attempts_v1 (
                    attempt_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
                    selection_event_id TEXT NOT NULL, frame_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL, subject TEXT NOT NULL,
                    executor TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
                    sensitivity TEXT NOT NULL, attempted_at TEXT NOT NULL
                )
                """
            )
            legacy.commit()
        finally:
            legacy.close()
        outcomes = OutcomeProjection(journal)
        migrated = sqlite3.connect(journal.path)
        try:
            assert "authorization_event_id" in {
                row[1]
                for row in migrated.execute("PRAGMA table_info(action_attempts_v1)")
            }
        finally:
            migrated.close()
        evidence = EventEnvelope(
            event_id="evidence:outcome-test",
            event_type="discovery.observed",
            source="test.fixture",
            actor="system:test",
            subject="user:test",
            payload={"fixture": True},
        )
        journal.append(evidence)
        historical_reply = EventEnvelope(
            event_id="reply:historical-outcome-test",
            event_type="conversation.inbound",
            source="test.channel",
            actor="user:test",
            subject="user:test",
            payload={"structural": True},
        )
        journal.append(historical_reply)

        def assessment(value: float, reason: str) -> DimensionAssessment:
            return DimensionAssessment(
                value,
                AssessmentBasis.MEASURED,
                (evidence.event_id,),
                reason,
            )

        candidate = ActionCandidate(
            candidate_id="candidate:outcome-test",
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            content_id="candidate-content:outcome-test",
            dimensions=DecisionDimensions(
                assessment(0.8, "valuable"),
                assessment(0.4, "not urgent"),
                assessment(0.9, "novel"),
                assessment(0.9, "well supported"),
                assessment(0.2, "brief"),
                assessment(0.1, "low risk"),
            ),
        )
        frame_record, frame = deliberation.append_frame(
            (candidate,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            frame_id="frame:outcome-test",
            candidate_contents={
                candidate.content_id: {
                    "schema_version": 1,
                    "capability": "hermes.channel.send",
                    "operation": {
                        "text": "Grounded proactive message.",
                        "format": "markdown",
                    },
                }
            },
        )
        deliberation.apply(frame_record)
        gate_event_id = install_exploration_gate(
            journal, deliberation, frame,
            subject="user:test", fixture_name="outcomes",
        )
        selection_record = deliberation.append_selection(
            SelectionProposal(
                frame.frame_id,
                candidate.candidate_id,
                "provider/model",
                "The candidate is admissible and useful.",
            ),
            actor="model:test",
            subject="user:test",
            selection_id="selection:outcome-test",
            exploration_gate_event_id=gate_event_id,
        )
        assert deliberation.apply(selection_record).outcome == "validated"
        authorization_event_id = install_action_authorization(
            journal,
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            subject="user:test",
            executor="hermes.channel.send",
            fixture_name="outcomes",
        )
        authentic = journal.get(authorization_event_id)
        assert authentic is not None
        forged_payload = dict(authentic.event.payload)
        forged_payload.pop("integrity_authenticator")
        forged_payload["operation_id"] = "fixture:forged-authorization"
        forged_authorization = EventEnvelope(
            event_id="action.authorization:fixture:forged-authorization",
            event_type="action.authorization_evaluated",
            source="alive.authorization",
            actor="system:alive-authorizer",
            subject="user:test",
            causation_id=selection_record.event.event_id,
            occurred_at=authentic.event.occurred_at,
            observed_at=authentic.event.observed_at,
            expires_at=authentic.event.expires_at,
            sensitivity=authentic.event.sensitivity,
            payload=forged_payload,
        )
        journal.append(forged_authorization)
        forged_attempt = outcomes.append_attempt(
            authorization_event_id=forged_authorization.event_id,
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="delivery:forged-authorization",
            actor="system:executor",
            subject="user:test",
            attempt_id="attempt:forged-authorization",
        )
        assert (
            outcomes.apply(forged_attempt).reason
            == "authorization_invalid_or_expired"
        )

        missing_authorization = outcomes.append_attempt(
            authorization_event_id="action.authorization:missing",
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="delivery:missing-authorization",
            actor="system:executor",
            subject="user:test",
            attempt_id="attempt:missing-authorization",
        )
        assert (
            outcomes.apply(missing_authorization).reason
            == "authorization_invalid_or_expired"
        )
        mismatched_capability = outcomes.append_attempt(
            authorization_event_id=authorization_event_id,
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.tool.execute",
            idempotency_key="delivery:mismatched-capability",
            actor="system:executor",
            subject="user:test",
            attempt_id="attempt:mismatched-capability",
        )
        assert (
            outcomes.apply(mismatched_capability).reason
            == "authorization_invalid_or_expired"
        )

        attempt_record = outcomes.append_attempt(
            authorization_event_id=authorization_event_id,
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="delivery:outcome-test",
            actor="system:executor",
            subject="user:test",
            attempt_id="attempt:outcome-test",
        )
        assert outcomes.apply(attempt_record).outcome == "recorded"
        snapshot_before_outcomes = journal.last_sequence()
        retry = outcomes.append_attempt(
            authorization_event_id=authorization_event_id,
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel.send",
            idempotency_key="delivery:outcome-test",
            actor="system:executor",
            subject="user:test",
            attempt_id="attempt:outcome-test",
        )
        assert retry.event.event_id == attempt_record.event.event_id

        delivery = EventEnvelope(
            event_id="delivery-receipt:outcome-test",
            event_type="delivery.succeeded",
            source="test.channel",
            actor="system:channel",
            subject="user:test",
            payload={"receipt": True},
        )
        journal.append(delivery)
        delivered_record = outcomes.append_outcome(
            attempt_id="attempt:outcome-test",
            kind=OutcomeKind.DELIVERY_SUCCEEDED,
            source_event_id=delivery.event_id,
            details={"channel": "test", "receipt": "opaque"},
            actor="system:channel",
            subject="user:test",
            outcome_id="outcome:delivered-test",
        )
        assert outcomes.apply(delivered_record).outcome == "recorded"

        reply = EventEnvelope(
            event_id="reply:outcome-test",
            event_type="conversation.inbound",
            source="test.channel",
            actor="user:test",
            subject="user:test",
            payload={"structural": True},
        )
        journal.append(reply)
        reply_record = outcomes.append_outcome(
            attempt_id="attempt:outcome-test",
            kind=OutcomeKind.USER_REPLIED,
            source_event_id=reply.event_id,
            details={"classification": "substantive_reply"},
            actor="user:test",
            subject="user:test",
            outcome_id="outcome:reply-test",
        )
        assert outcomes.apply(reply_record).outcome == "recorded"

        stale_source_record = outcomes.append_outcome(
            attempt_id="attempt:outcome-test",
            kind=OutcomeKind.USER_REPLIED,
            source_event_id=historical_reply.event_id,
            details={"classification": "stale"},
            actor="user:test",
            subject="user:test",
            outcome_id="outcome:stale-test",
        )
        assert outcomes.apply(stale_source_record).reason == "invalid_outcome_source"

        forged = outcomes.append_outcome(
            attempt_id="attempt:outcome-test",
            kind=OutcomeKind.USER_CORRECTED,
            source_event_id=reply.event_id,
            details={"classification": "forged"},
            actor="model:test",
            subject="user:test",
            outcome_id="outcome:forged-test",
        )
        assert outcomes.apply(forged).reason == "user_outcome_actor_mismatch"

        try:
            OutcomeKind("no_reply")
        except ValueError:
            pass
        else:
            raise AssertionError("ambiguous no-reply was accepted as an outcome")

        assert outcomes.attempts(clearance=Sensitivity.INTERNAL) == []
        attempts_before = outcomes.attempts(clearance=Sensitivity.PRIVATE)
        observed_before = outcomes.outcomes(
            "attempt:outcome-test", clearance=Sensitivity.PRIVATE
        )
        assert [item.kind for item in observed_before] == [
            OutcomeKind.DELIVERY_SUCCEEDED,
            OutcomeKind.USER_REPLIED,
        ]
        outcomes.content_vault.erase_item(observed_before[0].content_id)
        observed_before = outcomes.outcomes(
            "attempt:outcome-test", clearance=Sensitivity.PRIVATE
        )
        assert observed_before[0].content_status is OutcomeContentStatus.ERASED
        historical_episodes = build_factual_episodes(
            journal, outcomes, clearance=Sensitivity.PRIVATE,
            observed_through_sequence=snapshot_before_outcomes,
        )
        assert len(historical_episodes) == 1
        assert historical_episodes[0].labels.delivery_succeeded is None
        assert historical_episodes[0].labels.useful is None
        assert historical_episodes[0].outcome_event_ids == ()
        current_episodes = build_factual_episodes(
            journal, outcomes, clearance=Sensitivity.PRIVATE
        )
        assert current_episodes[0].labels.delivery_succeeded is True
        assert current_episodes[0].labels.useful is None
        outcomes.rebuild(batch_size=2)
        assert outcomes.attempts(clearance=Sensitivity.PRIVATE) == attempts_before
        assert (
            outcomes.outcomes("attempt:outcome-test", clearance=Sensitivity.PRIVATE)
            == observed_before
        )

    print("HERMES_ALIVE_KERNEL_OUTCOMES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
