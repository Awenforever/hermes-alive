"""Presentation policy cannot become truth, relationship, or send authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    EventEnvelope,
    ExperienceJournal,
    PresentationAuthority,
    PresentationDimension,
    PresentationPreference,
    PresentationProjection,
    Sensitivity,
    mirror_legacy_voice,
    presentation_shadow_enabled,
)


@dataclass
class LegacyVoice:
    verbosity: float = 0.8
    formality: float = 0.2
    humor_dry: float = 0.7
    humor_absurd: float = 0.4
    curiosity: float = 0.9
    warmth: float = 0.8
    quirkiness: float = 0.6
    emoji_usage: float = 0.1
    self_disclosure: float = 0.3


def main() -> int:
    now = datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc)
    subject = "user:presentation"
    with tempfile.TemporaryDirectory(prefix="alive-presentation-") as directory:
        shared = Path(directory)
        journal = ExperienceJournal(shared / "kernel" / "experience.sqlite3")
        projection = PresentationProjection(journal)

        inbound = EventEnvelope(
            event_id="conversation:presentation-explicit",
            event_type="conversation.inbound",
            source="test.channel",
            actor=subject,
            subject=subject,
            occurred_at=now,
            observed_at=now,
            sensitivity=Sensitivity.PRIVATE,
            payload={"raw_content_stored": False},
        )
        journal.append(inbound)
        explicit = PresentationPreference(
            subject=subject,
            dimension=PresentationDimension.VERBOSITY,
            value=0.2,
            authority=PresentationAuthority.USER_EXPLICIT,
            reason_code="user_requested_brief",
            valid_from=now,
            valid_until=now + timedelta(days=30),
            source_event_id=inbound.event_id,
        )
        decision = projection.apply(
            projection.append_preference(explicit, actor=subject, observed_at=now)
        )
        assert decision.outcome == "recorded"

        # A caller cannot self-assign explicit authority using another actor.
        bad = PresentationPreference(
            subject=subject,
            dimension=PresentationDimension.FORMALITY,
            value=1.0,
            authority=PresentationAuthority.USER_EXPLICIT,
            reason_code="forged_explicit",
            valid_from=now + timedelta(seconds=1),
            valid_until=now + timedelta(days=30),
            source_event_id=inbound.event_id,
            preference_id="preference:forged",
        )
        rejected = projection.apply(
            projection.append_preference(
                bad, actor="system:pretending-user", observed_at=now + timedelta(seconds=1)
            )
        )
        assert rejected.outcome == "rejected" and rejected.reason == "invalid_authority"

        reflection_proposal = EventEnvelope(
            event_id="reflection.proposal:reflection:presentation",
            event_type="reflection.proposed",
            source="alive.reflection",
            actor="system:alive-reflection",
            subject=subject,
            occurred_at=now + timedelta(seconds=2),
            observed_at=now + timedelta(seconds=2),
            sensitivity=Sensitivity.PRIVATE,
            payload={"reflection_id": "reflection:presentation"},
        )
        journal.append(reflection_proposal)
        reflection_approval = EventEnvelope(
            event_id="conversation:presentation-reflection-approval",
            event_type="conversation.inbound",
            source="test.channel",
            actor=subject,
            subject=subject,
            occurred_at=now + timedelta(seconds=3),
            observed_at=now + timedelta(seconds=3),
            sensitivity=Sensitivity.PRIVATE,
            payload={"raw_content_stored": False},
        )
        journal.append(reflection_approval)
        accepted_reflection = EventEnvelope(
            event_id="reflection.review:presentation",
            event_type="reflection.reviewed",
            source="alive.reflection",
            actor=subject,
            subject=subject,
            causation_id=reflection_approval.event_id,
            occurred_at=now + timedelta(seconds=4),
            observed_at=now + timedelta(seconds=4),
            sensitivity=Sensitivity.PRIVATE,
            payload={
                "reflection_id": "reflection:presentation",
                "review": "accept",
                "source_event_id": reflection_approval.event_id,
            },
        )
        journal.append(accepted_reflection)
        advisory = PresentationPreference(
            subject=subject,
            dimension=PresentationDimension.FORMALITY,
            value=0.9,
            authority=PresentationAuthority.LEARNED_ADVISORY,
            reason_code="reviewed_style_estimate",
            valid_from=now + timedelta(seconds=4),
            valid_until=now + timedelta(days=7),
            source_event_id=accepted_reflection.event_id,
        )
        advisory_decision = projection.apply(
            projection.append_preference(
                advisory,
                actor="system:alive-presentation",
                observed_at=now + timedelta(seconds=4),
            )
        )
        assert advisory_decision.reason == "advisory_only"

        # Legacy values are retained only for comparison and never override.
        env = {
            "HERMES_ALIVE_KERNEL_SHADOW_ENABLED": "true",
            "HERMES_ALIVE_PRESENTATION_SHADOW_ENABLED": "true",
        }
        assert presentation_shadow_enabled(env)
        first = mirror_legacy_voice(
            shared, raw_subject="external-chat-123", voice=LegacyVoice(), observed_at=now
        )
        second = mirror_legacy_voice(
            shared,
            raw_subject="external-chat-123",
            voice=LegacyVoice(),
            observed_at=now + timedelta(minutes=20),
        )
        assert len(first) == 9
        assert all(item.reason == "advisory_only" for item in first)
        assert tuple(item.event_id for item in first) == tuple(item.event_id for item in second)

        plan = projection.resolve(subject, as_of=now + timedelta(minutes=1))
        assert plan.values["verbosity"] == 0.2
        assert plan.values["formality"] == 0.5
        assert plan.explicit_dimensions == ("verbosity",)
        assert len(plan.advisory_event_ids) == 1
        assert plan.permits_action is False
        assert plan.may_change_semantics is False
        assert plan.may_choose_route is False
        assert plan.integrity_ok

        # Projection replay is deterministic.
        projection.rebuild()
        replayed = projection.resolve(subject, as_of=now + timedelta(minutes=1))
        assert replayed == plan

        # Row deletion plus forged count cannot silently alter style.
        connection = sqlite3.connect(journal.path)
        try:
            connection.execute(
                "DELETE FROM presentation_preferences_v1 WHERE authority=?",
                (PresentationAuthority.USER_EXPLICIT.value,),
            )
            connection.execute(
                "UPDATE presentation_projection_v1 SET preference_count=(SELECT COUNT(*) FROM presentation_preferences_v1)"
            )
            connection.commit()
        finally:
            connection.close()
        assert not projection.validate_projection()
        degraded = projection.resolve(subject, as_of=now + timedelta(minutes=1))
        # Reads fail closed to neutral style; startup/recovery performs repair.
        assert not degraded.integrity_ok and degraded.values["verbosity"] == 0.5
        projection.rebuild()
        repaired = projection.resolve(subject, as_of=now + timedelta(minutes=1))
        assert repaired.integrity_ok and repaired.values["verbosity"] == 0.2

        # Stored payloads contain no raw platform subject or relationship fiction.
        for record in journal.iter_replay():
            if record.event.event_type != "presentation.preference_observed":
                continue
            text = record.event.canonical_json()
            assert "external-chat-123" not in text
            assert "relationship_stage" not in text
            assert "social_urge" not in text
            assert record.event.payload["truth_claimed"] is False
            assert record.event.payload["semantic_change_allowed"] is False

    print("HERMES_ALIVE_KERNEL_PRESENTATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
