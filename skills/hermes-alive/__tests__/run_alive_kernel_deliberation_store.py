#!/usr/bin/env python3
"""Durability, privacy, policy recheck, and replay contracts for deliberation."""

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
from alive_kernel.agenda import (  # noqa: E402
    AgendaAuthority,
    AgendaItemKind,
    AgendaProjection,
    AgendaProposal,
)
from alive_kernel.event_store import ExperienceJournal  # noqa: E402
from alive_kernel.events import Sensitivity  # noqa: E402
from alive_kernel_testkit import install_exploration_gate  # noqa: E402
from alive_kernel.events import EventEnvelope  # noqa: E402


def dimensions(
    *, confidence: float, risk: float, evidence_id: str = "event:evidence"
) -> DecisionDimensions:
    def value(number: float, reason: str) -> DimensionAssessment:
        return DimensionAssessment(
            number,
            AssessmentBasis.MODEL_JUDGMENT,
            (evidence_id,),
            reason,
        )

    return DecisionDimensions(
        user_value=value(0.8, "useful to the user"),
        urgency=value(0.5, "timely but not critical"),
        novelty=value(0.9, "not previously delivered"),
        confidence=value(confidence, "evidence coverage"),
        interruption_cost=value(0.2, "brief message"),
        risk=value(risk, "bounded disclosure"),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-deliberation-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        projection = DeliberationProjection(journal)
        agenda = AgendaProjection(journal, content_vault=projection.content_vault)
        evidence = EventEnvelope(
            event_id="event:evidence",
            event_type="discovery.observed",
            source="test.fixture",
            actor="system:test",
            subject="user:test",
            payload={"fixture": True},
        )
        journal.append(evidence)
        agenda_item = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:test",
            details={"summary": "grounded active opportunity"},
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(evidence.event_id,),
            confidence=0.9,
            item_id="agenda:active-test",
        )
        assert agenda.apply(
            agenda.append_proposal(agenda_item, actor="system:discovery")
        ).outcome == "active"
        safe = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=dimensions(confidence=0.9, risk=0.1),
            content_id="candidate-content:safe",
            candidate_id="candidate:safe",
        )
        risky = ActionCandidate(
            action_kind=ActionKind.TOOL_ACTION,
            side_effect=SideEffect.IRREVERSIBLE_EXTERNAL,
            authority=ActionAuthority.USER_CONFIRMATION_REQUIRED,
            dimensions=dimensions(confidence=0.9, risk=0.9),
            content_id="candidate-content:risky",
            candidate_id="candidate:risky",
        )
        frame_record, frame = projection.append_frame(
            (safe, risky),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            sensitivity=Sensitivity.PRIVATE,
            frame_id="frame:durable-test",
            candidate_contents={
                "candidate-content:safe": {"message": "A useful, grounded update."},
                "candidate-content:risky": {"operation": "unsafe external mutation"},
            },
        )
        assert projection.apply(frame_record).outcome == "recorded"
        gate_event_id = install_exploration_gate(
            journal, projection, frame,
            subject="user:test", fixture_name="deliberation-store",
        )
        retry_record, retry_frame = projection.append_frame(
            (safe, risky),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            sensitivity=Sensitivity.PRIVATE,
            frame_id="frame:durable-test",
            candidate_contents={
                "candidate-content:safe": {"message": "A useful, grounded update."},
                "candidate-content:risky": {"operation": "unsafe external mutation"},
            },
        )
        assert retry_record.event.event_id == frame_record.event.event_id
        assert retry_frame == frame
        assert projection.inspect(frame.frame_id, clearance=Sensitivity.INTERNAL) is None
        before_selection = projection.inspect(
            frame.frame_id, clearance=Sensitivity.PRIVATE
        )
        assert before_selection is not None
        assert before_selection.selection is None
        assert dict(before_selection.candidate_contents)["candidate-content:safe"] == {
            "message": "A useful, grounded update."
        }
        assert before_selection.frame.rejections[0].candidate_id == "candidate:risky"

        bypass_record = projection.append_selection(
            SelectionProposal(
                frame.frame_id,
                "candidate:safe",
                "provider/model",
                "Attempt to bypass the diversity gate.",
            ),
            actor="model:provider",
            subject="user:test",
            sensitivity=Sensitivity.PRIVATE,
            selection_id="selection:bypass-test",
        )
        bypass = projection.apply(bypass_record)
        assert bypass.outcome == "rejected"
        assert bypass.reason == "exploration_gate_invalid"

        selection_record = projection.append_selection(
            SelectionProposal(
                frame.frame_id,
                "candidate:safe",
                "provider/model",
                "The safe candidate is useful and policy-admissible.",
            ),
            actor="model:provider",
            subject="user:test",
            sensitivity=Sensitivity.PRIVATE,
            selection_id="selection:safe-test",
            exploration_gate_event_id=gate_event_id,
        )
        assert projection.apply(selection_record).outcome == "validated"
        selected = projection.inspect(frame.frame_id, clearance=Sensitivity.PRIVATE)
        assert selected is not None and selected.selection is not None
        assert selected.selection.candidate.candidate_id == "candidate:safe"

        rejected_record = projection.append_selection(
            SelectionProposal(
                frame.frame_id,
                "candidate:risky",
                "provider/model",
                "Attempt to ignore the deterministic policy.",
            ),
            actor="model:provider",
            subject="user:test",
            sensitivity=Sensitivity.PRIVATE,
            selection_id="selection:risky-test",
            exploration_gate_event_id=gate_event_id,
        )
        rejected = projection.apply(rejected_record)
        assert rejected.outcome == "rejected"
        assert rejected.reason == "policy_rejected_candidate"

        agenda_candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=dimensions(confidence=0.9, risk=0.1),
            agenda_item_id=agenda_item.item_id,
            content_id="candidate-content:active-agenda",
            candidate_id="candidate:active-agenda",
        )
        agenda_ok_record, _agenda_ok_frame = projection.append_frame(
            (agenda_candidate,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            frame_id="frame:active-agenda",
            candidate_contents={
                "candidate-content:active-agenda": {"message": "grounded agenda action"}
            },
        )
        assert projection.apply(agenda_ok_record).outcome == "recorded"

        foreign_evidence = EventEnvelope(
            event_id="event:foreign-evidence",
            event_type="discovery.observed",
            source="test.fixture",
            actor="system:test",
            subject="user:other",
            payload={"fixture": True},
        )
        journal.append(foreign_evidence)
        foreign_agenda = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:other",
            details={"summary": "another user's opportunity"},
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(foreign_evidence.event_id,),
            confidence=0.9,
            item_id="agenda:foreign",
        )
        assert agenda.apply(
            agenda.append_proposal(foreign_agenda, actor="system:discovery")
        ).outcome == "active"
        cross_subject = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=dimensions(
                confidence=0.9,
                risk=0.1,
                evidence_id=foreign_evidence.event_id,
            ),
            content_id="candidate-content:cross-subject",
            candidate_id="candidate:cross-subject",
        )
        cross_record, _cross_frame = projection.append_frame(
            (cross_subject,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            frame_id="frame:cross-subject",
            candidate_contents={
                "candidate-content:cross-subject": {"message": "must be rejected"}
            },
        )
        cross_decision = projection.apply(cross_record)
        assert cross_decision.outcome == "rejected"
        assert cross_decision.reason == "frame_boundary_mismatch"

        foreign_agenda_candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=dimensions(confidence=0.9, risk=0.1),
            agenda_item_id=foreign_agenda.item_id,
            content_id="candidate-content:foreign-agenda",
            candidate_id="candidate:foreign-agenda",
        )
        agenda_record, _agenda_frame = projection.append_frame(
            (foreign_agenda_candidate,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject="user:test",
            frame_id="frame:foreign-agenda",
            candidate_contents={
                "candidate-content:foreign-agenda": {"message": "must be rejected"}
            },
        )
        agenda_decision = projection.apply(agenda_record)
        assert agenda_decision.outcome == "rejected"
        assert agenda_decision.reason == "frame_boundary_mismatch"

        before_rebuild = projection.inspect(frame.frame_id, clearance=Sensitivity.PRIVATE)
        decisions = projection.rebuild(batch_size=2)
        assert any(item.event_id == selection_record.event.event_id for item in decisions)
        after_rebuild = projection.inspect(frame.frame_id, clearance=Sensitivity.PRIVATE)
        assert after_rebuild == before_rebuild

    print("HERMES_ALIVE_KERNEL_DELIBERATION_STORE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
