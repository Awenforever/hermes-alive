"""Owner-only bounded pagination with current content states and no fake sends."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import sqlite3
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
from alive_kernel import (
    ContentVault, EventEnvelope, ExperienceJournal, LocalIdentityProtector,
    MeaningDocument, MeaningStore, MessageSpeechAct, SemanticAtom, SemanticAtomKind,
    SemanticRenderingError,
)
from alive_kernel.semantic_history import SemanticHistory
from alive_kernel.retention_command import handle_memory_command


def main():
    with tempfile.TemporaryDirectory(prefix="semantic-history-") as directory:
        kernel = Path(directory) / "kernel"
        journal = ExperienceJournal(kernel / "experience.sqlite3")
        protector = LocalIdentityProtector(kernel / "identity.key")
        owner, foreign = (protector.pseudonym("user", name) for name in ("owner", "foreign"))
        vault = ContentVault(kernel / "content-vault", backup_root=kernel / "content-backups")
        meanings = MeaningStore(journal, content_vault=vault, protector=protector)
        history = SemanticHistory(meanings)
        now = datetime.now(timezone.utc)
        for subject in (owner, foreign):
            journal.append(EventEnvelope(
                event_id=f"source:{subject}", event_type="conversation.inbound",
                source="test.host", actor=subject, subject=subject,
                occurred_at=now, observed_at=now, payload={},
            ))

        def define(index, subject=owner):
            return meanings.define(MeaningDocument(
                message_id=f"history-{subject}-{index}", subject=subject,
                speech_act=MessageSpeechAct.INFORM,
                atoms=(SemanticAtom("fact", SemanticAtomKind.FACT,
                                    f"PRIVATE-{subject}-{index}", (f"source:{subject}",)),),
                created_at=now, expires_at=now + timedelta(days=1),
            ), actor=subject)

        owned, others = [], []
        for index in range(25):
            owned.append(define(index))
            others.append(define(index, foreign))
        first = history.page(subject=owner, limit=7)
        assert len(first.items) == 7
        assert all(item.state == "available" and foreign not in item.preview for item in first.items)
        assert [item.event_id for item in first.items] == [row.event.event_id for row in reversed(owned[-7:])]
        define("new-after-first-page")
        ids = [item.event_id for item in first.items]
        cursor = first.next_before_event_id
        while cursor:
            page = history.page(subject=owner, before_event_id=cursor, limit=7)
            ids.extend(item.event_id for item in page.items)
            cursor = page.next_before_event_id
        assert ids == [row.event.event_id for row in reversed(owned)]
        assert len(set(ids)) == 25
        for cursor in (others[-1].event.event_id, "missing", f"source:{owner}"):
            try:
                history.page(subject=owner, before_event_id=cursor)
            except SemanticRenderingError:
                pass
            else:
                raise AssertionError("foreign/non-message cursor accepted")
        with closing(sqlite3.connect(journal.path)) as connection:
            plan = connection.execute(
                "EXPLAIN QUERY PLAN SELECT sequence, canonical_json, integrity_hash FROM experience_events "
                "WHERE subject=? AND event_type=? AND sequence < ? ORDER BY sequence DESC LIMIT ?",
                (owner, "message.meaning_defined", 10000, 10),
            ).fetchall()
        assert "idx_experience_subject_type_sequence" in repr(plan)
        for invalid_limit in (0, 21, True, "10"):
            try:
                history.page(subject=owner, limit=invalid_limit)
            except SemanticRenderingError:
                pass
            else:
                raise AssertionError("invalid page bound accepted")

        withdrawn_id = owned[-1].event.event_id
        meanings.retract(withdrawn_id, subject=owner, actor=owner)
        corrected_id = owned[-2].event.event_id
        corrected = meanings.correct_atom(
            corrected_id, subject=owner, actor=owner, atom_id="fact",
            kind=SemanticAtomKind.FACT, text="PRIVATE-REPLACEMENT",
        )
        erased_id = owned[-3].event.event_id
        vault.erase_item(owned[-3].event.payload["content"]["content_id"])
        pending_id = owned[-4].event.event_id
        with patch.object(meanings, "define", side_effect=RuntimeError("injected")):
            try:
                meanings.correct_atom(pending_id, subject=owner, actor=owner,
                                      atom_id="fact", kind=SemanticAtomKind.FACT, text="PRIVATE-PENDING")
            except RuntimeError:
                pass
        states = {item.event_id: item for item in history.page(subject=owner, limit=20).items}
        assert states[withdrawn_id].state == "withdrawn" and not states[withdrawn_id].preview
        assert states[corrected_id].state == "corrected" and not states[corrected_id].preview
        assert states[corrected_id].replacement_event_id == corrected.event.event_id
        assert states[erased_id].state == "unavailable" and not states[erased_id].preview
        assert states[pending_id].state == "correcting" and not states[pending_id].preview
        assert history.page(subject=owner, as_of=now + timedelta(days=2)).items[0].state == "expired"
        result = handle_memory_command(directory, {"user_id": "owner", "args": "alive messages"})
        assert "不代表已发送" in result["message"] and "下一页" in result["message"]
        assert "PRIVATE-REPLACEMENT" in result["message"] and foreign not in result["message"]
        result = handle_memory_command(directory, {"user_id": "foreign", "args": f"alive messages {withdrawn_id}"})
        assert "PRIVATE" not in result["message"]
        assert "PRIVATE" not in handle_memory_command(directory, {"args": "alive messages"})["message"]
        vault.erase_subject(owner)
        assert not any(item.preview for item in history.page(subject=owner, limit=20).items)
        # Bad semantic authentication hides content, but must not strand older
        # records: a cursor grants only an owner-filtered seek, never authority.
        forged = EventEnvelope(
            event_id="message.meaning:forged", event_type="message.meaning_defined",
            source="alive.semantic-rendering", actor=owner, subject=owner,
            payload={"integrity_authenticator": "forged", "message_id": "forged"},
        )
        journal.append(forged)
        page = history.page(subject=owner, limit=1)
        assert page.items[0].state == "unavailable" and not page.items[0].preview
        assert page.next_before_event_id == forged.event_id
        assert history.page(subject=owner, before_event_id=page.next_before_event_id, limit=1).items
        print("HERMES_ALIVE_SEMANTIC_HISTORY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
