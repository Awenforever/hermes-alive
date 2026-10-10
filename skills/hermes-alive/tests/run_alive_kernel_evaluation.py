#!/usr/bin/env python3
"""Factual labels, leakage boundaries and honest comparison contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import EventEnvelope, ExperienceJournal  # noqa: E402
from alive_kernel.evaluation import (  # noqa: E402
    FactualLabels, ReplayEpisode, ReplayEvaluationError, ReplayPrediction,
    StrategySubmission, compare_reports, evaluate_submission,
    labels_from_outcomes,
)
from alive_kernel.events import Sensitivity  # noqa: E402
from alive_kernel.outcomes import (  # noqa: E402
    OutcomeContentStatus, OutcomeKind, OutcomeRecord,
)


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
        attempted_at = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
        for suffix, observed_at in (
            ("a", attempted_at), ("b", attempted_at + timedelta(minutes=1))
        ):
            journal.append(EventEnvelope(
                event_id=f"action.attempt:attempt-{suffix}", event_type="action.attempted",
                source="test.fixture", actor="system:test", subject="user:test",
                observed_at=observed_at,
                payload={"candidate_id": f"candidate-{suffix}", "fixture": True},
            ))
        future = EventEnvelope(
            event_id="evidence:future", event_type="feedback.observed",
            source="test.fixture", actor="system:test", subject="user:test",
            observed_at=datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc),
            payload={"fixture": True},
        )
        journal.append(future)
        episodes = (
            ReplayEpisode(
                "attempt-a", 3, attempted_at, "candidate-a", "frame-a",
                FactualLabels(True, False, False, False, True), ("outcome-a",),
            ),
            ReplayEpisode(
                "attempt-b", 4, attempted_at + timedelta(minutes=1),
                "candidate-b", "frame-b",
                FactualLabels(False, True, True, None, False), ("outcome-b",),
            ),
        )
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
        old = evaluate_submission(journal, episodes, baseline, holdout_after_sequence=2)
        new = evaluate_submission(journal, episodes, candidate, holdout_after_sequence=2)
        comparison = compare_reports(old, new)
        assert comparison.candidate_improves_calibration
        assert not comparison.action_policy_superiority_proven
        assert new.delivery_succeeded == 1 and new.delivery_failed == 1
        assert new.user_control_violation.labelled == 1

        forged_episode = ReplayEpisode(
            "attempt-a", 3, attempted_at, "candidate-forged", "frame-a",
            FactualLabels(True), (),
        )
        try:
            evaluate_submission(
                journal, (forged_episode,),
                StrategySubmission(
                    "forged", 2,
                    (ReplayPrediction("attempt-a", attempted_at, (prior.event_id,), .9),),
                ),
                holdout_after_sequence=2,
            )
        except ReplayEvaluationError as error:
            assert "factual attempt" in str(error)
        else:
            raise AssertionError("a fabricated episode was evaluated")

        leaked = StrategySubmission(
            "leaked", 2,
            (ReplayPrediction("attempt-a", attempted_at, (future.event_id,), .9),),
        )
        try:
            evaluate_submission(journal, episodes, leaked, holdout_after_sequence=2)
        except ReplayEvaluationError as error:
            assert "future" in str(error)
        else:
            raise AssertionError("future evidence was accepted")

        trained_on_holdout = StrategySubmission("leaked-training", 3, ())
        try:
            evaluate_submission(
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
        partial_report = evaluate_submission(
            journal, episodes, partial, holdout_after_sequence=2
        )
        try:
            compare_reports(old, partial_report)
        except ReplayEvaluationError as error:
            assert "same factual" in str(error)
        else:
            raise AssertionError("different factual cohorts were compared")

    print("HERMES_ALIVE_KERNEL_EVALUATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
