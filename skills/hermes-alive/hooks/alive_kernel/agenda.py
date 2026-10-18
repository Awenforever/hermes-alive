"""Durable commitments and opportunities for the Alive kernel."""

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
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _freeze_json, _thaw_json


_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_SENSITIVITY_ORDER = (
    Sensitivity.PUBLIC,
    Sensitivity.INTERNAL,
    Sensitivity.PRIVATE,
    Sensitivity.RESTRICTED,
)


class AgendaValidationError(ValueError):
    """An agenda command cannot cross the kernel boundary."""


class AgendaItemKind(StrEnum):
    COMMITMENT = "commitment"
    OPPORTUNITY = "opportunity"


class AgendaAuthority(StrEnum):
    USER_EXPLICIT = "user_explicit"
    DIRECT_OBSERVATION = "direct_observation"
    SYSTEM_MIGRATION = "system_migration"
    MODEL_PROPOSAL = "model_proposal"


class AgendaState(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SNOOZED = "snoozed"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class AgendaContentStatus(StrEnum):
    AVAILABLE = "available"
    ERASED = "erased"
    MISSING = "missing"
    INTEGRITY_ERROR = "integrity_error"


def _utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise AgendaValidationError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _identity(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not _IDENTITY_RE.fullmatch(normalized):
        raise AgendaValidationError(f"invalid {name}")
    return normalized


def _json(value: Any) -> Any:
    try:
        return json.loads(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    except (TypeError, ValueError) as exc:
        raise AgendaValidationError("agenda details must be finite JSON") from exc


@dataclass(frozen=True, slots=True)
class AgendaProposal:
    kind: AgendaItemKind
    subject: str
    details: Any
    authority: AgendaAuthority
    source_event_ids: tuple[str, ...]
    confidence: float
    priority: float = 0.5
    sensitivity: Sensitivity = Sensitivity.PRIVATE
    available_at: datetime | None = None
    due_at: datetime | None = None
    expires_at: datetime | None = None
    item_id: str = ""

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "kind", AgendaItemKind(self.kind))
            object.__setattr__(self, "authority", AgendaAuthority(self.authority))
            object.__setattr__(self, "sensitivity", Sensitivity(self.sensitivity))
        except ValueError as exc:
            raise AgendaValidationError("invalid agenda enum value") from exc
        object.__setattr__(self, "subject", _identity(self.subject, "subject"))
        object.__setattr__(self, "item_id", _identity(self.item_id or str(uuid4()), "item_id"))
        sources = tuple(dict.fromkeys(str(value).strip() for value in self.source_event_ids))
        if not sources or any(not value for value in sources):
            raise AgendaValidationError("at least one source_event_id is required")
        object.__setattr__(self, "source_event_ids", sources)
        for name in ("confidence", "priority"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise AgendaValidationError(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, value)
        for name in ("available_at", "due_at", "expires_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.due_at and self.expires_at and self.expires_at < self.due_at:
            raise AgendaValidationError("expires_at must not precede due_at")
        object.__setattr__(self, "details", _freeze_json(_json(self.details)))

    def payload(self, content: ContentReference) -> dict[str, Any]:
        if content.sensitivity is not self.sensitivity:
            raise AgendaValidationError("content sensitivity does not match proposal")
        return {
            "item_id": self.item_id,
            "kind": self.kind.value,
            "subject": self.subject,
            "content": content.to_event_payload(),
            "authority": self.authority.value,
            "source_event_ids": list(self.source_event_ids),
            "confidence": self.confidence,
            "priority": self.priority,
            "sensitivity": self.sensitivity.value,
            "available_at": self.available_at.isoformat() if self.available_at else None,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass(frozen=True, slots=True)
class AgendaRecord:
    item_id: str
    kind: AgendaItemKind
    subject: str
    details: Any
    content_id: str
    content_status: AgendaContentStatus
    authority: AgendaAuthority
    state: AgendaState
    confidence: float
    priority: float
    sensitivity: Sensitivity
    source_event_ids: tuple[str, ...]
    available_at: datetime | None
    due_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AgendaDecision:
    event_id: str
    outcome: str
    reason: str
    item_id: str | None


_ALLOWED_TRANSITIONS = {
    AgendaState.PROPOSED: {AgendaState.ACTIVE, AgendaState.DISMISSED},
    AgendaState.ACTIVE: {
        AgendaState.SNOOZED,
        AgendaState.COMPLETED,
        AgendaState.DISMISSED,
        AgendaState.EXPIRED,
    },
    AgendaState.SNOOZED: {
        AgendaState.ACTIVE,
        AgendaState.COMPLETED,
        AgendaState.DISMISSED,
        AgendaState.EXPIRED,
    },
    AgendaState.COMPLETED: set(),
    AgendaState.DISMISSED: set(),
    AgendaState.EXPIRED: set(),
}


class AgendaProjection:
    """Event-sourced agenda; it does not authorize or execute actions."""

    CHECKPOINT = "alive-agenda-v1"

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
                CREATE TABLE IF NOT EXISTS agenda_items_v1 (
                    item_id TEXT PRIMARY KEY,
                    proposal_event_id TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    state TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    priority REAL NOT NULL,
                    sensitivity TEXT NOT NULL,
                    available_at TEXT,
                    due_at TEXT,
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agenda_due_v1
                    ON agenda_items_v1(state, available_at, due_at);
                CREATE TABLE IF NOT EXISTS agenda_sources_v1 (
                    item_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    PRIMARY KEY(item_id, event_id),
                    FOREIGN KEY(item_id) REFERENCES agenda_items_v1(item_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS agenda_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    item_id TEXT,
                    decided_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agenda_transitions_v1 (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    caused_by_event_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(item_id) REFERENCES agenda_items_v1(item_id)
                        ON DELETE CASCADE
                );
                COMMIT;
                """
            )

    def _append(self, event: EventEnvelope) -> JournalRecord:
        def compatible(existing: JournalRecord) -> JournalRecord:
            fields = (
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
            if any(
                getattr(existing.event, name) != getattr(event, name)
                for name in fields
            ):
                raise AgendaValidationError(
                    f"event_id {event.event_id!r} was reused with different semantics"
                )
            return existing

        existing = self.journal.get(event.event_id)
        if existing is not None:
            return compatible(existing)
        try:
            result = self.journal.append(event)
            return JournalRecord(result.sequence, result.event)
        except EventConflictError:
            existing = self.journal.get(event.event_id)
            if existing is None:
                raise
            return compatible(existing)

    def append_proposal(
        self,
        proposal: AgendaProposal,
        *,
        actor: str,
        correlation_id: str | None = None,
    ) -> JournalRecord:
        content = self.content_vault.put_json(
            _thaw_json(proposal.details),
            subject=proposal.subject,
            purpose=f"agenda.{proposal.kind.value}",
            sensitivity=proposal.sensitivity,
            retention_until=proposal.expires_at,
            content_id=f"agenda:{proposal.item_id}",
        )
        event = EventEnvelope(
            event_id=f"agenda.proposal:{proposal.item_id}",
            event_type="agenda.proposed",
            source="alive.agenda",
            actor=actor,
            subject=proposal.subject,
            correlation_id=correlation_id,
            causation_id=proposal.source_event_ids[-1],
            payload=proposal.payload(content),
            sensitivity=proposal.sensitivity,
            confidence=proposal.confidence,
        )
        return self._append(event)

    def append_transition(
        self,
        item_id: str,
        to_state: AgendaState,
        *,
        actor: str,
        authority: AgendaAuthority,
        source_event_id: str,
        reason: str,
        available_at: datetime | None = None,
        operation_id: str | None = None,
    ) -> JournalRecord:
        item_id = _identity(item_id, "item_id")
        state = AgendaState(to_state)
        authority = AgendaAuthority(authority)
        source_event_id = _identity(source_event_id, "source_event_id")
        available = _utc(available_at, "available_at")
        if state is AgendaState.SNOOZED and available is None:
            raise AgendaValidationError("snoozing requires available_at")
        event = EventEnvelope(
            event_id=_identity(operation_id or str(uuid4()), "operation_id"),
            event_type="agenda.transitioned",
            source="alive.agenda",
            actor=actor,
            subject=None,
            causation_id=source_event_id,
            payload={
                "item_id": item_id,
                "to_state": state.value,
                "authority": authority.value,
                "source_event_id": source_event_id,
                "reason": str(reason).strip()[:256],
                "available_at": available.isoformat() if available else None,
            },
            sensitivity=Sensitivity.INTERNAL,
        )
        return self._append(event)

    @staticmethod
    def _parse_time(value: object, name: str) -> datetime | None:
        if not value:
            return None
        try:
            return _utc(datetime.fromisoformat(str(value)), name)
        except ValueError as exc:
            raise AgendaValidationError(f"invalid {name}") from exc

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        item_id: str | None,
    ) -> AgendaDecision:
        connection.execute(
            "INSERT INTO agenda_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, item_id, event.observed_at.isoformat()),
        )
        return AgendaDecision(event.event_id, outcome, reason, item_id)

    def apply(self, record: JournalRecord) -> AgendaDecision:
        event = record.event
        if event.event_type not in {"agenda.proposed", "agenda.transitioned"}:
            raise AgendaValidationError("unsupported agenda event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM agenda_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return AgendaDecision(
                        event.event_id,
                        str(existing["outcome"]),
                        str(existing["reason"]),
                        existing["item_id"],
                    )
                decision = (
                    self._apply_proposal(connection, event)
                    if event.event_type == "agenda.proposed"
                    else self._apply_transition(connection, event)
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_proposal(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> AgendaDecision:
        payload = event.payload
        try:
            item_id = _identity(str(payload["item_id"]), "item_id")
            kind = AgendaItemKind(payload["kind"])
            subject = _identity(str(payload["subject"]), "subject")
            authority = AgendaAuthority(payload["authority"])
            sensitivity = Sensitivity(payload["sensitivity"])
            content = ContentReference.from_event_payload(payload["content"])
            sources = tuple(str(value) for value in payload["source_event_ids"])
            confidence = float(payload["confidence"])
            priority = float(payload["priority"])
            available_at = self._parse_time(payload.get("available_at"), "available_at")
            due_at = self._parse_time(payload.get("due_at"), "due_at")
            expires_at = self._parse_time(payload.get("expires_at"), "expires_at")
        except (KeyError, TypeError, ValueError, AgendaValidationError) as exc:
            return self._decision(
                connection, event, "rejected", f"invalid_proposal:{type(exc).__name__}", None
            )
        source_records = [self.journal.get(source) for source in sources]
        sources_within_subject = all(
            record is not None and record.event.subject in {None, subject}
            for record in source_records
        )
        authority_valid = sources_within_subject
        if authority is AgendaAuthority.USER_EXPLICIT:
            authority_valid = authority_valid and event.actor == subject and any(
                record is not None
                and record.event.event_type == "conversation.inbound"
                and record.event.actor == subject
                and record.event.subject == subject
                for record in source_records
            )
        elif authority is AgendaAuthority.SYSTEM_MIGRATION:
            authority_valid = (
                authority_valid
                and event.actor.startswith("system:")
                and any(
                    record is not None
                    and record.event.event_type == "system.migration"
                    for record in source_records
                )
            )
        if (
            event.subject != subject
            or event.sensitivity is not sensitivity
            or content.sensitivity is not sensitivity
            or not sources
            or not math.isfinite(confidence)
            or not 0.0 <= confidence <= 1.0
            or not math.isfinite(priority)
            or not 0.0 <= priority <= 1.0
        ):
            return self._decision(connection, event, "rejected", "proposal_boundary_mismatch", None)
        if not authority_valid:
            return self._decision(
                connection, event, "rejected", "proposal_authority_invalid", None
            )
        try:
            self.content_vault.resolve_json(
                content.content_id,
                expected_subject=subject,
                expected_purpose=f"agenda.{kind.value}",
                expected_sensitivity=sensitivity,
            )
        except (ContentUnavailableError, ContentIntegrityError):
            return self._decision(connection, event, "rejected", "content_unavailable", None)
        except ContentErasedError:
            pass
        if connection.execute(
            "SELECT 1 FROM agenda_items_v1 WHERE item_id=?", (item_id,)
        ).fetchone():
            return self._decision(connection, event, "deduplicated", "item_exists", item_id)
        state = AgendaState.ACTIVE
        reason = "authority_admitted"
        if kind is AgendaItemKind.COMMITMENT and authority not in {
            AgendaAuthority.USER_EXPLICIT,
            AgendaAuthority.SYSTEM_MIGRATION,
        }:
            state = AgendaState.PROPOSED
            reason = "commitment_requires_authority"
        now = event.observed_at.isoformat()
        connection.execute(
            """
            INSERT INTO agenda_items_v1 VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                item_id,
                event.event_id,
                kind.value,
                subject,
                content.content_id,
                authority.value,
                state.value,
                confidence,
                priority,
                sensitivity.value,
                available_at.isoformat() if available_at else None,
                due_at.isoformat() if due_at else None,
                expires_at.isoformat() if expires_at else None,
                now,
                now,
            ),
        )
        for source in sources:
            connection.execute("INSERT INTO agenda_sources_v1 VALUES (?, ?)", (item_id, source))
        connection.execute(
            "INSERT INTO agenda_transitions_v1 VALUES (NULL, ?, NULL, ?, ?, ?, ?)",
            (item_id, state.value, reason, event.event_id, now),
        )
        return self._decision(connection, event, state.value, reason, item_id)

    def _apply_transition(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> AgendaDecision:
        payload = event.payload
        try:
            item_id = _identity(str(payload["item_id"]), "item_id")
            to_state = AgendaState(payload["to_state"])
            authority = AgendaAuthority(payload["authority"])
            source_event_id = _identity(
                str(payload["source_event_id"]), "source_event_id"
            )
            reason = str(payload.get("reason") or "state_changed")[:256]
            available_at = self._parse_time(payload.get("available_at"), "available_at")
        except (KeyError, ValueError, AgendaValidationError) as exc:
            return self._decision(
                connection, event, "rejected", f"invalid_transition:{type(exc).__name__}", None
            )
        row = connection.execute(
            "SELECT kind, state, subject FROM agenda_items_v1 WHERE item_id=?",
            (item_id,),
        ).fetchone()
        if row is None:
            return self._decision(connection, event, "rejected", "unknown_item", None)
        from_state = AgendaState(row["state"])
        if to_state not in _ALLOWED_TRANSITIONS[from_state]:
            return self._decision(connection, event, "rejected", "invalid_state_transition", item_id)
        authority_source = self.journal.get(source_event_id)
        if authority_source is None:
            return self._decision(connection, event, "rejected", "missing_authority_source", item_id)
        if authority is AgendaAuthority.USER_EXPLICIT and not (
            authority_source.event.event_type == "conversation.inbound"
            and authority_source.event.actor == event.actor
            and authority_source.event.subject == row["subject"]
        ):
            return self._decision(
                connection, event, "rejected", "invalid_user_authority_source", item_id
            )
        if authority is AgendaAuthority.SYSTEM_MIGRATION and (
            authority_source.event.event_type != "system.migration"
        ):
            return self._decision(
                connection, event, "rejected", "invalid_migration_authority_source", item_id
            )
        if (
            AgendaItemKind(row["kind"]) is AgendaItemKind.COMMITMENT
            and to_state is not AgendaState.EXPIRED
            and authority
            not in {AgendaAuthority.USER_EXPLICIT, AgendaAuthority.SYSTEM_MIGRATION}
        ):
            return self._decision(
                connection, event, "rejected", "commitment_transition_requires_authority", item_id
            )
        if to_state is AgendaState.SNOOZED and available_at is None:
            return self._decision(connection, event, "rejected", "snooze_requires_time", item_id)
        now = event.observed_at.isoformat()
        connection.execute(
            "UPDATE agenda_items_v1 SET state=?, available_at=?, updated_at=? WHERE item_id=?",
            (
                to_state.value,
                available_at.isoformat() if available_at else None,
                now,
                item_id,
            ),
        )
        connection.execute(
            "INSERT INTO agenda_transitions_v1 VALUES (NULL, ?, ?, ?, ?, ?, ?)",
            (item_id, from_state.value, to_state.value, reason, event.event_id, now),
        )
        return self._decision(connection, event, "transitioned", reason, item_id)

    def project_new(self, *, limit: int = 1000) -> list[AgendaDecision]:
        decisions: list[AgendaDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type in {"agenda.proposed", "agenda.transitioned"}:
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence, coalesce=True)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[AgendaDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM agenda_transitions_v1")
            connection.execute("DELETE FROM agenda_sources_v1")
            connection.execute("DELETE FROM agenda_decisions_v1")
            connection.execute("DELETE FROM agenda_items_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        decisions: list[AgendaDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("agenda replay made no progress")
        return decisions

    def list_items(
        self,
        *,
        clearance: Sensitivity,
        states: Iterable[AgendaState] = (AgendaState.ACTIVE, AgendaState.SNOOZED),
        as_of: datetime | None = None,
        limit: int = 100,
        subject: str | None = None,
        kinds: Iterable[AgendaItemKind] | None = None,
        item_ids: Iterable[str] | None = None,
        source_cursor: int | None = None,
    ) -> list[AgendaRecord]:
        clearance = Sensitivity(clearance)
        allowed = _SENSITIVITY_ORDER[: _SENSITIVITY_ORDER.index(clearance) + 1]
        selected_states = tuple(dict.fromkeys(AgendaState(value) for value in states))
        if not selected_states or not 1 <= limit <= 1000:
            raise AgendaValidationError("states and a valid limit are required")
        now = _utc(as_of or datetime.now(timezone.utc), "as_of")
        extra = ""
        extra_parameters: list[Any] = []
        if subject is not None:
            extra += " AND subject=?"
            extra_parameters.append(_identity(subject, "subject"))
        if kinds is not None:
            selected_kinds = tuple(dict.fromkeys(AgendaItemKind(value) for value in kinds))
            if not selected_kinds:
                return []
            extra += f" AND kind IN ({','.join('?' for _ in selected_kinds)})"
            extra_parameters.extend(value.value for value in selected_kinds)
        if item_ids is not None:
            if isinstance(item_ids, (str, bytes)):
                raise AgendaValidationError("item_ids must be a bounded collection")
            selected_ids = tuple(dict.fromkeys(_identity(value, "item_id") for value in item_ids))
            if len(selected_ids) > 32:
                raise AgendaValidationError("too many pinned agenda items")
            if not selected_ids:
                return []
            extra += f" AND item_id IN ({','.join('?' for _ in selected_ids)})"
            extra_parameters.extend(selected_ids)
        order = 'CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC, priority DESC, created_at ASC'
        order_parameters = []
        if source_cursor is not None:
            if (type(source_cursor) is not int or source_cursor < 0 or subject is None
                    or item_ids is not None or kinds is None
                    or selected_kinds!=(AgendaItemKind.OPPORTUNITY,)):
                raise AgendaValidationError('source scan requires an explicit owner/opportunity scope')
            source_sequence = '(SELECT COALESCE(MAX(e.sequence),0) FROM agenda_sources_v1 s JOIN experience_events e ON e.event_id=s.event_id WHERE s.item_id=agenda_items_v1.item_id)'
            # Scope in WHERE, rotate before LIMIT: collector popularity must not
            # permanently hide a lower-priority observation beyond the first page.
            order = f'CASE WHEN {source_sequence}>? THEN 0 ELSE 1 END, {source_sequence}, item_id'
            order_parameters = [source_cursor]
        query = f"""
            SELECT * FROM agenda_items_v1
            WHERE state IN ({','.join('?' for _ in selected_states)})
              AND sensitivity IN ({','.join('?' for _ in allowed)})
              AND (available_at IS NULL OR available_at <= ?)
              AND (expires_at IS NULL OR expires_at > ?)
              {extra}
            ORDER BY {order}
            LIMIT ?
        """
        parameters = [*(value.value for value in selected_states), *(v.value for v in allowed)]
        parameters.extend((now.isoformat(), now.isoformat(), *extra_parameters, *order_parameters, limit))
        with closing(self._connect()) as connection:
            return [self._record(connection, row) for row in connection.execute(query, parameters)]

    def _record(self, connection: sqlite3.Connection, row: sqlite3.Row) -> AgendaRecord:
        sensitivity = Sensitivity(row["sensitivity"])
        try:
            details = self.content_vault.resolve_json(
                str(row["content_id"]),
                expected_subject=str(row["subject"]),
                expected_purpose=f"agenda.{row['kind']}",
                expected_sensitivity=sensitivity,
            )
            content_status = AgendaContentStatus.AVAILABLE
        except ContentErasedError:
            details, content_status = None, AgendaContentStatus.ERASED
        except ContentUnavailableError:
            details, content_status = None, AgendaContentStatus.MISSING
        except ContentIntegrityError:
            details, content_status = None, AgendaContentStatus.INTEGRITY_ERROR
        sources = tuple(
            value["event_id"]
            for value in connection.execute(
                "SELECT event_id FROM agenda_sources_v1 WHERE item_id=? ORDER BY event_id",
                (row["item_id"],),
            )
        )

        def parsed(name: str) -> datetime | None:
            return datetime.fromisoformat(row[name]) if row[name] else None

        created_at = parsed("created_at")
        updated_at = parsed("updated_at")
        if created_at is None or updated_at is None:
            raise AgendaValidationError("agenda item is missing durable timestamps")

        return AgendaRecord(
            item_id=str(row["item_id"]),
            kind=AgendaItemKind(row["kind"]),
            subject=str(row["subject"]),
            details=details,
            content_id=str(row["content_id"]),
            content_status=content_status,
            authority=AgendaAuthority(row["authority"]),
            state=AgendaState(row["state"]),
            confidence=float(row["confidence"]),
            priority=float(row["priority"]),
            sensitivity=sensitivity,
            source_event_ids=sources,
            available_at=parsed("available_at"),
            due_at=parsed("due_at"),
            expires_at=parsed("expires_at"),
            created_at=created_at,
            updated_at=updated_at,
        )
