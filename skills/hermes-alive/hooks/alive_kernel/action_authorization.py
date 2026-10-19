"""Send-time authority revalidation without performing an external action."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Iterable
from uuid import uuid4

from .action_contract import ActionContractError, parse_action_contract
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
from .host_capabilities import HostCapabilityProjection


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
    route_binding_id: str | None


class SendTimeAuthorizer:
    """Recheck current authority and emit a short-lived structural receipt."""

    MAX_SELECTION_AGE = timedelta(minutes=5)
    MAX_PERMIT_TTL = timedelta(seconds=60)

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
        route_binding_id: str | None = None,
        context_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.context_vault = context_vault
        self.deliberation = DeliberationProjection(
            journal, content_vault=content_vault
        )
        self.exploration = ExplorationProjection(
            journal, content_vault=self.deliberation.content_vault
        )
        self.agenda = AgendaProjection(
            journal, content_vault=self.deliberation.content_vault
        )
        self.commitments = AgendaProjection(journal)
        self.receipt_protector = LocalIdentityProtector(
            journal.path.parent / "identity.key"
        )
        self.autonomy = AutonomyPolicyProjection(journal)
        self.host = HostCapabilityProjection(
            journal, content_vault=self.deliberation.content_vault
        )
        self.route_binding_id = (
            str(route_binding_id).strip() if route_binding_id is not None else None
        )

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
        route_binding_id: str | None,
        permit_ttl_seconds: float,
        expression_event_id: str | None,
        delegation_event_id: str | None,
        final_wording_witness: dict | None,
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
            or payload.get("expression_event_id") != expression_event_id
            or payload.get("delegation_event_id") != delegation_event_id
            or payload.get("final_wording_witness") != final_wording_witness
            or payload.get("route_binding_id") != route_binding_id
            or payload.get("permit_ttl_seconds") != permit_ttl_seconds
            or payload.get("action_contract_version") != 1
            or (
                payload.get("outcome") == "authorized"
                and not re.fullmatch(
                    r"[0-9a-f]{64}",
                    str(payload.get("action_contract_binding") or ""),
                )
            )
        ):
            raise ActionAuthorizationError(
                "authorization operation ID was reused with different semantics"
            )
        valid_until = payload.get("valid_until")
        authorized = payload.get("outcome") == "authorized"
        parsed_until = datetime.fromisoformat(str(valid_until)) if valid_until else None
        reasons = tuple(str(value) for value in payload.get("reasons", ()))
        if authorized and final_wording_witness is not None:
            try:
                from .expression_support import ExpressionSourceSupportReviewer
                ExpressionSourceSupportReviewer(self.journal,
                    content_vault=self.deliberation.content_vault,
                    context_vault=self.context_vault).require_current_witness(final_wording_witness,
                        subject=subject, expression_event_id=expression_event_id,
                        selection_event_id=selection_event_id)
            except ValueError:
                authorized = False
                reasons = (*reasons, "final_wording_not_current")
        if authorized and (parsed_until is None or parsed_until <= now):
            authorized = False
            reasons = (*reasons, "permit_expired")
        if authorized and capability == "hermes.channel.send":
            if route_binding_id is None:
                authorized = False
                reasons = (*reasons, "route_binding_required")
            else:
                _binding, route_reasons = self.host.execution_binding(
                    route_binding_id,
                    subject=subject,
                    capability=capability,
                    as_of=now,
                )
                if route_reasons:
                    authorized = False
                    reasons = (*reasons, *route_reasons)
        if authorized:
            from .deliberation_synthesis import DeliberationSynthesizer, DeliberationContextChanged
            from .semantic_review import SemanticReviewError
            try:
                DeliberationSynthesizer(self.journal,
                    content_vault=self.deliberation.content_vault,
                    context_vault=self.context_vault).validate_selection_sources(
                        selection_event_id, owner=subject, sensitivity=event.sensitivity,
                        execution=True, expression_event_id=expression_event_id)
                if expression_event_id is not None:
                    from .opportunity_expression import OpportunityExpressionStore
                    expressed, _expiry = OpportunityExpressionStore(self.journal,
                        content_vault=self.deliberation.content_vault,
                        context_vault=self.context_vault).action_contract_for_expression(
                            expression_event_id=expression_event_id,
                            selection_event_id=selection_event_id, subject=subject, as_of=now)
                    if not self.receipt_protector.verify_json("action.contract.v1",
                            expressed.to_document(), payload.get("action_contract_binding")):
                        raise SemanticReviewError("retained expression binding changed")
            except (DeliberationContextChanged, SemanticReviewError):
                authorized = False
                reasons = (*reasons, "selection_inputs_not_current")
        if authorized and delegation_event_id is not None:
            from .action_delegation import ActionDelegationStore
            if not ActionDelegationStore(self.journal).permits(delegation_event_id,
                    subject=subject, policy_event_id=policy_event_id,
                    route_binding_id=route_binding_id, capability=capability,
                    action_kind=payload.get("delegated_action_kind"),
                    sensitivity=event.sensitivity, now=now,
                    natural_expression=expression_event_id is not None):
                authorized = False
                reasons = (*reasons, "delegation_not_current")
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
            route_binding_id,
        )

    def evaluate(
        self,
        *,
        selection_event_id: str,
        subject: str,
        capability: str,
        operation_id: str | None = None,
        confirmation_event_id: str | None = None,
        expression_event_id: str | None = None,
        final_wording_witness: dict | None = None,
        delegation_event_id: str | None = None,
        route_binding_id: str | None = None,
        now: datetime | None = None,
        permit_ttl: timedelta = timedelta(seconds=30),
    ) -> ActionAuthorizationDecision:
        operation = str(operation_id or uuid4()).strip()
        owner = str(subject).strip()
        capability = str(capability).strip()
        route_binding_id = (
            str(route_binding_id).strip()
            if route_binding_id is not None
            else self.route_binding_id
        )
        if not _ID_RE.fullmatch(operation) or not _ID_RE.fullmatch(owner):
            raise ActionAuthorizationError("invalid authorization identity")
        if not _EVENT_ID_RE.fullmatch(str(selection_event_id).strip()):
            raise ActionAuthorizationError("invalid selection event identity")
        selection_event_id = str(selection_event_id).strip()
        if expression_event_id is not None:
            expression_event_id = str(expression_event_id).strip()
            if not _EVENT_ID_RE.fullmatch(expression_event_id):
                raise ActionAuthorizationError("invalid expression event identity")
        if delegation_event_id is not None:
            delegation_event_id = str(delegation_event_id).strip()
            if not _EVENT_ID_RE.fullmatch(delegation_event_id):
                raise ActionAuthorizationError("invalid delegation event identity")
        if confirmation_event_id is not None:
            confirmation_event_id = str(confirmation_event_id).strip()
            if not _EVENT_ID_RE.fullmatch(confirmation_event_id):
                raise ActionAuthorizationError("invalid confirmation event identity")
        if route_binding_id is not None:
            route_binding_id = str(route_binding_id).strip()
            if not _ID_RE.fullmatch(route_binding_id):
                raise ActionAuthorizationError("invalid route binding identity")
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
            route_binding_id=route_binding_id,
            permit_ttl_seconds=permit_ttl_seconds,
            expression_event_id=expression_event_id,
            delegation_event_id=delegation_event_id,
            final_wording_witness=final_wording_witness,
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
        stored = None
        action_contract_binding: str | None = None
        executable_content_id: str | None = None
        route_binding_event_id: str | None = None
        host_snapshot_event_id: str | None = None
        route_binding_authenticator: str | None = None
        if capability == "hermes.channel.send":
            if route_binding_id is None:
                reasons.append("route_binding_required")
            else:
                route_binding, route_reasons = self.host.execution_binding(
                    route_binding_id,
                    subject=owner,
                    capability=capability,
                    as_of=current,
                )
                reasons.extend(route_reasons)
                if route_binding is not None:
                    route_binding_event_id = route_binding.event_id
                    host_snapshot_event_id = route_binding.snapshot_event_id
                    route_binding_authenticator = route_binding.binding_authenticator
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
            if delegation_event_id is not None and candidate.authority is not ActionAuthority.USER_DELEGATED:
                reasons.append("delegation_not_applicable")
            from .deliberation_synthesis import DeliberationSynthesizer, DeliberationContextChanged
            try:
                DeliberationSynthesizer(self.journal,
                    content_vault=self.deliberation.content_vault,
                    context_vault=self.context_vault).validate_selection_sources(
                        selection_event_id, owner=owner, sensitivity=sensitivity,
                        execution=True, expression_event_id=expression_event_id)
            except DeliberationContextChanged:
                reasons.append("generated_inputs_not_current")
            if candidate.action_kind is ActionKind.SILENCE:
                reasons.append("silence_not_executable")
            if self._required_capability(candidate.side_effect) != capability:
                reasons.append("capability_mismatch")
            content_document = dict(stored.candidate_contents).get(
                str(candidate.content_id)
            ) if stored is not None and candidate.content_id is not None else None
            if expression_event_id is not None:
                from .opportunity_expression import OpportunityExpressionStore
                from .semantic_review import SemanticReviewError
                confirmation = self.journal.get(str(confirmation_event_id)) if confirmation_event_id else None
                expression_header = self.journal.get(expression_event_id)
                confirmed_expression = not (candidate.authority is not ActionAuthority.USER_CONFIRMED
                        or confirmation is None or expression_header is None
                        or confirmation.event.event_type != "conversation.inbound"
                        or confirmation.event.actor != owner or confirmation.event.subject != owner
                        or confirmation.sequence <= expression_header.sequence
                        or confirmation.event.payload.get("authorizes_expression_event_id") != expression_event_id)
                from .action_delegation import ActionDelegationStore
                delegated_expression = (candidate.authority is ActionAuthority.USER_DELEGATED
                    and delegation_event_id is not None
                    and ActionDelegationStore(self.journal).permits(delegation_event_id,
                        subject=owner, policy_event_id=policy_event_id, route_binding_id=route_binding_id,
                        capability=capability, action_kind=candidate.action_kind,
                        sensitivity=sensitivity, now=current, natural_expression=True))
                if not confirmed_expression and not delegated_expression:
                    reasons.append("exact_expression_confirmation_required")
                else:
                    try:
                        expressed, expiry = OpportunityExpressionStore(self.journal,
                            content_vault=self.deliberation.content_vault,
                            context_vault=self.context_vault).action_contract_for_expression(
                                expression_event_id=expression_event_id,
                                selection_event_id=selection_event_id, subject=owner, as_of=current)
                        content_document = expressed.to_document()
                        reference = self.deliberation.content_vault.put_json(content_document,
                            subject=owner, purpose="deliberation.candidate", sensitivity=sensitivity,
                            retention_until=expiry, content_id="expression-action:" +
                            self.deliberation.content_vault.digest_json({'event_id': expression_event_id})[:40])
                        executable_content_id = reference.content_id
                    except SemanticReviewError:
                        reasons.append("expression_not_current")
            try:
                contract = parse_action_contract(
                    content_document,
                    capability=capability,
                )
                action_contract_binding = self.receipt_protector.authenticate_json(
                    "action.contract.v1", contract.to_document()
                )
            except ActionContractError:
                reasons.append("action_contract_invalid")
            if gate_event_id != self.exploration.latest_gate_event_id(frame_id):
                reasons.append("exploration_gate_stale")
            agenda_record = None
            if candidate.agenda_item_id is None:
                if candidate.authority is not ActionAuthority.SYSTEM_CRITICAL:
                    reasons.append("active_agenda_required")
            else:
                origin = self.journal.get('agenda.proposal:'+candidate.agenda_item_id)
                commitment = (candidate.candidate_id.startswith('opportunity-candidate:')
                              and origin is not None and origin.event.subject==owner
                              and origin.event.payload.get('kind')=='commitment')
                agenda_projection = self.commitments if commitment else self.agenda
                active = {
                    item.item_id: item
                    for item in agenda_projection.list_items(
                        clearance=sensitivity,
                        states=(AgendaState.ACTIVE,AgendaState.SNOOZED) if commitment else (AgendaState.ACTIVE,),
                        as_of=current,
                        limit=1000,
                        subject=owner,
                        item_ids=(candidate.agenda_item_id,),
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
                if delegation_event_id is not None:
                    from .action_delegation import ActionDelegationStore
                    if not ActionDelegationStore(self.journal).permits(delegation_event_id,
                            subject=owner, policy_event_id=policy_event_id,
                            route_binding_id=route_binding_id, capability=capability,
                            action_kind=candidate.action_kind, sensitivity=sensitivity, now=current,
                            natural_expression=expression_event_id is not None):
                        reasons.append("delegation_not_current")
                elif agenda_record is None or agenda_record.authority not in {
                    AgendaAuthority.USER_EXPLICIT,
                }:
                    reasons.append("user_delegation_unproven")
            elif candidate.authority is ActionAuthority.SYSTEM_CRITICAL:
                reasons.append("system_critical_authority_unimplemented")
            else:
                reasons.append("action_authority_invalid")

        if final_wording_witness is not None:
            from .expression_support import ExpressionSourceSupportReviewer
            try:
                ExpressionSourceSupportReviewer(self.journal,
                    content_vault=self.deliberation.content_vault,
                    context_vault=self.context_vault).require_current_witness(final_wording_witness,
                        subject=owner, expression_event_id=expression_event_id,
                        selection_event_id=selection_event_id)
            except ValueError:
                reasons.append("final_wording_not_current")
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
            "expression_event_id": expression_event_id,
            "delegation_event_id": delegation_event_id,
            "delegated_action_kind": candidate.action_kind.value if candidate is not None and delegation_event_id else None,
            "executable_content_id": executable_content_id,
            "route_binding_id": route_binding_id,
            "route_binding_event_id": route_binding_event_id,
            "host_snapshot_event_id": host_snapshot_event_id,
            "route_binding_authenticator": route_binding_authenticator,
            "capability": capability,
            "action_contract_version": 1,
            "action_contract_binding": action_contract_binding,
            "outcome": "authorized" if authorized else "denied",
            "reasons": reasons,
            "policy": policy_payload,
            "policy_event_id": policy_event_id,
            "policy_revision": policy_revision,
            "permit_ttl_seconds": permit_ttl_seconds,
            "valid_until": valid_until.isoformat() if valid_until else None,
            "executes_action": False,
        }
        if final_wording_witness is not None:
            payload["final_wording_witness"] = final_wording_witness
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
            route_binding_id,
        )
