"""Crash-safe dispatch leasing over authorized action attempts.

This module never calls a Hermes channel or tool.  It is an operational outbox
that lets a future adapter claim one still-live attempt without duplicating or
persisting plaintext candidate content.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import secrets
import sqlite3

from .action_contract import ActionContractError, parse_action_contract
from .autonomy_policy import AutonomyPolicyProjection
from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentUnavailableError,
    ContentVault,
)
from .deliberation import deserialize_frame
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector
from .outcomes import OutcomeKind, OutcomeProjection
from .host_capabilities import HostCapabilityProjection, RouteBinding


class DispatchOutboxError(ValueError):
    """A dispatch operation crossed its lease or authority boundary."""


@dataclass(frozen=True, slots=True)
class DispatchLease:
    dispatch_id: str
    attempt_id: str
    capability: str
    idempotency_key: str
    subject: str
    sensitivity: Sensitivity
    execute_by: datetime
    lease_until: datetime
    generation: int
    token: str


@dataclass(frozen=True, slots=True)
class DispatchExecution:
    lease: DispatchLease
    start_event_id: str
    content: object
    route: object


class DispatchOutbox:
    """SQLite outbox with expiring, token-bound, single-owner leases."""

    MAX_LEASE_TTL = timedelta(seconds=30)
    RESULT_KINDS = {
        "delivery.succeeded": OutcomeKind.DELIVERY_SUCCEEDED,
        "delivery.failed": OutcomeKind.DELIVERY_FAILED,
        "task.completed": OutcomeKind.TASK_COMPLETED,
        "task.failed": OutcomeKind.TASK_FAILED,
    }
    RESULT_OUTCOMES = {
        event_type: kind.value for event_type, kind in RESULT_KINDS.items()
    }

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        self.vault = content_vault or ContentVault(
            self.path.parent / "content-vault",
            backup_root=self.path.parent / "content-backups",
        )
        self.protector = LocalIdentityProtector(self.path.parent / "identity.key")
        self.autonomy = AutonomyPolicyProjection(journal)
        self.host = HostCapabilityProjection(journal, content_vault=self.vault)
        self._initialize()

    def _authorization_route(
        self,
        authorization: JournalRecord | None,
        *,
        subject: str,
        capability: str,
        now: datetime,
    ) -> tuple[RouteBinding | None, tuple[str, ...]]:
        """Revalidate the exact route and host snapshot bound into a permit."""

        if authorization is None:
            return None, ("authorization_unavailable",)
        payload = authorization.event.payload
        binding_id = str(payload.get("route_binding_id") or "")
        binding, reasons = self.host.execution_binding(
            binding_id,
            subject=subject,
            capability=capability,
            as_of=now,
        )
        if binding is None:
            return None, reasons
        mismatches: list[str] = []
        if payload.get("route_binding_event_id") != binding.event_id:
            mismatches.append("route_binding_event_mismatch")
        if payload.get("host_snapshot_event_id") != binding.snapshot_event_id:
            mismatches.append("host_snapshot_event_mismatch")
        if payload.get("route_binding_authenticator") != binding.binding_authenticator:
            mismatches.append("route_binding_authenticator_mismatch")
        return (binding if not mismatches else None), tuple(mismatches)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS dispatch_outbox_v3 (
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
                    lease_generation INTEGER NOT NULL DEFAULT 0,
                    started_event_id TEXT,
                    result_event_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    CHECK(state IN (
                        'pending', 'leased', 'started', 'uncertain',
                        'expired', 'revoked', 'acknowledged'
                    )),
                    FOREIGN KEY(attempt_id) REFERENCES action_attempts_v1(attempt_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_dispatch_ready_v3
                    ON dispatch_outbox_v3(state, available_at, execute_by);
                CREATE TABLE IF NOT EXISTS dispatch_evidence_projection_v1 (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    checkpoint_sequence INTEGER NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO dispatch_evidence_projection_v1
                    (singleton, checkpoint_sequence, evidence_count, updated_at)
                VALUES (1, 0, 0, '1970-01-01T00:00:00+00:00');
                CREATE TABLE IF NOT EXISTS dispatch_evidence_events_v1 (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    row_authenticator TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_dispatch_evidence_attempt_v1
                    ON dispatch_evidence_events_v1(
                        attempt_id, event_type, sequence DESC
                    );
                COMMIT;
                """
            )
            prior = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type='table' AND name='dispatch_outbox_v2'
                """
            ).fetchone()
            if prior is not None:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO dispatch_outbox_v3(
                        dispatch_id, attempt_id, authorization_event_id,
                        policy_event_id, capability, idempotency_key, subject,
                        content_id, sensitivity, state, execute_by, available_at,
                        lease_owner, lease_token_digest, lease_until,
                        lease_generation, started_event_id, result_event_id,
                        created_at, updated_at
                    )
                    SELECT dispatch_id, attempt_id, authorization_event_id,
                        policy_event_id, capability, idempotency_key, subject,
                        content_id, sensitivity,
                        CASE WHEN state='leased' THEN 'uncertain' ELSE state END,
                        execute_by, available_at,
                        CASE WHEN state='leased' THEN NULL ELSE lease_owner END,
                        CASE WHEN state='leased' THEN NULL ELSE lease_token_digest END,
                        CASE WHEN state='leased' THEN NULL ELSE lease_until END,
                        lease_generation, NULL, result_event_id,
                        created_at, updated_at
                    FROM dispatch_outbox_v2
                    """
                )
                connection.execute("COMMIT")
        if not self.validate_evidence_projection():
            self.rebuild_evidence_projection()

    def validate_evidence_projection(self) -> bool:
        """Startup structural/HMAC audit; callers may rebuild on false."""

        try:
            with closing(self._connect()) as connection:
                meta = connection.execute(
                    """
                    SELECT checkpoint_sequence, evidence_count
                    FROM dispatch_evidence_projection_v1 WHERE singleton=1
                    """
                ).fetchone()
                rows = connection.execute(
                    """
                    SELECT sequence, event_id, event_type, attempt_id,
                           row_authenticator
                    FROM dispatch_evidence_events_v1 ORDER BY sequence
                    """
                ).fetchall()
            if (
                meta is None
                or int(meta["checkpoint_sequence"]) > self.journal.last_sequence()
                or int(meta["evidence_count"]) != len(rows)
            ):
                return False
            return all(
                self.protector.verify_json(
                    "dispatch.evidence.row.v1",
                    {
                        "sequence": int(row["sequence"]),
                        "event_id": str(row["event_id"]),
                        "event_type": str(row["event_type"]),
                        "attempt_id": str(row["attempt_id"]),
                    },
                    row["row_authenticator"],
                )
                for row in rows
            )
        except (KeyError, TypeError, ValueError, sqlite3.DatabaseError):
            return False

    def evidence_checkpoint(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT checkpoint_sequence
                FROM dispatch_evidence_projection_v1 WHERE singleton=1
                """
            ).fetchone()
            return int(row["checkpoint_sequence"])

    def evidence_count(self) -> int:
        with closing(self._connect()) as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) AS value FROM dispatch_evidence_events_v1"
                ).fetchone()["value"]
            )

    def project_evidence(self, *, batch_size: int = 500) -> int:
        """Advance a rebuildable evidence index to one captured journal watermark.

        Each batch and its checkpoint commit atomically.  ``batch_size`` bounds
        transaction size, never total correctness: the loop continues until it
        reaches the watermark that existed when projection began.
        """

        if not 1 <= batch_size <= 10_000:
            raise DispatchOutboxError(
                "evidence projection batch size must be between 1 and 10000"
            )
        watermark = self.journal.last_sequence()
        indexed = 0
        while True:
            checkpoint = self.evidence_checkpoint()
            if checkpoint >= watermark:
                return indexed
            records: list[JournalRecord] = []
            for record in self.journal.iter_replay(
                after_sequence=checkpoint,
                batch_size=batch_size,
            ):
                if record.sequence > watermark:
                    break
                records.append(record)
                if len(records) >= batch_size:
                    break
            if not records:
                raise DispatchOutboxError(
                    "dispatch evidence projection could not reach its watermark"
                )
            candidates: list[tuple[int, str, str, str, str]] = []
            for record in records:
                if record.event.event_type == "dispatch.started":
                    payload = self._authenticated_start_payload(record)
                elif record.event.event_type in self.RESULT_KINDS:
                    payload = self._authenticated_result_payload(record)
                else:
                    continue
                attempt_id = str((payload or {}).get("attempt_id") or "").strip()
                if attempt_id:
                    row_document = {
                        "sequence": record.sequence,
                        "event_id": record.event.event_id,
                        "event_type": record.event.event_type,
                        "attempt_id": attempt_id,
                    }
                    candidates.append(
                        (
                            record.sequence,
                            record.event.event_id,
                            record.event.event_type,
                            attempt_id,
                            self.protector.authenticate_json(
                                "dispatch.evidence.row.v1", row_document
                            ),
                        )
                    )
            last_sequence = records[-1].sequence
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    current = int(
                        connection.execute(
                            """
                            SELECT checkpoint_sequence
                            FROM dispatch_evidence_projection_v1
                            WHERE singleton=1
                            """
                        ).fetchone()["checkpoint_sequence"]
                    )
                    if current != checkpoint:
                        connection.execute("ROLLBACK")
                        continue
                    before_count = int(
                        connection.execute(
                            "SELECT COUNT(*) AS value FROM dispatch_evidence_events_v1"
                        ).fetchone()["value"]
                    )
                    connection.executemany(
                        """
                        INSERT OR IGNORE INTO dispatch_evidence_events_v1(
                            sequence, event_id, event_type, attempt_id,
                            row_authenticator
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        candidates,
                    )
                    after_count = int(
                        connection.execute(
                            "SELECT COUNT(*) AS value FROM dispatch_evidence_events_v1"
                        ).fetchone()["value"]
                    )
                    indexed += after_count - before_count
                    connection.execute(
                        """
                        UPDATE dispatch_evidence_projection_v1
                        SET checkpoint_sequence=?, evidence_count=?, updated_at=?
                        WHERE singleton=1
                        """,
                        (
                            last_sequence,
                            after_count,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    connection.execute("COMMIT")
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise

    def rebuild_evidence_projection(self, *, batch_size: int = 500) -> int:
        """Discard the derived index and replay it from the durable journal."""

        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("DELETE FROM dispatch_evidence_events_v1")
                connection.execute(
                    """
                    UPDATE dispatch_evidence_projection_v1
                    SET checkpoint_sequence=0, evidence_count=0, updated_at=?
                    WHERE singleton=1
                    """,
                    (datetime.now(timezone.utc).isoformat(),),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return self.project_evidence(batch_size=batch_size)

    def _evidence_candidates(
        self,
        attempt_id: str,
        *,
        event_types: tuple[str, ...],
    ) -> list[tuple[JournalRecord, dict[str, object]]]:
        if not event_types:
            raise DispatchOutboxError("at least one evidence event type is required")
        placeholders = ",".join("?" for _ in event_types)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT sequence, event_id, event_type, attempt_id,
                       row_authenticator
                FROM dispatch_evidence_events_v1
                WHERE attempt_id=? AND event_type IN ("""
                + placeholders
                + ") ORDER BY sequence DESC",
                (attempt_id, *event_types),
            ).fetchall()
        candidates: list[tuple[JournalRecord, dict[str, object]]] = []
        for row in rows:
            row_document = {
                "sequence": int(row["sequence"]),
                "event_id": str(row["event_id"]),
                "event_type": str(row["event_type"]),
                "attempt_id": str(row["attempt_id"]),
            }
            if not self.protector.verify_json(
                "dispatch.evidence.row.v1",
                row_document,
                row["row_authenticator"],
            ):
                raise DispatchOutboxError("dispatch evidence projection is corrupt")
            record = self.journal.get(str(row["event_id"]))
            payload = (
                self._authenticated_start_payload(record)
                if record is not None and record.event.event_type == "dispatch.started"
                else self._authenticated_result_payload(record)
            )
            if record is not None and payload is not None:
                candidates.append((record, payload))
        return candidates

    @staticmethod
    def _utc(value: datetime | None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise DispatchOutboxError("dispatch time must be timezone-aware")
        return current.astimezone(timezone.utc)

    @staticmethod
    def _dispatch_id(attempt_id: str) -> str:
        digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()[:40]
        return f"dispatch:{digest}"

    @staticmethod
    def _start_event_id(dispatch_id: str, generation: int) -> str:
        digest = hashlib.sha256(
            f"{dispatch_id}\0{generation}".encode("utf-8")
        ).hexdigest()[:40]
        return f"dispatch.start:{digest}"

    def _authenticated_start_payload(
        self, record: JournalRecord | None
    ) -> dict[str, object] | None:
        if record is None:
            return None
        payload = _thaw_json(record.event.payload)
        authenticator = payload.pop("integrity_authenticator", None)
        if not self.protector.verify_json(
            "dispatch.start.v1", payload, authenticator
        ):
            return None
        return payload

    def _valid_start_evidence(
        self,
        record: JournalRecord | None,
        payload: dict[str, object] | None,
        attempt: JournalRecord | None,
        *,
        dispatch_id: str,
        attempt_id: str,
        idempotency_key: str,
        capability: str,
        policy_event_id: str,
        subject: str,
        sensitivity: Sensitivity,
        generation: int | None = None,
    ) -> bool:
        authorization = (
            self.journal.get(str(attempt.event.payload.get("authorization_event_id") or ""))
            if attempt is not None
            else None
        )
        authorization_payload = authorization.event.payload if authorization is not None else {}
        return bool(
            record is not None
            and payload is not None
            and attempt is not None
            and record.sequence > attempt.sequence
            and record.event.event_type == "dispatch.started"
            and record.event.source == "alive.dispatch"
            and record.event.actor == "system:alive-dispatch"
            and record.event.subject == subject
            and record.event.sensitivity == sensitivity
            and record.event.observed_at >= attempt.event.observed_at
            and payload.get("dispatch_id") == dispatch_id
            and payload.get("attempt_id") == attempt_id
            and payload.get("idempotency_key") == idempotency_key
            and payload.get("capability") == capability
            and payload.get("policy_event_id") == policy_event_id
            and payload.get("route_binding_id")
            == authorization_payload.get("route_binding_id")
            and payload.get("route_binding_event_id")
            == authorization_payload.get("route_binding_event_id")
            and payload.get("host_snapshot_event_id")
            == authorization_payload.get("host_snapshot_event_id")
            and isinstance(payload.get("lease_generation"), int)
            and int(payload["lease_generation"]) >= 1
            and record.event.event_id
            == self._start_event_id(
                dispatch_id, int(payload["lease_generation"])
            )
            and record.event.causation_id == f"action.attempt:{attempt_id}"
            and (
                generation is None
                or int(payload["lease_generation"]) == generation
            )
            and payload.get("external_result_observed") is False
        )

    def _authenticated_result_payload(
        self, result: JournalRecord | None
    ) -> dict[str, object] | None:
        if result is None:
            return None
        payload = _thaw_json(result.event.payload)
        authenticator = payload.pop("integrity_authenticator", None)
        if not self.protector.verify_json(
            "dispatch.result.v1", payload, authenticator
        ):
            return None
        return payload

    def _valid_result_evidence(
        self,
        result: JournalRecord | None,
        payload: dict[str, object] | None,
        attempt: JournalRecord | None,
        start: JournalRecord | None,
        *,
        dispatch_id: str,
        attempt_id: str,
        idempotency_key: str,
        capability: str,
        subject: str,
        sensitivity: Sensitivity,
        generation: int,
        observed_by: datetime | None = None,
    ) -> bool:
        expected_types = (
            {"delivery.succeeded", "delivery.failed"}
            if capability == "hermes.channel.send"
            else {"task.completed", "task.failed"}
        )
        return bool(
            result is not None
            and payload is not None
            and attempt is not None
            and start is not None
            and result.sequence > start.sequence > attempt.sequence
            and result.event.event_type in expected_types
            and result.event.subject == subject
            and result.event.sensitivity == sensitivity
            and result.event.observed_at >= start.event.observed_at
            and (observed_by is None or result.event.observed_at <= observed_by)
            and payload.get("dispatch_id") == dispatch_id
            and payload.get("attempt_id") == attempt_id
            and payload.get("idempotency_key") == idempotency_key
            and payload.get("capability") == capability
            and payload.get("start_event_id") == start.event.event_id
            and payload.get("lease_generation") == generation
            and payload.get("outcome")
            == self.RESULT_OUTCOMES.get(result.event.event_type)
        )

    def _select_start_evidence(
        self,
        candidates: list[tuple[JournalRecord, dict[str, object]]],
        attempt: JournalRecord | None,
        *,
        dispatch_id: str,
        attempt_id: str,
        idempotency_key: str,
        capability: str,
        policy_event_id: str,
        subject: str,
        sensitivity: Sensitivity,
    ) -> tuple[JournalRecord | None, dict[str, object] | None, int]:
        for record, payload in candidates:
            if self._valid_start_evidence(
                record,
                payload,
                attempt,
                dispatch_id=dispatch_id,
                attempt_id=attempt_id,
                idempotency_key=idempotency_key,
                capability=capability,
                policy_event_id=policy_event_id,
                subject=subject,
                sensitivity=sensitivity,
            ):
                return record, payload, int(payload["lease_generation"])
        return None, None, 0

    def _select_result_evidence(
        self,
        candidates: list[tuple[JournalRecord, dict[str, object]]],
        attempt: JournalRecord | None,
        start: JournalRecord | None,
        *,
        dispatch_id: str,
        attempt_id: str,
        idempotency_key: str,
        capability: str,
        subject: str,
        sensitivity: Sensitivity,
        generation: int,
    ) -> JournalRecord | None:
        for record, payload in candidates:
            if self._valid_result_evidence(
                record,
                payload,
                attempt,
                start,
                dispatch_id=dispatch_id,
                attempt_id=attempt_id,
                idempotency_key=idempotency_key,
                capability=capability,
                subject=subject,
                sensitivity=sensitivity,
                generation=generation,
            ):
                return record
        return None

    def reconcile(
        self,
        *,
        now: datetime | None = None,
        limit: int = 1000,
        recovering: bool = False,
    ) -> int:
        """Materialize missing jobs from recorded attempts without plaintext."""

        if not 1 <= limit <= 10_000:
            raise DispatchOutboxError("reconcile limit must be between 1 and 10000")
        current = self._utc(now)
        inserted = 0
        self.project_evidence()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    """
                    SELECT a.*, s.content_id AS selection_content_id,
                           f.content_id AS frame_content_id
                    FROM action_attempts_v1 a
                    JOIN deliberation_selections_v1 s
                      ON s.event_id=a.selection_event_id AND s.outcome='validated'
                    JOIN deliberation_frames_v1 f ON f.frame_id=a.frame_id
                    LEFT JOIN dispatch_outbox_v3 d ON d.attempt_id=a.attempt_id
                    WHERE d.attempt_id IS NULL
                      AND NOT EXISTS (
                        SELECT 1 FROM action_outcomes_v1 o
                        WHERE o.attempt_id=a.attempt_id
                          AND o.kind IN (
                            'delivery_succeeded', 'delivery_failed',
                            'task_completed', 'task_failed'
                          )
                      )
                    ORDER BY a.rowid LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                for row in rows:
                    authorization = self.journal.get(row["authorization_event_id"])
                    if authorization is None:
                        continue
                    valid_until = authorization.event.payload.get("valid_until")
                    policy_event_id = str(
                        authorization.event.payload.get("policy_event_id") or ""
                    )
                    try:
                        execute_by = datetime.fromisoformat(str(valid_until))
                    except (TypeError, ValueError):
                        continue
                    if execute_by.tzinfo is None or execute_by.utcoffset() is None:
                        continue
                    execute_by = execute_by.astimezone(timezone.utc)
                    frame_document = self.vault.resolve_json(
                        row["frame_content_id"],
                        expected_subject=row["subject"],
                        expected_purpose="deliberation.frame",
                        expected_sensitivity=Sensitivity(row["sensitivity"]),
                    )
                    frame, _context = deserialize_frame(frame_document)
                    candidate = next(
                        (
                            item
                            for item in frame.candidates
                            if item.candidate_id == row["candidate_id"]
                        ),
                        None,
                    )
                    if candidate is None or candidate.content_id is None:
                        continue
                    contract_valid = True
                    try:
                        contract_document = self.vault.resolve_json(
                            candidate.content_id,
                            expected_subject=str(row["subject"]),
                            expected_purpose="deliberation.candidate",
                            expected_sensitivity=Sensitivity(row["sensitivity"]),
                        )
                        contract = parse_action_contract(
                            contract_document,
                            capability=str(row["executor"]),
                        )
                    except (
                        ActionContractError,
                        ContentErasedError,
                        ContentIntegrityError,
                        ContentUnavailableError,
                    ):
                        contract_valid = False
                    else:
                        contract_valid = bool(
                            authorization.event.payload.get("action_contract_version")
                            == 1
                            and self.protector.verify_json(
                                "action.contract.v1",
                                contract.to_document(),
                                authorization.event.payload.get(
                                    "action_contract_binding"
                                ),
                            )
                        )
                    route_binding, _route_reasons = self._authorization_route(
                        authorization,
                        subject=str(row["subject"]),
                        capability=str(row["executor"]),
                        now=current,
                    )
                    contract_valid = contract_valid and route_binding is not None
                    dispatch_id = self._dispatch_id(str(row["attempt_id"]))
                    attempt_id = str(row["attempt_id"])
                    attempt_event = self.journal.get(str(row["event_id"]))
                    observed_starts = self._evidence_candidates(
                        attempt_id, event_types=("dispatch.started",)
                    )
                    observed_results = self._evidence_candidates(
                        attempt_id, event_types=tuple(self.RESULT_KINDS)
                    )
                    start_record, _start_payload, start_generation = (
                        self._select_start_evidence(
                            observed_starts,
                            attempt_event,
                            dispatch_id=dispatch_id,
                            attempt_id=attempt_id,
                            idempotency_key=str(row["idempotency_key"]),
                            capability=str(row["executor"]),
                            policy_event_id=policy_event_id,
                            subject=str(row["subject"]),
                            sensitivity=Sensitivity(row["sensitivity"]),
                        )
                    )
                    result_record = self._select_result_evidence(
                        observed_results,
                        attempt_event,
                        start_record,
                        dispatch_id=dispatch_id,
                        attempt_id=attempt_id,
                        idempotency_key=str(row["idempotency_key"]),
                        capability=str(row["executor"]),
                        subject=str(row["subject"]),
                        sensitivity=Sensitivity(row["sensitivity"]),
                        generation=start_generation,
                    )
                    valid_start = start_record is not None
                    result_event_id = (
                        result_record.event.event_id
                        if result_record is not None
                        else None
                    )
                    current_policy = self.autonomy.current(str(row["subject"]))
                    policy_current = bool(
                        current_policy is not None
                        and current_policy.enabled
                        and current_policy.event_id == policy_event_id
                    )
                    if result_event_id is not None:
                        state = "acknowledged"
                    elif valid_start:
                        state = "uncertain"
                    elif not contract_valid:
                        state = "revoked"
                    else:
                        state = (
                            "expired"
                            if execute_by <= current
                            else "pending" if policy_current else "revoked"
                        )
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO dispatch_outbox_v3(
                            dispatch_id, attempt_id, authorization_event_id,
                            policy_event_id,
                            capability, idempotency_key, subject, content_id,
                            sensitivity, state, execute_by, available_at,
                            lease_owner, lease_token_digest, lease_until,
                            lease_generation, started_event_id, result_event_id,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL,
                                  NULL, ?, ?, ?, ?, ?)
                        """,
                        (
                            dispatch_id,
                            row["attempt_id"],
                            row["authorization_event_id"],
                            policy_event_id,
                            row["executor"],
                            row["idempotency_key"],
                            row["subject"],
                            candidate.content_id,
                            row["sensitivity"],
                            state,
                            execute_by.isoformat(),
                            current.isoformat(),
                            start_generation,
                            start_record.event.event_id if valid_start else None,
                            result_event_id,
                            current.isoformat(),
                            current.isoformat(),
                        ),
                    )
                    inserted += int(connection.execute("SELECT changes()").fetchone()[0])
                active_rows = connection.execute(
                    """
                    SELECT * FROM dispatch_outbox_v3
                    WHERE state<>'acknowledged'
                    """
                ).fetchall()
                for row in active_rows:
                    attempt_id = str(row["attempt_id"])
                    attempt_event = self.journal.get(f"action.attempt:{attempt_id}")
                    observed_starts = self._evidence_candidates(
                        attempt_id, event_types=("dispatch.started",)
                    )
                    observed_results = self._evidence_candidates(
                        attempt_id, event_types=tuple(self.RESULT_KINDS)
                    )
                    start_record, _start_payload, generation = (
                        self._select_start_evidence(
                            observed_starts,
                            attempt_event,
                            dispatch_id=str(row["dispatch_id"]),
                            attempt_id=attempt_id,
                            idempotency_key=str(row["idempotency_key"]),
                            capability=str(row["capability"]),
                            policy_event_id=str(row["policy_event_id"]),
                            subject=str(row["subject"]),
                            sensitivity=Sensitivity(row["sensitivity"]),
                        )
                    )
                    result_record = self._select_result_evidence(
                        observed_results,
                        attempt_event,
                        start_record,
                        dispatch_id=str(row["dispatch_id"]),
                        attempt_id=attempt_id,
                        idempotency_key=str(row["idempotency_key"]),
                        capability=str(row["capability"]),
                        subject=str(row["subject"]),
                        sensitivity=Sensitivity(row["sensitivity"]),
                        generation=generation,
                    )
                    valid_start = start_record is not None
                    if result_record is not None:
                        connection.execute(
                            """
                            UPDATE dispatch_outbox_v3
                            SET state='acknowledged', lease_owner=NULL,
                                lease_token_digest=NULL, lease_until=NULL,
                                lease_generation=?, started_event_id=?,
                                result_event_id=?, updated_at=?
                            WHERE dispatch_id=?
                            """,
                            (
                                generation,
                                start_record.event.event_id,
                                result_record.event.event_id,
                                current.isoformat(),
                                row["dispatch_id"],
                            ),
                        )
                    elif valid_start:
                        lease_until = (
                            datetime.fromisoformat(str(row["lease_until"]))
                            if row["lease_until"]
                            else None
                        )
                        if (
                            recovering
                            or row["state"] != "started"
                            or lease_until is None
                            or lease_until <= current
                        ):
                            connection.execute(
                                """
                                UPDATE dispatch_outbox_v3
                                SET state='uncertain', lease_owner=NULL,
                                    lease_token_digest=NULL, lease_until=NULL,
                                    lease_generation=?, started_event_id=?,
                                    updated_at=?
                                WHERE dispatch_id=?
                                """,
                                (
                                    generation,
                                    start_record.event.event_id,
                                    current.isoformat(),
                                    row["dispatch_id"],
                                ),
                            )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return inserted

    def acquire(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
        lease_ttl: timedelta = timedelta(seconds=10),
    ) -> DispatchLease | None:
        current = self._utc(now)
        # A start event is the source of truth during the crash gap before the
        # operational row can be updated. Absorb it before considering reclaim.
        self.reconcile(now=current)
        self.refresh_authority(now=current)
        worker = self.protector.pseudonym("dispatch_worker", worker_id)
        if worker is None:
            raise DispatchOutboxError("worker identity is required")
        if not timedelta(0) < lease_ttl <= self.MAX_LEASE_TTL:
            raise DispatchOutboxError("lease TTL must be between zero and 30 seconds")
        token = secrets.token_urlsafe(32)
        token_digest = self.protector.pseudonym("dispatch_lease", token)
        assert token_digest is not None
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    UPDATE dispatch_outbox_v3
                    SET state='expired', lease_owner=NULL,
                        lease_token_digest=NULL, lease_until=NULL, updated_at=?
                    WHERE state IN ('pending', 'leased') AND execute_by<=?
                    """,
                    (current.isoformat(), current.isoformat()),
                )
                connection.execute(
                    """
                    UPDATE dispatch_outbox_v3
                    SET state='uncertain', lease_owner=NULL,
                        lease_token_digest=NULL, lease_until=NULL, updated_at=?
                    WHERE state='started' AND lease_until<=?
                    """,
                    (current.isoformat(), current.isoformat()),
                )
                connection.execute(
                    """
                    UPDATE dispatch_outbox_v3 AS d
                    SET state='revoked', lease_owner=NULL,
                        lease_token_digest=NULL, lease_until=NULL, updated_at=?
                    WHERE state IN ('pending', 'leased')
                      AND NOT EXISTS (
                        SELECT 1 FROM autonomy_policies_v1 p
                        WHERE p.subject=d.subject AND p.enabled=1
                          AND p.policy_event_id=d.policy_event_id
                      )
                    """,
                    (current.isoformat(),),
                )
                row = connection.execute(
                    """
                    SELECT * FROM dispatch_outbox_v3
                    WHERE execute_by>?
                      AND ((state='pending' AND available_at<=?)
                           OR (state='leased' AND lease_until<=?))
                    ORDER BY available_at, created_at, dispatch_id
                    LIMIT 1
                    """,
                    (current.isoformat(), current.isoformat(), current.isoformat()),
                ).fetchone()
                if row is None:
                    connection.execute("COMMIT")
                    return None
                execute_by = datetime.fromisoformat(row["execute_by"])
                lease_until = min(current + lease_ttl, execute_by)
                connection.execute(
                    """
                    UPDATE dispatch_outbox_v3
                    SET state='leased', lease_owner=?, lease_token_digest=?,
                        lease_until=?, lease_generation=lease_generation+1,
                        updated_at=?
                    WHERE dispatch_id=?
                    """,
                    (
                        worker,
                        token_digest,
                        lease_until.isoformat(),
                        current.isoformat(),
                        row["dispatch_id"],
                    ),
                )
                generation = int(row["lease_generation"]) + 1
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return DispatchLease(
            str(row["dispatch_id"]),
            str(row["attempt_id"]),
            str(row["capability"]),
            str(row["idempotency_key"]),
            str(row["subject"]),
            Sensitivity(row["sensitivity"]),
            execute_by,
            lease_until,
            generation,
            token,
        )

    def refresh_authority(self, *, now: datetime | None = None) -> int:
        """Revoke work whose policy, route, or host delivery contract changed."""

        current = self._utc(now)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    UPDATE dispatch_outbox_v3 AS d
                    SET state='revoked', lease_owner=NULL,
                        lease_token_digest=NULL, lease_until=NULL, updated_at=?
                    WHERE state IN ('pending', 'leased')
                      AND NOT EXISTS (
                        SELECT 1 FROM autonomy_policies_v1 p
                        WHERE p.subject=d.subject AND p.enabled=1
                          AND p.policy_event_id=d.policy_event_id
                      )
                    """,
                    (current.isoformat(),),
                )
                changed = int(connection.execute("SELECT changes()").fetchone()[0])
                rows = connection.execute(
                    """
                    SELECT * FROM dispatch_outbox_v3
                    WHERE state IN ('pending', 'leased')
                    """
                ).fetchall()
                for row in rows:
                    authorization = self.journal.get(str(row["authorization_event_id"]))
                    binding, _reasons = self._authorization_route(
                        authorization,
                        subject=str(row["subject"]),
                        capability=str(row["capability"]),
                        now=current,
                    )
                    if binding is None:
                        connection.execute(
                            """
                            UPDATE dispatch_outbox_v3
                            SET state='revoked', lease_owner=NULL,
                                lease_token_digest=NULL, lease_until=NULL, updated_at=?
                            WHERE dispatch_id=? AND state IN ('pending', 'leased')
                            """,
                            (current.isoformat(), row["dispatch_id"]),
                        )
                        changed += int(connection.execute("SELECT changes()").fetchone()[0])
                connection.execute("COMMIT")
                return changed
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def begin_execution(
        self,
        lease: DispatchLease,
        *,
        clearance: Sensitivity,
        now: datetime | None = None,
    ) -> DispatchExecution:
        """Cross the adapter boundary once and return content to that caller."""

        current = self._utc(now)
        self.refresh_authority(now=current)
        allowed = list(Sensitivity)[: list(Sensitivity).index(Sensitivity(clearance)) + 1]
        digest = self.protector.pseudonym("dispatch_lease", lease.token)
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                (lease.dispatch_id,),
            ).fetchone()
            policy = (
                connection.execute(
                    "SELECT * FROM autonomy_policies_v1 WHERE subject=?",
                    (row["subject"],),
                ).fetchone()
                if row is not None
                else None
            )
        if (
            row is None
            or row["state"] != "leased"
            or row["lease_token_digest"] != digest
            or int(row["lease_generation"]) != lease.generation
            or datetime.fromisoformat(row["lease_until"]) <= current
            or datetime.fromisoformat(row["execute_by"]) <= current
            or Sensitivity(row["sensitivity"]) not in allowed
            or policy is None
            or not bool(policy["enabled"])
            or policy["policy_event_id"] != row["policy_event_id"]
        ):
            raise DispatchOutboxError("dispatch lease is invalid or expired")
        try:
            content_document = self.vault.resolve_json(
                row["content_id"],
                expected_subject=row["subject"],
                expected_purpose="deliberation.candidate",
                expected_sensitivity=Sensitivity(row["sensitivity"]),
            )
            contract = parse_action_contract(
                content_document,
                capability=str(row["capability"]),
            )
        except (
            ActionContractError,
            ContentErasedError,
            ContentIntegrityError,
            ContentUnavailableError,
        ) as exc:
            raise DispatchOutboxError("dispatch action contract is invalid") from exc
        authorization = self.journal.get(str(row["authorization_event_id"]))
        if (
            authorization is None
            or authorization.event.payload.get("action_contract_version") != 1
            or not self.protector.verify_json(
                "action.contract.v1",
                contract.to_document(),
                authorization.event.payload.get("action_contract_binding"),
            )
        ):
            raise DispatchOutboxError("dispatch action contract was not authorized")
        route_binding, route_reasons = self._authorization_route(
            authorization,
            subject=str(row["subject"]),
            capability=str(row["capability"]),
            now=current,
        )
        if route_binding is None:
            raise DispatchOutboxError(
                "dispatch route is not authorized: " + ",".join(route_reasons)
            )
        route = self.host.resolve_route(route_binding)
        start_payload: dict[str, object] = {
            "dispatch_id": str(row["dispatch_id"]),
            "attempt_id": str(row["attempt_id"]),
            "idempotency_key": str(row["idempotency_key"]),
            "capability": str(row["capability"]),
            "policy_event_id": str(row["policy_event_id"]),
            "route_binding_id": route_binding.binding_id,
            "route_binding_event_id": route_binding.event_id,
            "host_snapshot_event_id": route_binding.snapshot_event_id,
            "lease_generation": int(row["lease_generation"]),
            "external_result_observed": False,
        }
        start_payload["integrity_authenticator"] = self.protector.authenticate_json(
            "dispatch.start.v1", start_payload
        )
        start_event = EventEnvelope(
            event_id=self._start_event_id(
                lease.dispatch_id, int(row["lease_generation"])
            ),
            event_type="dispatch.started",
            source="alive.dispatch",
            actor="system:alive-dispatch",
            subject=str(row["subject"]),
            causation_id=f"action.attempt:{lease.attempt_id}",
            occurred_at=current,
            observed_at=current,
            sensitivity=Sensitivity(row["sensitivity"]),
            payload=start_payload,
        )
        try:
            appended = self.journal.append(start_event)
        except EventConflictError as exc:
            raise DispatchOutboxError(
                "dispatch start identity was already consumed"
            ) from exc
        start_record = JournalRecord(appended.sequence, appended.event)
        attempt = self.journal.get(f"action.attempt:{lease.attempt_id}")
        if not self._valid_start_evidence(
            start_record,
            self._authenticated_start_payload(start_record),
            attempt,
            dispatch_id=lease.dispatch_id,
            attempt_id=lease.attempt_id,
            idempotency_key=lease.idempotency_key,
            capability=lease.capability,
            policy_event_id=str(row["policy_event_id"]),
            subject=lease.subject,
            sensitivity=lease.sensitivity,
            generation=lease.generation,
        ):
            raise DispatchOutboxError("dispatch start evidence is invalid")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT * FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                (lease.dispatch_id,),
            ).fetchone()
            current_policy = connection.execute(
                "SELECT * FROM autonomy_policies_v1 WHERE subject=?",
                (lease.subject,),
            ).fetchone()
            current_binding, _current_route_reasons = self._authorization_route(
                authorization,
                subject=lease.subject,
                capability=lease.capability,
                now=current,
            )
            if (
                current_row is None
                or current_row["state"] != "leased"
                or current_row["lease_token_digest"] != digest
                or int(current_row["lease_generation"]) != lease.generation
                or datetime.fromisoformat(current_row["lease_until"]) <= current
                or datetime.fromisoformat(current_row["execute_by"]) <= current
                or current_policy is None
                or not bool(current_policy["enabled"])
                or current_policy["policy_event_id"]
                != current_row["policy_event_id"]
                or current_binding is None
            ):
                connection.execute("ROLLBACK")
                raise DispatchOutboxError(
                    "dispatch authority changed before execution began"
                )
            connection.execute(
                """
                UPDATE dispatch_outbox_v3
                SET state='started', started_event_id=?, updated_at=?
                WHERE dispatch_id=?
                """,
                (start_event.event_id, current.isoformat(), lease.dispatch_id),
            )
            connection.execute("COMMIT")
        return DispatchExecution(
            lease, start_event.event_id, contract.to_document(), route
        )

    def release(
        self,
        lease: DispatchLease,
        *,
        retry_after: timedelta = timedelta(0),
        now: datetime | None = None,
    ) -> str:
        current = self._utc(now)
        self.refresh_authority(now=current)
        if not timedelta(0) <= retry_after <= timedelta(seconds=30):
            raise DispatchOutboxError("retry delay must be between zero and 30 seconds")
        digest = self.protector.pseudonym("dispatch_lease", lease.token)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                (lease.dispatch_id,),
            ).fetchone()
            if (
                row is None
                or row["state"] != "leased"
                or row["lease_token_digest"] != digest
                or int(row["lease_generation"]) != lease.generation
            ):
                connection.execute("ROLLBACK")
                raise DispatchOutboxError("dispatch lease is not owned by the caller")
            available = current + retry_after
            state = (
                "expired"
                if datetime.fromisoformat(row["execute_by"]) <= available
                else "pending"
            )
            connection.execute(
                """
                UPDATE dispatch_outbox_v3
                SET state=?, available_at=?, lease_owner=NULL,
                    lease_token_digest=NULL, lease_until=NULL, updated_at=?
                WHERE dispatch_id=?
                """,
                (state, available.isoformat(), current.isoformat(), lease.dispatch_id),
            )
            connection.execute("COMMIT")
        return state

    def acknowledge(
        self,
        lease: DispatchLease,
        *,
        result_event_id: str,
        now: datetime | None = None,
    ) -> None:
        """Close a live lease only against an observed Hermes result event."""

        current = self._utc(now)
        result = self.journal.get(str(result_event_id).strip())
        attempt = self.journal.get(f"action.attempt:{lease.attempt_id}")
        digest = self.protector.pseudonym("dispatch_lease", lease.token)
        result_payload = self._authenticated_result_payload(result)
        with closing(self._connect()) as connection:
            observed_row = connection.execute(
                "SELECT * FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                (lease.dispatch_id,),
            ).fetchone()
        start_event_id = (
            str(observed_row["started_event_id"])
            if observed_row is not None and observed_row["started_event_id"]
            else str((result_payload or {}).get("start_event_id") or "")
        )
        start = self.journal.get(start_event_id)
        start_payload = self._authenticated_start_payload(start)
        if not self._valid_result_evidence(
            result,
            result_payload,
            attempt,
            start,
            dispatch_id=lease.dispatch_id,
            attempt_id=lease.attempt_id,
            idempotency_key=lease.idempotency_key,
            capability=lease.capability,
            subject=lease.subject,
            sensitivity=lease.sensitivity,
            generation=lease.generation,
            observed_by=current,
        ) or not self._valid_start_evidence(
            start,
            start_payload,
            attempt,
            dispatch_id=lease.dispatch_id,
            attempt_id=lease.attempt_id,
            idempotency_key=lease.idempotency_key,
            capability=lease.capability,
            policy_event_id=str(observed_row["policy_event_id"])
            if observed_row is not None
            else str((start_payload or {}).get("policy_event_id") or ""),
            subject=lease.subject,
            sensitivity=lease.sensitivity,
            generation=lease.generation,
        ):
            raise DispatchOutboxError("dispatch result evidence is invalid")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM dispatch_outbox_v3 WHERE dispatch_id=?",
                (lease.dispatch_id,),
            ).fetchone()
            if (
                row is None
                or row["state"] not in {"started", "uncertain"}
                or int(row["lease_generation"]) != lease.generation
                or row["started_event_id"] != start_event_id
                or (
                    row["state"] == "started"
                    and row["lease_token_digest"] != digest
                )
            ):
                connection.execute("ROLLBACK")
                raise DispatchOutboxError("dispatch lease expired before acknowledgement")
            connection.execute(
                """
                UPDATE dispatch_outbox_v3
                SET state='acknowledged', result_event_id=?, lease_owner=NULL,
                    lease_token_digest=NULL, lease_until=NULL, updated_at=?
                WHERE dispatch_id=?
                """,
                (result.event.event_id, current.isoformat(), lease.dispatch_id),
            )
            connection.execute("COMMIT")

    def counts(self) -> dict[str, int]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT state, COUNT(*) AS count FROM dispatch_outbox_v3 GROUP BY state"
            )
            return {str(row["state"]): int(row["count"]) for row in rows}

    def reconcile_outcomes(self, *, limit: int = 1000) -> int:
        """Project acknowledged transport facts after an acknowledgement crash gap."""

        if not 1 <= limit <= 10_000:
            raise DispatchOutboxError("outcome reconcile limit is invalid")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT d.* FROM dispatch_outbox_v3 d
                LEFT JOIN action_outcomes_v1 o
                  ON o.attempt_id=d.attempt_id
                 AND o.source_event_id=d.result_event_id
                WHERE d.state='acknowledged' AND d.result_event_id IS NOT NULL
                  AND o.outcome_id IS NULL
                ORDER BY d.updated_at, d.dispatch_id LIMIT ?
                """,
                (limit,),
            ).fetchall()
        projection = OutcomeProjection(self.journal, content_vault=self.vault)
        recorded = 0
        for row in rows:
            result = self.journal.get(str(row["result_event_id"]))
            payload = self._authenticated_result_payload(result)
            attempt = self.journal.get(f"action.attempt:{row['attempt_id']}")
            start = self.journal.get(str(row["started_event_id"] or ""))
            start_payload = self._authenticated_start_payload(start)
            if not self._valid_result_evidence(
                result,
                payload,
                attempt,
                start,
                dispatch_id=str(row["dispatch_id"]),
                attempt_id=str(row["attempt_id"]),
                idempotency_key=str(row["idempotency_key"]),
                capability=str(row["capability"]),
                subject=str(row["subject"]),
                sensitivity=Sensitivity(row["sensitivity"]),
                generation=int(row["lease_generation"]),
            ) or not self._valid_start_evidence(
                start,
                start_payload,
                attempt,
                dispatch_id=str(row["dispatch_id"]),
                attempt_id=str(row["attempt_id"]),
                idempotency_key=str(row["idempotency_key"]),
                capability=str(row["capability"]),
                policy_event_id=str(row["policy_event_id"]),
                subject=str(row["subject"]),
                sensitivity=Sensitivity(row["sensitivity"]),
                generation=int(row["lease_generation"]),
            ):
                continue
            outcome_id = "dispatch-result:" + hashlib.sha256(
                result.event.event_id.encode("utf-8")
            ).hexdigest()[:40]
            event = projection.append_outcome(
                attempt_id=str(row["attempt_id"]),
                kind=self.RESULT_KINDS[result.event.event_type],
                source_event_id=result.event.event_id,
                details={
                    "dispatch_id": str(row["dispatch_id"]),
                    "capability": str(row["capability"]),
                    "transport_payload_stored": False,
                },
                actor=result.event.actor,
                subject=str(row["subject"]),
                sensitivity=Sensitivity(row["sensitivity"]),
                outcome_id=outcome_id,
            )
            if projection.apply(event).outcome == "recorded":
                recorded += 1
        return recorded
