#!/usr/bin/env python3
"""Relevance, privacy, explanation, and replay contracts for memory recall."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    ContentStatus,
    EventEnvelope,
    ExperienceJournal,
    MemoryAuthority,
    MemoryKind,
    MemoryProjection,
    MemoryProposal,
    MemoryRecord,
    MemoryState,
    Sensitivity,
    rank_records,
)


def fixture_record(
    memory_id: str,
    value: object,
    *,
    importance: float,
    age_hours: int,
    authority: MemoryAuthority,
) -> MemoryRecord:
    now = datetime.now(timezone.utc)
    return MemoryRecord(
        memory_id=memory_id,
        kind=MemoryKind.FACT,
        subject="user:test",
        predicate="research.topic",
        value=value,
        content_id=f"content:{memory_id}",
        content_status=ContentStatus.AVAILABLE,
        authority=authority,
        state=MemoryState.ACTIVE,
        confidence=0.9,
        importance=importance,
        sensitivity=Sensitivity.PRIVATE,
        source_event_ids=(f"source:{memory_id}",),
        valid_from=None,
        valid_until=None,
        supersedes_id=None,
        created_from_event_id=f"proposal:{memory_id}",
        created_at=now - timedelta(hours=age_hours),
        updated_at=now - timedelta(hours=age_hours),
    )


def main() -> int:
    records = [
        fixture_record(
            "relevant-old",
            "微重力扩散火焰熄火实验",
            importance=0.6,
            age_hours=48,
            authority=MemoryAuthority.USER_EXPLICIT,
        ),
        fixture_record(
            "relevant-new",
            "低压条件下扩散火焰的抬升与熄火",
            importance=0.8,
            age_hours=1,
            authority=MemoryAuthority.DIRECT_OBSERVATION,
        ),
        fixture_record(
            "important-irrelevant",
            "周末想看一部电影",
            importance=1.0,
            age_hours=0,
            authority=MemoryAuthority.USER_EXPLICIT,
        ),
    ]
    hits = rank_records(records, "扩散火焰熄火", limit=10)
    assert [hit.record.memory_id for hit in hits] == ["relevant-new", "relevant-old"]
    assert all(hit.matched_terms for hit in hits)
    assert all("relevance=#" in hit.explanation for hit in hits)
    assert rank_records(records, "完全无关的量子芯片") == []

    no_query = rank_records(records, limit=3)
    assert {name for name, _rank in no_query[0].component_ranks} == {
        "importance",
        "recency",
        "authority",
    }

    with tempfile.TemporaryDirectory(prefix="alive-kernel-retrieval-") as directory:
        journal = ExperienceJournal(Path(directory) / "kernel.sqlite3")
        memory = MemoryProjection(journal)

        def add(
            value: str,
            sensitivity: Sensitivity,
            importance: float,
            *,
            predicate: str = "research.topic",
        ) -> MemoryProposal:
            source = EventEnvelope(
                event_type="conversation.inbound",
                source="test.fixture",
                actor="user:test",
                subject="user:test",
                payload={"fixture": True},
            )
            journal.append(source)
            proposal = MemoryProposal(
                kind=MemoryKind.FACT,
                subject="user:test",
                predicate=predicate,
                value=value,
                authority=MemoryAuthority.USER_EXPLICIT,
                source_event_ids=(source.event_id,),
                confidence=1.0,
                importance=importance,
                sensitivity=sensitivity,
            )
            memory.apply(memory.append_proposal(proposal, actor="user:test"))
            return proposal

        private = add("甲烷扩散火焰与浮力耦合", Sensitivity.PRIVATE, 0.7)
        restricted = add(
            "受限项目中的甲烷扩散火焰",
            Sensitivity.RESTRICTED,
            0.9,
            predicate="research.restricted_topic",
        )
        restricted_recent = add(
            "受限项目中的低压甲烷扩散火焰",
            Sensitivity.RESTRICTED,
            0.8,
            predicate="research.restricted_condition",
        )

        private_hits = memory.search(
            "甲烷扩散火焰", clearance=Sensitivity.PRIVATE, limit=10
        )
        assert [hit.record.memory_id for hit in private_hits] == [private.proposal_id]
        restricted_hits = memory.search(
            "甲烷扩散火焰", clearance=Sensitivity.RESTRICTED, limit=10
        )
        assert {hit.record.memory_id for hit in restricted_hits} == {
            private.proposal_id,
            restricted.proposal_id,
            restricted_recent.proposal_id,
        }
        assert all(hit.record.source_event_ids for hit in restricted_hits)

        memory.forget_item(private.proposal_id, actor="user:test")
        assert memory.search(
            "甲烷扩散火焰", clearance=Sensitivity.PRIVATE, limit=10
        ) == []

        before = [
            (
                hit.record.memory_id,
                hit.record.created_at,
                hit.record.updated_at,
                hit.score,
                hit.component_ranks,
            )
            for hit in memory.search(
                "甲烷扩散火焰", clearance=Sensitivity.RESTRICTED, limit=10
            )
        ]
        assert len(before) == 2
        memory.rebuild(batch_size=2)
        after = [
            (
                hit.record.memory_id,
                hit.record.created_at,
                hit.record.updated_at,
                hit.score,
                hit.component_ranks,
            )
            for hit in memory.search(
                "甲烷扩散火焰", clearance=Sensitivity.RESTRICTED, limit=10
            )
        ]
        assert after == before

    print("HERMES_ALIVE_KERNEL_RETRIEVAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
