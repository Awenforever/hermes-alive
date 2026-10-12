"""Explainable post-selection expression stances, never synthetic emotion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hmac
from pathlib import Path
import re
from typing import Mapping

from .content_vault import ContentVault
from .deliberation import ActionKind, SideEffect, ValidatedSelection
from .deliberation_store import DeliberationProjection
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")


class DispositionError(ValueError):
    """A disposition attempted to exceed its expression-only boundary."""


class ExpressionStance(StrEnum):
    STEADY = "steady"
    CURIOUS = "curious"
    FOCUSED = "focused"
    GENTLE = "gentle"
    CAREFUL = "careful"


class DispositionBasis(StrEnum):
    CONFIDENCE = "confidence"
    NOVELTY = "novelty"
    URGENCY = "urgency"
    INTERRUPTION_COST = "interruption_cost"
    RISK = "risk"


@dataclass(frozen=True, slots=True)
class DispositionCue:
    stance: ExpressionStance
    basis: DispositionBasis
    intensity: float
    evidence_event_ids: tuple[str, ...]
    reason_code: str

    def __post_init__(self) -> None:
        intensity = float(self.intensity)
        evidence = tuple(dict.fromkeys(str(item).strip() for item in self.evidence_event_ids))
        reason = str(self.reason_code).strip().lower()
        if not 0.0 <= intensity <= 1.0:
            raise DispositionError("cue intensity must be between 0 and 1")
        if not evidence or any(not _ID_RE.fullmatch(item) for item in evidence):
            raise DispositionError("cue requires valid evidence event IDs")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", reason):
            raise DispositionError("invalid disposition reason")
        object.__setattr__(self, "stance", ExpressionStance(self.stance))
        object.__setattr__(self, "basis", DispositionBasis(self.basis))
        object.__setattr__(self, "intensity", intensity)
        object.__setattr__(self, "evidence_event_ids", evidence)
        object.__setattr__(self, "reason_code", reason)


@dataclass(frozen=True, slots=True)
class DispositionSnapshot:
    subject: str
    frame_id: str
    candidate_id: str
    selection_event_id: str
    action_kind: ActionKind
    cues: tuple[DispositionCue, ...]
    renderable: bool

    @property
    def permits_action(self) -> bool:
        return False

    @property
    def changes_selection(self) -> bool:
        return False

    @property
    def may_change_semantics(self) -> bool:
        return False


def derive_disposition(
    selection: ValidatedSelection,
    *,
    subject: str,
    selection_event_id: str,
) -> DispositionSnapshot:
    """Interpret independent dimensions after selection; never blend a score."""

    owner = str(subject).strip()
    event_id = str(selection_event_id).strip()
    if not _ID_RE.fullmatch(owner) or not _ID_RE.fullmatch(event_id):
        raise DispositionError("invalid disposition identity")
    candidate = selection.candidate
    renderable = bool(
        candidate.action_kind is not ActionKind.SILENCE
        and candidate.side_effect is SideEffect.COMMUNICATION
    )
    if not renderable:
        return DispositionSnapshot(
            owner,
            selection.frame_id,
            candidate.candidate_id,
            event_id,
            candidate.action_kind,
            (),
            False,
        )
    dimensions = candidate.dimensions
    if dimensions is None:
        raise DispositionError("renderable selection has no decision dimensions")
    cues: list[DispositionCue] = []

    def add(
        stance: ExpressionStance,
        basis: DispositionBasis,
        assessment: object,
        reason: str,
    ) -> None:
        cues.append(
            DispositionCue(
                stance,
                basis,
                float(getattr(assessment, "value")),
                tuple(getattr(assessment, "evidence_event_ids")),
                reason,
            )
        )

    # Each cue is a direct view of one already-audited decision dimension.
    # There is deliberately no weighted mood/personality score.
    if dimensions.risk.value >= 0.35:
        add(ExpressionStance.CAREFUL, DispositionBasis.RISK, dimensions.risk, "selected_action_has_material_risk")
    if dimensions.interruption_cost.value >= 0.55:
        add(
            ExpressionStance.GENTLE,
            DispositionBasis.INTERRUPTION_COST,
            dimensions.interruption_cost,
            "selected_action_has_high_interruption_cost",
        )
    if dimensions.urgency.value >= 0.7:
        add(ExpressionStance.FOCUSED, DispositionBasis.URGENCY, dimensions.urgency, "selected_action_is_time_sensitive")
    if dimensions.novelty.value >= 0.65 and dimensions.confidence.value >= 0.5:
        add(ExpressionStance.CURIOUS, DispositionBasis.NOVELTY, dimensions.novelty, "selected_action_contains_grounded_novelty")
    if not cues:
        add(ExpressionStance.STEADY, DispositionBasis.CONFIDENCE, dimensions.confidence, "selected_action_uses_neutral_expression")
    return DispositionSnapshot(
        owner,
        selection.frame_id,
        candidate.candidate_id,
        event_id,
        candidate.action_kind,
        tuple(cues),
        True,
    )


class DispositionRecorder:
    """Bind an expression-only snapshot to an exact validated selection."""

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
        protector: LocalIdentityProtector | None = None,
    ) -> None:
        self.journal = journal
        self.content_vault = content_vault or ContentVault(
            journal.path.parent / f"{journal.path.stem}-content-vault",
            backup_root=journal.path.parent / f"{journal.path.stem}-content-backups",
        )
        self.protector = protector or LocalIdentityProtector(
            journal.path.parent / "identity.key"
        )
        self.deliberation = DeliberationProjection(
            journal, content_vault=self.content_vault
        )

    @staticmethod
    def _authentication_document(payload: Mapping[str, object]) -> dict[str, object]:
        value = _thaw_json(payload)
        value.pop("integrity_authenticator", None)
        return {"contract": "disposition.snapshot.v1", "payload": value}

    def record(
        self,
        *,
        frame_id: str,
        selection_event_id: str,
        subject: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        observed_at: datetime | None = None,
    ) -> tuple[JournalRecord, DispositionSnapshot]:
        source = self.journal.get(selection_event_id)
        if (
            source is None
            or source.event.event_type != "deliberation.selected"
            or source.event.subject != subject
            or source.event.payload.get("frame_id") != frame_id
        ):
            raise DispositionError("selection evidence is missing or mismatched")
        self.deliberation.project_new()
        if self.deliberation.latest_selection_event_id(frame_id) != selection_event_id:
            raise DispositionError("selection is not the latest validated intent")
        stored = self.deliberation.inspect(frame_id, clearance=Sensitivity(sensitivity))
        if stored is None or stored.selection is None:
            raise DispositionError("validated selection is unavailable")
        snapshot = derive_disposition(
            stored.selection,
            subject=subject,
            selection_event_id=selection_event_id,
        )
        payload: dict[str, object] = {
            "frame_id": snapshot.frame_id,
            "candidate_id": snapshot.candidate_id,
            "selection_event_id": snapshot.selection_event_id,
            "action_kind": snapshot.action_kind.value,
            "renderable": snapshot.renderable,
            "cues": [
                {
                    "stance": cue.stance.value,
                    "basis": cue.basis.value,
                    "intensity": cue.intensity,
                    "evidence_event_ids": list(cue.evidence_event_ids),
                    "reason_code": cue.reason_code,
                }
                for cue in snapshot.cues
            ],
            "emotion_claimed": False,
            "relationship_inferred": False,
            "silence_interpreted": False,
            "action_authority_granted": False,
            "selection_changed": False,
            "semantic_change_allowed": False,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "disposition.snapshot.v1", self._authentication_document(payload)
        )
        snapshot_id = self.protector.pseudonym(
            "disposition-snapshot", selection_event_id
        )
        if snapshot_id is None:
            raise DispositionError("disposition identity is unavailable")
        event = EventEnvelope(
            event_id=f"disposition.snapshot:{snapshot_id.split(':', 1)[-1]}",
            event_type="disposition.interpreted",
            source="alive.disposition",
            actor="system:alive-disposition",
            subject=subject,
            correlation_id=frame_id,
            causation_id=selection_event_id,
            occurred_at=source.event.observed_at,
            observed_at=observed_at or datetime.now(timezone.utc),
            sensitivity=Sensitivity(sensitivity),
            payload=payload,
        )
        existing = self.journal.get(event.event_id)
        if existing is not None:
            return self._compatible(existing, event), snapshot
        try:
            result = self.journal.append(event)
            return JournalRecord(result.sequence, result.event), snapshot
        except EventConflictError:
            existing = self.journal.get(event.event_id)
            if existing is None:
                raise
            return self._compatible(existing, event), snapshot

    def verify(self, record: JournalRecord) -> bool:
        """Recheck the snapshot and its exact validated-selection dependency."""

        event = record.event
        payload = event.payload
        try:
            supplied = str(payload["integrity_authenticator"])
            selection_event_id = str(payload["selection_event_id"])
            frame_id = str(payload["frame_id"])
            candidate_id = str(payload["candidate_id"])
            source = self.journal.get(selection_event_id)
            if not hmac.compare_digest(
                supplied,
                self.protector.authenticate_json(
                    "disposition.snapshot.v1",
                    self._authentication_document(payload),
                ),
            ):
                return False
            self.deliberation.project_new()
            stored = self.deliberation.inspect(
                frame_id, clearance=event.sensitivity
            )
            expected = (
                derive_disposition(
                    stored.selection,
                    subject=str(event.subject or ""),
                    selection_event_id=selection_event_id,
                )
                if stored is not None and stored.selection is not None
                else None
            )
            expected_cues = (
                [
                    {
                        "stance": cue.stance.value,
                        "basis": cue.basis.value,
                        "intensity": cue.intensity,
                        "evidence_event_ids": list(cue.evidence_event_ids),
                        "reason_code": cue.reason_code,
                    }
                    for cue in expected.cues
                ]
                if expected is not None
                else None
            )
            return bool(
                event.event_type == "disposition.interpreted"
                and event.source == "alive.disposition"
                and event.actor == "system:alive-disposition"
                and event.causation_id == selection_event_id
                and event.correlation_id == frame_id
                and source is not None
                and source.event.event_type == "deliberation.selected"
                and source.event.subject == event.subject
                and self.deliberation.latest_selection_event_id(frame_id)
                == selection_event_id
                and stored is not None
                and stored.selection is not None
                and stored.selection.candidate.candidate_id == candidate_id
                and expected is not None
                and payload.get("action_kind") == expected.action_kind.value
                and payload.get("renderable") is expected.renderable
                and _thaw_json(payload.get("cues")) == expected_cues
                and payload.get("emotion_claimed") is False
                and payload.get("relationship_inferred") is False
                and payload.get("silence_interpreted") is False
                and payload.get("action_authority_granted") is False
                and payload.get("selection_changed") is False
                and payload.get("semantic_change_allowed") is False
            )
        except (KeyError, TypeError, ValueError):
            return False

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
            raise DispositionError("disposition identity was reused with different semantics")
        return existing
