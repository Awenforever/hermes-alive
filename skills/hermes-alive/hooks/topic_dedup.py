# Hermes Alive cross-tick Discovery topic and URL deduplication.
# Marker: HERMES_ALIVE_DISCOVERY_TOPIC_DEDUP_V1
# Marker: HERMES_ALIVE_CANONICAL_URL_HISTORY_V1
# Marker: HERMES_ALIVE_TOPIC_UNIT_RESERVATION_V1
# Marker: HERMES_ALIVE_CANONICAL_URL_HARDENING_V2
# Marker: HERMES_ALIVE_TOPIC_HISTORY_RECOVERY_V1

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

DEFAULT_BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
DEFAULT_COOLDOWN_HOURS = float(os.getenv("HERMES_ALIVE_TOPIC_COOLDOWN_HOURS", "24"))
DEFAULT_RESERVATION_TTL_SECONDS = float(
    os.getenv("HERMES_ALIVE_TOPIC_RESERVATION_TTL_SECONDS", "900")
)
DEFAULT_HISTORY_RETENTION_DAYS = float(
    os.getenv("HERMES_ALIVE_TOPIC_HISTORY_RETENTION_DAYS", "90")
)
DEFAULT_MAX_ENTRIES = int(os.getenv("HERMES_ALIVE_TOPIC_HISTORY_MAX_ENTRIES", "2000"))

_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
    "spm",
    "yclid",
}
_TRACKING_PREFIXES = ("utm_", "pk_", "mkt_", "vero_")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def _now() -> float:
    return time.time()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


_UNRESERVED_URL_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)
_PERCENT_ESCAPE_RE = re.compile(r"%([0-9A-Fa-f]{2})")


def _normalize_percent_encoding(value: str) -> str:
    """Decode percent-encoded RFC 3986 unreserved bytes and normalize others."""
    def replace(match: re.Match[str]) -> str:
        byte = int(match.group(1), 16)
        char = chr(byte)
        if char in _UNRESERVED_URL_CHARS:
            return char
        return "%" + match.group(1).upper()

    return _PERCENT_ESCAPE_RE.sub(replace, value)


def _coerce_state(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    delivered = value.get("delivered")
    reservations = value.get("reservations")
    if not isinstance(delivered, list) or not isinstance(reservations, list):
        return None
    return {
        "schema_version": 1,
        "delivered": [entry for entry in delivered if isinstance(entry, dict)],
        "reservations": [entry for entry in reservations if isinstance(entry, dict)],
    }


def canonicalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urlsplit(raw)
    except Exception:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""

    # Treat HTTP and HTTPS as one public content identity. Delivery still uses
    # the collector-provided URL; this value is only for deduplication.
    scheme = "https"
    host = parsed.hostname.rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except Exception:
        pass
    try:
        port = parsed.port
    except ValueError:
        return ""
    host_for_netloc = f"[{host}]" if ":" in host else host
    netloc = host_for_netloc
    if port and port not in {80, 443}:
        netloc = f"{host_for_netloc}:{port}"

    path = _normalize_percent_encoding(parsed.path or "/")
    path = quote(path, safe="/:@-._~!$&'()*+,;=%")
    path = re.sub(r"/{2,}", "/", path)
    if path != "/":
        path = path.rstrip("/")

    query: list[tuple[str, str]] = []
    for key, item_value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in _TRACKING_KEYS or lowered.startswith(_TRACKING_PREFIXES):
            continue
        query.append((key, item_value))
    query.sort(key=lambda pair: (pair[0], pair[1]))

    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ""))


def _normalized_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff+#.]+", " ", text)
    return " ".join(text.split())


def item_identity(item: dict[str, Any]) -> dict[str, str]:
    url = canonicalize_url(
        item.get("url") or item.get("link") or item.get("href")
    )
    url_hash = _sha("url:" + url) if url else ""
    title = _normalized_text(item.get("title"))
    source = _normalized_text(item.get("source"))
    summary = _normalized_text(
        item.get("summary") or item.get("description")
    )
    topic_basis = title if len(title) >= 8 else " ".join(x for x in (source, title) if x)
    topic_signature = _sha("topic:" + topic_basis) if topic_basis else ""
    content_identity = url_hash or topic_signature or _sha(
        "fallback:" + _normalized_text(json.dumps(item, ensure_ascii=False, sort_keys=True))
    )
    topic_unit_id = _sha("unit:" + (url_hash or topic_signature or content_identity))
    update_basis = "|".join(
        (
            url_hash,
            title,
            summary,
            _normalized_text(item.get("published_at")),
            _normalized_text(item.get("updated_at")),
            _normalized_text(item.get("version")),
            _normalized_text(item.get("update_token")),
        )
    )
    update_fingerprint = _sha("update:" + update_basis)
    return {
        "canonical_url_hash": url_hash,
        "topic_signature": topic_signature,
        "content_identity": content_identity,
        "topic_unit_id": topic_unit_id,
        "update_fingerprint": update_fingerprint,
    }


