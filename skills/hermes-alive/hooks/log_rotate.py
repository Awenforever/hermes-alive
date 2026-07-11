#!/usr/bin/env python3
"""Log rotation for Hermes Alive proactive_log.

Called from ProactivePlatformWatcher on startup.
Rotates daily: proactive_log.jsonl → proactive_log.2026-07-05.jsonl
Deletes dated logs older than retention_days (default 7).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 7
RETENTION_ENV = "HERMES_ALIVE_LOG_RETENTION_DAYS"


def rotate_proactive_log(base_dir: Path, log_name: str = "proactive_log.jsonl") -> None:
    """Rotate log if last-modified date differs from today. Purge old dated logs."""
    log_path = base_dir / log_name
    if not log_path.exists():
        return

    retention = int(os.getenv(RETENTION_ENV, str(DEFAULT_RETENTION_DAYS)))

    # Check if the log is from a previous day
    mtime = log_path.stat().st_mtime
    log_date = datetime.fromtimestamp(mtime).date()
    today = datetime.now().date()

    if log_date < today:
        # Rotate: rename to dated archive
        archive_name = f"{log_path.stem}.{log_date.isoformat()}{log_path.suffix}"
        archive_path = base_dir / archive_name
        try:
            log_path.rename(archive_path)
            logger.info("Rotated %s → %s", log_path.name, archive_name)
        except OSError as exc:
            logger.warning("Failed to rotate log %s → %s: %s", log_path.name, archive_name, exc)

    # Purge old dated logs
    cutoff = today - timedelta(days=retention)
    glob_pattern = f"{Path(log_name).stem}.*{Path(log_name).suffix}"
    for old_log in sorted(base_dir.glob(glob_pattern)):
        # Extract date from filename: proactive_log.2026-07-01.jsonl → 2026-07-01
        stem = old_log.name.replace(Path(log_name).stem + ".", "").replace(Path(log_name).suffix, "")
        try:
            file_date = datetime.strptime(stem, "%Y-%m-%d").date()
            if file_date < cutoff:
                old_log.unlink()
                logger.info("Purged old log: %s (date=%s < cutoff=%s)", old_log.name, file_date, cutoff)
        except ValueError:
            # Not a date-patterned file, skip
            continue
