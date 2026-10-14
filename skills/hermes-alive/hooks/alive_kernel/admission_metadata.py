"""Research-only ephemeral handoff; not registered by the Alive runtime.

No files, plaintext message bodies, model calls, authorization or learning.
Resolution must be called only by a trusted post-admission consumer. Matching
snapshots cannot themselves prove that authorization happened.
"""
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import threading
import time
from collections.abc import Mapping
import asyncio
import weakref
from contextvars import Context


@dataclass(frozen=True, slots=True)
class AdmissionMetadata:
    is_bot: bool | None
    quoted_message_id: str | None
    quote_is_own_message: bool | None


class AdmissionMetadataCache:
    def __init__(self, *, capacity=256, ttl_seconds=30, clock=time.monotonic):
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError("invalid metadata capacity")
        if type(ttl_seconds) not in (int, float) or not 0 < ttl_seconds <= 300:
            raise ValueError("invalid metadata lifetime")
        self.capacity, self.ttl, self.clock = capacity, ttl_seconds, clock
        self._key = os.urandom(32)
        self._entries = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _identifier(value, *, optional=False):
        if value is None and optional:
            return None
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            raise ValueError("metadata identity unavailable")
        return value

    def _identity(self, platform, source, message_id):
        if not isinstance(source, Mapping) or source.get("platform") != platform:
            raise ValueError("metadata source mismatch")
        data = {"platform":self._identifier(platform),
            "user":self._identifier(source.get("user_id")),
            "chat":self._identifier(source.get("chat_id")),
            "message":self._identifier(message_id),
            "thread":self._identifier(source.get("thread_id"), optional=True),
            "profile":self._identifier(source.get("profile"), optional=True)}
        return self._digest("identity", data)

    def _digest(self, kind, value):
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hmac.new(self._key, (kind + "\0" + data).encode("utf-8"), hashlib.sha256).digest()

    def _prune(self, now):
        for key, entry in tuple(self._entries.items()):
            if entry[0] <= now:
                del self._entries[key]

    def remember(self, event):
        source = getattr(event, "source", None)
        if source is None or not callable(getattr(source, "to_dict", None)):
            return
        snapshot = source.to_dict()
        try:
            key = self._identity(snapshot.get("platform"), snapshot, getattr(event, "message_id", None))
            text = getattr(event, "text", None)
            if not isinstance(text, str) or len(text) > 1_000_000:
                return
            fingerprint = self._digest("text", text)
            quoted = self._identifier(getattr(event, "reply_to_message_id", None), optional=True)
        except ValueError:
            return
        bot = getattr(source, "is_bot", None)
        own = getattr(event, "reply_to_is_own_message", None)
        metadata = AdmissionMetadata(bot if type(bot) is bool else None, quoted,
                                     own if type(own) is bool else None)
        with self._lock:
            now = self.clock()
            self._prune(now)
            if key in self._entries:
                # Even matching repeated intake is ambiguous. Never select the
                # latest metadata or refresh this identity's expiration.
                until = self._entries[key][0]
                self._entries[key] = (until, fingerprint, None)
                return
            while len(self._entries) >= self.capacity:
                self._entries.popitem(last=False)
            self._entries[key] = (now + self.ttl, fingerprint, metadata)

    def take(self, values):
        try:
            key = self._identity(values.get("platform"), values.get("source"), values.get("message_id"))
            text = values.get("text")
            if not isinstance(text, str) or len(text) > 1_000_000:
                return None
            fingerprint = self._digest("text", text)
        except ValueError:
            return None
        with self._lock:
            now = self.clock()
            self._prune(now)
            entry = self._entries.get(key)
            if entry is None:
                return None
            # A consumed, ambiguous or rewritten identity remains a tombstone
            # until its original deadline. It cannot attach to a second turn.
            self._entries[key] = (entry[0], entry[1], None)
            return entry[2] if hmac.compare_digest(entry[1], fingerprint) else None

    def clear(self):
        with self._lock:
            self._entries.clear()

    def pending_count(self):
        with self._lock:
            self._prune(self.clock())
            return len(self._entries)


class TaskAdmissionMetadataHandoff:
    """Research-only handoff across scoped plugin instances, not across tasks.

    Hermes' async dispatcher invokes synchronous callbacks inline. Task-private
    state can survive a profile change without a process-global identity pool.
    Missing task, wrong scope, task handoff or rewriting remain unavailable.
    """
    ATTRIBUTE = '_hermes_alive_experimental_admission_metadata_v1'

    def __init__(self, *, ttl_seconds=30, max_pending=256):
        # Reuse strict lifetime validation, without creating files.
        AdmissionMetadataCache(ttl_seconds=ttl_seconds, capacity=max_pending)
        self.ttl = ttl_seconds
        self.max_pending = max_pending
        self._tasks = weakref.WeakSet()
        self._lock = threading.RLock()

    @staticmethod
    def _task():
        try:
            return asyncio.current_task()
        except RuntimeError:
            return None

    @staticmethod
    def _scope(home):
        return os.path.normcase(os.path.abspath(os.fspath(home)))

    @classmethod
    def _clear(cls, task, state):
        state['cache'].clear()
        state['timer'].cancel()
        if task is not None and getattr(task, cls.ATTRIBUTE, None) is state:
            delattr(task, cls.ATTRIBUTE)
        if task is not None:
            task.remove_done_callback(state['done_callback'])
        owner = state['owner']()
        if owner is not None and task is not None:
            with owner._lock:
                owner._tasks.discard(task)

    def remember(self, event, *, runtime_home):
        task = self._task()
        if task is None:
            return
        scope = self._scope(runtime_home)
        state = getattr(task, self.ATTRIBUTE, None)
        if state is None:
            with self._lock:
                if len(self._tasks) >= self.max_pending:
                    return
                self._tasks.add(task)
            cache = AdmissionMetadataCache(capacity=1, ttl_seconds=self.ttl)
            state = {'cache':cache, 'scope':cache._digest('runtime-home', scope),
                     'owner':weakref.ref(self), 'blocked':False}
            task_ref = weakref.ref(task)
            def expire():
                self._clear(task_ref(), state)
            state['timer'] = asyncio.get_running_loop().call_later(self.ttl, expire, context=Context())
            setattr(task, self.ATTRIBUTE, state)
            state['done_callback'] = lambda finished:self._clear(finished, state)
            task.add_done_callback(state['done_callback'], context=Context())
        if not hmac.compare_digest(state['scope'], state['cache']._digest('runtime-home', scope)):
            # Do not replace a source staged for another routed home.
            state['cache'].clear()
            state['blocked'] = True
            return
        if state['blocked']:
            return
        state['cache'].remember(event)

    def take(self, values, *, runtime_home):
        task = self._task()
        if task is None:
            return None
        state = getattr(task, self.ATTRIBUTE, None)
        if state is None:
            return None
        try:
            if state['blocked']:
                return None
            if not hmac.compare_digest(state['scope'], state['cache']._digest('runtime-home', self._scope(runtime_home))):
                return None
            return state['cache'].take(values)
        finally:
            self._clear(task, state)

    def clear_current(self):
        task = self._task()
        state = getattr(task, self.ATTRIBUTE, None) if task is not None else None
        if state is not None:
            self._clear(task, state)

    def pending_tasks(self):
        with self._lock:
            return len(self._tasks)
