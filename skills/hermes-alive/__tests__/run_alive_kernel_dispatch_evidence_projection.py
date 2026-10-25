#!/usr/bin/env python3
"""Dispatch evidence is indexed incrementally and remains rebuildable."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import DispatchOutbox, EventEnvelope, ExperienceJournal  # noqa: E402


def append_noise(journal: ExperienceJournal, start: int, stop: int) -> None:
    for index in range(start, stop):
        journal.append(
            EventEnvelope(
                event_id=f"noise:{index}",
                event_type="system.noise",
                source="test.fixture",
                actor="system:test",
                payload={"index": index},
            )
        )


def append_evidence(
    journal: ExperienceJournal,
    outbox: DispatchOutbox,
    *,
    event_id: str,
    event_type: str,
    attempt_id: str,
    valid: bool = True,
) -> None:
    namespace = (
        "dispatch.start.v1"
        if event_type == "dispatch.started"
        else "dispatch.result.v1"
    )
    payload: dict[str, object] = {"attempt_id": attempt_id}
    payload["integrity_authenticator"] = (
        outbox.protector.authenticate_json(namespace, payload)
        if valid
        else "0" * 64
    )
    now = datetime.now(timezone.utc)
    journal.append(
        EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            source="test.fixture",
            actor="system:test",
            subject="user:test",
            occurred_at=now,
            observed_at=now,
            payload=payload,
        )
    )


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="alive-kernel-dispatch-evidence-"
    ) as directory:
        root = Path(directory)
        journal = ExperienceJournal(root / "kernel.sqlite3")
        outbox = DispatchOutbox(journal)

        append_noise(journal, 0, 19)
        append_evidence(
            journal,
            outbox,
            event_id="dispatch.start:test-a",
            event_type="dispatch.started",
            attempt_id="attempt-a",
        )
        append_evidence(
            journal,
            outbox,
            event_id="delivery:test-a",
            event_type="delivery.succeeded",
            attempt_id="attempt-a",
        )
        append_evidence(
            journal,
            outbox,
            event_id="dispatch.start:forged",
            event_type="dispatch.started",
            attempt_id="attempt-forged",
            valid=False,
        )
        first_watermark = journal.last_sequence()
        assert outbox.project_evidence(batch_size=4) == 2
        assert outbox.evidence_checkpoint() == first_watermark
        assert outbox.evidence_count() == 2
        assert outbox.project_evidence(batch_size=1) == 0

        append_noise(journal, 19, 31)
        append_evidence(
            journal,
            outbox,
            event_id="dispatch.start:test-b",
            event_type="dispatch.started",
            attempt_id="attempt-b",
        )
        second_watermark = journal.last_sequence()
        with ThreadPoolExecutor(max_workers=4) as pool:
            indexed = list(
                pool.map(lambda _: outbox.project_evidence(batch_size=3), range(4))
            )
        assert sum(indexed) == 1
        assert outbox.evidence_checkpoint() == second_watermark
        assert outbox.evidence_count() == 3

        # The projection is disposable. Simulate local projection loss and
        # prove journal replay restores the exact authenticated evidence set.
        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute(
                "DELETE FROM dispatch_evidence_events_v1 WHERE attempt_id=?",
                ("attempt-a",),
            )
            connection.commit()
        assert outbox.evidence_count() == 1
        assert outbox.rebuild_evidence_projection(batch_size=5) == 3
        assert outbox.evidence_checkpoint() == second_watermark
        assert outbox.evidence_count() == 3

        starts = outbox._evidence_candidates(
            "attempt-a", event_types=("dispatch.started",)
        )
        results = outbox._evidence_candidates(
            "attempt-a", event_types=("delivery.succeeded",)
        )
        assert [record.event.event_id for record, _payload in starts] == [
            "dispatch.start:test-a"
        ]
        assert [record.event.event_id for record, _payload in results] == [
            "delivery:test-a"
        ]
        assert outbox._evidence_candidates(
            "attempt-forged", event_types=("dispatch.started",)
        ) == []

        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute(
                """
                UPDATE dispatch_evidence_events_v1 SET attempt_id=?
                WHERE event_id=?
                """,
                ("attempt-tampered", "dispatch.start:test-a"),
            )
            connection.commit()
        assert not outbox.validate_evidence_projection()
        recovered = DispatchOutbox(journal, content_vault=outbox.vault)
        assert recovered.validate_evidence_projection()
        assert recovered.evidence_checkpoint() == second_watermark
        assert recovered.evidence_count() == 3

    print("HERMES_ALIVE_KERNEL_DISPATCH_EVIDENCE_PROJECTION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
