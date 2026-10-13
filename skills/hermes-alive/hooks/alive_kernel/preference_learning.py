"""Bounded, advisory preference estimates derived from reviewed evidence."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
import math
import re
import sqlite3
from typing import Any
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
from .reflection import ReflectionState, ReflectionProjection


class PreferenceLearningError(ValueError):
    """A learned preference signal violates its evidence boundary."""


class PreferenceAxis(StrEnum):
    TOPIC = "topic"
    TIMING = "timing"
    PRESENTATION = "presentation"
    INTERRUPTION = "interruption"


class PreferenceSignalOrigin(StrEnum):
    EXPLICIT_FEEDBACK = "explicit_feedback"
    ACCEPTED_REFLECTION = "accepted_reflection"


class PreferenceDirection(StrEnum):
    SUPPORT = "support"
    OPPOSE = "oppose"


class PreferenceSignalState(StrEnum):
    ACTIVE = "active"
    RETRACTED = "retracted"


class PreferenceContentStatus(StrEnum):
    AVAILABLE = "available"
    ERASED = "erased"
    MISSING = "missing"
    INTEGRITY_ERROR = "integrity_error"


@dataclass(frozen=True, slots=True)
class PreferenceSignalProposal:
    subject: str
    axis: PreferenceAxis
    key: str
    option: str
    direction: PreferenceDirection
    origin: PreferenceSignalOrigin
    source_id: str
    source_event_id: str
    rationale: str
    weight: float
    expires_at: datetime
    sensitivity: Sensitivity = Sensitivity.PRIVATE
    observation_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis", PreferenceAxis(self.axis))
        object.__setattr__(self, "direction", PreferenceDirection(self.direction))
        object.__setattr__(self, "origin", PreferenceSignalOrigin(self.origin))
        object.__setattr__(self, "sensitivity", Sensitivity(self.sensitivity))
        for name in (
            "subject", "key", "option", "source_id", "source_event_id", "rationale"
        ):
            value = str(getattr(self, name)).strip()
            if not value:
                raise PreferenceLearningError(f"{name} is required")
            object.__setattr__(self, name, value)
        observation_id = str(self.observation_id or uuid4()).strip()
        if not observation_id:
            raise PreferenceLearningError("observation_id is required")
        object.__setattr__(self, "observation_id", observation_id)
        weight = float(self.weight)
        if not math.isfinite(weight) or weight <= 0.0:
            raise PreferenceLearningError("weight must be positive and finite")
        object.__setattr__(self, "weight", weight)
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise PreferenceLearningError("expires_at must be timezone-aware")
        object.__setattr__(self, "expires_at", self.expires_at.astimezone(timezone.utc))


@dataclass(frozen=True, slots=True)
class PreferenceEstimate:
    target_digest: str
    axis: PreferenceAxis | None
    key: str | None
    option: str | None
    content_status: PreferenceContentStatus
    probability: float
    support_mass: float
    opposition_mass: float
    evidence_ids: tuple[str, ...]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PreferenceProjectionDecision:
    event_id: str
    outcome: str
    reason: str
    observation_id: str | None


_ORIGIN_WEIGHT_CAP = {
    PreferenceSignalOrigin.EXPLICIT_FEEDBACK: 0.25,
    PreferenceSignalOrigin.ACCEPTED_REFLECTION: 0.15,
}
_TOTAL_MASS_CAP = 2.0
_MAX_HORIZON = timedelta(days=365)
_SENSITIVITY_ORDER = list(Sensitivity)


class PreferenceLearningProjection:
    CHECKPOINT = "alive-preference-learning-v1"

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
                CREATE TABLE IF NOT EXISTS preference_observations_v1 (
                    observation_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    target_digest TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    weight REAL NOT NULL,
                    expires_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(target_digest, origin, source_id)
                );
                CREATE INDEX IF NOT EXISTS idx_preference_target_v1
                    ON preference_observations_v1(target_digest, state, expires_at);
                CREATE TABLE IF NOT EXISTS preference_learning_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    observation_id TEXT,
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
                raise PreferenceLearningError(
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

    def append_observation(
        self, proposal: PreferenceSignalProposal, *, actor: str
    ) -> JournalRecord:
        target = {
            "axis": proposal.axis.value,
            "key": proposal.key,
            "option": proposal.option,
        }
        target_digest = self.content_vault.digest_json(target)
        content = self.content_vault.put_json(
            {**target, "rationale": proposal.rationale},
            subject=proposal.subject,
            purpose="preference.observation",
            sensitivity=proposal.sensitivity,
            retention_until=proposal.expires_at,
            content_id=f"preference-observation:{proposal.observation_id}",
        )
        event = EventEnvelope(
            event_id=f"preference.observation:{proposal.observation_id}",
            event_type="preference.observed",
            source="alive.preference-learning",
            actor=actor,
            subject=proposal.subject,
            causation_id=proposal.source_event_id,
            sensitivity=proposal.sensitivity,
            expires_at=proposal.expires_at,
            payload={
                "observation_id": proposal.observation_id,
                "target_digest": target_digest,
                "content": content.to_event_payload(),
                "direction": proposal.direction.value,
                "origin": proposal.origin.value,
                "source_id": proposal.source_id,
                "source_event_id": proposal.source_event_id,
                "weight": proposal.weight,
            },
        )
        return self._append_idempotent(event)

    def append_retraction(
        self,
        observation_id: str,
        *,
        source_event_id: str,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        operation_id: str | None = None,
    ) -> JournalRecord:
        event = EventEnvelope(
            event_id=f"preference.retraction:{operation_id or uuid4()}",
            event_type="preference.retracted",
            source="alive.preference-learning",
            actor=actor,
            subject=subject,
            causation_id=source_event_id,
            sensitivity=Sensitivity(sensitivity),
            payload={
                "observation_id": str(observation_id),
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
        observation_id: str | None,
    ) -> PreferenceProjectionDecision:
        connection.execute(
            "INSERT INTO preference_learning_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, observation_id, event.observed_at.isoformat()),
        )
        return PreferenceProjectionDecision(event.event_id, outcome, reason, observation_id)

    def apply(self, record: JournalRecord) -> PreferenceProjectionDecision:
        event = record.event
        if event.event_type not in {"preference.observed", "preference.retracted"}:
            raise PreferenceLearningError("unsupported preference-learning event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM preference_learning_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return PreferenceProjectionDecision(
                        event.event_id,
                        existing["outcome"],
                        existing["reason"],
                        existing["observation_id"],
                    )
                decision = (
                    self._apply_observation(connection, event)
                    if event.event_type == "preference.observed"
                    else self._apply_retraction(connection, event)
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _source_valid(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        origin: PreferenceSignalOrigin,
        source_id: str,
        source_event_id: str,
    ) -> bool:
        if event.causation_id != source_event_id:
            return False
        source_event = self.journal.get(source_event_id)
        observation_event = self.journal.get(event.event_id)
        if (
            source_event is None
            or observation_event is None
            or source_event.sequence >= observation_event.sequence
        ):
            return False
        if origin is PreferenceSignalOrigin.EXPLICIT_FEEDBACK:
            row = connection.execute(
                "SELECT * FROM action_outcomes_v1 WHERE outcome_id=?",
                (source_id,),
            ).fetchone()
            return bool(
                row
                and source_event.event.payload.get("outcome_id") == row["outcome_id"]
                and source_event.event.payload.get("kind") == row["kind"]
                and OutcomeProjection.canonical_evidence_valid_for(self.journal, connection, source_event)
                and row["event_id"] == source_event_id
                and row["subject"] == event.subject
                and _SENSITIVITY_ORDER.index(Sensitivity(row["sensitivity"]))
                <= _SENSITIVITY_ORDER.index(event.sensitivity)
                and row["kind"]
                in {
                    OutcomeKind.EXPLICIT_FEEDBACK.value,
                    OutcomeKind.USER_CORRECTED.value,
                    OutcomeKind.USER_DISMISSED.value,
                }
            )
        row = connection.execute(
            "SELECT * FROM reflections_v1 WHERE reflection_id=?", (source_id,)
        ).fetchone()
        transition = connection.execute(
            """
            SELECT caused_by_event_id FROM reflection_transitions_v1
            WHERE reflection_id=? AND to_state=?
            ORDER BY transition_id DESC LIMIT 1
            """,
            (source_id, ReflectionState.ACCEPTED.value),
        ).fetchone()
        return bool(
            row
            and transition
            and ReflectionProjection.outcome_evidence_valid(self.journal, connection, source_id, event.subject)
            and row["subject"] == event.subject
            and _SENSITIVITY_ORDER.index(Sensitivity(row["sensitivity"]))
            <= _SENSITIVITY_ORDER.index(event.sensitivity)
            and row["state"] == ReflectionState.ACCEPTED.value
            and transition["caused_by_event_id"] == source_event_id
            and datetime.fromisoformat(row["expires_at"]) > event.observed_at
        )

    def _apply_observation(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> PreferenceProjectionDecision:
        payload = event.payload
        observation_id = str(payload.get("observation_id") or "")
        try:
            origin = PreferenceSignalOrigin(payload["origin"])
            direction = PreferenceDirection(payload["direction"])
            source_id = str(payload["source_id"])
            source_event_id = str(payload["source_event_id"])
            target_digest = str(payload["target_digest"])
            weight = float(payload["weight"])
            content = ContentReference.from_event_payload(payload["content"])
        except (KeyError, TypeError, ValueError):
            return self._decision(connection, event, "rejected", "observation_payload_invalid", None)
        if (
            not observation_id
            or not target_digest
            or event.subject is None
            or event.expires_at is None
            or event.expires_at <= event.observed_at
            or event.expires_at - event.observed_at > _MAX_HORIZON
            or not math.isfinite(weight)
            or weight <= 0.0
            or weight > _ORIGIN_WEIGHT_CAP[origin]
            or content.sensitivity is not event.sensitivity
        ):
            return self._decision(
                connection, event, "rejected", "observation_boundary_mismatch", observation_id or None
            )
        if not self._source_valid(
            connection, event, origin, source_id, source_event_id
        ):
            return self._decision(
                connection, event, "rejected", "preference_source_invalid", observation_id
            )
        try:
            details = self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose="preference.observation",
                expected_sensitivity=event.sensitivity,
            )
            recomputed = self.content_vault.digest_json(
                {
                    "axis": details["axis"],
                    "key": details["key"],
                    "option": details["option"],
                }
            )
            PreferenceAxis(details["axis"])
            if recomputed != target_digest:
                raise ContentIntegrityError("preference target digest mismatch")
        except ContentErasedError:
            pass
        except (KeyError, ContentUnavailableError, ContentIntegrityError, ValueError):
            return self._decision(
                connection, event, "rejected", "preference_content_invalid", observation_id
            )
        duplicate = connection.execute(
            """
            SELECT observation_id FROM preference_observations_v1
            WHERE target_digest=? AND origin=? AND source_id=?
            """,
            (target_digest, origin.value, source_id),
        ).fetchone()
        if duplicate is not None:
            return self._decision(
                connection,
                event,
                "deduplicated",
                "source_already_counted",
                duplicate["observation_id"],
            )
        now = event.observed_at.isoformat()
        connection.execute(
            "INSERT INTO preference_observations_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation_id, event.event_id, event.subject, target_digest,
                content.content_id, direction.value, origin.value, source_id,
                source_event_id, weight, event.expires_at.isoformat(),
                PreferenceSignalState.ACTIVE.value, event.sensitivity.value, now, now,
            ),
        )
        return self._decision(
            connection, event, "recorded", "bounded_advisory_signal", observation_id
        )

    def _apply_retraction(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> PreferenceProjectionDecision:
        observation_id = str(event.payload.get("observation_id") or "")
        source_event_id = str(event.payload.get("source_event_id") or "")
        row = connection.execute(
            "SELECT * FROM preference_observations_v1 WHERE observation_id=?",
            (observation_id,),
        ).fetchone()
        source = self.journal.get(source_event_id)
        proposal_event = self.journal.get(str(row["event_id"])) if row else None
        if row is None:
            return self._decision(connection, event, "rejected", "unknown_observation", None)
        if (
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
                connection, event, "rejected", "retraction_authority_invalid", observation_id
            )
        if row["state"] == PreferenceSignalState.RETRACTED.value:
            return self._decision(
                connection, event, "deduplicated", "already_retracted", observation_id
            )
        connection.execute(
            "UPDATE preference_observations_v1 SET state=?, updated_at=? WHERE observation_id=?",
            (PreferenceSignalState.RETRACTED.value, event.observed_at.isoformat(), observation_id),
        )
        return self._decision(connection, event, "retracted", "user_retracted", observation_id)

    def project_new(self, *, limit: int = 1000) -> list[PreferenceProjectionDecision]:
        decisions: list[PreferenceProjectionDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type in {"preference.observed", "preference.retracted"}:
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[PreferenceProjectionDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM preference_learning_decisions_v1")
            connection.execute("DELETE FROM preference_observations_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        decisions: list[PreferenceProjectionDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("preference replay made no progress")
        return decisions

    def estimates(
        self, *, subject: str, clearance: Sensitivity, as_of: datetime | None = None,
    ) -> list[PreferenceEstimate]:
        allowed = list(Sensitivity)[: list(Sensitivity).index(Sensitivity(clearance)) + 1]
        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise PreferenceLearningError("as_of must be timezone-aware")
        placeholders = ",".join("?" for _ in allowed)
        if not isinstance(subject, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}", subject):
            raise PreferenceLearningError("invalid preference estimate subject")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT p.* FROM preference_observations_v1 p
                LEFT JOIN reflections_v1 r
                  ON p.origin=? AND r.reflection_id=p.source_id
                WHERE p.state=? AND p.expires_at>?
                  AND p.sensitivity IN ({placeholders})
                  AND (p.origin<>? OR (r.state=? AND r.expires_at>?))
                  AND p.subject=?
                ORDER BY p.rowid
                """,
                (
                    PreferenceSignalOrigin.ACCEPTED_REFLECTION.value,
                    PreferenceSignalState.ACTIVE.value,
                    current.astimezone(timezone.utc).isoformat(),
                    *(value.value for value in allowed),
                    PreferenceSignalOrigin.ACCEPTED_REFLECTION.value,
                    ReflectionState.ACCEPTED.value,
                    current.astimezone(timezone.utc).isoformat(),
                    subject,
                ),
            ).fetchall()
            grouped: dict[str, list[sqlite3.Row]] = {}
            for row in rows:
                original = self.journal.get(row["event_id"])
                if original is None or original.event.event_type != "preference.observed" or any(
                    original.event.payload.get(field) != row[field]
                    for field in ("observation_id", "origin", "source_id", "source_event_id",
                                  "target_digest", "direction", "weight")
                ) or original.event.subject != row["subject"] or (
                    original.event.expires_at is None
                    or original.event.expires_at.isoformat() != row["expires_at"]
                ):
                    continue
                try:
                    ref = ContentReference.from_event_payload(original.event.payload["content"])
                except (KeyError, ValueError, TypeError):
                    continue
                if (ref.content_id != row["content_id"]
                        or original.event.sensitivity.value != row["sensitivity"]
                        or ref.sensitivity != original.event.sensitivity):
                    continue
                if not self._source_valid(
                    connection, original.event, PreferenceSignalOrigin(row["origin"]),
                    row["source_id"], row["source_event_id"],
                ):
                    continue
                try:
                    retained = self.content_vault.resolve_json(ref.content_id,
                        expected_subject=original.event.subject, expected_purpose="preference.observation",
                        expected_sensitivity=original.event.sensitivity)
                    if (self.content_vault.digest_json(retained) != ref.digest
                            or self.content_vault.digest_json({name: retained[name]
                                for name in ("axis", "key", "option")}) != row["target_digest"]):
                        continue
                except (ContentUnavailableError, ContentIntegrityError, KeyError, ValueError):
                    # Forgotten/unavailable observations cannot contribute hidden
                    # support mass through a still-readable representative.
                    continue
                grouped.setdefault(row["target_digest"], []).append(row)
            estimates: list[PreferenceEstimate] = []
            for target_digest, evidence in sorted(grouped.items()):
                support = min(
                    _TOTAL_MASS_CAP,
                    sum(row["weight"] for row in evidence if row["direction"] == "support"),
                )
                oppose = min(
                    _TOTAL_MASS_CAP,
                    sum(row["weight"] for row in evidence if row["direction"] == "oppose"),
                )
                probability = (2.0 + support) / (4.0 + support + oppose)
                axis = key = option = None
                status = PreferenceContentStatus.ERASED
                unavailable_statuses: set[PreferenceContentStatus] = set()
                for representative in reversed(evidence):
                    sensitivity = Sensitivity(representative["sensitivity"])
                    try:
                        details = self.content_vault.resolve_json(
                            representative["content_id"],
                            expected_subject=representative["subject"],
                            expected_purpose="preference.observation",
                            expected_sensitivity=sensitivity,
                        )
                        target = {name: details[name] for name in ("axis", "key", "option")}
                        if self.content_vault.digest_json(target) != target_digest:
                            raise ContentIntegrityError("preference target digest mismatch")
                        axis = PreferenceAxis(details["axis"])
                        key, option = str(details["key"]), str(details["option"])
                        status = PreferenceContentStatus.AVAILABLE
                        break
                    except ContentErasedError:
                        unavailable_statuses.add(PreferenceContentStatus.ERASED)
                        continue
                    except ContentUnavailableError:
                        unavailable_statuses.add(PreferenceContentStatus.MISSING)
                    except (ContentIntegrityError, KeyError, ValueError):
                        unavailable_statuses.add(PreferenceContentStatus.INTEGRITY_ERROR)
                if axis is None:
                    if PreferenceContentStatus.INTEGRITY_ERROR in unavailable_statuses:
                        status = PreferenceContentStatus.INTEGRITY_ERROR
                    elif PreferenceContentStatus.MISSING in unavailable_statuses:
                        status = PreferenceContentStatus.MISSING
                estimates.append(
                    PreferenceEstimate(
                        target_digest, axis, key, option, status, probability,
                        support, oppose,
                        tuple(row["observation_id"] for row in evidence),
                        max(datetime.fromisoformat(row["expires_at"]) for row in evidence),
                    )
                )
            return estimates
