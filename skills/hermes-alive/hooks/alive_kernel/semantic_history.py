"""Bounded owner-scoped discovery of semantic content, not delivery history."""
from dataclasses import dataclass
from datetime import datetime, timezone

from .event_store import JournalRecord
from .semantic_rendering import MeaningStore, SemanticRenderingError


@dataclass(frozen=True, slots=True)
class SemanticHistoryItem:
    event_id: str
    recorded_at: datetime
    state: str
    preview: str = ""
    replacement_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticHistoryPage:
    items: tuple[SemanticHistoryItem, ...]
    next_before_event_id: str | None


class SemanticHistory:
    def __init__(self, meanings: MeaningStore):
        self.meanings = meanings

    def _authentic_definition(self, record: JournalRecord, subject: str) -> bool:
        event = record.event
        return bool(
            event.event_type == "message.meaning_defined"
            and event.source == "alive.semantic-rendering"
            and event.subject == subject
            and self.meanings.protector.verify_json(
                "message.meaning.v1",
                self.meanings._authentication_document("message.meaning.v1", event.payload),
                str(event.payload.get("integrity_authenticator", "")),
            )
        )

    def page(
        self, *, subject: str, before_event_id: str | None = None, limit: int = 10,
        as_of: datetime | None = None,
    ) -> SemanticHistoryPage:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise SemanticRenderingError("message history limit must be between 1 and 20")
        current = as_of or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise SemanticRenderingError("history time must be timezone-aware")
        before_sequence = None
        if before_event_id is not None:
            cursor = self.meanings.journal.get(before_event_id)
            if (
                cursor is None or cursor.event.subject != subject
                or cursor.event.event_type != "message.meaning_defined"
            ):
                raise SemanticRenderingError("message history cursor is unavailable for this user")
            before_sequence = cursor.sequence
        records = self.meanings.journal.recent_for_subject(
            subject=subject, event_type="message.meaning_defined", limit=limit + 1,
            before_sequence=before_sequence,
        )
        items = []
        for record in records[:limit]:
            event = record.event
            state, preview, replacement = "unavailable", "", None
            if self._authentic_definition(record, subject):
                withdrawal = self.meanings.journal.get(
                    f"message.meaning_retracted:{event.payload.get('message_id', '')}"
                )
                if withdrawal is not None:
                    if self.meanings._valid_withdrawal(withdrawal, record):
                        state = "withdrawn"
                        if withdrawal.event.payload.get("reason") == "explicit_user_correction":
                            replacement = str(withdrawal.event.payload["replacement_event_id"])
                            successor = self.meanings.journal.get(replacement)
                            state = "correcting" if successor is None else (
                                "corrected" if self._authentic_definition(successor, subject) else "unavailable"
                            )
                elif event.expires_at is not None and event.expires_at <= current:
                    state = "expired"
                else:
                    try:
                        document = self.meanings.inspect_for_user(event.event_id, subject=subject)
                    except SemanticRenderingError:
                        pass
                    else:
                        state = "available"
                        text = " ".join(atom.text for atom in document.atoms)
                        preview = text[:117] + "…" if len(text) > 120 else text
            items.append(SemanticHistoryItem(event.event_id, event.observed_at, state, preview, replacement))
        next_cursor = records[limit - 1].event.event_id if len(records) > limit else None
        return SemanticHistoryPage(tuple(items), next_cursor)
