"""Durable diversity annotations, exposure history, and exploration receipts."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Iterable
from uuid import uuid4

from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .deliberation import deserialize_frame
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity
from .exploration import (
    DiversityAnnotation,
    DiversityTagger,
    ExplorationGateResult,
    ExplorationMode,
    ExplorationPolicy,
    ExplorationRejection,
    ExplorationValidationError,
    ExposureRecord,
    apply_exploration_gate,
)
from .outcomes import OutcomeKind, OutcomeProjection


@dataclass(frozen=True, slots=True)
class ExplorationProjectionDecision:
    event_id: str
    outcome: str
    reason: str
    frame_id: str | None


class ExplorationProjection:
    CHECKPOINT = "alive-exploration-v1"

    def __init__(
        self, journal: ExperienceJournal, *, content_vault: ContentVault | None = None
    ) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        self.content_vault = content_vault or ContentVault(
            self.path.parent / f"{self.path.stem}-content-vault",
            backup_root=self.path.parent / f"{self.path.stem}-content-backups",
        )
        self.tagger = DiversityTagger(self.content_vault)
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
                CREATE TABLE IF NOT EXISTS exploration_annotations_v1 (
                    annotation_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    frame_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    topic_digest TEXT NOT NULL,
                    source_digest TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(frame_id, candidate_id),
                    FOREIGN KEY(frame_id) REFERENCES deliberation_frames_v1(frame_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS exploration_evaluations_v1 (
                    evaluation_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    frame_id TEXT NOT NULL,
                    admissible_json TEXT NOT NULL,
                    rejections_json TEXT NOT NULL,
                    history_json TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(frame_id) REFERENCES deliberation_frames_v1(frame_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS exploration_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    frame_id TEXT,
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
                raise ExplorationValidationError(
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

    def append_annotation(
        self,
        *,
        frame_id: str,
        candidate_id: str,
        topic: str,
        source_label: str,
        mode: ExplorationMode,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        annotation_id: str | None = None,
    ) -> tuple[JournalRecord, DiversityAnnotation]:
        annotation_id = str(annotation_id or uuid4()).strip()
        annotation = self.tagger.annotate(
            candidate_id, topic=topic, source=source_label, mode=mode
        )
        sensitivity = Sensitivity(sensitivity)
        content = self.content_vault.put_json(
            {"topic": topic, "source": source_label},
            subject=subject,
            purpose="exploration.annotation",
            sensitivity=sensitivity,
            content_id=f"exploration-annotation:{annotation_id}",
        )
        event = EventEnvelope(
            event_id=f"exploration.annotation:{annotation_id}",
            event_type="exploration.annotated",
            source="alive.exploration",
            actor=actor,
            subject=subject,
            causation_id=f"deliberation.frame:{frame_id}",
            sensitivity=sensitivity,
            payload={
                "annotation_id": annotation_id,
                "frame_id": frame_id,
                "candidate_id": candidate_id,
                "topic_digest": annotation.topic_digest,
                "source_digest": annotation.source_digest,
                "mode": annotation.mode.value,
                "content": content.to_event_payload(),
            },
        )
        return self._append_idempotent(event), annotation

    @staticmethod
    def _policy_payload(policy: ExplorationPolicy) -> dict[str, object]:
        return {
            "window_size": policy.window_size,
            "max_explorations": policy.max_explorations,
            "minimum_share_sample": policy.minimum_share_sample,
            "maximum_topic_share": policy.maximum_topic_share,
            "maximum_source_share": policy.maximum_source_share,
            "maximum_topic_streak": policy.maximum_topic_streak,
        }

    @staticmethod
    def _policy_from_payload(payload: object) -> ExplorationPolicy:
        if not isinstance(payload, dict):
            raise ExplorationValidationError("invalid exploration policy payload")
        return ExplorationPolicy(**payload)

    def append_evaluation(
        self,
        frame_id: str,
        policy: ExplorationPolicy,
        *,
        actor: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        evaluation_id: str | None = None,
    ) -> tuple[JournalRecord, ExplorationGateResult]:
        evaluation_id = str(evaluation_id or uuid4()).strip()
        with closing(self._connect()) as connection:
            frame, annotations = self._frame_and_annotations(connection, frame_id)
            history = self._exposure_history(connection, subject, policy.window_size)
        result = apply_exploration_gate(frame, annotations, history, policy)
        event = EventEnvelope(
            event_id=f"exploration.evaluation:{evaluation_id}",
            event_type="exploration.evaluated",
            source="alive.exploration",
            actor=actor,
            subject=subject,
            causation_id=f"deliberation.frame:{frame_id}",
            sensitivity=Sensitivity(sensitivity),
            payload={
                "evaluation_id": evaluation_id,
                "frame_id": frame_id,
                "policy": self._policy_payload(policy),
                "admissible_ids": list(result.admissible_ids),
                "rejections": [
                    {"candidate_id": item.candidate_id, "reasons": list(item.reasons)}
                    for item in result.rejections
                ],
                "silence_id": result.silence_id,
                "history_event_ids": list(result.history_event_ids),
            },
        )
        return self._append_idempotent(event), result

    def _decision(
        self,
        connection: sqlite3.Connection,
        event: EventEnvelope,
        outcome: str,
        reason: str,
        frame_id: str | None,
    ) -> ExplorationProjectionDecision:
        connection.execute(
            "INSERT INTO exploration_decisions_v1 VALUES (?, ?, ?, ?, ?)",
            (event.event_id, outcome, reason, frame_id, event.observed_at.isoformat()),
        )
        return ExplorationProjectionDecision(event.event_id, outcome, reason, frame_id)

    def apply(self, record: JournalRecord) -> ExplorationProjectionDecision:
        event = record.event
        if event.event_type not in {"exploration.annotated", "exploration.evaluated"}:
            raise ExplorationValidationError("unsupported exploration event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM exploration_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if existing is not None:
                    connection.execute("COMMIT")
                    return ExplorationProjectionDecision(
                        event.event_id, existing["outcome"],
                        existing["reason"], existing["frame_id"],
                    )
                decision = (
                    self._apply_annotation(connection, event)
                    if event.event_type == "exploration.annotated"
                    else self._apply_evaluation(connection, event)
                )
                connection.execute("COMMIT")
                return decision
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _load_frame(self, connection: sqlite3.Connection, frame_id: str):
        row = connection.execute(
            "SELECT * FROM deliberation_frames_v1 WHERE frame_id=?", (frame_id,)
        ).fetchone()
        if row is None:
            raise ExplorationValidationError("unknown deliberation frame")
        document = self.content_vault.resolve_json(
            row["content_id"], expected_subject=row["subject"],
            expected_purpose="deliberation.frame",
            expected_sensitivity=Sensitivity(row["sensitivity"]),
        )
        frame, _context = deserialize_frame(document)
        return row, frame

    def _apply_annotation(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> ExplorationProjectionDecision:
        payload = event.payload
        frame_id = str(payload.get("frame_id") or "")
        try:
            annotation = DiversityAnnotation(
                str(payload["candidate_id"]), str(payload["topic_digest"]),
                str(payload["source_digest"]), ExplorationMode(payload["mode"]),
            )
            content = ContentReference.from_event_payload(payload["content"])
            frame_row, frame = self._load_frame(connection, frame_id)
            candidate = next(
                item for item in frame.candidates
                if item.candidate_id == annotation.candidate_id
            )
            if candidate.action_kind.value == "silence":
                raise ExplorationValidationError("silence cannot be annotated")
            labels = self.content_vault.resolve_json(
                content.content_id, expected_subject=event.subject,
                expected_purpose="exploration.annotation",
                expected_sensitivity=event.sensitivity,
            )
            recomputed = self.tagger.annotate(
                annotation.candidate_id, topic=labels["topic"],
                source=labels["source"], mode=annotation.mode,
            )
        except ContentErasedError:
            recomputed = annotation
            frame_row, frame = self._load_frame(connection, frame_id)
        except (
            KeyError, StopIteration, TypeError, ValueError,
            ContentUnavailableError, ContentIntegrityError, ExplorationValidationError,
        ) as exc:
            return self._decision(
                connection, event, "rejected", f"annotation_invalid:{type(exc).__name__}",
                frame_id or None,
            )
        if (
            recomputed != annotation
            or event.subject != frame_row["subject"]
            or event.sensitivity.value != frame_row["sensitivity"]
            or content.sensitivity is not event.sensitivity
            or event.causation_id != frame_row["event_id"]
        ):
            return self._decision(
                connection, event, "rejected", "annotation_boundary_mismatch", frame_id
            )
        connection.execute(
            "INSERT INTO exploration_annotations_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(payload.get("annotation_id") or ""), event.event_id, frame_id,
                annotation.candidate_id, event.subject, annotation.topic_digest,
                annotation.source_digest, annotation.mode.value, content.content_id,
                event.sensitivity.value, event.observed_at.isoformat(),
            ),
        )
        return self._decision(connection, event, "recorded", "annotation_validated", frame_id)

    def _frame_and_annotations(
        self, connection: sqlite3.Connection, frame_id: str
    ) -> tuple[object, tuple[DiversityAnnotation, ...]]:
        _row, frame = self._load_frame(connection, frame_id)
        rows = connection.execute(
            "SELECT * FROM exploration_annotations_v1 WHERE frame_id=? ORDER BY rowid",
            (frame_id,),
        ).fetchall()
        return frame, tuple(
            DiversityAnnotation(
                row["candidate_id"], row["topic_digest"], row["source_digest"], row["mode"]
            )
            for row in rows
        )

    def _exposure_history(
        self, connection: sqlite3.Connection, subject: str, limit: int
    ) -> tuple[ExposureRecord, ...]:
        outcome_schema = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='action_outcomes_v1'"
        ).fetchone()
        if outcome_schema is None:
            for row in connection.execute(
                "SELECT event_id FROM experience_events WHERE subject=? "
                "AND event_type='outcome.recorded' "
                "AND json_extract(canonical_json, '$.payload.kind')=?",
                (subject, OutcomeKind.DELIVERY_SUCCEEDED.value),
            ):
                original = self.journal.get(row["event_id"])
                if OutcomeProjection._observation_key(self.journal, original) is not None:
                    raise ExplorationValidationError("exposure cache schema requires repair")
            return ()
        rows = connection.execute(
            """
            SELECT e.event_id AS outcome_event_id, s.candidate_id,
                   a.topic_digest, a.source_digest, a.mode
            FROM experience_events e
            LEFT JOIN action_attempts_v1 t
              ON t.attempt_id=json_extract(e.canonical_json, '$.payload.attempt_id')
            LEFT JOIN deliberation_selections_v1 s ON s.event_id=t.selection_event_id
            LEFT JOIN exploration_annotations_v1 a
              ON a.frame_id=s.frame_id AND a.candidate_id=s.candidate_id
            WHERE e.subject=? AND e.event_type='outcome.recorded'
              AND json_extract(e.canonical_json, '$.payload.kind')=?
            ORDER BY e.sequence DESC
            """,
            (subject, OutcomeKind.DELIVERY_SUCCEEDED.value),
        )
        history = []
        for row in rows:
            original = self.journal.get(row["outcome_event_id"])
            if original is None or not OutcomeProjection.canonical_evidence_valid_for(
                self.journal, connection, original
            ):
                if (
                    original is not None and original.event.subject == subject
                    and OutcomeProjection._observation_key(self.journal, original) is not None
                ):
                    canonical = (
                        OutcomeProjection._earlier_observation(self.journal, connection, original)
                        or original
                    )
                    cached = connection.execute(
                        "SELECT * FROM action_outcomes_v1 WHERE event_id=?", (canonical.event.event_id,),
                    ).fetchone()
                    if cached is None or not OutcomeProjection._row_matches_record(cached, canonical):
                        raise ExplorationValidationError("canonical exposure cache requires repair")
                continue
            if any(
                row[name] is None
                for name in ("candidate_id", "topic_digest", "source_digest", "mode")
            ):
                raise ExplorationValidationError("exposure provenance cache requires repair")
            history.append(ExposureRecord(
                row["outcome_event_id"], row["candidate_id"], row["topic_digest"],
                row["source_digest"], ExplorationMode(row["mode"]),
            ))
            if len(history) >= limit:
                break
        return tuple(reversed(history))

    def _history_by_ids(
        self, connection: sqlite3.Connection, subject: str, event_ids: tuple[str, ...]
    ) -> tuple[ExposureRecord, ...]:
        if not event_ids:
            return ()
        history = self._exposure_history(connection, subject, 10000)
        mapping = {item.outcome_event_id: item for item in history}
        if any(value not in mapping for value in event_ids):
            raise ExplorationValidationError("exposure receipt is unavailable")
        return tuple(mapping[value] for value in event_ids)

    def _apply_evaluation(
        self, connection: sqlite3.Connection, event: EventEnvelope
    ) -> ExplorationProjectionDecision:
        payload = event.payload
        frame_id = str(payload.get("frame_id") or "")
        try:
            frame_row, frame = self._load_frame(connection, frame_id)
            _frame, annotations = self._frame_and_annotations(connection, frame_id)
            policy = self._policy_from_payload(dict(payload["policy"]))
            history_ids = tuple(str(value) for value in payload["history_event_ids"])
            history = self._history_by_ids(connection, str(event.subject), history_ids)
            result = apply_exploration_gate(frame, annotations, history, policy)
            expected_rejections = tuple(
                ExplorationRejection(
                    str(item["candidate_id"]),
                    tuple(str(reason) for reason in item["reasons"]),
                )
                for item in payload["rejections"]
            )
        except (
            KeyError, TypeError, ValueError, ContentUnavailableError,
            ContentIntegrityError, ExplorationValidationError,
        ) as exc:
            return self._decision(
                connection, event, "rejected", f"evaluation_invalid:{type(exc).__name__}",
                frame_id or None,
            )
        if (
            result.admissible_ids != tuple(payload["admissible_ids"])
            or result.rejections != expected_rejections
            or result.silence_id != payload["silence_id"]
            or result.history_event_ids != history_ids
            or event.subject != frame_row["subject"]
            or event.sensitivity.value != frame_row["sensitivity"]
            or event.causation_id != frame_row["event_id"]
        ):
            return self._decision(
                connection, event, "rejected", "evaluation_recompute_mismatch", frame_id
            )
        connection.execute(
            "INSERT INTO exploration_evaluations_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(payload.get("evaluation_id") or ""), event.event_id, frame_id,
                json.dumps(list(result.admissible_ids), separators=(",", ":")),
                json.dumps(
                    [
                        {"candidate_id": item.candidate_id, "reasons": list(item.reasons)}
                        for item in result.rejections
                    ], separators=(",", ":"), sort_keys=True,
                ),
                json.dumps(list(history_ids), separators=(",", ":")),
                json.dumps(self._policy_payload(policy), separators=(",", ":"), sort_keys=True),
                event.sensitivity.value, event.observed_at.isoformat(),
            ),
        )
        return self._decision(connection, event, "recorded", "exploration_gate_recomputed", frame_id)

    def gate_result(self, frame_id: str) -> ExplorationGateResult | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT * FROM exploration_evaluations_v1
                WHERE frame_id=? ORDER BY rowid DESC LIMIT 1
                """,
                (frame_id,),
            ).fetchone()
            frame = connection.execute(
                "SELECT silence_id FROM deliberation_frames_v1 WHERE frame_id=?",
                (frame_id,),
            ).fetchone()
            if row is None or frame is None:
                return None
            rejections = tuple(
                ExplorationRejection(
                    str(item["candidate_id"]),
                    tuple(str(reason) for reason in item["reasons"]),
                )
                for item in json.loads(row["rejections_json"])
            )
            return ExplorationGateResult(
                frame_id=frame_id,
                admissible_ids=tuple(json.loads(row["admissible_json"])),
                rejections=rejections,
                silence_id=frame["silence_id"],
                history_event_ids=tuple(json.loads(row["history_json"])),
            )

    def latest_gate_event_id(self, frame_id: str) -> str | None:
        """Return the exact latest successfully projected gate for a frame."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT e.event_id
                FROM exploration_evaluations_v1 e
                JOIN exploration_decisions_v1 d ON d.event_id=e.event_id
                WHERE e.frame_id=? AND d.outcome='recorded'
                ORDER BY e.rowid DESC LIMIT 1
                """,
                (frame_id,),
            ).fetchone()
            return None if row is None else str(row["event_id"])

    def project_new(self, *, limit: int = 1000) -> list[ExplorationProjectionDecision]:
        decisions: list[ExplorationProjectionDecision] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type in {"exploration.annotated", "exploration.evaluated"}:
                decisions.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return decisions

    def rebuild(self, *, batch_size: int = 1000) -> list[ExplorationProjectionDecision]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM exploration_evaluations_v1")
            connection.execute("DELETE FROM exploration_annotations_v1")
            connection.execute("DELETE FROM exploration_decisions_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        decisions: list[ExplorationProjectionDecision] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            decisions.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("exploration replay made no progress")
        return decisions
