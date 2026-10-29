"""Keep SQLite WAL resources open for one operation, without caching any data.

Short-lived query connections still perform all reads, writes and audits. An
idle keeper prevents a last-connection checkpoint for every nested read. It has
no transaction or cursor and closes at scope exit, including cancellation.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import logging
import os
from pathlib import Path
import sqlite3
import threading

_CURRENT=ContextVar('alive_sqlite_operation_scope',default=None)
_LOG=logging.getLogger(__name__)


class _Scope:
    def __init__(self):
        self.pid=os.getpid();self.lock=threading.RLock();self.keepers={};self.closed=False

    def hold(self,path):
        if self.pid!=os.getpid():return
        key=os.path.normcase(str(Path(path).resolve()))
        with self.lock:
            if self.closed or key in self.keepers or len(self.keepers)>=16:return
            connection=None
            try:
                # Never recreate a file concurrently removed by its owner.
                connection=sqlite3.connect(Path(key).as_uri()+'?mode=rw',uri=True,
                    timeout=1,isolation_level=None,check_same_thread=False)
                connection.execute('PRAGMA query_only=ON')
                cursor=connection.execute('PRAGMA user_version')
                cursor.fetchone();cursor.close()
                assert not connection.in_transaction
                self.keepers[key]=connection
            except sqlite3.Error:
                if connection is not None:connection.close()
                # This is an optimization, never an alternate database or an
                # authorization fallback. The ordinary connection still runs.
                _LOG.debug('SQLite operation keeper unavailable',exc_info=True)

    def close(self):
        if self.pid!=os.getpid():return
        with self.lock:
            self.closed=True
            connections=tuple(self.keepers.values());self.keepers.clear()
            for connection in connections:connection.close()


def hold_sqlite_resource(path):
    scope=_CURRENT.get()
    if scope is not None:scope.hold(path)


@contextmanager
def sqlite_operation_scope():
    """Nested scopes join; inherited threads cannot extend a retired scope."""
    existing=_CURRENT.get()
    if existing is not None and existing.pid==os.getpid() and not existing.closed:
        yield existing
        return
    scope=_Scope();token=_CURRENT.set(scope)
    try:yield scope
    finally:
        try:scope.close()
        finally:_CURRENT.reset(token)
