"""Owner corrections preserve provenance and recover without reviving old text."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
from alive_kernel import (
    ContentVault, EventEnvelope, ExperienceJournal, LocalIdentityProtector,
    MeaningDocument, MeaningStore, MessageSpeechAct, SemanticAtom, SemanticAtomKind,
    SemanticRenderingError,
)
from alive_kernel.retention_command import handle_memory_command


def main():
    with tempfile.TemporaryDirectory(prefix="semantic-correction-") as directory:
        kernel = Path(directory) / "kernel"
        journal = ExperienceJournal(kernel / "experience.sqlite3")
        protector = LocalIdentityProtector(kernel / "identity.key")
        subject = protector.pseudonym("user", "owner")
        vault = ContentVault(kernel / "content-vault", backup_root=kernel / "content-backups")
        store = MeaningStore(journal, content_vault=vault, protector=protector)
        now = datetime.now(timezone.utc)
        journal.append(EventEnvelope(
            event_id="correction:source", event_type="conversation.inbound", source="test.host",
            actor=subject, subject=subject, occurred_at=now, observed_at=now, payload={},
        ))

        def define(message_id):
            return store.define(MeaningDocument(
                message_id=message_id, subject=subject, speech_act=MessageSpeechAct.REMIND,
                atoms=(
                    SemanticAtom("deadline", SemanticAtomKind.DEADLINE, "PRIVATE: 2026-10-15 09:00",
                                 ("correction:source",), ("2026-10-15 09:00",)),
                    SemanticAtom("caveat", SemanticAtomKind.CAVEAT, "PRIVATE-CAVEAT-UNCHANGED",
                                 ("correction:source",)),
                ), created_at=now, expires_at=now + timedelta(days=1),
            ), actor=subject)

        def correction(event_id, **overrides):
            args = dict(subject=subject, actor=subject, atom_id="deadline",
                        kind=SemanticAtomKind.DEADLINE, text="PRIVATE: 2026-10-16 09:00")
            args.update(overrides)
            return store.correct_atom(event_id, **args)

        def rejected(call, fragment):
            try:
                call()
            except SemanticRenderingError as error:
                assert fragment in str(error), str(error)
            else:
                raise AssertionError("invalid correction succeeded")

        source = define("normal").event.event_id
        rejected(lambda: correction(source, subject="user:foreign", actor="user:foreign"), "unavailable")
        rejected(lambda: correction(source, atom_id="missing"), "atom")
        rejected(lambda: correction(source, text=""), "empty")
        corrected = correction(source)
        document = store.resolve(corrected.event.event_id)
        assert document.expires_at == now + timedelta(days=1)
        assert document.created_at > now
        assert document.speech_act == MessageSpeechAct.REMIND
        assert document.atoms[0].protected_literals == ("PRIVATE: 2026-10-16 09:00",)
        assert document.atoms[1].text == "PRIVATE-CAVEAT-UNCHANGED"
        assert document.atoms[1].evidence_event_ids == ("correction:source",)
        assert document.atoms[0].evidence_event_ids == ("message.meaning_retracted:normal",)
        assert correction(source).event.event_id == corrected.event.event_id
        rejected(lambda: store.resolve(source), "withdrawn")
        rejected(lambda: correction(source, text="different correction"), "different")
        second = correction(corrected.event.event_id, kind=SemanticAtomKind.CAVEAT,
                            text="PRIVATE-USER-CAVEAT")
        assert store.resolve(second.event.event_id).atoms[0].kind == SemanticAtomKind.CAVEAT
        rejected(lambda: correction(source), "withdrawn")

        before = define("before-withdrawal").event.event_id
        original_append = journal.append
        def fail_before_marker(event):
            if event.event_type == "message.meaning_retracted":
                raise RuntimeError("injected-before-withdrawal")
            return original_append(event)
        with patch.object(journal, "append", side_effect=fail_before_marker):
            try:
                correction(before)
            except RuntimeError:
                pass
            else:
                raise AssertionError("fault was not injected")
        assert store.resolve(before)
        assert correction(before)

        interrupted = define("after-withdrawal").event.event_id
        with patch.object(store, "define", side_effect=RuntimeError("injected-after-withdrawal")):
            try:
                correction(interrupted)
            except RuntimeError:
                pass
            else:
                raise AssertionError("fault was not injected")
        rejected(lambda: store.resolve(interrupted), "withdrawn")
        reopened = MeaningStore(journal, content_vault=vault, protector=protector)
        recovered = reopened.correct_atom(
            interrupted, subject=subject, actor=subject, atom_id="deadline",
            kind=SemanticAtomKind.DEADLINE, text="PRIVATE: 2026-10-16 09:00",
        )
        assert reopened.resolve(recovered.event.event_id)

        for same_request in (True, False):
            parallel_id = define(f"parallel-{same_request}").event.event_id
            barrier = Barrier(2)
            def append_at_barrier(event):
                if event.event_type == "message.meaning_retracted":
                    barrier.wait(timeout=10)
                return original_append(event)
            def worker(text):
                try:
                    return correction(parallel_id, text=text).event.event_id
                except SemanticRenderingError:
                    return None
            with patch.object(journal, "append", side_effect=append_at_barrier):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(worker, "PRIVATE-PARALLEL-A"),
                               pool.submit(worker, "PRIVATE-PARALLEL-A" if same_request else "PRIVATE-PARALLEL-B")]
                    results = [future.result(timeout=15) for future in futures]
            assert sum(result is not None for result in results) == (2 if same_request else 1)
            assert len({result for result in results if result}) == 1
            rejected(lambda: store.resolve(parallel_id), "withdrawn")

        command_source = define("command").event.event_id
        result = handle_memory_command(directory, {
            "user_id": "owner", "args": f"alive correct-message {command_source} caveat caveat\nPRIVATE-LINE-ONE\n\nPRIVATE-LINE-TWO",
        })
        assert "已修正" in result["message"]
        withdrawal = journal.get("message.meaning_retracted:command")
        command_doc = store.resolve(withdrawal.event.payload["replacement_event_id"])
        assert command_doc.atoms[1].text == "PRIVATE-LINE-ONE\n\nPRIVATE-LINE-TWO"
        inspected = handle_memory_command(directory, {
            "user_id": "owner", "args": f"alive message {withdrawal.event.payload['replacement_event_id']}",
        })
        assert "`caveat`" in inspected["message"]
        text = journal.path.read_bytes().decode("utf-8", errors="ignore")
        assert "PRIVATE" not in text
        assert "action_authority_granted" in text
        erased = define("erased-preparation").event.event_id
        with patch.object(store, "define", side_effect=RuntimeError("injected-after-withdrawal")):
            try:
                correction(erased)
            except RuntimeError:
                pass
        vault.erase_subject(subject)
        rejected(lambda: correction(erased), "content is unavailable")
        rejected(lambda: store.resolve(recovered.event.event_id), "content is unavailable")
    print("HERMES_ALIVE_SEMANTIC_USER_CORRECTION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
