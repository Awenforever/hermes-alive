"""Profile-owned context IO, physically retained across cancellation/unload.

No model, credentials, public search or channel dispatch. The native host lends
a current cycle binding to each call; Core supplies the context-bound thread.
The worker holds the profile lock, not the logically cancellable waiting task.
"""
import asyncio
import inspect
import math
from pathlib import Path

from .native_worker_protocol import NativeWorkerError


class ContextReadUncertainError(NativeWorkerError):
    pass


async def context_value(read_context,operation):
    """Default synchronous embedding remains supported; no implicit executor."""
    return operation() if read_context is None else await read_context(operation)


class CoreContextRead:
    def __init__(self,context,*,timeout_seconds=30):
        if (type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds)
                or not 0<timeout_seconds<=120 or not callable(getattr(context,'on_unload',None))):
            raise NativeWorkerError('bounded supervised context reads required')
        self.home=Path(context._manager.scope_key).resolve()
        self.timeout_seconds=timeout_seconds
        self._thread=None;self._future=None;self._closed=False
        context.on_unload(self.close)

    def close(self):
        # Never release the physical worker's lock or cancel its future here.
        self._closed=True

    @property
    def pending(self):
        return ({'phase':'context_read','local_task_closed':False},) if (
            self._thread is not None and self._thread.is_alive()) else ()

    async def reap_pending(self,*,timeout_seconds=0):
        if (type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds)
                or not 0<=timeout_seconds<=120):
            raise NativeWorkerError('bounded context settlement wait required')
        deadline=asyncio.get_running_loop().time()+timeout_seconds
        had_thread=self._thread is not None
        while self.pending and asyncio.get_running_loop().time()<deadline:
            await asyncio.sleep(.005)
        if not self.pending and self._future is not None and self._future.done():
            if not self._future.cancelled():self._future.exception()
        return dict(closed=int(had_thread and not self.pending),remaining=len(self.pending),retired=self._closed)

    def _current(self,read_binding,expected=None):
        from hermes_constants import get_hermes_home
        if self._closed or Path(get_hermes_home()).resolve()!=self.home:
            raise NativeWorkerError('context read capability closed or wrong profile')
        binding=read_binding()
        if binding is None or expected is not None and binding!=expected:
            raise NativeWorkerError('context read cycle authority changed')
        return binding

    def ensure_available(self):
        """Fence a replacement host before public/model preparation can start."""
        from hermes_constants import get_hermes_home
        from .file_locks import file_lock
        if self._closed or Path(get_hermes_home()).resolve()!=self.home:
            raise NativeWorkerError('context read capability closed or wrong profile')
        if self.pending:raise ContextReadUncertainError('context work still physically pending')
        try:
            with file_lock(self.home/'plugin-data/hermes-alive/runtime/kernel/context-read.lock',timeout=0):pass
        except TimeoutError:
            raise ContextReadUncertainError('prior profile context work still active') from None

    async def invoke(self,operation,*,read_binding):
        if not callable(operation) or not callable(read_binding):
            raise NativeWorkerError('explicit current context read required')
        if self.pending:raise ContextReadUncertainError('context work still physically pending')
        binding=self._current(read_binding)
        await self.reap_pending()
        loop=asyncio.get_running_loop();future=loop.create_future()
        self._future=future
        def publish(value,error):
            if future.done():return
            if error is None:future.set_result(value)
            else:future.set_exception(error)
        def worker():
            value=None;error=None
            try:
                from .file_locks import file_lock
                with file_lock(self.home/'plugin-data/hermes-alive/runtime/kernel/context-read.lock',timeout=0):
                    self._current(read_binding,binding)
                    value=operation()
                    if inspect.isawaitable(value):
                        if inspect.iscoroutine(value):value.close()
                        raise NativeWorkerError('context worker cannot invoke asynchronous/model work')
            except BaseException as exception:
                # A local provider/parser exception may contain private content.
                # Keep no original message/cause in the published exception.
                error=NativeWorkerError('context read failed ('+type(exception).__name__+')')
            try:loop.call_soon_threadsafe(publish,value,error)
            except RuntimeError:
                # The old event loop may be gone. The physical lock has already
                # settled; no result is delivered into a replacement generation.
                pass
        from agent.memory_provider import spawn_context_thread
        self._thread=spawn_context_thread(worker,name='alive-context-read')
        self._thread.start()
        try:
            value=await asyncio.wait_for(asyncio.shield(future),self.timeout_seconds)
            while self.pending:await asyncio.sleep(.001)
            self._current(read_binding,binding)
            return value
        except TimeoutError:
            if self.pending:raise ContextReadUncertainError('context read wait ended before physical work') from None
            raise
