#!/usr/bin/env python3
"""Exploration budget, diversity, silence and non-bypass contracts."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel.deliberation import (  # noqa: E402
    ActionAuthority, ActionCandidate, ActionKind, AssessmentBasis,
    DecisionDimensions, DeliberationValidationError, DimensionAssessment,
    PolicyContext, SelectionProposal, SideEffect, build_frame,
)
from alive_kernel.exploration import (  # noqa: E402
    DiversityAnnotation, DiversityTagger, ExplorationMode, ExplorationPolicy, ExposureRecord,
    apply_exploration_gate, exploration_rejection_map,
    validate_exploratory_selection,
)
from alive_kernel.content_vault import ContentVault  # noqa: E402


def score(value: float) -> DimensionAssessment:
    return DimensionAssessment(
        value, AssessmentBasis.MEASURED, ("event:test",), "test evidence"
    )


def candidate(candidate_id: str, *, risk: float = 0.1) -> ActionCandidate:
    return ActionCandidate(
        candidate_id=candidate_id,
        action_kind=ActionKind.SHARE,
        side_effect=SideEffect.COMMUNICATION,
        authority=ActionAuthority.USER_DELEGATED,
        content_id=f"content:{candidate_id}",
        dimensions=DecisionDimensions(
            score(0.8), score(0.4), score(0.8),
            score(0.9), score(0.2), score(risk),
        ),
    )


def main() -> int:
    temporary = tempfile.TemporaryDirectory(prefix="alive-exploration-tags-")
    vault = ContentVault(Path(temporary.name) / "vault")
    tagger = DiversityTagger(vault)

    def annotation(
        candidate_id: str, topic: str, source: str, mode: ExplorationMode
    ) -> DiversityAnnotation:
        return tagger.annotate(
            candidate_id, topic=topic, source=source, mode=mode
        )

    safe = candidate("safe")
    explore = candidate("explore")
    missing = candidate("missing")
    base_rejected = candidate("base-rejected", risk=0.9)
    frame = build_frame(
        (safe, explore, missing, base_rejected),
        PolicyContext(can_interrupt=True, maximum_risk=0.5),
        frame_id="frame:exploration-test",
    )
    annotations = (
        annotation("safe", "topic:c", "source:c", ExplorationMode.EXPLOIT),
        annotation("explore", "topic:d", "source:d", ExplorationMode.EXPLORE),
        annotation(
            "base-rejected", "topic:z", "source:z", ExplorationMode.EXPLORE
        ),
    )
    topic_a = annotation("old-a", "topic:a", "source:a", ExplorationMode.EXPLOIT)
    topic_b = annotation("old-b", "topic:b", "source:b", ExplorationMode.EXPLORE)
    history = (
        ExposureRecord(
            "outcome:1", "old-a", topic_a.topic_digest,
            topic_a.source_digest, ExplorationMode.EXPLOIT,
        ),
        ExposureRecord(
            "outcome:2", "old-b", topic_b.topic_digest,
            topic_b.source_digest, ExplorationMode.EXPLORE,
        ),
    )
    gate = apply_exploration_gate(
        frame,
        annotations,
        history,
        ExplorationPolicy(
            window_size=5,
            max_explorations=1,
            minimum_share_sample=3,
            maximum_topic_share=0.6,
            maximum_source_share=0.6,
            maximum_topic_streak=2,
        ),
    )
    assert set(gate.admissible_ids) == {"safe", frame.silence_id}
    reasons = exploration_rejection_map(gate)
    assert reasons["explore"] == ("exploration_budget_exhausted",)
    assert reasons["missing"] == ("diversity_metadata_missing",)
    assert "base-rejected" not in gate.admissible_ids
    assert "base-rejected" not in reasons

    selected = validate_exploratory_selection(
        frame,
        gate,
        SelectionProposal(frame.frame_id, "safe", "provider/model", "diverse and safe"),
    )
    assert selected.candidate.candidate_id == "safe"
    try:
        validate_exploratory_selection(
            frame,
            gate,
            SelectionProposal(frame.frame_id, "explore", "provider/model", "ignore budget"),
        )
    except DeliberationValidationError:
        pass
    else:
        raise AssertionError("exploration-rejected selection was accepted")

    echo_frame = build_frame(
        (safe,), PolicyContext(can_interrupt=True), frame_id="frame:echo-test"
    )
    echo_history = (
        ExposureRecord(
            "outcome:3", "old-1", annotations[0].topic_digest,
            annotations[0].source_digest, ExplorationMode.EXPLOIT,
        ),
        ExposureRecord(
            "outcome:4", "old-2", annotations[0].topic_digest,
            annotations[0].source_digest, ExplorationMode.EXPLOIT,
        ),
    )
    echo_gate = apply_exploration_gate(
        echo_frame,
        (annotation("safe", "topic:c", "source:c", ExplorationMode.EXPLOIT),),
        echo_history,
        ExplorationPolicy(
            window_size=5,
            max_explorations=2,
            minimum_share_sample=3,
            maximum_topic_share=0.6,
            maximum_source_share=0.6,
            maximum_topic_streak=2,
        ),
    )
    assert echo_gate.admissible_ids == (echo_frame.silence_id,)
    assert exploration_rejection_map(echo_gate)["safe"] == (
        "topic_share_exceeded",
        "source_share_exceeded",
        "topic_streak_exceeded",
    )
    assert "topic:c" not in annotations[0].topic_digest
    temporary.cleanup()

    print("HERMES_ALIVE_KERNEL_EXPLORATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
