#!/usr/bin/env python3
"""Privacy and isolation contracts for Alive kernel shadow ingestion."""

from __future__ import annotations

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
            "message": {
                "message_id": "real-message-id",
                "content": "raw private message that must not persist",
                "authorization": "Bearer should-never-persist",
            },
            "api_key": "sk-should-never-persist",
        }
        observed = bridge.observe_hook("session:start", context)
        assert observed is not None and observed.created
        ignored = bridge.observe_hook("unsupported:event", context)
        assert ignored is None

        records = bridge.journal.read()
        assert len(records) == 1
        event = records[0].event
        assert event.event_type == "session.started"
        assert event.payload["platform"] == "weixin"
        assert event.payload["raw_content_stored"] is False
        identities = event.payload["identities"]
        assert identities["session_id"].startswith("session:")
        assert identities["session_id"] != "real-session-id"
        assert identities["chat_id"] != "real-chat-id"

        database_bytes = (Path(directory) / "kernel" / "experience.sqlite3").read_bytes()
        wal_path = Path(directory) / "kernel" / "experience.sqlite3-wal"
        if wal_path.exists():
            database_bytes += wal_path.read_bytes()
        forbidden = (
            b"raw private message",
            b"real-session-id",
            b"real-chat-id",
            b"real-message-id",
            b"should-never-persist",
        )
        assert not any(value in database_bytes for value in forbidden)

        first_identity = identities["session_id"]
        reopened = ShadowKernelBridge(directory)
        second = reopened.observe_hook("agent:end", context)
        assert second is not None
        second_identity = second.event.payload["identities"]["session_id"]
        assert first_identity == second_identity
        assert os.stat(Path(directory) / "kernel" / "identity.key").st_size == 32
        assert reopened.journal.verify_integrity() == 2

        canonical = "\n".join(record.event.canonical_json() for record in reopened.journal.read())
        json.loads(reopened.journal.read()[0].event.canonical_json())
        assert "authorization" not in canonical.lower()
        assert "api_key" not in canonical.lower()

    print("HERMES_ALIVE_KERNEL_SHADOW_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
