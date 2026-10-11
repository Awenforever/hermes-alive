#!/usr/bin/env python3
"""Bounded influence, source authority, rollback, privacy and replay tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ActionAuthority, ActionCandidate, ActionKind, AssessmentBasis,
    DecisionDimensions, DeliberationProjection, DimensionAssessment,
    EventEnvelope, ExperienceJournal, OutcomeKind, OutcomeProjection,
    PolicyContext, SelectionProposal, Sensitivity, SideEffect,
)
from alive_kernel.preference_learning import (  # noqa: E402
    PreferenceAxis,
    PreferenceContentStatus,
    PreferenceDirection,
    PreferenceLearningProjection,
    PreferenceSignalOrigin,
    PreferenceSignalProposal,
)
from alive_kernel.reflection import (  # noqa: E402
    ReflectionProjection, ReflectionProposal, ReflectionReview, ReflectionScope
)
from alive_kernel_testkit import (  # noqa: E402
    install_action_authorization,
    install_exploration_gate,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-preference-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        deliberation = DeliberationProjection(journal)
        outcomes = OutcomeProjection(journal)
        reflections = ReflectionProjection(journal)
        learning = PreferenceLearningProjection(journal)
        now = datetime.now(timezone.utc)
        evidence = EventEnvelope(
            event_id="evidence:preference-test", event_type="discovery.observed",
            source="test.fixture", actor="system:test", subject="user:test",
            payload={"fixture": True},
        )
        journal.append(evidence)

        def score(value: float) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (evidence.event_id,), "test evidence"
            )

        candidate = ActionCandidate(
            candidate_id="candidate:preference-test", action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            content_id="candidate-content:preference-test",
            dimensions=DecisionDimensions(
                score(0.8), score(0.4), score(0.8),
                score(0.9), score(0.2), score(0.1),
            ),
        )
        framed, frame = deliberation.append_frame(
            (candidate,), PolicyContext(can_interrupt=True), actor="system:alive",
            subject="user:test", frame_id="frame:preference-test",
            candidate_contents={candidate.content_id: {"message": "test"}},
        )
        deliberation.apply(framed)
        gate_event_id = install_exploration_gate(
            journal, deliberation, frame,
            subject="user:test", fixture_name="preference-learning",
        )
        selected = deliberation.append_selection(
            SelectionProposal(frame.frame_id, candidate.candidate_id, "model", "safe"),
            actor="model:test", subject="user:test",
            selection_id="selection:preference-test",
            exploration_gate_event_id=gate_event_id,
        )
        deliberation.apply(selected)
        authorization_event_id = install_action_authorization(
            journal,
            selection_event_id=selected.event.event_id,
            candidate_id=candidate.candidate_id,
            subject="user:test",
            executor="test.channel",
            fixture_name="preference",
        )
        attempted = outcomes.append_attempt(
            authorization_event_id=authorization_event_id,
            selection_event_id=selected.event.event_id,
            candidate_id=candidate.candidate_id, executor="test.channel",
            idempotency_key="delivery:preference-test", actor="system:test",
            subject="user:test", attempt_id="attempt:preference-test",
        )
        outcomes.apply(attempted)
        feedback_event = EventEnvelope(
            event_id="feedback:preference-test", event_type="conversation.inbound",
            source="test.channel", actor="user:test", subject="user:test",
            payload={"structural": True},
        )
        journal.append(feedback_event)
        feedback = outcomes.append_outcome(
            attempt_id="attempt:preference-test", kind=OutcomeKind.EXPLICIT_FEEDBACK,
            source_event_id=feedback_event.event_id,
            details={"signal": "prefer concise proactive messages"},
            actor="user:test", subject="user:test",
            outcome_id="outcome:preference-feedback",
        )
        outcomes.apply(feedback)

        explicit_signal = PreferenceSignalProposal(
            observation_id="preference-observation:explicit",
            subject="user:test", axis=PreferenceAxis.PRESENTATION,
            key="message_length", option="concise",
            direction=PreferenceDirection.SUPPORT,
            origin=PreferenceSignalOrigin.EXPLICIT_FEEDBACK,
            source_id="outcome:preference-feedback",
            source_event_id=feedback.event.event_id,
            rationale="The user explicitly requested concise messages.",
            weight=0.25, expires_at=now + timedelta(days=180),
        )
        explicit_record = learning.append_observation(
            explicit_signal, actor="system:learning"
        )
        assert "message_length" not in explicit_record.event.canonical_json()
        assert "concise" not in explicit_record.event.canonical_json()
        assert learning.apply(explicit_record).outcome == "recorded"
        estimate = learning.estimates(clearance=Sensitivity.PRIVATE)[0]
        assert round(estimate.probability, 6) == round(2.25 / 4.25, 6)
        assert estimate.support_mass == 0.25

        overweight = PreferenceSignalProposal(
            observation_id="preference-observation:overweight",
            subject="user:test", axis=PreferenceAxis.PRESENTATION,
            key="message_length", option="concise",
            direction=PreferenceDirection.SUPPORT,
            origin=PreferenceSignalOrigin.EXPLICIT_FEEDBACK,
            source_id="outcome:preference-feedback",
            source_event_id=feedback.event.event_id,
            rationale="Must not exceed the origin cap.", weight=0.3,
            expires_at=now + timedelta(days=180),
        )
        assert learning.apply(
            learning.append_observation(overweight, actor="system:learning")
        ).reason == "observation_boundary_mismatch"

        duplicate = PreferenceSignalProposal(
            observation_id="preference-observation:duplicate",
            subject="user:test", axis=PreferenceAxis.PRESENTATION,
            key="message_length", option="concise",
            direction=PreferenceDirection.SUPPORT,
            origin=PreferenceSignalOrigin.EXPLICIT_FEEDBACK,
            source_id="outcome:preference-feedback",
            source_event_id=feedback.event.event_id,
            rationale="The same source must not count twice.",
            weight=0.25, expires_at=now + timedelta(days=180),
        )
        assert learning.apply(
            learning.append_observation(duplicate, actor="system:learning")
        ).reason == "source_already_counted"

        reflection = ReflectionProposal(
            reflection_id="reflection:preference-test", subject="user:test",
            scope=ReflectionScope.PRESENTATION,
            hypothesis="The user may prefer concise proactive messages.",
            predicted_effect="Shorter messages may reduce interruption cost.",
            limitations=("The feedback may be context-specific.",),
            evidence_outcome_ids=("outcome:preference-feedback",),
            confidence=0.7, expires_at=now + timedelta(days=90), model="model",
        )
        reflected = reflections.append_proposal(reflection, actor="model:test")
        reflections.apply(reflected)
        approval = EventEnvelope(
            event_id="approval:preference-test", event_type="conversation.inbound",
            source="test.channel", actor="user:test", subject="user:test",
            payload={"structural": True},
        )
        journal.append(approval)
        accepted = reflections.append_review(
            reflection.reflection_id, ReflectionReview.ACCEPT,
            source_event_id=approval.event_id, actor="user:test", subject="user:test",
            operation_id="accept-preference-test",
        )
        reflections.apply(accepted)
        reflected_signal = PreferenceSignalProposal(
            observation_id="preference-observation:reflection",
            subject="user:test", axis=PreferenceAxis.PRESENTATION,
            key="message_length", option="concise",
            direction=PreferenceDirection.OPPOSE,
            origin=PreferenceSignalOrigin.ACCEPTED_REFLECTION,
            source_id=reflection.reflection_id,
            source_event_id=accepted.event.event_id,
            rationale="A bounded counter-signal for test coverage.",
            weight=0.15, expires_at=now + timedelta(days=60),
        )
        reflected_record = learning.append_observation(
            reflected_signal, actor="system:learning"
        )
        assert learning.apply(reflected_record).outcome == "recorded"
        estimate = learning.estimates(clearance=Sensitivity.PRIVATE)[0]
        assert round(estimate.probability, 6) == round(2.25 / 4.4, 6)
        learning.content_vault.erase_item(
            f"preference-observation:{reflected_signal.observation_id}"
        )
        estimate = learning.estimates(clearance=Sensitivity.PRIVATE)[0]
        assert estimate.content_status is PreferenceContentStatus.AVAILABLE
        assert estimate.key == "message_length"

        retraction_message = EventEnvelope(
            event_id="retract-reflection:preference-test",
            event_type="conversation.inbound", source="test.channel",
            actor="user:test", subject="user:test", payload={"structural": True},
        )
        journal.append(retraction_message)
        retract_reflection = reflections.append_review(
            reflection.reflection_id, ReflectionReview.RETRACT,
            source_event_id=retraction_message.event_id,
            actor="user:test", subject="user:test", operation_id="retract-preference-test",
        )
        reflections.apply(retract_reflection)
        estimate = learning.estimates(clearance=Sensitivity.PRIVATE)[0]
        assert round(estimate.probability, 6) == round(2.25 / 4.25, 6)
        assert estimate.evidence_ids == (explicit_signal.observation_id,)

        retract_signal_message = EventEnvelope(
            event_id="retract-signal:preference-test",
            event_type="conversation.inbound", source="test.channel",
            actor="user:test", subject="user:test", payload={"structural": True},
        )
        journal.append(retract_signal_message)
        retract_signal = learning.append_retraction(
            explicit_signal.observation_id,
            source_event_id=retract_signal_message.event_id,
            actor="user:test", subject="user:test", operation_id="signal-test",
        )
        assert learning.apply(retract_signal).outcome == "retracted"
        assert learning.estimates(clearance=Sensitivity.PRIVATE) == []

        learning.rebuild(batch_size=2)
        assert learning.estimates(clearance=Sensitivity.PRIVATE) == []

    print("HERMES_ALIVE_KERNEL_PREFERENCE_LEARNING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
