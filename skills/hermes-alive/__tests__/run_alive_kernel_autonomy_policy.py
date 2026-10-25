#!/usr/bin/env python3
"""Self-authority, revision, concurrency and replay policy contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    AutonomyPolicyError,
    AutonomyPolicyProjection,
    EventEnvelope,
    ExperienceJournal,
    PolicyContext,
    Sensitivity,
    SideEffect,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-autonomy-policy-") as directory:
        path = Path(directory) / "kernel.sqlite3"
        journal = ExperienceJournal(path)
        projection = AutonomyPolicyProjection(journal)
        assert projection.current("user:test") is None

        try:
            projection.append_update(
                subject="user:test",
                actor="system:impersonator",
                expected_revision=0,
                enabled=True,
                context=PolicyContext(can_interrupt=True),
            )
        except AutonomyPolicyError:
            pass
        else:
            raise AssertionError("non-user policy authority was accepted")

        first = projection.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=0,
            enabled=True,
            context=PolicyContext(
                can_interrupt=True,
                minimum_confidence=0.7,
                maximum_risk=0.2,
                allowed_side_effects=frozenset(
                    {SideEffect.NONE, SideEffect.COMMUNICATION}
                ),
            ),
            operation_id="initial",
        )
        assert projection.apply(first).outcome == "recorded"
        assert projection.apply(first).outcome == "recorded"
        policy = projection.current("user:test")
        assert policy is not None
        assert policy.revision == 1 and policy.enabled
        assert policy.context.minimum_confidence == 0.7

        winner = projection.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=1,
            enabled=True,
            context=PolicyContext(can_interrupt=False),
            operation_id="revision-winner",
        )
        stale = projection.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=1,
            enabled=False,
            context=PolicyContext(can_interrupt=False),
            operation_id="revision-stale",
        )
        assert projection.apply(winner).outcome == "recorded"
        rejected = projection.apply(stale)
        assert rejected.outcome == "rejected"
        assert rejected.reason == "policy_revision_conflict"

        forged = EventEnvelope(
            event_id="autonomy.policy:forged",
            event_type="autonomy.policy_changed",
            source="hermes.command.alive",
            actor="user:test",
            subject="user:test",
            sensitivity=Sensitivity.PRIVATE,
            payload={
                "revision": 3,
                "expected_revision": 2,
                "enabled": True,
                "can_interrupt": True,
                "minimum_confidence": 0.5,
                "maximum_risk": 0.5,
                "allowed_side_effects": ["none", "communication"],
                "raw_command_stored": False,
            },
        )
        forged_record = journal.append(forged)
        assert projection.apply(forged_record).reason == "policy_authority_invalid"

        paused = projection.append_update(
            subject="user:test",
            actor="user:test",
            expected_revision=2,
            enabled=False,
            context=PolicyContext(can_interrupt=False),
            operation_id="paused",
        )
        assert projection.apply(paused).outcome == "recorded"
        assert projection.current("user:test").enabled is False

        competing = tuple(
            projection.append_update(
                subject="user:test",
                actor="user:test",
                expected_revision=3,
                enabled=True,
                context=PolicyContext(
                    can_interrupt=bool(index % 2),
                    minimum_confidence=0.5 + index / 100,
                ),
                operation_id=f"concurrent-{index}",
            )
            for index in range(8)
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            decisions = tuple(pool.map(projection.apply, competing))
        assert sum(item.outcome == "recorded" for item in decisions) == 1
        assert sum(item.reason == "policy_revision_conflict" for item in decisions) == 7
        expected = projection.current("user:test")
        assert expected is not None and expected.revision == 4 and expected.enabled

        with closing(sqlite3.connect(path)) as connection:
            connection.execute("DELETE FROM autonomy_policies_v1")
            connection.execute("DELETE FROM autonomy_policy_decisions_v1")
            connection.execute(
                "DELETE FROM consumer_checkpoints WHERE consumer_name=?",
                (projection.CHECKPOINT,),
            )
            connection.commit()
        replayed = AutonomyPolicyProjection(journal)
        replayed.rebuild(batch_size=1)
        rebuilt = replayed.current("user:test")
        assert rebuilt == expected

        raw = path.read_bytes()
        wal = path.with_name(path.name + "-wal")
        if wal.exists():
            raw += wal.read_bytes()
        assert b"system:impersonator" not in raw
        assert journal.verify_integrity() == journal.last_sequence()

    print("HERMES_ALIVE_KERNEL_AUTONOMY_POLICY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
