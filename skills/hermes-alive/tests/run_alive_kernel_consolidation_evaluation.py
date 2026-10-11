#!/usr/bin/env python3
"""Blinded review completeness and consolidation qualification contracts."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from alive_kernel.consolidation_evaluation import (  # noqa: E402
    ConsolidationCandidateReview,
    ConsolidationCaseReview,
    ConsolidationEvaluationError,
    ConsolidationReplayCandidate,
    ConsolidationReviewVerdict,
    evaluate_consolidation_reviews,
    qualify_consolidation_report,
)


def main() -> int:
    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "consolidation_replay_seed_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert fixture["schema_version"] == 1
    assert fixture["provenance"] == "synthetic_seed"
    assert fixture["privacy_reviewed"] is True
    assert len(fixture["cases"]) == 10
    text = json.dumps(fixture, ensure_ascii=False)
    assert "@" not in text and "sk-" not in text.lower()

    candidates = (
        ConsolidationReplayCandidate(
            "stable-style", "candidate-style", "provider/model-a", ("evidence:style",)
        ),
        ConsolidationReplayCandidate(
            "temporary-task", "candidate-temporary", "provider/model-a", ("evidence:task",)
        ),
        ConsolidationReplayCandidate(
            "secret-material", "candidate-secret", "provider/model-b", ("evidence:secret",)
        ),
        ConsolidationReplayCandidate(
            "professional-field", "candidate-field", "provider/model-b", ("evidence:field",)
        ),
    )
    case_claims = {
        item["case_id"]: tuple(item["expected_durable_claim_ids"])
        for item in fixture["cases"]
    }
    review_map = {
        "stable-style": (
            ConsolidationCandidateReview(
                "candidate-style",
                ConsolidationReviewVerdict.ACCEPTABLE,
                True,
                "stable-style-claim-1",
            ),
        ),
        "temporary-task": (
            ConsolidationCandidateReview(
                "candidate-temporary", ConsolidationReviewVerdict.TRANSIENT, True
            ),
        ),
        "secret-material": (
            ConsolidationCandidateReview(
                "candidate-secret", ConsolidationReviewVerdict.SENSITIVE, True
            ),
        ),
        "professional-field": (
            ConsolidationCandidateReview(
                "candidate-field",
                ConsolidationReviewVerdict.ACCEPTABLE,
                False,
                "professional-field-claim-1",
            ),
        ),
    }
    reviews = tuple(
        ConsolidationCaseReview(
            case_id,
            expected,
            review_map.get(case_id, ()),
        )
        for case_id, expected in case_claims.items()
    )
    expected_case_ids = tuple(case_claims)
    report = evaluate_consolidation_reviews(
        candidates, reviews, expected_case_ids=expected_case_ids
    )
    assert report.cases == 10 and report.proposals == 4
    assert report.acceptable == 2 and report.transient == 1 and report.sensitive == 1
    assert report.precision == 0.5
    assert report.recall == 0.5
    assert report.citation_accuracy == 0.75
    assert report.unsafe_rate == 0.25
    assert report.review_items_per_acceptable == 2.0
    assert report.actual_models == ("provider/model-a", "provider/model-b")
    qualification = qualify_consolidation_report(
        report, minimum_cases=10, minimum_expected_claims=4
    )
    assert not qualification.qualified
    assert "unsafe_candidate_present" in qualification.failures
    assert "review_burden_above_1.5" in qualification.failures

    incomplete_reviews = tuple(
        review for review in reviews if review.case_id != "stable-style"
    )
    try:
        evaluate_consolidation_reviews(
            candidates,
            incomplete_reviews,
            expected_case_ids=expected_case_ids,
        )
    except ConsolidationEvaluationError as exc:
        assert "every replay case" in str(exc)
    else:
        raise AssertionError("candidate without a case review was scored")

    try:
        evaluate_consolidation_reviews(
            candidates,
            tuple(
                ConsolidationCaseReview(
                    review.case_id,
                    review.expected_durable_claim_ids,
                    () if review.case_id == "stable-style" else review.candidate_reviews,
                )
                for review in reviews
            ),
            expected_case_ids=expected_case_ids,
        )
    except ConsolidationEvaluationError as exc:
        assert "every candidate" in str(exc)
    else:
        raise AssertionError("unreviewed candidate was scored")

    print("HERMES_ALIVE_KERNEL_CONSOLIDATION_EVALUATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
