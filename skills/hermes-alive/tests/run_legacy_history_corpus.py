#!/usr/bin/env python3
"""Privacy and epistemic boundaries for structural historical observations."""

from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


def main():
    script = Path(__file__).resolve().parents[1] / "scripts" / "legacy-history-corpus.py"
    spec = importlib.util.spec_from_file_location("legacy_structural_export", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    private = "PRIVATE-CONTENT-do-not-export"
    raw = {"time": "2026-10-12T08:00:00+08:00", "started_at": "2026-10-12T07:00:00+08:00",
           "decision": "sent", "watcher_id": private, "tick_id": private, "model": private,
           "message_preview": private, "delivered_content": private, "reason": private,
           "message_hash": private, "configured_chat_hash": private,
           "semantic_plan": {"body": private}, "context_token_present": True,
           "session_busy_boolean": "false", "msg_count": True, "msg_index": 2,
           "latest_context_age_seconds": 10 ** 1000}
    clean = module.sanitize(raw, key=b"test-key", source_index=0, line_index=1)
    assert private not in json.dumps(clean)
    assert clean["observed_at"] == "2026-10-12T00:00:00+00:00"
    assert clean["reported_counts"]["msg_count"] is None
    assert clean["reported_counts"]["msg_index"] == 2
    assert clean["reported_flags"]["session_busy_boolean"] is None
    assert clean["reported_ages_seconds"]["latest_context_age_seconds"] is None
    assert clean["delivery_claim"] == "legacy_sent_report"
    assert all(value is None for value in clean["labels"].values())
    assert clean["tick_ref"] != clean["watcher_ref"]
    assert module.timestamp("2026-10-12T08:00:00") is None
    unknown = module.sanitize(dict(raw, decision=private, time="bad"), key=b"test-key",
                              source_index=0, line_index=2)
    assert unknown["decision_class"] == "other" and unknown["observed_at"] is None
    with tempfile.TemporaryDirectory(prefix="alive-legacy-corpus-") as directory:
        path = Path(directory) / "history.jsonl"
        path.write_text(json.dumps(raw) + "\n" + json.dumps(raw) + "\ninvalid\n[]\n", encoding="utf-8")
        before = path.read_bytes()
        first, second = module.export([path]), module.export([path])
        assert path.read_bytes() == before
        assert first["summary"]["records"] == 2 and first["summary"]["invalid_lines"] == 2
        assert first["records"][0]["tick_ref"] == first["records"][1]["tick_ref"]
        assert first["records"][0]["tick_ref"] != second["records"][0]["tick_ref"]
        assert first["sources"][0]["snapshot_ref"] != second["sources"][0]["snapshot_ref"]
        assert first["corpus_id"] != second["corpus_id"]
        assert private not in json.dumps(first)
        stat = path.stat()
        later = SimpleNamespace(st_size=stat.st_size + 1)
        with patch.object(module.os, "fstat", side_effect=[stat, later]):
            assert module.export([path])["sources"][0]["append_observed"] is True
        with patch.object(module.os, "fstat", side_effect=[stat, SimpleNamespace(st_size=0)]):
            try:
                module.export([path])
            except ValueError as error:
                assert "truncation" in str(error)
            else:
                raise AssertionError("concurrent source truncation was ignored")
        try:
            module.export([path, path])
        except ValueError as error:
            assert "duplicate" in str(error)
        else:
            raise AssertionError("a repeated input duplicated the historical cohort")
        try:
            module.export([path], max_bytes=1)
        except ValueError:
            pass
        else:
            raise AssertionError("oversized source was silently truncated")
        output = Path(directory) / "private-corpus.json"
        commands = []
        def remote(command, **kwargs):
            commands.append(command)
            assert "--output" not in command[-1]
            assert "/opt/data/history.jsonl" in command[-1]
            return subprocess.CompletedProcess(command, 0, json.dumps(first), "")
        args = [str(script), "--input", "/opt/data/history.jsonl", "--output", str(output),
                "--remote-ssh", "fixture-host", "--container", "fixture-container"]
        with patch.object(sys, "argv", args), patch.object(module.subprocess, "run", side_effect=remote), \
             redirect_stdout(io.StringIO()):
            module.main()
            try:
                module.main()
            except FileExistsError:
                pass
            else:
                raise AssertionError("existing corpus was overwritten")
        assert json.loads(output.read_text()) == first and len(commands) == 2
        failed_output = Path(directory) / "failed-corpus.json"
        args[args.index("--output") + 1] = str(failed_output)
        failed = subprocess.CompletedProcess(["ssh"], 1, private, private)
        with patch.object(sys, "argv", args), \
             patch.object(module.subprocess, "run", return_value=failed) as attempted:
            try:
                module.main()
            except RuntimeError as error:
                assert private not in str(error)
            else:
                raise AssertionError("failed remote export was treated as a corpus")
            assert attempted.call_count == 1
        assert not failed_output.exists(), "remote refusal wrote private failure output"
    print("HERMES_ALIVE_LEGACY_HISTORY_CORPUS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
