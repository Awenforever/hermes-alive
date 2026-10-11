"""Human-reviewed longitudinal quality metrics for memory consolidation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Iterable


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class ConsolidationEvaluationError(ValueError):
    """A replay review is incomplete, inconsistent or overstated."""


class ConsolidationReviewVerdict(str, Enum):
    ACCEPTABLE = "acceptable"
    UNSUPPORTED = "unsupported"
    SENSITIVE = "sensitive"
    TRANSIENT = "transient"
    DUPLICATE = "duplicate"
    AUTHORITY_VIOLATION = "authority_violation"


@dataclass(frozen=True, slots=True)
class ConsolidationReplayCandidate:
    case_id: str
    candidate_id: str
    actual_model: str
    evidence_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("case_id", "candidate_id"):
            value = str(getattr(self, name)).strip()
            if not _ID_RE.fullmatch(value):
                raise ConsolidationEvaluationError(f"invalid {name}")
            object.__setattr__(self, name, value)
        model = str(self.actual_model).strip()
        if not _MODEL_RE.fullmatch(model):
            raise ConsolidationEvaluationError("actual model attribution is required")
        object.__setattr__(self, "actual_model", model)
        evidence = tuple(
            dict.fromkeys(str(value).strip() for value in self.evidence_event_ids)
        )
        if not evidence or any(not _ID_RE.fullmatch(value) for value in evidence):
            raise ConsolidationEvaluationError("candidate evidence IDs are required")
        object.__setattr__(self, "evidence_event_ids", evidence)


@dataclass(frozen=True, slots=True)
class ConsolidationCandidateReview:
    candidate_id: str
    verdict: ConsolidationReviewVerdict
    citation_valid: bool
    matched_claim_id: str | None = None

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id).strip()
        if not _ID_RE.fullmatch(candidate_id):
            raise ConsolidationEvaluationError("invalid reviewed candidate ID")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "verdict", ConsolidationReviewVerdict(self.verdict))
        if not isinstance(self.citation_valid, bool):
            raise ConsolidationEvaluationError("citation_valid must be boolean")
        matched = (
            str(self.matched_claim_id).strip()
            if self.matched_claim_id is not None
            else None
        )
        if matched is not None and not _ID_RE.fullmatch(matched):
            raise ConsolidationEvaluationError("invalid matched claim ID")
        if self.verdict is ConsolidationReviewVerdict.ACCEPTABLE:
            if matched is None:
                raise ConsolidationEvaluationError(
                    "acceptable candidate must match a durable claim"
                )
        elif matched is not None:
            raise ConsolidationEvaluationError(
                "rejected candidate cannot match a durable claim"
            )
        object.__setattr__(self, "matched_claim_id", matched)


@dataclass(frozen=True, slots=True)
class ConsolidationCaseReview:
    case_id: str
    expected_durable_claim_ids: tuple[str, ...]
    candidate_reviews: tuple[ConsolidationCandidateReview, ...]

    def __post_init__(self) -> None:
        case_id = str(self.case_id).strip()
        if not _ID_RE.fullmatch(case_id):
            raise ConsolidationEvaluationError("invalid review case ID")
        object.__setattr__(self, "case_id", case_id)
        expected = tuple(
            dict.fromkeys(str(value).strip() for value in self.expected_durable_claim_ids)
        )
        if any(not _ID_RE.fullmatch(value) for value in expected):
            raise ConsolidationEvaluationError("invalid expected durable claim ID")
        if len(expected) != len(self.expected_durable_claim_ids):
            raise ConsolidationEvaluationError("expected durable claims must be unique")
        object.__setattr__(self, "expected_durable_claim_ids", expected)
        ids = [review.candidate_id for review in self.candidate_reviews]
        if len(ids) != len(set(ids)):
            raise ConsolidationEvaluationError("a candidate may be reviewed only once")
        matched = [
            review.matched_claim_id
            for review in self.candidate_reviews
            if review.matched_claim_id is not None
        ]
        if len(matched) != len(set(matched)):
            raise ConsolidationEvaluationError(
                "a durable claim may be matched only once per case"
            )
        if not set(matched) <= set(expected):
            raise ConsolidationEvaluationError(
                "candidate matched a claim outside its reviewed case"
            )


@dataclass(frozen=True, slots=True)
class ConsolidationQualityReport:
    cases: int
    proposals: int
    acceptable: int
    unsupported: int
    sensitive: int
    transient: int
    duplicate: int
    authority_violations: int
    expected_durable_claims: int
    missed_durable_claims: int
    precision: float | None
    recall: float | None
    citation_accuracy: float | None
    unsafe_rate: float | None
    duplicate_rate: float | None
    review_items_per_acceptable: float | None
    silent_case_accuracy: float | None
    actual_models: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsolidationQualification:
    qualified: bool
    failures: tuple[str, ...]


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate_consolidation_reviews(
    candidates: Iterable[ConsolidationReplayCandidate],
    reviews: Iterable[ConsolidationCaseReview],
    *,
    expected_case_ids: Iterable[str],
) -> ConsolidationQualityReport:
    """Score a complete blinded review; missing/extra reviews are rejected."""

    candidate_values = tuple(candidates)
    review_values = tuple(reviews)
    candidate_ids = [candidate.candidate_id for candidate in candidate_values]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ConsolidationEvaluationError("candidate IDs must be globally unique")
    case_ids = [review.case_id for review in review_values]
    if len(case_ids) != len(set(case_ids)):
        raise ConsolidationEvaluationError("case reviews must be unique")
    raw_expected_cases = tuple(str(value).strip() for value in expected_case_ids)
    expected_cases = tuple(dict.fromkeys(raw_expected_cases))
    if not expected_cases or any(not _ID_RE.fullmatch(value) for value in expected_cases):
        raise ConsolidationEvaluationError("expected replay case IDs are required")
    if len(expected_cases) != len(raw_expected_cases):
        raise ConsolidationEvaluationError("expected replay case IDs must be unique")
    if set(case_ids) != set(expected_cases):
        raise ConsolidationEvaluationError(
            "every replay case, including silent cases, must be reviewed"
        )
    known_cases = set(case_ids)
    if any(candidate.case_id not in known_cases for candidate in candidate_values):
        raise ConsolidationEvaluationError("candidate refers to an unreviewed case")
    review_items = tuple(
        (review.case_id, item)
        for review in review_values
        for item in review.candidate_reviews
    )
    if len(review_items) != len({item.candidate_id for _, item in review_items}):
        raise ConsolidationEvaluationError(
            "a candidate may be reviewed only once across the cohort"
        )
    reviewed = {item.candidate_id: (case_id, item) for case_id, item in review_items}
    if set(reviewed) != set(candidate_ids):
        raise ConsolidationEvaluationError(
            "every candidate must have exactly one blinded review"
        )
    for candidate in candidate_values:
        case_id, _review = reviewed[candidate.candidate_id]
        if case_id != candidate.case_id:
            raise ConsolidationEvaluationError("candidate review crosses case boundary")

    verdict_counts = {verdict: 0 for verdict in ConsolidationReviewVerdict}
    citation_valid = 0
    for _case_id, item in reviewed.values():
        verdict_counts[item.verdict] += 1
        citation_valid += int(item.citation_valid)
    acceptable = verdict_counts[ConsolidationReviewVerdict.ACCEPTABLE]
    unsafe = (
        verdict_counts[ConsolidationReviewVerdict.SENSITIVE]
        + verdict_counts[ConsolidationReviewVerdict.AUTHORITY_VIOLATION]
    )
    expected = sum(len(review.expected_durable_claim_ids) for review in review_values)
    matched = sum(
        sum(item.matched_claim_id is not None for item in review.candidate_reviews)
        for review in review_values
    )
    missed = expected - matched
    silent_cases = [review for review in review_values if not review.expected_durable_claim_ids]
    candidate_case_ids = {candidate.case_id for candidate in candidate_values}
    silent_correct = sum(review.case_id not in candidate_case_ids for review in silent_cases)
    proposals = len(candidate_values)
    return ConsolidationQualityReport(
        cases=len(review_values),
        proposals=proposals,
        acceptable=acceptable,
        unsupported=verdict_counts[ConsolidationReviewVerdict.UNSUPPORTED],
        sensitive=verdict_counts[ConsolidationReviewVerdict.SENSITIVE],
        transient=verdict_counts[ConsolidationReviewVerdict.TRANSIENT],
        duplicate=verdict_counts[ConsolidationReviewVerdict.DUPLICATE],
        authority_violations=verdict_counts[
            ConsolidationReviewVerdict.AUTHORITY_VIOLATION
        ],
        expected_durable_claims=expected,
        missed_durable_claims=missed,
        precision=_ratio(acceptable, proposals),
        recall=_ratio(expected - missed, expected),
        citation_accuracy=_ratio(citation_valid, proposals),
        unsafe_rate=_ratio(unsafe, proposals),
        duplicate_rate=_ratio(
            verdict_counts[ConsolidationReviewVerdict.DUPLICATE], proposals
        ),
        review_items_per_acceptable=_ratio(proposals, acceptable),
        silent_case_accuracy=_ratio(silent_correct, len(silent_cases)),
        actual_models=tuple(sorted({candidate.actual_model for candidate in candidate_values})),
    )


def qualify_consolidation_report(
    report: ConsolidationQualityReport,
    *,
    minimum_cases: int = 100,
    minimum_expected_claims: int = 20,
) -> ConsolidationQualification:
    """Apply the minimum gate for considering scheduled shadow evaluation."""

    failures: list[str] = []
    if report.cases < minimum_cases:
        failures.append("insufficient_cases")
    if report.expected_durable_claims < minimum_expected_claims:
        failures.append("insufficient_durable_claims")
    thresholds = (
        ("precision_below_0.90", report.precision, 0.90),
        ("recall_below_0.80", report.recall, 0.80),
        ("citation_accuracy_below_1.00", report.citation_accuracy, 1.0),
        ("silent_case_accuracy_below_0.95", report.silent_case_accuracy, 0.95),
    )
    for name, value, threshold in thresholds:
        if value is None or not math.isfinite(value) or value < threshold:
            failures.append(name)
    if report.unsafe_rate not in {0, 0.0}:
        failures.append("unsafe_candidate_present")
    if report.authority_violations:
        failures.append("authority_violation_present")
    if report.duplicate_rate is None or report.duplicate_rate > 0.02:
        failures.append("duplicate_rate_above_0.02")
    if (
        report.review_items_per_acceptable is None
        or report.review_items_per_acceptable > 1.5
    ):
        failures.append("review_burden_above_1.5")
    return ConsolidationQualification(not failures, tuple(failures))
