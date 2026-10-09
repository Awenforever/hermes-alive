"""Shadow-only bridge from Hermes hook events to the experience journal."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Any, Mapping

from .event_store import AppendResult, ExperienceJournal
from .events import EventEnvelope, Sensitivity
from .privacy import LocalIdentityProtector, assert_no_obvious_secret, structural_hook_payload


logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "gateway:startup": "lifecycle.gateway_started",
    "session:start": "session.started",
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

    def observe_hook(self, event_name: str, context: Mapping[str, Any] | None) -> AppendResult | None:
        event_type = EVENT_TYPES.get(event_name)
        if event_type is None:
            return None
        payload = structural_hook_payload(event_name, context, self.protector)
        assert_no_obvious_secret(payload)
        identities = payload.get("identities") or {}
        subject = None
        if isinstance(identities, Mapping):
            subject = identities.get("session_id") or identities.get("conversation_id")
        event = EventEnvelope(
            event_type=event_type,
            source="hermes.hook",
            actor="hermes:gateway",
            subject=str(subject) if subject else None,
            payload=payload,
            occurred_at=datetime.now(timezone.utc),
            observed_at=datetime.now(timezone.utc),
            sensitivity=Sensitivity.PRIVATE,
        )
        return self.journal.append(event)


def mirror_hook_event(
    shared_dir: str | Path,
    event_name: str,
    context: Mapping[str, Any] | None,
) -> AppendResult | None:
    """Best-effort shadow ingestion. Caller decides how failures are logged."""

    return ShadowKernelBridge(shared_dir).observe_hook(event_name, context)
