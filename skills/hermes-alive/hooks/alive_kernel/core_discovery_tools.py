"""Owner-bound Core web tools; no provider, scheduler, or delivery implementation.

Synchronous Core dispatch cannot be forcibly cancelled. Shield and retain its
task, and hold a profile file lock inside the physical worker until it returns.
Timeout/unload retires this capability, never claiming the read was stopped.
"""
import asyncio
import json
import math
from pathlib import Path

from .host_discovery import HostDiscoveryError,HostReadUncertainError


class CoreDiscoveryTools:
    def __init__(self, context, *, read_binding, approved_queries, timeout_seconds=60):
        if (not callable(read_binding) or not isinstance(approved_queries, tuple)
                or len(approved_queries)>3 or any(not isinstance(q,str) or not q.strip()
                or len(q)>128 for q in approved_queries)
                or type(timeout_seconds) not in (int,float)
                or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=120):
            raise HostDiscoveryError('explicit bounded approved public queries required')
        self.context=context
        self.home=Path(context._manager.scope_key).resolve()
        self.read_binding=read_binding
        self.approved_queries=approved_queries
        self.timeout_seconds=timeout_seconds
        self._active=None
        self._closed=False
        context.on_unload(self.close)

    def close(self):
        self._closed=True

    @property
    def pending(self):
        return self._active is not None and not self._active.done()

    async def reap_pending(self, *, timeout_seconds=0):
        if type(timeout_seconds) not in (int,float) or not 0<=timeout_seconds<=120:
            raise HostDiscoveryError('bounded settlement wait required')
        if self.pending and timeout_seconds:
            await asyncio.wait((self._active,),timeout=timeout_seconds)
        if self._active is not None and self._active.done():
            if not self._active.cancelled(): self._active.exception()
        return dict(remaining=int(self.pending),retired=self._closed)

    def _current(self, expected=None):
        from hermes_constants import get_hermes_home
        if self._closed or Path(get_hermes_home()).resolve()!=self.home:
            raise HostDiscoveryError('Core public-read capability closed or wrong profile')
        binding=self.read_binding()
        if binding is None or expected is not None and binding!=expected:
            raise HostDiscoveryError('Core public-read authority changed')
        return binding

    async def _invoke(self, operation):
        if self.pending: raise HostDiscoveryError('Core public read still physically pending')
        binding=self._current()
        def worker():
            from safe_io import file_lock
            # Same lock across instances/module generations/processes. It is held
            # by the worker, not the waiting task: cancellation cannot release it.
            with file_lock(self.home/'plugin-data/hermes-alive/runtime/kernel/public-read.lock',timeout=0):
                self._current(binding)
                return operation()
        self._active=asyncio.create_task(asyncio.to_thread(worker))
        self._active.add_done_callback(lambda task: None if task.cancelled() else task.exception())
        try:
            result=await asyncio.wait_for(asyncio.shield(self._active),self.timeout_seconds)
            self._current(binding)
            return result
        except TimeoutError:
            self.close()
            if self.pending:
                raise HostReadUncertainError('Core physical public read has not settled') from None
            raise
        except BaseException:
            self.close()
            raise

    async def allow_url(self,url):
        def check():
            from tools.web_tools_extract import _validate_extract_urls
            from tools.url_safety import async_is_safe_url
            normalized,indices,invalid,blocked=_validate_extract_urls([url])
            if blocked is not None or invalid or len(normalized)!=1: return False
            return asyncio.run(async_is_safe_url(normalized[0])) is True
        return await self._invoke(check)

    async def _dispatch(self,name,args):
        result=await self._invoke(lambda:self.context.dispatch_tool(name,args))
        if isinstance(result,dict): result=json.dumps(result,ensure_ascii=False,allow_nan=False)
        if not isinstance(result,str) or len(result)>262144:
            raise HostDiscoveryError('Core public-read result exceeds boundary')
        return result

    async def search(self,query,*,limit):
        if query not in self.approved_queries or type(limit) is not int or not 1<=limit<=5:
            raise HostDiscoveryError('query not approved for external disclosure')
        return await self._dispatch('web_search',dict(query=query,limit=limit))

    async def extract(self,urls,*,char_limit):
        if (not isinstance(urls,list) or len(urls)!=1 or not isinstance(urls[0],str)
                or not 1<=len(urls[0])<=4096 or type(char_limit) is not int or not 1<=char_limit<=6000):
            raise HostDiscoveryError('bounded single public URL required')
        # Core web_extract repeats URL/secret/SSRF checks immediately before IO.
        return await self._dispatch('web_extract',dict(urls=urls,char_limit=char_limit))
