"""Evidence-backed, expiring, user-reviewable Alive reflections."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import math
from pathlib import Path
import sqlite3
from typing import Any, Iterable
from uuid import uuid4

from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity
from .outcomes import OutcomeKind, OutcomeProjection
from .owner_review import owner_review_source


class ReflectionValidationError(ValueError):
    """A reflection crosses an evidence or authority boundary."""


class ReflectionScope(StrEnum):
    TOPIC = "topic"
    TIMING = "timing"
    PRESENTATION = "presentation"
    INTERRUPTION = "interruption"
    WORKFLOW = "workflow"


class ReflectionAuthority(StrEnum):
    MODEL_SYNTHESIS = "model_synthesis"
    SYSTEM_MIGRATION = "system_migration"


class ReflectionState(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RETRACTED = "retracted"


class ReflectionReview(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    RETRACT = "retract"


_REVIEW_TRANSITIONS = {
    (ReflectionState.PROPOSED, ReflectionReview.ACCEPT): ReflectionState.ACCEPTED,
    (ReflectionState.PROPOSED, ReflectionReview.REJECT): ReflectionState.REJECTED,
    (ReflectionState.ACCEPTED, ReflectionReview.RETRACT): ReflectionState.RETRACTED,
}


class ReflectionContentStatus(StrEnum):
    AVAILABLE = "available"
    ERASED = "erased"
    MISSING = "missing"
    INTEGRITY_ERROR = "integrity_error"


@dataclass(frozen=True, slots=True)
class ReflectionProposal:
    subject: str
    scope: ReflectionScope
    hypothesis: str
    predicted_effect: str
    limitations: tuple[str, ...]
    evidence_outcome_ids: tuple[str, ...]
    confidence: float
    expires_at: datetime
    model: str
    authority: ReflectionAuthority = ReflectionAuthority.MODEL_SYNTHESIS
    sensitivity: Sensitivity = Sensitivity.PRIVATE
    reflection_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", ReflectionScope(self.scope))
        object.__setattr__(self, "authority", ReflectionAuthority(self.authority))
        object.__setattr__(self, "sensitivity", Sensitivity(self.sensitivity))
        for name in ("subject", "hypothesis", "predicted_effect", "model"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ReflectionValidationError(f"{name} is required")
            object.__setattr__(self, name, value)
        reflection_id = str(self.reflection_id or uuid4()).strip()
        if not reflection_id:
            raise ReflectionValidationError("reflection_id is required")
        object.__setattr__(self, "reflection_id", reflection_id)
        evidence = tuple(
            dict.fromkeys(str(value).strip() for value in self.evidence_outcome_ids)
        )
        if not evidence or any(not value for value in evidence):
            raise ReflectionValidationError("reflection requires outcome evidence")
        object.__setattr__(self, "evidence_outcome_ids", evidence)
        limitations = tuple(
            value for value in (str(item).strip() for item in self.limitations) if value
        )
        if not limitations:
            raise ReflectionValidationError("reflection must state limitations")
        object.__setattr__(self, "limitations", limitations)
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ReflectionValidationError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ReflectionValidationError("expires_at must be timezone-aware")
        object.__setattr__(self, "expires_at", self.expires_at.astimezone(timezone.utc))


@dataclass(frozen=True, slots=True)
class ReflectionRecord:
    reflection_id: str
    subject: str
    scope: ReflectionScope
    details: Any
    content_id: str
    content_status: ReflectionContentStatus
    evidence_outcome_ids: tuple[str, ...]
    confidence: float
    expires_at: datetime
    model: str
    authority: ReflectionAuthority
    state: ReflectionState
    sensitivity: Sensitivity
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReflectionProjectionDecision:
    event_id: str
    outcome: str
    reason: str
    reflection_id: str | None


_EXPLICIT_EVIDENCE = {
    OutcomeKind.USER_CORRECTED.value,
    OutcomeKind.USER_DISMISSED.value,
    OutcomeKind.EXPLICIT_FEEDBACK.value,
}
_REPEATED_EVIDENCE = {
    OutcomeKind.TASK_COMPLETED.value,
    OutcomeKind.TASK_FAILED.value,
}


class ReflectionProjection:
    CHECKPOINT = "alive-reflection-v1"
    MAX_HORIZON = timedelta(days=180)

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
                CREATE TABLE IF NOT EXISTS reflections_v1 (
                    reflection_id TEXT PRIMARY KEY,
                    proposal_event_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    expires_at TEXT NOT NULL,
                    model TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    state TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reflection_evidence_v1 (
                    reflection_id TEXT NOT NULL,
                    outcome_id TEXT NOT NULL,
                    PRIMARY KEY(reflection_id, outcome_id),
                    FOREIGN KEY(reflection_id) REFERENCES reflections_v1(reflection_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS reflection_transitions_v1 (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reflection_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    source_event_id TEXT,
                    caused_by_event_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(reflection_id) REFERENCES reflections_v1(reflection_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS reflection_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    reflection_id TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )

    def _append_idempotent(self, event: EventEnvelope) -> JournalRecord:
        def compatible(existing: JournalRecord) -> JournalRecord:
            fields = (
                "event_type", "source", "actor", "subject", "correlation_id",
                "causation_id", "schema_version", "sensitivity", "confidence",
                "expires_at", "payload",
            )
            if any(
                getattr(existing.event, name) != getattr(event, name)
                for name in fields
            ):
                raise ReflectionValidationError(
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

    def append_proposal(self, proposal: ReflectionProposal, *, actor: str) -> JournalRecord:
        content = self.content_vault.put_json(
            {
                "hypothesis": proposal.hypothesis,
                "predicted_effect": proposal.predicted_effect,
                "limitations": list(proposal.limitations),
            },
            subject=proposal.subject,
            purpose=f"reflection.{proposal.scope.value}",
            sensitivity=proposal.sensitivity,
            retention_until=proposal.expires_at,
            content_id=f"reflection:{proposal.reflection_id}",
        )
        event = EventEnvelope(
            event_id=f"reflection.proposal:{proposal.reflection_id}",
            event_type="reflection.proposed",
            source="alive.reflection",
            actor=actor,
            subject=proposal.subject,
            causation_id=f"outcome.record:{proposal.evidence_outcome_ids[-1]}",
            sensitivity=proposal.sensitivity,
            confidence=proposal.confidence,
            expires_at=proposal.expires_at,
            payload={
                "reflection_id": proposal.reflection_id,
                "scope": proposal.scope.value,
                "content": content.to_event_payload(),
                "evidence_outcome_ids": list(proposal.evidence_outcome_ids),
                "model": proposal.model,
                "authority": proposal.authority.value,
            },
        )
        return self._append_idempotent(event)

    def append_review(
        self,
        reflection_id: str,
        review: ReflectionReview,
        *,
        source_event_id: str,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        operation_id: str | None = None,
    ) -> JournalRecord:
        event = EventEnvelope(
            event_id=f"reflection.review:{operation_id or uuid4()}",
            event_type="reflection.reviewed",
            source="alive.reflection",
            actor=actor,
            subject=subject,
            causation_id=source_event_id,
            sensitivity=Sensitivity(sensitivity),
            payload={
                "reflection_id": str(reflection_id),
                "review": ReflectionReview(review).value,
                "source_event_id": str(source_event_id),
            },
        )
        return self._append_idempotent(event)

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        reflection_id: str | None,
    ) -> ReflectionProjectionDecision:
        connection.execute(
            "INSERT INTO reflection_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, reflection_id, event.observed_at.isoformat()),
        )
        return ReflectionProjectionDecision(event.event_id, outcome, reason, reflection_id)

    def apply(self, record: JournalRecord) -> ReflectionProjectionDecision:
        event = record.event
        if event.event_type not in {"reflection.proposed", "reflection.reviewed"}:
            raise ReflectionValidationError("unsupported reflection event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM reflection_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return ReflectionProjectionDecision(
                        event.event_id,
                        existing["outcome"],
                        existing["reason"],
                        existing["reflection_id"],
                    )
                decision = (
                    self._apply_proposal(connection, event)
                    if event.event_type == "reflection.proposed"
                    else self._apply_review(connection, event)
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_proposal(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> ReflectionProjectionDecision:
        payload = event.payload
        reflection_id = str(payload.get("reflection_id") or "")
        try:
            scope = ReflectionScope(payload["scope"])
            authority = ReflectionAuthority(payload["authority"])
            content = ContentReference.from_event_payload(payload["content"])
            evidence_ids = tuple(str(value) for value in payload["evidence_outcome_ids"])
            expires_at = event.expires_at
        except (KeyError, TypeError, ValueError):
            return self._decision(connection, event, "rejected", "proposal_payload_invalid", None)
        if (
            not reflection_id
            or not evidence_ids
            or event.subject is None
            or expires_at is None
            or expires_at <= event.observed_at
            or expires_at - event.observed_at > self.MAX_HORIZON
            or content.sensitivity is not event.sensitivity
            or not str(payload.get("model") or "").strip()
        ):
            return self._decision(
                connection, event, "rejected", "proposal_boundary_mismatch", reflection_id or None
            )
        placeholders = ",".join("?" for _ in evidence_ids)
        evidence = connection.execute(
            f"""
            SELECT o.outcome_id, o.event_id, o.kind, o.subject, o.attempt_id
            FROM action_outcomes_v1 o
            WHERE o.outcome_id IN ({placeholders})
            """,
            evidence_ids,
        ).fetchall()
        if (
            len(evidence_ids) != len(set(evidence_ids))
            or len(evidence) != len(set(evidence_ids))
            or any(
            row["subject"] != event.subject for row in evidence
            )
        ):
            return self._decision(
                connection, event, "rejected", "outcome_evidence_missing", reflection_id
            )
        kinds = {row["kind"] for row in evidence}
        if any(
            (original := self.journal.get(row["event_id"])) is None
            or original.event.payload.get("outcome_id") != row["outcome_id"]
            or original.event.payload.get("kind") != row["kind"]
            or original.event.payload.get("attempt_id") != row["attempt_id"]
            or not OutcomeProjection.canonical_evidence_valid_for(self.journal, connection, original)
            for row in evidence
        ):
            return self._decision(connection, event, "rejected", "outcome_evidence_invalid", reflection_id)
        evidence_events = {row["outcome_id"]: row["event_id"] for row in evidence}
        if event.causation_id != evidence_events[evidence_ids[-1]]:
            return self._decision(
                connection, event, "rejected", "reflection_causation_mismatch", reflection_id
            )
        explicit = bool(kinds & _EXPLICIT_EVIDENCE)
        repeated_attempts = len({row["attempt_id"] for row in evidence}) >= 2
        if not explicit and not (
            kinds and kinds <= _REPEATED_EVIDENCE and repeated_attempts
        ):
            return self._decision(
                connection, event, "rejected", "evidence_insufficient_for_reflection", reflection_id
            )
        if not self._basis_supports_review(self.journal, connection, self.journal.get(event.event_id)):
            return self._decision(connection, event, "rejected", "reflection_basis_invalid", reflection_id)
        try:
            self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose=f"reflection.{scope.value}",
                expected_sensitivity=event.sensitivity,
            )
        except ContentErasedError:
            pass
        except (ContentUnavailableError, ContentIntegrityError):
            return self._decision(
                connection, event, "rejected", "reflection_content_unavailable", reflection_id
            )
        now = event.observed_at.isoformat()
        connection.execute(
            "INSERT INTO reflections_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                reflection_id,
                event.event_id,
                event.subject,
                scope.value,
                content.content_id,
                event.confidence,
                expires_at.isoformat(),
                str(payload.get("model") or ""),
                authority.value,
                ReflectionState.PROPOSED.value,
                event.sensitivity.value,
                now,
                now,
            ),
        )
        for outcome_id in evidence_ids:
            connection.execute(
                "INSERT INTO reflection_evidence_v1 VALUES (?, ?)",
                (reflection_id, outcome_id),
            )
        connection.execute(
            "INSERT INTO reflection_transitions_v1 VALUES (NULL, ?, NULL, ?, ?, NULL, ?, ?)",
            (
                reflection_id,
                ReflectionState.PROPOSED.value,
                "evidence_admitted_for_review",
                event.event_id,
                now,
            ),
        )
        return self._decision(
            connection, event, "proposed", "requires_user_review", reflection_id
        )

    @staticmethod
    def outcome_evidence_valid(journal, connection, reflection_id, subject) -> bool:
        rows = connection.execute(
            "SELECT o.* FROM reflection_evidence_v1 e JOIN action_outcomes_v1 o "
            "ON o.outcome_id=e.outcome_id WHERE e.reflection_id=?", (reflection_id,),
        ).fetchall()
        count = connection.execute(
            "SELECT COUNT(*) FROM reflection_evidence_v1 WHERE reflection_id=?", (reflection_id,),
        ).fetchone()[0]
        if not rows or len(rows) != count:
            return False
        for row in rows:
            original = journal.get(row["event_id"])
            if (
                original is None or original.event.subject != subject or row["subject"] != subject
                or original.event.payload.get("outcome_id") != row["outcome_id"]
                or original.event.payload.get("kind") != row["kind"]
                or original.event.payload.get("attempt_id") != row["attempt_id"]
                or not OutcomeProjection.canonical_evidence_valid_for(journal, connection, original)
            ):
                return False
        return True

    def _apply_review(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> ReflectionProjectionDecision:
        payload = event.payload
        reflection_id = str(payload.get("reflection_id") or "")
        try:
            review = ReflectionReview(payload["review"])
            source_event_id = str(payload["source_event_id"])
        except (KeyError, ValueError):
            return self._decision(connection, event, "rejected", "review_payload_invalid", None)
        row = connection.execute(
            "SELECT * FROM reflections_v1 WHERE reflection_id=?", (reflection_id,)
        ).fetchone()
        source = self.journal.get(source_event_id)
        proposal_event = self.journal.get(str(row["proposal_event_id"])) if row else None
        if row is None:
            return self._decision(connection, event, "rejected", "unknown_reflection", None)
        if (
            owner_review_source(self.journal, event, proposal_event) is None
            or
            source is None
            or proposal_event is None
            or source.sequence <= proposal_event.sequence
            or source.event.event_type != "conversation.inbound"
            or source.event.actor != event.actor
            or source.event.subject != row["subject"]
            or event.subject != row["subject"]
            or event.sensitivity.value != row["sensitivity"]
            or event.causation_id != source_event_id
        ):
            return self._decision(
                connection, event, "rejected", "review_authority_invalid", reflection_id
            )
        canonical = self.verified_state(
            self.journal, connection, reflection_id, event.subject,
            before_sequence=self.journal.get(event.event_id).sequence,
        )
        if canonical is None:
            return self._decision(connection, event, "rejected", "outcome_evidence_invalid", reflection_id)
        current = canonical[0]
        if review is ReflectionReview.ACCEPT and not self.outcome_evidence_valid(
            self.journal, connection, reflection_id, event.subject
        ):
            return self._decision(connection, event, "rejected", "outcome_evidence_invalid", reflection_id)
        transition = _REVIEW_TRANSITIONS.get((current, review))
        if transition is None:
            return self._decision(
                connection, event, "rejected", "invalid_review_transition", reflection_id
            )
        if review is ReflectionReview.ACCEPT and source.event.observed_at >= datetime.fromisoformat(
            row["expires_at"]
        ):
            return self._decision(
                connection, event, "rejected", "reflection_expired", reflection_id
            )
        now = event.observed_at.isoformat()
        connection.execute(
            "UPDATE reflections_v1 SET state=?, updated_at=? WHERE reflection_id=?",
            (transition.value, now, reflection_id),
        )
        connection.execute(
            "INSERT INTO reflection_transitions_v1 VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
            (
                reflection_id,
                current.value,
                transition.value,
                f"user_{review.value}",
                source_event_id,
                event.event_id,
                now,
            ),
        )
        return self._decision(connection, event, transition.value, f"user_{review.value}", reflection_id)

    @staticmethod
    def _basis_supports_review(journal, connection, proposal):
        if proposal is None:
            return False
        event = proposal.event
        ids = tuple(event.payload.get("evidence_outcome_ids", ()))
        if not ids or len(ids) != len(set(ids)):
            return False
        records = [journal.get(f"outcome.record:{item}") for item in ids]
        if any(
            record is None or record.sequence >= proposal.sequence
            or record.event.observed_at > event.observed_at
            or record.event.subject != event.subject
            or list(Sensitivity).index(record.event.sensitivity) > list(Sensitivity).index(event.sensitivity)
            or not OutcomeProjection.canonical_evidence_valid_for(journal, connection, record)
            for record in records
        ):
            return False
        kinds = {record.event.payload["kind"] for record in records}
        repeated = len({record.event.payload["attempt_id"] for record in records}) >= 2
        return bool(
            event.causation_id == records[-1].event.event_id
            and (kinds & _EXPLICIT_EVIDENCE or (kinds <= _REPEATED_EVIDENCE and repeated))
        )

    @staticmethod
    def verified_state(journal, connection, reflection_id, subject, *, before_sequence=None):
        """Recover owner control from immutable reviews, including pending retracts.

        Materialized states/transitions are recovery aids, not approval evidence.
        Return (state, latest valid review event id), or None for an invalid basis.
        This reads no private prose and grants no permission to act.
        """
        row = connection.execute("SELECT * FROM reflections_v1 WHERE reflection_id=?",
                                 (reflection_id,)).fetchone()
        proposal = journal.get(row["proposal_event_id"]) if row else None
        if proposal is None or proposal.event.event_type != "reflection.proposed":
            return None
        event = proposal.event
        try:
            reference = ContentReference.from_event_payload(event.payload["content"])
            ReflectionScope(event.payload["scope"])
            ReflectionAuthority(event.payload["authority"])
            evidence = {item[0] for item in connection.execute(
                "SELECT outcome_id FROM reflection_evidence_v1 WHERE reflection_id=?", (reflection_id,))}
            if (
                event.subject != subject or row["subject"] != subject
                or event.payload.get("reflection_id") != reflection_id
                or any(event.payload.get(field) != row[field] for field in ("scope", "model", "authority"))
                or reference.content_id != row["content_id"]
                or reference.sensitivity != event.sensitivity
                or event.sensitivity.value != row["sensitivity"]
                or event.confidence != row["confidence"]
                or event.expires_at is None or event.expires_at.isoformat() != row["expires_at"]
                or event.expires_at <= event.observed_at
                or event.expires_at - event.observed_at > ReflectionProjection.MAX_HORIZON
                or event.observed_at.isoformat() != row["created_at"]
                or evidence != set(event.payload["evidence_outcome_ids"])
                or not ReflectionProjection.outcome_evidence_valid(journal, connection, reflection_id, subject)
                or not ReflectionProjection._basis_supports_review(journal, connection, proposal)
            ):
                return None
        except (KeyError, TypeError, ValueError):
            return None
        state, latest = ReflectionState.PROPOSED, None
        reviews = connection.execute(
            "SELECT event_id FROM experience_events WHERE subject=? AND event_type='reflection.reviewed' "
            "AND sequence>? AND (? IS NULL OR sequence<?) "
            "AND json_extract(canonical_json, '$.payload.reflection_id')=? ORDER BY sequence",
            (subject, proposal.sequence, before_sequence, before_sequence, reflection_id),
        ).fetchall()
        for item in reviews:
            record = journal.get(item["event_id"])
            if record is None or owner_review_source(journal, record.event, proposal) is None:
                continue
            try:
                review = ReflectionReview(record.event.payload["review"])
            except (KeyError, ValueError):
                continue
            transition = _REVIEW_TRANSITIONS.get((state, review))
            if transition is None or (review is ReflectionReview.ACCEPT and
                                      record.event.observed_at >= event.expires_at):
                continue
            state, latest = transition, record.event.event_id
        return state, latest

    def project_new(self, *, limit: int = 1000) -> list[ReflectionProjectionDecision]:
        decisions: list[ReflectionProjectionDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type in {"reflection.proposed", "reflection.reviewed"}:
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence, coalesce=True)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[ReflectionProjectionDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM reflection_transitions_v1")
            connection.execute("DELETE FROM reflection_evidence_v1")
            connection.execute("DELETE FROM reflection_decisions_v1")
            connection.execute("DELETE FROM reflections_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        decisions: list[ReflectionProjectionDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("reflection replay made no progress")
        return decisions

    def list_reflections(
        self,
        *,
        clearance: Sensitivity,
        states: Iterable[ReflectionState] = (
            ReflectionState.PROPOSED,
            ReflectionState.ACCEPTED,
        ),
        as_of: datetime | None = None,
    ) -> list[ReflectionRecord]:
        allowed = list(Sensitivity)[: list(Sensitivity).index(Sensitivity(clearance)) + 1]
        selected_states = tuple(dict.fromkeys(ReflectionState(value) for value in states))
        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ReflectionValidationError("as_of must be timezone-aware")
        placeholders_sensitivity = ",".join("?" for _ in allowed)
        parameters = [value.value for value in allowed]
        parameters.append(current.astimezone(timezone.utc).isoformat())
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM reflections_v1
                WHERE 1=1
                  AND sensitivity IN ({placeholders_sensitivity})
                  AND expires_at > ?
                ORDER BY created_at, reflection_id
                """,
                parameters,
            ).fetchall()
            records: list[ReflectionRecord] = []
            for row in rows:
                verified = self.verified_state(self.journal, connection, row["reflection_id"], row["subject"])
                if verified is None or verified[0] not in selected_states:
                    continue
                latest = self.journal.get(verified[1] or row["proposal_event_id"])
                sensitivity = Sensitivity(row["sensitivity"])
                try:
                    details = self.content_vault.resolve_json(
                        row["content_id"],
                        expected_subject=row["subject"],
                        expected_purpose=f"reflection.{row['scope']}",
                        expected_sensitivity=sensitivity,
                    )
                    status = ReflectionContentStatus.AVAILABLE
                except ContentErasedError:
                    details, status = None, ReflectionContentStatus.ERASED
                except ContentUnavailableError:
                    details, status = None, ReflectionContentStatus.MISSING
                except ContentIntegrityError:
                    details, status = None, ReflectionContentStatus.INTEGRITY_ERROR
                evidence = tuple(
                    item["outcome_id"]
                    for item in connection.execute(
                        "SELECT outcome_id FROM reflection_evidence_v1 WHERE reflection_id=? ORDER BY outcome_id",
                        (row["reflection_id"],),
                    )
                )
                records.append(
                    ReflectionRecord(
                        row["reflection_id"], row["subject"], ReflectionScope(row["scope"]),
                        details, row["content_id"], status, evidence, float(row["confidence"]),
                        datetime.fromisoformat(row["expires_at"]), row["model"],
                        ReflectionAuthority(row["authority"]), verified[0],
                        sensitivity, datetime.fromisoformat(row["created_at"]),
                        latest.event.observed_at,
                    )
                )
            return records
