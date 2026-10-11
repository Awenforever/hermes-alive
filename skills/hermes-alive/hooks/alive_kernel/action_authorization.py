"""Send-time authority revalidation without performing an external action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Iterable
from uuid import uuid4

from .autonomy_policy import AutonomyPolicyProjection
from .agenda import (
    AgendaAuthority,
    AgendaContentStatus,
    AgendaProjection,
    AgendaState,
)
from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentUnavailableError,
    ContentVault,
)
from .deliberation import (
    ActionAuthority,
    ActionKind,
    PolicyContext,
    SideEffect,
    build_frame,
)
from .deliberation_store import DeliberationProjection
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .exploration_store import ExplorationProjection
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_CAPABILITIES = frozenset(
    {"hermes.channel.send", "hermes.tool.execute", "hermes.internal.review"}
)


class ActionAuthorizationError(ValueError):
    """An authorization request violates the kernel boundary."""


@dataclass(frozen=True, slots=True)
class ActionAuthorizationDecision:
    operation_id: str
    event_id: str
    authorized: bool
    reasons: tuple[str, ...]
    selection_event_id: str
    frame_id: str
    candidate_id: str
    capability: str
    valid_until: datetime | None


class SendTimeAuthorizer:
    """Recheck current authority and emit a short-lived structural receipt."""

    MAX_SELECTION_AGE = timedelta(minutes=5)
    MAX_PERMIT_TTL = timedelta(seconds=60)

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.deliberation = DeliberationProjection(
            journal, content_vault=content_vault
        )
        self.exploration = ExplorationProjection(
            journal, content_vault=self.deliberation.content_vault
        )
        self.agenda = AgendaProjection(
            journal, content_vault=self.deliberation.content_vault
        )
        self.receipt_protector = LocalIdentityProtector(
            journal.path.parent / "identity.key"
        )
        self.autonomy = AutonomyPolicyProjection(journal)

    @staticmethod
    def _utc(value: datetime | None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ActionAuthorizationError("authorization time must be timezone-aware")
        return current.astimezone(timezone.utc)

    @staticmethod
    def _required_capability(side_effect: SideEffect) -> str:
        if side_effect is SideEffect.COMMUNICATION:
            return "hermes.channel.send"
        if side_effect in {
            SideEffect.REVERSIBLE_EXTERNAL,
            SideEffect.IRREVERSIBLE_EXTERNAL,
        }:
            return "hermes.tool.execute"
        return "hermes.internal.review"

    @staticmethod
    def _evidence_ids(candidate: object) -> Iterable[str]:
        dimensions = getattr(candidate, "dimensions", None)
        if dimensions is None:
            return ()
        return dict.fromkeys(
            event_id
            for name in (
                "user_value",
                "urgency",
                "novelty",
                "confidence",
                "interruption_cost",
                "risk",
            )
            for event_id in getattr(dimensions, name).evidence_event_ids
        )

    def _existing(
        self,
        operation: str,
        *,
        selection_event_id: str,
        subject: str,
        capability: str,
        now: datetime,
        policy: dict[str, object],
        policy_event_id: str | None,
        policy_revision: int | None,
        confirmation_event_id: str | None,
        permit_ttl_seconds: float,
    ) -> ActionAuthorizationDecision | None:
        record = self.journal.get(f"action.authorization:{operation}")
        if record is None:
            return None
        event = record.event
        payload = _thaw_json(event.payload)
        authenticator = payload.pop("integrity_authenticator", None)
        if (
            event.event_type != "action.authorization_evaluated"
            or not self.receipt_protector.verify_json(
                "action.authorization.v1", payload, authenticator
            )
            or event.subject != subject
            or payload.get("selection_event_id") != selection_event_id
            or payload.get("capability") != capability
            or payload.get("policy") != policy
            or payload.get("policy_event_id") != policy_event_id
            or payload.get("policy_revision") != policy_revision
            or payload.get("confirmation_event_id") != confirmation_event_id
            or payload.get("permit_ttl_seconds") != permit_ttl_seconds
        ):
            raise ActionAuthorizationError(
                "authorization operation ID was reused with different semantics"
            )
        valid_until = payload.get("valid_until")
        authorized = payload.get("outcome") == "authorized"
        parsed_until = datetime.fromisoformat(str(valid_until)) if valid_until else None
        reasons = tuple(str(value) for value in payload.get("reasons", ()))
        if authorized and (parsed_until is None or parsed_until <= now):
            authorized = False
            reasons = (*reasons, "permit_expired")
        return ActionAuthorizationDecision(
            operation,
            event.event_id,
            authorized,
            reasons,
            selection_event_id,
            str(payload.get("frame_id") or ""),
            str(payload.get("candidate_id") or ""),
            capability,
            parsed_until,
        )

    def evaluate(
        self,
        *,
        selection_event_id: str,
        subject: str,
        capability: str,
        operation_id: str | None = None,
        confirmation_event_id: str | None = None,
        now: datetime | None = None,
        permit_ttl: timedelta = timedelta(seconds=30),
    ) -> ActionAuthorizationDecision:
        operation = str(operation_id or uuid4()).strip()
        owner = str(subject).strip()
        capability = str(capability).strip()
        if not _ID_RE.fullmatch(operation) or not _ID_RE.fullmatch(owner):
            raise ActionAuthorizationError("invalid authorization identity")
        if not _EVENT_ID_RE.fullmatch(str(selection_event_id).strip()):
            raise ActionAuthorizationError("invalid selection event identity")
        selection_event_id = str(selection_event_id).strip()
        if confirmation_event_id is not None:
            confirmation_event_id = str(confirmation_event_id).strip()
            if not _EVENT_ID_RE.fullmatch(confirmation_event_id):
                raise ActionAuthorizationError("invalid confirmation event identity")
        if capability not in _CAPABILITIES:
            raise ActionAuthorizationError("unknown Hermes capability")
        current = self._utc(now)
        if not timedelta(0) < permit_ttl <= self.MAX_PERMIT_TTL:
            raise ActionAuthorizationError("permit TTL must be between zero and 60 seconds")
        durable_policy = self.autonomy.current(owner)
        if durable_policy is None:
            current_policy = PolicyContext(
                can_interrupt=False,
                allowed_side_effects=frozenset({SideEffect.NONE}),
            )
            policy_event_id = None
            policy_revision = None
            initial_reasons = ["autonomy_policy_missing"]
        else:
            current_policy = durable_policy.context
            policy_event_id = durable_policy.event_id
            policy_revision = durable_policy.revision
            initial_reasons = [] if durable_policy.enabled else ["autonomy_disabled"]
            if durable_policy.updated_at > current:
                initial_reasons.append("autonomy_policy_from_future")
        policy_payload = {
            "can_interrupt": current_policy.can_interrupt,
            "minimum_confidence": current_policy.minimum_confidence,
            "maximum_risk": current_policy.maximum_risk,
            "allowed_side_effects": sorted(
                value.value for value in current_policy.allowed_side_effects
            ),
        }
        permit_ttl_seconds = permit_ttl.total_seconds()
        existing = self._existing(
            operation,
            selection_event_id=selection_event_id,
            subject=owner,
            capability=capability,
            now=current,
            policy=policy_payload,
            policy_event_id=policy_event_id,
            policy_revision=policy_revision,
            confirmation_event_id=confirmation_event_id,
            permit_ttl_seconds=permit_ttl_seconds,
        )
        if existing is not None:
            return existing

        reasons: list[str] = list(initial_reasons)
        selection_record = self.journal.get(selection_event_id)
        frame_id = ""
        candidate_id = ""
        gate_event_id = ""
        sensitivity = Sensitivity.PRIVATE
        candidate = None
        if selection_record is None or selection_record.event.event_type != "deliberation.selected":
            reasons.append("selection_unavailable")
        else:
            selection_event = selection_record.event
            frame_id = str(selection_event.payload.get("frame_id") or "")
            candidate_id = str(selection_event.payload.get("candidate_id") or "")
            gate_event_id = str(
                selection_event.payload.get("exploration_gate_event_id") or ""
            )
            sensitivity = selection_event.sensitivity
            if selection_event.subject != owner:
                reasons.append("selection_subject_mismatch")
            try:
                stored = self.deliberation.inspect(frame_id, clearance=sensitivity)
            except (
                ContentErasedError,
                ContentIntegrityError,
                ContentUnavailableError,
            ):
                stored = None
                reasons.append("selection_content_unavailable")
            if (
                stored is None
                or stored.selection is None
                or self.deliberation.latest_selection_event_id(frame_id)
                != selection_event_id
            ):
                reasons.append("selection_not_latest_validated")
            else:
                candidate = stored.selection.candidate
                if candidate.candidate_id != candidate_id:
                    reasons.append("selection_candidate_mismatch")
                refreshed = build_frame(
                    (candidate,), current_policy, frame_id=f"send-time:{frame_id}"
                )
                if candidate_id not in refreshed.admissible_ids:
                    reasons.append("current_policy_rejected")
            if current - selection_event.observed_at > self.MAX_SELECTION_AGE:
                reasons.append("selection_stale")
            if selection_event.observed_at > current:
                reasons.append("selection_from_future")

        if candidate is not None:
            if candidate.action_kind is ActionKind.SILENCE:
                reasons.append("silence_not_executable")
            if self._required_capability(candidate.side_effect) != capability:
                reasons.append("capability_mismatch")
            if gate_event_id != self.exploration.latest_gate_event_id(frame_id):
                reasons.append("exploration_gate_stale")
            agenda_record = None
            if candidate.agenda_item_id is None:
                if candidate.authority is not ActionAuthority.SYSTEM_CRITICAL:
                    reasons.append("active_agenda_required")
            else:
                active = {
                    item.item_id: item
                    for item in self.agenda.list_items(
                        clearance=sensitivity,
                        states=(AgendaState.ACTIVE,),
                        as_of=current,
                        limit=1000,
                    )
                    if item.subject == owner
                }
                if candidate.agenda_item_id not in active:
                    reasons.append("agenda_not_active")
                else:
                    agenda_record = active[candidate.agenda_item_id]
                    if agenda_record.content_status is not AgendaContentStatus.AVAILABLE:
                        reasons.append("agenda_content_unavailable")
            for evidence_id in self._evidence_ids(candidate):
                evidence = self.journal.get(evidence_id)
                if (
                    evidence is None
                    or evidence.event.subject not in {None, owner}
                    or (
                        evidence.event.expires_at is not None
                        and evidence.event.expires_at <= current
                    )
                    or evidence.sequence >= selection_record.sequence
                ):
                    reasons.append("evidence_not_current")
                    break
            if candidate.authority is ActionAuthority.USER_CONFIRMATION_REQUIRED:
                reasons.append("user_confirmation_required")
            elif candidate.authority is ActionAuthority.USER_CONFIRMED:
                confirmation = (
                    self.journal.get(str(confirmation_event_id))
                    if confirmation_event_id
                    else None
                )
                if (
                    confirmation is None
                    or confirmation.event.event_type != "conversation.inbound"
                    or confirmation.event.actor != owner
                    or confirmation.event.subject != owner
                    or confirmation.sequence <= selection_record.sequence
                    or confirmation.event.payload.get(
                        "authorizes_selection_event_id"
                    )
                    != selection_event_id
                ):
                    reasons.append("user_confirmation_unavailable")
            elif candidate.authority is ActionAuthority.USER_DELEGATED:
                if agenda_record is None or agenda_record.authority not in {
                    AgendaAuthority.USER_EXPLICIT,
                }:
                    reasons.append("user_delegation_unproven")
            elif candidate.authority is ActionAuthority.SYSTEM_CRITICAL:
                reasons.append("system_critical_authority_unimplemented")
            else:
                reasons.append("action_authority_invalid")

        reasons = list(dict.fromkeys(reasons))
        authorized = not reasons
        valid_until = current + permit_ttl if authorized else None
        payload = {
            "operation_id": operation,
            "selection_event_id": selection_event_id,
            "frame_id": frame_id,
            "candidate_id": candidate_id,
            "gate_event_id": gate_event_id,
            "agenda_item_id": getattr(candidate, "agenda_item_id", None),
            "confirmation_event_id": confirmation_event_id,
            "capability": capability,
            "outcome": "authorized" if authorized else "denied",
            "reasons": reasons,
            "policy": policy_payload,
            "policy_event_id": policy_event_id,
            "policy_revision": policy_revision,
            "permit_ttl_seconds": permit_ttl_seconds,
            "valid_until": valid_until.isoformat() if valid_until else None,
            "executes_action": False,
        }
        payload["integrity_authenticator"] = self.receipt_protector.authenticate_json(
            "action.authorization.v1", payload
        )
        event = EventEnvelope(
            event_id=f"action.authorization:{operation}",
            event_type="action.authorization_evaluated",
            source="alive.authorization",
            actor="system:alive-authorizer",
            subject=owner,
            causation_id=selection_event_id if selection_record is not None else None,
            occurred_at=current,
            observed_at=current,
            expires_at=valid_until,
            sensitivity=sensitivity,
            payload=payload,
        )
        try:
            appended = self.journal.append(event)
        except EventConflictError as exc:
            raise ActionAuthorizationError("conflicting authorization receipt") from exc
        record = JournalRecord(appended.sequence, appended.event)
        return ActionAuthorizationDecision(
            operation,
            record.event.event_id,
            authorized,
            tuple(reasons),
            selection_event_id,
            frame_id,
            candidate_id,
            capability,
            valid_until,
        )
