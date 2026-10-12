#!/usr/bin/env python3
"""Provider routing, parsing, privacy and review-only synthesis contracts."""

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
    ConsolidationSynthesisError,
    ConsolidationSynthesizer,
    MemoryProjection,
    MemoryState,
    ProjectionDecisionKind,
    Sensitivity,
    ShadowKernelBridge,
)
from alive_kernel.retention_command import handle_memory_command  # noqa: E402


def response(content: str, *, model: str = "provider/actual-model") -> SimpleNamespace:
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )


async def must_reject(awaitable) -> ConsolidationSynthesisError:
    try:
        await awaitable
    except ConsolidationSynthesisError as exc:
        return exc
    raise AssertionError("unsafe synthesis request was accepted")


async def exercise(shared: Path) -> None:
    bridge = ShadowKernelBridge(shared)
    subject = bridge.protector.pseudonym("user", "synthesis-user")
    synthesizer = ConsolidationSynthesizer(
        bridge.journal, content_vault=bridge.content_vault
    )
    calls: list[dict] = []

    async def forbidden_call(**kwargs):
        calls.append(kwargs)
        raise AssertionError("model route ran before consent and retained evidence")

    error = await must_reject(
        synthesizer.run(subject=subject, call=forbidden_call, operation_id="no-consent")
    )
    assert "not authorized" in str(error)
    assert calls == []

    handle_memory_command(
        shared, {"user_id": "synthesis-user", "args": "alive learn on"}
    )
    error = await must_reject(
        synthesizer.run(subject=subject, call=forbidden_call, operation_id="no-content")
    )
    assert "no authorized retained evidence" in str(error)
    assert calls == []

    handle_memory_command(
        shared,
        {
            "user_id": "synthesis-user",
            "args": "alive retain on 30 both",
        },
    )
    inbound = bridge.observe_hook(
        "agent:start",
        {
            "platform": "weixin",
            "user_id": "synthesis-user",
            "chat_id": "synthesis-chat",
            "session_id": "synthesis-session",
            "message": "RAW_EVIDENCE_SENTINEL I prefer concise but complete explanations.",
        },
    )
    outbound = bridge.observe_hook(
        "agent:end",
        {
            "platform": "weixin",
            "user_id": "synthesis-user",
            "chat_id": "synthesis-chat",
            "session_id": "synthesis-session",
            "response": "Acknowledged without changing any durable preference.",
        },
    )
    assert inbound is not None and outbound is not None

    attempts = 0
    routed: list[dict] = []

    async def routed_call(**kwargs):
        nonlocal attempts
        attempts += 1
        routed.append(kwargs)
        if attempts == 1:
            return response("RAW_MODEL_RESPONSE_SENTINEL not-json")
        evidence = json.loads(kwargs["messages"][1]["content"].split("\n", 1)[1])
        inbound_id = next(
            item["event_id"] for item in evidence if item["direction"] == "inbound"
        )
        valid = {
            "kind": "preference",
            "predicate": "communication.detail",
            "value": {"style": "concise-but-complete"},
            "evidence_event_ids": [inbound_id],
            "confidence": 0.91,
            "importance": 0.67,
            "ttl_days": 30,
        }
        document = {
            "candidates": [
                valid,
                {
                    **valid,
                    "kind": "commitment",
                    "predicate": "unsafe.promise",
                },
                {**valid, "evidence_event_ids": ["outside-window"]},
                valid,
            ]
        }
        return response(json.dumps(document, separators=(",", ":")))

    result = await synthesizer.run(
        subject=subject,
        call=routed_call,
        requested_model="provider/requested-model",
        operation_id="synthesis-success",
        attempts=2,
    )
    assert attempts == 2
    assert all(call["task"] == "alive_memory_consolidation" for call in routed)
    assert all(call["model"] == "provider/requested-model" for call in routed)
    assert "untrusted" in routed[0]["messages"][0]["content"].lower()
    assert "RAW_EVIDENCE_SENTINEL" in routed[0]["messages"][1]["content"]
    assert result.plan.actual_model == "provider/actual-model"
    assert len(result.plan.candidates) == 1
    assert {item.reason for item in result.plan.rejections} == {
        "candidate_contract_invalid",
        "candidate_evidence_outside_window",
        "candidate_duplicate",
    }
    assert len(result.decisions) == 1
    assert result.decisions[0].decision is ProjectionDecisionKind.PROPOSED
    assert result.proposal_failures == ()
    assert len(result.receipt_event_ids) == 2

    candidate = result.plan.candidates[0]
    memory = MemoryProjection(bridge.journal, content_vault=bridge.content_vault)
    stored = memory.get(candidate.candidate_id, clearance=Sensitivity.RESTRICTED)
    assert stored is not None and stored.state is MemoryState.PROPOSED
    assert stored.value == {"style": "concise-but-complete"}

    before = attempts
    error = await must_reject(
        synthesizer.run(
            subject=subject,
            call=routed_call,
            operation_id="synthesis-success",
        )
    )
    assert "already attempted" in str(error)
    assert attempts == before

    async def unattributed_call(**_kwargs):
        return response('{"candidates":[]}', model="")

    error = await must_reject(
        synthesizer.run(
            subject=subject,
            call=unattributed_call,
            operation_id="missing-attribution",
            attempts=1,
        )
    )
    assert "model attribution" in str(error)

    receipts = bridge.journal.read(event_type="consolidation.synthesis_completed")
    assert [record.event.payload["status"] for record in receipts] == [
        "rejected",
        "parsed",
        "rejected",
    ]
    assert receipts[0].event.payload["error_class"] == "ConsolidationSynthesisError"
    assert receipts[1].event.payload["actual_model"] == "provider/actual-model"
    assert all(record.event.payload["raw_prompt_stored"] is False for record in receipts)
    assert all(record.event.payload["raw_response_stored"] is False for record in receipts)

    database = (shared / "kernel" / "experience.sqlite3").read_bytes()
    wal = shared / "kernel" / "experience.sqlite3-wal"
    if wal.exists():
        database += wal.read_bytes()
    assert b"RAW_EVIDENCE_SENTINEL" not in database
    assert b"RAW_MODEL_RESPONSE_SENTINEL" not in database
    assert b"concise-but-complete" not in database

    cancelled_calls = 0

    async def cancelled_call(**_kwargs):
        nonlocal cancelled_calls
        cancelled_calls += 1
        raise asyncio.CancelledError()

    try:
        await synthesizer.run(subject=subject, call=cancelled_call,
                              operation_id="synthesis-cancelled")
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError("cancellation was consumed")
    await must_reject(synthesizer.run(
        subject=subject, call=cancelled_call, operation_id="synthesis-cancelled",
    ))
    assert cancelled_calls == 1

    concurrent_calls = 0

    async def concurrent_call(**_kwargs):
        nonlocal concurrent_calls
        concurrent_calls += 1
        await asyncio.sleep(0)
        return response('{"candidates":[]}')

    concurrent = await asyncio.gather(*(synthesizer.run(
        subject=subject, call=concurrent_call, operation_id="synthesis-concurrent",
    ) for _ in range(2)), return_exceptions=True)
    assert concurrent_calls == 1
    assert sum(isinstance(item, ConsolidationSynthesisError) for item in concurrent) == 1

    withdrawal_calls = 0

    async def withdrawn_during_call(**_kwargs):
        nonlocal withdrawal_calls
        withdrawal_calls += 1
        handle_memory_command(
            shared, {"user_id": "synthesis-user", "args": "alive learn off"}
        )
        return response("invalid response must not retry withdrawn private evidence")

    await must_reject(synthesizer.run(
        subject=subject, call=withdrawn_during_call,
        operation_id="consent-withdrawn-in-flight", attempts=2,
    ))
    assert withdrawal_calls == 1
    handle_memory_command(
        shared, {"user_id": "synthesis-user", "args": "alive learn on"}
    )

    erased_calls = 0

    async def erased_during_call(**_kwargs):
        nonlocal erased_calls
        erased_calls += 1
        bridge.content_vault.erase_subject(subject)
        return response('{"candidates":[]}')

    await must_reject(synthesizer.run(
        subject=subject, call=erased_during_call,
        operation_id="evidence-erased-in-flight", attempts=2,
    ))
    assert erased_calls == 1
    before = len(calls)
    error = await must_reject(
        synthesizer.run(subject=subject, call=forbidden_call, operation_id="erased")
    )
    assert "no authorized retained evidence" in str(error)
    assert len(calls) == before


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="alive-kernel-consolidation-synthesis-"
    ) as directory:
        asyncio.run(exercise(Path(directory)))
    print("HERMES_ALIVE_KERNEL_CONSOLIDATION_SYNTHESIS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
