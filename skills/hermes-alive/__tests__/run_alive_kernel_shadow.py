#!/usr/bin/env python3
"""Privacy and isolation contracts for Alive kernel shadow ingestion."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import ShadowKernelBridge, shadow_enabled  # noqa: E402


def main() -> int:
    assert shadow_enabled({}) is False
    assert shadow_enabled({"HERMES_ALIVE_KERNEL_SHADOW_ENABLED": "true"}) is True

    with tempfile.TemporaryDirectory(prefix="alive-kernel-shadow-") as directory:
        bridge = ShadowKernelBridge(directory)
        context = {
            "platform": "weixin",
            "session_id": "real-session-id",
            "chat_id": "real-chat-id",
            "user_id": "real-user-id",
            "message_id": "real-message-id",
            "message": "raw private message that must not persist",
            "metadata": {"authorization": "Bearer should-never-persist"},
            "api_key": "sk-should-never-persist",
        }
        observed = bridge.observe_hook("session:start", context)
        assert observed is not None and observed.created
        ignored = bridge.observe_hook("unsupported:event", context)
        assert ignored is None

        duplicate_session = bridge.observe_hook("session:start", context)
        assert duplicate_session is not None and not duplicate_session.created

        inbound = bridge.observe_hook("agent:start", context)
        assert inbound is not None and inbound.created
        duplicate_inbound = bridge.observe_hook("agent:start", context)
        assert duplicate_inbound is not None and not duplicate_inbound.created
        assert duplicate_inbound.event.event_id == inbound.event.event_id

        step_context = {
            **context,
            "iteration": 1,
            "tool_names": ["web_search"],
            "tools": [{
                "name": "web_search",
                "arguments": {"query": "private query must not persist"},
                "result": "private tool result must not persist",
            }],
        }
        step = bridge.observe_hook("agent:step", step_context)
        assert step is not None and step.created
        duplicate_step = bridge.observe_hook("agent:step", step_context)
        assert duplicate_step is not None and not duplicate_step.created
        assert step.event.causation_id == inbound.event.event_id
        assert step.event.payload["tool_arguments_stored"] is False
        assert step.event.payload["tool_results_stored"] is False

        end_context = {
            **context,
            "response": "private assistant response must not persist",
            "model": "private/model-alias",
            "provider": "private-provider",
        }
        ended = bridge.observe_hook("agent:end", end_context)
        assert ended is not None and ended.created
        duplicate_end = bridge.observe_hook("agent:end", end_context)
        assert duplicate_end is not None and not duplicate_end.created
        assert ended.event.causation_id == inbound.event.event_id

        # The same user may legitimately repeat the exact text after the prior
        # turn closes; this must be a new turn, not a global content dedupe.
        repeated = bridge.observe_hook("agent:start", context)
        assert repeated is not None and repeated.created
        assert repeated.event.event_id != inbound.event.event_id

        records = bridge.journal.read()
        assert len(records) == 5
        event = records[0].event
        assert event.event_type == "session.started"
        assert event.payload["platform"] == "weixin"
        assert event.payload["raw_content_stored"] is False
        identities = event.payload["identities"]
        assert identities["session_id"].startswith("session:")
        assert identities["session_id"] != "real-session-id"
        assert identities["chat_id"] != "real-chat-id"
        assert event.subject == identities["user_id"]
        assert inbound.event.subject == identities["user_id"]
        assert inbound.event.actor == identities["user_id"]
        assert inbound.event.correlation_id == identities["session_id"]

        database_bytes = (Path(directory) / "kernel" / "experience.sqlite3").read_bytes()
        wal_path = Path(directory) / "kernel" / "experience.sqlite3-wal"
        if wal_path.exists():
            database_bytes += wal_path.read_bytes()
        forbidden = (
            b"raw private message",
            b"real-session-id",
            b"real-chat-id",
            b"real-message-id",
            b"real-user-id",
            b"should-never-persist",
            b"private query",
            b"private tool result",
            b"private assistant response",
            b"private/model-alias",
            b"private-provider",
        )
        assert not any(value in database_bytes for value in forbidden)

        first_identity = identities["session_id"]
        reopened = ShadowKernelBridge(directory)
        second = reopened.observe_hook("agent:end", context)
        assert second is not None
        second_identity = second.event.payload["identities"]["session_id"]
        assert first_identity == second_identity

        interrupted_start = reopened.observe_hook("agent:start", {
            **context, "message": "turn interrupted by gateway restart",
        })
        assert interrupted_start is not None and interrupted_start.created
        startup = reopened.observe_hook("gateway:startup", {"platforms": ["weixin"]})
        assert startup is not None and startup.created
        interruption = reopened.journal.read(
            event_type="session.turn_interrupted"
        )
        assert len(interruption) == 1
        assert interruption[0].event.causation_id == interrupted_start.event.event_id
        assert interruption[0].event.payload["reason"] == "gateway_restarted"
        orphaned_end = reopened.observe_hook("agent:end", {
            **context,
            "message": "turn interrupted by gateway restart",
            "response": "must not be linked across a restart",
        })
        assert orphaned_end is not None and orphaned_end.created
        assert orphaned_end.event.causation_id is None
        assert orphaned_end.event.payload["turn_link_status"] == "orphaned"

        superseded_context = {
            **context,
            "session_id": "superseded-session-id",
            "message": "first private in-flight turn",
        }
        superseded_start = reopened.observe_hook("agent:start", superseded_context)
        replacement_context = {
            **superseded_context, "message": "replacement private turn",
        }
        replacement_start = reopened.observe_hook("agent:start", replacement_context)
        assert superseded_start is not None and replacement_start is not None
        assert superseded_start.event.event_id != replacement_start.event.event_id
        superseded_events = [
            record for record in reopened.journal.read(
                event_type="session.turn_interrupted"
            )
            if record.event.causation_id == superseded_start.event.event_id
        ]
        assert len(superseded_events) == 1
        assert superseded_events[0].event.payload["reason"] == "superseded_by_new_turn"
        replacement_end = reopened.observe_hook("agent:end", replacement_context)
        assert replacement_end is not None and replacement_end.created
        assert replacement_end.event.causation_id == replacement_start.event.event_id

        concurrent_context = {
            **context,
            "session_id": "concurrent-session-id",
            "message": "concurrent private message must not persist",
        }
        with ThreadPoolExecutor(max_workers=12) as executor:
            concurrent = list(executor.map(
                lambda _index: reopened.observe_hook("agent:start", concurrent_context),
                range(24),
            ))
        assert all(result is not None for result in concurrent)
        concurrent_ids = {result.event.event_id for result in concurrent if result}
        assert len(concurrent_ids) == 1
        assert sum(bool(result and result.created) for result in concurrent) == 1
        concurrent_end = reopened.observe_hook("agent:end", concurrent_context)
        assert concurrent_end is not None and concurrent_end.created

        assert os.stat(Path(directory) / "kernel" / "identity.key").st_size == 32
        assert reopened.journal.verify_integrity() == 16

        canonical = "\n".join(record.event.canonical_json() for record in reopened.journal.read())
        json.loads(reopened.journal.read()[0].event.canonical_json())
        assert "authorization" not in canonical.lower()
        assert "api_key" not in canonical.lower()
        final_database_bytes = (
            Path(directory) / "kernel" / "experience.sqlite3"
        ).read_bytes()
        final_wal = Path(directory) / "kernel" / "experience.sqlite3-wal"
        if final_wal.exists():
            final_database_bytes += final_wal.read_bytes()
        assert b"turn interrupted by gateway restart" not in final_database_bytes
        assert b"must not be linked across a restart" not in final_database_bytes
        assert b"concurrent private message" not in final_database_bytes
        assert b"first private in-flight turn" not in final_database_bytes
        assert b"replacement private turn" not in final_database_bytes

    print("HERMES_ALIVE_KERNEL_SHADOW_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
