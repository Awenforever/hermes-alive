#!/usr/bin/env python3
"""Discovery becomes traceable opportunity evidence and never a send."""

from __future__ import annotations

from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel import (  # noqa: E402
    AgendaProjection,
    AgendaState,
    DiscoveryCandidate,
    DiscoveryOpportunityError,
    DiscoveryOpportunityIngestor,
    ExperienceJournal,
    Sensitivity,
    candidate_from_legacy,
    canonicalize_discovery_url,
    discovery_shadow_enabled,
    mirror_legacy_discovery_batch,
)


def candidate(title: str, *, observed_at: datetime) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        source="Example Research Feed",
        external_id="paper-42",
        title=title,
        url="https://Example.COM/paper/42?utm_source=test&b=2&a=1#abstract",
        summary="Private discovery summary sentinel",
        published_at=observed_at - timedelta(hours=2),
        observed_at=observed_at,
        confidence=0.83,
        priority_hint=0.71,
        attributes={"lane": "research", "authors": ["Private Author"]},
    )


def main() -> int:
    now = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory(prefix="alive-kernel-discovery-") as directory:
        path = Path(directory)
        journal = ExperienceJournal(path / "kernel.sqlite3")
        ingestor = DiscoveryOpportunityIngestor(journal)

        assert canonicalize_discovery_url(
            "https://Example.COM/x?utm_medium=noise&z=2&a=1#frag"
        ) == "https://example.com/x?a=1&z=2"
        # URL validation never reads these resources. Synthetic destinations
        # test the scheme boundary without suggesting access to a host secret.
        for non_web_url in (
            "file:///synthetic/non-web-resource",
            "ftp://example.invalid/resource",
            "ssh://example.invalid/resource",
            "data:text/plain,synthetic",
        ):
            try:
                canonicalize_discovery_url(non_web_url)
            except DiscoveryOpportunityError:
                pass
            else:
                raise AssertionError("non-web URL crossed discovery boundary")

        first = ingestor.ingest(candidate("First title", observed_at=now), subject="user:test")
        assert first.observation_created is True
        assert first.material_update is False
        assert first.agenda_decision.outcome == "active"

        # Reconstructing the same collector item later is idempotent even though
        # its default retention and ranking hint would otherwise differ.
        retry = ingestor.ingest(
            DiscoveryCandidate(
                source="Example Research Feed",
                external_id="paper-42",
                title="First title",
                url="https://example.com/paper/42?a=1&b=2",
                summary="Private discovery summary sentinel",
                published_at=now - timedelta(hours=2),
                observed_at=now + timedelta(minutes=5),
                confidence=0.83,
                priority_hint=0.2,
                attributes={"authors": ["Private Author"], "lane": "research"},
            ),
            subject="user:test",
        )
        assert retry.observation_event_id == first.observation_event_id
        assert retry.observation_created is False

        update = ingestor.ingest(
            candidate("Corrected title", observed_at=now + timedelta(hours=1)),
            subject="user:test",
        )
        assert update.material_update is True
        assert update.superseded_agenda_item_id == first.agenda_item_id
        agenda = AgendaProjection(journal, content_vault=ingestor.vault)
        dismissed = agenda.list_items(
            clearance=Sensitivity.PRIVATE,
            states=(AgendaState.DISMISSED,),
            as_of=now + timedelta(hours=2),
        )
        assert [item.item_id for item in dismissed] == [first.agenda_item_id]
        active = agenda.list_items(
            clearance=Sensitivity.PRIVATE,
            states=(AgendaState.ACTIVE,),
            as_of=now + timedelta(hours=2),
        )
        assert [item.item_id for item in active] == [update.agenda_item_id]

        # Competing material updates serialize across the vault-backed causal
        # write. Exactly one latest version remains active.
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent_results = list(
                pool.map(
                    lambda title: ingestor.ingest(
                        candidate(title, observed_at=now + timedelta(hours=2)),
                        subject="user:test",
                    ),
                    ("Concurrent correction A", "Concurrent correction B"),
                )
            )
        active = agenda.list_items(
            clearance=Sensitivity.PRIVATE,
            states=(AgendaState.ACTIVE,),
            as_of=now + timedelta(hours=3),
        )
        assert len(active) == 1
        assert active[0].item_id in {item.agenda_item_id for item in concurrent_results}

        failure = ingestor.record_source_failure(
            subject="user:test",
            source="private-source-name",
            error_class="TimeoutError",
            observed_at=now,
        )
        assert failure.event.event_type == "discovery.source_failed"
        assert "private-source-name" not in failure.event.canonical_json()
        assert len(active) == 1  # source health did not create an opportunity

        legacy = candidate_from_legacy(
            {
                "source": "rss",
                "id": "legacy-1",
                "title": "Legacy item",
                "url": "https://example.com/legacy",
                "description": "legacy summary",
                "score": 0.9,
                "lane": "news",
            },
            observed_at=now,
        )
        assert legacy.priority_hint == 0.9
        assert legacy.attributes == {"lane": "news"}

        # Neither private discovery text nor URLs may enter the journal.
        with closing(sqlite3.connect(journal.path)) as connection:
            raw = "\n".join(row[0] for row in connection.execute("SELECT canonical_json FROM experience_events"))
        for sentinel in (
            "Private discovery summary sentinel",
            "Private Author",
            "Example Research Feed",
            "https://example.com/paper/42",
        ):
            assert sentinel not in raw

        before = ingestor.current(
            "entity:" + ingestor.vault.digest_json(
                candidate("Corrected title", observed_at=now + timedelta(hours=1)).entity_document("user:test")
            )[:40]
        )
        assert before is not None
        ingestor.rebuild_projection(batch_size=1)
        assert ingestor.current(before.entity_fingerprint) == before

        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute(
                "UPDATE discovery_entities_v1 SET agenda_item_id='tampered' WHERE entity_fingerprint=?",
                (before.entity_fingerprint,),
            )
            connection.commit()
        assert ingestor.validate_projection() is False
        repaired = DiscoveryOpportunityIngestor(journal, content_vault=ingestor.vault)
        assert repaired.validate_projection() is True
        assert repaired.current(before.entity_fingerprint) == before
        with closing(sqlite3.connect(journal.path)) as connection:
            connection.execute(
                "DELETE FROM discovery_entities_v1 WHERE entity_fingerprint=?",
                (before.entity_fingerprint,),
            )
            connection.commit()
        assert repaired.validate_projection() is False
        repaired = DiscoveryOpportunityIngestor(journal, content_vault=ingestor.vault)
        assert repaired.current(before.entity_fingerprint) == before

        # This entire module has no route, adapter, delivery or outbox API.
        assert not any(
            hasattr(ingestor, name)
            for name in ("send", "send_text", "send_rich", "reserve", "dispatch")
        )

    assert discovery_shadow_enabled({}) is False
    assert discovery_shadow_enabled(
        {
            "HERMES_ALIVE_KERNEL_SHADOW_ENABLED": "true",
            "HERMES_ALIVE_DISCOVERY_KERNEL_SHADOW_ENABLED": "false",
        }
    ) is False
    with tempfile.TemporaryDirectory(prefix="alive-discovery-shadow-") as directory:
        report = mirror_legacy_discovery_batch(
            directory,
            raw_subject="raw-chat-id-must-not-persist",
            discovery_context={
                "external": [
                    {
                        "source": "shadow-rss",
                        "id": "shadow-1",
                        "title": "Shadow item",
                        "url": "https://example.com/shadow",
                        "description": "shadow body sentinel",
                        "score": 0.8,
                    },
                    {"source": "broken", "title": "missing URL"},
                ],
                "source_health": {
                    "shadow-rss": {"ok": True, "fetched": 1},
                    "private-failed-source": {"ok": False, "error": "TimeoutError"},
                },
            },
            observed_at=now,
        )
        assert report.observed == 1
        assert report.rejected == 1
        assert report.source_failures == 1
        raw_db = Path(directory) / "kernel" / "experience.sqlite3"
        with closing(sqlite3.connect(raw_db)) as connection:
            raw = "\n".join(
                row[0] for row in connection.execute("SELECT canonical_json FROM experience_events")
            )
        for sentinel in (
            "raw-chat-id-must-not-persist",
            "shadow body sentinel",
            "private-failed-source",
        ):
            assert sentinel not in raw

    print("HERMES_ALIVE_KERNEL_DISCOVERY_OPPORTUNITIES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
