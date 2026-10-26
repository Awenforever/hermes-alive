"""Privacy-bounded receipts from Hermes' native ``post_tool_call`` hook."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from enum import StrEnum
from pathlib import Path
import re
from typing import Any, Mapping
from uuid import uuid4

from .event_store import AppendResult, ExperienceJournal
from .events import EventEnvelope, Sensitivity
from .privacy import LocalIdentityProtector, assert_no_obvious_secret


_STRUCTURAL_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
_EXPLICIT_TERMINAL_STATUSES = frozenset({"blocked", "cancelled", "timeout"})


class ToolOutcome(StrEnum):
    """Only outcomes justified by an explicit Hermes terminal signal."""

    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ToolReceiptAssessment:
    outcome: ToolOutcome
    authority: str
    learning_eligible: bool


def assess_reported_outcome(status: Any, error_type: Any) -> ToolReceiptAssessment:
    """Separate explicit terminal facts from Hermes' prose-derived classification.

    Hermes currently derives ordinary ``ok`` and ``error/tool_error`` values by
    inspecting a tool's returned value.  They are useful diagnostics but are not
    authoritative success evidence.  Explicit blocked/cancelled/timeout values,
    and exception-backed errors, are emitted by the executor itself.
    """

    normalized_status = str(status or "").strip().lower()
    normalized_error = str(error_type or "").strip().lower()
    if normalized_status in _EXPLICIT_TERMINAL_STATUSES:
        outcome = {
            "blocked": ToolOutcome.BLOCKED,
            "cancelled": ToolOutcome.CANCELLED,
            "timeout": ToolOutcome.TIMED_OUT,
        }[normalized_status]
        return ToolReceiptAssessment(outcome, "explicit_core_terminal", True)
    if normalized_status == "error" and normalized_error not in {"", "tool_error"}:
        return ToolReceiptAssessment(
            ToolOutcome.FAILED, "explicit_core_exception", True
        )
    return ToolReceiptAssessment(
        ToolOutcome.UNKNOWN, "completion_only_untrusted_classification", False
    )


def _structural_token(value: Any, *, default: str) -> str:
    token = str(value or "").strip()
    return token if _STRUCTURAL_TOKEN_RE.fullmatch(token) else default


class ToolReceiptRecorder:
    """Append terminal tool facts without retaining arguments, results or errors."""

    def __init__(self, shared_dir: str | Path) -> None:
        self.kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
        self.protector = LocalIdentityProtector(self.kernel_dir / "identity.key")
        self.journal = ExperienceJournal(self.kernel_dir / "experience.sqlite3")
        self.configured_store = self.configured = None

    @classmethod
    def for_configured_owner(cls,store,configured):
        """Reuse protected storage, never initialize replacement keys on a hook."""
        current=store.configuration()
        if (current is None or current.event_id!=configured.event_id
                or current.subject!=configured.subject or current.options.get('observe_core_tools') is not True):
            raise ValueError('current guided owner observation permission required')
        result=object.__new__(cls)
        result.kernel_dir=store.root
        result.protector,result.journal=store.protector,store.journal
        result.configured_store,result.configured=store,configured
        return result

    def _identities(self, values: Mapping[str, Any]) -> dict[str, str]:
        identities: dict[str, str] = {}
        for field, namespace in (
            ("task_id", "task"),
            ("session_id", "session"),
            ("tool_call_id", "tool_call"),
            ("turn_id", "turn"),
            ("api_request_id", "api_request"),
        ):
            pseudonym = self.protector.pseudonym(namespace, values.get(field))
            if pseudonym:
                identities[field] = pseudonym
        return identities

    def _event_id(self, values: Mapping[str, Any]) -> tuple[str, str]:
        coordinates = [
            str(values.get(field) or "").strip()
            for field in (
                "session_id", "turn_id", "api_request_id", "task_id", "tool_call_id"
            )
        ]
        if coordinates[-1] and any(coordinates[:-1]):
            if self.configured is not None:
                coordinates.extend((self.configured.subject,self.configured.event_id))
            pseudonym = self.protector.pseudonym(
                "tool_receipt", "\x1f".join(coordinates)
            )
            assert pseudonym is not None
            return f"tool.receipt:{pseudonym.rsplit(':', 1)[-1]}", "stable"
        return f"tool.receipt:{uuid4()}", "unlinked"

    def record(self, values: Mapping[str, Any] | None) -> AppendResult:
        context = values if isinstance(values, Mapping) else {}
        event_id, identity_quality = self._event_id(context)
        existing = self.journal.get(event_id)
        if existing is not None:
            return AppendResult(existing.sequence, existing.event, False)

        status = _structural_token(context.get("status"), default="unspecified")
        error_type = _structural_token(context.get("error_type"), default="unspecified")
        assessment = assess_reported_outcome(status, error_type)
        try:
            duration_ms = max(0, min(int(context.get("duration_ms") or 0), 86_400_000))
        except (TypeError, ValueError):
            duration_ms = 0
        identities = self._identities(context)
        payload = {
            "tool_name": _structural_token(context.get("tool_name"), default="unknown"),
            "terminal_observed": True,
            "reported_status": status,
            "reported_error_type": error_type,
            "outcome": assessment.outcome.value,
            "outcome_authority": assessment.authority,
            "learning_eligible": assessment.learning_eligible,
            "duration_ms": duration_ms,
            "identities": identities,
            "identity_quality": identity_quality,
            "arguments_stored": False,
            "result_stored": False,
            "error_message_stored": False,
            "source_contract": "hermes-plugin-post-tool-call-v1",
        }
        configured=self.configured
        if configured is not None:
            payload.update(configuration_event_id=configured.event_id,owner_bound=True,
                task_success_proven=False,automatic_learning_authority=False,
                structural_ledger_retained_until_removed=True)
        assert_no_obvious_secret(payload)
        event = EventEnvelope(
            event_id=event_id,
            event_type="tool.execution_observed",
            source="hermes.plugin.post_tool_call",
            actor="system:hermes",
            subject=configured.subject if configured else None,
            correlation_id=identities.get("session_id"),
            sensitivity=Sensitivity.PRIVATE,
            payload=payload,
            expires_at=(datetime.now(timezone.utc)+timedelta(days=configured.options['outbound_retention_days'])) if configured else None,
        )
        def current_permission(_connection):
            if configured is not None:
                current=self.configured_store.configuration()
                if (current is None or current.event_id!=configured.event_id
                        or current.options.get('observe_core_tools') is not True):
                    raise ValueError('owner observation permission changed')
        return self.journal.append(event,precondition=current_permission)


def record_post_tool_call(
    shared_dir: str | Path, values: Mapping[str, Any] | None
) -> AppendResult:
    return ToolReceiptRecorder(shared_dir).record(values)
