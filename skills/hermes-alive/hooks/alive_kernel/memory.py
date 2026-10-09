"""Typed, evidence-backed memory projection for the Alive kernel."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .event_store import ExperienceJournal, JournalRecord
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


def _value_hash(value_json: str) -> str:
    return hashlib.sha256(value_json.encode("utf-8")).hexdigest()


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

    @property
    def value_json(self) -> str:
        return _canonical_json(_thaw_json(self.value))

    def to_payload(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "kind": self.kind.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "value": _thaw_json(self.value),
            "authority": self.authority.value,
            "source_event_ids": list(self.source_event_ids),
            "confidence": self.confidence,
            "importance": self.importance,
            "sensitivity": self.sensitivity.value,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "supersedes_id": self.supersedes_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MemoryProposal":
        def parsed(name: str) -> datetime | None:
            value = payload.get(name)
            return datetime.fromisoformat(str(value)) if value else None

        return cls(
            proposal_id=str(payload.get("proposal_id") or ""),
            kind=MemoryKind(payload["kind"]),
            subject=str(payload["subject"]),
            predicate=str(payload["predicate"]),
            value=payload.get("value"),
            authority=MemoryAuthority(payload["authority"]),
            source_event_ids=tuple(payload.get("source_event_ids") or ()),
            confidence=float(payload["confidence"]),
            importance=float(payload.get("importance", 0.5)),
            sensitivity=Sensitivity(payload.get("sensitivity", Sensitivity.PRIVATE.value)),
            valid_from=parsed("valid_from"),
            valid_until=parsed("valid_until"),
            supersedes_id=payload.get("supersedes_id"),
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

    CHECKPOINT = "typed-memory-v1"

    def __init__(self, journal: ExperienceJournal) -> None:
        self.journal = journal
        self.path = Path(journal.path)
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
                CREATE TABLE IF NOT EXISTS memory_records (
                    memory_id TEXT PRIMARY KEY,
                    proposal_event_id TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    value_hash TEXT NOT NULL,
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
                CREATE INDEX IF NOT EXISTS idx_memory_lookup
                    ON memory_records(subject, predicate, state);
                CREATE TABLE IF NOT EXISTS memory_sources (
                    memory_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    PRIMARY KEY(memory_id, event_id),
                    FOREIGN KEY(memory_id) REFERENCES memory_records(memory_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS memory_projection_decisions (
                    proposal_event_id TEXT PRIMARY KEY,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    memory_id TEXT,
                    decided_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memory_transitions (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    caused_by_event_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(memory_id) REFERENCES memory_records(memory_id)
                        ON DELETE CASCADE
                );
                COMMIT;
                """
            )

    def proposal_event(
        self,
        proposal: MemoryProposal,
        *,
        actor: str,
        correlation_id: str | None = None,
    ) -> EventEnvelope:
        return EventEnvelope(
            event_type="memory.proposed",
            source="alive.memory",
            actor=actor,
            subject=proposal.subject,
            correlation_id=correlation_id,
            causation_id=proposal.source_event_ids[-1],
            payload=proposal.to_payload(),
            sensitivity=proposal.sensitivity,
            confidence=proposal.confidence,
        )

    def append_proposal(
        self,
        proposal: MemoryProposal,
        *,
        actor: str,
        correlation_id: str | None = None,
    ) -> JournalRecord:
        event = self.proposal_event(proposal, actor=actor, correlation_id=correlation_id)
        result = self.journal.append(event)
        return JournalRecord(result.sequence, result.event)

    def project_new(self, *, limit: int = 1000) -> list[ProjectionDecision]:
        after = self.journal.checkpoint(self.CHECKPOINT)
        records = self.journal.read(after_sequence=after, limit=limit)
        decisions: list[ProjectionDecision] = []
        for record in records:
            if record.event.event_type == "memory.proposed":
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[ProjectionDecision]:
        """Discard derived state and deterministically replay journal facts."""

        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("DELETE FROM memory_transitions")
                connection.execute("DELETE FROM memory_sources")
                connection.execute("DELETE FROM memory_projection_decisions")
                connection.execute("DELETE FROM memory_records")
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
            "SELECT * FROM memory_projection_decisions WHERE proposal_event_id=?",
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
        connection.execute(
            "INSERT INTO memory_projection_decisions VALUES (?, ?, ?, ?, ?)",
            (event_id, decision.value, reason, memory_id, datetime.now(timezone.utc).isoformat()),
        )
        return ProjectionDecision(event_id, decision, reason, memory_id)

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
    def _admitted_state(proposal: MemoryProposal) -> tuple[MemoryState, str]:
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
        if event.event_type != "memory.proposed":
            raise MemoryValidationError("projection accepts only memory.proposed events")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing_decision = self._existing_decision(connection, event.event_id)
                if existing_decision is not None:
                    connection.execute("COMMIT")
                    return existing_decision
                try:
                    proposal = MemoryProposal.from_payload(event.payload)
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

                value_json = proposal.value_json
                value_hash = _value_hash(value_json)
                duplicate = None
                # An explicit supersession is a state-changing correction, not
                # merely additional evidence for a same-valued contested row.
                if proposal.supersedes_id is None:
                    duplicate = connection.execute(
                        """
                        SELECT memory_id FROM memory_records
                        WHERE subject=? AND predicate=? AND value_hash=?
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
                    for source_id in proposal.source_event_ids:
                        connection.execute(
                            "INSERT OR IGNORE INTO memory_sources VALUES (?, ?)",
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
                now = datetime.now(timezone.utc).isoformat()

                if proposal.supersedes_id:
                    target = connection.execute(
                        "SELECT * FROM memory_records WHERE memory_id=?",
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
                    SELECT memory_id, state FROM memory_records
                    WHERE subject=? AND predicate=? AND value_hash<>?
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
                    INSERT INTO memory_records VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        memory_id,
                        event.event_id,
                        proposal.kind.value,
                        proposal.subject,
                        proposal.predicate,
                        value_json,
                        value_hash,
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
                        "INSERT INTO memory_sources VALUES (?, ?)",
                        (memory_id, source_id),
                    )
                connection.execute(
                    """
                    INSERT INTO memory_transitions(
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

    def _transition(
        self,
        connection: sqlite3.Connection,
        memory_id: str,
        from_state: MemoryState,
        to_state: MemoryState,
        reason: str,
        event_id: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "UPDATE memory_records SET state=?, updated_at=? WHERE memory_id=? AND state=?",
            (to_state.value, now, memory_id, from_state.value),
        )
        connection.execute(
            """
            INSERT INTO memory_transitions(
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
        parameters.extend([current_text, current_text, limit])
        query = (
            "SELECT * FROM memory_records WHERE "
            + " AND ".join(clauses)
            + " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        )
        with closing(self._connect()) as connection:
            return [self._record(connection, row) for row in connection.execute(query, parameters)]

    def get(self, memory_id: str) -> MemoryRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM memory_records WHERE memory_id=?",
                (memory_id,),
            ).fetchone()
            return self._record(connection, row) if row is not None else None

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
                    FROM memory_transitions WHERE memory_id=?
                    ORDER BY transition_id
                    """,
                    (memory_id,),
                )
            ]

    def _record(self, connection: sqlite3.Connection, row: sqlite3.Row) -> MemoryRecord:
        sources = tuple(
            str(value["event_id"])
            for value in connection.execute(
                "SELECT event_id FROM memory_sources WHERE memory_id=? ORDER BY event_id",
                (row["memory_id"],),
            )
        )

        def parsed(name: str) -> datetime | None:
            value = row[name]
            return datetime.fromisoformat(str(value)) if value else None

        return MemoryRecord(
            memory_id=str(row["memory_id"]),
            kind=MemoryKind(row["kind"]),
            subject=str(row["subject"]),
            predicate=str(row["predicate"]),
            value=json.loads(row["value_json"]),
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
            created_at=parsed("created_at") or datetime.now(timezone.utc),
            updated_at=parsed("updated_at") or datetime.now(timezone.utc),
        )
