"""Disposition is explainable post-selection form, never synthetic emotion."""

from __future__ import annotations

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
    DispositionError,
    DispositionRecorder,
    ExperienceJournal,
    ExpressionStance,
    PolicyContext,
    SelectionProposal,
    Sensitivity,
    SideEffect,
    ValidatedSelection,
    derive_disposition,
    silence_candidate,
)
from alive_kernel_testkit import install_exploration_gate  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-disposition-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel" / "experience.sqlite3")
        deliberation = DeliberationProjection(journal)
        evidence_id = "event:disposition-evidence"

        def assessment(value: float, reason: str) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (evidence_id,), reason
            )

        from alive_kernel import EventEnvelope

        journal.append(
            EventEnvelope(
                event_id=evidence_id,
                event_type="observation.measured",
                source="test.fixture",
                actor="system:test",
                subject="user:disposition",
                payload={"raw_content_stored": False},
            )
        )
        candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=DecisionDimensions(
                assessment(0.8, "useful"),
                assessment(0.8, "time sensitive"),
                assessment(0.9, "new evidence"),
                assessment(0.9, "well supported"),
                assessment(0.7, "costly interruption"),
                assessment(0.4, "material but admissible risk"),
            ),
            content_id="candidate-content:disposition",
            candidate_id="candidate:disposition",
        )
        frame_record, frame = deliberation.append_frame(
            (candidate,),
            PolicyContext(can_interrupt=True, maximum_risk=0.5),
            actor="system:alive",
            subject="user:disposition",
            sensitivity=Sensitivity.PRIVATE,
            frame_id="frame:disposition",
            candidate_contents={
                "candidate-content:disposition": {"message": "private candidate"}
            },
        )
        assert deliberation.apply(frame_record).outcome == "recorded"
        gate_id = install_exploration_gate(
            journal,
            deliberation,
            frame,
            subject="user:disposition",
            fixture_name="disposition",
        )
        selection_record = deliberation.append_selection(
            SelectionProposal(
                frame.frame_id,
                candidate.candidate_id,
                "provider/test",
                "selected independently of expression",
            ),
            actor="model:test",
            subject="user:disposition",
            sensitivity=Sensitivity.PRIVATE,
            selection_id="selection:disposition",
            exploration_gate_event_id=gate_id,
        )
        assert deliberation.apply(selection_record).outcome == "validated"

        recorder = DispositionRecorder(
            journal, content_vault=deliberation.content_vault
        )
        record, snapshot = recorder.record(
            frame_id=frame.frame_id,
            selection_event_id=selection_record.event.event_id,
            subject="user:disposition",
        )
        assert recorder.verify(record)
        assert [cue.stance for cue in snapshot.cues] == [
            ExpressionStance.CAREFUL,
            ExpressionStance.GENTLE,
            ExpressionStance.FOCUSED,
            ExpressionStance.CURIOUS,
        ]
        assert all(cue.evidence_event_ids == (evidence_id,) for cue in snapshot.cues)
        assert snapshot.permits_action is False
        assert snapshot.changes_selection is False
        assert snapshot.may_change_semantics is False
        assert record.event.payload["emotion_claimed"] is False
        assert "annoyance" not in record.event.canonical_json()
        assert "affection" not in record.event.canonical_json()
        assert "ignored" not in record.event.canonical_json()

        silent = derive_disposition(
            ValidatedSelection(
                "frame:silent",
                silence_candidate(candidate_id="candidate:silent"),
                "system:test",
                "silence is independently selected",
            ),
            subject="user:disposition",
            selection_event_id="selection:silent",
        )
        assert not silent.renderable and silent.cues == ()
        assert silent.permits_action is False

        retry, repeated = recorder.record(
            frame_id=frame.frame_id,
            selection_event_id=selection_record.event.event_id,
            subject="user:disposition",
        )
        assert retry.event.event_id == record.event.event_id
        assert repeated == snapshot

        default_recorder = DispositionRecorder(journal)
        default_retry, default_snapshot = default_recorder.record(
            frame_id=frame.frame_id,
            selection_event_id=selection_record.event.event_id,
            subject="user:disposition",
        )
        assert default_retry.event.event_id == record.event.event_id
        assert default_snapshot == snapshot
        assert default_recorder.verify(default_retry)

        try:
            recorder.record(
                frame_id=frame.frame_id,
                selection_event_id="selection:foreign",
                subject="user:disposition",
            )
        except DispositionError:
            pass
        else:
            raise AssertionError("foreign selection must not create disposition")

    print("HERMES_ALIVE_KERNEL_DISPOSITION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
