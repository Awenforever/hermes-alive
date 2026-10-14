"""Exact consented native ingress, not a guessed feedback target or agent turn.

Only the trusted post_gateway_admission caller may invoke this internal function.
Payload fields alone cannot prove that gateway authorization actually ran.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections.abc import Mapping
import re
from uuid import uuid4

from .content_vault import ContentVault
from .event_store import ExperienceJournal, AppendResult, EventConflictError
from .events import EventEnvelope, Sensitivity
from .privacy import LocalIdentityProtector


class AdmittedInboundError(ValueError):
    pass


def _identifier(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 4096


def _consent(journal, subject):
    rows = tuple(journal.iter_reverse(event_types=("retention.consent_changed",),
                                     subject=subject, max_records=1))
    record = rows[0] if rows else None
    if record is None:
        return None
    event, payload = record.event, record.event.payload
    directions = payload.get("directions")
    if (event.source != "hermes.command.memory" or event.actor != subject
            or event.sensitivity != Sensitivity.PRIVATE or payload.get("enabled") is not True
            or type(payload.get("retention_days")) is not int
            or not 1 <= payload["retention_days"] <= 365
            or payload.get("content_sensitivity") not in ("private", "restricted")
            or payload.get("raw_command_stored") is not False
            or not isinstance(directions, (list, tuple)) or not 1 <= len(directions) <= 2
            or any(value not in ("inbound", "outbound") for value in directions)
            or len(set(directions)) != len(directions) or "inbound" not in directions
            or event.observed_at > datetime.now(timezone.utc)
            or (event.expires_at is not None and event.expires_at <= datetime.now(timezone.utc))):
        return None
    return record


def record_admitted_inbound(shared_dir, values):
    source = values.get("source")
    platform = values.get("platform")
    text = values.get("text")
    if (not isinstance(source, Mapping) or not isinstance(platform, str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", platform)
            or source.get("platform") != platform or not isinstance(text, str)
            or not all(_identifier(value) for value in (
                source.get("user_id"), source.get("chat_id"), values.get("message_id"),
                values.get("session_key")))
            or (source.get("thread_id") is not None and not _identifier(source["thread_id"]))):
        raise AdmittedInboundError("native ingress identity or text unavailable")
    # Reject before creating state. This is not an unbounded alternate text store.
    if len(text) > 1_000_000:
        raise AdmittedInboundError("native ingress exceeds storage boundary")
    root = Path(shared_dir).expanduser().resolve() / "kernel"
    protector = LocalIdentityProtector(root / "identity.key")
    journal = ExperienceJournal(root / "experience.sqlite3")
    subject = protector.pseudonym("user", source["user_id"])
    identity = {"platform":platform, "user":source["user_id"], "chat":source["chat_id"],
                "thread":source.get("thread_id"), "session":values["session_key"],
                "message":values["message_id"]}
    event_id = "conversation.admitted:" + protector.authenticate_json("admitted.identity.v1", identity)
    fingerprint = protector.authenticate_json("admitted.text.v1", text)

    def existing_receipt():
        record = journal.get(event_id)
        if record is None:
            return None
        if (record.event.event_type != "conversation.admitted"
                or record.event.source != "hermes.plugin.post_gateway_admission"
                or record.event.subject != subject or record.event.actor != subject
                or record.event.payload.get("text_fingerprint") != fingerprint):
            raise AdmittedInboundError("native identity reused with conflicting content")
        return AppendResult(record.sequence, record.event, False)

    existing = existing_receipt()
    if existing is not None:
        # Never renew retention or recreate erased/expired copies on replay.
        return existing
    now = datetime.now(timezone.utc)
    consent = _consent(journal, subject)
    payload = {"platform":platform,
        "message_identity":protector.authenticate_json("admitted.message.v1", identity),
        "text_fingerprint":fingerprint, "text_characters":len(text),
        "content_contract":"hermes-post-gateway-admission-v1",
        "content_may_be_truncated":False, "raw_content_stored":False,
        "erasable_content_stored":False, "content_retention_status":"not_authorized",
        "quoted_target_available":False, "feedback_attribution":"unavailable",
        "learning_authority_granted":False, "execution_authority_granted":False,
        "role":"native_input_observation_not_agent_turn"}
    sensitivity = Sensitivity.PRIVATE
    ref, vault = None, None
    if consent is not None and text:
        sensitivity = Sensitivity(consent.event.payload["content_sensitivity"])
        vault = ContentVault(root / "content-vault", backup_root=root / "content-backups")
        ref = vault.put_json({"text":text, "direction":"inbound",
            "source_contract":"hermes-post-gateway-admission-v1", "may_be_truncated":False},
            subject=subject, purpose="conversation.inbound", sensitivity=sensitivity,
            retention_until=now + timedelta(days=consent.event.payload["retention_days"]),
            content_id="admitted-content:" + uuid4().hex)
        payload.update(erasable_content_stored=True, content_retention_status="retained",
                       content=ref.to_event_payload(), consent_event_id=consent.event.event_id)
    def still_consented(connection):
        if ref is None:
            return
        row = connection.execute("SELECT event_id FROM experience_events WHERE subject=? "
            "AND event_type='retention.consent_changed' ORDER BY sequence DESC LIMIT 1", (subject,)).fetchone()
        if row is None or row["event_id"] != consent.event.event_id:
            raise AdmittedInboundError("retention changed during native capture")
        current = datetime.now(timezone.utc)
        if ((consent.event.expires_at is not None and current >= consent.event.expires_at)
                or current >= ref.retention_until):
            raise AdmittedInboundError("native retention expired before publication")
    try:
        return journal.append(EventEnvelope(event_id=event_id, event_type="conversation.admitted",
            source="hermes.plugin.post_gateway_admission", actor=subject, subject=subject,
            correlation_id=protector.pseudonym("session", values["session_key"]),
            observed_at=now, occurred_at=now, sensitivity=sensitivity, payload=payload),
            precondition=still_consented)
    except EventConflictError:
        if ref is not None:
            vault.erase_item(ref.content_id)
        existing = existing_receipt()
        if existing is None:
            raise
        return existing
    except Exception:
        if ref is not None:
            vault.erase_item(ref.content_id)
        raise
