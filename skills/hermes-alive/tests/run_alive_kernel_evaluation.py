#!/usr/bin/env python3
"""Factual labels, leakage boundaries and honest comparison contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import EventEnvelope, ExperienceJournal  # noqa: E402
from alive_kernel.evaluation import (  # noqa: E402
    FactualLabels, ReplayEpisode, ReplayEvaluationError, ReplayPrediction,
    StrategySubmission, compare_reports, evaluate_submission,
    labels_from_outcomes, build_factual_episodes,
)
from alive_kernel.events import Sensitivity  # noqa: E402
from alive_kernel.outcomes import (  # noqa: E402
    OutcomeContentStatus, OutcomeKind, OutcomeRecord, OutcomeProjection,
)
from alive_kernel.deliberation import (
    ActionAuthority, ActionCandidate, ActionKind, AssessmentBasis,
    DecisionDimensions, DimensionAssessment, PolicyContext, SelectionProposal, SideEffect,
)
from alive_kernel.deliberation_store import DeliberationProjection
from alive_kernel_testkit import (
    install_action_authorization, install_exploration_gate, authenticated_dispatch_receipt,
)


def admitted_attempt(journal, projection, suffix):
    deliberation = DeliberationProjection(journal)
    def dimension(value):
        return DimensionAssessment(value, AssessmentBasis.MEASURED, ("evidence:prior",), "fixture")
    candidate = ActionCandidate(
        candidate_id=f"candidate-{suffix}", action_kind=ActionKind.SHARE,
        side_effect=SideEffect.COMMUNICATION, authority=ActionAuthority.USER_DELEGATED,
        content_id=f"content-{suffix}", dimensions=DecisionDimensions(
            dimension(.8), dimension(.4), dimension(.9), dimension(.9), dimension(.2), dimension(.1),
        ),
    )
    record, frame = deliberation.append_frame(
        (candidate,), PolicyContext(can_interrupt=True), actor="system:alive", subject="user:test",
        frame_id=f"frame-{suffix}", candidate_contents={candidate.content_id: {
            "schema_version": 1, "capability": "hermes.channel.send",
            "operation": {"text": "Synthetic evaluation fixture", "format": "markdown"},
        }},
    )
    deliberation.apply(record)
    gate = install_exploration_gate(journal, deliberation, frame, subject="user:test", fixture_name=suffix)
    selection = deliberation.append_selection(
        SelectionProposal(frame.frame_id, candidate.candidate_id, "test/model", "fixture"),
        actor="model:test", subject="user:test", selection_id=f"selection-{suffix}",
        exploration_gate_event_id=gate,
    )
    assert deliberation.apply(selection).outcome == "validated"
    authorization = install_action_authorization(
        journal, selection_event_id=selection.event.event_id, candidate_id=candidate.candidate_id,
        subject="user:test", executor="hermes.channel.send", fixture_name=suffix,
    )
    attempt = projection.append_attempt(
        authorization_event_id=authorization, selection_event_id=selection.event.event_id,
        candidate_id=candidate.candidate_id, executor="hermes.channel.send",
        idempotency_key=f"fixture:{suffix}", actor="system:executor", subject="user:test",
        attempt_id=f"attempt-{suffix}",
    )
    assert projection.apply(attempt).outcome == "recorded"
    return attempt


def outcome(kind: OutcomeKind, details: object, number: int) -> OutcomeRecord:
    now = datetime(2026, 10, 10, 8, number, tzinfo=timezone.utc)
    return OutcomeRecord(
        f"outcome-{number}", "attempt-test", kind, "user:test", f"source-{number}",
        details, f"content-{number}", OutcomeContentStatus.AVAILABLE,
        Sensitivity.PRIVATE, now,
    )


def main() -> int:
    unknown = labels_from_outcomes(())
    assert unknown.useful is None
    assert unknown.interruption_regret is None
    assert unknown.delivery_succeeded is None
    assert unknown.task_completed is None
    for invalid in (1, 0, "true", "false"):
        try:
            FactualLabels(useful=invalid)
        except ReplayEvaluationError:
            pass
        else:
            raise AssertionError("coercible non-boolean factual label accepted")
    for kind, completed in (
        (OutcomeKind.TASK_COMPLETED, True), (OutcomeKind.TASK_FAILED, False),
    ):
        task = labels_from_outcomes((outcome(kind, {}, 1),))
        assert task.task_completed is completed
        assert task.useful is None
        assert task.delivery_succeeded is None
    success_but_unhelpful = labels_from_outcomes((
        outcome(OutcomeKind.TASK_COMPLETED, {}, 1),
        outcome(OutcomeKind.EXPLICIT_FEEDBACK, {"sentiment": "unhelpful"}, 2),
    ))
    assert success_but_unhelpful.task_completed is True
    assert success_but_unhelpful.useful is False
    failed_but_helpful = labels_from_outcomes((
        outcome(OutcomeKind.TASK_FAILED, {}, 1),
        outcome(OutcomeKind.EXPLICIT_FEEDBACK, {"sentiment": "helpful"}, 2),
    ))
    assert failed_but_helpful.task_completed is False
    assert failed_but_helpful.useful is True
    conflicting_tasks = labels_from_outcomes((
        outcome(OutcomeKind.TASK_COMPLETED, {}, 1),
        outcome(OutcomeKind.TASK_FAILED, {}, 2),
    ))
    assert conflicting_tasks.task_completed is None
    assert conflicting_tasks.useful is None

    labelled = labels_from_outcomes(
        (
            outcome(OutcomeKind.DELIVERY_SUCCEEDED, {}, 1),
            outcome(OutcomeKind.EXPLICIT_FEEDBACK, {"sentiment": "helpful"}, 2),
            outcome(OutcomeKind.USER_REPLIED, {"text": "thanks"}, 3),
            outcome(OutcomeKind.USER_CORRECTED, {"factual_error": True}, 4),
        )
    )
    assert labelled.delivery_succeeded is True
    assert labelled.useful is True
    assert labelled.factual_error is True
    assert labelled.interruption_regret is None

    with tempfile.TemporaryDirectory(prefix="alive-kernel-evaluation-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        prior = EventEnvelope(
            event_id="evidence:prior", event_type="context.observed",
            source="test.fixture", actor="system:test", subject="user:test",
            observed_at=datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc),
            payload={"fixture": True},
        )
        journal.append(prior)
        boundary = EventEnvelope(
            event_id="training:boundary", event_type="training.closed",
            source="test.fixture", actor="system:test", subject="user:test",
            observed_at=datetime(2026, 10, 10, 7, 30, tzinfo=timezone.utc),
            payload={"fixture": True},
        )
        journal.append(boundary)
        for event_id, subject, sensitivity, expiry in (
            ("evidence:foreign", "user:other", Sensitivity.PRIVATE, None),
            ("evidence:foreign-public", "user:other", Sensitivity.PUBLIC, None),
            ("evidence:restricted", "user:test", Sensitivity.RESTRICTED, None),
            ("evidence:global", None, Sensitivity.PUBLIC, None),
            ("evidence:unscoped-private", None, Sensitivity.PRIVATE, None),
            ("evidence:expired", "user:test", Sensitivity.PRIVATE,
             datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)),
        ):
            journal.append(EventEnvelope(
                event_id=event_id, event_type="context.observed", source="test.fixture",
                actor="system:test", subject=subject, sensitivity=sensitivity,
                observed_at=prior.observed_at, expires_at=expiry, payload={"fixture": True},
            ))
        projection = OutcomeProjection(journal)
        attempts = [admitted_attempt(journal, projection, suffix) for suffix in ("a", "b")]
        attempted_at = attempts[0].event.observed_at
        before_feedback = journal.last_sequence()
        for suffix, attempt, helpful in zip(("a", "b"), attempts, (True, False)):
            receipt = authenticated_dispatch_receipt(
                journal, attempt, event_id=f"receipt:{suffix}",
                event_type="delivery.succeeded" if helpful else "delivery.failed",
            )
            delivery_record = projection.append_outcome(
                attempt_id=f"attempt-{suffix}",
                kind=OutcomeKind.DELIVERY_SUCCEEDED if helpful else OutcomeKind.DELIVERY_FAILED,
                source_event_id=receipt.event_id, details={}, actor=receipt.actor,
                subject="user:test", outcome_id=f"delivery-{suffix}",
            )
            assert projection.apply(delivery_record).outcome == "recorded"
            source = EventEnvelope(
                event_id=f"feedback:{suffix}", event_type="conversation.inbound",
                source="test.channel", actor="user:test", subject="user:test",
                causation_id=attempt.event.event_id,
                payload={"user_outcome_kind": OutcomeKind.EXPLICIT_FEEDBACK.value},
            )
            journal.append(source)
            feedback_record = projection.append_outcome(
                attempt_id=f"attempt-{suffix}", kind=OutcomeKind.EXPLICIT_FEEDBACK,
                source_event_id=source.event_id, actor="user:test", subject="user:test",
                outcome_id=f"feedback-{suffix}", details={
                    "sentiment": "helpful" if helpful else "unhelpful",
                    "interruption_regret": not helpful, "factual_error": not helpful,
                    **({"user_control_violation": False} if helpful else {}),
                },
            )
            assert projection.apply(feedback_record).outcome == "recorded"
        def evaluate(journal, episodes, submission, **kwargs):
            return evaluate_submission(journal, episodes, submission, outcomes=projection,
                                       clearance=Sensitivity.PRIVATE, **kwargs)
        future = EventEnvelope(
            event_id="evidence:future", event_type="feedback.observed",
            source="test.fixture", actor="system:test", subject="user:test",
            observed_at=attempted_at + timedelta(hours=1),
            payload={"fixture": True},
        )
        journal.append(future)
        episodes = build_factual_episodes(journal, projection, clearance=Sensitivity.PRIVATE)
        baseline = StrategySubmission(
            "baseline", 2,
            (
                ReplayPrediction("attempt-a", attempted_at, (prior.event_id,), .5, .5, .5, .5),
                ReplayPrediction("attempt-b", attempted_at, (prior.event_id,), .5, .5, .5, .5),
            ),
        )
        candidate = StrategySubmission(
            "candidate", 2,
            (
                ReplayPrediction("attempt-a", attempted_at, (prior.event_id,), .9, .1, .1, .2),
                ReplayPrediction("attempt-b", attempted_at, (prior.event_id,), .1, .9, .9, .2),
            ),
        )
        old = evaluate(journal, episodes, baseline, holdout_after_sequence=2)
        new = evaluate(journal, episodes, candidate, holdout_after_sequence=2)
        comparison = compare_reports(old, new)
        assert comparison.candidate_improves_calibration
        assert not comparison.action_policy_superiority_proven
        assert new.delivery_succeeded == 1 and new.delivery_failed == 1
        assert new.task_completed == 0 and new.task_failed == 0
        assert new.task_unknown == 2
        assert new.user_control_violation.labelled == 1
        for evidence_id, reason in (
            ("evidence:foreign", "privacy scope"),
            ("evidence:foreign-public", "privacy scope"),
            ("evidence:restricted", "privacy clearance"),
            ("evidence:unscoped-private", "privacy scope"),
            ("evidence:expired", "expired"),
        ):
            submission = StrategySubmission("private-evidence", 2, (
                ReplayPrediction("attempt-a", attempted_at, (evidence_id,), .9),
            ))
            try:
                evaluate(journal, episodes, submission, holdout_after_sequence=2)
            except ReplayEvaluationError as error:
                assert reason in str(error)
            else:
                raise AssertionError(f"inadmissible evidence accepted: {evidence_id}")
        public_submission = StrategySubmission("public-evidence", 2, (
            ReplayPrediction("attempt-a", attempted_at, ("evidence:global",), .9),
        ))
        public_report = evaluate(journal, episodes, public_submission, holdout_after_sequence=2)
        assert public_report.useful.labelled == 1
        for altered in (
            replace(episodes[0], labels=replace(episodes[0].labels, useful=False)),
            replace(episodes[0], frame_id="frame-forged"),
            replace(episodes[0], outcome_event_ids=()),
            replace(episodes[0], outcome_event_ids=episodes[1].outcome_event_ids),
            replace(episodes[0], outcome_event_ids=("outcome.record:missing",)),
            replace(episodes[0], outcome_event_ids=episodes[0].outcome_event_ids * 2),
        ):
            try:
                evaluate(journal, (altered, episodes[1]), candidate, holdout_after_sequence=2)
            except ReplayEvaluationError as error:
                assert "factual snapshot" in str(error)
            else:
                raise AssertionError("fabricated labels/evidence were scored")
        try:
            evaluate(journal, (episodes[0], episodes[0]), baseline, holdout_after_sequence=2)
        except ReplayEvaluationError as error:
            assert "duplicate" in str(error)
        else:
            raise AssertionError("duplicate episodes were scored")
        historical = build_factual_episodes(journal, projection, clearance=Sensitivity.PRIVATE,
                                           observed_through_sequence=before_feedback)
        operational_report = evaluate(journal, historical, candidate, holdout_after_sequence=2,
                                      observed_through_sequence=before_feedback)
        assert operational_report.useful.labelled == 0
        assert operational_report.useful.brier is None
        assert operational_report.task_completed == 0
        assert operational_report.task_failed == 0
        assert operational_report.delivery_unknown == 2
        try:
            evaluate(journal, historical, candidate, holdout_after_sequence=2)
        except ReplayEvaluationError as error:
            assert "factual snapshot" in str(error)
        else:
            raise AssertionError("silently omitted later feedback was accepted")

        forged_episode = ReplayEpisode(
            "attempt-a", 3, attempted_at, "candidate-forged", "frame-a",
            FactualLabels(True), (),
        )
        try:
            evaluate(
                journal, (forged_episode,),
                StrategySubmission(
                    "forged", 2,
                    (ReplayPrediction("attempt-a", attempted_at, (prior.event_id,), .9),),
                ),
                holdout_after_sequence=2,
            )
        except ReplayEvaluationError as error:
            assert "factual snapshot" in str(error)
        else:
            raise AssertionError("a fabricated episode was evaluated")

        leaked = StrategySubmission(
            "leaked", 2,
            (ReplayPrediction("attempt-a", attempted_at, (future.event_id,), .9),),
        )
        try:
            evaluate(journal, episodes, leaked, holdout_after_sequence=2)
        except ReplayEvaluationError as error:
            assert "future" in str(error)
        else:
            raise AssertionError("future evidence was accepted")

        trained_on_holdout = StrategySubmission("leaked-training", 3, ())
        try:
            evaluate(
                journal, episodes, trained_on_holdout, holdout_after_sequence=2
            )
        except ReplayEvaluationError as error:
            assert "training" in str(error)
        else:
            raise AssertionError("holdout leakage was accepted")

        partial = StrategySubmission(
            "partial", 2,
            (ReplayPrediction("attempt-a", attempted_at, (prior.event_id,), .9),),
        )
        partial_report = evaluate(
            journal, episodes, partial, holdout_after_sequence=2
        )
        try:
            compare_reports(old, partial_report)
        except ReplayEvaluationError as error:
            assert "same factual" in str(error)
        else:
            raise AssertionError("different factual cohorts were compared")
        feedback = next(item for item in projection.outcomes("attempt-a", clearance=Sensitivity.PRIVATE)
                        if item.kind is OutcomeKind.EXPLICIT_FEEDBACK)
        projection.content_vault.erase_item(feedback.content_id)
        try:
            evaluate(journal, episodes, candidate, holdout_after_sequence=2)
        except ReplayEvaluationError as error:
            assert "factual snapshot" in str(error)
        else:
            raise AssertionError("erased feedback survived as an old cached episode label")
        erased = build_factual_episodes(journal, projection, clearance=Sensitivity.PRIVATE)
        erased_report = evaluate(journal, erased, candidate, holdout_after_sequence=2)
        assert erased_report.useful.labelled == 1
        assert erased_report.delivery_succeeded == 1
        try:
            compare_reports(old, erased_report)
        except ReplayEvaluationError as error:
            assert "label snapshot" in str(error)
        else:
            raise AssertionError("reports over different factual labels were compared")

    print("HERMES_ALIVE_KERNEL_EVALUATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
