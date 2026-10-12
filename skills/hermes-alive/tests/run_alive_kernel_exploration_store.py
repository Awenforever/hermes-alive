#!/usr/bin/env python3
"""Private annotations, delivered exposure, receipts and replay contracts."""

from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from contextlib import closing
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))
from alive_kernel_testkit import authenticated_dispatch_receipt, inject_legacy_outcome_row

from alive_kernel import (  # noqa: E402
    ActionAuthority, ActionCandidate, ActionKind, AssessmentBasis,
    DecisionDimensions, DeliberationProjection, DimensionAssessment,
    EventEnvelope, ExperienceJournal, OutcomeKind, OutcomeProjection,
    PolicyContext, SelectionProposal, SideEffect,
)
from alive_kernel.exploration import (  # noqa: E402
    ExplorationMode, ExplorationPolicy, exploration_rejection_map,
)
from alive_kernel.exploration_store import ExplorationProjection  # noqa: E402
from alive_kernel_testkit import install_action_authorization  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-exploration-store-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        deliberation = DeliberationProjection(journal)
        exploration = ExplorationProjection(journal)
        outcomes = OutcomeProjection(journal)
        evidence = EventEnvelope(
            event_id="evidence:exploration-store", event_type="discovery.observed",
            source="test.fixture", actor="system:test", subject="user:test",
            payload={"fixture": True},
        )
        journal.append(evidence)

        def score(value: float) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (evidence.event_id,), "test evidence"
            )

        def make_candidate(name: str) -> ActionCandidate:
            return ActionCandidate(
                candidate_id=f"candidate:{name}", action_kind=ActionKind.SHARE,
                side_effect=SideEffect.COMMUNICATION,
                authority=ActionAuthority.USER_DELEGATED,
                content_id=f"candidate-content:{name}",
                dimensions=DecisionDimensions(
                    score(0.8), score(0.4), score(0.8),
                    score(0.9), score(0.2), score(0.1),
                ),
            )

        policy = ExplorationPolicy(
            window_size=5, max_explorations=1, minimum_share_sample=2,
            maximum_topic_share=0.5, maximum_source_share=0.5,
            maximum_topic_streak=1,
        )
        first = make_candidate("first")
        first_event, first_frame = deliberation.append_frame(
            (first,), PolicyContext(can_interrupt=True), actor="system:alive",
            subject="user:test", frame_id="frame:exploration-first",
            candidate_contents={first.content_id: {
                "schema_version": 1,
                "capability": "hermes.channel.send",
                "operation": {"text": "first", "format": "plain"},
            }},
        )
        deliberation.apply(first_event)
        first_annotation_event, first_annotation = exploration.append_annotation(
            frame_id=first_frame.frame_id, candidate_id=first.candidate_id,
            topic="combustion", source_label="source-one",
            mode=ExplorationMode.EXPLOIT, actor="system:discovery",
            subject="user:test", annotation_id="annotation:first",
        )
        canonical = first_annotation_event.event.canonical_json()
        assert "combustion" not in canonical and "source-one" not in canonical
        assert exploration.apply(first_annotation_event).outcome == "recorded"
        first_gate_event, first_gate = exploration.append_evaluation(
            first_frame.frame_id, policy, actor="system:alive",
            subject="user:test", evaluation_id="evaluation:first",
        )
        assert exploration.apply(first_gate_event).outcome == "recorded"
        assert first.candidate_id in first_gate.admissible_ids

        selected = deliberation.append_selection(
            SelectionProposal(
                first_frame.frame_id, first.candidate_id, "provider/model", "safe"
            ),
            actor="model:test", subject="user:test", selection_id="selection:first",
            exploration_gate_event_id=first_gate_event.event.event_id,
        )
        deliberation.apply(selected)
        authorization_event_id = install_action_authorization(
            journal,
            selection_event_id=selected.event.event_id,
            candidate_id=first.candidate_id,
            subject="user:test",
            executor="hermes.channel.send",
            fixture_name="exploration-store",
        )
        attempted = outcomes.append_attempt(
            authorization_event_id=authorization_event_id,
            selection_event_id=selected.event.event_id,
            candidate_id=first.candidate_id, executor="hermes.channel.send",
            idempotency_key="delivery:exploration-first", actor="system:test",
            subject="user:test", attempt_id="attempt:exploration-first",
        )
        outcomes.apply(attempted)
        receipt = authenticated_dispatch_receipt(
            journal, attempted, event_id="receipt:exploration-first",
        )
        delivered = outcomes.append_outcome(
            attempt_id="attempt:exploration-first",
            kind=OutcomeKind.DELIVERY_SUCCEEDED, source_event_id=receipt.event_id,
            details={"receipt": True}, actor="system:test", subject="user:test",
            outcome_id="outcome:exploration-first",
        )
        outcomes.apply(delivered)
        alias = replace(receipt, event_id="receipt:exploration-copy")
        journal.append(alias)
        copied = outcomes.append_outcome(
            attempt_id="attempt:exploration-first", kind=OutcomeKind.DELIVERY_SUCCEEDED,
            source_event_id=alias.event_id, details={"legacy_copy": True}, actor="system:test",
            subject="user:test", outcome_id="outcome:exploration-copy",
        )
        assert outcomes.apply(copied).outcome == "deduplicated"
        inject_legacy_outcome_row(outcomes, copied)
        unsigned = EventEnvelope(
            event_id="receipt:exploration-unsigned", event_type="delivery.succeeded",
            source="test.channel", actor="system:test", subject="user:test", payload={"legacy": True},
        )
        journal.append(unsigned)
        invalid = outcomes.append_outcome(
            attempt_id="attempt:exploration-first", kind=OutcomeKind.DELIVERY_SUCCEEDED,
            source_event_id=unsigned.event_id, details={}, actor="system:test",
            subject="user:test", outcome_id="outcome:exploration-invalid",
        )
        inject_legacy_outcome_row(outcomes, invalid)
        with closing(exploration._connect()) as connection:
            # Invalid/duplicate newest rows must not consume a requested
            # history limit and hide the genuinely observed older exposure.
            history = exploration._exposure_history(connection, "user:test", 1)
            assert len(history) == 1 and history[0].outcome_event_id == delivered.event.event_id

        second = make_candidate("second")
        second_event, second_frame = deliberation.append_frame(
            (second,), PolicyContext(can_interrupt=True), actor="system:alive",
            subject="user:test", frame_id="frame:exploration-second",
            candidate_contents={second.content_id: {
                "schema_version": 1,
                "capability": "hermes.channel.send",
                "operation": {"text": "second", "format": "plain"},
            }},
        )
        deliberation.apply(second_event)
        second_annotation_event, _annotation = exploration.append_annotation(
            frame_id=second_frame.frame_id, candidate_id=second.candidate_id,
            topic="combustion", source_label="source-one",
            mode=ExplorationMode.EXPLOIT, actor="system:discovery",
            subject="user:test", annotation_id="annotation:second",
        )
        exploration.apply(second_annotation_event)
        second_gate_event, second_gate = exploration.append_evaluation(
            second_frame.frame_id, policy, actor="system:alive",
            subject="user:test", evaluation_id="evaluation:second",
        )
        assert exploration.apply(second_gate_event).outcome == "recorded"
        assert second_gate.admissible_ids == (second_frame.silence_id,)
        assert exploration_rejection_map(second_gate)[second.candidate_id] == (
            "topic_share_exceeded", "source_share_exceeded", "topic_streak_exceeded"
        )
        assert second_gate.history_event_ids == (delivered.event.event_id,)

        before = exploration.gate_result(second_frame.frame_id)
        rebuilt = exploration.rebuild(batch_size=2)
        assert any(item.event_id == second_gate_event.event.event_id for item in rebuilt)
        assert exploration.gate_result(second_frame.frame_id) == before
        assert journal.get(copied.event.event_id) is not None
        assert journal.get(invalid.event.event_id) is not None

    print("HERMES_ALIVE_KERNEL_EXPLORATION_STORE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
