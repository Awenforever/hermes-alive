#!/usr/bin/env python3
"""Causality, evidence, ambiguity, privacy, and replay outcome contracts."""

from __future__ import annotations

from pathlib import Path
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
from alive_kernel.outcomes import (  # noqa: E402
    OutcomeContentStatus,
    OutcomeKind,
    OutcomeProjection,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-outcomes-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        deliberation = DeliberationProjection(journal)
        outcomes = OutcomeProjection(journal)
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
                candidate.content_id: {"message": "Grounded proactive message."}
            },
        )
        deliberation.apply(frame_record)
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
        )
        assert deliberation.apply(selection_record).outcome == "validated"

        attempt_record = outcomes.append_attempt(
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel",
            idempotency_key="delivery:outcome-test",
            actor="system:executor",
            subject="user:test",
            attempt_id="attempt:outcome-test",
        )
        assert outcomes.apply(attempt_record).outcome == "recorded"
        retry = outcomes.append_attempt(
            selection_event_id=selection_record.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="hermes.channel",
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
