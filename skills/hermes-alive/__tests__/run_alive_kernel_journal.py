#!/usr/bin/env python3
"""Phase-1 contracts for the Hermes Alive durable experience journal."""

from __future__ import annotations

from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile
from uuid import uuid4


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    EventConflictError,
    EventEnvelope,
    EventIntegrityError,
    EventValidationError,
    ExperienceJournal,
    Sensitivity,
)


def event(**overrides: object) -> EventEnvelope:
    values: dict[str, object] = {
        "event_id": str(uuid4()),
        "event_type": "conversation.inbound",
        "source": "hermes.gateway",
        "actor": "user:paired-test",
        "subject": "conversation:test",
        "correlation_id": "turn:test-1",
        "payload": {"text": "hello", "nested": {"value": 1}},
        "sensitivity": Sensitivity.PRIVATE,
    }
    values.update(overrides)
    return EventEnvelope(**values)  # type: ignore[arg-type]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-journal-") as directory:
        path = Path(directory) / "experience.sqlite3"
        journal = ExperienceJournal(path)

        root = event()
        try:
            root.payload["nested"]["value"] = 2  # type: ignore[index]
        except TypeError:
            pass
        else:
            raise AssertionError("nested event payload remained mutable")
        first = journal.append(root)
        assert first.created and first.sequence == 1
        duplicate = journal.append(root)
        assert not duplicate.created and duplicate.sequence == 1

        try:
            journal.append(replace(root, payload={"text": "different"}))
        except EventConflictError:
            pass
        else:
            raise AssertionError("same event ID with changed content was accepted")

        child = event(
            event_type="action.proposed",
            actor="hermes:alive",
            causation_id=root.event_id,
            payload={"kind": "remain_silent", "reason": "recent_user_activity"},
        )
        second = journal.append(child)
        assert second.sequence == 2
        assert [record.sequence for record in journal.read()] == [1, 2]
        assert journal.read(correlation_id="turn:test-1")[1].event.causation_id == root.event_id

        expired = event(
            event_type="context.snapshot",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        journal.append(expired)
        visible = journal.read(include_expired=False)
        assert expired.event_id not in {record.event.event_id for record in visible}

        concurrent = event(event_type="observation.concurrent")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: journal.append(concurrent), range(16)))
        assert sum(result.created for result in results) == 1
        assert len({result.sequence for result in results}) == 1

        assert journal.checkpoint("memory-projector") == 0
        assert journal.advance_checkpoint("memory-projector", 2) == 2
        assert journal.checkpoint("memory-projector") == 2
        try:
            journal.advance_checkpoint("memory-projector", 1)
        except ValueError:
            pass
        else:
            raise AssertionError("consumer checkpoint moved backwards")
        try:
            journal.advance_checkpoint("memory-projector", 100)
        except ValueError:
            pass
        else:
            raise AssertionError("consumer checkpoint advanced beyond journal")

        reopened = ExperienceJournal(path)
        assert reopened.last_sequence() == 4
        assert [record.sequence for record in reopened.iter_replay(batch_size=1)] == [1, 2, 3, 4]
        assert [
            record.sequence
            for record in reopened.iter_reverse(batch_size=1, max_records=3)
        ] == [4, 3, 2]
        assert [
            record.sequence
            for record in reopened.iter_reverse(
                event_types=("conversation.inbound",),
                subject="conversation:test",
                max_records=2,
            )
        ] == [1]
        assert list(
            reopened.iter_reverse(subject="conversation:missing", max_records=2)
        ) == []
        assert reopened.verify_integrity() == 4

        try:
            event(event_type="not_namespaced")
        except EventValidationError:
            pass
        else:
            raise AssertionError("invalid event type was accepted")

        try:
            event(payload={"bad": float("nan")})
        except EventValidationError:
            pass
        else:
            raise AssertionError("non-finite payload number was accepted")

        with closing(sqlite3.connect(path)) as connection:
            connection.execute(
                "UPDATE experience_events SET canonical_json=? WHERE sequence=2",
                ('{"tampered":true}',),
            )
            connection.commit()
        try:
            reopened.verify_integrity()
        except EventIntegrityError:
            pass
        else:
            raise AssertionError("tampered event was not detected")

    print("HERMES_ALIVE_KERNEL_JOURNAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
