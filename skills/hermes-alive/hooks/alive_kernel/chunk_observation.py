"""Research-only owned send-boundary observation; not installed in production.

Operator qualification is required: normal return at this specific chunk seam
must mean protocol acknowledgement. These observations are not user receipt,
quote mapping, a complete inventory, an authorization or a channel queue.
"""
import asyncio
from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class ChunkReturnObservation:
    ordinal: int
    scoped_client_reference: str


class OwnedChunkObserver:
    def __init__(self, adapter, *, protector, subject, route, qualified=False, limit=128):
        if qualified is not True or type(limit) is not int or not 1 <= limit <= 1024:
            raise ValueError('explicit operator qualification and bounded capacity required')
        if not isinstance(subject, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}', subject):
            raise ValueError('invalid observation owner')
        if (set(route) != {'platform', 'profile', 'chat_id', 'thread_id'}
                or route['platform'] != 'weixin'
                or any(not isinstance(route[k], str) or not route[k] for k in ('profile', 'chat_id'))
                or (route['thread_id'] is not None and not isinstance(route['thread_id'], str))):
            raise ValueError('exact operator route required')
        self.adapter, self.protector, self.subject = adapter, protector, subject
        self.route, self.limit = dict(route), limit
        self._observations = []
        self.failures = self.cancellations = 0
        self.observation_failed = self.capacity_exceeded = False
        self.unscoped_same_chat_calls = self.restoration_conflicted = False
        self._entered = False
        self._closed = self.active = False
        self._inflight_owned = 0
        self.closed_with_pending_calls = False

    @property
    def observations(self):
        return tuple(self._observations)

    async def __aenter__(self):
        if self._closed or self._entered or getattr(self.adapter, '_alive_owned_chunk_observer', None) is not None:
            raise ValueError('observer already installed or reused')
        self.task = asyncio.current_task()
        if self.task is None:
            raise ValueError('observation requires an owning asyncio task')
        original = self.adapter._send_text_chunk
        self._had_instance_method = '_send_text_chunk' in vars(self.adapter)
        self._prior_instance_method = vars(self.adapter).get('_send_text_chunk')
        if not callable(original):
            raise ValueError('qualified chunk seam unavailable')
        async def wrapper(*args, **kwargs):
            if not self.active:
                return await original(*args, **kwargs)
            scoped = asyncio.current_task() is self.task and kwargs.get('chat_id') == self.route['chat_id']
            if not scoped and kwargs.get('chat_id') == self.route['chat_id']:
                self.unscoped_same_chat_calls = True
            if scoped:
                self._inflight_owned += 1
            try:
                result = await original(*args, **kwargs)
            except asyncio.CancelledError:
                if scoped and self.active:
                    self.cancellations += 1
                raise
            except BaseException:
                if scoped and self.active:
                    self.failures += 1
                raise
            finally:
                if scoped:
                    self._inflight_owned -= 1
            if scoped and self.active:
                try:
                    identifier = kwargs.get('client_id')
                    if (result is not None or not isinstance(identifier, str)
                            or not 1 <= len(identifier) <= 512 or identifier != identifier.strip()
                            or any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in identifier)):
                        raise ValueError('qualified chunk result/identity unavailable')
                    if len(self.observations) >= self.limit:
                        self.capacity_exceeded = True
                    else:
                        reference = self.protector.authenticate_json('alive.chunk-return.v1',
                            {'subject': self.subject, 'route': self.route, 'client_id': identifier})
                        if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{64}', reference):
                            raise ValueError('invalid protected chunk reference')
                        self._observations.append(ChunkReturnObservation(len(self.observations) + 1, reference))
                except Exception:
                    # No body/token/error detail is retained or logged. Observation
                    # failure must not replace a completed original IO result.
                    self.observation_failed = True
            return result
        self.wrapper = wrapper
        self.active = True
        self.adapter._alive_owned_chunk_observer = self
        self.adapter._send_text_chunk = wrapper
        self._entered = True
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if self._closed:
            return False
        self._closed = True
        self.closed_with_pending_calls = self._inflight_owned > 0
        self.active = False
        if not self._entered:
            self.adapter = None
            return False
        if vars(self.adapter).get('_send_text_chunk') is self.wrapper:
            if self._had_instance_method:
                self.adapter._send_text_chunk = self._prior_instance_method
            else:
                del self.adapter._send_text_chunk
        else:
            # Another owner replaced the method; never clobber its hook on exit.
            self.restoration_conflicted = True
        if getattr(self.adapter, '_alive_owned_chunk_observer', None) is self:
            del self.adapter._alive_owned_chunk_observer
        self.task = None
        self.adapter = self.wrapper = self._prior_instance_method = None
        return False  # Original exceptions/cancellation always propagate.
