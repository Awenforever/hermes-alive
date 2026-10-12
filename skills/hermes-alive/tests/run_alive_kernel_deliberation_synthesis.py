#!/usr/bin/env python3
"""Hermes routing, gate enforcement, attribution and privacy for selection."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
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
    CycleCandidate,
    DecisionDimensions,
    DeliberationSynthesisError,
    DeliberationSynthesizer,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    ExplorationPolicy,
    PolicyContext,
    SelectionProposal,
    SideEffect,
)


def dimensions(evidence_id: str, *, risk: float) -> DecisionDimensions:
    def score(value: float, reason: str) -> DimensionAssessment:
        return DimensionAssessment(
            value, AssessmentBasis.MEASURED, (evidence_id,), reason
        )

    return DecisionDimensions(
        user_value=score(0.8, "agenda priority"),
        urgency=score(0.5, "bounded urgency"),
        novelty=score(0.9, "new evidence"),
        confidence=score(0.9, "direct evidence"),
        interruption_cost=score(0.2, "brief"),
        risk=score(risk, "measured risk"),
    )


def response(content: str, model: str = "provider/actual-fallback") -> SimpleNamespace:
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )


async def rejected(awaitable) -> DeliberationSynthesisError:
    try:
        await awaitable
    except DeliberationSynthesisError as exc:
        return exc
    raise AssertionError("invalid deliberation was accepted")


async def exercise(path: Path) -> None:
    journal = ExperienceJournal(path / "kernel.sqlite3")
    coordinator = CognitionCycleCoordinator(journal)
    agenda = AgendaProjection(journal, content_vault=coordinator.vault)
    evidence = EventEnvelope(
        event_id="evidence:deliberation-synthesis",
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
        details={"summary": "encrypted selector agenda"},
        authority=AgendaAuthority.DIRECT_OBSERVATION,
        source_event_ids=(evidence.event_id,),
        confidence=0.9,
        item_id="agenda:selector",
    )
    assert agenda.apply(
        agenda.append_proposal(opportunity, actor="system:discovery")
    ).outcome == "active"
    safe = ActionCandidate(
        action_kind=ActionKind.SHARE,
        side_effect=SideEffect.COMMUNICATION,
        authority=ActionAuthority.USER_DELEGATED,
        dimensions=dimensions(evidence.event_id, risk=0.1),
        agenda_item_id=opportunity.item_id,
        content_id="selector-content:safe",
        candidate_id="selector:safe",
    )
    risky = ActionCandidate(
        action_kind=ActionKind.TOOL_ACTION,
        side_effect=SideEffect.IRREVERSIBLE_EXTERNAL,
        authority=ActionAuthority.USER_CONFIRMATION_REQUIRED,
        dimensions=dimensions(evidence.event_id, risk=0.9),
        agenda_item_id=opportunity.item_id,
        content_id="selector-content:risky",
        candidate_id="selector:risky",
    )
    cycle = coordinator.plan_safe_silence(
        cycle_id="selector-cycle",
        subject="user:test",
        candidates=(
            CycleCandidate(
                safe,
                {"message": "RAW_SELECTOR_CONTENT_SENTINEL"},
                "topic safe",
                "source safe",
            ),
            CycleCandidate(
                risky,
                {"operation": "must not reach model"},
                "topic risky",
                "source risky",
            ),
        ),
        policy_context=PolicyContext(can_interrupt=True),
        causation_id=evidence.event_id,
    )
    assert risky.candidate_id not in cycle.gate.admissible_ids
    synthesizer = DeliberationSynthesizer(journal, content_vault=coordinator.vault)

    refreshed_record, refreshed_gate = coordinator.exploration.append_evaluation(
        cycle.selection.frame_id,
        ExplorationPolicy(),
        actor="system:test",
        subject="user:test",
        evaluation_id="selector-refreshed-gate",
    )
    assert coordinator.exploration.apply(refreshed_record).outcome == "recorded"
    assert refreshed_gate.admissible_ids == cycle.gate.admissible_ids

    stale_calls = 0

    async def stale_call(**_kwargs):
        nonlocal stale_calls
        stale_calls += 1
        return response("{}")

    error = await rejected(
        synthesizer.run(
            frame_id=cycle.selection.frame_id,
            gate_event_id=cycle.exploration_event_id,
            subject="user:test",
            call=stale_call,
            operation_id="stale-gate-operation",
        )
    )
    assert "gate is unavailable" in str(error)
    assert stale_calls == 0
    calls: list[dict] = []

    async def fake_call(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return response("RAW_SELECTOR_RESPONSE_SENTINEL not-json")
        return response(
            json.dumps(
                {
                    "candidate_id": safe.candidate_id,
                    "rationale": "RAW_RATIONALE_SENTINEL grounded and admissible",
                },
                separators=(",", ":"),
            )
        )

    result = await synthesizer.run(
        frame_id=cycle.selection.frame_id,
        gate_event_id=refreshed_record.event.event_id,
        subject="user:test",
        call=fake_call,
        requested_model="provider/requested-primary",
        operation_id="selector-operation",
        attempts=2,
    )
    assert len(calls) == 2
    assert all(call["task"] == "alive_deliberation" for call in calls)
    assert all(call["model"] == "provider/requested-primary" for call in calls)
    prompt = json.loads(calls[0]["messages"][1]["content"].split("\n", 1)[1])
    prompt_ids = {item["candidate_id"] for item in prompt}
    assert prompt_ids == {safe.candidate_id, cycle.gate.silence_id}
    assert risky.candidate_id not in calls[0]["messages"][1]["content"]
    assert result.actual_model == "provider/actual-fallback"
    assert result.selection.candidate.candidate_id == safe.candidate_id
    assert len(result.receipt_event_ids) == 2
    assert journal.read(event_type="action.attempted") == []

    before = len(calls)
    error = await rejected(
        synthesizer.run(
            frame_id=cycle.selection.frame_id,
            gate_event_id=refreshed_record.event.event_id,
            subject="user:test",
            call=fake_call,
            operation_id="selector-operation",
        )
    )
    assert "already attempted" in str(error)
    assert len(calls) == before

    receipts = journal.read(event_type="deliberation.synthesis_completed")
    assert [record.event.payload["status"] for record in receipts] == [
        "rejected",
        "selected",
    ]
    assert receipts[1].event.payload["actual_model"] == "provider/actual-fallback"
    assert all(record.event.payload["raw_prompt_stored"] is False for record in receipts)
    assert all(record.event.payload["raw_response_stored"] is False for record in receipts)

    cancelled_calls = 0

    async def cancelled_call(**_kwargs):
        nonlocal cancelled_calls
        cancelled_calls += 1
        raise asyncio.CancelledError()

    try:
        await synthesizer.run(
            frame_id=cycle.selection.frame_id,
            gate_event_id=refreshed_record.event.event_id,
            subject="user:test", call=cancelled_call,
            operation_id="selector-cancelled",
        )
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("cancellation was consumed")
    await rejected(synthesizer.run(
        frame_id=cycle.selection.frame_id,
        gate_event_id=refreshed_record.event.event_id,
        subject="user:test", call=cancelled_call,
        operation_id="selector-cancelled",
    ))
    assert cancelled_calls == 1

    concurrent_calls = 0

    async def concurrent_call(**_kwargs):
        nonlocal concurrent_calls
        concurrent_calls += 1
        await asyncio.sleep(0)
        return response(json.dumps({"candidate_id": safe.candidate_id,
                                    "rationale": "one concurrent operation"}))

    concurrent = await asyncio.gather(*(synthesizer.run(
        frame_id=cycle.selection.frame_id,
        gate_event_id=refreshed_record.event.event_id,
        subject="user:test", call=concurrent_call,
        operation_id="selector-concurrent",
    ) for _ in range(2)), return_exceptions=True)
    assert concurrent_calls == 1
    assert sum(isinstance(item, DeliberationSynthesisError) for item in concurrent) == 1

    async def selection_changed_during_call(**_kwargs):
        record = coordinator.deliberation.append_selection(
            SelectionProposal(cycle.selection.frame_id, safe.candidate_id,
                              "provider/newer-choice", "newer independent judgment"),
            actor="system:test", subject="user:test",
            selection_id="newer-selection-during-call",
            exploration_gate_event_id=refreshed_record.event.event_id,
        )
        assert coordinator.deliberation.apply(record).outcome == "validated"
        return response(json.dumps({"candidate_id": safe.candidate_id,
                                    "rationale": "older choice must not overwrite newer intent"}))

    before_newer = len(journal.read(event_type="deliberation.selected"))
    await rejected(synthesizer.run(
        frame_id=cycle.selection.frame_id,
        gate_event_id=refreshed_record.event.event_id,
        subject="user:test", call=selection_changed_during_call,
        operation_id="selection-changed-in-flight", attempts=2,
    ))
    assert len(journal.read(event_type="deliberation.selected")) == before_newer + 1

    # A model call yields control: a newer gate can replace the one shown in
    # its prompt before the response returns. Old context must not become a
    # durable current selection, even when the candidate IDs happen to match.
    async def gate_changed_during_call(**_kwargs):
        record, _gate = coordinator.exploration.append_evaluation(
            cycle.selection.frame_id,
            ExplorationPolicy(),
            actor="system:test", subject="user:test",
            evaluation_id="selector-gate-during-call",
        )
        assert coordinator.exploration.apply(record).outcome == "recorded"
        return response(json.dumps({
            "candidate_id": safe.candidate_id,
            "rationale": "response based on superseded context",
        }))

    selections_before = len(journal.read(event_type="deliberation.selected"))
    await rejected(synthesizer.run(
        frame_id=cycle.selection.frame_id,
        gate_event_id=refreshed_record.event.event_id,
        subject="user:test", call=gate_changed_during_call,
        operation_id="gate-changed-during-call", attempts=2,
    ))
    assert len(journal.read(event_type="deliberation.selected")) == selections_before

    failure_calls = 0
    current_gate_id = coordinator.exploration.latest_gate_event_id(cycle.selection.frame_id)

    async def gate_changed_then_provider_failed(**_kwargs):
        nonlocal failure_calls
        failure_calls += 1
        record, _gate = coordinator.exploration.append_evaluation(
            cycle.selection.frame_id, ExplorationPolicy(),
            actor="system:test", subject="user:test",
            evaluation_id="selector-gate-during-provider-failure",
        )
        assert coordinator.exploration.apply(record).outcome == "recorded"
        raise ConnectionError("private provider error must not be retained")

    await rejected(synthesizer.run(
        frame_id=cycle.selection.frame_id, gate_event_id=current_gate_id,
        subject="user:test", call=gate_changed_then_provider_failed,
        operation_id="context-invalid-before-retry", attempts=2,
    ))
    assert failure_calls == 1

    async def erase_during_call(**_kwargs):
        coordinator.vault.erase_item(safe.content_id)
        return response(json.dumps({"candidate_id": safe.candidate_id,
                                    "rationale": "erased candidate cannot be selected"}))

    await rejected(synthesizer.run(
        frame_id=cycle.selection.frame_id,
        gate_event_id=coordinator.exploration.latest_gate_event_id(cycle.selection.frame_id),
        subject="user:test", call=erase_during_call,
        operation_id="candidate-erased-in-flight", attempts=2,
    ))
    assert len(journal.read(event_type="deliberation.selected")) == selections_before

    database = (path / "kernel.sqlite3").read_bytes()
    wal = path / "kernel.sqlite3-wal"
    if wal.exists():
        database += wal.read_bytes()
    for forbidden in (
        b"RAW_SELECTOR_CONTENT_SENTINEL",
        b"RAW_SELECTOR_RESPONSE_SENTINEL",
        b"RAW_RATIONALE_SENTINEL",
        b"must not reach model",
    ):
        assert forbidden not in database


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="alive-kernel-deliberation-synthesis-"
    ) as directory:
        asyncio.run(exercise(Path(directory)))
    print("HERMES_ALIVE_KERNEL_DELIBERATION_SYNTHESIS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
