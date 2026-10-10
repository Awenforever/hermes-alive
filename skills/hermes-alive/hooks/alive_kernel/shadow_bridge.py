"""Shadow-only bridge from Hermes hook events to the experience journal."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from .event_store import AppendResult, ExperienceJournal
from .events import EventEnvelope, Sensitivity
from .content_vault import ContentVault
from .privacy import LocalIdentityProtector, assert_no_obvious_secret, structural_hook_payload
from .retention import RetentionDirection, RetentionProjection


logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "gateway:startup": "lifecycle.gateway_started",
    "session:start": "session.started",
    "session:end": "session.ended",
    "session:reset": "session.reset",
    "agent:start": "conversation.inbound",
    "agent:step": "tool.round_observed",
    "agent:end": "session.agent_ended",
}


def shadow_enabled(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    return str(values.get("HERMES_ALIVE_KERNEL_SHADOW_ENABLED", "false")).strip().lower() in {
        "1", "true", "yes", "on", "enabled",
    }


class ShadowKernelBridge:
    """Mirror structural facts without participating in current decisions."""

    def __init__(self, shared_dir: str | Path) -> None:
        self.kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
        self.protector = LocalIdentityProtector(self.kernel_dir / "identity.key")
        self.journal = ExperienceJournal(self.kernel_dir / "experience.sqlite3")
        self.content_vault = ContentVault(
            self.kernel_dir / "content-vault",
            backup_root=self.kernel_dir / "content-backups",
        )
        self.retention = RetentionProjection(
            self.journal, content_vault=self.content_vault
        )
        self._initialize_ingestion_state()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.journal.path, timeout=10.0, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize_ingestion_state(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS shadow_turn_counters_v1 (
                    correlation_id TEXT PRIMARY KEY,
                    next_turn INTEGER NOT NULL CHECK(next_turn >= 1)
                );
                CREATE TABLE IF NOT EXISTS shadow_open_turns_v1 (
                    correlation_id TEXT PRIMARY KEY,
                    start_event_id TEXT NOT NULL UNIQUE,
                    message_digest TEXT NOT NULL,
                    started_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shadow_recent_ends_v1 (
                    correlation_id TEXT PRIMARY KEY,
                    message_digest TEXT NOT NULL,
                    end_event_id TEXT NOT NULL UNIQUE,
                    ended_at TEXT NOT NULL
                );
                COMMIT;
                """
            )

    @staticmethod
    def _bounded_length(value: Any) -> str:
        length = len(str(value or ""))
        if length == 0:
            return "empty"
        if length <= 32:
            return "1-32"
        if length <= 128:
            return "33-128"
        if length <= 500:
            return "129-500"
        return "501+"

    def _event_details(
        self, event_name: str, context: Mapping[str, Any], payload: dict[str, Any]
    ) -> None:
        if event_name == "agent:start":
            message = context.get("message")
            payload["message_present"] = bool(str(message or ""))
            payload["message_length_bucket"] = self._bounded_length(message)
        elif event_name == "agent:step":
            try:
                iteration = max(0, min(int(context.get("iteration", 0)), 1_000_000))
            except (TypeError, ValueError):
                iteration = 0
            tools = context.get("tools")
            tool_names = context.get("tool_names")
            if not isinstance(tools, (list, tuple)):
                tools = ()
            if not isinstance(tool_names, (list, tuple)):
                tool_names = ()
            raw_names = [
                item.get("name") if isinstance(item, Mapping) else item
                for item in (tools or tool_names)
            ]
            digests = tuple(
                digest
                for name in raw_names[:64]
                if (digest := self.protector.pseudonym("tool", name)) is not None
            )
            payload.update(
                {
                    "iteration": iteration,
                    "tool_count": min(len(tools or tool_names), 10_000),
                    "tool_name_digests": list(dict.fromkeys(digests)),
                    "tool_arguments_stored": False,
                    "tool_results_stored": False,
                }
            )
        elif event_name == "agent:end":
            response = context.get("response")
            payload["response_present"] = bool(str(response or ""))
            payload["response_length_bucket"] = self._bounded_length(response)
            for key in ("model", "provider"):
                digest = self.protector.pseudonym(key, context.get(key))
                if digest is not None:
                    payload[f"{key}_digest"] = digest

    def _identity_fields(
        self, payload: Mapping[str, Any]
    ) -> tuple[str | None, str | None]:
        identities = payload.get("identities") or {}
        if not isinstance(identities, Mapping):
            return None, None
        subject = (
            identities.get("user_id")
            or identities.get("conversation_id")
            or identities.get("chat_id")
            or identities.get("session_id")
        )
        correlation = identities.get("session_id") or identities.get("conversation_id")
        return (
            str(subject) if subject else None,
            str(correlation) if correlation else None,
        )

    def _retain_conversation_content(
        self,
        *,
        event_id: str,
        event_name: str,
        subject: str | None,
        causation_id: str | None,
        context: Mapping[str, Any],
        payload: dict[str, Any],
        now: datetime,
    ) -> Sensitivity:
        payload["erasable_content_stored"] = False
        if subject is None or event_name not in {"agent:start", "agent:end"}:
            return Sensitivity.PRIVATE
        direction = (
            RetentionDirection.INBOUND
            if event_name == "agent:start"
            else RetentionDirection.OUTBOUND
        )
        if direction is RetentionDirection.OUTBOUND and causation_id is None:
            payload["content_retention_status"] = "orphaned_not_retained"
            return Sensitivity.PRIVATE
        policy = self.retention.policy(subject)
        if policy is None or not policy.allows(direction):
            payload["content_retention_status"] = "not_authorized"
            return Sensitivity.PRIVATE
        field = "message" if direction is RetentionDirection.INBOUND else "response"
        text = context.get(field)
        if not isinstance(text, str) or not text:
            payload["content_retention_status"] = "empty"
            return policy.sensitivity
        retention_until = now + timedelta(days=policy.retention_days)
        reference = self.content_vault.put_json(
            {
                "text": text,
                "direction": direction.value,
                "source_contract": "hermes-hook-500",
                "may_be_truncated": len(text) >= 500,
            },
            subject=subject,
            purpose=f"conversation.{direction.value}",
            sensitivity=policy.sensitivity,
            retention_until=retention_until,
            content_id=f"experience:{event_id}:{direction.value}",
        )
        payload.update(
            {
                "erasable_content_stored": True,
                "content_retention_status": "retained",
                "content": reference.to_event_payload(),
                "content_contract": "hermes-hook-500",
                "content_may_be_truncated": len(text) >= 500,
                "consent_event_id": policy.consent_event_id,
            }
        )
        return policy.sensitivity

    def _claim_turn(
        self, correlation_id: str, message_digest: str, now: datetime
    ) -> tuple[str, datetime, bool, str | None]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                open_row = connection.execute(
                    "SELECT * FROM shadow_open_turns_v1 WHERE correlation_id=?",
                    (correlation_id,),
                ).fetchone()
                if open_row is not None and open_row["message_digest"] == message_digest:
                    connection.execute("COMMIT")
                    return (
                        str(open_row["start_event_id"]),
                        datetime.fromisoformat(str(open_row["started_at"])),
                        False,
                        None,
                    )
                if open_row is not None:
                    # Do not replace it inside this transaction. The caller
                    # must first append a durable interruption fact, then
                    # remove this exact activity row and retry the claim.
                    connection.execute("COMMIT")
                    return (
                        "",
                        now,
                        False,
                        str(open_row["start_event_id"]),
                    )
                counter_row = connection.execute(
                    "SELECT next_turn FROM shadow_turn_counters_v1 WHERE correlation_id=?",
                    (correlation_id,),
                ).fetchone()
                counter = int(counter_row["next_turn"]) if counter_row else 1
                connection.execute(
                    """
                    INSERT INTO shadow_turn_counters_v1(correlation_id, next_turn)
                    VALUES (?, ?)
                    ON CONFLICT(correlation_id) DO UPDATE SET next_turn=excluded.next_turn
                    """,
                    (correlation_id, counter + 1),
                )
                event_id = self.protector.pseudonym(
                    "turn", f"{correlation_id}\0{counter}"
                )
                assert event_id is not None
                connection.execute(
                    "DELETE FROM shadow_recent_ends_v1 WHERE correlation_id=?",
                    (correlation_id,),
                )
                connection.execute(
                    "INSERT INTO shadow_open_turns_v1 VALUES (?, ?, ?, ?)",
                    (correlation_id, event_id, message_digest, now.isoformat()),
                )
                connection.execute("COMMIT")
                return event_id, now, True, None
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _open_turn(self, correlation_id: str) -> sqlite3.Row | None:
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT * FROM shadow_open_turns_v1 WHERE correlation_id=?",
                (correlation_id,),
            ).fetchone()

    def _delete_open_turn(self, correlation_id: str, start_event_id: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                DELETE FROM shadow_open_turns_v1
                WHERE correlation_id=? AND start_event_id=?
                """,
                (correlation_id, start_event_id),
            )
            connection.execute("COMMIT")

    def _recent_end(self, correlation_id: str, message_digest: str) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT end_event_id FROM shadow_recent_ends_v1
                WHERE correlation_id=? AND message_digest=?
                """,
                (correlation_id, message_digest),
            ).fetchone()
            return str(row["end_event_id"]) if row is not None else None

    def _close_turn(
        self,
        correlation_id: str,
        start_event_id: str,
        message_digest: str,
        end_event_id: str,
        now: datetime,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    DELETE FROM shadow_open_turns_v1
                    WHERE correlation_id=? AND start_event_id=?
                    """,
                    (correlation_id, start_event_id),
                )
                connection.execute(
                    """
                    INSERT INTO shadow_recent_ends_v1 VALUES (?, ?, ?, ?)
                    ON CONFLICT(correlation_id) DO UPDATE SET
                        message_digest=excluded.message_digest,
                        end_event_id=excluded.end_event_id,
                        ended_at=excluded.ended_at
                    """,
                    (correlation_id, message_digest, end_event_id, now.isoformat()),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def _append_interruption(
        self,
        start_event_id: str,
        correlation_id: str,
        *,
        reason: str,
        observed_at: datetime,
        recovered_by: str | None = None,
    ) -> AppendResult:
        start = self.journal.get(start_event_id)
        event_id = self.protector.pseudonym(
            "hook", f"{start_event_id}\0interrupted"
        )
        assert event_id is not None
        existing = self.journal.get(event_id)
        if existing is not None:
            return AppendResult(existing.sequence, existing.event, False)
        payload: dict[str, Any] = {
            "turn_link_status": "interrupted",
            "reason": reason,
            "raw_content_stored": False,
            "privacy_policy": "structural-hook-v1",
        }
        if recovered_by is not None:
            payload["recovered_by_gateway_event"] = recovered_by
        assert_no_obvious_secret(payload)
        event = EventEnvelope(
            event_id=event_id,
            event_type="session.turn_interrupted",
            source="hermes.hook",
            actor="hermes:gateway",
            subject=start.event.subject if start is not None else None,
            correlation_id=correlation_id,
            causation_id=start_event_id,
            payload=payload,
            occurred_at=observed_at,
            observed_at=observed_at,
            sensitivity=Sensitivity.PRIVATE,
        )
        return self.journal.append(event)

    def _recover_open_turns(self, gateway_event_id: str, now: datetime) -> None:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM shadow_open_turns_v1 ORDER BY started_at"
            ).fetchall()
        for row in rows:
            correlation_id = str(row["correlation_id"])
            start_event_id = str(row["start_event_id"])
            self._append_interruption(
                start_event_id,
                correlation_id,
                reason="gateway_restarted",
                observed_at=now,
                recovered_by=gateway_event_id,
            )
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    DELETE FROM shadow_open_turns_v1
                    WHERE correlation_id=? AND start_event_id=?
                    """,
                    (correlation_id, start_event_id),
                )
                connection.execute("COMMIT")

    def observe_hook(self, event_name: str, context: Mapping[str, Any] | None) -> AppendResult | None:
        event_type = EVENT_TYPES.get(event_name)
        if event_type is None:
            return None
        payload = structural_hook_payload(event_name, context, self.protector)
        safe_context = context if isinstance(context, Mapping) else {}
        self._event_details(event_name, safe_context, payload)
        assert_no_obvious_secret(payload)
        subject, correlation_id = self._identity_fields(payload)
        now = datetime.now(timezone.utc)
        actor = "hermes:gateway"
        causation_id = None
        event_id = None
        occurred_at = now

        message_digest = self.protector.pseudonym(
            "message", safe_context.get("message")
        ) or "message:none"
        if event_name == "agent:start":
            if correlation_id is None:
                payload["turn_link_status"] = "missing_session_identity"
            else:
                event_id, occurred_at, created, displaced_id = self._claim_turn(
                    correlation_id, message_digest, now
                )
                if displaced_id is not None:
                    self._append_interruption(
                        displaced_id,
                        correlation_id,
                        reason="superseded_by_new_turn",
                        observed_at=now,
                    )
                    self._delete_open_turn(correlation_id, displaced_id)
                    event_id, occurred_at, created, displaced_id = self._claim_turn(
                        correlation_id, message_digest, now
                    )
                    if displaced_id is not None:
                        raise RuntimeError("turn replacement did not converge")
                if not created:
                    existing = self.journal.get(event_id)
                    if existing is not None:
                        return AppendResult(existing.sequence, existing.event, False)
            actor = subject or "user:unknown"
        elif event_name == "agent:step":
            open_row = self._open_turn(correlation_id) if correlation_id else None
            if open_row is not None:
                causation_id = str(open_row["start_event_id"])
                iteration = int(payload.get("iteration", 0))
                event_id = self.protector.pseudonym(
                    "hook", f"{causation_id}\0step\0{iteration}"
                )
                payload["turn_link_status"] = "linked"
            else:
                payload["turn_link_status"] = "orphaned"
            actor = "hermes:agent"
        elif event_name == "agent:end":
            open_row = self._open_turn(correlation_id) if correlation_id else None
            if open_row is not None:
                causation_id = str(open_row["start_event_id"])
                message_digest = str(open_row["message_digest"])
                event_id = self.protector.pseudonym(
                    "hook", f"{causation_id}\0end"
                )
                payload["turn_link_status"] = "linked"
            elif correlation_id:
                previous = self._recent_end(correlation_id, message_digest)
                if previous is not None:
                    existing = self.journal.get(previous)
                    if existing is not None:
                        return AppendResult(existing.sequence, existing.event, False)
                payload["turn_link_status"] = "orphaned"
            else:
                payload["turn_link_status"] = "missing_session_identity"
            actor = "hermes:agent"
        elif correlation_id:
            event_id = self.protector.pseudonym(
                "hook", f"{event_name}\0{correlation_id}"
            )

        if event_id is not None:
            existing = self.journal.get(event_id)
            if existing is not None:
                if event_name == "agent:end" and correlation_id and causation_id:
                    self._close_turn(
                        correlation_id, causation_id, message_digest, event_id, now
                    )
                return AppendResult(existing.sequence, existing.event, False)

        event_id = event_id or str(uuid4())
        sensitivity = self._retain_conversation_content(
            event_id=event_id,
            event_name=event_name,
            subject=subject,
            causation_id=causation_id,
            context=safe_context,
            payload=payload,
            now=occurred_at,
        )
        assert_no_obvious_secret(payload)
        event = EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            source="hermes.hook",
            actor=actor,
            subject=subject,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload,
            occurred_at=occurred_at,
            observed_at=occurred_at,
            sensitivity=sensitivity,
        )
        result = self.journal.append(event)
        if event_name == "gateway:startup":
            self._recover_open_turns(event.event_id, now)
        if event_name == "agent:end" and correlation_id and causation_id:
            self._close_turn(
                correlation_id, causation_id, message_digest, event.event_id, now
            )
        return result


def mirror_hook_event(
    shared_dir: str | Path,
    event_name: str,
    context: Mapping[str, Any] | None,
) -> AppendResult | None:
    """Best-effort shadow ingestion. Caller decides how failures are logged."""

    return ShadowKernelBridge(shared_dir).observe_hook(event_name, context)
