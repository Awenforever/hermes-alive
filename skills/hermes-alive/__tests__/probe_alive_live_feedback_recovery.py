#!/usr/bin/env python3
"""Explicit one-call recovery probe on a retained public synthetic experiment."""

import argparse
import asyncio
import hashlib
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.feedback_synthesis import FeedbackSynthesizer, FeedbackSynthesisError
from alive_kernel.feedback_recovery import FeedbackRecovery
from alive_kernel.outcomes import OutcomeProjection
from alive_kernel.semantic_comparator import SemanticComparator


async def exercise(args):
    logging.disable(logging.CRITICAL)
    from agent.auxiliary_client import async_call_llm
    import httpx
    prior = json.loads(args.prior_report.read_text(encoding="utf-8"))
    cases = [c for c in prior.get("cases", []) if c.get("case_id") == args.case_id]
    if (len(cases) != 1 or prior.get("sends") != 0 or prior.get("semantic_accuracy_proven") is not False
            or prior.get("automatic_learning_authority") is not False
            or not cases[0].get("interpretation_completed") or not cases[0].get("rejected_signal_count")
            or not cases[0].get("no_external_dispatch") or not cases[0].get("no_new_preference_signals")
            or not isinstance(cases[0].get("raw_response"), str)):
        raise ValueError("recovery probe requires a retained partial synthetic experiment")
    if not (args.journal_root / "kernel.sqlite3").is_file():
        raise ValueError("original fixture journal unavailable")
    journal = ExperienceJournal(args.journal_root / "kernel.sqlite3")
    interpreter = FeedbackSynthesizer(journal, content_vault=OutcomeProjection(journal).content_vault)
    recovery = FeedbackRecovery(interpreter)
    kwargs = dict(subject="user:synthetic-" + args.case_id, outcome_event_id="outcome.record:reply:fixture",
                  operation_id="prospective-feedback")
    context = recovery.context(**kwargs, clearance="private")
    evidence = context[2]["evidence"]
    parent = journal.get(context[0])
    if (evidence["delivered_text"] != cases[0]["sent"] or evidence["feedback_text"] != cases[0]["reply"]
            or interpreter.vault.digest_json(json.loads(cases[0]["raw_response"]))
                != parent.event.payload["content"]["digest"]):
        raise ValueError("report does not match retained original evidence")
    args.output.mkdir(exist_ok=False)
    report = {"logical_calls": 0, "observed_async_http": [], "sends": 0,
              "source_report_digest": hashlib.sha256(args.prior_report.read_bytes()).hexdigest(),
              "case_id": args.case_id, "evidence": evidence,
              "parent_findings": context[1], "semantic_accuracy_proven": False,
              "automatic_learning_authority": False}
    def save():
        temporary = args.output / "report.json.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(args.output / "report.json")
    original = httpx.AsyncClient.send
    async def send(client, request, *a, **kw):
        if len(report["observed_async_http"]) >= 4:
            raise RuntimeError("recovery transport budget exhausted")
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
        if report["logical_calls"] != 1:
            raise RuntimeError("recovery logical budget exhausted")
        result = await async_call_llm(**kw)
        text, model, provider = SemanticComparator._response(result, kw["route_info"])
        report.update(raw_response=text, actual_model=model, actual_provider=provider)
        return result
    before = tuple(journal.read(event_type="preference.observed"))
    httpx.AsyncClient.send = send
    try:
        save()
        receipt = await recovery.run(**kwargs, call=call, model=args.model)
        report.update(recovery_completed=True, recovered_signal_count=receipt.recovered_signal_count,
                      remaining_signal_count=receipt.remaining_signal_count,
                      findings=recovery.load_completed(**kwargs), receipt_event_id=receipt.event_id)
    except Exception as error:
        report["error_class"] = type(error).__name__
        if type(error) is FeedbackSynthesisError:
            report["validation_reason"] = str(error)
    finally:
        httpx.AsyncClient.send = original
        report["no_new_preference_signals"] = tuple(journal.read(event_type="preference.observed")) == before
        report["no_external_dispatch"] = not bool(journal.read(event_type="dispatch.externally_started"))
        save()
    print(json.dumps({"logical_calls": report["logical_calls"], "recovery_completed": report.get("recovery_completed", False),
                      "recovered": report.get("recovered_signal_count", 0), "sends": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live-models", action="store_true", required=True)
    parser.add_argument("--prior-report", type=Path, required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", help="An existing Hermes model selection only.")
    asyncio.run(exercise(parser.parse_args()))
