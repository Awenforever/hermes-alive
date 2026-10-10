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
    ContentErasedError,
    ContentStatus,
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


def get_memory(memory: MemoryProjection, memory_id: str):
    return memory.get(memory_id, clearance=Sensitivity.RESTRICTED)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-kernel-memory-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        memory = MemoryProjection(journal)

        first_source = source(journal)
        first = proposal(first_source)
        first_event = memory.append_proposal(first, actor="user:test")
        assert memory.append_proposal(first, actor="user:test") == first_event
        first_decision = memory.apply(first_event)
        assert first_decision.decision is ProjectionDecisionKind.ACTIVATED
        assert get_memory(memory, first.proposal_id).state is MemoryState.ACTIVE  # type: ignore[union-attr]

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
        assert get_memory(memory, inferred.proposal_id).state is MemoryState.PROPOSED  # type: ignore[union-attr]
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
        first_record = get_memory(memory, first.proposal_id)
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
        assert get_memory(memory, first.proposal_id).state is MemoryState.CONTESTED  # type: ignore[union-attr]
        assert get_memory(memory, observed.proposal_id).state is MemoryState.CONTESTED  # type: ignore[union-attr]
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
        assert get_memory(memory, first.proposal_id).state is MemoryState.SUPERSEDED  # type: ignore[union-attr]
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
        stale_record = get_memory(memory, stale_correction.proposal_id)
        assert stale_record is not None and stale_record.state is MemoryState.PROPOSED
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
        assert get_memory(memory, old.proposal_id) is not None
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
        assert memory.get(
            restricted.proposal_id, clearance=Sensitivity.PRIVATE
        ) is None
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

        sensitivity_source = source(journal)
        low_sensitivity = proposal(
            sensitivity_source,
            predicate="profile.classified_value",
            value="same-claim",
            sensitivity=Sensitivity.PRIVATE,
        )
        memory.apply(memory.append_proposal(low_sensitivity, actor="user:test"))
        sensitivity_upgrade_source = source(journal)
        high_sensitivity = proposal(
            sensitivity_upgrade_source,
            predicate="profile.classified_value",
            value="same-claim",
            sensitivity=Sensitivity.RESTRICTED,
        )
        upgraded = memory.apply(
            memory.append_proposal(high_sensitivity, actor="user:test")
        )
        assert upgraded.decision is ProjectionDecisionKind.DEDUPLICATED
        assert memory.get(
            low_sensitivity.proposal_id, clearance=Sensitivity.PRIVATE
        ) is None
        upgraded_record = memory.get(
            low_sensitivity.proposal_id, clearance=Sensitivity.RESTRICTED
        )
        assert upgraded_record is not None
        assert upgraded_record.content_status is ContentStatus.AVAILABLE
        assert upgraded_record.value == "same-claim"

        concurrent_source = source(journal)
        concurrent_proposal = proposal(
            concurrent_source,
            predicate="profile.language",
            value="zh-CN",
        )
        concurrent_record = memory.append_proposal(concurrent_proposal, actor="user:test")
        with ThreadPoolExecutor(max_workers=8) as pool:
            concurrent_appends = list(
                pool.map(
                    lambda _: memory.append_proposal(
                        concurrent_proposal, actor="user:test"
                    ),
                    range(16),
                )
            )
        assert {
            (item.sequence, item.event.event_id) for item in concurrent_appends
        } == {(concurrent_record.sequence, concurrent_record.event.event_id)}
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

        # Private values never cross the journal/projection boundary. Explicit
        # forgetting is durable, idempotent, and replay exposes an erased
        # state instead of reconstructing the value.
        private_sentinel = "PRIVATE-MEMORY-SENTINEL-火焰-a872"
        private_source = source(journal)
        private = proposal(
            private_source,
            predicate="profile.private_note",
            value=private_sentinel,
        )
        private_event = memory.append_proposal(private, actor="user:test")
        assert "value" not in private_event.event.payload
        assert "content" in private_event.event.payload
        memory.apply(private_event)
        assert private_sentinel.encode("utf-8") not in (Path(directory) / "kernel.sqlite3").read_bytes()
        malicious_payload = dict(private_event.event.payload)
        malicious_payload["proposal_id"] = "malicious-cross-subject"
        malicious_payload["subject"] = "user:attacker"
        malicious = EventEnvelope(
            event_type="memory.proposed",
            source="test.fixture",
            actor="user:attacker",
            subject="user:attacker",
            payload=malicious_payload,
            sensitivity=Sensitivity.PRIVATE,
        )
        malicious_record = journal.append(malicious)
        malicious_decision = memory.apply(
            type(first_event)(malicious_record.sequence, malicious_record.event)
        )
        assert malicious_decision.decision is ProjectionDecisionKind.REJECTED
        assert malicious_decision.reason == "content_integrity_error"
        assert memory.forget_item(
            private.proposal_id,
            actor="user:test",
            request_id="forget-private-note",
        )
        assert memory.forget_item(
            private.proposal_id,
            actor="user:test",
            request_id="forget-private-note",
        )
        erased = get_memory(memory, private.proposal_id)
        assert erased is not None
        assert erased.state is MemoryState.RETRACTED
        assert erased.content_status is ContentStatus.ERASED
        assert erased.value is None
        assert memory.retrieve(
            subject="user:test",
            predicate="profile.private_note",
            states=tuple(MemoryState),
            clearance=Sensitivity.PRIVATE,
        ) == []
        unavailable = memory.retrieve(
            subject="user:test",
            predicate="profile.private_note",
            states=tuple(MemoryState),
            clearance=Sensitivity.PRIVATE,
            include_unavailable=True,
        )
        assert len(unavailable) == 1
        assert unavailable[0].content_status is ContentStatus.ERASED
        for path in Path(directory).rglob("*"):
            if path.is_file():
                assert private_sentinel.encode("utf-8") not in path.read_bytes()

        erase_subject_source = source(journal)
        erase_subject_memory = proposal(
            erase_subject_source,
            subject="user:erase",
            predicate="profile.note",
            value="erase-me",
        )
        keep_subject_source = source(journal)
        keep_subject_memory = proposal(
            keep_subject_source,
            subject="user:keep",
            predicate="profile.note",
            value="keep-me",
        )
        memory.apply(memory.append_proposal(erase_subject_memory, actor="user:erase"))
        memory.apply(memory.append_proposal(keep_subject_memory, actor="user:keep"))
        assert memory.forget_subject(
            "user:erase", actor="user:erase", request_id="forget-subject"
        ) == 1
        erased_subject_record = get_memory(memory, erase_subject_memory.proposal_id)
        kept_subject_record = get_memory(memory, keep_subject_memory.proposal_id)
        assert erased_subject_record is not None
        assert erased_subject_record.content_status is ContentStatus.ERASED
        assert kept_subject_record is not None and kept_subject_record.value == "keep-me"
        after_forget_source = source(journal)
        after_forget = proposal(
            after_forget_source,
            subject="user:erase",
            predicate="profile.new_note",
            value="created-after-forgetting",
        )
        memory.apply(memory.append_proposal(after_forget, actor="user:erase"))
        after_forget_record = get_memory(memory, after_forget.proposal_id)
        assert after_forget_record is not None
        assert after_forget_record.value == "created-after-forgetting"

        # Deduplicated claims own multiple encrypted objects. Forgetting the
        # projected memory must erase every associated object, not only the
        # first proposal's primary reference.
        assert memory.forget_item(
            first.proposal_id,
            actor="user:test",
            request_id="forget-deduplicated-memory",
        )
        for proposal_id in (first.proposal_id, duplicate.proposal_id):
            try:
                memory.content_vault.resolve_json(f"memory:{proposal_id}")
            except ContentErasedError:
                pass
            else:
                raise AssertionError("deduplicated content survived forgetting")

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
        before = get_memory(reopened, corrected.proposal_id)
        replayed = reopened.apply(
            next(
                record
                for record in reopened.journal.iter_replay()
                if record.event.event_id == correction_decision.proposal_event_id
            )
        )
        after = get_memory(reopened, corrected.proposal_id)
        assert replayed == correction_decision
        assert before == after

        expected = [
            (
                item.memory_id,
                item.state,
                item.value,
                item.content_status,
                item.source_event_ids,
            )
            for item in reopened.retrieve(
                subject="user:test",
                states=tuple(MemoryState),
                clearance=Sensitivity.RESTRICTED,
                limit=1000,
                include_unavailable=True,
            )
        ]
        rebuilt_decisions = reopened.rebuild(batch_size=3)
        assert rebuilt_decisions
        actual = [
            (
                item.memory_id,
                item.state,
                item.value,
                item.content_status,
                item.source_event_ids,
            )
            for item in reopened.retrieve(
                subject="user:test",
                states=tuple(MemoryState),
                clearance=Sensitivity.RESTRICTED,
                limit=1000,
                include_unavailable=True,
            )
        ]
        assert actual == expected
        replay_erased = get_memory(reopened, private.proposal_id)
        assert replay_erased is not None
        assert replay_erased.state is MemoryState.RETRACTED
        assert replay_erased.content_status is ContentStatus.ERASED
        assert replay_erased.value is None
        replay_after_forget = get_memory(reopened, after_forget.proposal_id)
        assert replay_after_forget is not None
        assert replay_after_forget.value == "created-after-forgetting"

    print("HERMES_ALIVE_KERNEL_MEMORY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
