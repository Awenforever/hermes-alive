"""Transactional append-only experience journal for Hermes Alive."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Callable, Iterator

from .events import EventEnvelope


JOURNAL_SCHEMA_VERSION = 1


class EventConflictError(RuntimeError):
    """An existing event ID was reused for different content."""


class EventIntegrityError(RuntimeError):
    """Stored event content no longer matches its integrity hash."""


@dataclass(frozen=True, slots=True)
class AppendResult:
    sequence: int
    event: EventEnvelope
    created: bool


@dataclass(frozen=True, slots=True)
class JournalRecord:
    sequence: int
    event: EventEnvelope


class ExperienceJournal:
    """A portable event history with explicit replay/checkpoint semantics."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 10.0) -> None:
        self.path = Path(path).expanduser().resolve()
        if self.path.exists() and self.path.is_dir():
            raise ValueError("journal path must be a file")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        from .sqlite_operation_scope import hold_sqlite_resource
        hold_sqlite_resource(self.path)
        return connection

    def _initialize(self) -> None:
        # sqlite3.Connection's context manager commits/rolls back but does not
        # close the handle.  Explicit closing is required on Windows where an
        # open handle prevents backup rotation, migration and test cleanup.
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS kernel_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experience_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    subject TEXT,
                    correlation_id TEXT,
                    causation_id TEXT,
                    schema_version INTEGER NOT NULL,
                    sensitivity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    expires_at TEXT,
                    canonical_json TEXT NOT NULL,
                    integrity_hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_experience_type_sequence
                    ON experience_events(event_type, sequence);
                CREATE INDEX IF NOT EXISTS idx_experience_subject_sequence
                    ON experience_events(subject, sequence);
                CREATE INDEX IF NOT EXISTS idx_experience_subject_type_sequence
                    ON experience_events(subject, event_type, sequence);
                CREATE INDEX IF NOT EXISTS idx_experience_correlation_sequence
                    ON experience_events(correlation_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_experience_causation
                    ON experience_events(causation_id);
                CREATE INDEX IF NOT EXISTS idx_experience_outcome_identity
                    ON experience_events(
                        subject,
                        json_extract(canonical_json, '$.payload.attempt_id'),
                        json_extract(canonical_json, '$.payload.kind'),
                        sequence
                    ) WHERE event_type='outcome.recorded';
                CREATE TABLE IF NOT EXISTS consumer_checkpoints (
                    consumer_name TEXT PRIMARY KEY,
                    last_sequence INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK(last_sequence >= 0)
                );
                INSERT INTO kernel_meta(key, value)
                    VALUES ('journal_schema_version', '1')
                    ON CONFLICT(key) DO NOTHING;
                COMMIT;
                """
            )
            row = connection.execute(
                "SELECT value FROM kernel_meta WHERE key='journal_schema_version'"
            ).fetchone()
            if row is None or int(row["value"]) != JOURNAL_SCHEMA_VERSION:
                raise RuntimeError("unsupported experience journal schema")

    @staticmethod
    def _hash(canonical_json: str) -> str:
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def append(self, event: EventEnvelope | Callable[[sqlite3.Connection], EventEnvelope], *,
               precondition: Callable[[sqlite3.Connection], None] | None = None) -> AppendResult:
        """Append once, optionally checking an internal condition under the writer lock.

        An internal event factory may timestamp a fact under the writer lock.
        Factories/preconditions must not project,
        acquire another writer or perform external I/O. Identical replay does not
        reconsume a resource; conflicts still fail before checking the condition.
        """
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if callable(event):
                    event = event(connection)
                canonical = event.canonical_json()
                digest = self._hash(canonical)
                existing = connection.execute(
                    "SELECT sequence, canonical_json, integrity_hash "
                    "FROM experience_events WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["canonical_json"] != canonical
                        or existing["integrity_hash"] != digest
                    ):
                        raise EventConflictError(
                            f"event_id {event.event_id!r} already has different content"
                        )
                    connection.execute("COMMIT")
                    return AppendResult(int(existing["sequence"]), event, False)

                if precondition is not None:
                    precondition(connection)
                cursor = connection.execute(
                    """
                    INSERT INTO experience_events(
                        event_id, event_type, occurred_at, observed_at, source,
                        actor, subject, correlation_id, causation_id,
                        schema_version, sensitivity, confidence, expires_at,
                        canonical_json, integrity_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.event_type,
                        event.occurred_at.isoformat(),
                        event.observed_at.isoformat(),
                        event.source,
                        event.actor,
                        event.subject,
                        event.correlation_id,
                        event.causation_id,
                        event.schema_version,
                        event.sensitivity.value,
                        event.confidence,
                        event.expires_at.isoformat() if event.expires_at else None,
                        canonical,
                        digest,
                    ),
                )
                sequence = int(cursor.lastrowid)
                connection.execute("COMMIT")
                return AppendResult(sequence, event, True)
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _record(self, row: sqlite3.Row) -> JournalRecord:
        canonical = str(row["canonical_json"])
        actual = self._hash(canonical)
        if actual != row["integrity_hash"]:
            raise EventIntegrityError(f"event sequence {row['sequence']} failed integrity check")
        value = json.loads(canonical)
        return JournalRecord(int(row["sequence"]), EventEnvelope.from_canonical_dict(value))

    def get(self, event_id: str) -> JournalRecord | None:
        """Return one integrity-checked event by identity, if it exists."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT sequence, canonical_json, integrity_hash
                FROM experience_events WHERE event_id=?
                """,
                (event_id,),
            ).fetchone()
        return self._record(row) if row is not None else None

    def recent_for_subject(
        self, *, subject: str, event_type: str, limit: int = 20,
        before_sequence: int | None = None,
    ) -> list[JournalRecord]:
        """Bounded newest-first reads with ownership filtered in SQL.

        This primitive does not authorize a caller; the host supplies the
        authenticated subject. Ascending replay/checkpoints remain unchanged.
        """
        if not subject or not event_type:
            raise ValueError("subject and event_type are required")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("recent read limit must be between 1 and 100")
        if before_sequence is not None and (
            isinstance(before_sequence, bool) or not isinstance(before_sequence, int)
            or before_sequence < 1
        ):
            raise ValueError("before_sequence must be a positive integer")
        query = "SELECT sequence, canonical_json, integrity_hash FROM experience_events WHERE subject=? AND event_type=?"
        parameters: list[object] = [subject, event_type]
        if before_sequence is not None:
            query += " AND sequence < ?"
            parameters.append(before_sequence)
        query += " ORDER BY sequence DESC LIMIT ?"
        parameters.append(limit)
        with closing(self._connect()) as connection:
            return [self._record(row) for row in connection.execute(query, parameters)]

    def read(
        self,
        *,
        after_sequence: int = 0,
        limit: int = 100,
        event_type: str | None = None,
        correlation_id: str | None = None,
        include_expired: bool = True,
        as_of: datetime | None = None,
    ) -> list[JournalRecord]:
        if after_sequence < 0:
            raise ValueError("after_sequence must not be negative")
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        clauses = ["sequence > ?"]
        parameters: list[object] = [after_sequence]
        if event_type is not None:
            clauses.append("event_type = ?")
            parameters.append(event_type)
        if correlation_id is not None:
            clauses.append("correlation_id = ?")
            parameters.append(correlation_id)
        if not include_expired:
            reference = as_of or datetime.now(timezone.utc)
            if reference.tzinfo is None or reference.utcoffset() is None:
                raise ValueError("as_of must be timezone-aware")
            clauses.append("(expires_at IS NULL OR expires_at > ?)")
            parameters.append(reference.astimezone(timezone.utc).isoformat())
        parameters.append(limit)
        query = (
            "SELECT sequence, canonical_json, integrity_hash FROM experience_events WHERE "
            + " AND ".join(clauses)
            + " ORDER BY sequence ASC LIMIT ?"
        )
        with closing(self._connect()) as connection:
            return [self._record(row) for row in connection.execute(query, parameters)]

    def iter_replay(self, *, after_sequence: int = 0, batch_size: int = 500) -> Iterator[JournalRecord]:
        cursor = after_sequence
        while True:
            batch = self.read(after_sequence=cursor, limit=batch_size)
            if not batch:
                return
            yield from batch
            cursor = batch[-1].sequence

    def iter_reverse(
        self,
        *,
        event_types: tuple[str, ...] = (),
        subject: str | None = None,
        batch_size: int = 500,
        max_records: int | None = None,
        before_sequence: int | None = None,
    ) -> Iterator[JournalRecord]:
        """Read newest records first through a bounded, filtered cursor."""

        if not 1 <= batch_size <= 10_000:
            raise ValueError("batch_size must be between 1 and 10000")
        if max_records is not None and max_records < 1:
            raise ValueError("max_records must be positive")
        types = tuple(dict.fromkeys(str(value).strip() for value in event_types))
        if any(not value for value in types):
            raise ValueError("event_types must not contain empty values")
        normalized_subject = str(subject).strip() if subject is not None else None
        if subject is not None and not normalized_subject:
            raise ValueError("subject must not be empty")
        if before_sequence is not None and (type(before_sequence) is not int or before_sequence < 1):
            raise ValueError("before_sequence must be a positive integer")
        before: int | None = before_sequence
        yielded = 0
        while max_records is None or yielded < max_records:
            clauses: list[str] = []
            parameters: list[object] = []
            if before is not None:
                clauses.append("sequence < ?")
                parameters.append(before)
            if types:
                placeholders = ",".join("?" for _ in types)
                clauses.append(f"event_type IN ({placeholders})")
                parameters.extend(types)
            if normalized_subject is not None:
                clauses.append("subject = ?")
                parameters.append(normalized_subject)
            remaining = batch_size
            if max_records is not None:
                remaining = min(remaining, max_records - yielded)
            parameters.append(remaining)
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            query = (
                "SELECT sequence, canonical_json, integrity_hash "
                f"FROM experience_events{where} ORDER BY sequence DESC LIMIT ?"
            )
            with closing(self._connect()) as connection:
                rows = list(connection.execute(query, parameters))
            if not rows:
                return
            for row in rows:
                yield self._record(row)
                yielded += 1
            before = int(rows[-1]["sequence"])

    def last_sequence(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value FROM experience_events"
            ).fetchone()
            return int(row["value"])

    def checkpoint(self, consumer_name: str) -> int:
        name = consumer_name.strip()
        if not name:
            raise ValueError("consumer_name is required")
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT last_sequence FROM consumer_checkpoints WHERE consumer_name=?",
                (name,),
            ).fetchone()
            return int(row["last_sequence"]) if row else 0

    def advance_checkpoint(self, consumer_name: str, sequence: int, *, coalesce: bool = False) -> int:
        """Acknowledge an applied prefix; optionally accept another worker's later ack.

        Strict by default. Projection workers may coalesce only after applying the
        record idempotently. Coalescing never lowers the stored watermark.
        """
        name = consumer_name.strip()
        if not name:
            raise ValueError("consumer_name is required")
        if sequence < 0:
            raise ValueError("sequence must not be negative")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                maximum = int(
                    connection.execute(
                        "SELECT COALESCE(MAX(sequence), 0) AS value FROM experience_events"
                    ).fetchone()["value"]
                )
                if sequence > maximum:
                    raise ValueError("checkpoint cannot advance beyond the journal")
                current_row = connection.execute(
                    "SELECT last_sequence FROM consumer_checkpoints WHERE consumer_name=?",
                    (name,),
                ).fetchone()
                current = int(current_row["last_sequence"]) if current_row else 0
                if sequence < current:
                    if coalesce:
                        connection.execute("COMMIT")
                        return current
                    raise ValueError("checkpoint cannot move backwards")
                connection.execute(
                    """
                    INSERT INTO consumer_checkpoints(consumer_name, last_sequence, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(consumer_name) DO UPDATE SET
                        last_sequence=excluded.last_sequence,
                        updated_at=excluded.updated_at
                    """,
                    (name, sequence, datetime.now(timezone.utc).isoformat()),
                )
                connection.execute("COMMIT")
                return sequence
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def verify_integrity(self) -> int:
        verified = 0
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT sequence, canonical_json, integrity_hash "
                "FROM experience_events ORDER BY sequence"
            )
            for row in rows:
                self._record(row)
                verified += 1
        return verified
