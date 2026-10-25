#!/usr/bin/env python3
"""Rejected synthetic model output remains diagnosable; provider secrets do not."""
import asyncio
import json
import logging
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx
from probe_alive_live_feedback import exercise


async def check(root):
    document = {"purpose": "Prospective synthetic semantic qualification, not private user data or a literal keyword oracle.",
                "reference_status": "Synthetic test only", "cases": [
                    {"id": name, "sent": "公开合成示例。", "reply": "谢谢，收到。", "constraints": []}
                    for name in ("bad-quote", "provider-failure")]}
    path = root / "cases.json"
    path.write_text(json.dumps(document))
    counter = 0
    raw = json.dumps({"summary": "A synthetic deliberately invalid interpretation", "signals": [
        {"axis": "topic", "key": "ads", "option": "all ads", "direction": "support", "scope": "durable",
         "quote": "fabricated quote", "hypothesis": "Not supported", "uncertainties": []}], "unresolved": []})
    async def fake(**kw):
        nonlocal counter
        counter += 1
        if counter == 2:
            raise RuntimeError("synthetic-secret-that-must-not-enter-report")
        kw["route_info"]["provider"] = "synthetic-provider"
        return SimpleNamespace(model="synthetic/probe", choices=[SimpleNamespace(message=SimpleNamespace(content=raw))])
    async def forbidden(*a, **kw):
        raise AssertionError("unit fixture made a network request")
    package = ModuleType("agent")
    package.__path__ = []
    auxiliary = ModuleType("agent.auxiliary_client")
    auxiliary.async_call_llm = fake
    old_logging = logging.root.manager.disable
    try:
        with patch.dict(sys.modules, {"agent": package, "agent.auxiliary_client": auxiliary}), \
             patch.object(httpx.AsyncClient, "send", forbidden):
            await exercise(SimpleNamespace(cases=path, case_id=["bad-quote", "provider-failure"],
                                           output=root / "output", model=None))
    finally:
        logging.disable(old_logging)
    report_text = (root / "output/report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert report["logical_calls"] == 2 and report["observed_async_http"] == []
    assert report["cases"][0]["raw_response"] == raw
    assert report["cases"][0]["rejected_signal_count"] == 1
    assert report["cases"][0]["interpretation_completed"] is True
    assert report["cases"][0]["findings"]["signals"] == []
    assert report["cases"][0]["actual_model"] == "synthetic/probe"
    assert report["cases"][1]["error_class"] == "RuntimeError"
    assert "synthetic-secret-that-must-not-enter-report" not in report_text
    assert all(not case["structurally_completed"] and case["no_external_dispatch"]
               and case["no_new_preference_signals"] for case in report["cases"])
    assert report["automatic_learning_authority"] is False


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="alive-feedback-observability-") as folder:
        asyncio.run(check(Path(folder)))
    print("HERMES_ALIVE_KERNEL_FEEDBACK_PROBE_OK")
