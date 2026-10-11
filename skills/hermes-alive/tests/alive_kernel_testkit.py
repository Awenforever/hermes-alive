"""Shared integration fixtures for the shadow Alive kernel tests."""

from __future__ import annotations

from datetime import timedelta

from alive_kernel.autonomy_policy import AutonomyPolicyProjection
from alive_kernel.deliberation import (
    ActionKind,
    DeliberationFrame,
    PolicyContext,
    SideEffect,
)
from alive_kernel.deliberation_store import DeliberationProjection
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.events import EventEnvelope
from alive_kernel.privacy import LocalIdentityProtector
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


def install_action_authorization(
    journal: ExperienceJournal,
    *,
    selection_event_id: str,
    candidate_id: str,
    subject: str,
    executor: str,
    fixture_name: str,
) -> str:
    """Create an authentic-shaped short-lived authorization fixture."""

    selection = journal.get(selection_event_id)
    assert selection is not None
    autonomy = AutonomyPolicyProjection(journal)
    policy = autonomy.current(subject)
    if policy is None:
        policy_event = autonomy.append_update(
            subject=subject,
            actor=subject,
            expected_revision=0,
            enabled=True,
            context=PolicyContext(
                can_interrupt=True,
                allowed_side_effects=frozenset(SideEffect),
            ),
            operation_id=f"fixture:{fixture_name}",
        )
        assert autonomy.apply(policy_event).outcome == "recorded"
        policy = autonomy.current(subject)
    assert policy is not None and policy.enabled
    authorization_time = max(selection.event.observed_at, policy.updated_at)
    valid_until = authorization_time + timedelta(seconds=60)
    payload = {
        "operation_id": f"fixture:{fixture_name}",
        "selection_event_id": selection_event_id,
        "frame_id": selection.event.payload["frame_id"],
        "candidate_id": candidate_id,
        "gate_event_id": selection.event.payload["exploration_gate_event_id"],
        "agenda_item_id": None,
        "confirmation_event_id": None,
        "capability": executor,
        "outcome": "authorized",
        "reasons": [],
        "policy": {},
        "policy_event_id": policy.event_id,
        "policy_revision": policy.revision,
        "permit_ttl_seconds": 60.0,
        "valid_until": valid_until.isoformat(),
        "executes_action": False,
    }
    payload["integrity_authenticator"] = LocalIdentityProtector(
        journal.path.parent / "identity.key"
    ).authenticate_json("action.authorization.v1", payload)
    event = EventEnvelope(
        event_id=f"action.authorization:fixture:{fixture_name}",
        event_type="action.authorization_evaluated",
        source="alive.authorization",
        actor="system:alive-authorizer",
        subject=subject,
        causation_id=selection_event_id,
        occurred_at=authorization_time,
        observed_at=authorization_time,
        expires_at=valid_until,
        sensitivity=selection.event.sensitivity,
        payload=payload,
    )
    return journal.append(event).event.event_id
