"""Typed, evidence-backed memory projection for the Alive kernel."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .content_vault import (
    ContentErasedError,
    ContentExpiredError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _freeze_json, _thaw_json


_PREDICATE_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SUBJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_SENSITIVITY_ORDER = (
    Sensitivity.PUBLIC,
    Sensitivity.INTERNAL,
    Sensitivity.PRIVATE,
    Sensitivity.RESTRICTED,
)


class MemoryValidationError(ValueError):
    """A memory proposal is structurally invalid."""


class MemoryKind(StrEnum):
    EPISODE = "episode"
    FACT = "fact"
    PREFERENCE = "preference"
    COMMITMENT = "commitment"
    SELF_MODEL = "self_model"
    REFLECTION = "reflection"


class MemoryAuthority(StrEnum):
    USER_EXPLICIT = "user_explicit"
    DIRECT_OBSERVATION = "direct_observation"
    SYSTEM_MIGRATION = "system_migration"
    MODEL_INFERENCE = "model_inference"
    REFLECTION = "reflection"


class MemoryState(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    CONTESTED = "contested"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"
    EXPIRED = "expired"


class ProjectionDecisionKind(StrEnum):
    ACTIVATED = "activated"
    PROPOSED = "proposed"
    CONTESTED = "contested"
    DEDUPLICATED = "deduplicated"
    REJECTED = "rejected"
    RETRACTED = "retracted"


class MemoryReview(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    RETRACT = "retract"


class ContentStatus(StrEnum):
    AVAILABLE = "available"
    EXPIRED = "expired"
    ERASED = "erased"
    MISSING = "missing"
    INTEGRITY_ERROR = "integrity_error"


def _utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise MemoryValidationError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MemoryValidationError("memory value must be finite JSON") from exc


def _validate_commitment(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise MemoryValidationError("commitment value must be an object")
    for field in ("promisor", "beneficiary", "condition"):
        if not str(value.get(field) or "").strip():
            raise MemoryValidationError(f"commitment requires {field}")


@dataclass(frozen=True, slots=True)
class MemoryProposal:
    kind: MemoryKind
    subject: str
    predicate: str
    value: Any
    authority: MemoryAuthority
    source_event_ids: tuple[str, ...]
    confidence: float
    importance: float = 0.5
    sensitivity: Sensitivity = Sensitivity.PRIVATE
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    supersedes_id: str | None = None
    proposal_id: str = ""

    def __post_init__(self) -> None:
        try:
            kind = MemoryKind(self.kind)
            authority = MemoryAuthority(self.authority)
            sensitivity = Sensitivity(self.sensitivity)
        except ValueError as exc:
            raise MemoryValidationError("invalid memory enum value") from exc
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "sensitivity", sensitivity)
        subject = str(self.subject).strip()
        predicate = str(self.predicate).strip().lower()
        if not _SUBJECT_RE.fullmatch(subject):
            raise MemoryValidationError("invalid memory subject")
        if not _PREDICATE_RE.fullmatch(predicate):
            raise MemoryValidationError("invalid memory predicate")
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "predicate", predicate)
        confidence = float(self.confidence)
        importance = float(self.importance)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise MemoryValidationError("confidence must be between 0 and 1")
        if not math.isfinite(importance) or not 0.0 <= importance <= 1.0:
            raise MemoryValidationError("importance must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "importance", importance)
        source_ids = tuple(dict.fromkeys(str(item).strip() for item in self.source_event_ids))
        if not source_ids or any(not value for value in source_ids):
            raise MemoryValidationError("at least one source_event_id is required")
        object.__setattr__(self, "source_event_ids", source_ids)
        valid_from = _utc(self.valid_from, "valid_from")
        valid_until = _utc(self.valid_until, "valid_until")
        if valid_from and valid_until and valid_until <= valid_from:
            raise MemoryValidationError("valid_until must be after valid_from")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)
        if kind is MemoryKind.COMMITMENT:
            _validate_commitment(self.value)
        canonical = _canonical_json(self.value)
        object.__setattr__(self, "value", _freeze_json(json.loads(canonical)))
        proposal_id = str(self.proposal_id or uuid4()).strip()
        if not _SUBJECT_RE.fullmatch(proposal_id):
            raise MemoryValidationError("invalid proposal_id")
        object.__setattr__(self, "proposal_id", proposal_id)
        if self.supersedes_id is not None:
            supersedes = str(self.supersedes_id).strip()
            if not _SUBJECT_RE.fullmatch(supersedes):
                raise MemoryValidationError("invalid supersedes_id")
            object.__setattr__(self, "supersedes_id", supersedes)

    def to_payload(self, content: ContentReference) -> dict[str, Any]:
        if content.sensitivity is not self.sensitivity:
            raise MemoryValidationError("content sensitivity does not match proposal")
        return {
            "proposal_id": self.proposal_id,
            "kind": self.kind.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "content": content.to_event_payload(),
            "authority": self.authority.value,
            "source_event_ids": list(self.source_event_ids),
            "confidence": self.confidence,
            "importance": self.importance,
            "sensitivity": self.sensitivity.value,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "supersedes_id": self.supersedes_id,
        }


@dataclass(frozen=True, slots=True)
class StoredMemoryProposal:
    proposal_id: str
    kind: MemoryKind
    subject: str
    predicate: str
    content: ContentReference
    authority: MemoryAuthority
    source_event_ids: tuple[str, ...]
    confidence: float
    importance: float
    sensitivity: Sensitivity
    valid_from: datetime | None
    valid_until: datetime | None
    supersedes_id: str | None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "StoredMemoryProposal":
        def parsed(name: str) -> datetime | None:
            value = payload.get(name)
            return _utc(datetime.fromisoformat(str(value)), name) if value else None

        proposal_id = str(payload.get("proposal_id") or "").strip()
        subject = str(payload["subject"]).strip()
        predicate = str(payload["predicate"]).strip().lower()
        if not _SUBJECT_RE.fullmatch(proposal_id):
            raise MemoryValidationError("invalid proposal_id")
        if not _SUBJECT_RE.fullmatch(subject):
            raise MemoryValidationError("invalid memory subject")
        if not _PREDICATE_RE.fullmatch(predicate):
            raise MemoryValidationError("invalid memory predicate")
        content = ContentReference.from_event_payload(payload.get("content"))
        sensitivity = Sensitivity(payload.get("sensitivity", Sensitivity.PRIVATE.value))
        if content.sensitivity is not sensitivity:
            raise MemoryValidationError("content sensitivity does not match proposal")
        confidence = float(payload["confidence"])
        importance = float(payload.get("importance", 0.5))
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise MemoryValidationError("confidence must be between 0 and 1")
        if not math.isfinite(importance) or not 0.0 <= importance <= 1.0:
            raise MemoryValidationError("importance must be between 0 and 1")
        source_ids = tuple(
            dict.fromkeys(str(item).strip() for item in payload.get("source_event_ids") or ())
        )
        if not source_ids or any(not value for value in source_ids):
            raise MemoryValidationError("at least one source_event_id is required")
        valid_from = parsed("valid_from")
        valid_until = parsed("valid_until")
        if valid_from and valid_until and valid_until <= valid_from:
            raise MemoryValidationError("valid_until must be after valid_from")
        supersedes = payload.get("supersedes_id")
        if supersedes is not None:
            supersedes = str(supersedes).strip()
            if not _SUBJECT_RE.fullmatch(supersedes):
                raise MemoryValidationError("invalid supersedes_id")
        return cls(
            proposal_id=proposal_id,
            kind=MemoryKind(payload["kind"]),
            subject=subject,
            predicate=predicate,
            content=content,
            authority=MemoryAuthority(payload["authority"]),
            source_event_ids=source_ids,
            confidence=confidence,
            importance=importance,
            sensitivity=sensitivity,
            valid_from=valid_from,
            valid_until=valid_until,
            supersedes_id=supersedes,
        )


@dataclass(frozen=True, slots=True)
class ProjectionDecision:
    proposal_event_id: str
    decision: ProjectionDecisionKind
    reason: str
    memory_id: str | None


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    kind: MemoryKind
    subject: str
    predicate: str
    value: Any
    content_id: str
    content_status: ContentStatus
    authority: MemoryAuthority
    state: MemoryState
    confidence: float
    importance: float
    sensitivity: Sensitivity
    source_event_ids: tuple[str, ...]
    valid_from: datetime | None
    valid_until: datetime | None
    supersedes_id: str | None
    created_from_event_id: str
    created_at: datetime
    updated_at: datetime


class MemoryProjection:
    """Idempotent typed-memory projection over an ExperienceJournal."""

    CHECKPOINT = "typed-memory-v2"

    def __init__(
        self, journal: ExperienceJournal, *, content_vault: ContentVault | None = None
    ) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        self.content_vault = content_vault or ContentVault(
            self.path.parent / f"{self.path.stem}-content-vault",
            backup_root=self.path.parent / f"{self.path.stem}-content-backups",
        )
        self._initialize()

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
                CREATE TABLE IF NOT EXISTS memory_records_v2 (
                    memory_id TEXT PRIMARY KEY,
                    proposal_event_id TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    content_digest TEXT NOT NULL,
                    content_size INTEGER NOT NULL,
                    authority TEXT NOT NULL,
                    state TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    importance REAL NOT NULL,
                    sensitivity TEXT NOT NULL,
                    valid_from TEXT,
                    valid_until TEXT,
                    supersedes_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_memory_lookup_v2
                    ON memory_records_v2(subject, predicate, state);
                CREATE TABLE IF NOT EXISTS memory_contents_v2 (
                    memory_id TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    PRIMARY KEY(memory_id, content_id),
                    FOREIGN KEY(memory_id) REFERENCES memory_records_v2(memory_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS memory_sources_v2 (
                    memory_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    PRIMARY KEY(memory_id, event_id),
                    FOREIGN KEY(memory_id) REFERENCES memory_records_v2(memory_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS memory_projection_decisions_v2 (
                    proposal_event_id TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    memory_id TEXT,
                    decided_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_review_decisions_v1 (
                    review_event_id TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    memory_id TEXT,
                    decided_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_transitions_v2 (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    caused_by_event_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(memory_id) REFERENCES memory_records_v2(memory_id)
                        ON DELETE CASCADE
                );
                COMMIT;
                """
            )

    def proposal_event(
        self,
        proposal: MemoryProposal,
        *,
        content: ContentReference,
        actor: str,
        correlation_id: str | None = None,
    ) -> EventEnvelope:
        return EventEnvelope(
            event_id=f"memory.proposal:{proposal.proposal_id}",
            event_type="memory.proposed",
            source="alive.memory",
            actor=actor,
            subject=proposal.subject,
            correlation_id=correlation_id,
            causation_id=proposal.source_event_ids[-1],
            payload=proposal.to_payload(content),
            sensitivity=proposal.sensitivity,
            confidence=proposal.confidence,
        )

    def _append_idempotent_event(self, event: EventEnvelope) -> JournalRecord:
        def compatible(existing: JournalRecord) -> JournalRecord:
            prior = existing.event
            semantic_fields = (
                "event_type",
                "source",
                "actor",
                "subject",
                "correlation_id",
                "causation_id",
                "schema_version",
                "sensitivity",
                "confidence",
                "expires_at",
                "payload",
            )
            if any(getattr(prior, name) != getattr(event, name) for name in semantic_fields):
                raise MemoryValidationError(
                    f"event_id {event.event_id!r} was reused with different semantics"
                )
            return existing

        existing = self.journal.get(event.event_id)
        if existing is not None:
            return compatible(existing)
        try:
            appended = self.journal.append(event)
        except EventConflictError:
            raced = self.journal.get(event.event_id)
            if raced is None:
                raise
            return compatible(raced)
        return JournalRecord(appended.sequence, appended.event)

    def append_proposal(
        self,
        proposal: MemoryProposal,
        *,
        actor: str,
        correlation_id: str | None = None,
    ) -> JournalRecord:
        content_id = f"memory:{proposal.proposal_id}"
        content = self.content_vault.put_json(
            _thaw_json(proposal.value),
            subject=proposal.subject,
            purpose=f"memory.{proposal.kind.value}",
            sensitivity=proposal.sensitivity,
            retention_until=proposal.valid_until,
            content_id=content_id,
        )
        if content.digest != self.content_vault.digest_json(_thaw_json(proposal.value)):
            raise MemoryValidationError("content digest does not match proposal value")
        event = self.proposal_event(
            proposal,
            content=content,
            actor=actor,
            correlation_id=correlation_id,
        )
        # The deterministic content/event IDs make a retry converge after a
        # crash between these two durable writes.  An orphan is encrypted and
        # can be garbage-collected; tombstoning it here would make retry
        # impossible and turn a transient journal failure into data loss.
        return self._append_idempotent_event(event)

    def append_review(
        self,
        memory_id: str,
        *,
        review: MemoryReview,
        subject: str,
        actor: str,
        operation_id: str | None = None,
    ) -> JournalRecord:
        memory_id = str(memory_id).strip()
        subject = str(subject).strip()
        actor = str(actor).strip()
        if not _SUBJECT_RE.fullmatch(memory_id):
            raise MemoryValidationError("invalid memory_id")
        if not _SUBJECT_RE.fullmatch(subject) or actor != subject:
            raise MemoryValidationError("memory review must be self-authorized")
        event = EventEnvelope(
            event_id=f"memory.review:{operation_id or uuid4()}",
            event_type="memory.reviewed",
            source="hermes.command.memory",
            actor=actor,
            subject=subject,
            payload={
                "memory_id": memory_id,
                "review": MemoryReview(review).value,
                "raw_command_stored": False,
            },
            sensitivity=Sensitivity.PRIVATE,
        )
        return self._append_idempotent_event(event)

    def forget_item(
        self, memory_id: str, *, actor: str, request_id: str | None = None
    ) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT subject FROM memory_records_v2 WHERE memory_id=?",
                (memory_id,),
            ).fetchone()
            content_ids = [
                str(item["content_id"])
                for item in connection.execute(
                    "SELECT content_id FROM memory_contents_v2 WHERE memory_id=? ORDER BY content_id",
                    (memory_id,),
                )
            ]
        if row is None:
            return False
        if str(actor).strip() != str(row["subject"]):
            raise MemoryValidationError("memory forgetting must be self-authorized")
        event = EventEnvelope(
            event_id=f"memory.forget:{request_id or uuid4()}",
            event_type="memory.forgotten",
            source="alive.memory",
            actor=actor,
            subject=str(row["subject"]),
            payload={
                "scope": "item",
                "memory_id": str(memory_id),
                "content_ids": content_ids,
                "reason": "user_requested",
            },
            sensitivity=Sensitivity.INTERNAL,
        )
        appended = self._append_idempotent_event(event)
        self._apply_forgetting(appended)
        return True

    def forget_subject(
        self, subject: str, *, actor: str, request_id: str | None = None
    ) -> int:
        subject = str(subject).strip()
        if not _SUBJECT_RE.fullmatch(subject):
            raise MemoryValidationError("invalid memory subject")
        if str(actor).strip() != subject:
            raise MemoryValidationError("memory forgetting must be self-authorized")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT records.memory_id, contents.content_id
                FROM memory_records_v2 AS records
                JOIN memory_contents_v2 AS contents
                  ON contents.memory_id=records.memory_id
                WHERE records.subject=? AND records.state<>?
                ORDER BY records.memory_id, contents.content_id
                """,
                (subject, MemoryState.RETRACTED.value),
            ).fetchall()
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(str(row["memory_id"]), []).append(str(row["content_id"]))
        targets = [
            {"memory_id": memory_id, "content_ids": content_ids}
            for memory_id, content_ids in grouped.items()
        ]
        count = len(grouped)
        event = EventEnvelope(
            event_id=f"memory.forget:{request_id or uuid4()}",
            event_type="memory.forgotten",
            source="alive.memory",
            actor=actor,
            subject=subject,
            payload={
                "scope": "subject",
                "targets": targets,
                "reason": "user_requested",
            },
            sensitivity=Sensitivity.INTERNAL,
        )
        appended = self._append_idempotent_event(event)
        self._apply_forgetting(appended)
        return count

    def project_new(self, *, limit: int = 1000) -> list[ProjectionDecision]:
        after = self.journal.checkpoint(self.CHECKPOINT)
        records = self.journal.read(after_sequence=after, limit=limit)
        decisions: list[ProjectionDecision] = []
        for record in records:
            if record.event.event_type in {"memory.proposed", "memory.reviewed"}:
                decisions.append(self.apply(record))
            elif record.event.event_type == "memory.forgotten":
                self._apply_forgetting(record)
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence, coalesce=True)
        return decisions

    def _apply_forgetting(self, record: JournalRecord) -> None:
        event = record.event
        payload = event.payload
        scope = str(payload.get("scope") or "")
        if (
            event.event_type != "memory.forgotten"
            or event.source != "alive.memory"
            or event.subject is None
            or event.actor != event.subject
            or scope not in {"item", "subject"}
        ):
            raise MemoryValidationError("invalid memory forgetting event")

        def content_ids(value: Any) -> tuple[str, ...]:
            if not isinstance(value, (list, tuple)):
                raise MemoryValidationError("forgotten content_ids must be a list")
            result = tuple(dict.fromkeys(str(item).strip() for item in value))
            if not result or any(not item or len(item) > 255 for item in result):
                raise MemoryValidationError("invalid forgotten content_id")
            return result

        if scope == "item":
            memory_id = str(payload.get("memory_id") or "").strip()
            selected_content_ids = content_ids(payload.get("content_ids"))
            if not _SUBJECT_RE.fullmatch(memory_id):
                raise MemoryValidationError("invalid forgotten item target")
            targets = [(memory_id, selected_content_ids)]
        else:
            subject = str(event.subject or "").strip()
            if not _SUBJECT_RE.fullmatch(subject):
                raise MemoryValidationError("invalid forgotten subject")
            raw_targets = payload.get("targets")
            if not isinstance(raw_targets, (list, tuple)):
                raise MemoryValidationError("forgotten subject targets must be a list")
            targets = []
            for target in raw_targets:
                if not isinstance(target, Mapping):
                    raise MemoryValidationError("invalid forgotten subject target")
                memory_id = str(target.get("memory_id") or "").strip()
                selected_content_ids = content_ids(target.get("content_ids"))
                if not _SUBJECT_RE.fullmatch(memory_id):
                    raise MemoryValidationError("invalid forgotten subject target")
                targets.append((memory_id, selected_content_ids))

        with closing(self._connect()) as connection:
            for memory_id, selected_content_ids in targets:
                row = connection.execute(
                    "SELECT subject FROM memory_records_v2 WHERE memory_id=?",
                    (memory_id,),
                ).fetchone()
                if row is not None:
                    known_ids = {
                        str(item["content_id"])
                        for item in connection.execute(
                            "SELECT content_id FROM memory_contents_v2 WHERE memory_id=?",
                            (memory_id,),
                        )
                    }
                    if row["subject"] != event.subject or not set(selected_content_ids).issubset(known_ids):
                        raise MemoryValidationError(
                            "forgetting target crosses a memory boundary"
                        )

        for _memory_id, selected_content_ids in targets:
            for content_id in selected_content_ids:
                self.content_vault.erase_item(content_id)
        memory_ids = list(dict.fromkeys(memory_id for memory_id, _ids in targets))

        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for memory_id in memory_ids:
                    row = connection.execute(
                        "SELECT state FROM memory_records_v2 WHERE memory_id=?",
                        (memory_id,),
                    ).fetchone()
                    if row is None or row["state"] == MemoryState.RETRACTED.value:
                        continue
                    self._transition(
                        connection,
                        memory_id,
                        MemoryState(row["state"]),
                        MemoryState.RETRACTED,
                        "user_requested_forgetting",
                        event.event_id,
                    )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def rebuild(self, *, batch_size: int = 1000) -> list[ProjectionDecision]:
        """Discard derived state and deterministically replay journal facts."""

        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("DELETE FROM memory_transitions_v2")
                connection.execute("DELETE FROM memory_sources_v2")
                connection.execute("DELETE FROM memory_contents_v2")
                connection.execute("DELETE FROM memory_projection_decisions_v2")
                connection.execute("DELETE FROM memory_review_decisions_v1")
                connection.execute("DELETE FROM memory_records_v2")
                connection.execute(
                    "DELETE FROM consumer_checkpoints WHERE consumer_name=?",
                    (self.CHECKPOINT,),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        decisions: list[ProjectionDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            after = self.journal.checkpoint(self.CHECKPOINT)
            if after <= before:
                raise RuntimeError("memory projection replay made no progress")
        return decisions

    def _existing_decision(self, connection: sqlite3.Connection, event_id: str) -> ProjectionDecision | None:
        row = connection.execute(
            "SELECT * FROM memory_projection_decisions_v2 WHERE proposal_event_id=?",
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return ProjectionDecision(
            proposal_event_id=event_id,
            decision=ProjectionDecisionKind(row["decision"]),
            reason=str(row["reason"]),
            memory_id=row["memory_id"],
        )

    def _decide(
        self,
        connection: sqlite3.Connection,
        event_id: str,
        decision: ProjectionDecisionKind,
        reason: str,
        memory_id: str | None,
    ) -> ProjectionDecision:
        decided_at = self._event_time(connection, event_id)
        connection.execute(
            "INSERT INTO memory_projection_decisions_v2 VALUES (?, ?, ?, ?, ?)",
            (event_id, decision.value, reason, memory_id, decided_at),
        )
        return ProjectionDecision(event_id, decision, reason, memory_id)

    @staticmethod
    def _event_time(connection: sqlite3.Connection, event_id: str) -> str:
        row = connection.execute(
            "SELECT observed_at FROM experience_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise MemoryValidationError(f"missing event time for {event_id!r}")
        return str(row["observed_at"])

    def _sources_exist(self, connection: sqlite3.Connection, ids: Iterable[str]) -> bool:
        for event_id in ids:
            row = connection.execute(
                "SELECT 1 FROM experience_events WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if row is None:
                return False
        return True

    @staticmethod
    def _admitted_state(proposal: StoredMemoryProposal) -> tuple[MemoryState, str]:
        if proposal.authority in {MemoryAuthority.MODEL_INFERENCE, MemoryAuthority.REFLECTION}:
            return MemoryState.PROPOSED, "model_output_requires_review"
        if proposal.authority is MemoryAuthority.DIRECT_OBSERVATION and proposal.kind not in {
            MemoryKind.EPISODE,
            MemoryKind.FACT,
        }:
            return MemoryState.PROPOSED, "observation_cannot_activate_this_memory_kind"
        return MemoryState.ACTIVE, "authority_admitted"

    def apply(self, record: JournalRecord) -> ProjectionDecision:
        event = record.event
        if event.event_type not in {"memory.proposed", "memory.reviewed"}:
            raise MemoryValidationError("unsupported memory projection event")
        if event.event_type == "memory.reviewed":
            return self._apply_review(record)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing_decision = self._existing_decision(connection, event.event_id)
                if existing_decision is not None:
                    connection.execute("COMMIT")
                    return existing_decision
                try:
                    proposal = StoredMemoryProposal.from_payload(event.payload)
                except (KeyError, TypeError, ValueError, MemoryValidationError) as exc:
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.REJECTED,
                        f"invalid_proposal:{type(exc).__name__}",
                        None,
                    )
                    connection.execute("COMMIT")
                    return decision
                if (
                    event.subject != proposal.subject
                    or event.sensitivity is not proposal.sensitivity
                ):
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.REJECTED,
                        "event_proposal_boundary_mismatch",
                        None,
                    )
                    connection.execute("COMMIT")
                    return decision
                if not self._sources_exist(connection, proposal.source_event_ids):
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.REJECTED,
                        "missing_source_event",
                        None,
                    )
                    connection.execute("COMMIT")
                    return decision

                value_hash = proposal.content.digest
                try:
                    resolved_value = self.content_vault.resolve_json(
                        proposal.content.content_id,
                        expected_subject=proposal.subject,
                        expected_purpose=f"memory.{proposal.kind.value}",
                        expected_sensitivity=proposal.sensitivity,
                    )
                    if self.content_vault.digest_json(resolved_value) != value_hash:
                        raise ContentIntegrityError("memory content digest mismatch")
                    if proposal.kind is MemoryKind.COMMITMENT:
                        _validate_commitment(resolved_value)
                except (ContentErasedError, ContentExpiredError):
                    # Preserve structural history without retrieving expired or
                    # erased plaintext, including during projection replay.
                    pass
                except ContentUnavailableError:
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.REJECTED,
                        "content_unavailable_missing",
                        None,
                    )
                    connection.execute("COMMIT")
                    return decision
                except ContentIntegrityError:
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.REJECTED,
                        "content_integrity_error",
                        None,
                    )
                    connection.execute("COMMIT")
                    return decision
                except MemoryValidationError:
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.REJECTED,
                        "invalid_memory_content",
                        None,
                    )
                    connection.execute("COMMIT")
                    return decision
                duplicate = None
                # An explicit supersession is a state-changing correction, not
                # merely additional evidence for a same-valued contested row.
                if proposal.supersedes_id is None:
                    duplicate = connection.execute(
                        """
                        SELECT memory_id, sensitivity FROM memory_records_v2
                        WHERE subject=? AND predicate=? AND content_digest=?
                          AND state IN (?, ?, ?)
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (
                            proposal.subject,
                            proposal.predicate,
                            value_hash,
                            MemoryState.ACTIVE.value,
                            MemoryState.PROPOSED.value,
                            MemoryState.CONTESTED.value,
                        ),
                    ).fetchone()
                if duplicate is not None:
                    memory_id = str(duplicate["memory_id"])
                    existing_sensitivity = Sensitivity(duplicate["sensitivity"])
                    proposal_level = _SENSITIVITY_ORDER.index(proposal.sensitivity)
                    existing_level = _SENSITIVITY_ORDER.index(existing_sensitivity)
                    if proposal_level > existing_level:
                        connection.execute(
                            """
                            UPDATE memory_records_v2
                            SET content_id=?, sensitivity=?, updated_at=?
                            WHERE memory_id=?
                            """,
                            (
                                proposal.content.content_id,
                                proposal.sensitivity.value,
                                self._event_time(connection, event.event_id),
                                memory_id,
                            ),
                        )
                    connection.execute(
                        "INSERT OR IGNORE INTO memory_contents_v2 VALUES (?, ?)",
                        (memory_id, proposal.content.content_id),
                    )
                    for source_id in proposal.source_event_ids:
                        connection.execute(
                            "INSERT OR IGNORE INTO memory_sources_v2 VALUES (?, ?)",
                            (memory_id, source_id),
                        )
                    decision = self._decide(
                        connection,
                        event.event_id,
                        ProjectionDecisionKind.DEDUPLICATED,
                        "same_claim_additional_evidence",
                        memory_id,
                    )
                    connection.execute("COMMIT")
                    return decision

                state, reason = self._admitted_state(proposal)
                now = event.observed_at.isoformat()

                if proposal.supersedes_id:
                    target = connection.execute(
                        "SELECT * FROM memory_records_v2 WHERE memory_id=?",
                        (proposal.supersedes_id,),
                    ).fetchone()
                    authorized = proposal.authority in {
                        MemoryAuthority.USER_EXPLICIT,
                        MemoryAuthority.SYSTEM_MIGRATION,
                    }
                    same_key = target is not None and (
                        target["subject"] == proposal.subject
                        and target["predicate"] == proposal.predicate
                    )
                    target_eligible = target is not None and target["state"] in {
                        MemoryState.ACTIVE.value,
                        MemoryState.CONTESTED.value,
                        MemoryState.PROPOSED.value,
                    }
                    if not authorized or not same_key or not target_eligible:
                        state = MemoryState.PROPOSED
                        reason = "supersession_requires_authorized_matching_target"
                    else:
                        self._transition(
                            connection,
                            str(target["memory_id"]),
                            MemoryState(str(target["state"])),
                            MemoryState.SUPERSEDED,
                            "authorized_correction",
                            event.event_id,
                        )

                conflicts = connection.execute(
                    """
                    SELECT memory_id, state FROM memory_records_v2
                    WHERE subject=? AND predicate=? AND content_digest<>?
                      AND state IN (?, ?)
                    """,
                    (
                        proposal.subject,
                        proposal.predicate,
                        value_hash,
                        MemoryState.ACTIVE.value,
                        MemoryState.CONTESTED.value,
                    ),
                ).fetchall()
                if conflicts and state is MemoryState.ACTIVE and not proposal.supersedes_id:
                    state = MemoryState.CONTESTED
                    reason = "contradictory_claim_requires_resolution"
                    for conflict in conflicts:
                        if conflict["state"] == MemoryState.ACTIVE.value:
                            self._transition(
                                connection,
                                str(conflict["memory_id"]),
                                MemoryState.ACTIVE,
                                MemoryState.CONTESTED,
                                "contradictory_claim",
                                event.event_id,
                            )

                memory_id = proposal.proposal_id
                connection.execute(
                    """
                    INSERT INTO memory_records_v2 VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        memory_id,
                        event.event_id,
                        proposal.kind.value,
                        proposal.subject,
                        proposal.predicate,
                        proposal.content.content_id,
                        value_hash,
                        proposal.content.size_bytes,
                        proposal.authority.value,
                        state.value,
                        proposal.confidence,
                        proposal.importance,
                        proposal.sensitivity.value,
                        proposal.valid_from.isoformat() if proposal.valid_from else None,
                        proposal.valid_until.isoformat() if proposal.valid_until else None,
                        proposal.supersedes_id,
                        now,
                        now,
                    ),
                )
                for source_id in proposal.source_event_ids:
                    connection.execute(
                        "INSERT INTO memory_sources_v2 VALUES (?, ?)",
                        (memory_id, source_id),
                    )
                connection.execute(
                    "INSERT INTO memory_contents_v2 VALUES (?, ?)",
                    (memory_id, proposal.content.content_id),
                )
                connection.execute(
                    """
                    INSERT INTO memory_transitions_v2(
                        memory_id, from_state, to_state, reason,
                        caused_by_event_id, occurred_at
                    ) VALUES (?, NULL, ?, ?, ?, ?)
                    """,
                    (memory_id, state.value, reason, event.event_id, now),
                )
                decision_kind = {
                    MemoryState.ACTIVE: ProjectionDecisionKind.ACTIVATED,
                    MemoryState.PROPOSED: ProjectionDecisionKind.PROPOSED,
                    MemoryState.CONTESTED: ProjectionDecisionKind.CONTESTED,
                    MemoryState.RETRACTED: ProjectionDecisionKind.RETRACTED,
                }[state]
                decision = self._decide(
                    connection,
                    event.event_id,
                    decision_kind,
                    reason,
                    memory_id,
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_review(self, record: JournalRecord) -> ProjectionDecision:
        event = record.event
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                prior = connection.execute(
                    "SELECT * FROM memory_review_decisions_v1 WHERE review_event_id=?",
                    (event.event_id,),
                ).fetchone()
                if prior is not None:
                    connection.execute("COMMIT")
                    return ProjectionDecision(
                        event.event_id,
                        ProjectionDecisionKind(prior["decision"]),
                        str(prior["reason"]),
                        prior["memory_id"],
                    )

                def decide(
                    decision: ProjectionDecisionKind,
                    reason: str,
                    memory_id: str | None,
                ) -> ProjectionDecision:
                    connection.execute(
                        "INSERT INTO memory_review_decisions_v1 VALUES (?, ?, ?, ?, ?)",
                        (
                            event.event_id,
                            decision.value,
                            reason,
                            memory_id,
                            event.observed_at.isoformat(),
                        ),
                    )
                    return ProjectionDecision(event.event_id, decision, reason, memory_id)

                try:
                    memory_id = str(event.payload["memory_id"]).strip()
                    review = MemoryReview(event.payload["review"])
                except (KeyError, ValueError):
                    result = decide(
                        ProjectionDecisionKind.REJECTED, "review_payload_invalid", None
                    )
                    connection.execute("COMMIT")
                    return result
                row = connection.execute(
                    "SELECT * FROM memory_records_v2 WHERE memory_id=?", (memory_id,)
                ).fetchone()
                authorized = (
                    row is not None
                    and event.source == "hermes.command.memory"
                    and event.subject == row["subject"]
                    and event.actor == event.subject
                    and event.payload.get("raw_command_stored") is False
                )
                if not authorized:
                    result = decide(
                        ProjectionDecisionKind.REJECTED,
                        "review_authority_invalid",
                        memory_id if row is not None else None,
                    )
                    connection.execute("COMMIT")
                    return result
                current = MemoryState(row["state"])
                transition = {
                    (MemoryState.PROPOSED, MemoryReview.ACCEPT): MemoryState.ACTIVE,
                    (MemoryState.PROPOSED, MemoryReview.REJECT): MemoryState.RETRACTED,
                    (MemoryState.ACTIVE, MemoryReview.RETRACT): MemoryState.RETRACTED,
                    (MemoryState.CONTESTED, MemoryReview.RETRACT): MemoryState.RETRACTED,
                }.get((current, review))
                if transition is None:
                    result = decide(
                        ProjectionDecisionKind.REJECTED,
                        "invalid_review_transition",
                        memory_id,
                    )
                    connection.execute("COMMIT")
                    return result
                valid_until = row["valid_until"]
                if (
                    review is MemoryReview.ACCEPT
                    and valid_until
                    and event.observed_at >= datetime.fromisoformat(str(valid_until))
                ):
                    result = decide(
                        ProjectionDecisionKind.REJECTED, "memory_expired", memory_id
                    )
                    connection.execute("COMMIT")
                    return result
                self._transition(
                    connection,
                    memory_id,
                    current,
                    transition,
                    f"user_{review.value}",
                    event.event_id,
                )
                decision = (
                    ProjectionDecisionKind.ACTIVATED
                    if transition is MemoryState.ACTIVE
                    else ProjectionDecisionKind.RETRACTED
                )
                result = decide(decision, f"user_{review.value}", memory_id)
                connection.execute("COMMIT")
                return result
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _transition(
        self,
        connection: sqlite3.Connection,
        memory_id: str,
        from_state: MemoryState,
        to_state: MemoryState,
        reason: str,
        event_id: str,
    ) -> None:
        now = self._event_time(connection, event_id)
        connection.execute(
            "UPDATE memory_records_v2 SET state=?, updated_at=? WHERE memory_id=? AND state=?",
            (to_state.value, now, memory_id, from_state.value),
        )
        connection.execute(
            """
            INSERT INTO memory_transitions_v2(
                memory_id, from_state, to_state, reason,
                caused_by_event_id, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (memory_id, from_state.value, to_state.value, reason, event_id, now),
        )

    def retrieve(
        self,
        *,
        subject: str | None = None,
        predicate: str | None = None,
        kinds: Iterable[MemoryKind] | None = None,
        states: Iterable[MemoryState] = (MemoryState.ACTIVE,),
        clearance: Sensitivity,
        as_of: datetime | None = None,
        limit: int = 100,
        include_unavailable: bool = False,
    ) -> list[MemoryRecord]:
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        state_values = tuple(MemoryState(value).value for value in states)
        if not state_values:
            return []
        clauses = ["state IN (" + ",".join("?" for _ in state_values) + ")"]
        parameters: list[Any] = list(state_values)
        clearance_value = Sensitivity(clearance)
        allowed_sensitivities = tuple(
            value.value
            for value in _SENSITIVITY_ORDER[: _SENSITIVITY_ORDER.index(clearance_value) + 1]
        )
        clauses.append(
            "sensitivity IN (" + ",".join("?" for _ in allowed_sensitivities) + ")"
        )
        parameters.extend(allowed_sensitivities)
        if subject is not None:
            clauses.append("subject=?")
            parameters.append(subject)
        if predicate is not None:
            clauses.append("predicate=?")
            parameters.append(predicate)
        if kinds is not None:
            kind_values = tuple(MemoryKind(value).value for value in kinds)
            if not kind_values:
                return []
            clauses.append("kind IN (" + ",".join("?" for _ in kind_values) + ")")
            parameters.extend(kind_values)
        current = _utc(as_of or datetime.now(timezone.utc), "as_of")
        assert current is not None
        current_text = current.isoformat()
        clauses.extend(
            [
                "(valid_from IS NULL OR valid_from<=?)",
                "(valid_until IS NULL OR valid_until>?)",
            ]
        )
        parameters.extend([current_text, current_text, 10_000])
        query = (
            "SELECT * FROM memory_records_v2 WHERE "
            + " AND ".join(clauses)
            + " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        )
        with closing(self._connect()) as connection:
            records: list[MemoryRecord] = []
            for row in connection.execute(query, parameters):
                record = self._record(connection, row)
                if include_unavailable or record.content_status is ContentStatus.AVAILABLE:
                    records.append(record)
                if len(records) >= limit:
                    break
            return records

    def search(
        self,
        query: str,
        *,
        clearance: Sensitivity,
        subject: str | None = None,
        predicate: str | None = None,
        kinds: Iterable[MemoryKind] | None = None,
        states: Iterable[MemoryState] = (MemoryState.ACTIVE,),
        as_of: datetime | None = None,
        limit: int = 20,
        candidate_limit: int = 2000,
    ) -> list["RetrievalHit"]:
        if not 1 <= candidate_limit <= 10_000:
            raise ValueError("candidate_limit must be between 1 and 10000")
        from .retrieval import rank_records

        records = self.retrieve(
            subject=subject,
            predicate=predicate,
            kinds=kinds,
            states=states,
            clearance=clearance,
            as_of=as_of,
            limit=candidate_limit,
        )
        return rank_records(records, query, limit=limit)

    def get(
        self, memory_id: str, *, clearance: Sensitivity
    ) -> MemoryRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM memory_records_v2 WHERE memory_id=?",
                (memory_id,),
            ).fetchone()
            if row is None:
                return None
            clearance_value = Sensitivity(clearance)
            if _SENSITIVITY_ORDER.index(Sensitivity(row["sensitivity"])) > _SENSITIVITY_ORDER.index(clearance_value):
                return None
            return self._record(connection, row)

    def transition_history(self, memory_id: str) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            return [
                {
                    "from_state": row["from_state"],
                    "to_state": row["to_state"],
                    "reason": row["reason"],
                    "caused_by_event_id": row["caused_by_event_id"],
                    "occurred_at": row["occurred_at"],
                }
                for row in connection.execute(
                    """
                    SELECT from_state, to_state, reason, caused_by_event_id, occurred_at
                    FROM memory_transitions_v2 WHERE memory_id=?
                    ORDER BY transition_id
                    """,
                    (memory_id,),
                )
            ]

    def _record(self, connection: sqlite3.Connection, row: sqlite3.Row) -> MemoryRecord:
        sources = tuple(
            str(value["event_id"])
            for value in connection.execute(
                "SELECT event_id FROM memory_sources_v2 WHERE memory_id=? ORDER BY event_id",
                (row["memory_id"],),
            )
        )

        def parsed(name: str) -> datetime | None:
            value = row[name]
            return datetime.fromisoformat(str(value)) if value else None

        created_at = parsed("created_at")
        updated_at = parsed("updated_at")
        if created_at is None or updated_at is None:
            raise MemoryValidationError("memory record is missing durable timestamps")

        content_id = str(row["content_id"])
        try:
            value = self.content_vault.resolve_json(
                content_id,
                expected_subject=str(row["subject"]),
                expected_purpose=f"memory.{row['kind']}",
                expected_sensitivity=Sensitivity(row["sensitivity"]),
            )
            content_status = ContentStatus.AVAILABLE
        except ContentErasedError:
            value = None
            content_status = ContentStatus.ERASED
        except ContentExpiredError:
            value = None
            content_status = ContentStatus.EXPIRED
        except ContentUnavailableError:
            value = None
            content_status = ContentStatus.MISSING
        except ContentIntegrityError:
            value = None
            content_status = ContentStatus.INTEGRITY_ERROR

        return MemoryRecord(
            memory_id=str(row["memory_id"]),
            kind=MemoryKind(row["kind"]),
            subject=str(row["subject"]),
            predicate=str(row["predicate"]),
            value=value,
            content_id=content_id,
            content_status=content_status,
            authority=MemoryAuthority(row["authority"]),
            state=MemoryState(row["state"]),
            confidence=float(row["confidence"]),
            importance=float(row["importance"]),
            sensitivity=Sensitivity(row["sensitivity"]),
            source_event_ids=sources,
            valid_from=parsed("valid_from"),
            valid_until=parsed("valid_until"),
            supersedes_id=row["supersedes_id"],
            created_from_event_id=str(row["proposal_event_id"]),
            created_at=created_at,
            updated_at=updated_at,
        )
