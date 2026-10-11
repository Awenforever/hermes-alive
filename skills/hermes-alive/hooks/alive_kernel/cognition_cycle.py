"""Crash-safe cognition-cycle planning with deterministic safe silence."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from .content_vault import ContentIntegrityError, ContentVault
from .deliberation import (
    ActionCandidate,
    ActionKind,
    PolicyContext,
    SelectionProposal,
    ValidatedSelection,
)
from .deliberation_store import DeliberationProjection
from .event_store import ExperienceJournal
from .events import Sensitivity
from .exploration import ExplorationGateResult, ExplorationMode, ExplorationPolicy
from .exploration_store import ExplorationProjection


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")


class CognitionCycleError(ValueError):
    """A cognition cycle could not preserve its deterministic safety contract."""


@dataclass(frozen=True, slots=True)
class CycleCandidate:
    action: ActionCandidate
    content: Any
    topic: str
    source_label: str
    mode: ExplorationMode = ExplorationMode.EXPLOIT

    def __post_init__(self) -> None:
        if self.action.action_kind is ActionKind.SILENCE:
            raise CognitionCycleError("cycle input must not supply its own silence candidate")
        if not str(self.action.content_id or "").strip():
            raise CognitionCycleError("cycle candidate requires erasable content")
        topic = str(self.topic).strip()
        source = str(self.source_label).strip()
        if not topic or not source:
            raise CognitionCycleError("cycle candidate requires diversity labels")
        object.__setattr__(self, "topic", topic[:256])
        object.__setattr__(self, "source_label", source[:256])
        object.__setattr__(self, "mode", ExplorationMode(self.mode))


@dataclass(frozen=True, slots=True)
class CognitionCycleResult:
    cycle_id: str
    frame_event_id: str
    exploration_event_id: str
    selection_event_id: str
    gate: ExplorationGateResult
    selection: ValidatedSelection


class CognitionCycleCoordinator:
    """Persist a complete internal cycle without authorizing external action."""

    MAX_CANDIDATES = 32
    SAFE_SILENCE_MODEL = "system/alive-safe-silence"

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.vault = content_vault or ContentVault(
            journal.path.parent / "content-vault",
            backup_root=journal.path.parent / "content-backups",
        )
        self.deliberation = DeliberationProjection(
            journal, content_vault=self.vault
        )
        self.exploration = ExplorationProjection(journal, content_vault=self.vault)

    def _identifier(self, namespace: str, cycle_id: str, suffix: str = "") -> str:
        digest = self.vault.digest_json(
            {"namespace": namespace, "cycle_id": cycle_id, "suffix": suffix}
        )
        return f"{namespace}:{digest[:40]}"

    def plan_safe_silence(
        self,
        *,
        cycle_id: str,
        subject: str,
        candidates: Iterable[CycleCandidate],
        policy_context: PolicyContext,
        exploration_policy: ExplorationPolicy | None = None,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        causation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> CognitionCycleResult:
        """Record the full cycle and close it with a no-side-effect selection."""

        cycle = str(cycle_id).strip()
        owner = str(subject).strip()
        if not _ID_RE.fullmatch(cycle) or not _ID_RE.fullmatch(owner):
            raise CognitionCycleError("invalid cycle or subject identifier")
        values = tuple(candidates)
        if len(values) > self.MAX_CANDIDATES:
            raise CognitionCycleError("candidate count exceeds the cycle boundary")
        ids = [item.action.candidate_id for item in values]
        if len(ids) != len(set(ids)):
            raise CognitionCycleError("cycle candidate IDs must be unique")
        content_ids = [str(item.action.content_id) for item in values]
        if len(content_ids) != len(set(content_ids)):
            raise CognitionCycleError("cycle content IDs must be unique")
        sensitivity = Sensitivity(sensitivity)
        frame_id = self._identifier("cycle-frame", cycle)
        actor = "system:alive-coordinator"
        try:
            frame_record, frame = self.deliberation.append_frame(
                (item.action for item in values),
                policy_context,
                actor=actor,
                subject=owner,
                sensitivity=sensitivity,
                frame_id=frame_id,
                causation_id=causation_id,
                correlation_id=correlation_id,
                candidate_contents={
                    str(item.action.content_id): item.content for item in values
                },
            )
        except ContentIntegrityError as exc:
            raise CognitionCycleError(
                "cycle ID or content ID was reused with different semantics"
            ) from exc
        frame_decision = self.deliberation.apply(frame_record)
        if frame_decision.outcome != "recorded":
            raise CognitionCycleError(
                f"deliberation frame was not admitted: {frame_decision.reason}"
            )

        for item in values:
            annotation_id = self._identifier(
                "cycle-annotation", cycle, item.action.candidate_id
            )
            annotation_record, _annotation = self.exploration.append_annotation(
                frame_id=frame.frame_id,
                candidate_id=item.action.candidate_id,
                topic=item.topic,
                source_label=item.source_label,
                mode=item.mode,
                actor=actor,
                subject=owner,
                sensitivity=sensitivity,
                annotation_id=annotation_id,
            )
            annotation_decision = self.exploration.apply(annotation_record)
            if annotation_decision.outcome != "recorded":
                raise CognitionCycleError(
                    "diversity annotation was not admitted: "
                    + annotation_decision.reason
                )

        evaluation_id = self._identifier("cycle-exploration", cycle)
        evaluation_record, gate = self.exploration.append_evaluation(
            frame.frame_id,
            exploration_policy or ExplorationPolicy(),
            actor=actor,
            subject=owner,
            sensitivity=sensitivity,
            evaluation_id=evaluation_id,
        )
        evaluation_decision = self.exploration.apply(evaluation_record)
        if evaluation_decision.outcome != "recorded":
            raise CognitionCycleError(
                f"exploration gate was not admitted: {evaluation_decision.reason}"
            )

        selection_id = self._identifier("cycle-selection", cycle)
        selection_record = self.deliberation.append_selection(
            SelectionProposal(
                frame_id=frame.frame_id,
                candidate_id=frame.silence_id,
                model=self.SAFE_SILENCE_MODEL,
                rationale=(
                    "The cycle is audit-only; no model or operator has authorized "
                    "an external action."
                ),
            ),
            actor=actor,
            subject=owner,
            sensitivity=sensitivity,
            selection_id=selection_id,
            exploration_gate_event_id=evaluation_record.event.event_id,
        )
        selection_decision = self.deliberation.apply(selection_record)
        if selection_decision.outcome != "validated":
            raise CognitionCycleError(
                f"safe-silence selection was not admitted: {selection_decision.reason}"
            )
        stored = self.deliberation.inspect(frame.frame_id, clearance=sensitivity)
        if stored is None or stored.selection is None:
            raise CognitionCycleError("durable cycle selection is unavailable")
        if stored.selection.candidate.action_kind is not ActionKind.SILENCE:
            raise CognitionCycleError("audit-only cycle selected an external action")
        return CognitionCycleResult(
            cycle,
            frame_record.event.event_id,
            evaluation_record.event.event_id,
            selection_record.event.event_id,
            gate,
            stored.selection,
        )
