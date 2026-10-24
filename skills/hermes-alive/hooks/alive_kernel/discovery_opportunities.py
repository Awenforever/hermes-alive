"""Discovery ingestion boundary for the Alive kernel.

Collectors report observations here.  This module may persist evidence and
propose an opportunity, but it deliberately cannot compose, route, reserve, or
send a message.  Those decisions belong to later cognition and authorization
stages.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hmac
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .agenda import (
    AgendaAuthority,
    AgendaContentStatus,
    AgendaDecision,
    AgendaItemKind,
    AgendaProjection,
    AgendaProposal,
    AgendaState,
)
from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
)
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _freeze_json, _thaw_json
from .privacy import LocalIdentityProtector


_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
}
_MAX_ATTRIBUTES_BYTES = 8_192
_MAX_RETENTION = timedelta(days=30)
_DEFAULT_RETENTION = timedelta(days=7)


class DiscoveryOpportunityError(ValueError):
    """A collector value cannot cross the discovery/kernel boundary."""


def _utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise DiscoveryOpportunityError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _bounded(value: Any, name: str, limit: int, *, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise DiscoveryOpportunityError(f"{name} is required")
    if len(text) > limit:
        raise DiscoveryOpportunityError(f"{name} exceeds {limit} characters")
    return text


def _finite_unit(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise DiscoveryOpportunityError(f"{name} must be between 0 and 1")
    return number


def _json(value: Any) -> Any:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DiscoveryOpportunityError("attributes must be finite JSON") from exc
    if len(encoded) > _MAX_ATTRIBUTES_BYTES:
        raise DiscoveryOpportunityError("attributes exceed the discovery boundary")
    return json.loads(encoded.decode("utf-8"))


def canonicalize_discovery_url(value: Any) -> str:
    """Return a conservative identity URL, never a permissive fetch target."""

    raw = _bounded(value, "url", 4_096, required=True)
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise DiscoveryOpportunityError("url must be an absolute HTTP(S) URL")
    host = parts.hostname.encode("idna").decode("ascii").lower()
    port = parts.port
    netloc = host
    if port is not None and not (
        (parts.scheme.lower() == "http" and port == 80)
        or (parts.scheme.lower() == "https" and port == 443)
    ):
        netloc = f"{host}:{port}"
    path = parts.path or "/"
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in _TRACKING_QUERY_KEYS
        ),
        doseq=True,
    )
    return urlunsplit((parts.scheme.lower(), netloc, path, query, ""))


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """One collector observation, before any decision to interrupt the user."""

    source: str
    title: str
    url: str
    summary: str = ""
    external_id: str = ""
    published_at: datetime | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    confidence: float = 0.5
    priority_hint: float = 0.5
    attributes: Any = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _bounded(self.source, "source", 256, required=True))
        object.__setattr__(self, "title", _bounded(self.title, "title", 1_024, required=True))
        object.__setattr__(self, "summary", _bounded(self.summary, "summary", 8_192))
        object.__setattr__(self, "external_id", _bounded(self.external_id, "external_id", 1_024))
        object.__setattr__(self, "url", canonicalize_discovery_url(self.url))
        observed = _utc(self.observed_at, "observed_at")
        published = _utc(self.published_at, "published_at")
        expires = _utc(self.expires_at, "expires_at") or (observed + _DEFAULT_RETENTION)
        if expires <= observed or expires - observed > _MAX_RETENTION:
            raise DiscoveryOpportunityError("expires_at must be within 30 days")
        if published is not None and published > observed + timedelta(minutes=10):
            raise DiscoveryOpportunityError("published_at is implausibly in the future")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "published_at", published)
        object.__setattr__(self, "expires_at", expires)
        object.__setattr__(self, "confidence", _finite_unit(self.confidence, "confidence"))
        object.__setattr__(self, "priority_hint", _finite_unit(self.priority_hint, "priority_hint"))
        object.__setattr__(self, "attributes", _json(self.attributes))

    def entity_document(self, subject: str) -> dict[str, Any]:
        return {
            "subject": subject,
            "source": self.source,
            "external_id": self.external_id,
            "url": self.url if not self.external_id else "",
        }

    def content_document(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "external_id": self.external_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "attributes": self.attributes,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryIngestResult:
    observation_event_id: str
    agenda_item_id: str
    observation_created: bool
    material_update: bool
    agenda_decision: AgendaDecision
    superseded_agenda_item_id: str | None


@dataclass(frozen=True, slots=True)
class DiscoveryProjectionRecord:
    entity_fingerprint: str
    version_fingerprint: str
    observation_event_id: str
    agenda_item_id: str
    sequence: int


@dataclass(frozen=True, slots=True)
class OpportunityEvidence:
    agenda_item_id: str
    observation_event_id: str
    expires_at: datetime
    sensitivity: Sensitivity
    content: Any = field(repr=False)


@dataclass(frozen=True, slots=True)
class DiscoveryShadowReport:
    observed: int
    deduplicated: int
    updated: int
    rejected: int
    source_failures: int


def discovery_shadow_enabled(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    truthy = {"1", "true", "yes", "on", "enabled"}
    return (
        str(values.get("HERMES_ALIVE_KERNEL_SHADOW_ENABLED", "false")).strip().lower()
        in truthy
        and str(
            values.get("HERMES_ALIVE_DISCOVERY_KERNEL_SHADOW_ENABLED", "false")
        ).strip().lower()
        in truthy
    )


class DiscoveryOpportunityIngestor:
    """Persist discovery evidence and active opportunities without side effects."""

    CHECKPOINT = "alive-discovery-opportunities-v1"

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
        self.agenda = AgendaProjection(journal, content_vault=self.vault)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.journal.path, timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS discovery_projection_v1 (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    checkpoint_sequence INTEGER NOT NULL,
                    entity_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO discovery_projection_v1
                    (singleton, checkpoint_sequence, entity_count, updated_at)
                VALUES (1, 0, 0, '1970-01-01T00:00:00+00:00');
                CREATE TABLE IF NOT EXISTS discovery_entities_v1 (
                    entity_fingerprint TEXT PRIMARY KEY,
                    version_fingerprint TEXT NOT NULL,
                    observation_event_id TEXT NOT NULL UNIQUE,
                    agenda_item_id TEXT NOT NULL UNIQUE,
                    sequence INTEGER NOT NULL UNIQUE,
                    row_authenticator TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_discovery_entities_sequence_v1
                    ON discovery_entities_v1(sequence);
                COMMIT;
                """
            )
        if not self.validate_projection():
            self.rebuild_projection()

    def _row_document(self, row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "entity_fingerprint": str(row["entity_fingerprint"]),
            "version_fingerprint": str(row["version_fingerprint"]),
            "observation_event_id": str(row["observation_event_id"]),
            "agenda_item_id": str(row["agenda_item_id"]),
            "sequence": int(row["sequence"]),
        }

    def _row_authenticator(self, row: Mapping[str, Any]) -> str:
        return self.vault.digest_json({"projection": "discovery.entity.v1", **self._row_document(row)})

    def _valid_observation(self, record: JournalRecord) -> bool:
        event = record.event
        payload = event.payload
        if not (
            event.event_type == "discovery.opportunity_observed"
            and event.source == "alive.discovery"
            and event.actor == "system:alive-discovery"
            and event.subject
            and event.expires_at
            and payload.get("raw_content_stored") is False
        ):
            return False
        try:
            reference = ContentReference.from_event_payload(payload["content"])
            if reference.sensitivity is not event.sensitivity:
                return False
            values = (
                str(payload["entity_fingerprint"]),
                str(payload["version_fingerprint"]),
                str(payload["agenda_item_id"]),
            )
            if not all(_IDENTITY_RE.fullmatch(value) for value in values):
                return False
            authenticated = _thaw_json(payload)
            supplied = str(authenticated.pop("integrity_authenticator", ""))
            expected = "auth:" + self.vault.digest_json(
                {"contract": "discovery.observation.v1", "payload": authenticated}
            )
            if not hmac.compare_digest(supplied, expected):
                return False
            document = self.vault.resolve_json(
                reference.content_id,
                expected_subject=event.subject,
                expected_purpose="discovery.observation",
                expected_sensitivity=event.sensitivity,
            )
            source = str(document.get("source") or "")
            external_id = str(document.get("external_id") or "")
            url = str(document.get("url") or "")
            expected_entity = "entity:" + self.vault.digest_json(
                {
                    "subject": event.subject,
                    "source": source,
                    "external_id": external_id,
                    "url": url if not external_id else "",
                }
            )[:40]
            expected_version = "version:" + self.vault.digest_json(
                {"entity_fingerprint": expected_entity, "content": document}
            )[:40]
            return bool(
                payload.get("entity_fingerprint") == expected_entity
                and payload.get("version_fingerprint") == expected_version
                and payload.get("source_fingerprint")
                == "source:" + self.vault.digest_json(source)[:40]
            )
        except ContentErasedError:
            return True
        except (KeyError, TypeError, ValueError, ContentIntegrityError, ContentUnavailableError):
            return False

    def validate_projection(self) -> bool:
        try:
            checkpoint = self.projection_checkpoint()
            if checkpoint > self.journal.last_sequence():
                return False
            with closing(self._connect()) as connection:
                metadata = connection.execute(
                    "SELECT entity_count FROM discovery_projection_v1 WHERE singleton=1"
                ).fetchone()
                rows = connection.execute(
                    "SELECT * FROM discovery_entities_v1 ORDER BY sequence"
                ).fetchall()
            if (
                metadata is None
                or int(metadata["entity_count"]) != len(rows)
                or any(int(row["sequence"]) > checkpoint for row in rows)
            ):
                return False
            for row in rows:
                document = self._row_document(row)
                if self._row_authenticator(document) != row["row_authenticator"]:
                    return False
                record = self.journal.get(document["observation_event_id"])
                if record is None or record.sequence != document["sequence"] or not self._valid_observation(record):
                    return False
                payload = record.event.payload
                if any(
                    str(payload[key]) != document[key]
                    for key in ("entity_fingerprint", "version_fingerprint", "agenda_item_id")
                ):
                    return False
            return True
        except (KeyError, TypeError, ValueError, sqlite3.DatabaseError):
            return False

    def projection_checkpoint(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT checkpoint_sequence FROM discovery_projection_v1 WHERE singleton=1"
            ).fetchone()
        if row is None:
            raise DiscoveryOpportunityError("discovery projection metadata is missing")
        return int(row["checkpoint_sequence"])

    def project_new(self, *, batch_size: int = 500) -> int:
        if not 1 <= batch_size <= 10_000:
            raise DiscoveryOpportunityError("batch_size must be between 1 and 10000")
        watermark = self.journal.last_sequence()
        indexed = 0
        while True:
            checkpoint = self.projection_checkpoint()
            # Observe completion and choose the replay cursor from the same
            # checkpoint read. Another projector may have reached the watermark
            # between two reads; an empty replay at that new cursor is success,
            # not evidence loss. The commit-time comparison still fences writers.
            if checkpoint >= watermark:
                break
            records = []
            for record in self.journal.iter_replay(after_sequence=checkpoint, batch_size=batch_size):
                if record.sequence > watermark:
                    break
                records.append(record)
                if len(records) >= batch_size:
                    break
            if not records:
                raise DiscoveryOpportunityError("discovery projection could not reach its watermark")
            rows = []
            for record in records:
                if not self._valid_observation(record):
                    continue
                payload = record.event.payload
                document = {
                    "entity_fingerprint": str(payload["entity_fingerprint"]),
                    "version_fingerprint": str(payload["version_fingerprint"]),
                    "observation_event_id": record.event.event_id,
                    "agenda_item_id": str(payload["agenda_item_id"]),
                    "sequence": record.sequence,
                }
                rows.append((*self._row_document(document).values(), self._row_authenticator(document)))
            last_sequence = records[-1].sequence
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    current = int(
                        connection.execute(
                            "SELECT checkpoint_sequence FROM discovery_projection_v1 WHERE singleton=1"
                        ).fetchone()["checkpoint_sequence"]
                    )
                    if current != checkpoint:
                        connection.execute("ROLLBACK")
                        continue
                    for row in rows:
                        previous = connection.execute(
                            "SELECT sequence FROM discovery_entities_v1 WHERE entity_fingerprint=?",
                            (row[0],),
                        ).fetchone()
                        if previous is None or int(previous["sequence"]) < int(row[4]):
                            connection.execute(
                                """
                                INSERT INTO discovery_entities_v1 VALUES (?, ?, ?, ?, ?, ?)
                                ON CONFLICT(entity_fingerprint) DO UPDATE SET
                                    version_fingerprint=excluded.version_fingerprint,
                                    observation_event_id=excluded.observation_event_id,
                                    agenda_item_id=excluded.agenda_item_id,
                                    sequence=excluded.sequence,
                                    row_authenticator=excluded.row_authenticator
                                """,
                                row,
                            )
                            indexed += 1
                    entity_count = int(
                        connection.execute(
                            "SELECT COUNT(*) AS value FROM discovery_entities_v1"
                        ).fetchone()["value"]
                    )
                    connection.execute(
                        """
                        UPDATE discovery_projection_v1
                        SET checkpoint_sequence=?, entity_count=?, updated_at=?
                        WHERE singleton=1
                        """,
                        (
                            last_sequence,
                            entity_count,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    connection.execute("COMMIT")
                except Exception:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
        return indexed

    def rebuild_projection(self, *, batch_size: int = 500) -> int:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM discovery_entities_v1")
            connection.execute(
                """
                UPDATE discovery_projection_v1
                SET checkpoint_sequence=0, entity_count=0, updated_at=?
                WHERE singleton=1
                """,
                (datetime.now(timezone.utc).isoformat(),),
            )
            connection.execute("COMMIT")
        return self.project_new(batch_size=batch_size)

    def current(self, entity_fingerprint: str) -> DiscoveryProjectionRecord | None:
        self.project_new()
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM discovery_entities_v1 WHERE entity_fingerprint=?",
                (entity_fingerprint,),
            ).fetchone()
        if row is None:
            return None
        if self._row_authenticator(row) != row["row_authenticator"]:
            raise DiscoveryOpportunityError("discovery projection is corrupt")
        return DiscoveryProjectionRecord(**self._row_document(row))

    def active_evidence(self, *, subject: str, clearance: Sensitivity,
                        limit: int = 8,
                        observation_event_ids: tuple[str, ...] | None = None,
                        source_cursor: int | None = None) -> tuple[OpportunityEvidence, ...]:
        """Current authenticated facts; candidate exclusions never affect this API."""
        return self._read_evidence(subject=subject,clearance=clearance,limit=limit,
            observation_event_ids=observation_event_ids,source_cursor=source_cursor)

    def candidate_evidence(self, *, subject: str, clearance: Sensitivity, limit: int = 8,
                           excluded_urls: tuple[str,...] = (), source_cursor: int | None = None):
        """Attempt-eligible discovery window, never retained-proof resolution.

        Exclusion is scoped to this read, before the result limit; it changes
        neither source truth, agenda state nor active_evidence's pinned API.
        """
        if (type(limit) is not int or not 1<=limit<=32
                or not isinstance(excluded_urls,tuple) or len(excluded_urls)>64
                or any(not isinstance(url,str) for url in excluded_urls)):
            raise DiscoveryOpportunityError('bounded explicit candidate exclusions required')
        excluded=frozenset(canonicalize_discovery_url(url) for url in excluded_urls)
        return self._read_evidence(subject=subject,clearance=clearance,limit=limit,
            source_cursor=source_cursor,excluded_urls=excluded)

    def _read_evidence(self, *, subject, clearance,limit=8,observation_event_ids=None,
                       source_cursor=None,excluded_urls=()):
        """Read authenticated current discovery content, scoped before LIMIT.

        The caller supplies a Hermes-authorized principal, never a model-proposed
        identity. This is not a cross-user administration view or a fetch API.
        """
        owner = _bounded(subject, "subject", 128, required=True)
        if not _IDENTITY_RE.fullmatch(owner) or not 1 <= limit <= 32:
            raise DiscoveryOpportunityError("invalid evidence subject or limit")
        if source_cursor is not None and (type(source_cursor) is not int or source_cursor<0
                                         or observation_event_ids is not None):
            raise DiscoveryOpportunityError('invalid discovery source cursor')
        pinned_ids = None
        if observation_event_ids is not None:
            if (not isinstance(observation_event_ids, tuple)
                    or not 1 <= len(observation_event_ids) <= limit
                    or any(not isinstance(value, str) or not _IDENTITY_RE.fullmatch(value)
                           for value in observation_event_ids)
                    or len(set(observation_event_ids)) != len(observation_event_ids)):
                raise DiscoveryOpportunityError("invalid pinned observation identities")
            pinned_ids = []
            for observation_id in observation_event_ids:
                record = self.journal.get(observation_id)
                # Scope and authenticate before reading any associated content.
                if (record is not None and record.event.subject == owner
                        and self._valid_observation(record)):
                    pinned_ids.append(str(record.event.payload["agenda_item_id"]))
        target = self.journal.last_sequence()
        while self.journal.checkpoint(self.agenda.CHECKPOINT) < target:
            before = self.journal.checkpoint(self.agenda.CHECKPOINT)
            self.agenda.project_new(limit=1000)
            after = self.journal.checkpoint(self.agenda.CHECKPOINT)
            if after < target and after <= before:
                raise DiscoveryOpportunityError("agenda evidence projection made no progress")
        now = datetime.now(timezone.utc)
        values = []
        items = self.agenda.list_items(
            subject=owner, kinds=(AgendaItemKind.OPPORTUNITY,),
            states=(AgendaState.ACTIVE,), clearance=clearance, as_of=now, limit=1000,
            item_ids=pinned_ids,
            source_cursor=source_cursor,
        )
        for item in items:
            if item.content_status is not AgendaContentStatus.AVAILABLE:
                continue
            observation_id = str(item.details.get("observation_event_id") or "")
            if observation_event_ids is not None and observation_id not in observation_event_ids:
                continue
            record = self.journal.get(observation_id)
            if (record is None or record.event.subject != owner
                    or item.source_event_ids != (observation_id,)
                    or record.event.sensitivity != item.sensitivity
                    or record.event.expires_at is None or record.event.expires_at <= now
                    or not self._valid_observation(record)
                    or record.event.payload.get("agenda_item_id") != item.item_id):
                continue
            current = self.current(str(record.event.payload["entity_fingerprint"]))
            if current is None or current.observation_event_id != observation_id:
                continue
            try:
                ref = ContentReference.from_event_payload(record.event.payload["content"])
                content = self.vault.resolve_json(
                    ref.content_id, expected_subject=owner,
                    expected_purpose="discovery.observation", expected_sensitivity=item.sensitivity,
                )
            except (ContentUnavailableError, ContentIntegrityError):
                continue
            if excluded_urls and canonicalize_discovery_url(content['url']) in excluded_urls:
                continue
            values.append(OpportunityEvidence(
                item.item_id, observation_id, record.event.expires_at,
                item.sensitivity, _freeze_json(content),
            ))
            if len(values) == limit:
                break
        if observation_event_ids is not None:
            by_id = {value.observation_event_id: value for value in values}
            return tuple(by_id[value] for value in observation_event_ids if value in by_id)
        return tuple(values)

    def _append_idempotent(self, event: EventEnvelope) -> tuple[JournalRecord, bool]:
        existing = self.journal.get(event.event_id)
        if existing is not None:
            return existing, False
        try:
            result = self.journal.append(event)
            return JournalRecord(result.sequence, result.event), result.created
        except EventConflictError:
            existing = self.journal.get(event.event_id)
            if existing is None:
                raise
            return existing, False

    def ingest(
        self,
        candidate: DiscoveryCandidate,
        *,
        subject: str,
        correlation_id: str | None = None,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
    ) -> DiscoveryIngestResult:
        with self.vault.exclusive_operation():
            return self._ingest_locked(
                candidate,
                subject=subject,
                correlation_id=correlation_id,
                sensitivity=sensitivity,
            )

    def _ingest_locked(
        self,
        candidate: DiscoveryCandidate,
        *,
        subject: str,
        correlation_id: str | None,
        sensitivity: Sensitivity,
    ) -> DiscoveryIngestResult:
        owner = str(subject).strip()
        if not _IDENTITY_RE.fullmatch(owner):
            raise DiscoveryOpportunityError("invalid subject")
        sensitivity = Sensitivity(sensitivity)
        entity_fingerprint = "entity:" + self.vault.digest_json(candidate.entity_document(owner))[:40]
        version_document = candidate.content_document()
        version_fingerprint = "version:" + self.vault.digest_json(
            {"entity_fingerprint": entity_fingerprint, "content": version_document}
        )[:40]
        current = self.current(entity_fingerprint)
        observation_id = f"discovery.observation:{version_fingerprint.split(':', 1)[1]}"
        agenda_item_id = f"discovery-opportunity:{version_fingerprint.split(':', 1)[1]}"
        prior_observation = current.observation_event_id if current and current.version_fingerprint != version_fingerprint else None
        prior_agenda = current.agenda_item_id if prior_observation else None
        existing = self.journal.get(observation_id)
        if existing is None:
            content = self.vault.put_json(
                version_document,
                subject=owner,
                purpose="discovery.observation",
                sensitivity=sensitivity,
                retention_until=candidate.expires_at,
                content_id=f"discovery:{version_fingerprint.split(':', 1)[1]}",
            )
            payload = {
                "entity_fingerprint": entity_fingerprint,
                "version_fingerprint": version_fingerprint,
                "source_fingerprint": "source:" + self.vault.digest_json(candidate.source)[:40],
                "agenda_item_id": agenda_item_id,
                "content": content.to_event_payload(),
                "supersedes_observation_event_id": prior_observation,
                "supersedes_agenda_item_id": prior_agenda,
                "material_update": prior_observation is not None,
                "raw_content_stored": False,
            }
            payload["integrity_authenticator"] = "auth:" + self.vault.digest_json(
                {"contract": "discovery.observation.v1", "payload": payload}
            )
            event = EventEnvelope(
                event_id=observation_id,
                event_type="discovery.opportunity_observed",
                source="alive.discovery",
                actor="system:alive-discovery",
                subject=owner,
                correlation_id=correlation_id,
                occurred_at=candidate.published_at or candidate.observed_at,
                observed_at=candidate.observed_at,
                expires_at=candidate.expires_at,
                payload=payload,
                sensitivity=sensitivity,
                confidence=candidate.confidence,
            )
            observation, created = self._append_idempotent(event)
        else:
            observation, created = existing, False
            if not self._valid_observation(observation):
                raise DiscoveryOpportunityError("observation identity belongs to invalid evidence")
            content = ContentReference.from_event_payload(observation.event.payload["content"])
        durable_payload = observation.event.payload
        prior_agenda = str(durable_payload.get("supersedes_agenda_item_id") or "") or None
        proposal = AgendaProposal(
            kind=AgendaItemKind.OPPORTUNITY,
            subject=owner,
            details={
                "observation_event_id": observation.event.event_id,
                "observation_content_id": content.content_id,
                "entity_fingerprint": entity_fingerprint,
                "version_fingerprint": version_fingerprint,
                "collector_priority_hint": candidate.priority_hint,
                "decision_status": "unassessed",
            },
            authority=AgendaAuthority.DIRECT_OBSERVATION,
            source_event_ids=(observation.event.event_id,),
            confidence=observation.event.confidence,
            priority=candidate.priority_hint,
            sensitivity=sensitivity,
            expires_at=observation.event.expires_at,
            item_id=agenda_item_id,
        )
        existing_proposal = self.journal.get(f"agenda.proposal:{agenda_item_id}")
        proposal_record = existing_proposal or self.agenda.append_proposal(
            proposal,
            actor="system:alive-discovery",
            correlation_id=correlation_id,
        )
        agenda_decision = self.agenda.apply(proposal_record)
        if prior_agenda and prior_agenda != agenda_item_id:
            transition = self.agenda.append_transition(
                prior_agenda,
                AgendaState.DISMISSED,
                actor="system:alive-discovery",
                authority=AgendaAuthority.DIRECT_OBSERVATION,
                source_event_id=observation.event.event_id,
                reason="superseded_by_material_update",
                operation_id=f"agenda-supersede:{agenda_item_id.split(':', 1)[1]}",
            )
            supersede_decision = self.agenda.apply(transition)
            if supersede_decision.outcome not in {"transitioned", "deduplicated"}:
                # A terminal prior item needs no mutation; every other rejection
                # is a violated causal contract and must fail closed.
                prior = {
                    item.item_id: item
                    for item in self.agenda.list_items(
                        clearance=Sensitivity.RESTRICTED,
                        states=tuple(AgendaState),
                        limit=1000,
                    )
                }.get(prior_agenda)
                if prior is not None and prior.state not in {
                    AgendaState.COMPLETED,
                    AgendaState.DISMISSED,
                    AgendaState.EXPIRED,
                }:
                    raise DiscoveryOpportunityError("failed to supersede prior opportunity")
        self.project_new()
        return DiscoveryIngestResult(
            observation.event.event_id,
            agenda_item_id,
            created,
            bool(durable_payload.get("material_update")),
            agenda_decision,
            prior_agenda,
        )

    def record_source_failure(
        self,
        *,
        subject: str,
        source: str,
        error_class: str,
        observed_at: datetime | None = None,
    ) -> JournalRecord:
        """Record source health; failures never become agenda opportunities."""

        owner = str(subject).strip()
        if not _IDENTITY_RE.fullmatch(owner):
            raise DiscoveryOpportunityError("invalid subject")
        current = _utc(observed_at or datetime.now(timezone.utc), "observed_at")
        source_name = _bounded(source, "source", 256, required=True)
        error = _bounded(error_class, "error_class", 128, required=True)
        bucket = current.replace(minute=0, second=0, microsecond=0)
        identity = self.vault.digest_json(
            {"subject": owner, "source": source_name, "error": error, "bucket": bucket.isoformat()}
        )[:40]
        failure_payload = {
            "source_fingerprint": "source:" + self.vault.digest_json(source_name)[:40],
            "error_class_fingerprint": "error:" + self.vault.digest_json(error)[:40],
            "window_started_at": bucket.isoformat(),
            "opportunity_created": False,
            "raw_content_stored": False,
        }
        failure_payload["integrity_authenticator"] = "auth:" + self.vault.digest_json(
            {"contract": "discovery.source-failure.v1", "payload": failure_payload}
        )
        event = EventEnvelope(
            event_id=f"discovery.source_failure:{identity}",
            event_type="discovery.source_failed",
            source="alive.discovery",
            actor="system:alive-discovery",
            subject=owner,
            occurred_at=current,
            observed_at=current,
            expires_at=current + timedelta(days=7),
            payload=failure_payload,
            sensitivity=Sensitivity.INTERNAL,
            confidence=1.0,
        )
        return self._append_idempotent(event)[0]


def candidate_from_legacy(item: Mapping[str, Any], *, observed_at: datetime | None = None) -> DiscoveryCandidate:
    """Pure compatibility adapter; it imports no legacy ranking or send state."""

    published = item.get("published_at")
    published_at = None
    if isinstance(published, datetime):
        published_at = published
    elif published:
        try:
            published_at = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
        except ValueError:
            try:
                published_at = parsedate_to_datetime(str(published))
            except (TypeError, ValueError, OverflowError):
                published_at = None
    if published_at is not None and published_at.utcoffset() is None:
        published_at = None  # Unknown timezone is not an observed publication instant.
    attributes = {
        key: value
        for key, value in item.items()
        if key
        not in {
            "source",
            "title",
            "url",
            "summary",
            "description",
            "id",
            "published_at",
            "score",
            "interest_score",
        }
    }
    if published and published_at is None:
        attributes['published_at_raw'] = str(published)
    return DiscoveryCandidate(
        source=item.get("source") or "legacy-unknown",
        title=item.get("title"),
        url=item.get("url"),
        summary=item.get("summary") or item.get("description") or "",
        external_id=item.get("id") or "",
        published_at=published_at,
        observed_at=observed_at or datetime.now(timezone.utc),
        confidence=float(item.get("confidence", 0.5)),
        # Legacy rank is a collector hint only.  It cannot authorize sending.
        priority_hint=float(item.get("score", 0.5)),
        attributes=attributes,
    )


def mirror_legacy_discovery_batch(
    shared_dir: str | Path,
    *,
    raw_subject: Any,
    discovery_context: Mapping[str, Any],
    observed_at: datetime | None = None,
    max_candidates: int = 32,
) -> DiscoveryShadowReport:
    """Mirror a bounded legacy batch; never call delivery or legacy dedup APIs."""

    if not 1 <= max_candidates <= 128:
        raise DiscoveryOpportunityError("max_candidates must be between 1 and 128")
    kernel_dir = Path(shared_dir).expanduser().resolve() / "kernel"
    protector = LocalIdentityProtector(kernel_dir / "identity.key")
    subject = protector.pseudonym("discovery-subject", raw_subject)
    if subject is None:
        raise DiscoveryOpportunityError("discovery shadow subject is unavailable")
    journal = ExperienceJournal(kernel_dir / "experience.sqlite3")
    vault = ContentVault(
        kernel_dir / "content-vault",
        backup_root=kernel_dir / "content-backups",
    )
    ingestor = DiscoveryOpportunityIngestor(journal, content_vault=vault)
    current = _utc(observed_at or datetime.now(timezone.utc), "observed_at")
    observed = deduplicated = updated = rejected = source_failures = 0
    external = discovery_context.get("external")
    if isinstance(external, list):
        for item in external[:max_candidates]:
            if not isinstance(item, Mapping):
                rejected += 1
                continue
            try:
                result = ingestor.ingest(
                    candidate_from_legacy(item, observed_at=current), subject=subject
                )
                if result.observation_created:
                    observed += 1
                else:
                    deduplicated += 1
                if result.material_update:
                    updated += 1
            except (DiscoveryOpportunityError, TypeError, ValueError):
                rejected += 1
    health = discovery_context.get("source_health")
    if isinstance(health, Mapping):
        for source, status in health.items():
            if not isinstance(status, Mapping) or status.get("ok") is not False:
                continue
            ingestor.record_source_failure(
                subject=subject,
                source=str(source),
                error_class=str(status.get("error") or "SourceUnavailable"),
                observed_at=current,
            )
            source_failures += 1
    return DiscoveryShadowReport(
        observed, deduplicated, updated, rejected, source_failures
    )
