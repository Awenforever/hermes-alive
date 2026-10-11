"""User-owned, replayable autonomy policy for proactive external action."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from .deliberation import PolicyContext, SideEffect
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")


class AutonomyPolicyError(ValueError):
    """An autonomy policy mutation crossed the user-authority boundary."""


@dataclass(frozen=True, slots=True)
class AutonomyPolicy:
    subject: str
    revision: int
    enabled: bool
    context: PolicyContext
    event_id: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AutonomyPolicyDecision:
    event_id: str
    outcome: str
    reason: str
    subject: str | None
    revision: int | None


class AutonomyPolicyProjection:
    """Project explicit user policy; absence is a durable fail-closed state."""

    CHECKPOINT = "alive-autonomy-policy-v1"

    def __init__(self, journal: ExperienceJournal) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        self.protector = LocalIdentityProtector(self.path.parent / "identity.key")
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
                CREATE TABLE IF NOT EXISTS autonomy_policies_v1 (
                    subject TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL CHECK(revision >= 1),
                    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
                    can_interrupt INTEGER NOT NULL CHECK(can_interrupt IN (0, 1)),
                    minimum_confidence REAL NOT NULL,
                    maximum_risk REAL NOT NULL,
                    allowed_side_effects TEXT NOT NULL,
                    policy_event_id TEXT NOT NULL UNIQUE,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS autonomy_policy_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    subject TEXT,
                    revision INTEGER,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )

    @staticmethod
    def _policy_payload(
        *,
        revision: int,
        expected_revision: int,
        enabled: bool,
        context: PolicyContext,
    ) -> dict[str, object]:
        return {
            "revision": revision,
            "expected_revision": expected_revision,
            "enabled": enabled,
            "can_interrupt": context.can_interrupt,
            "minimum_confidence": context.minimum_confidence,
            "maximum_risk": context.maximum_risk,
            "allowed_side_effects": sorted(
                value.value for value in context.allowed_side_effects
            ),
            "raw_command_stored": False,
        }

    def append_update(
        self,
        *,
        subject: str,
        actor: str,
        expected_revision: int,
        enabled: bool,
        context: PolicyContext,
        operation_id: str | None = None,
    ) -> JournalRecord:
        owner = str(subject).strip()
        principal = str(actor).strip()
        operation = str(operation_id or uuid4()).strip()
        expected = int(expected_revision)
        if not _ID_RE.fullmatch(owner) or not _ID_RE.fullmatch(operation):
            raise AutonomyPolicyError("invalid policy identity")
        if principal != owner:
            raise AutonomyPolicyError("autonomy policy must be self-authorized")
        if expected < 0:
            raise AutonomyPolicyError("expected revision cannot be negative")
        if not isinstance(enabled, bool):
            raise AutonomyPolicyError("enabled must be boolean")
        if not isinstance(context, PolicyContext):
            raise AutonomyPolicyError("policy context is required")
        payload = self._policy_payload(
            revision=expected + 1,
            expected_revision=expected,
            enabled=enabled,
            context=context,
        )
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "autonomy.policy.v1", payload
        )
        event = EventEnvelope(
            event_id=f"autonomy.policy:{operation}",
            event_type="autonomy.policy_changed",
            source="hermes.command.alive",
            actor=principal,
            subject=owner,
            sensitivity=Sensitivity.PRIVATE,
            payload=payload,
        )
        existing = self.journal.get(event.event_id)
        if existing is not None:
            if existing.event.canonical_json() != event.canonical_json():
                # Timestamps differ on a legitimate retry, so compare the
                # authority-bearing fields rather than accepting ID reuse.
                prior = existing.event
                if (
                    prior.event_type != event.event_type
                    or prior.source != event.source
                    or prior.actor != event.actor
                    or prior.subject != event.subject
                    or prior.sensitivity != event.sensitivity
                    or prior.payload != event.payload
                ):
                    raise AutonomyPolicyError(
                        "operation ID was reused with different policy semantics"
                    )
            return existing
        try:
            appended = self.journal.append(event)
            return JournalRecord(appended.sequence, appended.event)
        except EventConflictError as exc:
            raise AutonomyPolicyError("conflicting autonomy policy event") from exc

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        revision: int | None,
    ) -> AutonomyPolicyDecision:
        connection.execute(
            "INSERT INTO autonomy_policy_decisions_v1 VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                outcome,
                reason,
                event.subject,
                revision,
                event.observed_at.isoformat(),
            ),
        )
        return AutonomyPolicyDecision(
            event.event_id, outcome, reason, event.subject, revision
        )

    @staticmethod
    def _context(payload: dict[str, object]) -> PolicyContext:
        enabled = payload["enabled"]
        can_interrupt = payload["can_interrupt"]
        raw_stored = payload["raw_command_stored"]
        if not isinstance(enabled, bool) or not isinstance(can_interrupt, bool):
            raise TypeError("policy booleans are invalid")
        if raw_stored is not False:
            raise ValueError("raw command storage is forbidden")
        allowed = frozenset(
            SideEffect(value) for value in payload["allowed_side_effects"]
        )
        return PolicyContext(
            can_interrupt=can_interrupt,
            minimum_confidence=float(payload["minimum_confidence"]),
            maximum_risk=float(payload["maximum_risk"]),
            allowed_side_effects=allowed,
        )

    def apply(self, record: JournalRecord) -> AutonomyPolicyDecision:
        event = record.event
        if event.event_type != "autonomy.policy_changed":
            raise AutonomyPolicyError("unsupported autonomy policy event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM autonomy_policy_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return AutonomyPolicyDecision(
                        event.event_id,
                        str(existing["outcome"]),
                        str(existing["reason"]),
                        existing["subject"],
                        existing["revision"],
                    )
                payload = _thaw_json(event.payload)
                authenticator = payload.pop("integrity_authenticator", None)
                if (
                    event.source != "hermes.command.alive"
                    or event.subject is None
                    or event.actor != event.subject
                    or event.sensitivity is not Sensitivity.PRIVATE
                    or not self.protector.verify_json(
                        "autonomy.policy.v1", payload, authenticator
                    )
                ):
                    decision = self._decision(
                        connection, event, "rejected", "policy_authority_invalid", None
                    )
                    connection.execute("COMMIT")
                    return decision
                try:
                    revision = int(payload["revision"])
                    expected = int(payload["expected_revision"])
                    context = self._context(payload)
                    enabled = payload["enabled"]
                except (KeyError, TypeError, ValueError):
                    decision = self._decision(
                        connection, event, "rejected", "policy_payload_invalid", None
                    )
                    connection.execute("COMMIT")
                    return decision
                current = connection.execute(
                    "SELECT revision FROM autonomy_policies_v1 WHERE subject=?",
                    (event.subject,),
                ).fetchone()
                current_revision = int(current["revision"]) if current else 0
                earlier_authenticated_contender = False
                if revision == expected + 1 and expected == current_revision:
                    for earlier in self.journal.iter_replay():
                        if earlier.sequence >= record.sequence:
                            break
                        candidate = earlier.event
                        if (
                            candidate.event_type != "autonomy.policy_changed"
                            or candidate.subject != event.subject
                        ):
                            continue
                        earlier_payload = _thaw_json(candidate.payload)
                        earlier_authenticator = earlier_payload.pop(
                            "integrity_authenticator", None
                        )
                        try:
                            self._context(earlier_payload)
                        except (KeyError, TypeError, ValueError):
                            continue
                        if (
                            earlier_payload.get("expected_revision") == expected
                            and earlier_payload.get("revision") == revision
                            and candidate.source == "hermes.command.alive"
                            and candidate.actor == event.subject
                            and candidate.sensitivity is Sensitivity.PRIVATE
                            and self.protector.verify_json(
                                "autonomy.policy.v1",
                                earlier_payload,
                                earlier_authenticator,
                            )
                        ):
                            earlier_authenticated_contender = True
                            break
                if (
                    revision != expected + 1
                    or expected != current_revision
                    or earlier_authenticated_contender
                ):
                    decision = self._decision(
                        connection,
                        event,
                        "rejected",
                        "policy_revision_conflict",
                        revision,
                    )
                    connection.execute("COMMIT")
                    return decision
                connection.execute(
                    """
                    INSERT INTO autonomy_policies_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(subject) DO UPDATE SET
                        revision=excluded.revision,
                        enabled=excluded.enabled,
                        can_interrupt=excluded.can_interrupt,
                        minimum_confidence=excluded.minimum_confidence,
                        maximum_risk=excluded.maximum_risk,
                        allowed_side_effects=excluded.allowed_side_effects,
                        policy_event_id=excluded.policy_event_id,
                        updated_at=excluded.updated_at
                    """,
                    (
                        event.subject,
                        revision,
                        int(enabled),
                        int(context.can_interrupt),
                        context.minimum_confidence,
                        context.maximum_risk,
                        ",".join(
                            sorted(value.value for value in context.allowed_side_effects)
                        ),
                        event.event_id,
                        event.observed_at.isoformat(),
                    ),
                )
                decision = self._decision(
                    connection, event, "recorded", "explicit_user_policy", revision
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def current(self, subject: str) -> AutonomyPolicy | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM autonomy_policies_v1 WHERE subject=?",
                (str(subject),),
            ).fetchone()
        if row is None:
            return None
        values = str(row["allowed_side_effects"])
        allowed = frozenset(
            SideEffect(value) for value in values.split(",") if value
        )
        return AutonomyPolicy(
            subject=str(row["subject"]),
            revision=int(row["revision"]),
            enabled=bool(row["enabled"]),
            context=PolicyContext(
                can_interrupt=bool(row["can_interrupt"]),
                minimum_confidence=float(row["minimum_confidence"]),
                maximum_risk=float(row["maximum_risk"]),
                allowed_side_effects=allowed,
            ),
            event_id=str(row["policy_event_id"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def project_new(self, *, limit: int = 1000) -> list[AutonomyPolicyDecision]:
        decisions: list[AutonomyPolicyDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(
            self.journal.iter_replay(after_sequence=start), start=1
        ):
            if record.event.event_type == "autonomy.policy_changed":
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[AutonomyPolicyDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM autonomy_policies_v1")
            connection.execute("DELETE FROM autonomy_policy_decisions_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?",
                (self.CHECKPOINT,),
            )
            connection.execute("COMMIT")
        decisions: list[AutonomyPolicyDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("autonomy policy replay made no progress")
        return decisions
