#!/usr/bin/env python3
"""Encrypted model candidates and review receipts fail closed when stale."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from alive_kernel import (  # noqa: E402
    ActionAuthority,
    ActionCandidate,
    ActionKind,
    AssessmentBasis,
    AtomReview,
    DecisionDimensions,
    DeliberationProjection,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    IndependentSemanticReview,
    MeaningDocument,
    MeaningStore,
    MessageSpeechAct,
    PolicyContext,
    ReviewerKind,
    SelectionProposal,
    SemanticAtom,
    SemanticAtomKind,
    SemanticReviewError,
    SemanticReviewStore,
    Sensitivity,
    SideEffect,
    candidate_digest,
)
from alive_kernel_testkit import install_exploration_gate  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    subject = "user:semantic-review-store"
    with tempfile.TemporaryDirectory(prefix="alive-semantic-review-store-") as tmp:
        journal = ExperienceJournal(Path(tmp) / "kernel" / "experience.sqlite3")
        deliberation = DeliberationProjection(journal)
        meanings = MeaningStore(journal, content_vault=deliberation.content_vault)
        store = SemanticReviewStore(
            journal, content_vault=deliberation.content_vault
        )
        evidence = EventEnvelope(
            event_id="conversation:review-store-source",
            event_type="conversation.inbound",
            source="test.channel",
            actor=subject,
            subject=subject,
            observed_at=now,
            occurred_at=now,
            sensitivity=Sensitivity.PRIVATE,
            payload={"raw_content_stored": False},
        )
        journal.append(evidence)
        document = MeaningDocument(
            message_id="semantic-review-store",
            subject=subject,
            speech_act=MessageSpeechAct.REMIND,
            atoms=(
                SemanticAtom(
                    "deadline",
                    SemanticAtomKind.DEADLINE,
                    "请在 2026-10-15 09:00 CST 前确认。",
                    (evidence.event_id,),
                    ("2026-10-15 09:00 CST",),
                ),
                SemanticAtom(
                    "status",
                    SemanticAtomKind.NEGATION,
                    "目前尚未确认。",
                    (evidence.event_id,),
                    ("尚未",),
                ),
            ),
            created_at=now,
            expires_at=now + timedelta(days=1),
        )
        meaning_record = meanings.define(document, actor="model:test", observed_at=now)

        def score(value: float, reason: str) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (evidence.event_id,), reason
            )

        candidate = ActionCandidate(
            action_kind=ActionKind.REMIND,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=DecisionDimensions(
                score(0.9, "useful"),
                score(0.8, "timely"),
                score(0.4, "not novel"),
                score(0.9, "supported"),
                score(0.2, "brief"),
                score(0.1, "low risk"),
            ),
            content_id="candidate-content:review-store",
            candidate_id="candidate:review-store",
        )
        frame_record, frame = deliberation.append_frame(
            (candidate,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            frame_id="frame:semantic-review-store",
            candidate_contents={
                candidate.content_id: meanings.candidate_reference(
                    meaning_record.event.event_id
                )
            },
        )
        assert deliberation.apply(frame_record).outcome == "recorded"
        gate_id = install_exploration_gate(
            journal,
            deliberation,
            frame,
            subject=subject,
            fixture_name="semantic-review-store",
        )

        def select(selection_id: str, rationale: str):
            record = deliberation.append_selection(
                SelectionProposal(
                    frame.frame_id,
                    candidate.candidate_id,
                    "provider/selector",
                    rationale,
                ),
                actor="model:selector",
                subject=subject,
                sensitivity=Sensitivity.PRIVATE,
                selection_id=selection_id,
                exploration_gate_event_id=gate_id,
            )
            assert deliberation.apply(record).outcome == "validated"
            return record

        selection = select("selection:review-store-1", "first validated intent")
        text = "你尚未确认，请在 2026-10-15 09:00 CST 前处理。"
        model_candidate = store.record_model_candidate(
            selection_event_id=selection.event.event_id,
            meaning_event_id=meaning_record.event.event_id,
            subject=subject,
            text=text,
            renderer_execution_id="execution:renderer-1",
            renderer_model="provider-a/renderer",
            renderer_independence_domain="provider-a/family-a",
            observed_at=now + timedelta(seconds=1),
        )
        model_event = journal.get(model_candidate.event_id)
        assert model_event is not None
        assert text not in repr(model_event.event.payload)

        def review_for(
            value,
            review_id: str,
            execution_id: str,
        ) -> IndependentSemanticReview:
            return IndependentSemanticReview(
                review_id=review_id,
                meaning_event_id=value.meaning_event_id,
                candidate_digest=candidate_digest(value.text),
                renderer_execution_id=value.renderer_execution_id,
                renderer_model=value.renderer_model,
                renderer_independence_domain=value.renderer_independence_domain,
                reviewer_kind=ReviewerKind.MODEL,
                reviewer_execution_id=execution_id,
                reviewer_model="provider-b/reviewer",
                reviewer_independence_domain="provider-b/family-b",
                atom_reviews=tuple(
                    AtomReview(atom.atom_id, True) for atom in document.atoms
                ),
                added_claims_detected=False,
                speech_act_preserved=True,
                protected_literals_preserved=True,
            )

        receipt = store.record_review(
            candidate_event_id=model_candidate.event_id,
            review=review_for(
                model_candidate, "review:review-store-1", "execution:reviewer-1"
            ),
            actor="model:reviewer",
            observed_at=now + timedelta(seconds=2),
        )
        assert receipt.assessment.eligible_for_shadow_comparison
        assert not receipt.assessment.safe_for_automatic_delivery
        review_record = journal.get(receipt.event_id)
        assert review_record is not None
        assert store.verify_review(
            review_record, as_of=now + timedelta(seconds=2)
        ) == receipt

        mismatched = replace(
            review_for(
                model_candidate, "review:review-store-bad", "execution:reviewer-bad"
            ),
            renderer_model="provider-x/other",
        )
        try:
            store.record_review(
                candidate_event_id=model_candidate.event_id,
                review=mismatched,
                actor="model:reviewer",
                observed_at=now + timedelta(seconds=3),
            )
        except SemanticReviewError as exc:
            assert "stored renderer evidence" in str(exc)
        else:
            raise AssertionError("review of different renderer evidence was accepted")

        assert (
            store.resolve_model_candidate(
                model_candidate.event_id, as_of=document.expires_at
            )
            is None
        )
        assert store.verify_review(review_record, as_of=document.expires_at) is None

        superseding = select(
            "selection:review-store-2", "new intent invalidates prior receipts"
        )
        assert store.resolve_model_candidate(
            model_candidate.event_id, as_of=now + timedelta(seconds=3)
        ) is None
        assert store.verify_review(
            review_record, as_of=now + timedelta(seconds=3)
        ) is None

        fresh_candidate = store.record_model_candidate(
            selection_event_id=superseding.event.event_id,
            meaning_event_id=meaning_record.event.event_id,
            subject=subject,
            text=text,
            renderer_execution_id="execution:renderer-2",
            renderer_model="provider-a/renderer",
            renderer_independence_domain="provider-a/family-a",
            observed_at=now + timedelta(seconds=4),
        )
        fresh_receipt = store.record_review(
            candidate_event_id=fresh_candidate.event_id,
            review=review_for(
                fresh_candidate, "review:review-store-2", "execution:reviewer-2"
            ),
            actor="model:reviewer",
            observed_at=now + timedelta(seconds=5),
        )
        fresh_review_record = journal.get(fresh_receipt.event_id)
        assert fresh_review_record is not None
        fresh_event = journal.get(fresh_candidate.event_id)
        assert fresh_event is not None
        content_id = str(fresh_event.event.payload["content"]["content_id"])
        deliberation.content_vault.erase_item(content_id)
        assert store.resolve_model_candidate(
            fresh_candidate.event_id, as_of=now + timedelta(seconds=6)
        ) is None
        assert store.verify_review(
            fresh_review_record, as_of=now + timedelta(seconds=6)
        ) is None

        journal_text = journal.path.read_bytes().decode("utf-8", errors="ignore")
        assert text not in journal_text
        print("HERMES_ALIVE_KERNEL_SEMANTIC_REVIEW_STORE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
