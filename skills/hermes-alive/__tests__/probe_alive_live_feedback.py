#!/usr/bin/env python3
"""Bounded synthetic feedback interpretation through Hermes' configured models."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.content_vault import ContentVault
from alive_kernel.events import EventEnvelope, Sensitivity
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.feedback_synthesis import FeedbackSynthesizer, FeedbackSynthesisError
from alive_kernel.semantic_comparator import SemanticComparator
from alive_kernel.outcomes import OutcomeKind, OutcomeProjection
from alive_kernel.preference_learning import PreferenceDirection
from alive_kernel_testkit import authenticated_dispatch_receipt
from run_alive_kernel_learning_context import seed


def prepare_case(root, case, *, feedback_retention_days=29):
    """Create only synthetic fixture grants/receipts; no transport invocation."""
    if type(feedback_retention_days) is not int or not 1<=feedback_retention_days<=30:
        raise ValueError('synthetic feedback retention outside fixture consent')
    journal = ExperienceJournal(root / "kernel.sqlite3")
    subject = "user:synthetic-" + case["id"]
    seed(journal, subject, PreferenceDirection.SUPPORT, message_text=case["sent"])
    outcomes = OutcomeProjection(journal)
    retention = journal.append(EventEnvelope(event_id="retention.consent:fixture",
        event_type="retention.consent_changed", source="hermes.command.memory", actor=subject,
        subject=subject, sensitivity=Sensitivity.PRIVATE, payload={"enabled": True, "retention_days": 30,
        "directions": ["inbound"], "content_sensitivity": "private"}))
    journal.append(EventEnvelope(event_id="consolidation.consent:fixture",
        event_type="consolidation.consent_changed", source="hermes.command.memory", actor=subject,
        subject=subject, sensitivity=Sensitivity.PRIVATE, payload={"enabled": True}))
    attempt = journal.get("action.attempt:attempt:" + subject)
    receipt = authenticated_dispatch_receipt(journal, attempt, event_id="receipt:fixture")
    journal.append(receipt)
    delivered = outcomes.append_outcome(attempt_id="attempt:" + subject, kind=OutcomeKind.DELIVERY_SUCCEEDED,
        source_event_id=receipt.event_id, details={"synthetic": True}, actor="system:test", subject=subject,
        outcome_id="delivery:fixture")
    assert outcomes.apply(delivered).outcome == "recorded"
    content = outcomes.content_vault.put_json({"text": case["reply"], "direction": "inbound", "may_be_truncated": False},
        subject=subject, purpose="conversation.inbound", sensitivity=Sensitivity.PRIVATE,
        retention_until=datetime.now(timezone.utc) + timedelta(days=feedback_retention_days), content_id="input:fixture")
    incoming = journal.append(EventEnvelope(event_id="input:fixture", event_type="conversation.inbound",
        source="synthetic-public-fixture", actor=subject, subject=subject, sensitivity=Sensitivity.PRIVATE,
        causation_id=attempt.event.event_id, payload={"erasable_content_stored": True, "content_may_be_truncated": False,
        "consent_event_id": retention.event.event_id, "content": content.to_event_payload()}))
    feedback = outcomes.append_outcome(attempt_id="attempt:" + subject, kind=OutcomeKind.USER_REPLIED,
        source_event_id=incoming.event.event_id, details={"classification": "ordinary_reply", "synthetic": True},
        actor=subject, subject=subject, outcome_id="reply:fixture")
    assert outcomes.apply(feedback).outcome == "recorded"
    interpreter = FeedbackSynthesizer(journal, content_vault=outcomes.content_vault)
    snapshot, _ = interpreter.snapshot(subject=subject, outcome_event_id=feedback.event.event_id)
    assert snapshot["delivered_text"] == case["sent"] and snapshot["feedback_text"] == case["reply"]
    return interpreter, subject, feedback.event.event_id


async def exercise(args):
    logging.disable(logging.CRITICAL)
    from agent.auxiliary_client import async_call_llm
    import httpx
    document = json.loads(args.cases.read_text(encoding="utf-8"))
    if document.get("purpose") != "Prospective synthetic semantic qualification, not private user data or a literal keyword oracle.":
        raise ValueError("probe requires the explicit synthetic corpus")
    selected = [case for case in document["cases"] if case["id"] in args.case_id]
    if (not 1 <= len(selected) <= 3 or len(selected) != len(set(args.case_id))
            or any(not isinstance(case["sent"], str) or not isinstance(case["reply"], str) for case in selected)):
        raise ValueError("probe requires one to three distinct synthetic cases")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"logical_calls": 0, "observed_async_http": [], "sends": 0,
              "semantic_accuracy_proven": False, "automatic_learning_authority": False,
              "reference_status": document["reference_status"], "cases": []}
    def save():
        temporary = args.output / "report.json.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(args.output / "report.json")
    original = httpx.AsyncClient.send
    async def send(client, request, *a, **kw):
        if len(report["observed_async_http"]) >= 12:
            raise RuntimeError("feedback transport budget exhausted")
        item = {"host": request.url.host}
        report["observed_async_http"].append(item)
        try:
            response = await original(client, request, *a, **kw)
            item["status"] = response.status_code
            return response
        except BaseException as error:
            item["error_class"] = type(error).__name__
            raise
    async def call(**kw):
        report["logical_calls"] += 1
        if report["logical_calls"] > len(selected):
            raise RuntimeError("feedback logical budget exhausted")
        response = await async_call_llm(**kw)
        text, model, provider = SemanticComparator._response(response, kw["route_info"])
        # Inputs are explicitly synthetic. Keep returned text even when the
        # kernel rejects it; a parser error must not erase diagnostic evidence.
        report["cases"][-1].update(raw_response=text, actual_model=model, actual_provider=provider)
        return response
    httpx.AsyncClient.send = send
    try:
        for case in selected:
            root = args.output / case["id"]
            root.mkdir(exist_ok=False)
            item = {"case_id": case["id"], "sent": case["sent"], "reply": case["reply"],
                    "reference_constraints": case["constraints"], "structurally_completed": False}
            report["cases"].append(item)
            save()
            interpreter, subject, outcome_event_id = prepare_case(root, case)
            before = tuple(interpreter.journal.read(event_type="preference.observed"))
            try:
                receipt = await interpreter.run(subject=subject, outcome_event_id=outcome_event_id,
                    operation_id="prospective-feedback", model=args.model, call=call)
                findings = interpreter.load_completed(subject=subject, outcome_event_id=outcome_event_id,
                                                     operation_id="prospective-feedback")
                item.update(interpretation_completed=True, structurally_completed=not findings["rejected_signals"],
                            rejected_signal_count=len(findings["rejected_signals"]), receipt_event_id=receipt.event_id,
                            actual_model=receipt.actual_model, actual_provider=receipt.actual_provider,
                            findings=findings)
            except Exception as error:
                item["error_class"] = type(error).__name__
                if type(error) is FeedbackSynthesisError:
                    # These are the kernel's fixed validation reasons, not
                    # provider exceptions that might contain credential material.
                    item["validation_reason"] = str(error)
            item["no_new_preference_signals"] = tuple(interpreter.journal.read(event_type="preference.observed")) == before
            item["no_external_dispatch"] = not bool(interpreter.journal.read(event_type="dispatch.externally_started"))
            save()
    finally:
        httpx.AsyncClient.send = original
        save()
    print(json.dumps({"logical_calls": report["logical_calls"], "cases": len(report["cases"]),
        "completed": sum(item["structurally_completed"] for item in report["cases"]), "sends": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live-models", action="store_true", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--case-id", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", help="Optional existing Hermes model selection, never a new credential/configuration.")
    asyncio.run(exercise(parser.parse_args()))
