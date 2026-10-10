"""Consent-gated conversion of retained evidence into review-only memory proposals."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import re
import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from .content_vault import (
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity
from .memory import (
    MemoryAuthority,
    MemoryKind,
    MemoryProjection,
    MemoryProposal,
    ProjectionDecision,
    ProjectionDecisionKind,
)


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_ALLOWED_KINDS = frozenset(
    {MemoryKind.FACT, MemoryKind.PREFERENCE, MemoryKind.SELF_MODEL}
)
_EVIDENCE_TYPES = {
    "conversation.inbound": "conversation.inbound",
    "conversation.outbound": "conversation.outbound",
}


class ConsolidationValidationError(ValueError):
    """A consolidation request crosses evidence, consent or authority bounds."""


@dataclass(frozen=True, slots=True)
class ConsolidationPolicy:
    subject: str
    enabled: bool
    consent_event_id: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConsolidationCandidate:
    subject: str
    kind: MemoryKind
    predicate: str
    value: Any
    evidence_event_ids: tuple[str, ...]
    confidence: float
    importance: float
    expires_at: datetime
    model: str
    candidate_id: str = ""

    def __post_init__(self) -> None:
        subject = str(self.subject).strip()
        if not _ID_RE.fullmatch(subject):
            raise ConsolidationValidationError("invalid consolidation subject")
        object.__setattr__(self, "subject", subject)
        kind = MemoryKind(self.kind)
        if kind not in _ALLOWED_KINDS:
            raise ConsolidationValidationError(
                "model consolidation may propose only fact, preference or self_model memory"
            )
        object.__setattr__(self, "kind", kind)
        evidence = tuple(
            dict.fromkeys(str(value).strip() for value in self.evidence_event_ids)
        )
        if not evidence or len(evidence) > 32 or any(not _ID_RE.fullmatch(v) for v in evidence):
            raise ConsolidationValidationError("consolidation requires 1-32 evidence event IDs")
        object.__setattr__(self, "evidence_event_ids", evidence)
        confidence = float(self.confidence)
        importance = float(self.importance)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ConsolidationValidationError("confidence must be between 0 and 1")
        if not math.isfinite(importance) or not 0.0 <= importance <= 1.0:
            raise ConsolidationValidationError("importance must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "importance", importance)
        expires = self.expires_at
        if expires.tzinfo is None or expires.utcoffset() is None:
            raise ConsolidationValidationError("expires_at must be timezone-aware")
        object.__setattr__(self, "expires_at", expires.astimezone(timezone.utc))
        now = datetime.now(timezone.utc)
        if not now < self.expires_at <= now + timedelta(days=180):
            raise ConsolidationValidationError("model proposal expiry must be within 180 days")
        model = str(self.model).strip()
        if not _MODEL_RE.fullmatch(model):
            raise ConsolidationValidationError("invalid model identifier")
        object.__setattr__(self, "model", model)
        candidate_id = str(self.candidate_id or uuid4()).strip()
        if not _ID_RE.fullmatch(candidate_id):
            raise ConsolidationValidationError("invalid candidate_id")
        object.__setattr__(self, "candidate_id", candidate_id)


class ConsolidationPolicyProjection:
    """Replayable user authority for model-assisted memory consolidation."""

    CHECKPOINT = "alive-consolidation-consent-v1"

    def __init__(self, journal: ExperienceJournal) -> None:
        self.journal = journal
        self.path = Path(journal.path)
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS consolidation_policies_v1 (
                    subject TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL,
                    consent_event_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS consolidation_policy_decisions_v1 (
                    event_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    subject TEXT,
                    decided_at TEXT NOT NULL
                );
                COMMIT;
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def append_consent(
        self,
        *,
        subject: str,
        actor: str,
        enabled: bool,
        operation_id: str | None = None,
    ) -> JournalRecord:
        subject = str(subject).strip()
        actor = str(actor).strip()
        if not subject or actor != subject:
            raise ConsolidationValidationError(
                "memory consolidation consent must be self-authorized"
            )
        event = EventEnvelope(
            event_id=f"consolidation.consent:{operation_id or uuid4()}",
            event_type="consolidation.consent_changed",
            source="hermes.command.memory",
            actor=actor,
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            payload={"enabled": bool(enabled), "raw_command_stored": False},
        )
        existing = self.journal.get(event.event_id)
        if existing is not None:
            fields = ("event_type", "source", "actor", "subject", "sensitivity", "payload")
            if any(
                getattr(existing.event, field) != getattr(event, field)
                for field in fields
            ):
                raise ConsolidationValidationError(
                    "operation_id was reused with different consolidation consent"
                )
            return existing
        try:
            appended = self.journal.append(event)
        except EventConflictError as exc:
            raise ConsolidationValidationError("conflicting consolidation consent") from exc
        return JournalRecord(appended.sequence, appended.event)

    def apply(self, record: JournalRecord) -> str:
        event = record.event
        if event.event_type != "consolidation.consent_changed":
            raise ConsolidationValidationError("unsupported consolidation policy event")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                prior = connection.execute(
                    "SELECT outcome FROM consolidation_policy_decisions_v1 WHERE event_id=?",
                    (event.event_id,),
                ).fetchone()
                if prior is not None:
                    connection.execute("COMMIT")
                    return str(prior["outcome"])
                valid = (
                    event.source == "hermes.command.memory"
                    and event.subject is not None
                    and event.actor == event.subject
                    and isinstance(event.payload.get("enabled"), bool)
                    and event.payload.get("raw_command_stored") is False
                )
                outcome = "recorded" if valid else "rejected"
                reason = "explicit_user_consent" if valid else "consent_authority_invalid"
                if valid:
                    connection.execute(
                        """
                        INSERT INTO consolidation_policies_v1 VALUES (?, ?, ?, ?)
                        ON CONFLICT(subject) DO UPDATE SET
                            enabled=excluded.enabled,
                            consent_event_id=excluded.consent_event_id,
                            updated_at=excluded.updated_at
                        """,
                        (
                            event.subject,
                            int(bool(event.payload["enabled"])),
                            event.event_id,
                            event.observed_at.isoformat(),
                        ),
                    )
                connection.execute(
                    "INSERT INTO consolidation_policy_decisions_v1 VALUES (?, ?, ?, ?, ?)",
                    (
                        event.event_id,
                        outcome,
                        reason,
                        event.subject,
                        event.observed_at.isoformat(),
                    ),
                )
                connection.execute("COMMIT")
                return outcome
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def policy(self, subject: str) -> ConsolidationPolicy | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM consolidation_policies_v1 WHERE subject=?",
                (str(subject),),
            ).fetchone()
        if row is None:
            return None
        return ConsolidationPolicy(
            subject=str(row["subject"]),
            enabled=bool(row["enabled"]),
            consent_event_id=str(row["consent_event_id"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def project_new(self, *, limit: int = 1000) -> list[str]:
        if limit < 1:
            raise ValueError("limit must be positive")
        outcomes: list[str] = []
        start = self.journal.checkpoint(self.CHECKPOINT)
        for index, record in enumerate(self.journal.iter_replay(after_sequence=start), start=1):
            if record.event.event_type == "consolidation.consent_changed":
                outcomes.append(self.apply(record))
            self.journal.advance_checkpoint(self.CHECKPOINT, record.sequence)
            if index >= limit:
                break
        return outcomes

    def rebuild(self, *, batch_size: int = 1000) -> list[str]:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM consolidation_policy_decisions_v1")
            connection.execute("DELETE FROM consolidation_policies_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?", (self.CHECKPOINT,)
            )
            connection.execute("COMMIT")
        outcomes: list[str] = []
        while self.journal.checkpoint(self.CHECKPOINT) < self.journal.last_sequence():
            before = self.journal.checkpoint(self.CHECKPOINT)
            outcomes.extend(self.project_new(limit=batch_size))
            if self.journal.checkpoint(self.CHECKPOINT) <= before:
                raise RuntimeError("consolidation consent replay made no progress")
        return outcomes


class ConsolidationService:
    """Admit model candidates only as review-required memory proposals."""

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.vault = content_vault or ContentVault(
            Path(journal.path).parent / "content-vault",
            backup_root=Path(journal.path).parent / "content-backups",
        )
        self.policy_projection = ConsolidationPolicyProjection(journal)
        self.memory = MemoryProjection(journal, content_vault=self.vault)

    def _validate_evidence(self, candidate: ConsolidationCandidate) -> None:
        for event_id in candidate.evidence_event_ids:
            record = self.journal.get(event_id)
            if record is None:
                raise ConsolidationValidationError(f"missing evidence event {event_id!r}")
            event = record.event
            purpose = _EVIDENCE_TYPES.get(event.event_type)
            if event.subject != candidate.subject or purpose is None:
                raise ConsolidationValidationError("evidence crosses subject or type boundary")
            if event.payload.get("erasable_content_stored") is not True:
                raise ConsolidationValidationError("evidence has no authorized retained content")
            try:
                reference = ContentReference.from_event_payload(event.payload["content"])
                self.vault.resolve_json(
                    reference.content_id,
                    expected_subject=candidate.subject,
                    expected_purpose=purpose,
                    expected_sensitivity=event.sensitivity,
                )
            except (
                KeyError,
                TypeError,
                ValueError,
                ContentUnavailableError,
                ContentIntegrityError,
            ) as exc:
                raise ConsolidationValidationError(
                    "evidence content is unavailable or invalid"
                ) from exc

    def propose(self, candidate: ConsolidationCandidate) -> ProjectionDecision:
        policy = self.policy_projection.policy(candidate.subject)
        if policy is None or not policy.enabled:
            raise ConsolidationValidationError(
                "model-assisted memory consolidation is not authorized for this user"
            )
        self._validate_evidence(candidate)
        generation = EventEnvelope(
            event_id=f"consolidation.candidate:{candidate.candidate_id}",
            event_type="consolidation.candidate_generated",
            source="alive.consolidation",
            actor="system:alive-consolidator",
            subject=candidate.subject,
            sensitivity=Sensitivity.PRIVATE,
            confidence=candidate.confidence,
            expires_at=candidate.expires_at,
            payload={
                "candidate_id": candidate.candidate_id,
                "kind": candidate.kind.value,
                "predicate": candidate.predicate,
                "value_digest": self.vault.digest_json(candidate.value),
                "model": candidate.model,
                "evidence_event_ids": list(candidate.evidence_event_ids),
                "consent_event_id": policy.consent_event_id,
                "raw_content_stored": False,
                "disposition": "review_required",
            },
        )
        existing = self.journal.get(generation.event_id)
        if existing is None:
            try:
                appended = self.journal.append(generation)
            except EventConflictError as exc:
                existing = self.journal.get(generation.event_id)
                if existing is None:
                    raise
                self._assert_generation_compatible(existing, generation)
                generation_record = existing
            else:
                generation_record = JournalRecord(appended.sequence, appended.event)
        else:
            self._assert_generation_compatible(existing, generation)
            generation_record = existing
        proposal = MemoryProposal(
            proposal_id=candidate.candidate_id,
            kind=candidate.kind,
            subject=candidate.subject,
            predicate=candidate.predicate,
            value=candidate.value,
            authority=MemoryAuthority.MODEL_INFERENCE,
            source_event_ids=(*candidate.evidence_event_ids, generation_record.event.event_id),
            confidence=candidate.confidence,
            importance=candidate.importance,
            sensitivity=Sensitivity.RESTRICTED,
            valid_until=candidate.expires_at,
        )
        proposal_record = self.memory.append_proposal(
            proposal,
            actor="system:alive-consolidator",
            correlation_id=candidate.subject,
        )
        decision = self.memory.apply(proposal_record)
        if decision.decision not in {
            ProjectionDecisionKind.PROPOSED,
            ProjectionDecisionKind.DEDUPLICATED,
        }:
            raise ConsolidationValidationError(
                f"unexpected model proposal disposition: {decision.decision.value}"
            )
        return decision

    @staticmethod
    def _assert_generation_compatible(
        existing: JournalRecord, expected: EventEnvelope
    ) -> None:
        fields = (
            "event_type",
            "source",
            "actor",
            "subject",
            "sensitivity",
            "confidence",
            "expires_at",
            "payload",
        )
        if any(
            getattr(existing.event, field) != getattr(expected, field) for field in fields
        ):
            raise ConsolidationValidationError(
                "candidate_id was reused with different consolidation semantics"
            )
