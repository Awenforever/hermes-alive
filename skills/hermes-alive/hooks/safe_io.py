
"""Safe file IO helpers for Hermes Alive runtime state.

Cross-platform:
- fcntl.flock on POSIX and msvcrt.locking on Windows
- temp file + fsync + os.replace for atomic writes
- JSONL append with lock
"""

from __future__ import annotations

import contextlib
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


if os.name == "nt":
    import msvcrt

    def _try_lock(fh: Any) -> bool:
        if os.fstat(fh.fileno()).st_size == 0:
            fh.write("\0")
            fh.flush()
        fh.seek(0)
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _unlock(fh: Any) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _try_lock(fh: Any) -> bool:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def _unlock(fh: Any) -> None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with open(path, "a+", encoding="utf-8") as fh:
        while True:
            if _try_lock(fh):
                break
            if time.monotonic() - start >= timeout:
                raise TimeoutError(f"lock timeout: {path}")
            time.sleep(0.05)
        try:
            yield
        finally:
            _unlock(fh)

@contextlib.contextmanager
def try_file_lock(path: Path) -> Iterator[bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+", encoding="utf-8")
    acquired = False
    try:
        try:
            acquired = _try_lock(fh)
        except OSError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            _unlock(fh)
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
