#!/usr/bin/env python3
"""Conservative v2-to-v3 dispatch migration contract."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import DispatchOutbox, ExperienceJournal, OutcomeProjection  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-dispatch-migration-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        OutcomeProjection(journal)
        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                """
                INSERT INTO action_attempts_v1(
                    attempt_id, event_id, selection_event_id, frame_id,
                    candidate_id, subject, executor, idempotency_key,
                    sensitivity, attempted_at, authorization_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "attempt:migration",
                    "action.attempt:attempt:migration",
                    "deliberation.selection:migration",
                    "frame:migration",
                    "candidate:migration",
                    "user:migration",
                    "hermes.channel.send",
                    "migration-key",
                    "private",
                    "2026-10-11T00:00:00+00:00",
                    "action.authorization:migration",
                ),
            )
            connection.executescript(
                """
                CREATE TABLE dispatch_outbox_v2 (
                    dispatch_id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL UNIQUE,
                    authorization_event_id TEXT NOT NULL,
                    policy_event_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    state TEXT NOT NULL,
                    execute_by TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    lease_owner TEXT,
                    lease_token_digest TEXT,
                    lease_until TEXT,
                    lease_generation INTEGER NOT NULL,
                    result_event_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(attempt_id) REFERENCES action_attempts_v1(attempt_id)
                );
                """
            )
            connection.execute(
                """
                INSERT INTO dispatch_outbox_v2 VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    "dispatch:migration",
                    "attempt:migration",
                    "action.authorization:migration",
                    "autonomy.policy:migration",
                    "hermes.channel.send",
                    "migration-key",
                    "user:migration",
                    "content:migration",
                    "private",
                    "leased",
                    "2026-10-11T00:01:00+00:00",
                    "2026-10-11T00:00:00+00:00",
                    "raw-worker-must-disappear",
                    "raw-token-digest-must-disappear",
                    "2026-10-11T00:00:10+00:00",
                    7,
                    None,
                    "2026-10-11T00:00:00+00:00",
                    "2026-10-11T00:00:00+00:00",
                ),
            )
            connection.commit()

        outbox = DispatchOutbox(journal)
        assert outbox.counts() == {"uncertain": 1}
        with closing(sqlite3.connect(journal.path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                ("dispatch:migration",),
            ).fetchone()
            assert row is not None
            assert row["lease_generation"] == 7
            assert row["lease_owner"] is None
            assert row["lease_token_digest"] is None
            assert row["lease_until"] is None
            assert row["started_event_id"] is None
            assert row["content_id"] == "content:migration"

        # Reopening is idempotent and never downgrades uncertainty to pending.
        assert DispatchOutbox(journal).counts() == {"uncertain": 1}

    print("HERMES_ALIVE_KERNEL_DISPATCH_MIGRATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