@dataclass(frozen=True)
class TopicDecision:
    allowed: bool
    reason: str
    identity: dict[str, str]
    reservation_id: str = ""
    age_seconds: float | None = None

    @property
    def blocked(self) -> bool:
        return not self.allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked": self.blocked,
            "reason": self.reason,
            "reservation_id": self.reservation_id,
            "age_seconds": self.age_seconds,
            **self.identity,
        }


class TopicDedupStore:
    def __init__(
        self,
        base_dir: Path | str | None = None,
        *,
        cooldown_hours: float | None = None,
        reservation_ttl_seconds: float | None = None,
    ) -> None:
        self.base = Path(base_dir) if base_dir is not None else DEFAULT_BASE
        self.state_path = self.base / "state" / "topic_delivery_history.json"
        self.backup_path = self.base / "state" / "topic_delivery_history.json.bak"
        self.lock_path = self.base / "locks" / "topic_delivery_history.lock"
        self.cooldown_seconds = max(
            60.0,
            float(DEFAULT_COOLDOWN_HOURS if cooldown_hours is None else cooldown_hours) * 3600.0,
        )
        self.reservation_ttl_seconds = max(
            30.0,
            float(
                DEFAULT_RESERVATION_TTL_SECONDS
                if reservation_ttl_seconds is None
                else reservation_ttl_seconds
            ),
        )
        self.retention_seconds = max(86400.0, DEFAULT_HISTORY_RETENTION_DAYS * 86400.0)
        self.max_entries = max(100, DEFAULT_MAX_ENTRIES)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _default_state(self) -> dict[str, Any]:
        return {"schema_version": 1, "delivered": [], "reservations": []}

    def _read_state(self) -> dict[str, Any]:
        existing_paths = [path for path in (self.state_path, self.backup_path) if path.exists()]
        if not existing_paths:
            return self._default_state()
        for path in existing_paths:
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            state = _coerce_state(value)
            if state is not None:
                return state
        return {
            **self._default_state(),
            "history_unreadable": True,
        }

    def _atomic_write_path(self, path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=path.name + ".",
            dir=str(path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def _write_state(self, state: dict[str, Any]) -> None:
        if state.get("history_unreadable"):
            return
        persisted = {
            "schema_version": 1,
            "delivered": state.get("delivered", []),
            "reservations": state.get("reservations", []),
        }
        payload = json.dumps(persisted, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        # Write the backup first so a process interruption always leaves at
        # least one complete state file.
        self._atomic_write_path(self.backup_path, payload)
        self._atomic_write_path(self.state_path, payload)

    def _prune(self, state: dict[str, Any], now: float) -> None:
        state["reservations"] = [
            entry
            for entry in state["reservations"]
            if now - float(entry.get("reserved_at", 0.0)) <= self.reservation_ttl_seconds
        ][-self.max_entries :]
        state["delivered"] = [
            entry
            for entry in state["delivered"]
            if now - float(entry.get("delivered_at", 0.0)) <= self.retention_seconds
        ][-self.max_entries :]

    def _same_topic(self, entry: dict[str, Any], identity: dict[str, str]) -> bool:
        url_hash = identity.get("canonical_url_hash")
        topic_signature = identity.get("topic_signature")
        return bool(
            entry.get("content_identity") == identity.get("content_identity")
            or (url_hash and entry.get("canonical_url_hash") == url_hash)
            or (topic_signature and entry.get("topic_signature") == topic_signature)
        )

    def _evaluate(
        self,
        state: dict[str, Any],
        item: dict[str, Any],
        *,
        now: float,
        include_reservations: bool,
        own_reservation_id: str = "",
    ) -> TopicDecision:
        identity = item_identity(item)
        if state.get("history_unreadable"):
            return TopicDecision(False, "topic_history_unreadable_fail_closed", identity)
        material_update = _truthy(item.get("material_update"))
        update_fingerprint = identity["update_fingerprint"]

        if include_reservations:
            for entry in reversed(state["reservations"]):
                if own_reservation_id and entry.get("reservation_id") == own_reservation_id:
                    continue
                if self._same_topic(entry, identity):
                    return TopicDecision(False, "topic_reserved_by_another_tick", identity)

        for entry in reversed(state["delivered"]):
            if not self._same_topic(entry, identity):
                continue
            age = max(0.0, now - float(entry.get("delivered_at", 0.0)))
            if age >= self.cooldown_seconds:
                continue
            if material_update and entry.get("update_fingerprint") != update_fingerprint:
                return TopicDecision(True, "material_update_allowed", identity, age_seconds=age)
            return TopicDecision(False, "topic_delivered_within_cooldown", identity, age_seconds=age)

        return TopicDecision(True, "topic_available", identity)

    def check(
        self,
        item: dict[str, Any],
        *,
        include_reservations: bool = True,
        now: float | None = None,
    ) -> TopicDecision:
        current = _now() if now is None else float(now)
        with self._lock():
            state = self._read_state()
            self._prune(state, current)
            decision = self._evaluate(
                state,
                item,
                now=current,
                include_reservations=include_reservations,
            )
            self._write_state(state)
            return decision

    def reserve(
        self,
        item: dict[str, Any],
        *,
        tick_id: str,
        now: float | None = None,
    ) -> TopicDecision:
        current = _now() if now is None else float(now)
        with self._lock():
            state = self._read_state()
            self._prune(state, current)
            decision = self._evaluate(
                state,
                item,
                now=current,
                include_reservations=True,
            )
            if decision.blocked:
                self._write_state(state)
                return decision
            reservation_id = uuid.uuid4().hex
            state["reservations"].append(
                {
                    **decision.identity,
                    "reservation_id": reservation_id,
                    "reserved_at": current,
                    "tick_id_hash": _sha(str(tick_id or ""))[:20],
                }
            )
            self._write_state(state)
            return TopicDecision(
                True,
                decision.reason,
                decision.identity,
                reservation_id=reservation_id,
                age_seconds=decision.age_seconds,
            )

    def validate_reservation(
        self,
        item: dict[str, Any],
        *,
        reservation_id: str,
        now: float | None = None,
    ) -> TopicDecision:
        current = _now() if now is None else float(now)
        identity = item_identity(item)
        with self._lock():
            state = self._read_state()
            self._prune(state, current)
            matching = next(
                (
                    entry
                    for entry in state["reservations"]
                    if entry.get("reservation_id") == reservation_id
                    and self._same_topic(entry, identity)
                ),
                None,
            )
            if matching is None:
                self._write_state(state)
                return TopicDecision(False, "topic_reservation_missing_or_expired", identity)
            decision = self._evaluate(
                state,
                item,
                now=current,
                include_reservations=True,
                own_reservation_id=reservation_id,
            )
            self._write_state(state)
            if decision.blocked:
                return decision
            return TopicDecision(
                True,
                "topic_reservation_valid",
                identity,
                reservation_id=reservation_id,
                age_seconds=decision.age_seconds,
            )

    def commit_delivery(
        self,
        item: dict[str, Any],
        *,
        tick_id: str | None = None,
        reservation_id: str = "",
        now: float | None = None,
    ) -> TopicDecision:
        current = _now() if now is None else float(now)
        identity = item_identity(item)
        with self._lock():
            state = self._read_state()
            self._prune(state, current)
            if state.get("history_unreadable"):
                return TopicDecision(
                    False,
                    "topic_history_unreadable_fail_closed",
                    identity,
                )
            if reservation_id:
                state["reservations"] = [
                    entry
                    for entry in state["reservations"]
                    if entry.get("reservation_id") != reservation_id
                ]
            # Idempotent for repeated bookkeeping of the same actual send.
            state["delivered"] = [
                entry
                for entry in state["delivered"]
                if not (
                    self._same_topic(entry, identity)
                    and entry.get("update_fingerprint") == identity["update_fingerprint"]
                    and abs(current - float(entry.get("delivered_at", 0.0))) < 5.0
                )
            ]
            state["delivered"].append(
                {
                    **identity,
                    "delivered_at": current,
                    "tick_id_hash": _sha(str(tick_id or ""))[:20],
                }
            )
            self._prune(state, current)
            self._write_state(state)
        return TopicDecision(True, "topic_delivery_committed", identity)

    def release(
        self,
        *,
        reservation_id: str,
    ) -> None:
        if not reservation_id:
            return
        with self._lock():
            state = self._read_state()
            if state.get("history_unreadable"):
                return
            state["reservations"] = [
                entry
                for entry in state["reservations"]
                if entry.get("reservation_id") != reservation_id
            ]
            self._write_state(state)

    def filter_candidates(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        allowed: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        batch_units: set[str] = set()
        for raw in items:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            identity = item_identity(item)
            item.update(identity)
            unit = identity["topic_unit_id"]
            if unit in batch_units:
                rejected.append({"reason": "duplicate_within_discovery_batch", **identity})
                continue
            decision = self.check(item, include_reservations=True)
            if decision.blocked:
                rejected.append(decision.to_dict())
                continue
            batch_units.add(unit)
            allowed.append(item)
        return allowed, rejected
