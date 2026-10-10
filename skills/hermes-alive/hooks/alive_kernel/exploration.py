"""Constrained exploration and anti-echo-chamber gate for Alive decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import re
from types import MappingProxyType
from typing import Iterable, Mapping

from .deliberation import (
    ActionKind,
    DeliberationFrame,
    DeliberationValidationError,
    SelectionProposal,
    ValidatedSelection,
    validate_selection,
)
from .content_vault import ContentVault


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class ExplorationValidationError(ValueError):
    """Exploration metadata or policy is structurally invalid."""


class ExplorationMode(StrEnum):
    EXPLOIT = "exploit"
    EXPLORE = "explore"


@dataclass(frozen=True, slots=True)
class DiversityAnnotation:
    candidate_id: str
    topic_digest: str
    source_digest: str
    mode: ExplorationMode

    def __post_init__(self) -> None:
        for name in ("candidate_id", "topic_digest", "source_digest"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ExplorationValidationError(f"{name} is required")
            object.__setattr__(self, name, value)
        if not _DIGEST_RE.fullmatch(self.topic_digest) or not _DIGEST_RE.fullmatch(
            self.source_digest
        ):
            raise ExplorationValidationError("diversity labels must be keyed digests")
        object.__setattr__(self, "mode", ExplorationMode(self.mode))


@dataclass(frozen=True, slots=True)
class DiversityTagger:
    vault: ContentVault

    def annotate(
        self,
        candidate_id: str,
        *,
        topic: str,
        source: str,
        mode: ExplorationMode,
    ) -> DiversityAnnotation:
        topic = str(topic).strip()
        source = str(source).strip()
        if not topic or not source:
            raise ExplorationValidationError("topic and source labels are required")
        return DiversityAnnotation(
            candidate_id=candidate_id,
            topic_digest=self.vault.digest_json(
                {"namespace": "exploration.topic", "value": topic}
            ),
            source_digest=self.vault.digest_json(
                {"namespace": "exploration.source", "value": source}
            ),
            mode=mode,
        )


@dataclass(frozen=True, slots=True)
class ExposureRecord:
    outcome_event_id: str
    candidate_id: str
    topic_digest: str
    source_digest: str
    mode: ExplorationMode


@dataclass(frozen=True, slots=True)
class ExplorationPolicy:
    window_size: int = 20
    max_explorations: int = 4
    minimum_share_sample: int = 5
    maximum_topic_share: float = 0.6
    maximum_source_share: float = 0.5
    maximum_topic_streak: int = 3

    def __post_init__(self) -> None:
        for name in (
            "window_size",
            "max_explorations",
            "minimum_share_sample",
            "maximum_topic_streak",
        ):
            value = int(getattr(self, name))
            if value < 1:
                raise ExplorationValidationError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        if self.max_explorations > self.window_size:
            raise ExplorationValidationError("exploration budget exceeds window")
        if self.minimum_share_sample > self.window_size:
            raise ExplorationValidationError("minimum sample exceeds window")
        for name in ("maximum_topic_share", "maximum_source_share"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 < value <= 1.0:
                raise ExplorationValidationError(f"{name} must be in (0, 1]")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class ExplorationRejection:
    candidate_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExplorationGateResult:
    frame_id: str
    admissible_ids: tuple[str, ...]
    rejections: tuple[ExplorationRejection, ...]
    silence_id: str
    history_event_ids: tuple[str, ...]


def _share(values: list[str], target: str) -> float:
    return sum(value == target for value in values) / len(values)


def apply_exploration_gate(
    frame: DeliberationFrame,
    annotations: Iterable[DiversityAnnotation],
    history: Iterable[ExposureRecord],
    policy: ExplorationPolicy,
) -> ExplorationGateResult:
    """Narrow base-policy candidates without ever widening authority."""

    annotation_values = list(annotations)
    annotation_map = {item.candidate_id: item for item in annotation_values}
    if len(annotation_map) != len(annotation_values):
        raise ExplorationValidationError("candidate annotations must be unique")
    known_ids = {item.candidate_id for item in frame.candidates}
    if any(candidate_id not in known_ids for candidate_id in annotation_map):
        raise ExplorationValidationError("annotation references an unknown candidate")
    if frame.silence_id in annotation_map:
        raise ExplorationValidationError("silence must not carry diversity metadata")

    history_values = list(history)[-policy.window_size :]
    history_ids = [item.outcome_event_id for item in history_values]
    if len(history_ids) != len(set(history_ids)):
        raise ExplorationValidationError("exposure history contains duplicate outcomes")

    admitted: list[str] = []
    rejected: list[ExplorationRejection] = []
    for candidate_id in frame.admissible_ids:
        if candidate_id == frame.silence_id:
            admitted.append(candidate_id)
            continue
        annotation = annotation_map.get(candidate_id)
        reasons: list[str] = []
        if annotation is None:
            reasons.append("diversity_metadata_missing")
        else:
            prospective = [*history_values, ExposureRecord(
                outcome_event_id="prospective",
                candidate_id=candidate_id,
                topic_digest=annotation.topic_digest,
                source_digest=annotation.source_digest,
                mode=annotation.mode,
            )][-policy.window_size :]
            exploration_count = sum(
                item.mode is ExplorationMode.EXPLORE for item in prospective
            )
            if (
                annotation.mode is ExplorationMode.EXPLORE
                and exploration_count > policy.max_explorations
            ):
                reasons.append("exploration_budget_exhausted")
            if len(prospective) >= policy.minimum_share_sample:
                topics = [item.topic_digest for item in prospective]
                sources = [item.source_digest for item in prospective]
                if _share(topics, annotation.topic_digest) > policy.maximum_topic_share:
                    reasons.append("topic_share_exceeded")
                if _share(sources, annotation.source_digest) > policy.maximum_source_share:
                    reasons.append("source_share_exceeded")
            prior_topics = [item.topic_digest for item in history_values]
            if (
                len(prior_topics) >= policy.maximum_topic_streak
                and all(
                    value == annotation.topic_digest
                    for value in prior_topics[-policy.maximum_topic_streak :]
                )
            ):
                reasons.append("topic_streak_exceeded")
        if reasons:
            rejected.append(ExplorationRejection(candidate_id, tuple(reasons)))
        else:
            admitted.append(candidate_id)
    if frame.silence_id not in admitted:
        raise ExplorationValidationError("base frame did not preserve silence")
    return ExplorationGateResult(
        frame_id=frame.frame_id,
        admissible_ids=tuple(admitted),
        rejections=tuple(rejected),
        silence_id=frame.silence_id,
        history_event_ids=tuple(history_ids),
    )


def exploration_rejection_map(
    result: ExplorationGateResult,
) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType({item.candidate_id: item.reasons for item in result.rejections})


def validate_exploratory_selection(
    frame: DeliberationFrame,
    gate: ExplorationGateResult,
    proposal: SelectionProposal,
) -> ValidatedSelection:
    if gate.frame_id != frame.frame_id:
        raise ExplorationValidationError("exploration result belongs to another frame")
    selected = validate_selection(frame, proposal)
    if proposal.candidate_id not in gate.admissible_ids:
        raise DeliberationValidationError("model selected an exploration-rejected candidate")
    return selected
