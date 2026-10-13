#!/usr/bin/env python3
"""Synthetic one-shot recovery, original evidence and no-learning boundaries."""

import asyncio
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.content_vault import ContentErasedError
from alive_kernel.events import EventEnvelope, Sensitivity
from alive_kernel.feedback_recovery import FeedbackRecovery
from alive_kernel.feedback_synthesis import FeedbackSynthesisError
from probe_alive_live_feedback import prepare_case
from probe_alive_live_feedback_recovery import exercise as probe_recovery


CASE = {"id": "synthetic-recovery", "sent": "这里是公开活动信息。",
        "reply": "内容可以，不过以后先给我两句重点，详细资料放链接里。"}
SIGNAL = {"axis": "presentation", "key": "informational updates", "option": "brief introduction",
          "direction": "support", "scope": "durable", "quote": "以后先给我两句重点",
          "hypothesis": "可能希望此类消息先给简短重点。", "uncertainties": ["适用范围不明确。"]}


def response(kw, value):
    kw["route_info"]["provider"] = "synthetic-provider"
    return SimpleNamespace(model="synthetic/recoverer", choices=[
        SimpleNamespace(message=SimpleNamespace(content=json.dumps(value, ensure_ascii=False)))])


async def reject(awaitable, expected=FeedbackSynthesisError):
    try:
        await awaitable
    except expected:
        return
    raise AssertionError("unsafe recovery accepted")


async def fixture(root, operation="initial"):
    interpreter, subject, outcome = prepare_case(root, CASE)
    incomplete = {k: v for k, v in SIGNAL.items() if k != "uncertainties"}
    original = {"summary": "内容可接受，表达需要简明。", "signals": [incomplete, SIGNAL], "unresolved": ["范围不明确。"]}
    async def initial(**kw):
        return response(kw, original)
    receipt = await interpreter.run(subject=subject, outcome_event_id=outcome,
                                    operation_id=operation, call=initial)
    assert receipt.accepted_signal_count == 1 and receipt.rejected_signal_count == 1
    return FeedbackRecovery(interpreter), dict(subject=subject, outcome_event_id=outcome, operation_id=operation)


