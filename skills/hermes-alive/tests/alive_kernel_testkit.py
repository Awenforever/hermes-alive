"""Shared integration fixtures for the shadow Alive kernel tests."""

from __future__ import annotations

from alive_kernel.deliberation import ActionKind, DeliberationFrame
from alive_kernel.deliberation_store import DeliberationProjection
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.exploration import ExplorationMode, ExplorationPolicy
from alive_kernel.exploration_store import ExplorationProjection


def install_exploration_gate(
    journal: ExperienceJournal,
    deliberation: DeliberationProjection,
    frame: DeliberationFrame,
    *,
    subject: str,
    fixture_name: str,
) -> str:
    """Create a permissive but real gate receipt for integration fixtures."""

    exploration = ExplorationProjection(journal)
    for index, candidate in enumerate(frame.candidates):
        if (
            candidate.action_kind is ActionKind.SILENCE
            or candidate.candidate_id not in frame.admissible_ids
        ):
            continue
        annotation_event, _annotation = exploration.append_annotation(
            frame_id=frame.frame_id,
            candidate_id=candidate.candidate_id,
            topic=f"fixture-topic-{fixture_name}-{index}",
            source_label=f"fixture-source-{fixture_name}-{index}",
            mode=ExplorationMode.EXPLOIT,
            actor="system:test",
            subject=subject,
            annotation_id=f"fixture:{fixture_name}:{index}",
        )
        assert exploration.apply(annotation_event).outcome == "recorded"
    evaluation_event, _result = exploration.append_evaluation(
        frame.frame_id,
        ExplorationPolicy(
            window_size=100,
            max_explorations=20,
            minimum_share_sample=100,
            maximum_topic_share=1.0,
            maximum_source_share=1.0,
            maximum_topic_streak=99,
        ),
        actor="system:test",
        subject=subject,
        evaluation_id=f"fixture:{fixture_name}",
    )
    assert exploration.apply(evaluation_event).outcome == "recorded"
    return evaluation_event.event.event_id
