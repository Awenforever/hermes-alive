"""Leakage-resistant factual replay evaluation for the Alive kernel.

The evaluator deliberately does not estimate rewards for actions that were not
executed. It scores pre-outcome predictions only where the journal contains a
compatible, attributable observation. Missing feedback remains unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Iterable, Mapping

from .event_store import ExperienceJournal
from .events import Sensitivity
from .outcomes import OutcomeKind, OutcomeProjection, OutcomeRecord


class ReplayEvaluationError(ValueError):
    """A replay submission would overstate or leak evaluation evidence."""


@dataclass(frozen=True, slots=True)
class FactualLabels:
    useful: bool | None = None
    interruption_regret: bool | None = None
    factual_error: bool | None = None
    user_control_violation: bool | None = None
    delivery_succeeded: bool | None = None
    task_completed: bool | None = None

    def __post_init__(self) -> None:
        for name in (
            "useful", "interruption_regret", "factual_error", "user_control_violation",
            "delivery_succeeded", "task_completed",
        ):
            value = getattr(self, name)
            if value is not None and type(value) is not bool:
                raise ReplayEvaluationError(f"{name} must be boolean or unknown")


@dataclass(frozen=True, slots=True)
class ReplayEpisode:
    attempt_id: str
    attempt_sequence: int
    attempted_at: datetime
    candidate_id: str
    frame_id: str
    labels: FactualLabels
    outcome_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not all((self.attempt_id, self.candidate_id, self.frame_id)):
            raise ReplayEvaluationError("episode identifiers are required")
        if self.attempt_sequence <= 0:
            raise ReplayEvaluationError("attempt_sequence must be positive")
        if self.attempted_at.tzinfo is None or self.attempted_at.utcoffset() is None:
            raise ReplayEvaluationError("attempted_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ReplayPrediction:
    attempt_id: str
    generated_at: datetime
    evidence_event_ids: tuple[str, ...]
    useful_probability: float | None = None
    interruption_regret_probability: float | None = None
    factual_error_probability: float | None = None
    user_control_violation_probability: float | None = None

    def __post_init__(self) -> None:
        if not str(self.attempt_id).strip():
            raise ReplayEvaluationError("prediction attempt_id is required")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ReplayEvaluationError("generated_at must be timezone-aware")
        evidence = tuple(dict.fromkeys(str(value).strip() for value in self.evidence_event_ids))
        if any(not value for value in evidence):
            raise ReplayEvaluationError("prediction evidence IDs cannot be blank")
        object.__setattr__(self, "evidence_event_ids", evidence)
        for name in (
            "useful_probability",
            "interruption_regret_probability",
            "factual_error_probability",
            "user_control_violation_probability",
        ):
            value = getattr(self, name)
            if value is None:
                continue
            number = float(value)
            if not math.isfinite(number) or not 0.0 <= number <= 1.0:
                raise ReplayEvaluationError(f"{name} must be between zero and one")
            object.__setattr__(self, name, number)


@dataclass(frozen=True, slots=True)
class StrategySubmission:
    strategy: str
    trained_through_sequence: int
    predictions: tuple[ReplayPrediction, ...]

    def __post_init__(self) -> None:
        if not str(self.strategy).strip():
            raise ReplayEvaluationError("strategy is required")
        if self.trained_through_sequence < 0:
            raise ReplayEvaluationError("trained_through_sequence cannot be negative")
        ids = [prediction.attempt_id for prediction in self.predictions]
        if len(ids) != len(set(ids)):
            raise ReplayEvaluationError("a strategy may predict an attempt only once")


@dataclass(frozen=True, slots=True)
class MetricScore:
    brier: float | None
    labelled: int


@dataclass(frozen=True, slots=True)
class StrategyReport:
    strategy: str
    evaluated_attempt_ids: tuple[str, ...]
    useful: MetricScore
    interruption_regret: MetricScore
    factual_error: MetricScore
    user_control_violation: MetricScore
    delivery_succeeded: int
    delivery_failed: int
    delivery_unknown: int
    factual_snapshot_digest: str
    counterfactual_claim_allowed: bool = False
    task_completed: int = 0
    task_failed: int = 0
    task_unknown: int = 0


@dataclass(frozen=True, slots=True)
class ReplayComparison:
    baseline: str
    candidate: str
    common_attempt_ids: tuple[str, ...]
    metric_deltas: Mapping[str, float | None]
    candidate_improves_calibration: bool
    action_policy_superiority_proven: bool = False


def _explicit_boolean(details: object, *keys: str) -> bool | None:
    if not isinstance(details, Mapping):
        return None
    for key in keys:
        value = details.get(key)
        if isinstance(value, bool):
            return value
    return None


def _feedback_sentiment(details: object) -> str | None:
    if not isinstance(details, Mapping):
        return None
    value = str(details.get("sentiment") or details.get("rating") or "").strip().lower()
    if value in {"positive", "helpful", "useful", "good"}:
        return "positive"
    if value in {"negative", "unhelpful", "bad"}:
        return "negative"
    return None


def labels_from_outcomes(outcomes: Iterable[OutcomeRecord]) -> FactualLabels:
    values = tuple(outcomes)
    kinds = {value.kind for value in values}
    useful_votes: set[bool] = set()
    # Operational completion is observable, user benefit is not implied.
    # Keep this separate even for repeated successful executions.
    for outcome in values:
        if outcome.kind is OutcomeKind.EXPLICIT_FEEDBACK:
            sentiment = _feedback_sentiment(outcome.details)
            if sentiment is not None:
                useful_votes.add(sentiment == "positive")

    def single(votes: set[bool]) -> bool | None:
        return next(iter(votes)) if len(votes) == 1 else None

    regret_votes = {
        value
        for outcome in values
        if (value := _explicit_boolean(outcome.details, "interruption_regret")) is not None
    }
    factual_votes = {
        value
        for outcome in values
        if (value := _explicit_boolean(outcome.details, "factual_error")) is not None
    }
    control_votes = {
        value
        for outcome in values
        if (value := _explicit_boolean(outcome.details, "user_control_violation")) is not None
    }
    delivery_votes: set[bool] = set()
    if OutcomeKind.DELIVERY_SUCCEEDED in kinds:
        delivery_votes.add(True)
    if OutcomeKind.DELIVERY_FAILED in kinds:
        delivery_votes.add(False)
    task_votes: set[bool] = set()
    if OutcomeKind.TASK_COMPLETED in kinds:
        task_votes.add(True)
    if OutcomeKind.TASK_FAILED in kinds:
        task_votes.add(False)
    return FactualLabels(
        useful=single(useful_votes),
        interruption_regret=single(regret_votes),
        factual_error=single(factual_votes),
        user_control_violation=single(control_votes),
        delivery_succeeded=single(delivery_votes),
        task_completed=single(task_votes),
    )


def build_factual_episodes(
    journal: ExperienceJournal,
    outcomes: OutcomeProjection,
    *,
    clearance: Sensitivity,
    observed_through_sequence: int | None = None,
    observed_by: datetime | None = None,
) -> tuple[ReplayEpisode, ...]:
    """Build factual episodes within journal and optional wall-clock snapshots.

    Sequence describes journal availability, not chronological observation.
    Retrospective callers must supply observed_by as well: an earlier append
    may carry a future observation time (for example under host clock skew).
    Both the outcome and its originating observation must fit the snapshot.
    """

    if observed_by is not None and (
        observed_by.tzinfo is None or observed_by.utcoffset() is None
    ):
        raise ReplayEvaluationError("observed_by must be timezone-aware")

    through = (
        journal.last_sequence()
        if observed_through_sequence is None
        else observed_through_sequence
    )
    if through < 0 or through > journal.last_sequence():
        raise ReplayEvaluationError("invalid observed_through_sequence")
    episodes: list[ReplayEpisode] = []
    for attempt in outcomes.attempts(clearance=clearance):
        attempt_event = journal.get(f"action.attempt:{attempt.attempt_id}")
        if attempt_event is None or attempt_event.sequence > through:
            continue
        if observed_by is not None and attempt_event.event.observed_at > observed_by:
            continue
        included: list[OutcomeRecord] = []
        event_ids: list[str] = []
        for outcome in outcomes.outcomes(attempt.attempt_id, clearance=clearance):
            event_id = f"outcome.record:{outcome.outcome_id}"
            record = journal.get(event_id)
            source = journal.get(outcome.source_event_id)
            if (
                record is not None and source is not None
                and record.sequence <= through and source.sequence <= through
                and (observed_by is None or (
                    record.event.observed_at <= observed_by
                    and source.event.observed_at <= observed_by
                ))
            ):
                included.append(outcome)
                event_ids.append(event_id)
        episodes.append(
            ReplayEpisode(
                attempt.attempt_id,
                attempt_event.sequence,
                attempt.attempted_at,
                attempt.candidate_id,
                attempt.frame_id,
                labels_from_outcomes(included),
                tuple(event_ids),
            )
        )
    return tuple(episodes)


def _metric(pairs: Iterable[tuple[float | None, bool | None]]) -> MetricScore:
    labelled = [
        (prediction, label)
        for prediction, label in pairs
        if prediction is not None and label is not None
    ]
    if not labelled:
        return MetricScore(None, 0)
    error = sum((float(prediction) - float(label)) ** 2 for prediction, label in labelled)
    return MetricScore(error / len(labelled), len(labelled))


def evaluate_submission(
    journal: ExperienceJournal,
    episodes: Iterable[ReplayEpisode],
    submission: StrategySubmission,
    *,
    holdout_after_sequence: int,
    outcomes: OutcomeProjection,
    clearance: Sensitivity,
    observed_through_sequence: int | None = None,
    observed_by: datetime | None = None,
) -> StrategyReport:
    if outcomes.journal is not journal:
        raise ReplayEvaluationError("outcome projection must belong to the evaluation journal")
    if holdout_after_sequence < 0 or holdout_after_sequence > journal.last_sequence():
        raise ReplayEvaluationError("invalid holdout boundary")
    if submission.trained_through_sequence > holdout_after_sequence:
        raise ReplayEvaluationError("strategy training crosses the holdout boundary")
    # Supplied episodes are a request, not a trusted label authority. Rebuild
    # labels and their complete evidence set from current validated reads under
    # the explicitly requested snapshot, including erased-content semantics.
    factual = {
        episode.attempt_id: episode for episode in build_factual_episodes(
            journal, outcomes, clearance=clearance,
            observed_through_sequence=observed_through_sequence, observed_by=observed_by,
        )
    }
    supplied = tuple(episodes)
    if len({episode.attempt_id for episode in supplied}) != len(supplied):
        raise ReplayEvaluationError("duplicate factual episode")
    if any(factual.get(episode.attempt_id) != episode for episode in supplied):
        raise ReplayEvaluationError("episode labels or evidence do not match the factual snapshot")
    episode_map = {
        episode.attempt_id: episode
        for episode in supplied
        if episode.attempt_sequence > holdout_after_sequence
    }
    predictions: list[tuple[ReplayEpisode, ReplayPrediction]] = []
    for prediction in submission.predictions:
        episode = episode_map.get(prediction.attempt_id)
        if episode is None:
            raise ReplayEvaluationError("prediction does not belong to the holdout cohort")
        attempt_event = journal.get(f"action.attempt:{episode.attempt_id}")
        if (
            attempt_event is None
            or attempt_event.event.event_type != "action.attempted"
            or attempt_event.sequence != episode.attempt_sequence
            or attempt_event.event.observed_at != episode.attempted_at
            or str(attempt_event.event.payload.get("candidate_id") or "")
            != episode.candidate_id
        ):
            raise ReplayEvaluationError("episode is not backed by its factual attempt event")
        if prediction.generated_at.astimezone(timezone.utc) > episode.attempted_at.astimezone(timezone.utc):
            raise ReplayEvaluationError("prediction was generated after the action attempt")
        for event_id in prediction.evidence_event_ids:
            evidence = journal.get(event_id)
            if evidence is None:
                raise ReplayEvaluationError("prediction cites missing evidence")
            if list(Sensitivity).index(evidence.event.sensitivity) > list(Sensitivity).index(
                Sensitivity(clearance)
            ):
                raise ReplayEvaluationError("prediction evidence exceeds privacy clearance")
            if evidence.event.subject != attempt_event.event.subject and not (
                evidence.event.subject is None and evidence.event.sensitivity is Sensitivity.PUBLIC
            ):
                raise ReplayEvaluationError("prediction evidence belongs to another privacy scope")
            if evidence.sequence >= episode.attempt_sequence:
                raise ReplayEvaluationError("prediction cites future or same-attempt evidence")
            if evidence.event.observed_at > prediction.generated_at:
                raise ReplayEvaluationError("prediction cites evidence observed after generation")
            if evidence.event.expires_at is not None and evidence.event.expires_at <= prediction.generated_at:
                raise ReplayEvaluationError("prediction cites evidence expired at generation")
        predictions.append((episode, prediction))

    delivery = [episode.labels.delivery_succeeded for episode, _ in predictions]
    tasks = [episode.labels.task_completed for episode, _ in predictions]
    snapshot = [
        {
            "attempt_id": episode.attempt_id,
            "attempt_sequence": episode.attempt_sequence,
            "attempted_at": episode.attempted_at.isoformat(),
            "candidate_id": episode.candidate_id,
            "frame_id": episode.frame_id,
            "outcome_event_ids": episode.outcome_event_ids,
            "labels": {name: getattr(episode.labels, name) for name in (
                "useful", "interruption_regret", "factual_error", "user_control_violation",
                "delivery_succeeded", "task_completed",
            )},
        }
        for episode, _ in sorted(predictions, key=lambda pair: pair[0].attempt_id)
    ]
    return StrategyReport(
        strategy=submission.strategy,
        evaluated_attempt_ids=tuple(episode.attempt_id for episode, _ in predictions),
        useful=_metric(
            (prediction.useful_probability, episode.labels.useful)
            for episode, prediction in predictions
        ),
        interruption_regret=_metric(
            (prediction.interruption_regret_probability, episode.labels.interruption_regret)
            for episode, prediction in predictions
        ),
        factual_error=_metric(
            (prediction.factual_error_probability, episode.labels.factual_error)
            for episode, prediction in predictions
        ),
        user_control_violation=_metric(
            (prediction.user_control_violation_probability, episode.labels.user_control_violation)
            for episode, prediction in predictions
        ),
        delivery_succeeded=sum(value is True for value in delivery),
        delivery_failed=sum(value is False for value in delivery),
        delivery_unknown=sum(value is None for value in delivery),
        task_completed=sum(value is True for value in tasks),
        task_failed=sum(value is False for value in tasks),
        task_unknown=sum(value is None for value in tasks),
        factual_snapshot_digest=hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    )


def compare_reports(baseline: StrategyReport, candidate: StrategyReport) -> ReplayComparison:
    candidate_ids = set(candidate.evaluated_attempt_ids)
    common = tuple(value for value in baseline.evaluated_attempt_ids if value in candidate_ids)
    if (
        not common
        or set(common) != set(baseline.evaluated_attempt_ids)
        or set(common) != candidate_ids
    ):
        raise ReplayEvaluationError("strategy comparison requires the same factual attempt cohort")
    if not baseline.factual_snapshot_digest or (
        baseline.factual_snapshot_digest != candidate.factual_snapshot_digest
    ):
        raise ReplayEvaluationError("strategy comparison requires the same factual label snapshot")
    deltas: dict[str, float | None] = {}
    comparable: list[float] = []
    for name in (
        "useful", "interruption_regret", "factual_error", "user_control_violation"
    ):
        old = getattr(baseline, name)
        new = getattr(candidate, name)
        if old.labelled != new.labelled or old.brier is None or new.brier is None:
            deltas[name] = None
            continue
        delta = new.brier - old.brier
        deltas[name] = delta
        comparable.append(delta)
    improves = bool(comparable) and all(value <= 0.0 for value in comparable) and any(
        value < 0.0 for value in comparable
    )
    return ReplayComparison(
        baseline.strategy, candidate.strategy, common, deltas, improves
    )