async def exercise(root):
    recovery, args = await fixture(root / "success")
    before = tuple(recovery.journal.read(event_type="preference.observed"))
    calls = []
    async def fix(**kw):
        calls.append(kw)
        data = json.loads(kw["messages"][1]["content"])
        assert data["accepted_units"] == [SIGNAL]
        assert [item["index"] for item in data["quarantined_units"]] == [0]
        return response(kw, {"replacements": [{"index": 0, "signal": SIGNAL, "reason": "补全有根据的范围限制。"}]})
    receipt = await recovery.run(**args, call=fix)
    assert receipt.recovered_signal_count == 1 and receipt.remaining_signal_count == 0
    assert not receipt.safe_for_automatic_learning
    loaded = recovery.load_completed(**args)
    assert loaded["parent_findings"]["signals"] == [SIGNAL]
    assert loaded["parent_findings"]["rejected_signals"]  # History is not overwritten.
    assert loaded["recovered_signals"][0]["index"] == 0
    assert loaded["automatic_learning_authority"] is False
    assert tuple(recovery.journal.read(event_type="preference.observed")) == before
    assert not recovery.journal.read(event_type="dispatch.externally_started")
    assert SIGNAL["quote"] not in recovery.journal.get(receipt.event_id).event.canonical_json()
    await reject(recovery.run(**args, call=fix))
    get = recovery.journal.get
    prefix = recovery.prefix(args["subject"], receipt.parent_event_id)
    def stale_read(event_id):
        return None if event_id == prefix + ":started" else get(event_id)
    with patch.object(recovery.journal, "get", stale_read):
        await reject(recovery.run(**args, call=fix))
    await reject(recovery.run(**{**args, "subject": "user:other"}, call=fix))
    assert len(calls) == 1
    context = recovery.context(**args, clearance=Sensitivity.PRIVATE)
    minimal = recovery.interpret(json.dumps({"replacements": [{"index": 0, "signal": SIGNAL}]}), context)
    assert minimal["recovered_signals"] == [{"index": 0, "signal": SIGNAL}]
    for document in [
        {"replacements": []},
        {"replacements": [{"index": 0, "signal": None}]},
        {"replacements": [{"index": 0, "signal": SIGNAL, "reason": 42}]},
        {"replacements": [{"index": 1, "signal": SIGNAL, "reason": "rewrite accepted"}]},
        {"replacements": [{"index": True, "signal": SIGNAL, "reason": "bool index"}]},
        {"replacements": [{"index": 0, "signal": SIGNAL, "reason": "a"},
                          {"index": 0, "signal": SIGNAL, "reason": "b"}]},
    ]:
        try:
            recovery.interpret(json.dumps(document), context)
        except FeedbackSynthesisError:
            pass
        else:
            raise AssertionError("recovery expanded or rewrote original targets")
    source = recovery.journal.get(context[2]["evidence"]["source_event_id"])
    recovery.vault.erase_item(source.event.payload["content"]["content_id"])
    try:
        recovery.load_completed(**args)
    except ContentErasedError:
        pass
    else:
        raise AssertionError("erased evidence still supports recovered interpretation")

    for name in ("abstain", "unsupported", "malformed", "revoke", "erase", "cancel", "provider-failure"):
        component, params = await fixture(root / name)
        async def attempt(**kw):
            if name == "revoke":
                component.journal.append(EventEnvelope(event_id="owner:withdraw", event_type="consolidation.consent_changed",
                    source="hermes.command.memory", actor=params["subject"], subject=params["subject"],
                    sensitivity=Sensitivity.PRIVATE, payload={"enabled": False}))
            if name == "cancel":
                raise asyncio.CancelledError()
            if name == "erase":
                evidence = component.context(**params, clearance=Sensitivity.PRIVATE)[2]["evidence"]
                component.vault.erase_item(evidence["feedback_content_id"])
            if name == "provider-failure":
                raise RuntimeError("synthetic-secret-not-for-journal")
            signal = None if name == "abstain" else dict(SIGNAL)
            if name == "unsupported":
                signal["quote"] = CASE["sent"]
            if name == "malformed":
                del signal["uncertainties"]
            return response(kw, {"replacements": [{"index": 0, "signal": signal, "reason": "模型的有界判断。"}]})
        if name in ("revoke", "erase", "cancel", "provider-failure"):
            expected = (asyncio.CancelledError if name == "cancel" else RuntimeError if name == "provider-failure"
                        else ContentErasedError if name == "erase" else FeedbackSynthesisError)
            await reject(component.run(**params, call=attempt), expected)
            assert len(component.journal.read(event_type="feedback.recovery_failed")) == 1
            assert not component.journal.read(event_type="feedback.recovery_completed")
            assert "synthetic-secret-not-for-journal" not in str(component.journal.read(event_type="feedback.recovery_failed"))
        else:
            result = await component.run(**params, call=attempt)
            assert result.recovered_signal_count == 0 and result.remaining_signal_count == 1
            resolved = component.load_completed(**params)
            assert resolved["parent_findings"]["signals"] == [SIGNAL]
            status = "abstained" if name == "abstain" else "rejected"
            assert resolved["remaining_signals"][0]["status"] == status
        await reject(component.run(**params, call=attempt), ContentErasedError if name == "erase" else FeedbackSynthesisError)

    racing, params = await fixture(root / "concurrent")
    launched = []
    gate = asyncio.Event()
    async def waiting(**kw):
        launched.append(True)
        await gate.wait()
        return response(kw, {"replacements": [{"index": 0, "signal": SIGNAL, "reason": "范围有限。"}]})
    first = asyncio.create_task(racing.run(**params, call=waiting))
    await asyncio.sleep(0)
    await reject(racing.run(**params, call=waiting))
    gate.set()
    await first
    assert len(launched) == 1

    probe, params = await fixture(root / "probe", operation="prospective-feedback")
    context = probe.context(**params, clearance=Sensitivity.PRIVATE)
    parent = probe.journal.get(context[0])
    raw = probe.vault.resolve_json(parent.event.payload["content"]["content_id"], expected_subject=params["subject"],
        expected_purpose="feedback.interpretation", expected_sensitivity=Sensitivity.PRIVATE)
    old_findings = json.loads(json.dumps(context[1]))
    old_findings["rejected_signals"][0]["reason"] = "historical diagnostic wording"
    prior = {"sends": 0, "semantic_accuracy_proven": False, "automatic_learning_authority": False,
        "cases": [{"case_id": CASE["id"], "sent": CASE["sent"], "reply": CASE["reply"],
                   "interpretation_completed": True, "rejected_signal_count": 1,
                   "no_external_dispatch": True, "no_new_preference_signals": True,
                   "raw_response": json.dumps(raw), "findings": old_findings}]}
    path = root / "prior.json"
    path.write_text(json.dumps(prior), encoding="utf-8")
    package = ModuleType("agent")
    package.__path__ = []
    auxiliary = ModuleType("agent.auxiliary_client")
    async def fake(**kw):
        return response(kw, {"replacements": [{"index": 0, "signal": SIGNAL}]})
    async def forbidden(*a, **kw):
        raise AssertionError("recovery regression attempted external HTTP")
    auxiliary.async_call_llm = fake
    old_logging = logging.root.manager.disable
    try:
        with patch.dict(sys.modules, {"agent": package, "agent.auxiliary_client": auxiliary}), \
             patch.object(httpx.AsyncClient, "send", forbidden):
            await probe_recovery(SimpleNamespace(prior_report=path, case_id=CASE["id"],
                journal_root=root / "probe", output=root / "probe-report", model=None))
    finally:
        logging.disable(old_logging)
    report = json.loads((root / "probe-report/report.json").read_text(encoding="utf-8"))
    assert report["logical_calls"] == 1 and report["observed_async_http"] == []
    assert report["recovery_completed"] and report["recovered_signal_count"] == 1
    assert report["no_new_preference_signals"] and report["no_external_dispatch"]


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="alive-feedback-recovery-") as folder:
        asyncio.run(exercise(Path(folder)))
    print("HERMES_ALIVE_KERNEL_FEEDBACK_RECOVERY_OK")
