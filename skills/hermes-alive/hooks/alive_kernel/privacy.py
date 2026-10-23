"""Privacy boundary for events entering the Alive kernel.

Phase 1 mirrors only structural hook facts. Raw conversation text, credentials
and platform identifiers are deliberately not admitted to the journal.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping


_SECRET_KEY_RE = re.compile(
    r"(?:api[_-]?key|authorization|bearer|cookie|credential|password|secret|token)",
    re.IGNORECASE,
)
_ID_KEYS = (
    "event_id",
    "message_id",
    "session_id",
    "conversation_id",
    "thread_id",
    "chat_id",
    "user_id",
)
_PLATFORM_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class LocalIdentityProtector:
    """Create stable, installation-local pseudonyms for external identifiers."""

    def __init__(self, key_path: str | Path) -> None:
        self.key_path = Path(key_path).expanduser().resolve()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_create()

    def _load_or_create(self) -> bytes:
        try:
            existing = self.key_path.read_bytes()
        except FileNotFoundError:
            pass
        else:
            if len(existing) < 32:
                raise RuntimeError('Alive identity key is invalid')
            return existing
        key = os.urandom(32)
        try:
            descriptor = os.open(
                self.key_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(key)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            key = self.key_path.read_bytes()
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            # Windows and some network filesystems do not expose POSIX modes.
            pass
        if len(key) < 32:
            raise RuntimeError("Alive identity key is invalid")
        return key

    def pseudonym(self, namespace: str, raw_value: Any) -> str | None:
        text = str(raw_value or "").strip()
        if not text:
            return None
        digest = hmac.new(
            self._key,
            f"{namespace}\0{text}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:32]
        return f"{namespace}:{digest}"

    def authenticate_json(self, namespace: str, value: Any) -> str:
        """Authenticate one canonical JSON value without exposing the key."""

        canonical = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return hmac.new(
            self._key,
            f"{namespace}\0{canonical}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify_json(self, namespace: str, value: Any, authenticator: Any) -> bool:
        supplied = str(authenticator or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", supplied):
            return False
        expected = self.authenticate_json(namespace, value)
        return hmac.compare_digest(expected, supplied)


def _find_value(context: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = context.get(name)
        if value is not None and str(value).strip():
            return value
    for nested_name in ("event", "session", "message", "request", "metadata", "context"):
        nested = context.get(nested_name)
        if isinstance(nested, Mapping):
            value = _find_value(nested, names)
            if value is not None:
                return value
    return None


def _schema_keys(context: Mapping[str, Any]) -> list[str]:
    keys: set[str] = set()
    for key in context:
        normalized = str(key).strip().lower()
        if not normalized or _SECRET_KEY_RE.search(normalized):
            continue
        # Key names are structural diagnostics only. Bound them so attacker-
        # controlled objects cannot turn this into an alternate content store.
        keys.add(normalized[:64])
    return sorted(keys)[:64]


def structural_hook_payload(
    event_name: str,
    context: Mapping[str, Any] | None,
    protector: LocalIdentityProtector,
) -> dict[str, Any]:
    """Return a bounded payload that contains no raw text or external IDs."""

    safe_context = context if isinstance(context, Mapping) else {}
    platform_raw = _find_value(safe_context, ("platform", "source", "channel"))
    platform = str(platform_raw or "").strip().lower()
    if not _PLATFORM_RE.fullmatch(platform):
        platform = "unknown"

    identities: dict[str, str] = {}
    for key in _ID_KEYS:
        raw = _find_value(safe_context, (key,))
        pseudonym = protector.pseudonym(key.removesuffix("_id"), raw)
        if pseudonym:
            identities[key] = pseudonym

    return {
        "hook_event": event_name,
        "platform": platform,
        "identities": identities,
        "context_schema_keys": _schema_keys(safe_context),
        "raw_content_stored": False,
        "privacy_policy": "structural-hook-v1",
    }


def assert_no_obvious_secret(payload: Any) -> None:
    """Fail closed if a future adapter accidentally emits secret-shaped keys."""

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if _SECRET_KEY_RE.search(str(key)):
                raise ValueError(f"secret-shaped key rejected: {key}")
            assert_no_obvious_secret(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            assert_no_obvious_secret(item)
