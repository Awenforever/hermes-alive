#!/usr/bin/env python3
"""Evidence sufficiency, review authority, expiry, erasure and replay tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ActionAuthority,
    ActionCandidate,
    ActionKind,
    AssessmentBasis,
    DecisionDimensions,
    DeliberationProjection,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    OutcomeKind,
    OutcomeProjection,
    PolicyContext,
    SelectionProposal,
    Sensitivity,
    SideEffect,
)
from alive_kernel.reflection import (  # noqa: E402
    ReflectionContentStatus,
    ReflectionProjection,
    ReflectionProposal,
    ReflectionReview,
    ReflectionScope,
    ReflectionState,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-reflection-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        deliberation = DeliberationProjection(journal)
        outcomes = OutcomeProjection(journal)
        reflections = ReflectionProjection(journal)
        now = datetime.now(timezone.utc)
        discovery = EventEnvelope(
            event_id="evidence:reflection-test",
            event_type="discovery.observed",
            source="test.fixture",
            actor="system:test",
            subject="user:test",
            payload={"fixture": True},
        )
        journal.append(discovery)

        def score(value: float, reason: str) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (discovery.event_id,), reason
            )

        candidate = ActionCandidate(
            candidate_id="candidate:reflection-test",
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            content_id="candidate-content:reflection-test",
            dimensions=DecisionDimensions(
                score(0.8, "value"), score(0.4, "urgency"),
                score(0.8, "novelty"), score(0.9, "confidence"),
                score(0.2, "interruption"), score(0.1, "risk"),
            ),
        )
        frame_event, frame = deliberation.append_frame(
            (candidate,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            frame_id="frame:reflection-test",
            candidate_contents={candidate.content_id: {"message": "test"}},
        )
        deliberation.apply(frame_event)
        selection_event = deliberation.append_selection(
            SelectionProposal(
                frame.frame_id, candidate.candidate_id, "provider/model", "admissible"
            ),
            actor="model:test",
            subject="user:test",
            selection_id="selection:reflection-test",
        )
        deliberation.apply(selection_event)
        attempt_event = outcomes.append_attempt(
            selection_event_id=selection_event.event.event_id,
            candidate_id=candidate.candidate_id,
            executor="test.channel",
            idempotency_key="delivery:reflection-test",
            actor="system:test",
            subject="user:test",
            attempt_id="attempt:reflection-test",
        )
        outcomes.apply(attempt_event)

        receipt = EventEnvelope(
            event_id="receipt:reflection-test",
            event_type="delivery.succeeded",
            source="test.channel",
            actor="system:test",
            subject="user:test",
            payload={"receipt": True},
        )
        journal.append(receipt)
        delivered = outcomes.append_outcome(
            attempt_id="attempt:reflection-test",
            kind=OutcomeKind.DELIVERY_SUCCEEDED,
            source_event_id=receipt.event_id,
            details={"receipt": True},
            actor="system:test",
            subject="user:test",
            outcome_id="outcome:reflection-delivered",
        )
        outcomes.apply(delivered)
        feedback = EventEnvelope(
            event_id="feedback:reflection-test",
            event_type="conversation.inbound",
            source="test.channel",
            actor="user:test",
            subject="user:test",
            payload={"structural": True},
        )
        journal.append(feedback)
        explicit = outcomes.append_outcome(
            attempt_id="attempt:reflection-test",
            kind=OutcomeKind.EXPLICIT_FEEDBACK,
            source_event_id=feedback.event_id,
            details={"signal": "user explicitly requested fewer interruptions"},
            actor="user:test",
            subject="user:test",
            outcome_id="outcome:reflection-feedback",
        )
        outcomes.apply(explicit)

        weak = ReflectionProposal(
            reflection_id="reflection:weak-test",
            subject="user:test",
            scope=ReflectionScope.INTERRUPTION,
            hypothesis="Delivery success means this timing is preferred.",
            predicted_effect="Send more at this time.",
            limitations=("A receipt is not user benefit.",),
            evidence_outcome_ids=("outcome:reflection-delivered",),
            confidence=0.8,
            expires_at=now + timedelta(days=30),
            model="provider/model",
        )
        weak_decision = reflections.apply(
            reflections.append_proposal(weak, actor="model:test")
        )
        assert weak_decision.reason == "evidence_insufficient_for_reflection"

        valid = ReflectionProposal(
            reflection_id="reflection:valid-test",
            subject="user:test",
            scope=ReflectionScope.INTERRUPTION,
            hypothesis="The user may prefer fewer non-urgent interruptions.",
            predicted_effect="Raise the interruption threshold for non-urgent shares.",
            limitations=("One explicit response may be context-specific.",),
            evidence_outcome_ids=("outcome:reflection-feedback",),
            confidence=0.7,
            expires_at=now + timedelta(days=30),
            model="provider/model",
        )
        proposal_event = reflections.append_proposal(valid, actor="model:test")
        assert reflections.apply(proposal_event).outcome == "proposed"
        proposed = reflections.list_reflections(clearance=Sensitivity.PRIVATE)
        assert [item.reflection_id for item in proposed] == [valid.reflection_id]

        stale_review = reflections.append_review(
            valid.reflection_id,
            ReflectionReview.ACCEPT,
            source_event_id=feedback.event_id,
            actor="user:test",
            subject="user:test",
            operation_id="stale-accept-test",
        )
        assert reflections.apply(stale_review).reason == "review_authority_invalid"

        approval = EventEnvelope(
            event_id="approval:reflection-test",
            event_type="conversation.inbound",
            source="test.channel",
            actor="user:test",
            subject="user:test",
            payload={"structural": True},
        )
        journal.append(approval)
        accepted_event = reflections.append_review(
            valid.reflection_id,
            ReflectionReview.ACCEPT,
            source_event_id=approval.event_id,
            actor="user:test",
            subject="user:test",
            operation_id="accept-test",
        )
        assert reflections.apply(accepted_event).outcome == ReflectionState.ACCEPTED.value
        accepted = reflections.list_reflections(clearance=Sensitivity.PRIVATE)
        assert accepted[0].state is ReflectionState.ACCEPTED

        reflections.content_vault.erase_item(accepted[0].content_id)
        erased_before = reflections.list_reflections(clearance=Sensitivity.PRIVATE)
        assert erased_before[0].content_status is ReflectionContentStatus.ERASED
        reflections.rebuild(batch_size=2)
        assert reflections.list_reflections(clearance=Sensitivity.PRIVATE) == erased_before

        retraction = EventEnvelope(
            event_id="retraction:reflection-test",
            event_type="conversation.inbound",
            source="test.channel",
            actor="user:test",
            subject="user:test",
            payload={"structural": True},
        )
        journal.append(retraction)
        retract_event = reflections.append_review(
            valid.reflection_id,
            ReflectionReview.RETRACT,
            source_event_id=retraction.event_id,
            actor="user:test",
            subject="user:test",
            operation_id="retract-test",
        )
        assert reflections.apply(retract_event).outcome == ReflectionState.RETRACTED.value
        retracted = reflections.list_reflections(
            clearance=Sensitivity.PRIVATE,
            states=(ReflectionState.RETRACTED,),
        )
        assert [item.reflection_id for item in retracted] == [valid.reflection_id]

    print("HERMES_ALIVE_KERNEL_REFLECTION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
