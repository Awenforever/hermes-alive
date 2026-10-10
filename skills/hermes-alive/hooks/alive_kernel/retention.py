"""Explicit, replayable consent for erasable conversation retention."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
import sqlite3
from typing import Iterable
from uuid import uuid4

from .content_vault import ContentVault, ErasureResult
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity


class RetentionValidationError(ValueError):
    """A retention request violates the explicit-consent boundary."""


class RetentionDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    subject: str
    enabled: bool
    retention_days: int
    directions: frozenset[RetentionDirection]
    sensitivity: Sensitivity
    consent_event_id: str
    updated_at: datetime

    def allows(self, direction: RetentionDirection) -> bool:
        return self.enabled and RetentionDirection(direction) in self.directions


@dataclass(frozen=True, slots=True)
class RetentionProjectionDecision:
    event_id: str
    outcome: str
    reason: str
    subject: str | None


class RetentionProjection:
    """Projects user-issued retention consent; default state is always off."""

    CHECKPOINT = "alive-retention-v1"
    MIN_DAYS = 1
    MAX_DAYS = 365

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        self.content_vault = content_vault or ContentVault(
            self.path.parent / "content-vault",
            backup_root=self.path.parent / "content-backups",
        )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS retention_policies_v1 (
                    subject TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL,
                    retention_days INTEGER NOT NULL,
                    directions TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    consent_event_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS retention_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    subject TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )

    @staticmethod
    def _directions(values: Iterable[RetentionDirection | str]) -> frozenset[RetentionDirection]:
        directions = frozenset(RetentionDirection(value) for value in values)
        if not directions:
            raise RetentionValidationError("at least one retention direction is required")
        return directions

    def append_consent(
        self,
        *,
        subject: str,
        enabled: bool,
        retention_days: int,
        directions: Iterable[RetentionDirection | str],
        sensitivity: Sensitivity,
        actor: str,
        operation_id: str | None = None,
    ) -> JournalRecord:
        subject = str(subject).strip()
        actor = str(actor).strip()
        days = int(retention_days)
        resolved_directions = self._directions(directions)
        sensitivity = Sensitivity(sensitivity)
        if not subject or actor != subject:
            raise RetentionValidationError("retention consent must be self-authorized")
        if not self.MIN_DAYS <= days <= self.MAX_DAYS:
            raise RetentionValidationError("retention_days is outside the supported boundary")
        if sensitivity not in {Sensitivity.PRIVATE, Sensitivity.RESTRICTED}:
            raise RetentionValidationError("retained conversation must be private or restricted")
        event = EventEnvelope(
            event_id=f"retention.consent:{operation_id or uuid4()}",
            event_type="retention.consent_changed",
            source="hermes.command.memory",
            actor=actor,
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            payload={
                "enabled": bool(enabled),
                "retention_days": days,
                "directions": sorted(value.value for value in resolved_directions),
                "content_sensitivity": sensitivity.value,
                "raw_command_stored": False,
            },
        )
        existing = self.journal.get(event.event_id)
        if existing is not None:
            fields = (
                "event_type", "source", "actor", "subject", "sensitivity", "payload"
            )
            if any(
                getattr(existing.event, name) != getattr(event, name) for name in fields
            ):
                raise RetentionValidationError("operation_id was reused with different consent")
            return existing
        try:
            result = self.journal.append(event)
            return JournalRecord(result.sequence, result.event)
        except EventConflictError as exc:
            raise RetentionValidationError("conflicting retention consent event") from exc

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
    ) -> RetentionProjectionDecision:
        connection.execute(
            "INSERT INTO retention_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, event.subject, event.observed_at.isoformat()),
        )
        return RetentionProjectionDecision(event.event_id, outcome, reason, event.subject)

    def apply(self, record: JournalRecord) -> RetentionProjectionDecision:
        event = record.event
        if event.event_type != "retention.consent_changed":
            raise RetentionValidationError("unsupported retention event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM retention_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return RetentionProjectionDecision(
                        event.event_id, existing["outcome"], existing["reason"],
                        existing["subject"],
                    )
                if (
                    event.source != "hermes.command.memory"
                    or event.subject is None
                    or event.actor != event.subject
                ):
                    decision = self._decision(
                        connection, event, "rejected", "consent_authority_invalid"
                    )
                    connection.execute("COMMIT")
                    return decision
                try:
                    enabled_value = event.payload["enabled"]
                    if not isinstance(enabled_value, bool):
                        raise TypeError("enabled must be boolean")
                    enabled = enabled_value
                    days = int(event.payload["retention_days"])
                    directions = self._directions(event.payload["directions"])
                    sensitivity = Sensitivity(event.payload["content_sensitivity"])
                except (KeyError, TypeError, ValueError):
                    decision = self._decision(
                        connection, event, "rejected", "consent_payload_invalid"
                    )
                    connection.execute("COMMIT")
                    return decision
                if (
                    not self.MIN_DAYS <= days <= self.MAX_DAYS
                    or sensitivity not in {Sensitivity.PRIVATE, Sensitivity.RESTRICTED}
                    or event.payload.get("raw_command_stored") is not False
                ):
                    decision = self._decision(
                        connection, event, "rejected", "consent_boundary_invalid"
                    )
                    connection.execute("COMMIT")
                    return decision
                connection.execute(
                    """
                    INSERT INTO retention_policies_v1 VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(subject) DO UPDATE SET
                        enabled=excluded.enabled,
                        retention_days=excluded.retention_days,
                        directions=excluded.directions,
                        sensitivity=excluded.sensitivity,
                        consent_event_id=excluded.consent_event_id,
                        updated_at=excluded.updated_at
                    """,
                    (
                        event.subject, int(enabled), days,
                        ",".join(sorted(value.value for value in directions)),
                        sensitivity.value, event.event_id, event.observed_at.isoformat(),
                    ),
                )
                decision = self._decision(
                    connection, event, "recorded", "explicit_user_consent"
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def policy(self, subject: str) -> RetentionPolicy | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM retention_policies_v1 WHERE subject=?", (str(subject),)
            ).fetchone()
        if row is None:
            return None
        return RetentionPolicy(
            str(row["subject"]), bool(row["enabled"]), int(row["retention_days"]),
            frozenset(RetentionDirection(value) for value in str(row["directions"]).split(",")),
            Sensitivity(row["sensitivity"]), str(row["consent_event_id"]),
            datetime.fromisoformat(str(row["updated_at"])),
        )

    def erase_subject(self, subject: str) -> ErasureResult:
        return self.content_vault.erase_subject(str(subject))

    def append_erasure_request(
        self,
        *,
        subject: str,
        actor: str,
        operation_id: str | None = None,
    ) -> JournalRecord:
        subject = str(subject).strip()
        actor = str(actor).strip()
        if not subject or actor != subject:
            raise RetentionValidationError("content erasure must be self-authorized")
        event = EventEnvelope(
            event_id=f"retention.erasure.request:{operation_id or uuid4()}",
            event_type="retention.erasure_requested",
            source="hermes.command.memory",
            actor=actor,
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            payload={"scope": "subject", "raw_command_stored": False},
        )
        existing = self.journal.get(event.event_id)
        if existing is not None:
            return existing
        result = self.journal.append(event)
        return JournalRecord(result.sequence, result.event)

    @staticmethod
    def completion_event_id(request_event_id: str) -> str:
        return f"retention.erasure.completed:{request_event_id.rsplit(':', 1)[-1]}"

    def execute_erasure(self, request: JournalRecord) -> tuple[ErasureResult, JournalRecord]:
        event = request.event
        if (
            event.event_type != "retention.erasure_requested"
            or event.source != "hermes.command.memory"
            or event.subject is None
            or event.actor != event.subject
            or event.payload.get("scope") != "subject"
        ):
            raise RetentionValidationError("invalid erasure request authority")
        completion_id = self.completion_event_id(event.event_id)
        existing = self.journal.get(completion_id)
        if existing is not None:
            payload = existing.event.payload
            return (
                ErasureResult(
                    int(payload.get("requested", 0)),
                    int(payload.get("newly_erased", 0)),
                    int(payload.get("managed_backups_removed", 0)),
                    bool(payload.get("already_erased", True)),
                ),
                existing,
            )
        result = self.content_vault.erase_subject(event.subject)
        completion = EventEnvelope(
            event_id=completion_id,
            event_type="retention.erasure_completed",
            source="alive.retention",
            actor="system:alive",
            subject=event.subject,
            causation_id=event.event_id,
            sensitivity=Sensitivity.PRIVATE,
            payload={
                "scope": "subject",
                "requested": result.requested,
                "newly_erased": result.newly_erased,
                "managed_backups_removed": result.managed_backups_removed,
                "already_erased": result.already_erased,
            },
        )
        appended = self.journal.append(completion)
        return result, JournalRecord(appended.sequence, appended.event)

    def resume_pending_erasures(self) -> int:
        resumed = 0
        cursor = 0
        while True:
            requests = self.journal.read(
                after_sequence=cursor,
                limit=1000,
                event_type="retention.erasure_requested",
            )
            if not requests:
                break
            for record in requests:
                if self.journal.get(self.completion_event_id(record.event.event_id)) is None:
                    self.execute_erasure(record)
                    resumed += 1
            cursor = requests[-1].sequence
        return resumed

    def project_new(self, *, limit: int = 1000) -> list[RetentionProjectionDecision]:
        decisions: list[RetentionProjectionDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type == "retention.consent_changed":
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[RetentionProjectionDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM retention_policies_v1")
            connection.execute("DELETE FROM retention_decisions_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        decisions: list[RetentionProjectionDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("retention replay made no progress")
        return decisions
