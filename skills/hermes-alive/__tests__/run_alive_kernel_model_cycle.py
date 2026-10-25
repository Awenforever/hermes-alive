#!/usr/bin/env python3
"""Discovery-to-agenda-to-model planning, without any external action."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))
from alive_kernel import (  # noqa: E402
    ActionAuthority, ActionCandidate, ActionKind, AssessmentBasis,
    CognitionCycleCoordinator, CognitionCycleError, CycleCandidate, DecisionDimensions,
    DeliberationSynthesisError, DimensionAssessment, DiscoveryCandidate,
    DiscoveryOpportunityIngestor, ExperienceJournal, KernelRecoverySupervisor,
    PolicyContext, Sensitivity, SideEffect,
)


def response(content: str) -> SimpleNamespace:
    return SimpleNamespace(model="provider/actual-fallback", choices=[
        SimpleNamespace(message=SimpleNamespace(content=content)),
    ])


async def exercise(shared: Path) -> None:
    journal = ExperienceJournal(shared / "kernel" / "experience.sqlite3")
    ingestion = DiscoveryOpportunityIngestor(journal)
    observation = ingestion.ingest(DiscoveryCandidate(
        source="synthetic local collector", title="PRIVATE_MODEL_CYCLE_TITLE",
        summary="PRIVATE_MODEL_CYCLE_SUMMARY", external_id="model-cycle-item",
        url="https://example.invalid/observation", observed_at=datetime.now(timezone.utc),
    ), subject="user:test")
    assert observation.agenda_decision.outcome == "active"
    coordinator = CognitionCycleCoordinator(journal, content_vault=ingestion.vault)

    def judgment(value: float) -> DimensionAssessment:
        # Fixture estimates, not measured benefit or inferred user permission.
        return DimensionAssessment(value, AssessmentBasis.MODEL_JUDGMENT,
                                   (observation.observation_event_id,), "synthetic estimate")

    action = ActionCandidate(
        ActionKind.SHARE, SideEffect.COMMUNICATION, ActionAuthority.USER_DELEGATED,
        DecisionDimensions(judgment(.8), judgment(.4), judgment(.9),
                           judgment(.9), judgment(.2), judgment(.1)),
        agenda_item_id=observation.agenda_item_id,
        content_id="model-cycle:content", candidate_id="model-cycle:share",
    )
    candidate = CycleCandidate(action, {"message": "PRIVATE_MODEL_CYCLE_BODY"},
                               "synthetic topic", "synthetic source")
    params = dict(cycle_id="integrated-model-cycle", subject="user:test",
                  candidates=(candidate,), policy_context=PolicyContext(can_interrupt=True),
                  causation_id=observation.observation_event_id)
    prepared = coordinator.prepare(**params)
    assert prepared.frame_event_id == journal.get(
        prepared.frame_event_id).event.event_id
    assert journal.get(prepared.frame_event_id).event.causation_id == observation.observation_event_id
    assert journal.read(event_type="deliberation.selected") == []
    before = journal.last_sequence()
    assert coordinator.prepare(**params) == prepared
    assert journal.last_sequence() == before

    baseline = coordinator.plan_safe_silence(**params)
    calls: list[dict] = []

    async def choose(**kwargs):
        calls.append(kwargs)
        values = json.loads(kwargs["messages"][1]["content"].split("\n", 1)[1])
        assert {item["candidate_id"] for item in values} == {
            action.candidate_id, prepared.frame.silence_id,
        }
        return response(json.dumps({"candidate_id": action.candidate_id,
                                    "rationale": "relevant synthetic opportunity"}))

    result = await coordinator.plan_with_model(
        call=choose, requested_model="provider/requested-primary", **params,
    )
    assert len(calls) == 1
    assert calls[0]["model"] == "provider/requested-primary"
    assert result.selection.candidate.action_kind is ActionKind.SHARE
    assert result.selection.selected_by == "provider/actual-fallback"
    assert len(result.model_receipt_event_ids) == 1
    assert journal.read(event_type="action.attempted") == []
    assert journal.read(event_type="dispatch.externally_started") == []

    # An old audit baseline is not the latest intent. Re-reading it must neither
    # mislabel the model choice as silence nor overwrite that newer selection.
    before = journal.last_sequence()
    assert coordinator.plan_safe_silence(**params) == baseline
    assert journal.last_sequence() == before
    assert coordinator.deliberation.inspect(
        prepared.frame.frame_id, clearance=Sensitivity.PRIVATE,
    ).selection == result.selection

    recovered = KernelRecoverySupervisor(shared).recover(batch_size=2)
    assert recovered is not None
    reopened = CognitionCycleCoordinator(ExperienceJournal(journal.path))
    assert reopened.deliberation.inspect(
        prepared.frame.frame_id, clearance=Sensitivity.PRIVATE,
    ).selection == result.selection
    try:
        await reopened.plan_with_model(call=choose, **params)
    except DeliberationSynthesisError as exc:
        assert "already attempted" in str(exc)
    else:
        raise AssertionError("recovered cycle spent on the model again")
    assert len(calls) == 1

    async def forbidden(**_kwargs):
        raise AssertionError("a silence-only gate must not invoke a model")

    # A one-shot generator catches accidental second preparation in the shortcut.
    blocked = await reopened.plan_with_model(
        call=forbidden, **{**params, "cycle_id": "blocked-model-cycle",
                           "candidates": (item for item in (candidate,)),
                           "policy_context": PolicyContext(can_interrupt=False)},
    )
    assert blocked.selection.candidate.action_kind is ActionKind.SILENCE
    assert blocked.model_receipt_event_ids == ()

    async def choose_silence(**kwargs):
        values = json.loads(kwargs["messages"][1]["content"].split("\n", 1)[1])
        silence_id = next(item["candidate_id"] for item in values
                          if item["action_kind"] == "silence")
        return response(json.dumps({"candidate_id": silence_id,
                                    "rationale": "no clear benefit in this fixture"}))

    quiet_params = {**params, "cycle_id": "deliberately-quiet-model-cycle"}
    quiet = await reopened.plan_with_model(call=choose_silence, **quiet_params)
    assert quiet.selection.candidate.action_kind is ActionKind.SILENCE
    assert quiet.selection.selected_by == "provider/actual-fallback"
    assert quiet.model_receipt_event_ids
    before = journal.last_sequence()
    try:
        reopened.plan_safe_silence(**quiet_params)
    except CognitionCycleError:
        pass
    else:
        raise AssertionError("a new audit baseline overwrote an existing model intent")
    assert journal.last_sequence() == before

    failure_params = {**params, "cycle_id": "failed-model-cycle"}

    async def invalid(**_kwargs):
        return response("private invalid response")

    try:
        await reopened.plan_with_model(call=invalid, attempts=1, **failure_params)
    except DeliberationSynthesisError:
        pass
    else:
        raise AssertionError("a failed model call was reported as a successful decision")
    failed_frame = reopened.prepare(**failure_params)
    assert reopened.deliberation.inspect(
        failed_frame.frame.frame_id, clearance=Sensitivity.PRIVATE,
    ).selection is None
    # An explicit audit close is allowed; it is never attributed to the model.
    closed = reopened.plan_safe_silence(**failure_params)
    assert closed.selection.selected_by == reopened.SAFE_SILENCE_MODEL

    database = journal.path.read_bytes()
    wal = journal.path.with_name(journal.path.name + "-wal")
    if wal.exists():
        database += wal.read_bytes()
    for raw in (b"PRIVATE_MODEL_CYCLE_TITLE", b"PRIVATE_MODEL_CYCLE_SUMMARY",
                b"PRIVATE_MODEL_CYCLE_BODY", b"private invalid response",
                b"relevant synthetic opportunity"):
        assert raw not in database


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-model-cycle-") as directory:
        asyncio.run(exercise(Path(directory)))
    print("HERMES_ALIVE_KERNEL_MODEL_CYCLE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
