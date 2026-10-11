"""Durable, replayable audit trail for Alive deliberation."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
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
from .deliberation import (
    ActionCandidate,
    DeliberationFrame,
    DeliberationValidationError,
    PolicyContext,
    SelectionProposal,
    ValidatedSelection,
    build_frame,
    deserialize_frame,
    serialize_frame,
    validate_selection,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity


@dataclass(frozen=True, slots=True)
class DeliberationAuditDecision:
    event_id: str
    outcome: str
    reason: str
    frame_id: str | None
    candidate_id: str | None


@dataclass(frozen=True, slots=True)
class StoredDeliberation:
    frame: DeliberationFrame
    context: PolicyContext
    candidate_contents: tuple[tuple[str, Any], ...]
    selection: ValidatedSelection | None
    selection_outcome: str | None
    selection_reason: str | None


class DeliberationProjection:
    """Stores deliberation facts without executing the selected action."""

    CHECKPOINT = "alive-deliberation-v1"
    FRAME_CHECKPOINT = "alive-deliberation-frames-v1"

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
                CREATE TABLE IF NOT EXISTS deliberation_frames_v1 (
                    frame_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    silence_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deliberation_selections_v1 (
                    event_id TEXT PRIMARY KEY,
                    selection_id TEXT NOT NULL UNIQUE,
                    frame_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    exploration_gate_event_id TEXT,
                    model TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    FOREIGN KEY(frame_id) REFERENCES deliberation_frames_v1(frame_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS deliberation_audit_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    frame_id TEXT,
                    candidate_id TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
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
                raise DeliberationValidationError(
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

    def append_frame(
        self,
        candidates: Iterable[ActionCandidate],
        context: PolicyContext,
        *,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        frame_id: str | None = None,
        causation_id: str | None = None,
        correlation_id: str | None = None,
        candidate_contents: Mapping[str, Any] | None = None,
    ) -> tuple[JournalRecord, DeliberationFrame]:
        frame = build_frame(candidates, context, frame_id=frame_id)
        sensitivity = Sensitivity(sensitivity)
        supplied_contents = dict(candidate_contents or {})
        required_ids = {
            str(candidate.content_id)
            for candidate in frame.candidates
            if candidate.content_id is not None
        }
        if set(supplied_contents) != required_ids:
            raise DeliberationValidationError(
                "candidate_contents must exactly cover non-silence content IDs"
            )
        for content_id, value in supplied_contents.items():
            self.content_vault.put_json(
                value,
                subject=subject,
                purpose="deliberation.candidate",
                sensitivity=sensitivity,
                content_id=content_id,
            )
        content = self.content_vault.put_json(
            serialize_frame(frame, context),
            subject=subject,
            purpose="deliberation.frame",
            sensitivity=sensitivity,
            content_id=f"deliberation-frame:{frame.frame_id}",
        )
        event = EventEnvelope(
            event_id=f"deliberation.frame:{frame.frame_id}",
            event_type="deliberation.framed",
            source="alive.deliberation",
            actor=actor,
            subject=subject,
            causation_id=causation_id,
            correlation_id=correlation_id,
            sensitivity=sensitivity,
            payload={
                "frame_id": frame.frame_id,
                "content": content.to_event_payload(),
                "silence_id": frame.silence_id,
                "candidate_ids": [item.candidate_id for item in frame.candidates],
            },
        )
        return self._append_idempotent(event), frame

    def append_selection(
        self,
        proposal: SelectionProposal,
        *,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        selection_id: str | None = None,
        exploration_gate_event_id: str | None = None,
    ) -> JournalRecord:
        selection_id = str(selection_id or uuid4()).strip()
        if not selection_id:
            raise DeliberationValidationError("selection_id is required")
        sensitivity = Sensitivity(sensitivity)
        content = self.content_vault.put_json(
            {"rationale": proposal.rationale},
            subject=subject,
            purpose="deliberation.selection",
            sensitivity=sensitivity,
            content_id=f"deliberation-selection:{selection_id}",
        )
        event = EventEnvelope(
            event_id=f"deliberation.selection:{selection_id}",
            event_type="deliberation.selected",
            source="alive.deliberation",
            actor=actor,
            subject=subject,
            causation_id=(
                exploration_gate_event_id
                or f"deliberation.frame:{proposal.frame_id}"
            ),
            sensitivity=sensitivity,
            payload={
                "selection_id": selection_id,
                "frame_id": proposal.frame_id,
                "candidate_id": proposal.candidate_id,
                "exploration_gate_event_id": exploration_gate_event_id,
                "model": proposal.model,
                "content": content.to_event_payload(),
            },
        )
        return self._append_idempotent(event)

    def _audit(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        frame_id: str | None,
        candidate_id: str | None,
    ) -> DeliberationAuditDecision:
        connection.execute(
            "INSERT INTO deliberation_audit_v1 VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                outcome,
                reason,
                frame_id,
                candidate_id,
                event.observed_at.isoformat(),
            ),
        )
        return DeliberationAuditDecision(
            event.event_id, outcome, reason, frame_id, candidate_id
        )

    def apply(self, record: JournalRecord) -> DeliberationAuditDecision:
        event = record.event
        if event.event_type not in {"deliberation.framed", "deliberation.selected"}:
            raise DeliberationValidationError("unsupported deliberation event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM deliberation_audit_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return DeliberationAuditDecision(
                        event.event_id,
                        existing["outcome"],
                        existing["reason"],
                        existing["frame_id"],
                        existing["candidate_id"],
                    )
                decision = (
                    self._apply_frame(connection, event)
                    if event.event_type == "deliberation.framed"
                    else self._apply_selection(connection, event)
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _apply_frame(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> DeliberationAuditDecision:
        try:
            frame_id = str(event.payload["frame_id"])
            content = ContentReference.from_event_payload(event.payload["content"])
            document = self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose="deliberation.frame",
                expected_sensitivity=event.sensitivity,
            )
            frame, _context = deserialize_frame(document)
            evidence_ids = {
                evidence_id
                for candidate in frame.candidates
                if candidate.dimensions is not None
                for name in (
                    "user_value",
                    "urgency",
                    "novelty",
                    "confidence",
                    "interruption_cost",
                    "risk",
                )
                for evidence_id in getattr(
                    candidate.dimensions, name
                ).evidence_event_ids
            }
            evidence_records = [self.journal.get(value) for value in evidence_ids]
            evidence_ok = all(
                record is not None and record.event.subject in {None, event.subject}
                for record in evidence_records
            )
            agenda_schema = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='agenda_items_v1'"
            ).fetchone()
            agenda_ok = True
            for candidate in frame.candidates:
                if candidate.agenda_item_id is None:
                    continue
                row = (
                    connection.execute(
                        "SELECT subject, state FROM agenda_items_v1 WHERE item_id=?",
                        (candidate.agenda_item_id,),
                    ).fetchone()
                    if agenda_schema is not None
                    else None
                )
                if (
                    row is None
                    or row["subject"] != event.subject
                    or row["state"] != "active"
                ):
                    agenda_ok = False
                    break
            contents_ok = True
            for candidate in frame.candidates:
                if candidate.content_id is None:
                    continue
                self.content_vault.resolve_json(
                    candidate.content_id,
                    expected_subject=event.subject,
                    expected_purpose="deliberation.candidate",
                    expected_sensitivity=event.sensitivity,
                )
            boundary_ok = (
                frame.frame_id == frame_id
                and frame.silence_id == event.payload["silence_id"]
                and [item.candidate_id for item in frame.candidates]
                == list(event.payload["candidate_ids"])
                and evidence_ok
                and agenda_ok
                and contents_ok
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            ContentUnavailableError,
            ContentIntegrityError,
            DeliberationValidationError,
        ) as exc:
            return self._audit(
                connection, event, "rejected", f"invalid_frame:{type(exc).__name__}", None, None
            )
        if not boundary_ok or event.subject is None:
            return self._audit(connection, event, "rejected", "frame_boundary_mismatch", None, None)
        connection.execute(
            "INSERT INTO deliberation_frames_v1 VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                frame_id,
                event.event_id,
                event.subject,
                content.content_id,
                event.sensitivity.value,
                frame.silence_id,
                event.observed_at.isoformat(),
            ),
        )
        return self._audit(connection, event, "recorded", "policy_recomputed", frame_id, None)

    def _apply_selection(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> DeliberationAuditDecision:
        payload = event.payload
        frame_id = str(payload.get("frame_id") or "")
        candidate_id = str(payload.get("candidate_id") or "")
        frame_row = connection.execute(
            "SELECT * FROM deliberation_frames_v1 WHERE frame_id=?", (frame_id,)
        ).fetchone()
        if frame_row is None:
            return self._audit(
                connection, event, "rejected", "unknown_frame", frame_id or None, candidate_id or None
            )
        try:
            frame_document = self.content_vault.resolve_json(
                frame_row["content_id"],
                expected_subject=frame_row["subject"],
                expected_purpose="deliberation.frame",
                expected_sensitivity=Sensitivity(frame_row["sensitivity"]),
            )
            frame, _context = deserialize_frame(frame_document)
            content = ContentReference.from_event_payload(payload["content"])
            rationale_document = self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose="deliberation.selection",
                expected_sensitivity=event.sensitivity,
            )
            proposal = SelectionProposal(
                frame_id=frame_id,
                candidate_id=candidate_id,
                model=str(payload["model"]),
                rationale=str(rationale_document["rationale"]),
            )
            selection = validate_selection(frame, proposal)
            gate_event_id = str(payload.get("exploration_gate_event_id") or "")
            if selection.candidate.action_kind.value != "silence":
                gate_schema = connection.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type='table' AND name='exploration_evaluations_v1'
                    """
                ).fetchone()
                gate = connection.execute(
                    """
                    SELECT e.*, d.outcome AS decision_outcome
                    FROM exploration_evaluations_v1 e
                    JOIN exploration_decisions_v1 d ON d.event_id=e.event_id
                    WHERE e.event_id=? AND e.frame_id=?
                    """,
                    (gate_event_id, frame_id),
                ).fetchone() if gate_event_id and gate_schema else None
                gate_record = self.journal.get(gate_event_id) if gate_event_id else None
                selection_record = self.journal.get(event.event_id)
                if (
                    gate is None
                    or gate["decision_outcome"] != "recorded"
                    or candidate_id not in json.loads(gate["admissible_json"])
                    or gate_record is None
                    or selection_record is None
                    or gate_record.sequence >= selection_record.sequence
                    or event.causation_id != gate_event_id
                ):
                    raise DeliberationValidationError(
                        "selection lacks an admissible exploration receipt"
                    )
            if (
                event.subject != frame_row["subject"]
                or event.sensitivity.value != frame_row["sensitivity"]
            ):
                raise DeliberationValidationError("selection subject does not match frame")
            outcome, reason = "validated", "selection_within_policy"
        except DeliberationValidationError as exc:
            reason = {
                "selection belongs to a different frame": "selection_frame_mismatch",
                "model selected an unknown candidate": "unknown_candidate",
                "model selected a policy-rejected candidate": "policy_rejected_candidate",
                "selection requires model provenance and rationale": "selection_metadata_missing",
                "selection subject does not match frame": "selection_boundary_mismatch",
                "selection lacks an admissible exploration receipt": "exploration_gate_invalid",
            }.get(str(exc), "invalid_selection")
            outcome = "rejected"
            selection = None
            content_id = str(payload.get("content", {}).get("content_id") or "")
        except (ContentUnavailableError, ContentIntegrityError):
            outcome, reason = "rejected", "selection_content_unavailable"
            selection = None
            content_id = str(payload.get("content", {}).get("content_id") or "")
        except (KeyError, TypeError, ValueError):
            outcome, reason = "rejected", "selection_payload_invalid"
            selection = None
            content_id = str(payload.get("content", {}).get("content_id") or "")
        else:
            content_id = content.content_id
        connection.execute(
            "INSERT INTO deliberation_selections_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                str(payload.get("selection_id") or ""),
                frame_id,
                candidate_id,
                str(payload.get("exploration_gate_event_id") or "") or None,
                str(payload.get("model") or ""),
                content_id,
                outcome,
                reason,
                event.observed_at.isoformat(),
            ),
        )
        return self._audit(connection, event, outcome, reason, frame_id, candidate_id)

    def project_new(self, *, limit: int = 1000) -> list[DeliberationAuditDecision]:
        decisions: list[DeliberationAuditDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type in {"deliberation.framed", "deliberation.selected"}:
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def project_frames_new(
        self, *, limit: int = 1000
    ) -> list[DeliberationAuditDecision]:
        """Pre-project frames so exploration can replay before selections."""

        decisions: list[DeliberationAuditDecision] = []
        start = self.journal.checkpoint(self.FRAME_CHECKPOINT)
        for index, record in enumerate(
            self.journal.iter_replay(after_sequence=start), start=1
        ):
            if record.event.event_type == "deliberation.framed":
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.FRAME_CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[DeliberationAuditDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM deliberation_selections_v1")
            connection.execute("DELETE FROM deliberation_audit_v1")
            connection.execute("DELETE FROM deliberation_frames_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?",
                (self.FRAME_CHECKPOINT,),
            )
            connection.execute("COMMIT")
        decisions: list[DeliberationAuditDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("deliberation replay made no progress")
        return decisions

    def inspect(self, frame_id: str, *, clearance: Sensitivity) -> StoredDeliberation | None:
        clearance = Sensitivity(clearance)
        sensitivity_order = list(Sensitivity)
        with closing(self._connect()) as connection:
            frame_row = connection.execute(
                "SELECT * FROM deliberation_frames_v1 WHERE frame_id=?", (frame_id,)
            ).fetchone()
            if frame_row is None:
                return None
            stored_sensitivity = Sensitivity(frame_row["sensitivity"])
            if sensitivity_order.index(stored_sensitivity) > sensitivity_order.index(clearance):
                return None
            document = self.content_vault.resolve_json(
                frame_row["content_id"],
                expected_subject=frame_row["subject"],
                expected_purpose="deliberation.frame",
                expected_sensitivity=stored_sensitivity,
            )
            frame, context = deserialize_frame(document)
            candidate_contents = tuple(
                (
                    str(candidate.content_id),
                    self.content_vault.resolve_json(
                        str(candidate.content_id),
                        expected_subject=frame_row["subject"],
                        expected_purpose="deliberation.candidate",
                        expected_sensitivity=stored_sensitivity,
                    ),
                )
                for candidate in frame.candidates
                if candidate.content_id is not None
            )
            selection_row = connection.execute(
                "SELECT * FROM deliberation_selections_v1 WHERE frame_id=? ORDER BY rowid DESC LIMIT 1",
                (frame_id,),
            ).fetchone()
            if selection_row is None:
                return StoredDeliberation(
                    frame, context, candidate_contents, None, None, None
                )
            selection = None
            if selection_row["outcome"] == "validated":
                rationale = self.content_vault.resolve_json(
                    selection_row["content_id"],
                    expected_subject=frame_row["subject"],
                    expected_purpose="deliberation.selection",
                    expected_sensitivity=stored_sensitivity,
                )["rationale"]
                selection = validate_selection(
                    frame,
                    SelectionProposal(
                        frame_id,
                        selection_row["candidate_id"],
                        selection_row["model"],
                        rationale,
                    ),
                )
            return StoredDeliberation(
                frame,
                context,
                candidate_contents,
                selection,
                selection_row["outcome"],
                selection_row["reason"],
            )

    def latest_selection_event_id(self, frame_id: str) -> str | None:
        """Return the latest successfully validated selection for a frame."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT event_id FROM deliberation_selections_v1
                WHERE frame_id=? AND outcome='validated'
                ORDER BY rowid DESC LIMIT 1
                """,
                (frame_id,),
            ).fetchone()
            return None if row is None else str(row["event_id"])
