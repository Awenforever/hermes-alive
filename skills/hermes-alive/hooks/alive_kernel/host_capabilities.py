"""Authenticated Hermes host capabilities and user-owned route bindings.

The action contract deliberately contains no destination.  This module owns
the other side of that boundary: facts reported by the Hermes host and an
encrypted route selected by the user.  A model can choose an action, but it
cannot manufacture a transport, recipient, receipt level, or route binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Mapping

from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}$")
_CAPABILITIES = frozenset(
    {"hermes.channel.send", "hermes.tool.execute", "hermes.internal.review"}
)
_ROUTE_FIELDS = frozenset({"platform", "profile", "chat_id", "thread_id"})
_REQUIRED_ROUTE_FIELDS = frozenset({"platform", "profile", "chat_id"})


class HostCapabilityError(ValueError):
    """A host or route assertion crossed the trusted execution boundary."""


class ReceiptLevel(str, Enum):
    """Strongest result a public host interface can truthfully prove."""

    REQUEST_ACCEPTED = "request_accepted"
    TURN_COMPLETED = "turn_completed"
    EXTERNAL_DELIVERED = "external_delivered"


@dataclass(frozen=True, slots=True)
class CapabilityClaim:
    capability: str
    interface: str
    available: bool
    public_api: bool
    receipt_level: ReceiptLevel

    def to_document(self) -> dict[str, object]:
        return {
            "interface": self.interface,
            "available": self.available,
            "public_api": self.public_api,
            "receipt_level": self.receipt_level.value,
        }


@dataclass(frozen=True, slots=True)
class HostCapabilitySnapshot:
    snapshot_id: str
    event_id: str
    hermes_version: str
    plugin_api_version: int
    claims: tuple[CapabilityClaim, ...]
    observed_at: datetime

    def claim(self, capability: str) -> CapabilityClaim | None:
        return next((item for item in self.claims if item.capability == capability), None)


@dataclass(frozen=True, slots=True)
class RouteBinding:
    binding_id: str
    event_id: str
    subject: str
    capability: str
    snapshot_event_id: str
    route_reference: ContentReference
    route_fingerprint: str
    binding_authenticator: str
    active: bool
    observed_at: datetime
    # Old bindings keep the original strict contract. Submission-only routes
    # require a new signed v2 binding and matching explicit user authority.
    receipt_requirement: ReceiptLevel = ReceiptLevel.EXTERNAL_DELIVERED


class HostCapabilityProjection:
    """Project signed host facts and encrypted user-authorized routes."""

    SNAPSHOT_NAMESPACE = "host.capability.snapshot.v1"
    ROUTE_NAMESPACE = "host.route.binding.v1"
    ROUTE_V2_NAMESPACE = "host.route.binding.v2"
    REVOKE_NAMESPACE = "host.route.revocation.v1"

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
    ) -> None:
        self.journal = journal
        self.vault = content_vault or ContentVault(
            journal.path.parent / "content-vault",
            backup_root=journal.path.parent / "content-backups",
        )
        self.protector = LocalIdentityProtector(journal.path.parent / "identity.key")

    @staticmethod
    def _utc(value: datetime | None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise HostCapabilityError("host time must be timezone-aware")
        return current.astimezone(timezone.utc)

    @staticmethod
    def _identity(value: object, name: str) -> str:
        text = str(value or "").strip()
        if not _ID_RE.fullmatch(text):
            raise HostCapabilityError(f"invalid {name}")
        return text

    @staticmethod
    def _claim(capability: str, raw: object) -> CapabilityClaim:
        if capability not in _CAPABILITIES or not isinstance(raw, Mapping):
            raise HostCapabilityError("invalid host capability claim")
        if frozenset(raw) != {
            "interface", "available", "public_api", "receipt_level"
        }:
            raise HostCapabilityError("host capability claim fields are invalid")
        interface = str(raw.get("interface") or "").strip()
        if not _ID_RE.fullmatch(interface):
            raise HostCapabilityError("invalid host capability interface")
        if type(raw.get("available")) is not bool or type(raw.get("public_api")) is not bool:
            raise HostCapabilityError("host capability booleans are invalid")
        try:
            receipt = ReceiptLevel(str(raw.get("receipt_level") or ""))
        except ValueError as exc:
            raise HostCapabilityError("invalid host receipt level") from exc
        return CapabilityClaim(
            capability,
            interface,
            bool(raw["available"]),
            bool(raw["public_api"]),
            receipt,
        )

    def observe_snapshot(
        self,
        *,
        snapshot_id: str,
        hermes_version: str,
        plugin_api_version: int,
        capabilities: Mapping[str, object],
        observed_at: datetime | None = None,
    ) -> HostCapabilitySnapshot:
        """Record one host-generated snapshot; this method performs no probing itself."""

        snapshot_id = self._identity(snapshot_id, "snapshot identity")
        version = str(hermes_version or "").strip()
        if not _VERSION_RE.fullmatch(version):
            raise HostCapabilityError("invalid Hermes version")
        if type(plugin_api_version) is not int or not 1 <= plugin_api_version <= 1000:
            raise HostCapabilityError("invalid plugin API version")
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise HostCapabilityError("at least one host capability is required")
        claims = tuple(
            self._claim(str(capability), raw)
            for capability, raw in sorted(capabilities.items())
        )
        current = self._utc(observed_at)
        previous = self.latest_snapshot()
        if previous is not None and previous.observed_at > current:
            raise HostCapabilityError("host capability time moved backwards")
        payload: dict[str, object] = {
            "schema_version": 1,
            "snapshot_id": snapshot_id,
            "hermes_version": version,
            "plugin_api_version": plugin_api_version,
            "capabilities": {
                claim.capability: claim.to_document() for claim in claims
            },
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            self.SNAPSHOT_NAMESPACE, payload
        )
        event = EventEnvelope(
            event_id=f"host.capabilities:{snapshot_id}",
            event_type="host.capabilities_observed",
            source="alive.host-bridge",
            actor="system:hermes-host",
            occurred_at=current,
            observed_at=current,
            sensitivity=Sensitivity.INTERNAL,
            payload=payload,
        )
        try:
            appended = self.journal.append(event)
        except EventConflictError as exc:
            raise HostCapabilityError("snapshot identity was reused") from exc
        return self._parse_snapshot(JournalRecord(appended.sequence, appended.event))

    def _parse_snapshot(self, record: JournalRecord | None) -> HostCapabilitySnapshot:
        if record is None or record.event.event_type != "host.capabilities_observed":
            raise HostCapabilityError("host capability snapshot is unavailable")
        payload = _thaw_json(record.event.payload)
        authenticator = payload.pop("integrity_authenticator", None)
        if (
            payload.get("schema_version") != 1
            or not self.protector.verify_json(
                self.SNAPSHOT_NAMESPACE, payload, authenticator
            )
        ):
            raise HostCapabilityError("host capability snapshot is unauthenticated")
        raw_claims = payload.get("capabilities")
        if not isinstance(raw_claims, Mapping):
            raise HostCapabilityError("host capability snapshot is malformed")
        claims = tuple(
            self._claim(str(capability), raw)
            for capability, raw in sorted(raw_claims.items())
        )
        snapshot_id = self._identity(payload.get("snapshot_id"), "snapshot identity")
        version = str(payload.get("hermes_version") or "")
        api_version = payload.get("plugin_api_version")
        if (
            record.event.event_id != f"host.capabilities:{snapshot_id}"
            or not _VERSION_RE.fullmatch(version)
            or type(api_version) is not int
        ):
            raise HostCapabilityError("host capability snapshot identity is invalid")
        return HostCapabilitySnapshot(
            snapshot_id,
            record.event.event_id,
            version,
            api_version,
            claims,
            record.event.observed_at,
        )

    def latest_snapshot(self, *, as_of: datetime | None = None) -> HostCapabilitySnapshot | None:
        cutoff = self._utc(as_of) if as_of is not None else None
        for record in self.journal.iter_reverse(event_types=("host.capabilities_observed",)):
            if cutoff is not None and record.event.observed_at > cutoff:
                continue
            try:
                return self._parse_snapshot(record)
            except HostCapabilityError:
                continue
        return None

    @staticmethod
    def _route_document(route: object) -> dict[str, str | None]:
        if not isinstance(route, Mapping) or not _REQUIRED_ROUTE_FIELDS.issubset(route):
            raise HostCapabilityError("route must name platform, profile and chat_id")
        if not frozenset(route).issubset(_ROUTE_FIELDS):
            raise HostCapabilityError("route fields are invalid")
        normalized: dict[str, str | None] = {}
        for key in sorted(_ROUTE_FIELDS):
            value = route.get(key)
            if value is None and key == "thread_id":
                normalized[key] = None
                continue
            text = str(value or "").strip()
            if not text or len(text) > 512 or any(ch in text for ch in "\r\n\0"):
                raise HostCapabilityError(f"invalid route {key}")
            normalized[key] = text
        return normalized

    def bind_route(
        self,
        *,
        binding_id: str,
        subject: str,
        capability: str,
        snapshot_event_id: str,
        route: Mapping[str, object],
        authority_event_id: str,
        observed_at: datetime | None = None,
        receipt_requirement: ReceiptLevel | None = None,
    ) -> RouteBinding:
        binding_id = self._identity(binding_id, "route binding identity")
        subject = self._identity(subject, "route subject")
        capability = str(capability).strip()
        if capability not in _CAPABILITIES:
            raise HostCapabilityError("unknown route capability")
        if receipt_requirement is not None and (
            capability != "hermes.channel.send" or not isinstance(receipt_requirement, ReceiptLevel)
        ):
            raise HostCapabilityError("explicit channel receipt requirement is invalid")
        current = self._utc(observed_at)
        snapshot = self._parse_snapshot(self.journal.get(str(snapshot_event_id)))
        latest_snapshot = self.latest_snapshot(as_of=current)
        if latest_snapshot is None or latest_snapshot.event_id != snapshot.event_id:
            raise HostCapabilityError("route must bind the latest host snapshot")
        if snapshot.claim(capability) is None:
            raise HostCapabilityError("snapshot does not declare the route capability")
        authority = self.journal.get(str(authority_event_id))
        if (
            authority is None
            or authority.event.event_type != "conversation.inbound"
            or authority.event.actor != subject
            or authority.event.subject != subject
            or authority.event.observed_at > current
            or (
                authority.event.expires_at is not None
                and authority.event.expires_at <= current
            )
            or authority.event.payload.get("authorizes_route_binding_id") != binding_id
        ):
            raise HostCapabilityError("explicit user route authority is unavailable")
        if receipt_requirement is not None and (
            authority.event.payload.get("authorizes_receipt_requirement") != receipt_requirement.value
            or authority.event.payload.get("authorizes_host_snapshot_event_id") != snapshot.event_id
        ):
            raise HostCapabilityError("explicit user receipt requirement authority is unavailable")
        route_document = self._route_document(route)
        route_fingerprint = self.protector.authenticate_json(
            "host.route.locator.v1", route_document
        )
        reference = self.vault.put_json(
            route_document,
            subject=subject,
            purpose="host.route.binding",
            sensitivity=Sensitivity.PRIVATE,
            content_id=f"host-route:{binding_id}",
        )
        binding_document: dict[str, object] = {
            "schema_version": 1,
            "binding_id": binding_id,
            "subject": subject,
            "capability": capability,
            "snapshot_event_id": snapshot.event_id,
            "authority_event_id": authority.event.event_id,
            "route_reference": reference.to_event_payload(),
            "route_fingerprint": route_fingerprint,
        }
        if receipt_requirement is not None:
            binding_document.update(schema_version=2, receipt_requirement=receipt_requirement.value)
        binding_authenticator = self.protector.authenticate_json(
            self.ROUTE_V2_NAMESPACE if receipt_requirement is not None else self.ROUTE_NAMESPACE,
            binding_document,
        )
        payload = {**binding_document, "binding_authenticator": binding_authenticator}
        event = EventEnvelope(
            event_id=f"host.route-bound:{binding_id}",
            event_type="host.route_bound",
            source="alive.host-bridge",
            actor="system:alive-route-authority",
            subject=subject,
            causation_id=authority.event.event_id,
            occurred_at=current,
            observed_at=current,
            sensitivity=Sensitivity.PRIVATE,
            payload=payload,
        )
        try:
            appended = self.journal.append(event)
        except EventConflictError as exc:
            raise HostCapabilityError("route binding identity was reused") from exc
        return self._parse_binding(JournalRecord(appended.sequence, appended.event))

    def _parse_binding(self, record: JournalRecord | None) -> RouteBinding:
        if record is None or record.event.event_type != "host.route_bound":
            raise HostCapabilityError("route binding is unavailable")
        payload = _thaw_json(record.event.payload)
        authenticator = str(payload.pop("binding_authenticator", ""))
        version = payload.get("schema_version")
        if (
            type(version) is not int or version not in (1, 2)
            or (version == 1 and "receipt_requirement" in payload)
            or not self.protector.verify_json(
                self.ROUTE_NAMESPACE if version == 1 else self.ROUTE_V2_NAMESPACE, payload, authenticator)
        ):
            raise HostCapabilityError("route binding is unauthenticated")
        binding_id = self._identity(payload.get("binding_id"), "route binding identity")
        subject = self._identity(payload.get("subject"), "route subject")
        capability = str(payload.get("capability") or "")
        try:
            requirement = (ReceiptLevel.EXTERNAL_DELIVERED if version == 1
                           else ReceiptLevel(payload.get("receipt_requirement")))
        except (ValueError, TypeError) as exc:
            raise HostCapabilityError("route receipt requirement is invalid") from exc
        if version == 2:
            authority = self.journal.get(str(payload.get("authority_event_id") or ""))
            if (capability != "hermes.channel.send" or authority is None
                or authority.sequence >= record.sequence
                or authority.event.event_type != "conversation.inbound"
                or authority.event.actor != subject or authority.event.subject != subject
                or authority.event.observed_at > record.event.observed_at
                or (authority.event.expires_at is not None
                    and authority.event.expires_at <= record.event.observed_at)
                or authority.event.payload.get("authorizes_route_binding_id") != binding_id
                or authority.event.payload.get("authorizes_receipt_requirement") != requirement.value
                or authority.event.payload.get("authorizes_host_snapshot_event_id") != payload.get("snapshot_event_id")
                or record.event.causation_id != authority.event.event_id):
                raise HostCapabilityError("route receipt requirement lacks exact user authority")
        reference = ContentReference.from_event_payload(payload.get("route_reference"))
        fingerprint = str(payload.get("route_fingerprint") or "")
        if (
            record.event.event_id != f"host.route-bound:{binding_id}"
            or record.event.subject != subject
            or capability not in _CAPABILITIES
            or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)
        ):
            raise HostCapabilityError("route binding identity is invalid")
        revoked = self.journal.get(f"host.route-revoked:{binding_id}")
        active = not self._valid_revocation(revoked, binding_id, record.event.event_id, subject)
        return RouteBinding(
            binding_id,
            record.event.event_id,
            subject,
            capability,
            str(payload.get("snapshot_event_id") or ""),
            reference,
            fingerprint,
            authenticator,
            active,
            record.event.observed_at,
            requirement,
        )

    def _valid_revocation(
        self,
        record: JournalRecord | None,
        binding_id: str,
        binding_event_id: str,
        subject: str,
    ) -> bool:
        if record is None or record.event.event_type != "host.route_revoked":
            return False
        payload = _thaw_json(record.event.payload)
        authenticator = payload.pop("integrity_authenticator", None)
        return bool(
            record.event.subject == subject
            and payload.get("binding_id") == binding_id
            and payload.get("binding_event_id") == binding_event_id
            and self.protector.verify_json(self.REVOKE_NAMESPACE, payload, authenticator)
        )

    def get_binding(self, binding_id: str) -> RouteBinding | None:
        try:
            return self._parse_binding(self.journal.get(f"host.route-bound:{binding_id}"))
        except HostCapabilityError:
            return None

    def revoke_route(
        self,
        binding_id: str,
        *,
        observed_at: datetime | None = None,
    ) -> str:
        binding = self.get_binding(binding_id)
        if binding is None:
            raise HostCapabilityError("route binding is unavailable")
        if not binding.active:
            return f"host.route-revoked:{binding.binding_id}"
        current = self._utc(observed_at)
        payload: dict[str, object] = {
            "schema_version": 1,
            "binding_id": binding.binding_id,
            "binding_event_id": binding.event_id,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            self.REVOKE_NAMESPACE, payload
        )
        event = EventEnvelope(
            event_id=f"host.route-revoked:{binding.binding_id}",
            event_type="host.route_revoked",
            source="alive.host-bridge",
            actor="system:alive-route-authority",
            subject=binding.subject,
            causation_id=binding.event_id,
            occurred_at=current,
            observed_at=current,
            sensitivity=Sensitivity.PRIVATE,
            payload=payload,
        )
        try:
            self.journal.append(event)
        except EventConflictError as exc:
            raise HostCapabilityError("route revocation identity was reused") from exc
        return event.event_id

    def execution_binding(
        self,
        binding_id: str,
        *,
        subject: str,
        capability: str,
        as_of: datetime | None = None,
    ) -> tuple[RouteBinding | None, tuple[str, ...]]:
        """Require the exact user-selected evidence contract, never invent delivery.

        Legacy bindings still require external delivery evidence. An explicitly
        authorized v2 submission-only route permits a send attempt, not a claim
        that the remote party received it or a retry of an uncertain action.
        """

        reasons: list[str] = []
        binding = self.get_binding(binding_id)
        if binding is None:
            return None, ("route_binding_unavailable",)
        if not binding.active:
            reasons.append("route_binding_revoked")
        if binding.subject != subject:
            reasons.append("route_subject_mismatch")
        if binding.capability != capability:
            reasons.append("route_capability_mismatch")
        snapshot = self.latest_snapshot(as_of=as_of)
        if snapshot is None:
            reasons.append("host_capability_snapshot_unavailable")
        elif snapshot.event_id != binding.snapshot_event_id:
            reasons.append("host_capability_snapshot_stale")
        else:
            claim = snapshot.claim(capability)
            if claim is None or not claim.available:
                reasons.append("host_capability_unavailable")
            elif not claim.public_api:
                reasons.append("host_capability_private_api")
            else:
                levels = (ReceiptLevel.REQUEST_ACCEPTED, ReceiptLevel.TURN_COMPLETED,
                          ReceiptLevel.EXTERNAL_DELIVERED)
                if levels.index(claim.receipt_level) < levels.index(binding.receipt_requirement):
                    reasons.append("host_terminal_receipt_unavailable" if
                        binding.receipt_requirement is ReceiptLevel.EXTERNAL_DELIVERED else
                        "host_receipt_requirement_unsatisfied")
        try:
            route = self.vault.resolve_json(
                binding.route_reference.content_id,
                expected_subject=binding.subject,
                expected_purpose="host.route.binding",
                expected_sensitivity=Sensitivity.PRIVATE,
            )
            normalized = self._route_document(route)
            if not self.protector.verify_json(
                "host.route.locator.v1", normalized, binding.route_fingerprint
            ):
                reasons.append("route_binding_content_mismatch")
        except (
            ContentErasedError,
            ContentIntegrityError,
            ContentUnavailableError,
            HostCapabilityError,
        ):
            reasons.append("route_binding_content_unavailable")
        return (binding if not reasons else None), tuple(dict.fromkeys(reasons))

    def resolve_route(self, binding: RouteBinding) -> dict[str, str | None]:
        """Resolve a previously revalidated binding for a trusted adapter only."""

        current, reasons = self.execution_binding(
            binding.binding_id,
            subject=binding.subject,
            capability=binding.capability,
        )
        if current is None:
            raise HostCapabilityError(",".join(reasons))
        value = self.vault.resolve_json(
            current.route_reference.content_id,
            expected_subject=current.subject,
            expected_purpose="host.route.binding",
            expected_sensitivity=Sensitivity.PRIVATE,
        )
        return self._route_document(value)
