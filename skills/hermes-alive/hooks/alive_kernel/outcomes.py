"""Causal action attempts and evidence-backed outcomes for Hermes Alive."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
import sqlite3
from typing import Any, Iterable
from uuid import uuid4

from .action_contract import ActionContractError, parse_action_contract
from .autonomy_policy import AutonomyPolicyProjection
from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .deliberation import ActionKind, deserialize_frame
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


class OutcomeValidationError(ValueError):
    """An action or outcome fact violates the causal contract."""


class OutcomeKind(StrEnum):
    DELIVERY_SUCCEEDED = "delivery_succeeded"
    DELIVERY_FAILED = "delivery_failed"
    USER_REPLIED = "user_replied"
    USER_CORRECTED = "user_corrected"
    USER_DISMISSED = "user_dismissed"
    EXPLICIT_FEEDBACK = "explicit_feedback"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class OutcomeContentStatus(StrEnum):
    AVAILABLE = "available"
    ERASED = "erased"
    MISSING = "missing"
    INTEGRITY_ERROR = "integrity_error"


@dataclass(frozen=True, slots=True)
class ActionAttemptRecord:
    attempt_id: str
    authorization_event_id: str
    selection_event_id: str
    frame_id: str
    candidate_id: str
    subject: str
    executor: str
    idempotency_key: str
    sensitivity: Sensitivity
    attempted_at: datetime


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    outcome_id: str
    attempt_id: str
    kind: OutcomeKind
    subject: str
    source_event_id: str
    details: Any
    content_id: str
    content_status: OutcomeContentStatus
    sensitivity: Sensitivity
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class OutcomeProjectionDecision:
    event_id: str
    outcome: str
    reason: str
    attempt_id: str | None
    outcome_id: str | None


_SOURCE_TYPES = {
    OutcomeKind.DELIVERY_SUCCEEDED: {"delivery.succeeded"},
    OutcomeKind.DELIVERY_FAILED: {"delivery.failed"},
    OutcomeKind.USER_REPLIED: {"conversation.inbound"},
    OutcomeKind.USER_CORRECTED: {"conversation.inbound"},
    OutcomeKind.USER_DISMISSED: {"conversation.inbound"},
    OutcomeKind.EXPLICIT_FEEDBACK: {"conversation.inbound"},
    OutcomeKind.TASK_COMPLETED: {"task.completed"},
    OutcomeKind.TASK_FAILED: {"task.failed"},
}


class OutcomeProjection:
    """Projects attempts and observations; never performs the action itself."""

    CHECKPOINT = "alive-outcomes-v1"

    def __init__(
        self, journal: ExperienceJournal, *, content_vault: ContentVault | None = None
    ) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        self.content_vault = content_vault or ContentVault(
            self.path.parent / f"{self.path.stem}-content-vault",
            backup_root=self.path.parent / f"{self.path.stem}-content-backups",
        )
        self.receipt_protector = LocalIdentityProtector(
            self.path.parent / "identity.key"
        )
        self.autonomy = AutonomyPolicyProjection(journal)
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
                CREATE TABLE IF NOT EXISTS action_attempts_v1 (
                    attempt_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    selection_event_id TEXT NOT NULL,
                    frame_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    executor TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    sensitivity TEXT NOT NULL,
                    attempted_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS action_outcomes_v1 (
                    outcome_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    attempt_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(attempt_id, kind, source_event_id),
                    FOREIGN KEY(attempt_id) REFERENCES action_attempts_v1(attempt_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS outcome_projection_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    attempt_id TEXT,
                    outcome_id TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(action_attempts_v1)")
            }
            if "authorization_event_id" not in columns:
                connection.execute(
                    "ALTER TABLE action_attempts_v1 ADD COLUMN authorization_event_id TEXT"
                )

    def _append_idempotent(self, event: EventEnvelope) -> JournalRecord:
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
                raise OutcomeValidationError(
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

    def append_attempt(
        self,
        *,
        authorization_event_id: str,
        selection_event_id: str,
        candidate_id: str,
        executor: str,
        idempotency_key: str,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        attempt_id: str | None = None,
    ) -> JournalRecord:
        attempt_id = str(attempt_id or uuid4()).strip()
        if not all(
            str(value).strip()
            for value in (
                attempt_id,
                authorization_event_id,
                selection_event_id,
                candidate_id,
                executor,
                idempotency_key,
            )
        ):
            raise OutcomeValidationError("attempt fields are required")
        event = EventEnvelope(
            event_id=f"action.attempt:{attempt_id}",
            event_type="action.attempted",
            source="alive.outcomes",
            actor=actor,
            subject=subject,
            causation_id=authorization_event_id,
            sensitivity=Sensitivity(sensitivity),
            payload={
                "attempt_id": attempt_id,
                "authorization_event_id": authorization_event_id,
                "selection_event_id": selection_event_id,
                "candidate_id": candidate_id,
                "executor": executor,
                "idempotency_key": idempotency_key,
            },
        )
        return self._append_idempotent(event)

    def append_outcome(
        self,
        *,
        attempt_id: str,
        kind: OutcomeKind,
        source_event_id: str,
        details: Any,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        outcome_id: str | None = None,
    ) -> JournalRecord:
        outcome_id = str(outcome_id or uuid4()).strip()
        if not outcome_id or not str(attempt_id).strip() or not str(source_event_id).strip():
            raise OutcomeValidationError("outcome identifiers are required")
        kind = OutcomeKind(kind)
        sensitivity = Sensitivity(sensitivity)
        content = self.content_vault.put_json(
            details,
            subject=subject,
            purpose=f"outcome.{kind.value}",
            sensitivity=sensitivity,
            content_id=f"outcome:{outcome_id}",
        )
        event = EventEnvelope(
            event_id=f"outcome.record:{outcome_id}",
            event_type="outcome.recorded",
            source="alive.outcomes",
            actor=actor,
            subject=subject,
            causation_id=source_event_id,
            sensitivity=sensitivity,
            payload={
                "outcome_id": outcome_id,
                "attempt_id": attempt_id,
                "kind": kind.value,
                "source_event_id": source_event_id,
                "content": content.to_event_payload(),
            },
        )
        return self._append_idempotent(event)

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        attempt_id: str | None,
        outcome_id: str | None,
    ) -> OutcomeProjectionDecision:
        connection.execute(
            "INSERT INTO outcome_projection_decisions_v1 VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                outcome,
                reason,
                attempt_id,
                outcome_id,
                event.observed_at.isoformat(),
            ),
        )
        return OutcomeProjectionDecision(
            event.event_id, outcome, reason, attempt_id, outcome_id
        )

    def apply(self, record: JournalRecord) -> OutcomeProjectionDecision:
        event = record.event
        if event.event_type not in {"action.attempted", "outcome.recorded"}:
            raise OutcomeValidationError("unsupported outcome event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM outcome_projection_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return OutcomeProjectionDecision(
                        event.event_id,
                        existing["outcome"],
                        existing["reason"],
                        existing["attempt_id"],
                        existing["outcome_id"],
                    )
                decision = (
                    self._apply_attempt(connection, event)
                    if event.event_type == "action.attempted"
                    else self._apply_outcome(connection, event)
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_attempt(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> OutcomeProjectionDecision:
        payload = event.payload
        attempt_id = str(payload.get("attempt_id") or "")
        authorization_event_id = str(payload.get("authorization_event_id") or "")
        selection_event_id = str(payload.get("selection_event_id") or "")
        candidate_id = str(payload.get("candidate_id") or "")
        authorization = self.journal.get(authorization_event_id)
        authorization_payload = (
            _thaw_json(authorization.event.payload) if authorization is not None else {}
        )
        authenticator = authorization_payload.pop("integrity_authenticator", None)
        receipt_authenticated = self.receipt_protector.verify_json(
            "action.authorization.v1", authorization_payload, authenticator
        )
        policy_event_id = str(authorization_payload.get("policy_event_id") or "")
        policy_event = self.journal.get(policy_event_id)
        policy_payload = (
            _thaw_json(policy_event.event.payload) if policy_event is not None else {}
        )
        policy_authenticator = policy_payload.pop("integrity_authenticator", None)
        policy_authenticated = self.receipt_protector.verify_json(
            "autonomy.policy.v1", policy_payload, policy_authenticator
        )
        policy_decision = connection.execute(
            "SELECT outcome FROM autonomy_policy_decisions_v1 WHERE event_id=?",
            (policy_event_id,),
        ).fetchone()
        policy_superseded_before_attempt = False
        if policy_event is not None:
            for later in self.journal.iter_replay(after_sequence=policy_event.sequence):
                if later.sequence >= self.journal.get(event.event_id).sequence:
                    break
                if (
                    later.event.event_type == "autonomy.policy_changed"
                    and later.event.subject == event.subject
                ):
                    later_decision = connection.execute(
                        """
                        SELECT outcome FROM autonomy_policy_decisions_v1
                        WHERE event_id=?
                        """,
                        (later.event.event_id,),
                    ).fetchone()
                    if later_decision is not None and later_decision["outcome"] == "recorded":
                        policy_superseded_before_attempt = True
                        break
        valid_until = None
        if authorization is not None:
            try:
                parsed_until = datetime.fromisoformat(
                    str(authorization.event.payload.get("valid_until") or "")
                )
                valid_until = (
                    parsed_until.astimezone(timezone.utc)
                    if parsed_until.tzinfo is not None
                    and parsed_until.utcoffset() is not None
                    else None
                )
            except ValueError:
                valid_until = None
        if (
            authorization is None
            or not receipt_authenticated
            or authorization.event.event_type != "action.authorization_evaluated"
            or authorization.event.source != "alive.authorization"
            or authorization.event.actor != "system:alive-authorizer"
            or authorization.event.payload.get("outcome") != "authorized"
            or tuple(authorization.event.payload.get("reasons", ()))
            or authorization.event.payload.get("executes_action") is not False
            or policy_event is None
            or not policy_authenticated
            or policy_decision is None
            or policy_decision["outcome"] != "recorded"
            or policy_event.event.event_type != "autonomy.policy_changed"
            or policy_event.event.source != "hermes.command.alive"
            or policy_event.event.actor != event.subject
            or policy_event.event.subject != event.subject
            or policy_event.event.sensitivity is not Sensitivity.PRIVATE
            or policy_payload.get("enabled") is not True
            or policy_payload.get("revision")
            != authorization_payload.get("policy_revision")
            or policy_event.sequence >= authorization.sequence
            or policy_event.event.observed_at > authorization.event.observed_at
            or policy_superseded_before_attempt
            or authorization.event.payload.get("selection_event_id")
            != selection_event_id
            or authorization.event.payload.get("candidate_id") != candidate_id
            or authorization.event.payload.get("capability")
            != str(payload.get("executor") or "")
            or authorization.event.subject != event.subject
            or authorization.event.sensitivity is not event.sensitivity
            or authorization.sequence >= self.journal.get(event.event_id).sequence
            or valid_until is None
            or authorization.event.expires_at != valid_until
            or not timedelta(0)
            < valid_until - authorization.event.observed_at
            <= timedelta(seconds=60)
            or event.observed_at < authorization.event.observed_at
            or event.observed_at >= valid_until
            or event.causation_id != authorization_event_id
        ):
            return self._decision(
                connection,
                event,
                "rejected",
                "authorization_invalid_or_expired",
                attempt_id or None,
                None,
            )
        selection = connection.execute(
            """
            SELECT s.*, f.subject, f.content_id AS frame_content_id,
                   f.sensitivity AS frame_sensitivity
            FROM deliberation_selections_v1 s
            JOIN deliberation_frames_v1 f ON f.frame_id=s.frame_id
            WHERE s.event_id=?
            """,
            (selection_event_id,),
        ).fetchone()
        if selection is None or selection["outcome"] != "validated":
            return self._decision(
                connection, event, "rejected", "selection_not_validated", attempt_id or None, None
            )
        latest_selection = connection.execute(
            """
            SELECT event_id FROM deliberation_selections_v1
            WHERE frame_id=? AND outcome='validated'
            ORDER BY rowid DESC LIMIT 1
            """,
            (selection["frame_id"],),
        ).fetchone()
        latest_gate = connection.execute(
            """
            SELECT event_id FROM exploration_evaluations_v1
            WHERE frame_id=? ORDER BY rowid DESC LIMIT 1
            """,
            (selection["frame_id"],),
        ).fetchone()
        if (
            latest_selection is None
            or latest_selection["event_id"] != selection_event_id
            or latest_gate is None
            or latest_gate["event_id"] != selection["exploration_gate_event_id"]
            or authorization.event.payload.get("frame_id") != selection["frame_id"]
            or authorization.event.payload.get("gate_event_id")
            != selection["exploration_gate_event_id"]
        ):
            return self._decision(
                connection,
                event,
                "rejected",
                "authorization_state_superseded",
                attempt_id or None,
                None,
            )
        if (
            candidate_id != selection["candidate_id"]
            or event.subject != selection["subject"]
            or event.sensitivity.value != selection["frame_sensitivity"]
        ):
            return self._decision(
                connection, event, "rejected", "attempt_boundary_mismatch", attempt_id or None, None
            )
        frame_document = self.content_vault.resolve_json(
            selection["frame_content_id"],
            expected_subject=selection["subject"],
            expected_purpose="deliberation.frame",
            expected_sensitivity=Sensitivity(selection["frame_sensitivity"]),
        )
        frame, _context = deserialize_frame(frame_document)
        candidate = next(
            (item for item in frame.candidates if item.candidate_id == candidate_id), None
        )
        if candidate is None or candidate.action_kind is ActionKind.SILENCE:
            return self._decision(
                connection, event, "rejected", "candidate_not_executable", attempt_id or None, None
            )
        try:
            contract_document = self.content_vault.resolve_json(
                str(candidate.content_id),
                expected_subject=str(selection["subject"]),
                expected_purpose="deliberation.candidate",
                expected_sensitivity=Sensitivity(selection["frame_sensitivity"]),
            )
            contract = parse_action_contract(
                contract_document,
                capability=str(payload.get("executor") or ""),
            )
        except (
            ActionContractError,
            ContentErasedError,
            ContentIntegrityError,
            ContentUnavailableError,
        ):
            return self._decision(
                connection,
                event,
                "rejected",
                "action_contract_invalid",
                attempt_id or None,
                None,
            )
        if (
            authorization.event.payload.get("action_contract_version") != 1
            or not self.receipt_protector.verify_json(
                "action.contract.v1",
                contract.to_document(),
                authorization.event.payload.get("action_contract_binding"),
            )
        ):
            return self._decision(
                connection,
                event,
                "rejected",
                "action_contract_not_authorized",
                attempt_id or None,
                None,
            )
        if candidate.agenda_item_id is not None:
            agenda = connection.execute(
                "SELECT state, subject, sensitivity FROM agenda_items_v1 WHERE item_id=?",
                (candidate.agenda_item_id,),
            ).fetchone()
            if (
                agenda is None
                or agenda["state"] != "active"
                or agenda["subject"] != event.subject
                or agenda["sensitivity"] != event.sensitivity.value
            ):
                return self._decision(
                    connection,
                    event,
                    "rejected",
                    "authorization_agenda_superseded",
                    attempt_id or None,
                    None,
                )
        existing_key = connection.execute(
            "SELECT attempt_id FROM action_attempts_v1 WHERE idempotency_key=?",
            (str(payload.get("idempotency_key") or ""),),
        ).fetchone()
        if existing_key is not None:
            reason = (
                "attempt_deduplicated"
                if existing_key["attempt_id"] == attempt_id
                else "idempotency_key_conflict"
            )
            return self._decision(
                connection,
                event,
                "deduplicated" if reason == "attempt_deduplicated" else "rejected",
                reason,
                existing_key["attempt_id"],
                None,
            )
        executor = str(payload.get("executor") or "").strip()
        idempotency_key = str(payload.get("idempotency_key") or "").strip()
        if not all((attempt_id, executor, idempotency_key)):
            return self._decision(
                connection, event, "rejected", "attempt_payload_invalid", attempt_id or None, None
            )
        connection.execute(
            """
            INSERT INTO action_attempts_v1(
                attempt_id, event_id, selection_event_id, frame_id, candidate_id,
                subject, executor, idempotency_key, sensitivity, attempted_at,
                authorization_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                event.event_id,
                selection_event_id,
                selection["frame_id"],
                candidate_id,
                event.subject,
                executor,
                idempotency_key,
                event.sensitivity.value,
                event.observed_at.isoformat(),
                authorization_event_id,
            ),
        )
        return self._decision(
            connection, event, "recorded", "validated_action_attempt", attempt_id, None
        )

    def _apply_outcome(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> OutcomeProjectionDecision:
        payload = event.payload
        outcome_id = str(payload.get("outcome_id") or "")
        attempt_id = str(payload.get("attempt_id") or "")
        try:
            kind = OutcomeKind(payload["kind"])
            source_event_id = str(payload["source_event_id"])
            content = ContentReference.from_event_payload(payload["content"])
        except (KeyError, TypeError, ValueError):
            return self._decision(
                connection, event, "rejected", "outcome_payload_invalid", attempt_id or None, outcome_id or None
            )
        attempt = connection.execute(
            "SELECT * FROM action_attempts_v1 WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
        source = self.journal.get(source_event_id)
        attempt_event = self.journal.get(str(attempt["event_id"])) if attempt else None
        if attempt is None:
            return self._decision(
                connection, event, "rejected", "unknown_attempt", attempt_id or None, outcome_id or None
            )
        if (
            source is None
            or attempt_event is None
            or source.sequence <= attempt_event.sequence
            or source.event.event_type not in _SOURCE_TYPES[kind]
            or event.causation_id != source_event_id
        ):
            return self._decision(
                connection, event, "rejected", "invalid_outcome_source", attempt_id, outcome_id or None
            )
        if (
            event.subject != attempt["subject"]
            or source.event.subject != attempt["subject"]
            or event.sensitivity.value != attempt["sensitivity"]
            or content.sensitivity is not event.sensitivity
        ):
            return self._decision(
                connection, event, "rejected", "outcome_boundary_mismatch", attempt_id, outcome_id or None
            )
        if kind in {
            OutcomeKind.USER_REPLIED,
            OutcomeKind.USER_CORRECTED,
            OutcomeKind.USER_DISMISSED,
            OutcomeKind.EXPLICIT_FEEDBACK,
        } and source.event.actor != event.actor:
            return self._decision(
                connection, event, "rejected", "user_outcome_actor_mismatch", attempt_id, outcome_id or None
            )
        try:
            self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose=f"outcome.{kind.value}",
                expected_sensitivity=event.sensitivity,
            )
        except ContentErasedError:
            pass
        except (ContentUnavailableError, ContentIntegrityError):
            return self._decision(
                connection, event, "rejected", "outcome_content_unavailable", attempt_id, outcome_id or None
            )
        duplicate = connection.execute(
            """
            SELECT outcome_id FROM action_outcomes_v1
            WHERE attempt_id=? AND kind=? AND source_event_id=?
            """,
            (attempt_id, kind.value, source_event_id),
        ).fetchone()
        if duplicate is not None:
            return self._decision(
                connection,
                event,
                "deduplicated",
                "same_observation",
                attempt_id,
                duplicate["outcome_id"],
            )
        connection.execute(
            "INSERT INTO action_outcomes_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                outcome_id,
                event.event_id,
                attempt_id,
                kind.value,
                event.subject,
                source_event_id,
                content.content_id,
                event.sensitivity.value,
                event.observed_at.isoformat(),
            ),
        )
        return self._decision(
            connection, event, "recorded", "observed_outcome", attempt_id, outcome_id
        )

    def project_new(self, *, limit: int = 1000) -> list[OutcomeProjectionDecision]:
        decisions: list[OutcomeProjectionDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type in {"action.attempted", "outcome.recorded"}:
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[OutcomeProjectionDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM action_outcomes_v1")
            connection.execute("DELETE FROM action_attempts_v1")
            connection.execute("DELETE FROM outcome_projection_decisions_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        decisions: list[OutcomeProjectionDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("outcome replay made no progress")
        return decisions

    def attempts(self, *, clearance: Sensitivity) -> list[ActionAttemptRecord]:
        allowed = list(Sensitivity)[: list(Sensitivity).index(Sensitivity(clearance)) + 1]
        with closing(self._connect()) as connection:
            placeholders = ",".join("?" for _ in allowed)
            rows = connection.execute(
                "SELECT * FROM action_attempts_v1 "
                f"WHERE sensitivity IN ({placeholders}) ORDER BY rowid",
                tuple(value.value for value in allowed),
            )
            return [
                ActionAttemptRecord(
                    row["attempt_id"],
                    row["authorization_event_id"],
                    row["selection_event_id"],
                    row["frame_id"],
                    row["candidate_id"],
                    row["subject"],
                    row["executor"],
                    row["idempotency_key"],
                    Sensitivity(row["sensitivity"]),
                    datetime.fromisoformat(row["attempted_at"]),
                )
                for row in rows
            ]

    def outcomes(
        self, attempt_id: str, *, clearance: Sensitivity
    ) -> list[OutcomeRecord]:
        allowed = list(Sensitivity)[: list(Sensitivity).index(Sensitivity(clearance)) + 1]
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM action_outcomes_v1
                WHERE attempt_id=? AND sensitivity IN ({','.join('?' for _ in allowed)})
                ORDER BY rowid
                """,
                (attempt_id, *(value.value for value in allowed)),
            ).fetchall()
            records: list[OutcomeRecord] = []
            for row in rows:
                sensitivity = Sensitivity(row["sensitivity"])
                try:
                    details = self.content_vault.resolve_json(
                        row["content_id"],
                        expected_subject=row["subject"],
                        expected_purpose=f"outcome.{row['kind']}",
                        expected_sensitivity=sensitivity,
                    )
                    status = OutcomeContentStatus.AVAILABLE
                except ContentErasedError:
                    details, status = None, OutcomeContentStatus.ERASED
                except ContentUnavailableError:
                    details, status = None, OutcomeContentStatus.MISSING
                except ContentIntegrityError:
                    details, status = None, OutcomeContentStatus.INTEGRITY_ERROR
                records.append(
                    OutcomeRecord(
                        row["outcome_id"],
                        row["attempt_id"],
                        OutcomeKind(row["kind"]),
                        row["subject"],
                        row["source_event_id"],
                        details,
                        row["content_id"],
                        status,
                        sensitivity,
                        datetime.fromisoformat(row["observed_at"]),
                    )
                )
            return records
