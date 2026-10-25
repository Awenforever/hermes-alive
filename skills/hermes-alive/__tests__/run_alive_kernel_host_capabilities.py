#!/usr/bin/env python3
"""Host facts and user routes are authenticated, private and fail closed."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    EventEnvelope,
    ExperienceJournal,
    HostCapabilityError,
    HostCapabilityProjection,
    ReceiptLevel,
)
from alive_kernel.event_store import JournalRecord  # noqa: E402


def claim(receipt: ReceiptLevel, *, public: bool = True) -> dict[str, object]:
    return {
        "interface": "plugin_context.channel_send",
        "available": True,
        "public_api": public,
        "receipt_level": receipt.value,
    }


def authority(binding_id: str, at: datetime) -> EventEnvelope:
    return EventEnvelope(
        event_id=f"authority:{binding_id}",
        event_type="conversation.inbound",
        source="test.channel",
        actor="user:test",
        subject="user:test",
        occurred_at=at,
        observed_at=at,
        payload={"authorizes_route_binding_id": binding_id},
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-host-capabilities-") as directory:
        root = Path(directory)
        journal = ExperienceJournal(root / "kernel.sqlite3")
        host = HostCapabilityProjection(journal)
        now = datetime.now(timezone.utc)

        accepted_only = host.observe_snapshot(
            snapshot_id="hermes-v0216-request-only",
            hermes_version="0.21.6",
            plugin_api_version=1,
            capabilities={
                "hermes.channel.send": claim(ReceiptLevel.REQUEST_ACCEPTED),
            },
            observed_at=now,
        )
        journal.append(authority("home-route", now))
        binding = host.bind_route(
            binding_id="home-route",
            subject="user:test",
            capability="hermes.channel.send",
            snapshot_event_id=accepted_only.event_id,
            route={
                "platform": "weixin",
                "profile": "default",
                "chat_id": "PRIVATE_CHAT_SENTINEL",
            },
            authority_event_id="authority:home-route",
            observed_at=now + timedelta(seconds=1),
        )
        assert binding.active
        assert binding.route_fingerprint != "PRIVATE_CHAT_SENTINEL"
        journal_bytes = (root / "kernel.sqlite3").read_bytes()
        assert b"PRIVATE_CHAT_SENTINEL" not in journal_bytes
        assert b"PRIVATE_CHAT_SENTINEL" not in (
            root / "content-vault" / "content.sqlite3"
        ).read_bytes()

        executable, reasons = host.execution_binding(
            "home-route",
            subject="user:test",
            capability="hermes.channel.send",
            as_of=now + timedelta(seconds=2),
        )
        assert executable is None
        assert reasons == ("host_terminal_receipt_unavailable",)

        delivered = host.observe_snapshot(
            snapshot_id="hermes-public-terminal",
            hermes_version="0.21.6",
            plugin_api_version=2,
            capabilities={
                "hermes.channel.send": claim(ReceiptLevel.EXTERNAL_DELIVERED),
            },
            observed_at=now + timedelta(seconds=3),
        )
        # A host upgrade invalidates routes bound to a previous contract.
        executable, reasons = host.execution_binding(
            "home-route",
            subject="user:test",
            capability="hermes.channel.send",
            as_of=now + timedelta(seconds=4),
        )
        assert executable is None
        assert reasons == ("host_capability_snapshot_stale",)

        journal.append(authority("terminal-route", now + timedelta(seconds=4)))
        terminal = host.bind_route(
            binding_id="terminal-route",
            subject="user:test",
            capability="hermes.channel.send",
            snapshot_event_id=delivered.event_id,
            route={
                "platform": "feishu",
                "profile": "research",
                "chat_id": "ou_private",
                "thread_id": "thread_private",
            },
            authority_event_id="authority:terminal-route",
            observed_at=now + timedelta(seconds=5),
        )
        executable, reasons = host.execution_binding(
            terminal.binding_id,
            subject="user:test",
            capability="hermes.channel.send",
            as_of=now + timedelta(seconds=6),
        )
        assert executable == terminal and reasons == ()
        assert host.resolve_route(terminal) == {
            "chat_id": "ou_private",
            "platform": "feishu",
            "profile": "research",
            "thread_id": "thread_private",
        }

        host.revoke_route("terminal-route", observed_at=now + timedelta(seconds=7))
        executable, reasons = host.execution_binding(
            "terminal-route",
            subject="user:test",
            capability="hermes.channel.send",
            as_of=now + timedelta(seconds=8),
        )
        assert executable is None and "route_binding_revoked" in reasons

        # An unauthenticated host assertion cannot silently widen authority.
        forged = EventEnvelope(
            event_id="host.capabilities:forged",
            event_type="host.capabilities_observed",
            source="attacker",
            actor="system:hermes-host",
            occurred_at=now + timedelta(seconds=8),
            observed_at=now + timedelta(seconds=8),
            payload={
                "schema_version": 1,
                "snapshot_id": "forged",
                "hermes_version": "0.21.6",
                "plugin_api_version": 99,
                "capabilities": {
                    "hermes.channel.send": claim(ReceiptLevel.EXTERNAL_DELIVERED)
                },
                "integrity_authenticator": "0" * 64,
            },
        )
        try:
            host._parse_snapshot(JournalRecord(999, forged))
        except HostCapabilityError:
            pass
        else:
            raise AssertionError("an unauthenticated host snapshot was accepted")

        try:
            host.bind_route(
                binding_id="forged-route",
                subject="user:test",
                capability="hermes.channel.send",
                snapshot_event_id=accepted_only.event_id,
                route={"platform": "weixin", "profile": "default", "chat_id": "x"},
                authority_event_id="authority:home-route",
                observed_at=now + timedelta(seconds=9),
            )
        except HostCapabilityError:
            pass
        else:
            raise AssertionError("a route was bound without exact user authority")

    print("HERMES_ALIVE_KERNEL_HOST_CAPABILITIES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
