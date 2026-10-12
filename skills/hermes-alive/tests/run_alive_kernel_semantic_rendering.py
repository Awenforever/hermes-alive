"""Meaning-first rendering preserves locked semantics and fails closed."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ActionAuthority,
    ActionCandidate,
    ActionKind,
    AssessmentBasis,
    DecisionDimensions,
    DeliberationProjection,
    DimensionAssessment,
    EventEnvelope,
    ExperienceJournal,
    FidelityStatus,
    MeaningDocument,
    MeaningStore,
    MessageSpeechAct,
    PolicyContext,
    RenderLayout,
    RendererClass,
    SelectionProposal,
    SemanticAtom,
    SemanticAtomKind,
    SemanticRenderingError,
    Sensitivity,
    SideEffect,
    assess_fidelity,
    deterministic_text,
)
from alive_kernel_testkit import install_exploration_gate  # noqa: E402


def main() -> int:
    now = datetime.now(timezone.utc)
    subject = "user:semantic-rendering"
    with tempfile.TemporaryDirectory(prefix="alive-semantic-rendering-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel" / "experience.sqlite3")
        deliberation = DeliberationProjection(journal)
        store = MeaningStore(journal, content_vault=deliberation.content_vault)
        evidence = EventEnvelope(
            event_id="conversation:semantic-source",
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
        atoms = (
            SemanticAtom(
                "fact",
                SemanticAtomKind.FACT,
                "研究组确认本周只发布一个候选结果。",
                (evidence.event_id,),
            ),
            SemanticAtom(
                "deadline",
                SemanticAtomKind.DEADLINE,
                "请在 2026-10-15 09:00 CST 前完成审阅。",
                (evidence.event_id,),
                ("2026-10-15 09:00 CST",),
            ),
            SemanticAtom(
                "link",
                SemanticAtomKind.LINK,
                "原文入口：https://example.org/paper?id=17",
                (evidence.event_id,),
                ("https://example.org/paper?id=17",),
            ),
            SemanticAtom(
                "negation",
                SemanticAtomKind.NEGATION,
                "这不是最终结论。",
                (evidence.event_id,),
                ("不是",),
            ),
            SemanticAtom(
                "uncertainty",
                SemanticAtomKind.UNCERTAINTY,
                "目前仍有不确定性。",
                (evidence.event_id,),
                ("不确定性",),
            ),
        )
        document = MeaningDocument(
            message_id="semantic-test",
            subject=subject,
            speech_act=MessageSpeechAct.INFORM,
            atoms=atoms,
            created_at=now,
            expires_at=now + timedelta(days=1),
            sensitivity=Sensitivity.PRIVATE,
        )
        meaning_record = store.define(
            document, actor="model:test", observed_at=now
        )
        assert store.resolve(meaning_record.event.event_id) == document

        def score(value: float, reason: str) -> DimensionAssessment:
            return DimensionAssessment(
                value, AssessmentBasis.MEASURED, (evidence.event_id,), reason
            )

        candidate = ActionCandidate(
            action_kind=ActionKind.SHARE,
            side_effect=SideEffect.COMMUNICATION,
            authority=ActionAuthority.USER_DELEGATED,
            dimensions=DecisionDimensions(
                score(0.9, "useful"),
                score(0.6, "timely"),
                score(0.8, "new"),
                score(0.9, "supported"),
                score(0.2, "brief"),
                score(0.1, "low risk"),
            ),
            content_id="candidate-content:semantic-test",
            candidate_id="candidate:semantic-test",
        )
        frame_record, frame = deliberation.append_frame(
            (candidate,),
            PolicyContext(can_interrupt=True),
            actor="system:alive",
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            frame_id="frame:semantic-test",
            candidate_contents={
                "candidate-content:semantic-test": store.candidate_reference(
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
            fixture_name="semantic-rendering",
        )
        selection_record = deliberation.append_selection(
            SelectionProposal(
                frame.frame_id,
                candidate.candidate_id,
                "provider/test",
                "meaning is selected before rendering",
            ),
            actor="model:test",
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            selection_id="selection:semantic-test",
            exploration_gate_event_id=gate_id,
        )
        assert deliberation.apply(selection_record).outcome == "validated"

        rendered = store.render_selected(
            selection_event_id=selection_record.event.event_id,
            meaning_event_id=meaning_record.event.event_id,
            subject=subject,
            layout=RenderLayout.BULLETS,
            observed_at=now + timedelta(seconds=1),
        )
        assert rendered.text == deterministic_text(document, RenderLayout.BULLETS)
        assert rendered.assessment.status is FidelityStatus.PROVEN
        assert rendered.assessment.fidelity_proven
        assert rendered.assessment.safe_for_automatic_rendering
        render_record = journal.get(rendered.event_id)
        assert render_record is not None and store.verify_render(render_record)

        model_candidate = rendered.text + "\n\n已替你完成付款。"
        model_assessment = assess_fidelity(
            document,
            model_candidate,
            renderer_class=RendererClass.MODEL_CANDIDATE,
            layout=RenderLayout.BULLETS,
        )
        assert model_assessment.status is FidelityStatus.REVIEW_REQUIRED
        assert model_assessment.unexpected_content
        assert not model_assessment.fidelity_proven
        assert not model_assessment.safe_for_automatic_rendering

        exact_model_assessment = assess_fidelity(
            document,
            rendered.text,
            renderer_class=RendererClass.MODEL_CANDIDATE,
            layout=RenderLayout.BULLETS,
        )
        assert exact_model_assessment.status is FidelityStatus.REVIEW_REQUIRED
        assert not exact_model_assessment.unexpected_content
        assert not exact_model_assessment.fidelity_proven

        missing_link = rendered.text.replace(
            "原文入口：https://example.org/paper?id=17", "原文入口稍后提供"
        )
        rejected = assess_fidelity(
            document,
            missing_link,
            renderer_class=RendererClass.MODEL_CANDIDATE,
            layout=RenderLayout.BULLETS,
        )
        assert rejected.status is FidelityStatus.REJECTED
        assert "link" in rejected.missing_atom_ids
        assert "https://example.org/paper?id=17" in rejected.missing_literals

        deterministic_extra = assess_fidelity(
            document,
            rendered.text + "\nextra",
            renderer_class=RendererClass.DETERMINISTIC,
            layout=RenderLayout.BULLETS,
        )
        assert deterministic_extra.status is FidelityStatus.REJECTED

        retry = store.render_selected(
            selection_event_id=selection_record.event.event_id,
            meaning_event_id=meaning_record.event.event_id,
            subject=subject,
            layout=RenderLayout.BULLETS,
            observed_at=now + timedelta(seconds=2),
        )
        assert retry.event_id == rendered.event_id

        try:
            store.render_selected(
                selection_event_id=selection_record.event.event_id,
                meaning_event_id=meaning_record.event.event_id,
                subject=subject,
                layout=RenderLayout.BULLETS,
                observed_at=document.expires_at,
            )
        except SemanticRenderingError:
            pass
        else:
            raise AssertionError("expired meaning must not be rendered")

        superseding_selection = deliberation.append_selection(
            SelectionProposal(
                frame.frame_id,
                candidate.candidate_id,
                "provider/test",
                "fresh validated intent invalidates an older render receipt",
            ),
            actor="model:test",
            subject=subject,
            sensitivity=Sensitivity.PRIVATE,
            selection_id="selection:semantic-test-v2",
            exploration_gate_event_id=gate_id,
        )
        assert deliberation.apply(superseding_selection).outcome == "validated"
        assert not store.verify_render(render_record)

        journal_text = journal.path.read_bytes().decode("utf-8", errors="ignore")
        for private_value in (
            "研究组确认本周只发布一个候选结果",
            "2026-10-15 09:00 CST",
            "https://example.org/paper?id=17",
            "这不是最终结论",
        ):
            assert private_value not in journal_text

        try:
            SemanticAtom(
                "unsafe-uncertainty",
                SemanticAtomKind.UNCERTAINTY,
                "也许如此。",
                (evidence.event_id,),
            )
        except SemanticRenderingError:
            pass
        else:
            raise AssertionError("uncertainty must lock its semantic marker")

    print("HERMES_ALIVE_KERNEL_SEMANTIC_RENDERING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
