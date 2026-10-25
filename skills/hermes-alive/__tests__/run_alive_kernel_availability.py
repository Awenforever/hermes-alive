#!/usr/bin/env python3
"""Availability is bounded evidence, not Circadian style or send authority."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    AvailabilityBasis,
    AvailabilityError,
    AvailabilityProjection,
    AvailabilitySignal,
    AvailabilityStance,
    AvailabilityState,
    EventEnvelope,
    ExperienceJournal,
    availability_shadow_enabled,
    mirror_legacy_activity_guard,
)


def main() -> int:
    now = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix="alive-kernel-availability-") as directory:
        path = Path(directory)
        journal = ExperienceJournal(path / "kernel.sqlite3")
        projection = AvailabilityProjection(journal)

        idle = AvailabilitySignal(
            subject="user:test",
            stance=AvailabilityStance.UNKNOWN,
            basis=AvailabilityBasis.DIRECT_ACTIVITY,
            reason_code="idle_and_queue_healthy",
            valid_from=now,
            valid_until=now + timedelta(minutes=5),
            confidence=0.5,
            signal_id="availability:idle",
        )
        assert projection.apply(
            projection.append_signal(idle, actor="system:alive-availability")
        ).outcome == "recorded"
        assessment = projection.assess("user:test", as_of=now + timedelta(minutes=1))
        assert assessment.state is AvailabilityState.UNKNOWN
        assert assessment.permits_action is False

        try:
            AvailabilitySignal(
                subject="user:test",
                stance=AvailabilityStance.ALLOW,
                basis=AvailabilityBasis.DIRECT_ACTIVITY,
                reason_code="idle_is_not_permission",
                valid_from=now,
                valid_until=now + timedelta(minutes=5),
                confidence=1.0,
            )
        except AvailabilityError:
            pass
        else:
            raise AssertionError("direct observation granted availability")

        inbound = EventEnvelope(
            event_id="conversation:availability-allow",
            event_type="conversation.inbound",
            source="test.fixture",
            actor="user:test",
            subject="user:test",
            occurred_at=now,
            observed_at=now,
            payload={"raw_content_stored": False},
        )
        journal.append(inbound)
        explicit_allow = AvailabilitySignal(
            subject="user:test",
            stance=AvailabilityStance.ALLOW,
            basis=AvailabilityBasis.USER_EXPLICIT,
            reason_code="user_available_now",
            valid_from=now,
            valid_until=now + timedelta(hours=1),
            confidence=1.0,
            source_event_id=inbound.event_id,
            signal_id="availability:explicit-allow",
        )
        assert projection.apply(
            projection.append_signal(explicit_allow, actor="user:test")
        ).outcome == "recorded"
        assessment = projection.assess("user:test", as_of=now + timedelta(minutes=1))
        assert assessment.state is AvailabilityState.EXPLICITLY_AVAILABLE
        assert assessment.permits_action is False

        busy = AvailabilitySignal(
            subject="user:test",
            stance=AvailabilityStance.BLOCK,
            basis=AvailabilityBasis.DIRECT_ACTIVITY,
            reason_code="shared_or_local_session_busy",
            valid_from=now + timedelta(minutes=2),
            valid_until=now + timedelta(minutes=7),
            confidence=1.0,
            signal_id="availability:busy",
        )
        projection.apply(projection.append_signal(busy, actor="system:alive-availability"))
        assessment = projection.assess("user:test", as_of=now + timedelta(minutes=3))
        assert assessment.state is AvailabilityState.BLOCKED
        assert assessment.reason_codes == ("shared_or_local_session_busy",)

        other = EventEnvelope(
            event_id="conversation:other-user",
            event_type="conversation.inbound",
            source="test.fixture",
            actor="user:other",
            subject="user:other",
            occurred_at=now,
            observed_at=now,
            payload={"raw_content_stored": False},
        )
        journal.append(other)
        forged = AvailabilitySignal(
            subject="user:test",
            stance=AvailabilityStance.BLOCK,
            basis=AvailabilityBasis.USER_EXPLICIT,
            reason_code="forged_cross_subject",
            valid_from=now,
            valid_until=now + timedelta(hours=1),
            confidence=1.0,
            source_event_id=other.event_id,
            signal_id="availability:forged",
        )
        forged_decision = projection.apply(
            projection.append_signal(forged, actor="user:test")
        )
        assert forged_decision.reason == "invalid_authority"

        before = projection.assess("user:test", as_of=now + timedelta(minutes=3))
        projection.rebuild(batch_size=1)
        assert projection.assess("user:test", as_of=now + timedelta(minutes=3)) == before

        # A locally tampered projection row cannot become availability evidence.
        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute(
                "UPDATE availability_signals_v1 SET stance='allow', basis='user_explicit' "
                "WHERE signal_id='availability:busy'"
            )
            connection.commit()
        after_tamper = projection.assess("user:test", as_of=now + timedelta(minutes=3))
        assert after_tamper.state is AvailabilityState.UNKNOWN
        assert after_tamper.reason_codes == ("projection_integrity_error",)
        projection.rebuild()
        assert projection.assess(
            "user:test", as_of=now + timedelta(minutes=3)
        ).state is AvailabilityState.BLOCKED

        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute(
                "DELETE FROM availability_signals_v1 WHERE signal_id='availability:busy'"
            )
            connection.execute(
                "UPDATE availability_projection_v1 SET signal_count=signal_count-1 "
                "WHERE singleton=1"
            )
            connection.commit()
        missing = projection.assess("user:test", as_of=now + timedelta(minutes=3))
        assert missing.state is AvailabilityState.UNKNOWN
        assert missing.reason_codes == ("projection_integrity_error",)
        projection.rebuild()

        late = AvailabilitySignal(
            subject="user:test",
            stance=AvailabilityStance.BLOCK,
            basis=AvailabilityBasis.DIRECT_ACTIVITY,
            reason_code="late_unprojected_activity",
            valid_from=now + timedelta(minutes=10),
            valid_until=now + timedelta(minutes=15),
            confidence=1.0,
            signal_id="availability:late",
        )
        projection.append_signal(late, actor="system:alive-availability")
        recovered = AvailabilityProjection(journal, protector=projection.protector)
        assert recovered.assess(
            "user:test", as_of=now + timedelta(minutes=11)
        ).state is AvailabilityState.BLOCKED

        expired = recovered.assess("user:test", as_of=now + timedelta(hours=2))
        assert expired.state is AvailabilityState.UNKNOWN
        assert expired.permits_action is False

    assert availability_shadow_enabled({}) is False
    assert availability_shadow_enabled(
        {
            "HERMES_ALIVE_KERNEL_SHADOW_ENABLED": "true",
            "HERMES_ALIVE_AVAILABILITY_SHADOW_ENABLED": "true",
        }
    ) is True
    with tempfile.TemporaryDirectory(prefix="alive-availability-shadow-") as directory:
        decision = mirror_legacy_activity_guard(
            directory,
            raw_subject="raw-chat-id-sentinel",
            tick_id="tick-1",
            stage="pre-send",
            user_active=False,
            snapshot={"activity_guard_reason_code": "idle_and_queue_healthy"},
            observed_at=now,
        )
        assert decision.outcome == "recorded"
        database = Path(directory) / "kernel" / "experience.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            raw = "\n".join(
                row[0] for row in connection.execute("SELECT canonical_json FROM experience_events")
            )
        assert "raw-chat-id-sentinel" not in raw
        for forbidden in ("sleep_debt", "planned_sleep", "deep_sleep", '"phase"'):
            assert forbidden not in raw.lower()

    print("HERMES_ALIVE_KERNEL_AVAILABILITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
