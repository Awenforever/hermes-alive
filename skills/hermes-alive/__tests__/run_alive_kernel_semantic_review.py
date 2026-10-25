#!/usr/bin/env python3
"""Independent review and multilingual semantic-evaluation contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from alive_kernel.semantic_rendering import (  # noqa: E402
    FidelityStatus,
    MeaningDocument,
    MessageSpeechAct,
    RendererClass,
    SemanticAtom,
    SemanticAtomKind,
    assess_fidelity,
)
from alive_kernel.semantic_review import (  # noqa: E402
    AtomReview,
    IndependentSemanticReview,
    ReviewDisposition,
    ReviewerKind,
    SemanticCaseJudgment,
    SemanticReplayPrediction,
    SemanticReviewError,
    SemanticRisk,
    assess_independent_review,
    candidate_digest,
    evaluate_semantic_reviews,
    qualify_semantic_review_report,
)


def _review(
    document: MeaningDocument,
    text: str,
    *,
    atom_reviews: tuple[AtomReview, ...] | None = None,
    renderer_model: str = "provider/model-renderer",
    reviewer_model: str | None = "other/model-reviewer",
    renderer_domain: str = "provider-a/model-family-a",
    reviewer_domain: str = "provider-b/model-family-b",
) -> IndependentSemanticReview:
    return IndependentSemanticReview(
        review_id="review:semantic-1",
        meaning_event_id="message.meaning:semantic-review",
        candidate_digest=candidate_digest(text),
        renderer_execution_id="execution:renderer-1",
        renderer_model=renderer_model,
        renderer_independence_domain=renderer_domain,
        reviewer_kind=ReviewerKind.MODEL,
        reviewer_execution_id="execution:reviewer-1",
        reviewer_model=reviewer_model,
        reviewer_independence_domain=reviewer_domain,
        atom_reviews=atom_reviews
        or tuple(AtomReview(atom.atom_id, True) for atom in document.atoms),
        added_claims_detected=False,
        speech_act_preserved=True,
        protected_literals_preserved=True,
    )


def main() -> int:
    now = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)
    document = MeaningDocument(
        message_id="semantic-review",
        subject="user:semantic-review",
        speech_act=MessageSpeechAct.REMIND,
        atoms=(
            SemanticAtom(
                "deadline",
                SemanticAtomKind.DEADLINE,
                "报名截止时间是 2026-11-03 09:00。",
                ("evidence:mail",),
                ("2026-11-03 09:00",),
            ),
            SemanticAtom(
                "status",
                SemanticAtomKind.NEGATION,
                "尚未完成报名。",
                ("evidence:mail",),
                ("尚未",),
            ),
        ),
        created_at=now,
        expires_at=now + timedelta(days=3),
    )
    paraphrase = "你尚未报名；请留意截止时间 2026-11-03 09:00。"
    baseline = assess_fidelity(
        document,
        paraphrase,
        renderer_class=RendererClass.MODEL_CANDIDATE,
    )
    assert baseline.status is FidelityStatus.REVIEW_REQUIRED
    assert baseline.missing_atom_ids == ("deadline", "status")
    assert baseline.missing_literals == ()

    good = assess_independent_review(document, paraphrase, _review(document, paraphrase))
    assert good.disposition is ReviewDisposition.SHADOW_ELIGIBLE
    assert good.eligible_for_shadow_comparison
    assert not good.safe_for_automatic_delivery

    self_review = _review(
        document,
        paraphrase,
        renderer_model="provider/model-renderer",
        reviewer_model="provider/model-renderer",
        renderer_domain="provider/model-family",
        reviewer_domain="provider/model-family",
    )
    invalid = assess_independent_review(document, paraphrase, self_review)
    assert invalid.disposition is ReviewDisposition.INVALID
    assert "reviewer_not_independent" in invalid.reasons

    wrong_text = assess_independent_review(
        document, paraphrase + " extra", _review(document, paraphrase)
    )
    assert wrong_text.disposition is ReviewDisposition.INVALID
    assert "candidate_digest_mismatch" in wrong_text.reasons

    wrong_meaning = IndependentSemanticReview(
        review_id="review:semantic-2",
        meaning_event_id="message.meaning:other",
        candidate_digest=candidate_digest(paraphrase),
        renderer_execution_id="execution:renderer-2",
        renderer_model="provider/model-renderer",
        renderer_independence_domain="provider-a/model-family-a",
        reviewer_kind=ReviewerKind.HUMAN,
        reviewer_execution_id="execution:reviewer-2",
        reviewer_model=None,
        reviewer_independence_domain="human/reviewer-1",
        atom_reviews=tuple(AtomReview(atom.atom_id, True) for atom in document.atoms),
        added_claims_detected=False,
        speech_act_preserved=True,
        protected_literals_preserved=True,
    )
    wrong_meaning_result = assess_independent_review(document, paraphrase, wrong_meaning)
    assert wrong_meaning_result.disposition is ReviewDisposition.INVALID
    assert "meaning_event_mismatch" in wrong_meaning_result.reasons

    missing_literal_text = paraphrase.replace("尚未", "已经")
    missing_literal_review = _review(document, missing_literal_text)
    missing_literal_result = assess_independent_review(
        document, missing_literal_text, missing_literal_review
    )
    assert missing_literal_result.disposition is ReviewDisposition.REJECTED
    assert "protected_literal_missing_from_candidate" in missing_literal_result.reasons

    risky_review = _review(
        document,
        paraphrase,
        atom_reviews=(
            AtomReview("deadline", True),
            AtomReview("status", False, (SemanticRisk.POLARITY_SHIFT,)),
        ),
    )
    rejected = assess_independent_review(document, paraphrase, risky_review)
    assert rejected.disposition is ReviewDisposition.REJECTED
    assert rejected.risks == (SemanticRisk.POLARITY_SHIFT,)

    fixture = json.loads(
        (ROOT / "__tests__" / "fixtures" / "semantic_fidelity_seed_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert fixture["schema_version"] == 1
    assert fixture["provenance"] == "synthetic_adversarial_seed"
    assert fixture["privacy_reviewed"] is True
    assert fixture["qualification_evidence"] is False
    assert len(fixture["cases"]) == 12
    serialized = json.dumps(fixture, ensure_ascii=False)
    assert "sk-" not in serialized.lower() and "@" not in serialized

    judgments = tuple(
        SemanticCaseJudgment(
            item["case_id"],
            item["language_tag"],
            tuple(SemanticRisk(value) for value in item["expected_risks"]),
        )
        for item in fixture["cases"]
    )
    predictions = tuple(
        SemanticReplayPrediction(
            case_id=item.case_id,
            candidate_id=f"candidate:{item.case_id}",
            language_tag=item.language_tag,
            renderer_model="provider-a/renderer",
            reviewer_model="provider-b/reviewer",
            renderer_independence_domain="provider-a/family-a",
            reviewer_independence_domain="provider-b/family-b",
            accepted_as_preserved=item.faithful,
            predicted_risks=item.expected_risks,
        )
        for item in judgments
    )
    report = evaluate_semantic_reviews(
        predictions,
        judgments,
        expected_case_ids=tuple(item.case_id for item in judgments),
    )
    assert report.cases == 12
    assert report.languages == ("en", "ja", "zh")
    assert report.faithful_cases == 3 and report.risky_cases == 9
    assert report.unsafe_acceptance_rate == 0
    assert report.faithful_acceptance_rate == 1
    assert report.issue_precision == 1
    assert report.macro_risk_recall == 1
    assert report.independence_violations == 0
    # The seed proves evaluation mechanics, not production qualification.
    qualification = qualify_semantic_review_report(report)
    assert not qualification.qualified
    assert qualification.failures == ("insufficient_cases",)

    flawed = list(predictions)
    target = next(
        index
        for index, item in enumerate(flawed)
        if item.case_id == "en-polarity-shift"
    )
    flawed[target] = SemanticReplayPrediction(
        case_id="en-polarity-shift",
        candidate_id="candidate:en-polarity-shift",
        language_tag="en",
        renderer_model="provider-a/renderer",
        reviewer_model="provider-a/renderer",
        renderer_independence_domain="provider-a/family-a",
        reviewer_independence_domain="provider-a/family-a",
        accepted_as_preserved=True,
        predicted_risks=(),
    )
    flawed_report = evaluate_semantic_reviews(
        flawed,
        judgments,
        expected_case_ids=tuple(item.case_id for item in judgments),
    )
    assert flawed_report.unsafe_acceptances == 1
    assert flawed_report.independence_violations == 1
    flawed_gate = qualify_semantic_review_report(
        flawed_report, minimum_cases=12, minimum_languages=3
    )
    assert not flawed_gate.qualified
    assert "reviewer_independence_violation" in flawed_gate.failures
    assert "unsafe_candidate_accepted" in flawed_gate.failures

    try:
        evaluate_semantic_reviews(
            predictions[:-1],
            judgments,
            expected_case_ids=tuple(item.case_id for item in judgments),
        )
    except SemanticReviewError as exc:
        assert "complete expected cohort" in str(exc)
    else:
        raise AssertionError("incomplete semantic cohort was scored")

    print("HERMES_ALIVE_KERNEL_SEMANTIC_REVIEW_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
