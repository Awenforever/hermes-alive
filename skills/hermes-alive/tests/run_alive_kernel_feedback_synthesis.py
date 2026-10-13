#!/usr/bin/env python3
"""Synthetic delivery-linked feedback semantics boundary, no real user benefit claim."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.content_vault import ContentErasedError
from alive_kernel.events import EventEnvelope, Sensitivity
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.feedback_synthesis import FeedbackSynthesizer, FeedbackSynthesisError
from alive_kernel.outcomes import OutcomeKind, OutcomeProjection
from alive_kernel.preference_learning import PreferenceDirection
from alive_kernel_testkit import authenticated_dispatch_receipt
from run_alive_kernel_learning_context import seed


async def rejected(awaitable, expected=FeedbackSynthesisError):
    try:
        await awaitable
    except expected:
        return
    raise AssertionError("unsafe feedback operation accepted")


async def exercise(root):
    journal = ExperienceJournal(root / "kernel.sqlite3")
    subject = "user:synthetic-feedback"
    seed(journal, subject, PreferenceDirection.SUPPORT)
    outcomes = OutcomeProjection(journal)
    interpreter = FeedbackSynthesizer(journal, content_vault=outcomes.content_vault)
    calls = []
    async def forbidden(**kw):
        calls.append(kw)
        raise AssertionError("model called without complete consented evidence")
    await rejected(interpreter.run(subject=subject, outcome_event_id="outcome.record:feedback:" + subject,
                                  operation_id="no-consent", call=forbidden))
    assert not calls
    retention = journal.append(EventEnvelope(event_id="retention.consent:feedback-fixture",
        event_type="retention.consent_changed", source="hermes.command.memory", actor=subject, subject=subject,
        sensitivity=Sensitivity.PRIVATE,
        payload={"enabled": True, "retention_days": 30, "directions": ["inbound"], "content_sensitivity": "private"}))
    journal.append(EventEnvelope(event_id="consolidation.consent:feedback-fixture",
        event_type="consolidation.consent_changed", source="hermes.command.memory", actor=subject, subject=subject,
        sensitivity=Sensitivity.PRIVATE,
        payload={"enabled": True}))
    attempt = journal.get("action.attempt:attempt:" + subject)
    text = "这类城市新闻挺有意思的，以后继续分享；只是今天在开会，别在这时候发。"
    def feedback(name, *, truncated=False):
        ref = outcomes.content_vault.put_json({"text": text, "may_be_truncated": truncated, "direction": "inbound"},
            subject=subject, purpose="conversation.inbound", sensitivity=Sensitivity.PRIVATE,
            retention_until=datetime.now(timezone.utc) + timedelta(days=29), content_id="raw-feedback:" + name)
        source = journal.append(EventEnvelope(event_id="inbound:" + name, event_type="conversation.inbound",
            source="synthetic-public-fixture", actor=subject, subject=subject, causation_id=attempt.event.event_id,
            sensitivity=Sensitivity.PRIVATE,
            payload={"erasable_content_stored": True, "content_may_be_truncated": truncated,
                     "consent_event_id": retention.event.event_id, "content": ref.to_event_payload()}))
        record = outcomes.append_outcome(attempt_id="attempt:" + subject, kind=OutcomeKind.USER_REPLIED,
            source_event_id=source.event.event_id, details={"classification": "ordinary_reply"},
            actor=subject, subject=subject, outcome_id=name)
        assert outcomes.apply(record).outcome == "recorded"
        return record, ref
    undelivered, _ = feedback("before-delivery")
    await rejected(interpreter.run(subject=subject, outcome_event_id=undelivered.event.event_id,
                                  operation_id="no-delivery", call=forbidden))
    receipt = authenticated_dispatch_receipt(journal, attempt, event_id="receipt:feedback-fixture")
    journal.append(receipt)
    delivered = outcomes.append_outcome(attempt_id="attempt:" + subject, kind=OutcomeKind.DELIVERY_SUCCEEDED,
        source_event_id=receipt.event_id, details={}, actor="system:test", subject=subject, outcome_id="delivery:feedback-fixture")
    assert outcomes.apply(delivered).outcome == "recorded"
    # A later receipt cannot retroactively establish the target of an earlier reply.
    await rejected(interpreter.run(subject=subject, outcome_event_id=undelivered.event.event_id,
                                  operation_id="future-delivery", call=forbidden))
    truncated, _ = feedback("truncated", truncated=True)
    await rejected(interpreter.run(subject=subject, outcome_event_id=truncated.event.event_id,
                                  operation_id="truncated", call=forbidden))
    assert not calls
    valid, reference = feedback("valid")
    snapshot, _ = interpreter.snapshot(subject=subject, outcome_event_id=valid.event.event_id)
    assert snapshot["delivered_text"] == "synthetic prior message"
    assert snapshot["feedback_text"] == text
    findings = {"summary": "主题有兴趣，但当次时机不合适。", "signals": [
        {"axis": "topic", "key": "news", "option": "city news", "direction": "support", "scope": "durable",
         "quote": "这类城市新闻挺有意思的，以后继续分享", "hypothesis": "可能欢迎继续分享此类内容。",
         "uncertainties": ["频率未明确。"]},
        {"axis": "interruption", "key": "meeting", "option": "during a meeting", "direction": "oppose", "scope": "situational",
         "quote": "今天在开会，别在这时候发", "hypothesis": "这次会议中不适合打扰。",
         "uncertainties": ["不能由此推断所有工作时间都禁止消息。"]}], "unresolved": []}
    async def generate(**kw):
        calls.append(kw)
        assert kw["model"] is None
        supplied = json.loads(kw["messages"][1]["content"])
        assert supplied == snapshot
        kw["route_info"]["provider"] = "synthetic-provider"
        return SimpleNamespace(model="synthetic/feedback-interpreter",
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(findings, ensure_ascii=False)))])
    prior_signals = tuple(journal.read(event_type="preference.observed"))
    result = await interpreter.run(subject=subject, outcome_event_id=valid.event.event_id, operation_id="mixed", call=generate)
    assert not result.safe_for_automatic_learning
    assert interpreter.load_completed(subject=subject, outcome_event_id=valid.event.event_id, operation_id="mixed") == {
        **findings, "rejected_signals": []}
    assert tuple(journal.read(event_type="preference.observed")) == prior_signals
    assert not journal.read(event_type="reflection.proposed")
    assert text not in journal.get(result.event_id).event.canonical_json()
    await rejected(interpreter.run(subject=subject, outcome_event_id=valid.event.event_id, operation_id="mixed", call=generate))
    assert len(calls) == 1
    # Exact quotations establish provenance, not correct semantic interpretation.
    wrong = json.loads(json.dumps(findings))
    wrong["signals"][1].update(axis="topic", scope="durable", option="all news",
                              hypothesis="用户永远讨厌全部新闻。")
    assert interpreter.findings(json.dumps(wrong), snapshot) == {**wrong, "rejected_signals": []}
    assert not result.safe_for_automatic_learning
    fabricated = json.loads(json.dumps(findings))
    fabricated["signals"][0]["quote"] = "I dislike all news"
    partial = interpreter.findings(json.dumps(fabricated), snapshot)
    assert partial["signals"] == [findings["signals"][1]]
    assert partial["rejected_signals"] == [{"index": 0, "reason": "feedback hypothesis lacks bounded original evidence"}]
    source_swap = json.loads(json.dumps(findings))
    source_swap["signals"][0]["quote"] = snapshot["delivered_text"]
    assert interpreter.findings(json.dumps(source_swap), snapshot)["rejected_signals"][0]["index"] == 0
    malformed = {**findings, "signals": [42, *findings["signals"]]}
    isolated = interpreter.findings(json.dumps(malformed), snapshot)
    assert isolated["signals"] == findings["signals"] and isolated["rejected_signals"][0]["index"] == 0
    assert isolated["rejected_signals"][0]["reason"] == "feedback hypothesis violates bounded signal protocol"
    omitted = json.loads(json.dumps(findings))
    del omitted["signals"][0]["uncertainties"]
    diagnosed = interpreter.findings(json.dumps(omitted), snapshot)
    assert diagnosed["signals"] == [findings["signals"][1]]
    assert diagnosed["rejected_signals"] == [{"index": 0, "reason": "feedback hypothesis violates bounded signal protocol"}]
    async def partial_generate(**kw):
        kw["route_info"]["provider"] = "synthetic-provider"
        return SimpleNamespace(model="synthetic/feedback-interpreter",
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(fabricated)))])
    partial_receipt = await interpreter.run(subject=subject, outcome_event_id=valid.event.event_id,
                                           operation_id="partial", call=partial_generate)
    assert partial_receipt.accepted_signal_count == 1 and partial_receipt.rejected_signal_count == 1
    assert not partial_receipt.all_signals_structurally_valid and not partial_receipt.safe_for_automatic_learning
    assert interpreter.load_completed(subject=subject, outcome_event_id=valid.event.event_id, operation_id="partial") == partial
    assert tuple(journal.read(event_type="preference.observed")) == prior_signals
    outcomes.content_vault.erase_item(reference.content_id)
    try:
        interpreter.load_completed(subject=subject, outcome_event_id=valid.event.event_id, operation_id="mixed")
    except ContentErasedError:
        pass
    else:
        raise AssertionError("forgotten input still supported a retained interpretation")
    changed, _ = feedback("changed-consent")
    async def revoke(**kw):
        journal.append(EventEnvelope(event_id="consolidation.consent:withdraw-feedback-fixture",
            event_type="consolidation.consent_changed", source="hermes.command.memory", actor=subject,
            subject=subject, payload={"enabled": False}))
        kw["route_info"]["provider"] = "synthetic-provider"
        return SimpleNamespace(model="synthetic/feedback-interpreter",
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(findings)))])
    await rejected(interpreter.run(subject=subject, outcome_event_id=changed.event.event_id,
                                  operation_id="consent-changed", call=revoke))
    assert len(journal.read(event_type="feedback.synthesis_failed")) == 1
    assert len(journal.read(event_type="feedback.synthesis_completed")) == 2
    assert not journal.read(event_type="dispatch.externally_started")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="alive-feedback-synthesis-") as folder:
        asyncio.run(exercise(Path(folder)))
    print("HERMES_ALIVE_KERNEL_FEEDBACK_SYNTHESIS_OK")
