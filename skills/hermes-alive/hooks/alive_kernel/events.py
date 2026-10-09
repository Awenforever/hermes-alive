"""Typed, immutable facts for the Hermes Alive experience journal."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


_EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9_-]+)+$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")


class EventValidationError(ValueError):
    """The event cannot cross the kernel ingestion boundary."""


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    RESTRICTED = "restricted"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventValidationError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _identity(value: str | None, field_name: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise EventValidationError(f"{field_name} is required")
        return None
    normalized = str(value).strip()
    if not normalized and not required:
        return None
    if not _IDENTITY_RE.fullmatch(normalized):
        raise EventValidationError(f"invalid {field_name}")
    return normalized


def _json_value(value: Any, path: str = "payload") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EventValidationError(f"{path} contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise EventValidationError(f"{path} contains a non-string key")
            normalized[key] = _json_value(item, f"{path}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{path}[]") for item in value]
    raise EventValidationError(f"{path} contains unsupported type {type(value).__name__}")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """One immutable observation or outcome in the Alive causal history."""

    event_type: str
    source: str
    actor: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utc_now)
    observed_at: datetime = field(default_factory=utc_now)
    subject: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    schema_version: int = 1
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    confidence: float = 1.0
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        event_type = str(self.event_type).strip().lower()
        if not _EVENT_TYPE_RE.fullmatch(event_type):
            raise EventValidationError(
                "event_type must be namespaced, for example conversation.inbound"
            )
        object.__setattr__(self, "event_type", event_type)
        for name in ("event_id", "source", "actor"):
            object.__setattr__(self, name, _identity(getattr(self, name), name, required=True))
        for name in ("subject", "correlation_id", "causation_id"):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        if self.schema_version < 1:
            raise EventValidationError("schema_version must be positive")
        confidence = float(self.confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise EventValidationError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "occurred_at", _utc(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        if self.expires_at is not None:
            object.__setattr__(self, "expires_at", _utc(self.expires_at, "expires_at"))
        try:
            sensitivity = Sensitivity(self.sensitivity)
        except ValueError as exc:
            raise EventValidationError("invalid sensitivity") from exc
        object.__setattr__(self, "sensitivity", sensitivity)
        payload = _json_value(self.payload)
        # A canonical round trip prevents mutable caller-owned nested values.
        detached_payload = json.loads(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        object.__setattr__(self, "payload", _freeze_json(detached_payload))

    def with_observed_at(self, value: datetime) -> "EventEnvelope":
        return replace(self, observed_at=value)

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "causation_id": self.causation_id,
            "confidence": self.confidence,
            "correlation_id": self.correlation_id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "observed_at": self.observed_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat(),
            "payload": _thaw_json(self.payload),
            "schema_version": self.schema_version,
            "sensitivity": self.sensitivity.value,
            "source": self.source,
            "subject": self.subject,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def from_canonical_dict(cls, value: Mapping[str, Any]) -> "EventEnvelope":
        def parsed(name: str) -> datetime | None:
            raw = value.get(name)
            return datetime.fromisoformat(str(raw)) if raw else None

        return cls(
            event_id=str(value["event_id"]),
            event_type=str(value["event_type"]),
            source=str(value["source"]),
            actor=str(value["actor"]),
            subject=value.get("subject"),
            correlation_id=value.get("correlation_id"),
            causation_id=value.get("causation_id"),
            occurred_at=parsed("occurred_at") or utc_now(),
            observed_at=parsed("observed_at") or utc_now(),
            schema_version=int(value.get("schema_version", 1)),
            sensitivity=Sensitivity(value.get("sensitivity", Sensitivity.INTERNAL.value)),
            confidence=float(value.get("confidence", 1.0)),
            expires_at=parsed("expires_at"),
            payload=value.get("payload") or {},
        )
