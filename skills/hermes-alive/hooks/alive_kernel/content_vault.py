"""Erasable encrypted content storage for the Alive kernel.

The durable experience journal must never contain private plaintext.  This
module owns the other half of that split: authenticated ciphertext, explicit
retention metadata, resumable erasure, and backups that participate in the
same deletion boundary.

This is intentionally a narrow storage primitive.  It does not decide what a
memory means or whether it may be retrieved; callers must enforce semantic and
authority policy before resolving a content reference.
"""

from __future__ import annotations

import base64
from contextlib import closing, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import time
from typing import Any
from uuid import uuid4

from .events import Sensitivity


_SCHEMA_VERSION = 1
_MAX_CONTENT_BYTES = 4 * 1024 * 1024
_OPERATION_LOCK = threading.Lock()

msvcrt = None
try:
    import fcntl
except ImportError:  # pragma: no cover - host-specific import
    fcntl = None
    with suppress(ImportError):
        import msvcrt


class ContentVaultError(RuntimeError):
    """Base class for content-vault failures safe to expose to callers."""


class ContentUnavailableError(ContentVaultError):
    """The reference never existed or its ciphertext is unavailable."""


class ContentErasedError(ContentUnavailableError):
    """The reference was deliberately erased and must not be reconstructed."""


class ContentIntegrityError(ContentVaultError):
    """Authenticated decryption or digest verification failed."""


