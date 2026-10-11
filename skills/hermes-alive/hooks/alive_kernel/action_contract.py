"""Versioned, destination-free action contracts for Hermes capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


class ActionContractError(ValueError):
    """A candidate tried to cross a capability boundary with an unsafe shape."""


@dataclass(frozen=True, slots=True)
class ActionContract:
    schema_version: int
    capability: str
    operation: Mapping[str, Any]

    def to_document(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "capability": self.capability,
            "operation": dict(self.operation),
        }


_CHANNEL_FORMATS = frozenset({"plain", "markdown"})
_CHANNEL_TOP_LEVEL = frozenset({"schema_version", "capability", "operation"})
_CHANNEL_OPERATION = frozenset({"text", "format"})


def parse_action_contract(document: object, *, capability: str) -> ActionContract:
    """Validate one kernel action without accepting transport routing from content.

    Only the channel-send contract is executable today. Tool execution and
    internal review need their own separately reviewed schemas before they can
    cross the outbox boundary.
    """

    expected = str(capability).strip()
    if expected != "hermes.channel.send":
        raise ActionContractError("capability contract is not implemented")
    if not isinstance(document, dict):
        raise ActionContractError("action contract must be an object")
    if frozenset(document) != _CHANNEL_TOP_LEVEL:
        raise ActionContractError("action contract fields are invalid")
    if (
        type(document.get("schema_version")) is not int
        or document["schema_version"] != 1
    ):
        raise ActionContractError("unsupported action contract version")
    if document.get("capability") != expected:
        raise ActionContractError("action contract capability mismatch")
    operation = document.get("operation")
    if not isinstance(operation, dict) or frozenset(operation) != _CHANNEL_OPERATION:
        raise ActionContractError("channel operation fields are invalid")
    text = operation.get("text")
    message_format = operation.get("format")
    if not isinstance(text, str) or not text.strip() or len(text) > 12_000:
        raise ActionContractError("channel text must contain 1 to 12000 characters")
    if message_format not in _CHANNEL_FORMATS:
        raise ActionContractError("channel format must be plain or markdown")
    normalized: dict[str, object] = {
        "schema_version": 1,
        "capability": expected,
        "operation": {
            "text": text,
            "format": message_format,
        },
    }
    return ActionContract(
        schema_version=1,
        capability=expected,
        operation=MappingProxyType(dict(normalized["operation"])),
    )
