"""Signed dispatch chains are checked without constructing an action outbox."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import sqlite3
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
from alive_kernel import ExperienceJournal, EventEnvelope, LocalIdentityProtector
from alive_kernel.dispatch_verifier import DispatchEvidenceVerifier


def main():
    with tempfile.TemporaryDirectory(prefix="dispatch-verifier-") as directory:
        root = Path(directory)
        journal = ExperienceJournal(root / "journal.sqlite3")
        protector = LocalIdentityProtector(root / "identity.key")
        now = datetime.now(timezone.utc)
        auth = EventEnvelope(event_id="authorization:test", event_type="action.authorized",
                             source="test.host", actor="system:test", subject="user:test",
                             payload={"policy_event_id": "policy:test", "route_binding_id": "route", "route_binding_event_id": "route-event",
                                      "host_snapshot_event_id": "host-snapshot"})
        journal.append(auth)
        attempt = journal.append(EventEnvelope(
            event_id="action.attempt:test", event_type="action.attempted", source="alive.outcomes",
            actor="system:test", subject="user:test", observed_at=now, occurred_at=now,
            payload={"attempt_id": "test", "authorization_event_id": auth.event_id,
                     "executor": "hermes.channel.send", "idempotency_key": "delivery:test"},
        ))
        verifier = DispatchEvidenceVerifier(journal, protector)
        def signed(payload, namespace):
            return {**payload, "integrity_authenticator": protector.authenticate_json(namespace, payload)}
        start_payload = {
            "dispatch_id": "dispatch:test", "attempt_id": "test", "idempotency_key": "delivery:test",
            "capability": "hermes.channel.send", "policy_event_id": "policy:test",
            **auth.payload, "lease_generation": 1, "external_result_observed": False,
        }
        start = journal.append(EventEnvelope(
            event_id=verifier._start_event_id("dispatch:test", 1), event_type="dispatch.started",
            source="alive.dispatch", actor="system:alive-dispatch", subject="user:test",
            causation_id=attempt.event.event_id, observed_at=now + timedelta(seconds=1),
            payload=signed(start_payload, "dispatch.start.v1"),
        ))
        result_payload = {
            "dispatch_id": "dispatch:test", "attempt_id": "test", "idempotency_key": "delivery:test",
            "capability": "hermes.channel.send", "start_event_id": start.event.event_id,
            "lease_generation": 1, "outcome": "delivery_succeeded",
        }
        result = journal.append(EventEnvelope(
            event_id="delivery:test", event_type="delivery.succeeded", source="test.channel",
            actor="system:channel", subject="user:test", observed_at=now + timedelta(seconds=2),
            payload=signed(result_payload, "dispatch.result.v1"),
        ))
        assert verifier.verify(result, attempt)
        assert not verifier.verify(result, attempt, observed_by=now + timedelta(seconds=1))
        for field, value in (("attempt_id", "other"), ("idempotency_key", "other"),
                             ("capability", "other"), ("start_event_id", "missing"),
                             ("lease_generation", True), ("lease_generation", 2),
                             ("outcome", "task_completed")):
            bad = replace(result, event=replace(result.event,
                payload=signed({**result_payload, field: value}, "dispatch.result.v1")))
            assert not verifier.verify(bad, attempt), field
        bad = replace(result, event=replace(result.event,
                      payload={**result.event.payload, "integrity_authenticator": "forged"}))
        assert not verifier.verify(bad, attempt)
        assert not verifier.verify(replace(result, event=replace(result.event, subject="user:foreign")), attempt)
        with closing(sqlite3.connect(journal.path)) as connection:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not any("dispatch" in name or "action_attempts" in name for name in names)
        assert not hasattr(verifier, "dispatch") and not hasattr(verifier, "enqueue")
    print("HERMES_ALIVE_DISPATCH_VERIFIER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
