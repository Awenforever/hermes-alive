"""Package-local cross-process locks, independent of legacy hook import paths.

Same OS locking protocol as legacy safe_io, including the Windows byte position.
No import-time runtime-directory creation and no dependence on a global sys.path.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import time


if os.name=='nt':
    import msvcrt

    def _try_lock(handle):
        if os.fstat(handle.fileno()).st_size==0:
            handle.write('\0');handle.flush()
        handle.seek(0)
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);return True
        except OSError:return False

    def _unlock(handle):
        handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
else:
    import fcntl

    def _try_lock(handle):
        try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);return True
        except BlockingIOError:return False

    def _unlock(handle):fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


@contextmanager
def file_lock(path:Path,timeout:float=5):
    path.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    with path.open('a+',encoding='utf-8') as handle:
        while not _try_lock(handle):
            if time.monotonic()-started>=timeout:raise TimeoutError(f'lock timeout: {path}')
            time.sleep(.05)
        try:yield
        finally:_unlock(handle)


@contextmanager
def try_file_lock(path:Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+',encoding='utf-8') as handle:
        try:acquired=_try_lock(handle)
        except OSError:acquired=False
        try:yield acquired
        finally:
            if acquired:_unlock(handle)
