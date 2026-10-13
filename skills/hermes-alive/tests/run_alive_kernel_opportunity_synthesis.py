#!/usr/bin/env python3
"""Owner-scoped interpretation, partial rejection and composed shadow choice."""

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
    ActionAuthority, ActionKind, AssessmentBasis, CognitionCycleCoordinator,
    DiscoveryCandidate, DiscoveryOpportunityIngestor, ExperienceJournal,
    OpportunitySynthesizer, OpportunitySynthesisError, PolicyContext, Sensitivity,
)
from alive_kernel.discovery_opportunities import DiscoveryOpportunityError


def response(value: dict) -> SimpleNamespace:
    return SimpleNamespace(model="provider/actual-interpreter", choices=[
        SimpleNamespace(message=SimpleNamespace(content=json.dumps(value))),
    ])


async def exercise(root: Path) -> None:
    journal = ExperienceJournal(root / "kernel" / "experience.sqlite3")
    reader = DiscoveryOpportunityIngestor(journal)
    other = reader.ingest(DiscoveryCandidate(
        source="foreign source", title="OTHER_OWNER_PRIVATE_TITLE", summary="foreign private text",
        url="https://example.invalid/other", priority_hint=.99,
        observed_at=datetime.now(timezone.utc),
    ), subject="user:other")
    own = reader.ingest(DiscoveryCandidate(
        source="synthetic source", title="OWN_PRIVATE_TITLE", summary="OWN_PRIVATE_SUMMARY",
        url="https://example.invalid/own", priority_hint=.01,
        observed_at=datetime.now(timezone.utc),
    ), subject="user:test")
    selected = reader.active_evidence(subject="user:test", clearance=Sensitivity.PRIVATE, limit=1)
    assert len(selected) == 1 and selected[0].agenda_item_id == own.agenda_item_id
    assert reader.active_evidence(subject="user:test", clearance=Sensitivity.PUBLIC) == ()
    pins = (own.observation_event_id,)
    assert reader.active_evidence(subject="user:test", clearance=Sensitivity.PRIVATE,
                                  observation_event_ids=pins) == selected
    assert reader.active_evidence(subject="user:test", clearance=Sensitivity.PUBLIC,
                                  observation_event_ids=pins) == ()
    assert reader.active_evidence(subject="user:other", clearance=Sensitivity.PRIVATE,
                                  observation_event_ids=pins) == ()
    assert reader.active_evidence(subject="user:test", clearance=Sensitivity.PRIVATE,
        observation_event_ids=(other.observation_event_id, own.observation_event_id)) == selected
    for invalid_pins in ((), (own.observation_event_id,)*2, (["unhashable"],), "not-a-tuple"):
        try:
            reader.active_evidence(subject="user:test", clearance=Sensitivity.PRIVATE,
                                   observation_event_ids=invalid_pins)
        except DiscoveryOpportunityError:
            pass
        else:
            raise AssertionError("invalid pinned identities were admitted")
    synthesizer = OpportunitySynthesizer(journal, content_vault=reader.vault)
    calls = []

    def proposal(item_id: str) -> dict:
        return {"agenda_item_id": item_id, "kind": "share", "text": "PROPOSED_PRIVATE_BODY",
                "topic": "synthetic topic", "dimensions": {
                    name: {"value": .1 if name in {"risk", "interruption_cost"} else .8,
                           "reason": "fixture model judgment"}
                    for name in ("user_value", "urgency", "novelty", "confidence", "risk", "interruption_cost")}}

    async def interpret(**kwargs):
        calls.append(kwargs)
        assert kwargs["task"] == "alive_opportunity_candidates"
        assert "OTHER_OWNER_PRIVATE_TITLE" not in kwargs["messages"][1]["content"]
        assert "OWN_PRIVATE_TITLE" in kwargs["messages"][1]["content"]
        escalated = {**proposal(own.agenda_item_id), "authority": "system_critical"}
        invalid_dimension = proposal(own.agenda_item_id)
        invalid_dimension["dimensions"]["risk"]["value"] = True
        return response({"candidates": [proposal(own.agenda_item_id),
                                        proposal(other.agenda_item_id),
                                        escalated, invalid_dimension]})

    result = await synthesizer.run(subject="user:test", operation_id="default-authority", call=interpret)
    assert len(result.candidates) == 1 and result.rejected_count == 3
    assert result.candidates[0].action.authority is ActionAuthority.NONE
    assert result.actual_model == "provider/actual-interpreter"
    assert result.candidates[0].action.dimensions.user_value.basis is AssessmentBasis.MODEL_JUDGMENT
    assert result.receipt_event_id in result.candidates[0].action.dimensions.user_value.evidence_event_ids
    try:
        await synthesizer.run(subject="user:test", operation_id="default-authority", call=interpret)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError("same interpretation operation ran twice")
    assert len(calls) == 1

    delegated = await synthesizer.run(
        subject="user:test", operation_id="host-delegated-fixture", call=interpret,
        authority=ActionAuthority.USER_DELEGATED, requested_model="provider/requested-primary",
    )
    assert calls[-1]["model"] == "provider/requested-primary"
    coordinator = CognitionCycleCoordinator(journal, content_vault=reader.vault)

    async def choose(**kwargs):
        assert kwargs["task"] == "alive_deliberation"
        values = json.loads(kwargs["messages"][1]["content"].split("\n", 1)[1])
        candidate = next(item for item in values if item["action_kind"] == "share")
        return response({"candidate_id": candidate["candidate_id"], "rationale": "fixture choice"})

    choice = await coordinator.plan_with_model(
        cycle_id="generated-opportunity-cycle", subject="user:test",
        candidates=delegated.candidates, policy_context=PolicyContext(can_interrupt=True),
        causation_id=delegated.receipt_event_id, call=choose,
    )
    assert choice.selection.candidate.action_kind is ActionKind.SHARE
    assert journal.read(event_type="action.attempted") == []
    assert journal.read(event_type="dispatch.externally_started") == []

    cancelled_calls = 0

    async def cancelled(**_kwargs):
        nonlocal cancelled_calls
        cancelled_calls += 1
        raise asyncio.CancelledError()

    try:
        await synthesizer.run(subject="user:test", operation_id="cancelled", call=cancelled)
    except asyncio.CancelledError:
        pass
    try:
        await synthesizer.run(subject="user:test", operation_id="cancelled", call=cancelled)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError("cancelled operation spent again")
    assert cancelled_calls == 1

    async def provider_failed(**_kwargs):
        raise ConnectionError("PRIVATE_PROVIDER_ERROR_SENTINEL")

    try:
        await synthesizer.run(subject="user:test", operation_id="provider-failed", call=provider_failed)
    except OpportunitySynthesisError as exc:
        assert "PRIVATE_PROVIDER_ERROR_SENTINEL" not in str(exc)
        assert exc.__suppress_context__ is True
    else:
        raise AssertionError("provider failure became a generated proposal")

    async def erased(**_kwargs):
        reader.vault.erase_subject("user:test")
        return response({"candidates": [proposal(own.agenda_item_id)]})

    try:
        await synthesizer.run(subject="user:test", operation_id="erased", call=erased)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError("erased context produced candidates")
    assert journal.get("opportunity.synthesis:erased:completed") is None
    assert journal.get("opportunity.synthesis:erased:failed") is not None
    database = journal.path.read_bytes()
    wal = journal.path.with_name(journal.path.name + "-wal")
    if wal.exists():
        database += wal.read_bytes()
    for forbidden in (b"PROPOSED_PRIVATE_BODY", b"OWN_PRIVATE_TITLE", b"OWN_PRIVATE_SUMMARY",
                      b"OTHER_OWNER_PRIVATE_TITLE", b"fixture model judgment",
                      b"PRIVATE_PROVIDER_ERROR_SENTINEL"):
        assert forbidden not in database


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-opportunity-synthesis-") as directory:
        asyncio.run(exercise(Path(directory)))
    print("HERMES_ALIVE_KERNEL_OPPORTUNITY_SYNTHESIS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
