#!/usr/bin/env python3
"""Authority, contradiction and replay contracts for typed Alive memory."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    EventEnvelope,
    ExperienceJournal,
    MemoryAuthority,
    MemoryKind,
    MemoryProjection,
    MemoryProposal,
    MemoryState,
    ProjectionDecisionKind,
    Sensitivity,
)


def source(journal: ExperienceJournal, event_type: str = "conversation.inbound") -> EventEnvelope:
    event = EventEnvelope(
        event_type=event_type,
        source="test.fixture",
        actor="user:test",
        subject="user:test",
        payload={"fixture": True},
    )
    journal.append(event)
    return event


def proposal(source_event: EventEnvelope, **changes: object) -> MemoryProposal:
    values: dict[str, object] = {
        "kind": MemoryKind.FACT,
        "subject": "user:test",
        "predicate": "profile.city",
        "value": "Hefei",
        "authority": MemoryAuthority.USER_EXPLICIT,
        "source_event_ids": (source_event.event_id,),
        "confidence": 1.0,
    }
    values.update(changes)
    return MemoryProposal(**values)  # type: ignore[arg-type]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-memory-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        memory = MemoryProjection(journal)

        first_source = source(journal)
        first = proposal(first_source)
        first_event = memory.append_proposal(first, actor="user:test")
        first_decision = memory.apply(first_event)
        assert first_decision.decision is ProjectionDecisionKind.ACTIVATED
        assert memory.get(first.proposal_id).state is MemoryState.ACTIVE  # type: ignore[union-attr]

        # Model confidence is not authority, even at 1.0.
        inference_source = source(journal, "reflection.generated")
        inferred = proposal(
            inference_source,
            value="Nanjing",
            authority=MemoryAuthority.MODEL_INFERENCE,
            confidence=1.0,
        )
        inferred_decision = memory.apply(
            memory.append_proposal(inferred, actor="model:test")
        )
        assert inferred_decision.decision is ProjectionDecisionKind.PROPOSED
        assert memory.get(inferred.proposal_id).state is MemoryState.PROPOSED  # type: ignore[union-attr]
        assert memory.retrieve(
            subject="user:test",
            predicate="profile.city",
            clearance=Sensitivity.PRIVATE,
        )[0].value == "Hefei"

        # Identical claims add provenance instead of another competing memory.
        duplicate_source = source(journal)
        duplicate = proposal(duplicate_source)
        duplicate_decision = memory.apply(
            memory.append_proposal(duplicate, actor="user:test")
        )
        assert duplicate_decision.decision is ProjectionDecisionKind.DEDUPLICATED
        assert duplicate_decision.memory_id == first.proposal_id
        first_record = memory.get(first.proposal_id)
        assert first_record is not None
        assert set(first_record.source_event_ids) == {
            first_source.event_id,
            duplicate_source.event_id,
        }

        # A contradictory observation preserves both sides as contested.
        observed_source = source(journal, "tool.location_observed")
        observed = proposal(
            observed_source,
            value="Shanghai",
            authority=MemoryAuthority.DIRECT_OBSERVATION,
            confidence=0.9,
        )
        observed_decision = memory.apply(
            memory.append_proposal(observed, actor="tool:location")
        )
        assert observed_decision.decision is ProjectionDecisionKind.CONTESTED
        assert memory.get(first.proposal_id).state is MemoryState.CONTESTED  # type: ignore[union-attr]
        assert memory.get(observed.proposal_id).state is MemoryState.CONTESTED  # type: ignore[union-attr]
        assert memory.retrieve(
            subject="user:test",
            predicate="profile.city",
            clearance=Sensitivity.PRIVATE,
        ) == []

        # An explicit correction names what it supersedes and becomes active.
        correction_source = source(journal)
        corrected = proposal(
            correction_source,
            value="Shanghai",
            supersedes_id=first.proposal_id,
        )
        correction_decision = memory.apply(
            memory.append_proposal(corrected, actor="user:test")
        )
        assert correction_decision.decision is ProjectionDecisionKind.ACTIVATED
        assert memory.get(first.proposal_id).state is MemoryState.SUPERSEDED  # type: ignore[union-attr]
        active = memory.retrieve(
            subject="user:test",
            predicate="profile.city",
            clearance=Sensitivity.PRIVATE,
        )
        assert len(active) == 1 and active[0].value == "Shanghai"
        first_history = memory.transition_history(first.proposal_id)
        assert [item["to_state"] for item in first_history] == [
            MemoryState.ACTIVE.value,
            MemoryState.CONTESTED.value,
            MemoryState.SUPERSEDED.value,
        ]

        stale_correction_source = source(journal)
        stale_correction = proposal(
            stale_correction_source,
            value="Wuhan",
            supersedes_id=first.proposal_id,
        )
        stale_decision = memory.apply(
            memory.append_proposal(stale_correction, actor="user:test")
        )
        assert stale_decision.decision is ProjectionDecisionKind.PROPOSED
        assert memory.get(stale_correction.proposal_id).state is MemoryState.PROPOSED  # type: ignore[union-attr]
        active = memory.retrieve(
            subject="user:test",
            predicate="profile.city",
            clearance=Sensitivity.PRIVATE,
        )
        assert len(active) == 1 and active[0].value == "Shanghai"

        # Direct observations cannot silently activate preferences.
        preference_source = source(journal, "behavior.observed")
        weak_preference = proposal(
            preference_source,
            kind=MemoryKind.PREFERENCE,
            predicate="content.likes_cats",
            value=True,
            authority=MemoryAuthority.DIRECT_OBSERVATION,
            confidence=0.99,
        )
        preference_decision = memory.apply(
            memory.append_proposal(weak_preference, actor="hermes:observer")
        )
        assert preference_decision.decision is ProjectionDecisionKind.PROPOSED

        # Expired active memory is retained for history but excluded at query.
        old_source = source(journal)
        old = proposal(
            old_source,
            predicate="context.temporary",
            value="old",
            valid_from=datetime.now(timezone.utc) - timedelta(hours=2),
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        memory.apply(memory.append_proposal(old, actor="user:test"))
        assert memory.get(old.proposal_id) is not None
        assert memory.retrieve(
            subject="user:test",
            predicate="context.temporary",
            clearance=Sensitivity.PRIVATE,
        ) == []

        # Retrieval requires an explicit privacy clearance.
        restricted_source = source(journal)
        restricted = proposal(
            restricted_source,
            predicate="profile.restricted_note",
            value="sensitive",
            sensitivity=Sensitivity.RESTRICTED,
        )
        memory.apply(memory.append_proposal(restricted, actor="user:test"))
        assert memory.retrieve(
            subject="user:test",
            predicate="profile.restricted_note",
            clearance=Sensitivity.PRIVATE,
        ) == []
        assert len(
            memory.retrieve(
                subject="user:test",
                predicate="profile.restricted_note",
                clearance=Sensitivity.RESTRICTED,
            )
        ) == 1

        concurrent_source = source(journal)
        concurrent_proposal = proposal(
            concurrent_source,
            predicate="profile.language",
            value="zh-CN",
        )
        concurrent_record = memory.append_proposal(concurrent_proposal, actor="user:test")
        with ThreadPoolExecutor(max_workers=8) as pool:
            concurrent_decisions = list(
                pool.map(lambda _: memory.apply(concurrent_record), range(16))
            )
        assert len(set(concurrent_decisions)) == 1
        assert concurrent_decisions[0].decision is ProjectionDecisionKind.ACTIVATED

        # Missing evidence is rejected rather than accepted by confidence.
        missing = MemoryProposal(
            kind=MemoryKind.FACT,
            subject="user:test",
            predicate="profile.timezone",
            value="Asia/Shanghai",
            authority=MemoryAuthority.USER_EXPLICIT,
            source_event_ids=("missing-event",),
            confidence=1.0,
        )
        missing_decision = memory.apply(
            memory.append_proposal(missing, actor="user:test")
        )
        assert missing_decision.decision is ProjectionDecisionKind.REJECTED
        assert missing_decision.memory_id is None

        # Commitment structure is mandatory.
        try:
            proposal(
                source(journal),
                kind=MemoryKind.COMMITMENT,
                predicate="commitment.follow_up",
                value={"condition": "tomorrow"},
            )
        except ValueError:
            pass
        else:
            raise AssertionError("incomplete commitment was accepted")

        # Reopen and replay: decisions are idempotent and checkpoint advances.
        reopened = MemoryProjection(ExperienceJournal(Path(directory) / "kernel.sqlite3"))
        decisions = reopened.project_new(limit=10_000)
        assert decisions
        assert reopened.project_new(limit=10_000) == []
        before = reopened.get(corrected.proposal_id)
        replayed = reopened.apply(
            next(
                record
                for record in reopened.journal.iter_replay()
                if record.event.event_id == correction_decision.proposal_event_id
            )
        )
        after = reopened.get(corrected.proposal_id)
        assert replayed == correction_decision
        assert before == after

        expected = [
            (item.memory_id, item.state, item.value, item.source_event_ids)
            for item in reopened.retrieve(
                subject="user:test",
                states=tuple(MemoryState),
                clearance=Sensitivity.RESTRICTED,
                limit=1000,
            )
        ]
        rebuilt_decisions = reopened.rebuild(batch_size=3)
        assert rebuilt_decisions
        actual = [
            (item.memory_id, item.state, item.value, item.source_event_ids)
            for item in reopened.retrieve(
                subject="user:test",
                states=tuple(MemoryState),
                clearance=Sensitivity.RESTRICTED,
                limit=1000,
            )
        ]
        assert actual == expected

    print("HERMES_ALIVE_KERNEL_MEMORY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
