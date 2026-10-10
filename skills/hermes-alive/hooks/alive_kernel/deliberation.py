"""Inspectable candidate and policy boundary for Alive deliberation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from types import MappingProxyType
from typing import Iterable, Mapping
from uuid import uuid4


class DeliberationValidationError(ValueError):
    """A deliberation object violates the kernel contract."""


class ActionKind(StrEnum):
    SILENCE = "silence"
    SHARE = "share"
    ASK = "ask"
    REMIND = "remind"
    ADVANCE_COMMITMENT = "advance_commitment"
    INTERNAL_REVIEW = "internal_review"
    TOOL_ACTION = "tool_action"


class SideEffect(StrEnum):
    NONE = "none"
    COMMUNICATION = "communication"
    REVERSIBLE_EXTERNAL = "reversible_external"
    IRREVERSIBLE_EXTERNAL = "irreversible_external"


class ActionAuthority(StrEnum):
    NONE = "none"
    SYSTEM_CRITICAL = "system_critical"
    USER_DELEGATED = "user_delegated"
    USER_CONFIRMED = "user_confirmed"
    USER_CONFIRMATION_REQUIRED = "user_confirmation_required"


class AssessmentBasis(StrEnum):
    MEASURED = "measured"
    USER_RULE = "user_rule"
    MODEL_JUDGMENT = "model_judgment"


@dataclass(frozen=True, slots=True)
class DimensionAssessment:
    value: float
    basis: AssessmentBasis
    evidence_event_ids: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise DeliberationValidationError("dimension value must be between 0 and 1")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "basis", AssessmentBasis(self.basis))
        evidence = tuple(dict.fromkeys(str(item).strip() for item in self.evidence_event_ids))
        if not evidence or any(not item for item in evidence):
            raise DeliberationValidationError("dimension assessment requires evidence")
        object.__setattr__(self, "evidence_event_ids", evidence)
        reason = str(self.reason).strip()
        if not reason:
            raise DeliberationValidationError("dimension assessment requires a reason")
        object.__setattr__(self, "reason", reason[:512])


@dataclass(frozen=True, slots=True)
class DecisionDimensions:
    user_value: DimensionAssessment
    urgency: DimensionAssessment
    novelty: DimensionAssessment
    confidence: DimensionAssessment
    interruption_cost: DimensionAssessment
    risk: DimensionAssessment


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    action_kind: ActionKind
    side_effect: SideEffect
    authority: ActionAuthority
    dimensions: DecisionDimensions | None
    agenda_item_id: str | None = None
    content_id: str | None = None
    candidate_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_kind", ActionKind(self.action_kind))
        object.__setattr__(self, "side_effect", SideEffect(self.side_effect))
        object.__setattr__(self, "authority", ActionAuthority(self.authority))
        candidate_id = str(self.candidate_id).strip()
        if not candidate_id:
            raise DeliberationValidationError("candidate_id is required")
        object.__setattr__(self, "candidate_id", candidate_id)
        if self.action_kind is ActionKind.SILENCE:
            if (
                self.side_effect is not SideEffect.NONE
                or self.authority is not ActionAuthority.NONE
                or self.dimensions is not None
                or self.content_id is not None
            ):
                raise DeliberationValidationError("silence must have no effect, content or score")
        elif self.dimensions is None:
            raise DeliberationValidationError("action candidate requires dimensions")
        elif not str(self.content_id or "").strip():
            raise DeliberationValidationError("action candidate requires an erasable content_id")


@dataclass(frozen=True, slots=True)
class PolicyContext:
    can_interrupt: bool
    minimum_confidence: float = 0.5
    maximum_risk: float = 0.5
    allowed_side_effects: frozenset[SideEffect] = frozenset(
        {SideEffect.NONE, SideEffect.COMMUNICATION}
    )

    def __post_init__(self) -> None:
        for name in ("minimum_confidence", "maximum_risk"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise DeliberationValidationError(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, value)
        object.__setattr__(
            self,
            "allowed_side_effects",
            frozenset(SideEffect(value) for value in self.allowed_side_effects),
        )


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    candidate_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeliberationFrame:
    frame_id: str
    candidates: tuple[ActionCandidate, ...]
    admissible_ids: tuple[str, ...]
    rejections: tuple[CandidateRejection, ...]
    silence_id: str


@dataclass(frozen=True, slots=True)
class SelectionProposal:
    frame_id: str
    candidate_id: str
    model: str
    rationale: str


@dataclass(frozen=True, slots=True)
class ValidatedSelection:
    frame_id: str
    candidate: ActionCandidate
    selected_by: str
    rationale: str


def silence_candidate(*, candidate_id: str = "") -> ActionCandidate:
    return ActionCandidate(
        action_kind=ActionKind.SILENCE,
        side_effect=SideEffect.NONE,
        authority=ActionAuthority.NONE,
        dimensions=None,
        candidate_id=candidate_id or str(uuid4()),
    )


def build_frame(
    candidates: Iterable[ActionCandidate],
    context: PolicyContext,
    *,
    frame_id: str | None = None,
) -> DeliberationFrame:
    values = list(candidates)
    if not any(value.action_kind is ActionKind.SILENCE for value in values):
        values.append(silence_candidate())
    ids = [value.candidate_id for value in values]
    if len(ids) != len(set(ids)):
        raise DeliberationValidationError("candidate IDs must be unique")
    silence = [value for value in values if value.action_kind is ActionKind.SILENCE]
    if len(silence) != 1:
        raise DeliberationValidationError("a frame must contain exactly one silence candidate")

    admissible: list[str] = []
    rejected: list[CandidateRejection] = []
    for candidate in values:
        reasons: list[str] = []
        if candidate.action_kind is not ActionKind.SILENCE:
            assert candidate.dimensions is not None
            if candidate.dimensions.confidence.value < context.minimum_confidence:
                reasons.append("confidence_below_policy")
            if candidate.dimensions.risk.value > context.maximum_risk:
                reasons.append("risk_above_policy")
            if candidate.side_effect not in context.allowed_side_effects:
                reasons.append("side_effect_not_granted")
            if candidate.authority is ActionAuthority.USER_CONFIRMATION_REQUIRED:
                reasons.append("user_confirmation_required")
            if (
                not context.can_interrupt
                and candidate.side_effect is SideEffect.COMMUNICATION
                and candidate.authority is not ActionAuthority.SYSTEM_CRITICAL
            ):
                reasons.append("protected_interruption_window")
        if reasons:
            rejected.append(CandidateRejection(candidate.candidate_id, tuple(reasons)))
        else:
            admissible.append(candidate.candidate_id)
    return DeliberationFrame(
        frame_id=str(frame_id or uuid4()),
        candidates=tuple(values),
        admissible_ids=tuple(admissible),
        rejections=tuple(rejected),
        silence_id=silence[0].candidate_id,
    )


def rejection_map(frame: DeliberationFrame) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType({item.candidate_id: item.reasons for item in frame.rejections})


def validate_selection(
    frame: DeliberationFrame, proposal: SelectionProposal
) -> ValidatedSelection:
    if proposal.frame_id != frame.frame_id:
        raise DeliberationValidationError("selection belongs to a different frame")
    candidates = {candidate.candidate_id: candidate for candidate in frame.candidates}
    if proposal.candidate_id not in candidates:
        raise DeliberationValidationError("model selected an unknown candidate")
    if proposal.candidate_id not in frame.admissible_ids:
        raise DeliberationValidationError("model selected a policy-rejected candidate")
    model = str(proposal.model).strip()
    rationale = str(proposal.rationale).strip()
    if not model or not rationale:
        raise DeliberationValidationError("selection requires model provenance and rationale")
    return ValidatedSelection(
        frame_id=frame.frame_id,
        candidate=candidates[proposal.candidate_id],
        selected_by=model,
        rationale=rationale[:2000],
    )
