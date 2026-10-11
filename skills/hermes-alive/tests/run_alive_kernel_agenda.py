#!/usr/bin/env python3
"""Authority, lifecycle, privacy, and replay contracts for the agenda."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    AgendaAuthority,
    AgendaContentStatus,
    AgendaItemKind,
    AgendaProjection,
    AgendaProposal,
    AgendaState,
    EventEnvelope,
    ExperienceJournal,
    Sensitivity,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-agenda-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        agenda = AgendaProjection(journal)
        now = datetime.now(timezone.utc)

        def source(label: str) -> EventEnvelope:
            event = EventEnvelope(
                event_type="conversation.inbound",
                source="test.fixture",
                actor="user:test",
                subject="user:test",
                payload={"label": label},
            )
            journal.append(event)
            return event

        explicit_source = source("explicit commitment")
        explicit = AgendaProposal(
            kind=AgendaItemKind.COMMITMENT,
            subject="user:test",
            details={"summary": "周五前完成验收", "beneficiary": "user:test"},
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_ids=(explicit_source.event_id,),
            confidence=1.0,
            priority=0.9,
            sensitivity=Sensitivity.PRIVATE,
            due_at=now + timedelta(days=2),
        )
        decision = agenda.apply(agenda.append_proposal(explicit, actor="user:test"))
        assert decision.outcome == AgendaState.ACTIVE.value
        retry = agenda.append_proposal(explicit, actor="user:test")
        assert retry.event.event_id == decision.event_id

        forged_actor = AgendaProposal(
            kind=AgendaItemKind.COMMITMENT,
            subject="user:test",
            details={"summary": "forged explicit authority"},
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_ids=(explicit_source.event_id,),
            confidence=1.0,
            item_id="agenda:forged-actor",
        )
        forged_actor_decision = agenda.apply(
            agenda.append_proposal(forged_actor, actor="model:test")
        )
        assert forged_actor_decision.reason == "proposal_authority_invalid"

        other_source = EventEnvelope(
            event_type="conversation.inbound",
            source="test.fixture",
            actor="user:other",
            subject="user:other",
            payload={"label": "cross-subject source"},
        )
        journal.append(other_source)
        cross_subject = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:test",
            details={"summary": "must not cross users"},
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(other_source.event_id,),
            confidence=0.8,
            item_id="agenda:cross-subject",
        )
        cross_subject_decision = agenda.apply(
            agenda.append_proposal(cross_subject, actor="system:discovery")
        )
        assert cross_subject_decision.reason == "proposal_authority_invalid"

        model_source = source("model commitment")
        model = AgendaProposal(
            kind=AgendaItemKind.COMMITMENT,
            subject="user:test",
            details={"summary": "模型猜测用户应该提交报告"},
            authority=AgendaAuthority.MODEL_PROPOSAL,
            source_event_ids=(model_source.event_id,),
            confidence=0.6,
            sensitivity=Sensitivity.PRIVATE,
        )
        model_decision = agenda.apply(agenda.append_proposal(model, actor="model:test"))
        assert model_decision.outcome == AgendaState.PROPOSED.value
        unauthorized_activation = agenda.append_transition(
            model.item_id,
            AgendaState.ACTIVE,
            actor="model:test",
            authority=AgendaAuthority.MODEL_PROPOSAL,
            source_event_id=model_source.event_id,
            reason="model cannot authorize its own commitment",
            operation_id="agenda-op:unauthorized-activation-test",
        )
        assert (
            agenda.apply(unauthorized_activation).reason
            == "commitment_transition_requires_authority"
        )
        authorized_activation = agenda.append_transition(
            model.item_id,
            AgendaState.ACTIVE,
            actor="user:test",
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_id=source("confirm model commitment").event_id,
            reason="用户确认承诺",
            operation_id="agenda-op:authorized-activation-test",
        )
        assert agenda.apply(authorized_activation).outcome == "transitioned"

        opportunity_source = source("observed opportunity")
        opportunity = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject="user:test",
            details={"summary": "发现一个可能有价值的新政策"},
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(opportunity_source.event_id,),
            confidence=0.8,
            priority=0.7,
            sensitivity=Sensitivity.RESTRICTED,
        )
        opportunity_decision = agenda.apply(
            agenda.append_proposal(opportunity, actor="system:discovery")
        )
        assert opportunity_decision.outcome == AgendaState.ACTIVE.value

        private_items = agenda.list_items(clearance=Sensitivity.PRIVATE)
        assert [item.item_id for item in private_items] == [explicit.item_id, model.item_id]
        restricted_items = agenda.list_items(clearance=Sensitivity.RESTRICTED)
        assert {item.item_id for item in restricted_items} == {
            explicit.item_id,
            model.item_id,
            opportunity.item_id,
        }
        assert all(
            item.content_status is AgendaContentStatus.AVAILABLE
            for item in restricted_items
        )

        wake_at = now + timedelta(hours=4)
        snooze = agenda.append_transition(
            explicit.item_id,
            AgendaState.SNOOZED,
            actor="user:test",
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_id=source("snooze explicit commitment").event_id,
            reason="稍后处理",
            available_at=wake_at,
            operation_id="agenda-op:snooze-test",
        )
        assert agenda.apply(snooze).outcome == "transitioned"
        assert [
            item.item_id
            for item in agenda.list_items(clearance=Sensitivity.PRIVATE, as_of=now)
        ] == [model.item_id]
        awakened = agenda.list_items(
            clearance=Sensitivity.PRIVATE,
            states=(AgendaState.SNOOZED,),
            as_of=wake_at + timedelta(seconds=1),
        )
        assert [item.item_id for item in awakened] == [explicit.item_id]

        complete = agenda.append_transition(
            explicit.item_id,
            AgendaState.COMPLETED,
            actor="user:test",
            authority=AgendaAuthority.USER_EXPLICIT,
            source_event_id=source("complete explicit commitment").event_id,
            reason="用户确认完成",
            operation_id="agenda-op:complete-test",
        )
        assert agenda.apply(complete).outcome == "transitioned"
        invalid = agenda.append_transition(
            explicit.item_id,
            AgendaState.ACTIVE,
            actor="model:test",
            authority=AgendaAuthority.MODEL_PROPOSAL,
            source_event_id=model_source.event_id,
            reason="terminal state cannot reopen",
            operation_id="agenda-op:invalid-reopen-test",
        )
        assert agenda.apply(invalid).reason == "invalid_state_transition"

        replay_states = (
            AgendaState.PROPOSED,
            AgendaState.ACTIVE,
            AgendaState.SNOOZED,
            AgendaState.COMPLETED,
        )

        def snapshot():
            return [
                (
                    item.item_id,
                    item.state,
                    item.details,
                    item.created_at,
                    item.updated_at,
                    item.source_event_ids,
                )
                for item in agenda.list_items(
                    clearance=Sensitivity.RESTRICTED,
                    states=replay_states,
                    as_of=wake_at + timedelta(days=1),
                )
            ]

        before = snapshot()
        agenda.rebuild(batch_size=2)
        assert snapshot() == before

    print("HERMES_ALIVE_KERNEL_AGENDA_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
