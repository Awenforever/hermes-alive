#!/usr/bin/env python3
"""Opt-in upstream CLI characterization; injected results, never real sends."""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path


def characterize(root: Path) -> dict:
    cli_path = root / "hermes_cli" / "send_cmd.py"
    tool_path = root / "tools" / "send_message_tool.py"
    source = tool_path.read_text(encoding="utf-8")
    # This declaration does not replace a loaded-registry probe.
    assert "intentionally NOT registered as an agent-callable model tool" in source
    spec = importlib.util.spec_from_file_location("alive_upstream_send_contract", cli_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = [
        ("reported_success", {"success": True, "message_id": "synthetic-id"}, 0),
        ("duplicate_skipped", {"success": True, "skipped": True,
                               "reason": "cron_auto_delivery_duplicate_target"}, 0),
        ("skipped_without_success", {"skipped": True}, 0),
        ("partial_effect", {"success": False, "partial_success": True,
                            "error": "synthetic attachment failure"}, 1),
        ("error_overrides_success", {"success": True, "error": "synthetic failure"}, 1),
        ("empty", {}, 1),
        ("non_boolean_success", {"success": "not a boolean"}, 0),
    ]
    results = []
    for name, payload, expected in cases:
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = module._emit_result(json.dumps(payload), json_mode=True, quiet=False)
        assert code == expected, (name, code, expected)
        assert json.loads(output.getvalue()) == payload, name
        results.append({"case": name, "exit_code": code,
                        "injected_payload": True, "external_delivery_proven": False})
    return {
        "source_sha256": {str(p.relative_to(root)).replace("\\", "/"):
                          hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (cli_path, tool_path)},
        "registration_evidence": "source declaration only; runtime registry not probed",
        "cases": results, "real_sends": 0, "production_mutations": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-root", type=Path)
    args = parser.parse_args()
    if args.hermes_root is None:
        print("SKIP host transport source contract: explicit upstream snapshot required")
        return
    print(json.dumps(characterize(args.hermes_root.resolve()), sort_keys=True))
    print("HERMES_ALIVE_HOST_TRANSPORT_SOURCE_CONTRACT_OK")


if __name__ == "__main__":
    main()
