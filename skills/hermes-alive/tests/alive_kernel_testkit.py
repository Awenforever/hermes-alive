"""Shared integration fixtures for the shadow Alive kernel tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import closing

from alive_kernel.action_contract import parse_action_contract
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
from alive_kernel.host_capabilities import HostCapabilityProjection, ReceiptLevel


def inject_legacy_outcome_row(projection, record):
    """Emulate an older materialized row without calling current admission."""
    event = record.event
    payload = event.payload
    with closing(projection._connect()) as connection:
        connection.execute("INSERT INTO action_outcomes_v1 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            payload["outcome_id"], event.event_id, payload["attempt_id"], payload["kind"],
            event.subject, payload["source_event_id"], payload["content"]["content_id"],
            event.sensitivity.value, event.observed_at.isoformat(),
        ))


def authenticated_dispatch_receipt(journal, attempt, *, event_id, event_type="delivery.succeeded"):
    """Synthetic host receipt over a real validated authorization/attempt fixture."""
    from alive_kernel.dispatch_outbox import DispatchOutbox
    protector = LocalIdentityProtector(journal.path.parent / "identity.key")
    authorization = journal.get(attempt.event.payload["authorization_event_id"])
    dispatch_id = f"fixture:{event_id}"
    start_time = max(datetime.now(timezone.utc), attempt.event.observed_at)
    payload = {
        "dispatch_id": dispatch_id, "attempt_id": attempt.event.payload["attempt_id"],
        "idempotency_key": attempt.event.payload["idempotency_key"],
        "capability": attempt.event.payload["executor"],
        "policy_event_id": authorization.event.payload.get("policy_event_id"),
        "route_binding_id": authorization.event.payload.get("route_binding_id"),
        "route_binding_event_id": authorization.event.payload.get("route_binding_event_id"),
        "host_snapshot_event_id": authorization.event.payload.get("host_snapshot_event_id"),
        "lease_generation": 1, "external_result_observed": False,
    }
    payload["integrity_authenticator"] = protector.authenticate_json("dispatch.start.v1", payload)
    start = journal.append(EventEnvelope(
        event_id=DispatchOutbox._start_event_id(dispatch_id, 1), event_type="dispatch.started",
        source="alive.dispatch", actor="system:alive-dispatch", subject=attempt.event.subject,
        sensitivity=attempt.event.sensitivity, causation_id=attempt.event.event_id,
        observed_at=start_time, occurred_at=start_time, payload=payload,
    ))
    payload = {
        "dispatch_id": dispatch_id, "attempt_id": attempt.event.payload["attempt_id"],
        "idempotency_key": attempt.event.payload["idempotency_key"],
        "capability": attempt.event.payload["executor"], "start_event_id": start.event.event_id,
        "lease_generation": 1, "outcome": DispatchOutbox.RESULT_OUTCOMES[event_type],
    }
    payload["integrity_authenticator"] = protector.authenticate_json("dispatch.result.v1", payload)
    event = EventEnvelope(
        event_id=event_id, event_type=event_type, source="test.channel", actor="system:test",
        subject=attempt.event.subject, sensitivity=attempt.event.sensitivity,
        observed_at=max(datetime.now(timezone.utc), start_time), payload=payload,
    )
    journal.append(event)
    return event


def install_terminal_route(
    journal: ExperienceJournal,
    *,
    subject: str,
    content_vault=None,
) -> str:
    """Install one explicit test-only route backed by a terminal receipt API."""

    binding_id = f"fixture-route:{subject}"
    host = HostCapabilityProjection(journal, content_vault=content_vault)
    existing = host.get_binding(binding_id)
    if existing is not None:
        return binding_id
    now = datetime.now(timezone.utc)
    snapshot = host.latest_snapshot()
    if snapshot is None:
        snapshot = host.observe_snapshot(
            snapshot_id="fixture-host-terminal-v1",
            hermes_version="0.21.6",
            plugin_api_version=1,
            capabilities={
                "hermes.channel.send": {
                    "interface": "test.public.channel_send",
                    "available": True,
                    "public_api": True,
                    "receipt_level": ReceiptLevel.EXTERNAL_DELIVERED.value,
                }
            },
            observed_at=now,
        )
    authority = EventEnvelope(
        event_id=f"fixture-route-authority:{subject}",
        event_type="conversation.inbound",
        source="test.fixture",
        actor=subject,
        subject=subject,
        occurred_at=now,
        observed_at=now,
        payload={"authorizes_route_binding_id": binding_id},
    )
    journal.append(authority)
    host.bind_route(
        binding_id=binding_id,
        subject=subject,
        capability="hermes.channel.send",
        snapshot_event_id=snapshot.event_id,
        route={
            "platform": "test",
            "profile": "default",
            "chat_id": f"test-chat:{subject}",
        },
        authority_event_id=authority.event_id,
        observed_at=now,
    )
    return binding_id


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
    deliberation = DeliberationProjection(journal)
    stored = deliberation.inspect(
        str(selection.event.payload["frame_id"]),
        clearance=selection.event.sensitivity,
    )
    contract_document = dict(stored.candidate_contents)[
        next(
            str(candidate.content_id)
            for candidate in stored.frame.candidates
            if candidate.candidate_id == candidate_id
        )
    ]
    contract = parse_action_contract(contract_document, capability=executor)
    route_binding_id = install_terminal_route(journal, subject=subject)
    route_binding = HostCapabilityProjection(journal).get_binding(route_binding_id)
    assert route_binding is not None
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
        "route_binding_id": route_binding_id,
        "route_binding_event_id": route_binding.event_id,
        "host_snapshot_event_id": route_binding.snapshot_event_id,
        "route_binding_authenticator": route_binding.binding_authenticator,
        "capability": executor,
        "action_contract_version": 1,
        "action_contract_binding": LocalIdentityProtector(
            journal.path.parent / "identity.key"
        ).authenticate_json("action.contract.v1", contract.to_document()),
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
