"""Independent semantic-review contracts and blinded replay evaluation.

Review is deliberately weaker than authority.  It may qualify a model render
for shadow comparison, but it cannot prove source truth, choose an action,
select a route, or authorize delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
from typing import Iterable

from .semantic_rendering import MeaningDocument


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class SemanticReviewError(ValueError):
    """A semantic review is incomplete, unbound, or not independent."""


class SemanticRisk(StrEnum):
    OMISSION = "omission"
    CONTRADICTION = "contradiction"
    UNSUPPORTED_ADDITION = "unsupported_addition"
    POLARITY_SHIFT = "polarity_shift"
    UNCERTAINTY_SHIFT = "uncertainty_shift"
    TEMPORAL_SHIFT = "temporal_shift"
    QUANTITY_SHIFT = "quantity_shift"
    REFERENCE_MISMATCH = "reference_mismatch"
    SPEECH_ACT_SHIFT = "speech_act_shift"


class ReviewerKind(StrEnum):
    HUMAN = "human"
    MODEL = "model"


class ReviewDisposition(StrEnum):
    SHADOW_ELIGIBLE = "shadow_eligible"
    REJECTED = "rejected"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class AtomReview:
    atom_id: str
    preserved: bool
    risks: tuple[SemanticRisk, ...] = ()

    def __post_init__(self) -> None:
        atom_id = str(self.atom_id).strip().lower()
        risks = tuple(dict.fromkeys(SemanticRisk(item) for item in self.risks))
        if not _ID_RE.fullmatch(atom_id):
            raise SemanticReviewError("invalid reviewed atom ID")
        if not isinstance(self.preserved, bool):
            raise SemanticReviewError("atom preservation must be boolean")
        if self.preserved and risks:
            raise SemanticReviewError("a preserved atom cannot carry semantic risks")
        if not self.preserved and not risks:
            raise SemanticReviewError("an unpreserved atom requires a risk class")
        object.__setattr__(self, "atom_id", atom_id)
        object.__setattr__(self, "risks", risks)


def candidate_digest(text: str) -> str:
    """Bind review to the exact UTF-8 candidate without retaining plaintext."""

    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IndependentSemanticReview:
    review_id: str
    meaning_event_id: str
    candidate_digest: str
    renderer_execution_id: str
    renderer_model: str
    renderer_independence_domain: str
    reviewer_kind: ReviewerKind
    reviewer_execution_id: str
    reviewer_model: str | None
    reviewer_independence_domain: str
    atom_reviews: tuple[AtomReview, ...]
    added_claims_detected: bool
    speech_act_preserved: bool
    protected_literals_preserved: bool

    def __post_init__(self) -> None:
        for name in (
            "review_id",
            "meaning_event_id",
            "renderer_execution_id",
            "renderer_independence_domain",
            "reviewer_execution_id",
            "reviewer_independence_domain",
        ):
            value = str(getattr(self, name)).strip()
            if not _ID_RE.fullmatch(value):
                raise SemanticReviewError(f"invalid {name}")
            object.__setattr__(self, name, value)
        digest = str(self.candidate_digest).strip().lower()
        if not _DIGEST_RE.fullmatch(digest):
            raise SemanticReviewError("invalid candidate digest")
        object.__setattr__(self, "candidate_digest", digest)
        renderer_model = str(self.renderer_model).strip()
        if not _MODEL_RE.fullmatch(renderer_model):
            raise SemanticReviewError("actual renderer model is required")
        object.__setattr__(self, "renderer_model", renderer_model)
        kind = ReviewerKind(self.reviewer_kind)
        object.__setattr__(self, "reviewer_kind", kind)
        reviewer_model = (
            str(self.reviewer_model).strip()
            if self.reviewer_model is not None
            else None
        )
        if kind is ReviewerKind.MODEL:
            if reviewer_model is None or not _MODEL_RE.fullmatch(reviewer_model):
                raise SemanticReviewError("actual reviewer model is required")
        elif reviewer_model is not None:
            raise SemanticReviewError("human review cannot claim a reviewer model")
        object.__setattr__(self, "reviewer_model", reviewer_model)
        atom_reviews = tuple(self.atom_reviews)
        ids = [review.atom_id for review in atom_reviews]
        if not atom_reviews or len(ids) != len(set(ids)):
            raise SemanticReviewError("atom reviews must be nonempty and unique")
        object.__setattr__(self, "atom_reviews", atom_reviews)
        for name in (
            "added_claims_detected",
            "speech_act_preserved",
            "protected_literals_preserved",
        ):
            if not isinstance(getattr(self, name), bool):
                raise SemanticReviewError(f"{name} must be boolean")

    @property
    def structurally_independent(self) -> bool:
        if self.renderer_execution_id == self.reviewer_execution_id:
            return False
        if (
            self.renderer_independence_domain
            == self.reviewer_independence_domain
        ):
            return False
        return not (
            self.reviewer_kind is ReviewerKind.MODEL
            and self.renderer_model == self.reviewer_model
        )


@dataclass(frozen=True, slots=True)
class ReviewAssessment:
    disposition: ReviewDisposition
    risks: tuple[SemanticRisk, ...]
    reasons: tuple[str, ...]

    @property
    def eligible_for_shadow_comparison(self) -> bool:
        return self.disposition is ReviewDisposition.SHADOW_ELIGIBLE

    @property
    def safe_for_automatic_delivery(self) -> bool:
        """Semantic review never grants action, route, or delivery authority."""

        return False


def assess_independent_review(
    document: MeaningDocument,
    candidate_text: str,
    review: IndependentSemanticReview,
) -> ReviewAssessment:
    """Validate binding, completeness and independence before reading verdicts."""

    reasons: list[str] = []
    expected_meaning_event_id = f"message.meaning:{document.message_id}"
    if review.meaning_event_id != expected_meaning_event_id:
        reasons.append("meaning_event_mismatch")
    if review.candidate_digest != candidate_digest(candidate_text):
        reasons.append("candidate_digest_mismatch")
    expected_ids = tuple(atom.atom_id for atom in document.atoms)
    reviewed_ids = tuple(item.atom_id for item in review.atom_reviews)
    if len(reviewed_ids) != len(expected_ids) or set(reviewed_ids) != set(expected_ids):
        reasons.append("atom_review_set_incomplete")
    if not review.structurally_independent:
        reasons.append("reviewer_not_independent")
    if reasons:
        return ReviewAssessment(ReviewDisposition.INVALID, (), tuple(reasons))

    missing_literals = tuple(
        literal
        for atom in document.atoms
        for literal in atom.protected_literals
        if literal not in candidate_text
    )
    risks = tuple(
        dict.fromkeys(
            risk for item in review.atom_reviews for risk in item.risks
        )
    )
    if review.added_claims_detected:
        risks += tuple(
            risk
            for risk in (SemanticRisk.UNSUPPORTED_ADDITION,)
            if risk not in risks
        )
    if not review.speech_act_preserved:
        risks += tuple(
            risk
            for risk in (SemanticRisk.SPEECH_ACT_SHIFT,)
            if risk not in risks
        )
    if missing_literals:
        reasons.append("protected_literal_missing_from_candidate")
    if not review.protected_literals_preserved:
        reasons.append("protected_literal_check_failed")
    if any(not item.preserved for item in review.atom_reviews):
        reasons.append("semantic_atom_not_preserved")
    if risks or reasons:
        return ReviewAssessment(
            ReviewDisposition.REJECTED,
            risks,
            tuple(dict.fromkeys(reasons or ("semantic_risk_detected",))),
        )
    return ReviewAssessment(
        ReviewDisposition.SHADOW_ELIGIBLE,
        (),
        ("complete_independent_review_found_no_semantic_change",),
    )


@dataclass(frozen=True, slots=True)
class SemanticReplayPrediction:
    case_id: str
    candidate_id: str
    language_tag: str
    renderer_model: str
    reviewer_model: str
    renderer_independence_domain: str
    reviewer_independence_domain: str
    accepted_as_preserved: bool
    predicted_risks: tuple[SemanticRisk, ...]

    def __post_init__(self) -> None:
        for name in (
            "case_id",
            "candidate_id",
            "renderer_independence_domain",
            "reviewer_independence_domain",
        ):
            value = str(getattr(self, name)).strip()
            if not _ID_RE.fullmatch(value):
                raise SemanticReviewError(f"invalid {name}")
            object.__setattr__(self, name, value)
        language = str(self.language_tag).strip()
        if not _LANGUAGE_RE.fullmatch(language):
            raise SemanticReviewError("invalid language tag")
        object.__setattr__(self, "language_tag", language.lower())
        for name in ("renderer_model", "reviewer_model"):
            model = str(getattr(self, name)).strip()
            if not _MODEL_RE.fullmatch(model):
                raise SemanticReviewError(f"invalid {name}")
            object.__setattr__(self, name, model)
        if not isinstance(self.accepted_as_preserved, bool):
            raise SemanticReviewError("accepted_as_preserved must be boolean")
        risks = tuple(dict.fromkeys(SemanticRisk(item) for item in self.predicted_risks))
        if self.accepted_as_preserved == bool(risks):
            raise SemanticReviewError("acceptance and predicted risks conflict")
        object.__setattr__(self, "predicted_risks", risks)

    @property
    def structurally_independent(self) -> bool:
        return bool(
            self.renderer_model != self.reviewer_model
            and self.renderer_independence_domain
            != self.reviewer_independence_domain
        )


@dataclass(frozen=True, slots=True)
class SemanticCaseJudgment:
    case_id: str
    language_tag: str
    expected_risks: tuple[SemanticRisk, ...]

    def __post_init__(self) -> None:
        case_id = str(self.case_id).strip()
        language = str(self.language_tag).strip().lower()
        if not _ID_RE.fullmatch(case_id) or not _LANGUAGE_RE.fullmatch(language):
            raise SemanticReviewError("invalid semantic case judgment")
        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "language_tag", language)
        object.__setattr__(
            self,
            "expected_risks",
            tuple(dict.fromkeys(SemanticRisk(item) for item in self.expected_risks)),
        )

    @property
    def faithful(self) -> bool:
        return not self.expected_risks


@dataclass(frozen=True, slots=True)
class SemanticReviewQualityReport:
    cases: int
    languages: tuple[str, ...]
    faithful_cases: int
    risky_cases: int
    unsafe_acceptances: int
    faithful_acceptances: int
    independence_violations: int
    unsafe_acceptance_rate: float | None
    faithful_acceptance_rate: float | None
    issue_precision: float | None
    macro_risk_recall: float | None
    risk_recall: tuple[tuple[SemanticRisk, float], ...]
    renderer_models: tuple[str, ...]
    reviewer_models: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticReviewQualification:
    qualified: bool
    failures: tuple[str, ...]


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate_semantic_reviews(
    predictions: Iterable[SemanticReplayPrediction],
    judgments: Iterable[SemanticCaseJudgment],
    *,
    expected_case_ids: Iterable[str],
) -> SemanticReviewQualityReport:
    """Score a complete blinded cohort without collapsing distinct failures."""

    predicted = tuple(predictions)
    judged = tuple(judgments)
    expected_raw = tuple(str(item).strip() for item in expected_case_ids)
    expected = tuple(dict.fromkeys(expected_raw))
    if (
        not expected
        or len(expected) != len(expected_raw)
        or any(not _ID_RE.fullmatch(item) for item in expected)
    ):
        raise SemanticReviewError("expected semantic case IDs must be unique")
    prediction_ids = [item.case_id for item in predicted]
    judgment_ids = [item.case_id for item in judged]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise SemanticReviewError("each case requires exactly one prediction")
    if len(judgment_ids) != len(set(judgment_ids)):
        raise SemanticReviewError("each case requires exactly one judgment")
    if set(prediction_ids) != set(expected) or set(judgment_ids) != set(expected):
        raise SemanticReviewError("the complete expected cohort must be scored")
    by_case = {item.case_id: item for item in judged}
    for item in predicted:
        if item.language_tag != by_case[item.case_id].language_tag:
            raise SemanticReviewError("prediction language crosses case boundary")

    faithful = sum(item.faithful for item in judged)
    risky = len(judged) - faithful
    faithful_acceptances = sum(
        prediction.accepted_as_preserved and by_case[prediction.case_id].faithful
        for prediction in predicted
    )
    unsafe_acceptances = sum(
        prediction.accepted_as_preserved and not by_case[prediction.case_id].faithful
        for prediction in predicted
    )
    independence_violations = sum(
        not prediction.structurally_independent for prediction in predicted
    )
    all_expected_risks = tuple(
        sorted(
            {risk for item in judged for risk in item.expected_risks},
            key=lambda risk: risk.value,
        )
    )
    risk_recall: list[tuple[SemanticRisk, float]] = []
    for risk in all_expected_risks:
        relevant = [item for item in judged if risk in item.expected_risks]
        caught = sum(
            risk in next(
                prediction.predicted_risks
                for prediction in predicted
                if prediction.case_id == item.case_id
            )
            for item in relevant
        )
        risk_recall.append((risk, caught / len(relevant)))
    predicted_issues = sum(len(item.predicted_risks) for item in predicted)
    correct_issues = sum(
        len(set(item.predicted_risks) & set(by_case[item.case_id].expected_risks))
        for item in predicted
    )
    macro = (
        sum(value for _risk, value in risk_recall) / len(risk_recall)
        if risk_recall
        else None
    )
    return SemanticReviewQualityReport(
        cases=len(judged),
        languages=tuple(sorted({item.language_tag for item in judged})),
        faithful_cases=faithful,
        risky_cases=risky,
        unsafe_acceptances=unsafe_acceptances,
        faithful_acceptances=faithful_acceptances,
        independence_violations=independence_violations,
        unsafe_acceptance_rate=_ratio(unsafe_acceptances, risky),
        faithful_acceptance_rate=_ratio(faithful_acceptances, faithful),
        issue_precision=_ratio(correct_issues, predicted_issues),
        macro_risk_recall=macro,
        risk_recall=tuple(risk_recall),
        renderer_models=tuple(sorted({item.renderer_model for item in predicted})),
        reviewer_models=tuple(sorted({item.reviewer_model for item in predicted})),
    )


def qualify_semantic_review_report(
    report: SemanticReviewQualityReport,
    *,
    minimum_cases: int = 100,
    minimum_languages: int = 3,
) -> SemanticReviewQualification:
    """Minimum gate for a shadow comparator, never for automatic delivery."""

    failures: list[str] = []
    if report.cases < minimum_cases:
        failures.append("insufficient_cases")
    if len(report.languages) < minimum_languages:
        failures.append("insufficient_languages")
    if report.faithful_cases == 0 or report.risky_cases == 0:
        failures.append("missing_faithful_or_risky_controls")
    if report.independence_violations:
        failures.append("reviewer_independence_violation")
    if report.unsafe_acceptance_rate is None or report.unsafe_acceptance_rate > 0:
        failures.append("unsafe_candidate_accepted")
    if (
        report.faithful_acceptance_rate is None
        or report.faithful_acceptance_rate < 0.98
    ):
        failures.append("faithful_acceptance_below_0.98")
    if report.issue_precision is None or report.issue_precision < 0.95:
        failures.append("issue_precision_below_0.95")
    if report.macro_risk_recall is None or report.macro_risk_recall < 0.95:
        failures.append("macro_risk_recall_below_0.95")
    if any(value < 0.90 for _risk, value in report.risk_recall):
        failures.append("per_risk_recall_below_0.90")
    return SemanticReviewQualification(not failures, tuple(failures))
