"""Replayable presentation preferences that never become truth or authority."""

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
from types import MappingProxyType
from typing import Any, Mapping

from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_SCOPE_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_EXPLICIT_MAX = timedelta(days=366)
_ADVISORY_MAX = timedelta(days=30)
_LEGACY_SHADOW_MAX = timedelta(days=2)


class PresentationError(ValueError):
    """Presentation data crossed its semantic or authority boundary."""


class PresentationDimension(StrEnum):
    VERBOSITY = "verbosity"
    FORMALITY = "formality"
    HUMOR_DRY = "humor_dry"
    HUMOR_ABSURD = "humor_absurd"
    CURIOSITY = "curiosity"
    WARMTH = "warmth"
    QUIRKINESS = "quirkiness"
    EMOJI_USAGE = "emoji_usage"
    SELF_DISCLOSURE = "self_disclosure"


class PresentationAuthority(StrEnum):
    USER_EXPLICIT = "user_explicit"
    LEARNED_ADVISORY = "learned_advisory"
    LEGACY_SHADOW = "legacy_shadow"


NEUTRAL_DEFAULTS: Mapping[PresentationDimension, float] = {
    PresentationDimension.VERBOSITY: 0.5,
    PresentationDimension.FORMALITY: 0.5,
    PresentationDimension.HUMOR_DRY: 0.3,
    PresentationDimension.HUMOR_ABSURD: 0.2,
    PresentationDimension.CURIOSITY: 0.5,
    PresentationDimension.WARMTH: 0.5,
    PresentationDimension.QUIRKINESS: 0.3,
    PresentationDimension.EMOJI_USAGE: 0.25,
    PresentationDimension.SELF_DISCLOSURE: 0.2,
}


@dataclass(frozen=True, slots=True)
class PresentationPreference:
    subject: str
    dimension: PresentationDimension
    value: float
    authority: PresentationAuthority
    reason_code: str
    valid_from: datetime
    valid_until: datetime
    scope: str = "proactive_social"
    source_event_id: str | None = None
    preference_id: str = ""

    def __post_init__(self) -> None:
        subject = str(self.subject).strip()
        preference_id = str(self.preference_id).strip()
        source = str(self.source_event_id or "").strip() or None
        scope = str(self.scope).strip().lower()
        reason = str(self.reason_code).strip().lower()
        if not _ID_RE.fullmatch(subject):
            raise PresentationError("invalid subject")
        if preference_id and not _ID_RE.fullmatch(preference_id):
            raise PresentationError("invalid preference_id")
        if source is not None and not _ID_RE.fullmatch(source):
            raise PresentationError("invalid source_event_id")
        if not _SCOPE_RE.fullmatch(scope) or not _REASON_RE.fullmatch(reason):
            raise PresentationError("invalid scope or reason")
        start = _utc(self.valid_from, "valid_from")
        end = _utc(self.valid_until, "valid_until")
        if end <= start:
            raise PresentationError("valid_until must follow valid_from")
        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise PresentationError("presentation value must be between 0 and 1")
        authority = PresentationAuthority(self.authority)
        maximum = {
            PresentationAuthority.USER_EXPLICIT: _EXPLICIT_MAX,
            PresentationAuthority.LEARNED_ADVISORY: _ADVISORY_MAX,
            PresentationAuthority.LEGACY_SHADOW: _LEGACY_SHADOW_MAX,
        }[authority]
        if end - start > maximum:
            raise PresentationError("preference exceeds its maximum lifetime")
        if authority is not PresentationAuthority.LEGACY_SHADOW and source is None:
            raise PresentationError("non-legacy preference requires source evidence")
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "preference_id", preference_id)
        object.__setattr__(self, "source_event_id", source)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "reason_code", reason)
        object.__setattr__(self, "dimension", PresentationDimension(self.dimension))
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "valid_from", start)
        object.__setattr__(self, "valid_until", end)


@dataclass(frozen=True, slots=True)
class PresentationDecision:
    event_id: str
    outcome: str
    reason: str
    preference_id: str | None


@dataclass(frozen=True, slots=True)
class PresentationPlan:
    subject: str
    scope: str
    values: Mapping[str, float]
    explicit_dimensions: tuple[str, ...]
    advisory_event_ids: tuple[str, ...]
    evidence_event_ids: tuple[str, ...]
    integrity_ok: bool

    @property
    def permits_action(self) -> bool:
        return False

    @property
    def may_change_semantics(self) -> bool:
        return False

    @property
    def may_choose_route(self) -> bool:
        return False


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PresentationError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


