#!/usr/bin/env python3
"""Integrated, idempotent, no-side-effect cognition-cycle contracts."""

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
    AgendaAuthority,
    AgendaItemKind,
    AgendaProjection,
    AgendaProposal,
    AssessmentBasis,
    CognitionCycleCoordinator,
    CognitionCycleError,
    CycleCandidate,
    DecisionDimensions,
    DeliberationProjection,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    ExplorationMode,
    ExplorationProjection,
    PolicyContext,
    Sensitivity,
    SideEffect,
)


def dimensions(evidence_id: str) -> DecisionDimensions:
    def score(value: float, reason: str) -> DimensionAssessment:
        return DimensionAssessment(
            value,
            AssessmentBasis.MEASURED,
            (evidence_id,),
            reason,
        )

    return DecisionDimensions(
        user_value=score(0.8, "agenda priority"),
        urgency=score(0.5, "no immediate deadline"),
        novelty=score(0.9, "not previously exposed"),
        confidence=score(0.9, "direct observation"),
        interruption_cost=score(0.2, "short candidate"),
        risk=score(0.1, "no sensitive disclosure"),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-cycle-") as directory:
        path = Path(directory)
        journal = ExperienceJournal(path / "kernel.sqlite3")
        coordinator = CognitionCycleCoordinator(journal)
        agenda = AgendaProjection(journal, content_vault=coordinator.vault)
        evidence = EventEnvelope(
            event_id="evidence:cycle",
            event_type="discovery.observed",
            source="test.fixture",
            actor="system:test",
            subject="user:test",
            payload={"raw_content_stored": False},
        )
        journal.append(evidence)
        opportunity = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:test",
            details={"summary": "encrypted agenda sentinel"},
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(evidence.event_id,),
            confidence=0.9,
            priority=0.8,
            item_id="agenda:cycle",
        )
        assert agenda.apply(
            agenda.append_proposal(opportunity, actor="system:discovery")
        ).outcome == "active"
        action = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=dimensions(evidence.event_id),
            agenda_item_id=opportunity.item_id,
            content_id="cycle-content:test",
            candidate_id="candidate:cycle",
        )
        cycle_candidate = CycleCandidate(
            action,
            {"message": "RAW_CYCLE_CONTENT_SENTINEL"},
            "private topic sentinel",
            "private source sentinel",
            ExplorationMode.EXPLORE,
        )
        before = journal.last_sequence()
        result = coordinator.plan_safe_silence(
            cycle_id="cycle-test",
            subject="user:test",
            candidates=(cycle_candidate,),
            policy_context=PolicyContext(can_interrupt=True),
            causation_id=evidence.event_id,
            correlation_id="session:test",
        )
        after = journal.last_sequence()
        assert after > before
        assert result.selection.candidate.action_kind is ActionKind.SILENCE
        assert result.selection.selected_by == coordinator.SAFE_SILENCE_MODEL
        assert set(result.gate.admissible_ids) == {
            action.candidate_id,
            result.gate.silence_id,
        }

        repeated = coordinator.plan_safe_silence(
            cycle_id="cycle-test",
            subject="user:test",
            candidates=(cycle_candidate,),
            policy_context=PolicyContext(can_interrupt=True),
            causation_id=evidence.event_id,
            correlation_id="session:test",
        )
        assert repeated == result
        assert journal.last_sequence() == after

        stored = DeliberationProjection(
            journal, content_vault=coordinator.vault
        ).inspect(result.selection.frame_id, clearance=Sensitivity.PRIVATE)
        assert stored is not None and stored.selection == result.selection
        assert ExplorationProjection(
            journal, content_vault=coordinator.vault
        ).gate_result(result.selection.frame_id) == result.gate

        try:
            coordinator.plan_safe_silence(
                cycle_id="cycle-test",
                subject="user:test",
                candidates=(
                    CycleCandidate(
                        action,
                        {"message": "changed semantics"},
                        "private topic sentinel",
                        "private source sentinel",
                    ),
                ),
                policy_context=PolicyContext(can_interrupt=True),
                causation_id=evidence.event_id,
                correlation_id="session:test",
            )
        except (CognitionCycleError, ValueError):
            pass
        else:
            raise AssertionError("cycle ID was reused with changed semantics")

        empty = coordinator.plan_safe_silence(
            cycle_id="empty-cycle",
            subject="user:test",
            candidates=(),
            policy_context=PolicyContext(can_interrupt=False),
        )
        assert empty.gate.admissible_ids == (empty.gate.silence_id,)
        assert empty.selection.candidate.action_kind is ActionKind.SILENCE

        database = (path / "kernel.sqlite3").read_bytes()
        wal = path / "kernel.sqlite3-wal"
        if wal.exists():
            database += wal.read_bytes()
        for forbidden in (
            b"RAW_CYCLE_CONTENT_SENTINEL",
            b"private topic sentinel",
            b"private source sentinel",
            b"encrypted agenda sentinel",
        ):
            assert forbidden not in database

        coordinator.deliberation.rebuild(batch_size=2)
        coordinator.exploration.rebuild(batch_size=2)
        replayed = coordinator.deliberation.inspect(
            result.selection.frame_id, clearance=Sensitivity.PRIVATE
        )
        assert replayed is not None and replayed.selection == result.selection
        assert coordinator.exploration.gate_result(result.selection.frame_id) == result.gate

    print("HERMES_ALIVE_KERNEL_COGNITION_CYCLE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
