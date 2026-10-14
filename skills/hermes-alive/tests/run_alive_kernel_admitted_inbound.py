#!/usr/bin/env python3
"""Synthetic native capture, consent, replay, failure and registration checks."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import os
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills/hermes-alive/hooks"))
from alive_kernel.admitted_inbound import record_admitted_inbound, AdmittedInboundError
from alive_kernel.content_vault import ContentVault, ContentUnavailableError
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.events import Sensitivity
from alive_kernel.privacy import LocalIdentityProtector
from alive_kernel.retention import RetentionProjection
from run_alive_kernel_tool_receipts import _load_plugin, FakePluginContext


def value(message="m1", user="synthetic-user"):
    return {"platform":"weixin", "session_key":"synthetic-session", "message_id":message,
        "source":{"platform":"weixin", "user_id":user, "chat_id":"synthetic-chat", "thread_id":None},
        "text":"  Synthetic full input\n\n" + "x" * 1200 + "\n  ",
        "reply_to_message_id":"untrusted-extra-not-forwarded-by-SDK"}


def runtime(shared):
    root = shared / "kernel"
    journal = ExperienceJournal(root / "experience.sqlite3")
    protector = LocalIdentityProtector(root / "identity.key")
    vault = ContentVault(root / "content-vault", backup_root=root / "content-backups")
    return journal, protector, vault, RetentionProjection(journal, content_vault=vault)


def consent(policy, subject, enabled=True, directions=("inbound",)):
    return policy.append_consent(subject=subject, actor=subject, enabled=enabled,
        retention_days=2, directions=directions, sensitivity=Sensitivity.PRIVATE)


def run():
    with tempfile.TemporaryDirectory(prefix="alive-native-input-") as directory:
        base = Path(directory)
        invalid = value()
        invalid["source"]["user_id"] = None
        try: record_admitted_inbound(base / "invalid", invalid)
        except AdmittedInboundError: pass
        else: raise AssertionError("missing owner accepted")
        assert not (base / "invalid").exists()

        shared = base / "main"
        first = record_admitted_inbound(shared, value())
        assert first.event.payload["erasable_content_stored"] is False
        assert first.event.payload["quoted_target_available"] is False
        assert first.event.payload["principal_kind"] == "not_exposed_by_host"
        assert first.event.payload["origin_contract"] == "normalized_gateway_event_not_wire_message"
        assert first.event.payload["wire_message_count"] is None
        assert first.event.event_type == "conversation.admitted"
        journal, protector, vault, policy = runtime(shared)
        subject = protector.pseudonym("user", "synthetic-user")
        allowed = consent(policy, subject)
        # Canonical consent works even before its projector consumes it.
        replay = record_admitted_inbound(shared, value())
        assert not replay.created and replay.event == first.event
        capture = record_admitted_inbound(shared, value("m2"))
        assert capture.event.payload["consent_event_id"] == allowed.event.event_id
        reference = capture.event.payload["content"]
        text = vault.resolve_json(reference["content_id"], expected_subject=subject,
            expected_purpose="conversation.inbound", expected_sensitivity=Sensitivity.PRIVATE)
        assert text["text"] == value()["text"] and text["may_be_truncated"] is False
        assert not capture.event.causation_id
        assert not capture.event.payload["learning_authority_granted"]
        assert not capture.event.payload["execution_authority_granted"]
        # Ordinary preview is not promoted or silently joined to this event.
        assert not journal.read(event_type="conversation.inbound")
        journal_text = "\n".join(row.event.canonical_json() for row in journal.read())
        for sentinel in ("Synthetic full input", "synthetic-user", "synthetic-session", "untrusted-extra"):
            assert sentinel not in journal_text
        changed = value("m2"); changed["text"] += "different"
        try: record_admitted_inbound(shared, changed)
        except AdmittedInboundError: pass
        else: raise AssertionError("same identity accepted conflicting text")
        vault.erase_item(reference["content_id"])
        assert not record_admitted_inbound(shared, value("m2")).created
        try: vault.resolve_json(reference["content_id"])
        except ContentUnavailableError: pass
        else: raise AssertionError("replay recreated forgotten input")
        assert record_admitted_inbound(shared, value("other", "other-user")).event.payload["erasable_content_stored"] is False
        consent(policy, subject, directions=("outbound",))
        assert record_admitted_inbound(shared, value("outbound-only")).event.payload["erasable_content_stored"] is False
        consent(policy, subject, enabled=False)
        assert record_admitted_inbound(shared, value("revoked")).event.payload["erasable_content_stored"] is False

        race = base / "race"
        journal2, protector2, vault2, policy2 = runtime(race)
        subject2 = protector2.pseudonym("user", "synthetic-user")
        consent(policy2, subject2)
        original_put = ContentVault.put_json
        def revoke_after_put(instance, *args, **kwargs):
            ref = original_put(instance, *args, **kwargs)
            consent(policy2, subject2, enabled=False)
            return ref
        with patch.object(ContentVault, "put_json", revoke_after_put):
            try: record_admitted_inbound(race, value())
            except AdmittedInboundError: pass
            else: raise AssertionError("revoked capture appended")
        assert not journal2.read(event_type="conversation.admitted")
        with closing(vault2._connect()) as db:
            assert db.execute("SELECT COUNT(*) FROM content_items").fetchone()[0] == 0

        concurrent = base / "concurrent"
        journal3, protector3, vault3, policy3 = runtime(concurrent)
        subject3 = protector3.pseudonym("user", "synthetic-user")
        consent(policy3, subject3)
        barrier = threading.Barrier(2)
        def put_with_barrier(instance, *args, **kwargs):
            ref = original_put(instance, *args, **kwargs)
            barrier.wait(timeout=10)
            return ref
        with patch.object(ContentVault, "put_json", put_with_barrier):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = tuple(pool.map(lambda _:record_admitted_inbound(concurrent, value()), range(2)))
        assert sum(result.created for result in results) == 1
        assert len(journal3.read(event_type="conversation.admitted")) == 1
        with closing(vault3._connect()) as db:
            assert db.execute("SELECT COUNT(*) FROM content_items").fetchone()[0] == 1

        # Installed plugin callback remains optional and never claims a message.
        old = {key:os.environ.get(key) for key in ("HERMES_ALIVE_SHARED_DIR", "HERMES_ALIVE_KERNEL_SHADOW_ENABLED")}
        try:
            os.environ["HERMES_ALIVE_SHARED_DIR"] = str(base / "registration")
            os.environ["HERMES_ALIVE_KERNEL_SHADOW_ENABLED"] = "false"
            plugin = _load_plugin(); ctx = FakePluginContext(); plugin.register(ctx)
            callback = ctx.hooks["post_gateway_admission"]
            assert callback(**value()) is None
            assert not (base / "registration").exists()
            os.environ["HERMES_ALIVE_KERNEL_SHADOW_ENABLED"] = "true"
            assert callback(**value()) is None
            assert callback(text="bad identity") is None
            installed = ExperienceJournal(base / "registration/kernel/experience.sqlite3")
            assert len(installed.read(event_type="conversation.admitted")) == 1
        finally:
            for key, previous in old.items():
                if previous is None: os.environ.pop(key, None)
                else: os.environ[key] = previous
    print("HERMES_ALIVE_ADMITTED_INBOUND_OK")


if __name__ == "__main__":
    run()
