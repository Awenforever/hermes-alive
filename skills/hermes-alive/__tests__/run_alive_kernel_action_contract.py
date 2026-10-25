#!/usr/bin/env python3
"""Capability payloads are typed, bounded and cannot choose their route."""

from __future__ import annotations

from pathlib import Path
import sys

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import ActionContractError, parse_action_contract  # noqa: E402


def rejected(document: object, capability: str = "hermes.channel.send") -> None:
    try:
        parse_action_contract(document, capability=capability)
    except ActionContractError:
        return
    raise AssertionError("unsafe action contract was accepted")


def main() -> int:
    source = {
        "schema_version": 1,
        "capability": "hermes.channel.send",
        "operation": {"text": "A concise update.", "format": "markdown"},
    }
    first = parse_action_contract(source, capability="hermes.channel.send")
    second = parse_action_contract(
        {
            "operation": {"format": "markdown", "text": "A concise update."},
            "capability": "hermes.channel.send",
            "schema_version": 1,
        },
        capability="hermes.channel.send",
    )
    assert first.to_document() == second.to_document() == source

    # Content never chooses profile, channel, recipient, thread, or adapter.
    for forbidden in ("platform", "chat_id", "recipient", "thread_id", "profile"):
        injected = dict(source)
        injected[forbidden] = "attacker-selected-route"
        rejected(injected)
        nested = dict(source)
        nested["operation"] = {**source["operation"], forbidden: "route"}
        rejected(nested)

    rejected({**source, "schema_version": 2})
    rejected({**source, "schema_version": True})
    rejected({**source, "capability": "hermes.tool.execute"})
    rejected(source, capability="hermes.tool.execute")
    rejected({**source, "operation": {"text": "", "format": "plain"}})
    rejected({**source, "operation": {"text": "x" * 12_001, "format": "plain"}})
    rejected({**source, "operation": {"text": "hello", "format": "html"}})
    rejected({"message": "legacy untyped payload"})

    print("HERMES_ALIVE_KERNEL_ACTION_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
