"""Host-authenticated message inspection and withdrawal across restart."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
from alive_kernel import (
    ContentVault, EventEnvelope, ExperienceJournal, LocalIdentityProtector,
    MeaningDocument, MeaningStore, MessageSpeechAct, SemanticAtom, SemanticAtomKind,
    SemanticRenderingError,
)
from alive_kernel.retention_command import handle_memory_command


def main():
    with tempfile.TemporaryDirectory(prefix="semantic-user-controls-") as directory:
        kernel = Path(directory) / "kernel"
        journal = ExperienceJournal(kernel / "experience.sqlite3")
        protector = LocalIdentityProtector(kernel / "identity.key")
        subject = protector.pseudonym("user", "host-user-a")
        vault = ContentVault(kernel / "content-vault", backup_root=kernel / "content-backups")
        store = MeaningStore(journal, content_vault=vault, protector=protector)
        now = datetime.now(timezone.utc)
        journal.append(EventEnvelope(
            event_id="evidence:user-control", event_type="conversation.inbound",
            source="test.host", actor=subject, subject=subject,
            occurred_at=now, observed_at=now, payload={},
        ))
        meaning = store.define(MeaningDocument(
            message_id="user-control", subject=subject, speech_act=MessageSpeechAct.INFORM,
            atoms=(SemanticAtom("fact", SemanticAtomKind.FACT,
                                "PRIVATE-CONTROL-FACT", ("evidence:user-control",)),),
            created_at=now, expires_at=now + timedelta(days=1),
        ), actor=subject)
        meaning_id = meaning.event.event_id

        def command(user, action):
            return handle_memory_command(directory, {"user_id": user, "args": action})

        inspected = command("host-user-a", f"alive message {meaning_id}")
        assert "PRIVATE-CONTROL-FACT" in inspected["message"]
        assert "evidence:user-control" in inspected["message"]
        denied = command("host-user-b", f"alive message {meaning_id}")
        assert "PRIVATE-CONTROL-FACT" not in denied["message"]
        anonymous = handle_memory_command(directory, {"args": f"alive message {meaning_id}"})
        assert "PRIVATE-CONTROL-FACT" not in anonymous["message"]
        command("host-user-b", f"alive withdraw-message {meaning_id}")
        assert store.resolve(meaning_id).atoms[0].text == "PRIVATE-CONTROL-FACT"
        result = command("host-user-a", f"alive withdraw-message {meaning_id}")
        assert "已撤回" in result["message"]
        assert "已撤回" in command(
            "host-user-a", f"alive withdraw-message {meaning_id}"
        )["message"]
        assert "PRIVATE-CONTROL-FACT" not in command(
            "host-user-a", f"alive message {meaning_id}"
        )["message"]
        # Permanent controls do not erase encrypted evidence or promise recall.
        assert vault.resolve_json(
            "message-meaning:user-control", expected_subject=subject,
            expected_purpose="message.meaning", expected_sensitivity=meaning.event.sensitivity,
        )
        second = store.define(MeaningDocument(
            message_id="bad-withdrawal", subject=subject, speech_act=MessageSpeechAct.INFORM,
            atoms=(SemanticAtom("fact", SemanticAtomKind.FACT,
                                "SECOND-PRIVATE-FACT", ("evidence:user-control",)),),
            created_at=now, expires_at=now + timedelta(days=1),
        ), actor=subject)
        journal.append(EventEnvelope(
            event_id="message.meaning_retracted:bad-withdrawal",
            event_type="message.meaning_retracted", source="alive.semantic-control",
            actor=subject, subject=subject, causation_id=second.event.event_id,
            payload={"meaning_event_id": second.event.event_id, "subject": subject,
                     "reason": "explicit_user_withdrawal", "integrity_authenticator": "forged"},
        ))
        for operation in (
            lambda: store.resolve(second.event.event_id),
            lambda: store.retract(second.event.event_id, subject=subject, actor=subject),
        ):
            try:
                operation()
            except SemanticRenderingError as error:
                assert "integrity" in str(error)
            else:
                raise AssertionError("forged withdrawal was accepted or ignored")
        assert handle_memory_command(directory, {"user_id": "host-user-a", "args": "other"}) is None
    print("HERMES_ALIVE_SEMANTIC_USER_CONTROLS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