class PresentationProjection:
    """Project explicit style separately from expiring inferred suggestions."""

    CHECKPOINT = "alive-presentation-v1"

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
                CREATE TABLE IF NOT EXISTS presentation_projection_v1 (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    preference_count INTEGER NOT NULL,
                    count_authenticator TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO presentation_projection_v1
                    (singleton, preference_count, count_authenticator, updated_at)
                VALUES (1, 0, '', '1970-01-01T00:00:00+00:00');
                CREATE TABLE IF NOT EXISTS presentation_preferences_v1 (
                    preference_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    value REAL NOT NULL,
                    authority TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    source_event_id TEXT,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_presentation_active_v1
                    ON presentation_preferences_v1(subject, scope, dimension, valid_until);
                CREATE TABLE IF NOT EXISTS presentation_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    preference_id TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )
            row = connection.execute(
                "SELECT preference_count, count_authenticator FROM presentation_projection_v1 WHERE singleton=1"
            ).fetchone()
            if row is not None and not str(row["count_authenticator"]):
                count = int(row["preference_count"])
                connection.execute(
                    "UPDATE presentation_projection_v1 SET count_authenticator=? WHERE singleton=1",
                    (self._count_authenticator(count),),
                )
        if not self.validate_projection():
            self.rebuild()

    @staticmethod
    def _authentication_document(payload: Mapping[str, Any]) -> dict[str, Any]:
        value = _thaw_json(payload)
        value.pop("integrity_authenticator", None)
        return {"contract": "presentation.preference.v1", "payload": value}

    def _count_authenticator(self, count: int) -> str:
        return self.protector.authenticate_json(
            "presentation.projection-count.v1", {"preference_count": int(count)}
        )

    def append_preference(
        self,
        preference: PresentationPreference,
        *,
        actor: str,
        observed_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> JournalRecord:
        current = _utc(observed_at or preference.valid_from, "observed_at")
        preference_id = preference.preference_id or self.protector.pseudonym(
            "presentation-preference",
            "\0".join(
                (
                    preference.subject,
                    preference.scope,
                    preference.dimension.value,
                    str(preference.value),
                    preference.authority.value,
                    preference.reason_code,
                    preference.valid_from.isoformat(),
                    preference.valid_until.isoformat(),
                    preference.source_event_id or "",
                )
            ),
        )
        if preference_id is None:
            raise PresentationError("preference identity is unavailable")
        payload = {
            "preference_id": preference_id,
            "dimension": preference.dimension.value,
            "value": preference.value,
            "authority": preference.authority.value,
            "reason_code": preference.reason_code,
            "scope": preference.scope,
            "source_event_id": preference.source_event_id,
            "valid_from": preference.valid_from.isoformat(),
            "valid_until": preference.valid_until.isoformat(),
            "raw_content_stored": False,
            "truth_claimed": False,
            "action_authority_granted": False,
            "route_authority_granted": False,
            "semantic_change_allowed": False,
            "relationship_inferred": False,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "presentation.preference.v1", self._authentication_document(payload)
        )
        event = EventEnvelope(
            event_id=f"presentation.preference:{preference_id.split(':', 1)[-1]}",
            event_type="presentation.preference_observed",
            source="alive.presentation",
            actor=actor,
            subject=preference.subject,
            correlation_id=correlation_id,
            causation_id=preference.source_event_id,
            occurred_at=preference.valid_from,
            observed_at=current,
            expires_at=preference.valid_until,
            payload=payload,
            sensitivity=Sensitivity.PRIVATE,
            confidence=1.0 if preference.authority is PresentationAuthority.USER_EXPLICIT else 0.5,
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
                raise PresentationError("conflicting presentation preference")
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
            raise PresentationError("preference identity was reused with different semantics")
        return existing

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        preference_id: str | None,
    ) -> PresentationDecision:
        connection.execute(
            "INSERT INTO presentation_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, preference_id, event.observed_at.isoformat()),
        )
        return PresentationDecision(event.event_id, outcome, reason, preference_id)

    def apply(self, record: JournalRecord) -> PresentationDecision:
        event = record.event
        if event.event_type != "presentation.preference_observed":
            raise PresentationError("unsupported presentation event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                prior = connection.execute(
                    "SELECT * FROM presentation_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if prior is not None:
                    connection.execute("COMMIT")
                    return PresentationDecision(
                        event.event_id, str(prior["outcome"]), str(prior["reason"]), prior["preference_id"]
                    )
                decision = self._apply_new(connection, event)
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_new(self, connection: sqlite3.Connection, event: EventEnvelope) -> PresentationDecision:
        payload = event.payload
        try:
            preference_id = str(payload["preference_id"])
            preference = PresentationPreference(
                subject=event.subject or "",
                dimension=PresentationDimension(payload["dimension"]),
                value=float(payload["value"]),
                authority=PresentationAuthority(payload["authority"]),
                reason_code=str(payload["reason_code"]),
                valid_from=datetime.fromisoformat(str(payload["valid_from"])),
                valid_until=datetime.fromisoformat(str(payload["valid_until"])),
                scope=str(payload["scope"]),
                source_event_id=str(payload.get("source_event_id") or "") or None,
                preference_id=preference_id,
            )
            supplied = str(payload["integrity_authenticator"])
        except (KeyError, TypeError, ValueError, PresentationError):
            return self._decision(connection, event, "rejected", "invalid_payload", None)
        if not self.protector.verify_json(
            "presentation.preference.v1", self._authentication_document(payload), supplied
        ):
            return self._decision(connection, event, "rejected", "invalid_authenticator", None)
        authority_valid = bool(
            event.source == "alive.presentation"
            and event.subject == preference.subject
            and event.sensitivity is Sensitivity.PRIVATE
            and event.expires_at == preference.valid_until
            and event.occurred_at == preference.valid_from
            and preference.valid_from <= event.observed_at < preference.valid_until
            and payload.get("raw_content_stored") is False
            and payload.get("truth_claimed") is False
            and payload.get("action_authority_granted") is False
            and payload.get("route_authority_granted") is False
            and payload.get("semantic_change_allowed") is False
            and payload.get("relationship_inferred") is False
        )
        source = self.journal.get(preference.source_event_id) if preference.source_event_id else None
        if preference.authority is PresentationAuthority.USER_EXPLICIT:
            authority_valid = bool(
                authority_valid
                and source is not None
                and source.event.event_type == "conversation.inbound"
                and source.event.actor == preference.subject
                and source.event.subject == preference.subject
                and event.actor == preference.subject
            )
        elif preference.authority is PresentationAuthority.LEARNED_ADVISORY:
            accepted_reflection = False
            if source is not None and source.event.event_type == "reflection.reviewed":
                reflection_id = str(source.event.payload.get("reflection_id") or "")
                approval_id = str(source.event.payload.get("source_event_id") or "")
                proposal = self.journal.get(f"reflection.proposal:{reflection_id}") if reflection_id else None
                approval = self.journal.get(approval_id) if approval_id else None
                accepted_reflection = bool(
                    source.event.source == "alive.reflection"
                    and source.event.subject == preference.subject
                    and source.event.actor == preference.subject
                    and source.event.payload.get("review") == "accept"
                    and source.event.causation_id == approval_id
                    and proposal is not None
                    and proposal.event.event_type == "reflection.proposed"
                    and proposal.event.source == "alive.reflection"
                    and proposal.event.subject == preference.subject
                    and approval is not None
                    and approval.event.event_type == "conversation.inbound"
                    and approval.event.subject == preference.subject
                    and approval.event.actor == preference.subject
                    and proposal.sequence < approval.sequence < source.sequence
                )
            explicit_feedback = False
            if source is not None and source.event.event_type == "outcome.recorded":
                feedback_source_id = str(source.event.payload.get("source_event_id") or "")
                feedback_source = self.journal.get(feedback_source_id) if feedback_source_id else None
                explicit_feedback = bool(
                    source.event.source == "alive.outcomes"
                    and source.event.subject == preference.subject
                    and source.event.payload.get("kind") == "explicit_feedback"
                    and feedback_source is not None
                    and feedback_source.event.event_type == "conversation.inbound"
                    and feedback_source.event.subject == preference.subject
                    and feedback_source.event.actor == preference.subject
                    and feedback_source.sequence < source.sequence
                )
            authority_valid = bool(
                authority_valid
                and (accepted_reflection or explicit_feedback)
                and event.actor == "system:alive-presentation"
            )
        else:
            authority_valid = bool(
                authority_valid
                and source is None
                and event.actor == "system:alive-presentation-shadow"
            )
        if not authority_valid:
            return self._decision(connection, event, "rejected", "invalid_authority", preference_id)
        if connection.execute(
            "SELECT 1 FROM presentation_preferences_v1 WHERE preference_id=?", (preference_id,)
        ).fetchone():
            return self._decision(connection, event, "deduplicated", "preference_exists", preference_id)
        connection.execute(
            "INSERT INTO presentation_preferences_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                preference_id,
                event.event_id,
                preference.subject,
                preference.dimension.value,
                preference.value,
                preference.authority.value,
                preference.reason_code,
                preference.scope,
                preference.source_event_id,
                preference.valid_from.isoformat(),
                preference.valid_until.isoformat(),
                event.observed_at.isoformat(),
            ),
        )
        count = int(connection.execute("SELECT COUNT(*) AS value FROM presentation_preferences_v1").fetchone()["value"])
        connection.execute(
            "UPDATE presentation_projection_v1 SET preference_count=?, count_authenticator=?, updated_at=? WHERE singleton=1",
            (count, self._count_authenticator(count), event.observed_at.isoformat()),
        )
        reason = "explicit_presentation_preference" if preference.authority is PresentationAuthority.USER_EXPLICIT else "advisory_only"
        return self._decision(connection, event, "recorded", reason, preference_id)

    def resolve(
        self,
        subject: str,
        *,
        scope: str = "proactive_social",
        as_of: datetime | None = None,
    ) -> PresentationPlan:
        owner = str(subject).strip()
        selected_scope = str(scope).strip().lower()
        if not _ID_RE.fullmatch(owner) or not _SCOPE_RE.fullmatch(selected_scope):
            raise PresentationError("invalid presentation subject or scope")
        self.project_new()
        current = _utc(as_of or datetime.now(timezone.utc), "as_of")
        integrity_ok = self.validate_projection()
        values = {dimension.value: value for dimension, value in NEUTRAL_DEFAULTS.items()}
        if not integrity_ok:
            return PresentationPlan(
                owner, selected_scope, MappingProxyType(values), (), (), (), False
            )
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT * FROM presentation_preferences_v1
                WHERE subject=? AND scope=? AND valid_from<=? AND valid_until>?
                ORDER BY observed_at DESC, event_id DESC
                """,
                (owner, selected_scope, current.isoformat(), current.isoformat()),
            ).fetchall()
        explicit: list[str] = []
        evidence: list[str] = []
        advisory: list[str] = []
        chosen: set[str] = set()
        for row in rows:
            event_id = str(row["event_id"])
            if row["authority"] == PresentationAuthority.USER_EXPLICIT.value:
                dimension = str(row["dimension"])
                if dimension not in chosen:
                    values[dimension] = float(row["value"])
                    chosen.add(dimension)
                    explicit.append(dimension)
                    evidence.append(event_id)
            else:
                advisory.append(event_id)
        return PresentationPlan(
            owner,
            selected_scope,
            MappingProxyType(values),
            tuple(explicit),
            tuple(advisory),
            tuple(evidence),
            True,
        )

    def _valid_projected_row(self, row: sqlite3.Row) -> bool:
        record = self.journal.get(str(row["event_id"]))
        if record is None or record.event.event_type != "presentation.preference_observed":
            return False
        payload = record.event.payload
        try:
            supplied = str(payload["integrity_authenticator"])
            return bool(
                self.protector.verify_json(
                    "presentation.preference.v1", self._authentication_document(payload), supplied
                )
                and payload.get("preference_id") == row["preference_id"]
                and record.event.subject == row["subject"]
                and payload.get("dimension") == row["dimension"]
                and float(payload.get("value")) == float(row["value"])
                and payload.get("authority") == row["authority"]
                and payload.get("reason_code") == row["reason_code"]
                and payload.get("scope") == row["scope"]
                and payload.get("source_event_id") == row["source_event_id"]
                and payload.get("valid_from") == row["valid_from"]
                and payload.get("valid_until") == row["valid_until"]
            )
        except (KeyError, TypeError, ValueError):
            return False

    def validate_projection(self) -> bool:
        try:
            with closing(self._connect()) as connection:
                metadata = connection.execute(
                    "SELECT preference_count, count_authenticator FROM presentation_projection_v1 WHERE singleton=1"
                ).fetchone()
                rows = connection.execute("SELECT * FROM presentation_preferences_v1 ORDER BY event_id").fetchall()
            return bool(
                metadata is not None
                and int(metadata["preference_count"]) == len(rows)
                and hmac.compare_digest(
                    str(metadata["count_authenticator"]), self._count_authenticator(len(rows))
                )
                and all(self._valid_projected_row(row) for row in rows)
            )
        except (KeyError, TypeError, ValueError, sqlite3.DatabaseError):
            return False

    def project_new(self, *, limit: int = 1000) -> list[PresentationDecision]:
        if not 1 <= limit <= 10_000:
            raise PresentationError("limit must be between 1 and 10000")
        decisions: list[PresentationDecision] = []
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
                raise PresentationError("presentation projection could not reach watermark")
            for record in records:
                if record.event.event_type == "presentation.preference_observed":
                    decisions.append(self.apply(record))
                try:
                    self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
                except ValueError:
                    if self.journal.checkpoint(self.CHECKPOINT) < record.sequence:
                        raise
        return decisions

    def rebuild(self, *, batch_size: int = 500) -> list[PresentationDecision]:
        if not 1 <= batch_size <= 10_000:
            raise PresentationError("batch_size must be between 1 and 10000")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM presentation_decisions_v1")
            connection.execute("DELETE FROM presentation_preferences_v1")
            connection.execute(
                "UPDATE presentation_projection_v1 SET preference_count=0, count_authenticator=?, updated_at=? WHERE singleton=1",
                (self._count_authenticator(0), datetime.now(timezone.utc).isoformat()),
            )
            connection.execute("DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,))
            connection.execute("COMMIT")
        decisions: list[PresentationDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise PresentationError("presentation replay made no progress")
        return decisions


def presentation_shadow_enabled(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    truthy = {"1", "true", "yes", "on", "enabled"}
    return (
        str(values.get("HERMES_ALIVE_KERNEL_SHADOW_ENABLED", "false")).strip().lower() in truthy
        and str(values.get("HERMES_ALIVE_PRESENTATION_SHADOW_ENABLED", "false")).strip().lower() in truthy
    )


def mirror_legacy_voice(
    shared_dir: str | Path,
    *,
    raw_subject: Any,
    voice: Any,
    observed_at: datetime | None = None,
) -> tuple[PresentationDecision, ...]:
    """Mirror legacy voice dimensions as advisory evidence; never activate them."""

    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    protector = LocalIdentityProtector(kernel_dir / "identity.key")
    subject = protector.pseudonym("presentation-subject", raw_subject)
    if subject is None:
        raise PresentationError("presentation subject is unavailable")
    now = _utc(observed_at or datetime.now(timezone.utc), "observed_at")
    bucket = now.replace(minute=0, second=0, microsecond=0)
    values: dict[PresentationDimension, float] = {}
    for dimension in PresentationDimension:
        try:
            value = float(getattr(voice, dimension.value))
        except (AttributeError, TypeError, ValueError):
            continue
        if math.isfinite(value) and 0.0 <= value <= 1.0:
            values[dimension] = value
    journal = ExperienceJournal(kernel_dir / "experience.sqlite3")
    projection = PresentationProjection(journal, protector=protector)
    revision = protector.pseudonym(
        "legacy-voice-revision",
        "\0".join(
            (bucket.isoformat(),)
            + tuple(
                f"{dimension.value}={values[dimension]:.6f}"
                for dimension in sorted(values, key=lambda item: item.value)
            )
        ),
    )
    if revision is None:
        raise PresentationError("legacy voice revision is unavailable")
    decisions = []
    for dimension, value in values.items():
        preference_id = protector.pseudonym(
            "presentation-preference", f"{subject}\0{revision}\0{dimension.value}"
        )
        if preference_id is None:
            raise PresentationError("legacy preference identity is unavailable")
        preference = PresentationPreference(
            subject=subject,
            dimension=dimension,
            value=value,
            authority=PresentationAuthority.LEGACY_SHADOW,
            reason_code="legacy_voice_snapshot",
            valid_from=bucket,
            valid_until=bucket + timedelta(hours=24),
            preference_id=preference_id,
        )
        record = projection.append_preference(
            preference,
            actor="system:alive-presentation-shadow",
            observed_at=bucket,
            correlation_id=revision,
        )
        decisions.append(projection.apply(record))
    return tuple(decisions)
