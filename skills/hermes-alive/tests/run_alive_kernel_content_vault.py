#!/usr/bin/env python3
"""Contracts for encrypted content storage, backup, and resumable erasure."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from alive_kernel.content_vault import (  # noqa: E402
    ContentErasedError,
    ContentVault,
)
from alive_kernel.events import Sensitivity  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def all_bytes(root: Path) -> bytes:
    chunks: list[bytes] = []
    for path in root.rglob("*"):
        if path.is_file():
            chunks.append(path.read_bytes())
    return b"\n".join(chunks)


def worker_main(base: Path, backups: Path, index: int) -> None:
    vault = ContentVault(base, backup_root=backups)
    vault.put_json(
        {"index": index},
        subject="subject:process",
        purpose="memory.episode",
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="alive-content-vault-") as raw:
        base = Path(raw)
        live = base / "live"
        backups = base / "backups"
        vault = ContentVault(live, backup_root=backups)

        sentinel = "PRIVATE-SENTINEL-火焰-8fbc9127"
        first = vault.put_json(
            {"note": sentinel, "nested": [1, {"ok": True}]},
            subject="subject:alpha",
            purpose="memory.fact",
            sensitivity=Sensitivity.PRIVATE,
        )
        plain_digest = hashlib.sha256(
            ('{"nested":[1,{"ok":true}],"note":"' + sentinel + '"}').encode("utf-8")
        ).hexdigest()
        require(first.digest != plain_digest, "journal digest is enumerable plaintext SHA-256")
        other = vault.put_json(
            {"note": "unrelated-value"},
            subject="subject:beta",
            purpose="memory.fact",
        )
        require(vault.resolve_json(first.content_id)["note"] == sentinel, "round trip failed")
        require(sentinel.encode("utf-8") not in all_bytes(live), "plaintext leaked to live files")

        old_backup = vault.create_managed_backup("before-erasure")
        require(old_backup.is_dir(), "managed backup missing")
        incomplete_backup = backups / "corrupt-uncommitted-copy"
        incomplete_backup.mkdir()
        (incomplete_backup / "content.sqlite3").write_bytes(
            (old_backup / "content.sqlite3").read_bytes()
        )
        restored_old = ContentVault.restore_managed_backup(
            old_backup, base / "restore-old", backup_root=base / "restore-old-backups"
        )
        require(restored_old.resolve_json(first.content_id)["note"] == sentinel, "backup restore failed")

        original_purge = vault._purge_affected_backups
        interrupted = {"raised": False}

        def fail_once(ids, *, subject):
            if not interrupted["raised"]:
                interrupted["raised"] = True
                raise RuntimeError("injected interruption after live erasure")
            return original_purge(ids, subject=subject)

        vault._purge_affected_backups = fail_once  # type: ignore[method-assign]
        try:
            vault.erase_item(first.content_id)
            raise AssertionError("interrupted erase unexpectedly succeeded")
        except RuntimeError as exc:
            require("injected interruption" in str(exc), "wrong interruption surfaced")
        require(vault.pending_erasure_jobs(), "erasure intent was not durable")
        try:
            vault.resolve_json(first.content_id)
            raise AssertionError("erased content remained resolvable")
        except ContentErasedError as exc:
            require(str(exc) == "content_unavailable_erased", "wrong erased state")

        del vault
        resumed = ContentVault(live, backup_root=backups)
        require(not resumed.pending_erasure_jobs(), "restart did not finish erasure")
        require(not old_backup.exists(), "affected pre-erasure backup survived")
        require(not incomplete_backup.exists(), "untracked incomplete backup survived erasure")
        require(resumed.resolve_json(other.content_id)["note"] == "unrelated-value", "unrelated content lost")

        post_backup = resumed.create_managed_backup("after-erasure")
        require(sentinel.encode("utf-8") not in all_bytes(base), "sentinel survived erasure boundary")
        restored_post = ContentVault.restore_managed_backup(
            post_backup, base / "restore-post", backup_root=base / "restore-post-backups"
        )
        try:
            restored_post.resolve_json(first.content_id)
            raise AssertionError("new backup resurrected erased content")
        except ContentErasedError:
            pass
        require(restored_post.resolve_json(other.content_id)["note"] == "unrelated-value", "new backup lost live data")

        alpha_two = resumed.put_json(
            {"value": "alpha-two"}, subject="subject:alpha", purpose="memory.preference"
        )
        beta_two = resumed.put_json(
            {"value": "beta-two"}, subject="subject:beta", purpose="memory.preference"
        )
        resumed.create_managed_backup("before-subject-erasure")
        subject_result = resumed.erase_subject("subject:alpha")
        require(subject_result.newly_erased == 1, "subject erase count is wrong")
        try:
            resumed.resolve_json(alpha_two.content_id)
            raise AssertionError("subject erase left selected content")
        except ContentErasedError:
            pass
        require(resumed.resolve_json(beta_two.content_id)["value"] == "beta-two", "subject erase crossed subjects")
        repeated = resumed.erase_subject("subject:alpha")
        require(repeated.already_erased and repeated.newly_erased == 0, "subject erase is not idempotent")

        expired = resumed.put_json(
            {"value": "expired"},
            subject="subject:beta",
            purpose="memory.episode",
            retention_until=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        expiry_result = resumed.erase_expired()
        require(expiry_result.newly_erased == 1, "retention erasure failed")
        try:
            resumed.resolve_json(expired.content_id)
            raise AssertionError("expired content remained available")
        except ContentErasedError:
            pass

        concurrent_base = base / "concurrent"

        def concurrent_put(index: int) -> tuple[str, int]:
            concurrent_vault = ContentVault(
                concurrent_base, backup_root=base / "concurrent-backups"
            )
            reference = concurrent_vault.put_json(
                {"index": index},
                subject="subject:concurrent",
                purpose="memory.episode",
            )
            return reference.content_id, index

        with ThreadPoolExecutor(max_workers=16) as pool:
            concurrent_items = list(pool.map(concurrent_put, range(64)))
        concurrent_vault = ContentVault(
            concurrent_base, backup_root=base / "concurrent-backups"
        )
        require(len(concurrent_vault.list_references()) == 64, "concurrent writes were lost")
        for content_id, index in concurrent_items:
            require(
                concurrent_vault.resolve_json(content_id)["index"] == index,
                "concurrent key initialization produced unreadable ciphertext",
            )

        race = concurrent_vault.put_json(
            {"value": "backup-erasure-race"},
            subject="subject:race",
            purpose="memory.fact",
        )

        def backup_or_erase(index: int):
            if index == 4:
                return concurrent_vault.erase_item(race.content_id)
            return concurrent_vault.create_managed_backup(f"race-{index}")

        with ThreadPoolExecutor(max_workers=9) as pool:
            list(pool.map(backup_or_erase, range(9)))
        for manifest_path in (base / "concurrent-backups").glob("*/manifest.json"):
            require(
                race.content_id not in manifest_path.read_text(encoding="utf-8"),
                "backup/erasure race left a restorable deleted object",
            )

        process_base = base / "process-concurrent"
        process_backups = base / "process-concurrent-backups"

        def spawn_worker(index: int) -> None:
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--worker",
                    str(process_base),
                    str(process_backups),
                    str(index),
                ],
                check=True,
                env={**dict(os.environ), "PYTHONDONTWRITEBYTECODE": "1"},
                stdout=subprocess.DEVNULL,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(spawn_worker, range(16)))
        process_vault = ContentVault(process_base, backup_root=process_backups)
        require(len(process_vault.list_references()) == 16, "cross-process writes were lost")

        print("ALIVE_KERNEL_CONTENT_VAULT_RESULT=PASS")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--worker":
        worker_main(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]))
    else:
        main()
