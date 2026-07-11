
"""Safe file IO helpers for Hermes Alive runtime state.

Linux/container oriented:
- fcntl.flock for inter-process locks
- temp file + fsync + os.replace for atomic writes
- JSONL append with lock
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

BASE = Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))
LOCK_DIR = BASE / "locks"
LOCK_DIR.mkdir(parents=True, exist_ok=True)

@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with open(path, "a+", encoding="utf-8") as fh:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - start >= timeout:
                    raise TimeoutError(f"lock timeout: {path}")
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

@contextlib.contextmanager
def try_file_lock(path: Path) -> Iterator[bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+", encoding="utf-8")
    acquired = False
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()

def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass

def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))

def locked_read_json(path: Path, default: Any, lock_name: str | None = None) -> Any:
    lock = LOCK_DIR / (lock_name or (path.name + ".lock"))
    with file_lock(lock):
        return read_json(path, default)

def locked_write_json(path: Path, data: Any, lock_name: str | None = None) -> None:
    lock = LOCK_DIR / (lock_name or (path.name + ".lock"))
    with file_lock(lock):
        atomic_write_json(path, data)

def append_jsonl(path: Path, record: dict[str, Any], lock_name: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = LOCK_DIR / (lock_name or (path.name + ".lock"))
    rec = dict(record)
    rec.setdefault("time", datetime.now().astimezone().isoformat())
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    with file_lock(lock):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def redact_preview(text: str, max_chars: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    text = text[:max_chars]
    patterns = [
        r"sk-[A-Za-z0-9_-]{10,}",
        r"o9cq[0-9A-Za-z_-]+@im\.wechat",
        r"(?i)(api[_-]?key|token|secret|password|cookie)\s*[:=]\s*[^,\s]+",
    ]
    for pat in patterns:
        text = re.sub(pat, "<REDACTED>", text)
    return text
