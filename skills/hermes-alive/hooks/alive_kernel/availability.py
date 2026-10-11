"""Evidence-backed user availability, separate from Alive presentation rhythm."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hmac
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SCOPE_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_DIRECT_MAX = timedelta(hours=1)
_EXPLICIT_MAX = timedelta(days=30)
_POLICY_MAX = timedelta(days=7)


class AvailabilityError(ValueError):
    """Availability evidence violated its authority or lifetime boundary."""


class AvailabilityStance(StrEnum):
    BLOCK = "block"
    ALLOW = "allow"
    UNKNOWN = "unknown"


class AvailabilityBasis(StrEnum):
    USER_EXPLICIT = "user_explicit"
    DIRECT_ACTIVITY = "direct_activity"
    SYSTEM_POLICY = "system_policy"


class AvailabilityState(StrEnum):
    BLOCKED = "blocked"
    EXPLICITLY_AVAILABLE = "explicitly_available"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AvailabilitySignal:
    subject: str
    stance: AvailabilityStance
    basis: AvailabilityBasis
    reason_code: str
    valid_from: datetime
    valid_until: datetime
    confidence: float
    scope: str = "proactive_social"
    source_event_id: str | None = None
    signal_id: str = ""

    def __post_init__(self) -> None:
        subject = str(self.subject).strip()
        signal_id = str(self.signal_id).strip()
        source = str(self.source_event_id or "").strip() or None
        scope = str(self.scope).strip().lower()
        reason = str(self.reason_code).strip().lower()
        if not _ID_RE.fullmatch(subject):
            raise AvailabilityError("invalid subject")
        if signal_id and not _ID_RE.fullmatch(signal_id):
            raise AvailabilityError("invalid signal_id")
        if source is not None and not _ID_RE.fullmatch(source):
            raise AvailabilityError("invalid source_event_id")
        if not _SCOPE_RE.fullmatch(scope) or not _REASON_RE.fullmatch(reason):
            raise AvailabilityError("invalid availability scope or reason")
        start = _utc(self.valid_from, "valid_from")
        end = _utc(self.valid_until, "valid_until")
        if end <= start:
            raise AvailabilityError("valid_until must follow valid_from")
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise AvailabilityError("confidence must be between 0 and 1")
        basis = AvailabilityBasis(self.basis)
        stance = AvailabilityStance(self.stance)
        maximum = {
            AvailabilityBasis.DIRECT_ACTIVITY: _DIRECT_MAX,
            AvailabilityBasis.USER_EXPLICIT: _EXPLICIT_MAX,
            AvailabilityBasis.SYSTEM_POLICY: _POLICY_MAX,
        }[basis]
        if end - start > maximum:
            raise AvailabilityError("availability evidence exceeds its maximum lifetime")
        if basis is AvailabilityBasis.DIRECT_ACTIVITY and stance is AvailabilityStance.ALLOW:
            raise AvailabilityError("absence of activity cannot grant availability")
        if basis is AvailabilityBasis.USER_EXPLICIT and source is None:
            raise AvailabilityError("explicit availability requires its inbound event")
        if basis is AvailabilityBasis.SYSTEM_POLICY and source is None:
            raise AvailabilityError("system policy requires its authority event")
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "signal_id", signal_id)
        object.__setattr__(self, "source_event_id", source)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "reason_code", reason)
        object.__setattr__(self, "valid_from", start)
        object.__setattr__(self, "valid_until", end)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "stance", stance)


@dataclass(frozen=True, slots=True)
class AvailabilityDecision:
    event_id: str
    outcome: str
    reason: str
    signal_id: str | None


@dataclass(frozen=True, slots=True)
class AvailabilityAssessment:
    subject: str
    scope: str
    state: AvailabilityState
    confidence: float
    reason_codes: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    valid_until: datetime | None

    @property
    def permits_action(self) -> bool:
        """Availability is context evidence, never action authority."""

        return False


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AvailabilityError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


class AvailabilityProjection:
    """Project bounded availability signals without consulting Circadian state."""

    CHECKPOINT = "alive-availability-v1"

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        protector: LocalIdentityProtector | None = None,
    ) -> None:
        self.journal = journal
        self.protector = protector or LocalIdentityProtector(
            journal.path.parent / "identity.key"
        )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.journal.path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS availability_projection_v1 (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    signal_count INTEGER NOT NULL,
                    count_authenticator TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO availability_projection_v1
                    (singleton, signal_count, count_authenticator, updated_at)
                VALUES (1, 0, '', '1970-01-01T00:00:00+00:00');
                CREATE TABLE IF NOT EXISTS availability_signals_v1 (
                    signal_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    stance TEXT NOT NULL,
                    basis TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    source_event_id TEXT,
                    confidence REAL NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_availability_active_v1
                    ON availability_signals_v1(subject, scope, valid_until);
                CREATE TABLE IF NOT EXISTS availability_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    signal_id TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )
            metadata = connection.execute(
                "SELECT signal_count, count_authenticator FROM availability_projection_v1 "
                "WHERE singleton=1"
            ).fetchone()
            if metadata is not None and not str(metadata["count_authenticator"]):
                count = int(metadata["signal_count"])
                connection.execute(
                    "UPDATE availability_projection_v1 SET count_authenticator=? "
                    "WHERE singleton=1",
                    (self._count_authenticator(count),),
                )
        if not self.validate_projection():
            self.rebuild()

    def _authentication_document(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        value = _thaw_json(payload)
        value.pop("integrity_authenticator", None)
        return {"contract": "availability.signal.v1", "payload": value}

    def _count_authenticator(self, count: int) -> str:
        return self.protector.authenticate_json(
            "availability.projection-count.v1", {"signal_count": int(count)}
        )

    def append_signal(
        self,
        signal: AvailabilitySignal,
        *,
        actor: str,
        observed_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> JournalRecord:
        current = _utc(observed_at or signal.valid_from, "observed_at")
        signal_id = signal.signal_id or self.protector.pseudonym(
            "availability-signal",
            "\0".join(
                (
                    signal.subject,
                    signal.scope,
                    signal.basis.value,
                    signal.stance.value,
                    signal.reason_code,
                    signal.valid_from.isoformat(),
                    signal.valid_until.isoformat(),
                    signal.source_event_id or "",
                )
            ),
        )
        if signal_id is None:
            raise AvailabilityError("signal identity is unavailable")
        payload = {
            "signal_id": signal_id,
            "stance": signal.stance.value,
            "basis": signal.basis.value,
            "reason_code": signal.reason_code,
            "scope": signal.scope,
            "source_event_id": signal.source_event_id,
            "confidence": signal.confidence,
            "valid_from": signal.valid_from.isoformat(),
            "valid_until": signal.valid_until.isoformat(),
            "raw_content_stored": False,
            "action_authority_granted": False,
            "circadian_input_used": False,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "availability.signal.v1", self._authentication_document(payload)
        )
        event = EventEnvelope(
            event_id=f"availability.signal:{signal_id.split(':', 1)[-1]}",
            event_type="availability.observed",
            source="alive.availability",
            actor=actor,
            subject=signal.subject,
            correlation_id=correlation_id,
            causation_id=signal.source_event_id,
            occurred_at=signal.valid_from,
            observed_at=current,
            expires_at=signal.valid_until,
            payload=payload,
            sensitivity=Sensitivity.PRIVATE,
            confidence=signal.confidence,
        )
        existing = self.journal.get(event.event_id)
        if existing is not None:
            return self._compatible(existing, event)
        try:
            result = self.journal.append(event)
            return JournalRecord(result.sequence, result.event)
        except EventConflictError:
            existing = self.journal.get(event.event_id)
            if existing is None:
                raise
            return self._compatible(existing, event)

    @staticmethod
    def _compatible(existing: JournalRecord, proposed: EventEnvelope) -> JournalRecord:
        fields = (
            "event_type",
            "source",
            "actor",
            "subject",
            "correlation_id",
            "causation_id",
            "occurred_at",
            "sensitivity",
            "confidence",
            "expires_at",
            "payload",
        )
        if any(
            getattr(existing.event, name) != getattr(proposed, name) for name in fields
        ):
            raise AvailabilityError("signal identity was reused with different semantics")
        return existing

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        signal_id: str | None,
    ) -> AvailabilityDecision:
        connection.execute(
            "INSERT INTO availability_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, signal_id, event.observed_at.isoformat()),
        )
        return AvailabilityDecision(event.event_id, outcome, reason, signal_id)

    def apply(self, record: JournalRecord) -> AvailabilityDecision:
        event = record.event
        if event.event_type != "availability.observed":
            raise AvailabilityError("unsupported availability event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                prior = connection.execute(
                    "SELECT * FROM availability_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if prior is not None:
                    connection.execute("COMMIT")
                    return AvailabilityDecision(
                        event.event_id,
                        str(prior["outcome"]),
                        str(prior["reason"]),
                        prior["signal_id"],
                    )
                decision = self._apply_new(connection, event)
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_new(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> AvailabilityDecision:
        payload = event.payload
        try:
            signal_id = str(payload["signal_id"])
            stance = AvailabilityStance(payload["stance"])
            basis = AvailabilityBasis(payload["basis"])
            reason = str(payload["reason_code"])
            scope = str(payload["scope"])
            source_event_id = str(payload.get("source_event_id") or "") or None
            confidence = float(payload["confidence"])
            valid_from = _utc(datetime.fromisoformat(str(payload["valid_from"])), "valid_from")
            valid_until = _utc(datetime.fromisoformat(str(payload["valid_until"])), "valid_until")
            supplied = str(payload["integrity_authenticator"])
        except (KeyError, TypeError, ValueError, AvailabilityError):
            return self._decision(connection, event, "rejected", "invalid_payload", None)
        if not self.protector.verify_json(
            "availability.signal.v1", self._authentication_document(payload), supplied
        ):
            return self._decision(connection, event, "rejected", "invalid_authenticator", None)
        try:
            normalized = AvailabilitySignal(
                event.subject or "",
                stance,
                basis,
                reason,
                valid_from,
                valid_until,
                confidence,
                scope,
                source_event_id,
                signal_id,
            )
        except AvailabilityError:
            return self._decision(connection, event, "rejected", "invalid_boundary", None)
        authority_valid = bool(
            event.source == "alive.availability"
            and event.subject == normalized.subject
            and event.sensitivity is Sensitivity.PRIVATE
            and event.expires_at == normalized.valid_until
            and event.confidence == normalized.confidence
            and payload.get("raw_content_stored") is False
            and payload.get("action_authority_granted") is False
            and payload.get("circadian_input_used") is False
            and event.occurred_at == normalized.valid_from
            and normalized.valid_from <= event.observed_at < normalized.valid_until
        )
        source = self.journal.get(source_event_id) if source_event_id else None
        if basis is AvailabilityBasis.DIRECT_ACTIVITY:
            authority_valid = authority_valid and event.actor == "system:alive-availability"
        elif basis is AvailabilityBasis.USER_EXPLICIT:
            authority_valid = bool(
                authority_valid
                and source is not None
                and source.event.event_type == "conversation.inbound"
                and source.event.actor == normalized.subject
                and source.event.subject == normalized.subject
                and event.actor == normalized.subject
            )
        elif basis is AvailabilityBasis.SYSTEM_POLICY:
            authority_valid = bool(
                authority_valid
                and source is not None
                and source.event.event_type == "availability.policy_observed"
                and source.event.subject in {None, normalized.subject}
                and event.actor.startswith("system:")
            )
        if not authority_valid:
            return self._decision(connection, event, "rejected", "invalid_authority", signal_id)
        if connection.execute(
            "SELECT 1 FROM availability_signals_v1 WHERE signal_id=?", (signal_id,)
        ).fetchone():
            return self._decision(connection, event, "deduplicated", "signal_exists", signal_id)
        connection.execute(
            "INSERT INTO availability_signals_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                signal_id,
                event.event_id,
                normalized.subject,
                stance.value,
                basis.value,
                reason,
                scope,
                source_event_id,
                confidence,
                valid_from.isoformat(),
                valid_until.isoformat(),
                event.observed_at.isoformat(),
            ),
        )
        signal_count = int(
            connection.execute(
                "SELECT COUNT(*) AS value FROM availability_signals_v1"
            ).fetchone()["value"]
        )
        connection.execute(
            """
            UPDATE availability_projection_v1
            SET signal_count=?, count_authenticator=?, updated_at=?
            WHERE singleton=1
            """,
            (
                signal_count,
                self._count_authenticator(signal_count),
                event.observed_at.isoformat(),
            ),
        )
        return self._decision(connection, event, "recorded", "bounded_context_evidence", signal_id)

    def assess(
        self,
        subject: str,
        *,
        scope: str = "proactive_social",
        as_of: datetime | None = None,
    ) -> AvailabilityAssessment:
        owner = str(subject).strip()
        selected_scope = str(scope).strip().lower()
        if not _ID_RE.fullmatch(owner) or not _SCOPE_RE.fullmatch(selected_scope):
            raise AvailabilityError("invalid assessment subject or scope")
        self.project_new()
        current = _utc(as_of or datetime.now(timezone.utc), "as_of")
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT * FROM availability_signals_v1
                WHERE subject=? AND scope=? AND valid_from<=? AND valid_until>?
                ORDER BY observed_at DESC, event_id DESC
                """,
                (owner, selected_scope, current.isoformat(), current.isoformat()),
            ).fetchall()
        if not self.validate_projection():
            return AvailabilityAssessment(
                owner,
                selected_scope,
                AvailabilityState.UNKNOWN,
                0.0,
                ("projection_integrity_error",),
                (),
                None,
            )
        evidence = list(rows)
        precedence = (
            (AvailabilityBasis.USER_EXPLICIT, AvailabilityStance.BLOCK),
            (AvailabilityBasis.SYSTEM_POLICY, AvailabilityStance.BLOCK),
            (AvailabilityBasis.DIRECT_ACTIVITY, AvailabilityStance.BLOCK),
            (AvailabilityBasis.USER_EXPLICIT, AvailabilityStance.ALLOW),
        )
        selected = None
        for basis, stance in precedence:
            selected = next(
                (
                    row
                    for row in evidence
                    if row["basis"] == basis.value and row["stance"] == stance.value
                ),
                None,
            )
            if selected is not None:
                break
        if selected is None:
            return AvailabilityAssessment(
                owner,
                selected_scope,
                AvailabilityState.UNKNOWN,
                0.0,
                tuple(dict.fromkeys(str(row["reason_code"]) for row in evidence)),
                tuple(str(row["event_id"]) for row in evidence),
                max(
                    (datetime.fromisoformat(str(row["valid_until"])) for row in evidence),
                    default=None,
                ),
            )
        state = (
            AvailabilityState.EXPLICITLY_AVAILABLE
            if selected["stance"] == AvailabilityStance.ALLOW.value
            else AvailabilityState.BLOCKED
        )
        return AvailabilityAssessment(
            owner,
            selected_scope,
            state,
            float(selected["confidence"]),
            (str(selected["reason_code"]),),
            (str(selected["event_id"]),),
            datetime.fromisoformat(str(selected["valid_until"])),
        )

    def _valid_projected_row(self, row: sqlite3.Row) -> bool:
        record = self.journal.get(str(row["event_id"]))
        if record is None or record.event.event_type != "availability.observed":
            return False
        payload = record.event.payload
        try:
            supplied = str(payload["integrity_authenticator"])
            if not self.protector.verify_json(
                "availability.signal.v1",
                self._authentication_document(payload),
                supplied,
            ):
                return False
            return bool(
                payload.get("signal_id") == row["signal_id"]
                and record.event.subject == row["subject"]
                and payload.get("stance") == row["stance"]
                and payload.get("basis") == row["basis"]
                and payload.get("reason_code") == row["reason_code"]
                and payload.get("scope") == row["scope"]
                and payload.get("source_event_id") == row["source_event_id"]
                and float(payload.get("confidence")) == float(row["confidence"])
                and payload.get("valid_from") == row["valid_from"]
                and payload.get("valid_until") == row["valid_until"]
            )
        except (KeyError, TypeError, ValueError):
            return False

    def validate_projection(self) -> bool:
        try:
            with closing(self._connect()) as connection:
                metadata = connection.execute(
                    "SELECT signal_count, count_authenticator "
                    "FROM availability_projection_v1 WHERE singleton=1"
                ).fetchone()
                rows = connection.execute(
                    "SELECT * FROM availability_signals_v1 ORDER BY event_id"
                ).fetchall()
            return bool(
                metadata is not None
                and int(metadata["signal_count"]) == len(rows)
                and hmac.compare_digest(
                    str(metadata["count_authenticator"]),
                    self._count_authenticator(len(rows)),
                )
                and all(self._valid_projected_row(row) for row in rows)
            )
        except (KeyError, TypeError, ValueError, sqlite3.DatabaseError):
            return False

    def project_new(self, *, limit: int = 1000) -> list[AvailabilityDecision]:
        if not 1 <= limit <= 10_000:
            raise AvailabilityError("limit must be between 1 and 10000")
        decisions = []
        watermark = self.journal.last_sequence()
        while self.journal.checkpoint(self.CHECKPOINT) < watermark:
            start = self.journal.checkpoint(self.CHECKPOINT)
            records = []
            for record in self.journal.iter_replay(after_sequence=start, batch_size=limit):
                if record.sequence > watermark:
                    break
                records.append(record)
                if len(records) >= limit:
                    break
            if not records:
                raise AvailabilityError("availability projection could not reach watermark")
            for record in records:
                if record.event.event_type == "availability.observed":
                    decisions.append(self.apply(record))
                try:
                    self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
                except ValueError:
                    if self.journal.checkpoint(self.CHECKPOINT) < record.sequence:
                        raise
        return decisions

    def rebuild(self, *, batch_size: int = 500) -> list[AvailabilityDecision]:
        if not 1 <= batch_size <= 10_000:
            raise AvailabilityError("batch_size must be between 1 and 10000")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM availability_decisions_v1")
            connection.execute("DELETE FROM availability_signals_v1")
            connection.execute(
                """
                UPDATE availability_projection_v1
                SET signal_count=0, count_authenticator=?, updated_at=?
                WHERE singleton=1
                """,
                (
                    self._count_authenticator(0),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?",
                (self.CHECKPOINT,),
            )
            connection.execute("COMMIT")
        decisions = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise AvailabilityError("availability replay made no progress")
        return decisions


def availability_shadow_enabled(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    truthy = {"1", "true", "yes", "on", "enabled"}
    return (
        str(values.get("HERMES_ALIVE_KERNEL_SHADOW_ENABLED", "false")).strip().lower()
        in truthy
        and str(values.get("HERMES_ALIVE_AVAILABILITY_SHADOW_ENABLED", "false"))
        .strip()
        .lower()
        in truthy
    )


def mirror_legacy_activity_guard(
    shared_dir: str | Path,
    *,
    raw_subject: Any,
    tick_id: str,
    stage: str,
    user_active: bool,
    snapshot: Mapping[str, Any],
    observed_at: datetime | None = None,
) -> AvailabilityDecision:
    """Mirror one structural activity check; idle never becomes permission."""

    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    protector = LocalIdentityProtector(kernel_dir / "identity.key")
    subject = protector.pseudonym("availability-subject", raw_subject)
    if subject is None:
        raise AvailabilityError("availability subject is unavailable")
    now = _utc(observed_at or datetime.now(timezone.utc), "observed_at")
    reason = str(snapshot.get("activity_guard_reason_code") or "activity_state_unknown")
    if not _REASON_RE.fullmatch(reason):
        reason = "activity_state_unknown"
    stage_value = str(stage).strip().lower().replace("-", "_")
    if not _REASON_RE.fullmatch(stage_value):
        stage_value = "unknown_stage"
    raw_identity = "\0".join((subject, str(tick_id), stage_value, reason, str(bool(user_active))))
    signal_id = protector.pseudonym("availability-signal", raw_identity)
    if signal_id is None:
        raise AvailabilityError("availability signal identity is unavailable")
    journal = ExperienceJournal(kernel_dir / "experience.sqlite3")
    projection = AvailabilityProjection(journal, protector=protector)
    signal = AvailabilitySignal(
        subject=subject,
        stance=AvailabilityStance.BLOCK if user_active else AvailabilityStance.UNKNOWN,
        basis=AvailabilityBasis.DIRECT_ACTIVITY,
        reason_code=reason,
        valid_from=now,
        valid_until=now + timedelta(minutes=5),
        confidence=1.0 if user_active else 0.5,
        signal_id=signal_id,
    )
    record = projection.append_signal(
        signal,
        actor="system:alive-availability",
        observed_at=now,
        correlation_id=protector.pseudonym("availability-tick", tick_id),
    )
    return projection.apply(record)