@dataclass(frozen=True, slots=True)
class ContentReference:
    content_id: str
    digest: str
    size_bytes: int
    sensitivity: Sensitivity
    retention_until: datetime | None

    def to_event_payload(self) -> dict[str, Any]:
        """Metadata safe for the durable journal; never includes plaintext."""

        return {
            "content_id": self.content_id,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "sensitivity": self.sensitivity.value,
            "retention_until": (
                self.retention_until.isoformat() if self.retention_until else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ErasureResult:
    requested: int
    newly_erased: int
    managed_backups_removed: int
    already_erased: bool


def _utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_json(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("content must be finite JSON") from exc
    payload = text.encode("utf-8")
    if len(payload) > _MAX_CONTENT_BYTES:
        raise ValueError(f"content exceeds {_MAX_CONTENT_BYTES} bytes")
    return payload


def _metadata_aad(
    *,
    content_id: str,
    subject: str,
    purpose: str,
    sensitivity: Sensitivity,
    created_at: str,
) -> bytes:
    return json.dumps(
        {
            "schema": _SCHEMA_VERSION,
            "content_id": content_id,
            "subject": subject,
            "purpose": purpose,
            "sensitivity": sensitivity.value,
            "created_at": created_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class ContentVault:
    """Profile-local encrypted content store with managed-backup erasure.

    ``backup_root`` names the only backup set for which this class promises
    coordinated deletion.  Arbitrary disk images and user-made copies are
    outside the boundary and must be governed by the operator's retention
    policy; pretending otherwise would be a false security claim.
    """

    def __init__(self, base_dir: Path, *, backup_root: Path | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "content.sqlite3"
        self.key_path = self.base_dir / "content.key"
        self.backup_root = Path(backup_root) if backup_root is not None else (
            self.base_dir / "managed-backups"
        )
        self._ensure_directories()
        self._initialize()
        with self._exclusive_operation():
            self._cleanup_incomplete_backups()
            self._resume_pending_erasure_unlocked()

    def _ensure_directories(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        for directory in (self.base_dir, self.backup_root):
            try:
                os.chmod(directory, 0o700)
            except OSError:
                pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("PRAGMA foreign_keys=ON")
            # First-open races are normal when gateway workers start together.
            # journal_mode takes a transient exclusive lock even when every
            # caller wants the same mode, so retry it explicitly.  If setup
            # still fails, close the half-open handle before surfacing the
            # error; this is required for Windows cleanup and rollback.
            for attempt in range(100):
                try:
                    connection.execute("PRAGMA journal_mode=WAL")
                    break
                except sqlite3.OperationalError as exc:
                    if "locked" not in str(exc).lower() or attempt == 99:
                        raise
                    time.sleep(0.01)
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA secure_delete=ON")
            return connection
        except Exception:
            connection.close()
            raise

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS content_items (
                    content_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    retention_until TEXT,
                    digest TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    nonce BLOB NOT NULL,
                    ciphertext BLOB NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_content_subject
                    ON content_items(subject);
                CREATE TABLE IF NOT EXISTS erasure_jobs (
                    job_id TEXT PRIMARY KEY,
                    selector_kind TEXT NOT NULL,
                    selector_value TEXT NOT NULL,
                    content_ids_json TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    live_erased_at TEXT NOT NULL,
                    backups_purged_at TEXT
                );
                CREATE TABLE IF NOT EXISTS erasure_items (
                    job_id TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    PRIMARY KEY(job_id, content_id),
                    FOREIGN KEY(job_id) REFERENCES erasure_jobs(job_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_erasure_item
                    ON erasure_items(content_id);
                CREATE TABLE IF NOT EXISTS access_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                COMMIT;
                """
            )

    @contextmanager
    def _exclusive_operation(self):
        """Serialize backup and erasure across threads and processes."""

        with _OPERATION_LOCK:
            lock_path = self.base_dir / ".content-vault.lock"
            if msvcrt and (not lock_path.exists() or lock_path.stat().st_size == 0):
                lock_path.write_text(" ", encoding="utf-8")
            with open(lock_path, "r+" if msvcrt else "a+", encoding="utf-8") as handle:
                if fcntl:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                elif msvcrt:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    with suppress(OSError):
                        if fcntl:
                            fcntl.flock(handle, fcntl.LOCK_UN)
                        elif msvcrt:
                            handle.seek(0)
                            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

    def _key(self) -> bytes:
        if not self.key_path.exists():
            key = os.urandom(32)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                fd = os.open(self.key_path, flags, 0o600)
            except FileExistsError:
                pass
            else:
                try:
                    os.write(fd, base64.urlsafe_b64encode(key))
                    os.fsync(fd)
                finally:
                    os.close(fd)
        # Another process may observe the O_EXCL-created file just before the
        # winner has finished its small write.  Wait for a complete key rather
        # than manufacturing a second one or misdiagnosing transient emptiness
        # as permanent corruption.
        key = b""
        decode_error: Exception | None = None
        for _ in range(100):
            try:
                encoded = self.key_path.read_bytes().strip()
                key = base64.urlsafe_b64decode(encoded)
                if len(key) == 32:
                    break
            except (OSError, ValueError) as exc:
                decode_error = exc
            time.sleep(0.01)
        if len(key) != 32:
            raise ContentVaultError("content vault key is malformed or incomplete") from decode_error
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    @staticmethod
    def _aesgcm(key: bytes):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:  # Hermes >=0.21.3 includes cryptography.
            raise ContentVaultError(
                "Hermes runtime is missing its required cryptography dependency"
            ) from exc
        return AESGCM(key)

    def put_json(
        self,
        value: Any,
        *,
        subject: str,
        purpose: str,
        sensitivity: Sensitivity = Sensitivity.PRIVATE,
        retention_until: datetime | None = None,
        content_id: str | None = None,
    ) -> ContentReference:
        subject = str(subject).strip()
        purpose = str(purpose).strip()
        if not subject or not purpose:
            raise ValueError("subject and purpose are required")
        sensitivity = Sensitivity(sensitivity)
        retention_until = _utc(retention_until, "retention_until")
        content_id = str(content_id or f"content_{uuid4().hex}").strip()
        if not content_id or len(content_id) > 255:
            raise ValueError("invalid content_id")
        payload = _canonical_json(value)
        digest = hashlib.sha256(payload).hexdigest()
        created_at = datetime.now(timezone.utc).isoformat()
        aad = _metadata_aad(
            content_id=content_id,
            subject=subject,
            purpose=purpose,
            sensitivity=sensitivity,
            created_at=created_at,
        )
        nonce = os.urandom(12)
        ciphertext = self._aesgcm(self._key()).encrypt(nonce, payload, aad)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                erased = connection.execute(
                    "SELECT 1 FROM erasure_items WHERE content_id=?",
                    (content_id,),
                ).fetchone()
                if erased is not None:
                    raise ContentErasedError(
                        "an erased content_id cannot be reused"
                    )
                connection.execute(
                    """
                    INSERT INTO content_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content_id,
                        subject,
                        purpose,
                        sensitivity.value,
                        retention_until.isoformat() if retention_until else None,
                        digest,
                        len(payload),
                        nonce,
                        ciphertext,
                        created_at,
                    ),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return ContentReference(
            content_id, digest, len(payload), sensitivity, retention_until
        )

    def resolve_json(self, content_id: str) -> Any:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM content_items WHERE content_id=?", (content_id,)
            ).fetchone()
            if row is None:
                erased = self._erasure_row(connection, content_id)
                self._audit(connection, content_id, "resolve", "erased" if erased else "missing")
                if erased:
                    raise ContentErasedError("content_unavailable_erased")
                raise ContentUnavailableError("content_unavailable_missing")
            aad = _metadata_aad(
                content_id=str(row["content_id"]),
                subject=str(row["subject"]),
                purpose=str(row["purpose"]),
                sensitivity=Sensitivity(row["sensitivity"]),
                created_at=str(row["created_at"]),
            )
            try:
                payload = self._aesgcm(self._key()).decrypt(
                    bytes(row["nonce"]), bytes(row["ciphertext"]), aad
                )
            except Exception as exc:
                self._audit(connection, content_id, "resolve", "integrity_error")
                raise ContentIntegrityError("content authentication failed") from exc
            if hashlib.sha256(payload).hexdigest() != row["digest"]:
                self._audit(connection, content_id, "resolve", "digest_mismatch")
                raise ContentIntegrityError("content digest mismatch")
            self._audit(connection, content_id, "resolve", "resolved")
        return json.loads(payload.decode("utf-8"))

    @staticmethod
    def _audit(
        connection: sqlite3.Connection, content_id: str, action: str, outcome: str
    ) -> None:
        connection.execute(
            "INSERT INTO access_audit(content_id, action, outcome, occurred_at) VALUES (?, ?, ?, ?)",
            (content_id, action, outcome, datetime.now(timezone.utc).isoformat()),
        )

    @staticmethod
    def _erasure_row(connection: sqlite3.Connection, content_id: str) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT jobs.* FROM erasure_jobs AS jobs
            JOIN erasure_items AS items ON items.job_id=jobs.job_id
            WHERE items.content_id=?
            ORDER BY jobs.requested_at DESC LIMIT 1
            """,
            (content_id,),
        ).fetchone()

    def erase_item(self, content_id: str) -> ErasureResult:
        with self._exclusive_operation():
            return self._erase("item", str(content_id))

    def erase_subject(self, subject: str) -> ErasureResult:
        with self._exclusive_operation():
            return self._erase("subject", str(subject))

    def _erase(self, selector_kind: str, selector_value: str) -> ErasureResult:
        if not selector_value:
            raise ValueError("erasure selector must not be empty")
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if selector_kind == "item":
                    rows = connection.execute(
                        "SELECT content_id FROM content_items WHERE content_id=?",
                        (selector_value,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT content_id FROM content_items WHERE subject=?",
                        (selector_value,),
                    ).fetchall()
                live_ids = [str(row["content_id"]) for row in rows]
                ids = live_ids or ([selector_value] if selector_kind == "item" else [])
                previous = connection.execute(
                    """
                    SELECT * FROM erasure_jobs
                    WHERE selector_kind=? AND selector_value=?
                    ORDER BY requested_at DESC LIMIT 1
                    """,
                    (selector_kind, selector_value),
                ).fetchone()
                if not live_ids and previous is not None:
                    connection.execute("COMMIT")
                    removed = self._finish_erasure(str(previous["job_id"]))
                    return ErasureResult(0, 0, removed, True)
                now = datetime.now(timezone.utc).isoformat()
                job_id = f"erase_{uuid4().hex}"
                connection.execute(
                    "INSERT INTO erasure_jobs VALUES (?, ?, ?, ?, ?, ?, NULL)",
                    (
                        job_id,
                        selector_kind,
                        selector_value,
                        json.dumps(ids, separators=(",", ":")),
                        now,
                        now,
                    ),
                )
                connection.executemany(
                    "INSERT INTO erasure_items(job_id, content_id) VALUES (?, ?)",
                    ((job_id, content_id) for content_id in ids),
                )
                if live_ids:
                    placeholders = ",".join("?" for _ in live_ids)
                    connection.execute(
                        f"DELETE FROM content_items WHERE content_id IN ({placeholders})",
                        live_ids,
                    )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        self._compact()
        removed = self._finish_erasure(job_id)
        return ErasureResult(len(ids), len(live_ids), removed, not live_ids)

    def _compact(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("VACUUM")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def resume_pending_erasure(self) -> int:
        with self._exclusive_operation():
            return self._resume_pending_erasure_unlocked()

    def _resume_pending_erasure_unlocked(self) -> int:
        with closing(self._connect()) as connection:
            jobs = [
                str(row["job_id"])
                for row in connection.execute(
                    "SELECT job_id FROM erasure_jobs WHERE backups_purged_at IS NULL"
                )
            ]
        if jobs:
            self._compact()
        for job_id in jobs:
            self._finish_erasure(job_id)
        return len(jobs)

    def _cleanup_incomplete_backups(self) -> None:
        root = self.backup_root.resolve()
        for candidate in list(self.backup_root.iterdir()):
            if not candidate.name.startswith(".pending-"):
                continue
            resolved = candidate.resolve()
            if resolved.parent == root and candidate.is_dir():
                shutil.rmtree(resolved)

    def _finish_erasure(self, job_id: str) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM erasure_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if row is None or row["backups_purged_at"] is not None:
                return 0
            ids = {
                str(item["content_id"])
                for item in connection.execute(
                    "SELECT content_id FROM erasure_items WHERE job_id=?", (job_id,)
                )
            }
            subject = row["selector_value"] if row["selector_kind"] == "subject" else None
        removed = self._purge_affected_backups(ids, subject=subject)
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE erasure_jobs SET backups_purged_at=? WHERE job_id=? AND backups_purged_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), job_id),
            )
        return removed

    def _purge_affected_backups(self, ids: set[str], *, subject: str | None) -> int:
        root = self.backup_root.resolve()
        removed = 0
        for candidate in list(self.backup_root.iterdir()):
            if not candidate.is_dir():
                continue
            resolved = candidate.resolve()
            if resolved.parent != root:
                continue
            manifest_path = candidate / "manifest.json"
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # This directory is inside the exclusively owned managed root
                # but was never committed with a valid manifest.  Keeping it
                # would create an untracked copy outside erasure accounting.
                shutil.rmtree(resolved)
                removed += 1
                continue
            manifest_ids = set(str(value) for value in manifest.get("content_ids", []))
            manifest_subjects = set(str(value) for value in manifest.get("subjects", []))
            if ids.intersection(manifest_ids) or (subject and subject in manifest_subjects):
                shutil.rmtree(resolved)
                removed += 1
        return removed

    def create_managed_backup(self, name: str | None = None) -> Path:
        with self._exclusive_operation():
            self._resume_pending_erasure_unlocked()
            self._key()
            backup_name = str(name or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
            allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            if not backup_name or any(ch not in allowed for ch in backup_name):
                raise ValueError("backup name contains unsupported characters")
            target = self.backup_root / backup_name
            if target.exists():
                raise FileExistsError(f"managed backup already exists: {backup_name}")
            staging = self.backup_root / f".pending-{uuid4().hex}"
            staging.mkdir(mode=0o700)
            try:
                database = staging / "content.sqlite3"
                with closing(self._connect()) as source, closing(
                    sqlite3.connect(database)
                ) as destination:
                    source.backup(destination)
                shutil.copy2(self.key_path, staging / "content.key")
                try:
                    os.chmod(staging / "content.key", 0o600)
                    os.chmod(database, 0o600)
                except OSError:
                    pass
                with closing(self._connect()) as connection:
                    rows = connection.execute(
                        "SELECT content_id, subject FROM content_items ORDER BY content_id"
                    ).fetchall()
                manifest = {
                    "schema": _SCHEMA_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content_ids": [str(row["content_id"]) for row in rows],
                    "subjects": sorted({str(row["subject"]) for row in rows}),
                }
                (staging / "manifest.json").write_text(
                    json.dumps(manifest, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8",
                )
                os.replace(staging, target)
                return target
            except Exception:
                if staging.exists() and staging.resolve().parent == self.backup_root.resolve():
                    shutil.rmtree(staging)
                raise

    @classmethod
    def restore_managed_backup(
        cls, backup: Path, destination: Path, *, backup_root: Path | None = None
    ) -> "ContentVault":
        backup = Path(backup)
        destination = Path(destination)
        if destination.exists() and any(destination.iterdir()):
            raise ContentVaultError("restore destination must be empty")
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in ("content.sqlite3", "content.key"):
            source = backup / name
            if not source.is_file():
                raise ContentVaultError(f"managed backup is missing {name}")
            shutil.copy2(source, destination / name)
        return cls(destination, backup_root=backup_root)

    def list_references(self) -> list[ContentReference]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM content_items ORDER BY created_at, content_id"
            ).fetchall()
        return [
            ContentReference(
                content_id=str(row["content_id"]),
                digest=str(row["digest"]),
                size_bytes=int(row["size_bytes"]),
                sensitivity=Sensitivity(row["sensitivity"]),
                retention_until=(
                    datetime.fromisoformat(str(row["retention_until"]))
                    if row["retention_until"]
                    else None
                ),
            )
            for row in rows
        ]

    def erase_expired(self, *, now: datetime | None = None) -> ErasureResult:
        current = _utc(now or datetime.now(timezone.utc), "now")
        assert current is not None
        with closing(self._connect()) as connection:
            ids = [
                str(row["content_id"])
                for row in connection.execute(
                    "SELECT content_id FROM content_items WHERE retention_until IS NOT NULL AND retention_until<=?",
                    (current.isoformat(),),
                )
            ]
        requested = len(ids)
        erased = 0
        backups = 0
        for content_id in ids:
            result = self.erase_item(content_id)
            erased += result.newly_erased
            backups += result.managed_backups_removed
        return ErasureResult(requested, erased, backups, requested == 0)

    def pending_erasure_jobs(self) -> list[str]:
        with closing(self._connect()) as connection:
            return [
                str(row["job_id"])
                for row in connection.execute(
                    "SELECT job_id FROM erasure_jobs WHERE backups_purged_at IS NULL ORDER BY requested_at"
                )
            ]
