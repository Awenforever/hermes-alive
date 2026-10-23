"""Profile/generation-owned handles from Core's public platform factories.

This acquires a transport capability, not a recipient, route, grant or sender.
Core alone owns adapter connection/queue lifetime. Canonical route resolution and
authorized standard execution are separate; a captured handle is never readiness.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import re
import weakref


class ChannelCapabilityUnavailable(ValueError):
    pass


def _current_home():
    from hermes_constants import get_hermes_home
    return Path(get_hermes_home()).resolve()


class CoreChannelHandle:
    def __init__(self, context, platform, *, observe_home=_current_home):
        if (not isinstance(platform,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',platform)
                or not callable(getattr(context,'register_platform_handler',None))
                or not callable(getattr(context,'on_unload',None)) or not callable(observe_home)):
            raise ChannelCapabilityUnavailable('Core public platform factory/lifecycle capability required')
        self.home=Path(context._manager.scope_key).resolve()
        self.platform=platform
        self._observe_home=observe_home
        self._adapter=None
        self._loop=None
        self._closed=False
        self._ambiguous=False
        self._require_home()
        context.on_unload(self.close)
        context.register_platform_handler(platform,self._bind)

    def _require_home(self):
        if self._closed or Path(self._observe_home()).resolve()!=self.home:
            raise ChannelCapabilityUnavailable('channel handle retired or belongs to another profile')

    def _bind(self, native, adapter):
        # Targeted unload in current Core may retain this factory. A retired
        # generation must never reacquire a handle, even on a fresh adapter.
        if self._closed:
            return
        self._require_home()
        if self._ambiguous:
            raise ChannelCapabilityUnavailable('channel ambiguity requires a new host lifecycle')
        platform=getattr(adapter,'platform',None)
        if (getattr(platform,'value',platform)!=self.platform
                or not callable(getattr(adapter,'send',None))):
            raise ChannelCapabilityUnavailable('Core factory returned a different channel')
        try:
            loop=asyncio.get_running_loop()
            adapter_ref,loop_ref=weakref.ref(adapter),weakref.ref(loop)
        except (RuntimeError,TypeError) as exc:
            raise ChannelCapabilityUnavailable('live weak-referenceable Core adapter/loop required') from exc
        prior=self._adapter() if self._adapter else None
        if (prior is not None and prior is not adapter
                and getattr(prior,'is_connected',False) is True):
            # Do not choose between two connected accounts/instances merely
            # because one callback ran later. Rebuild the Gateway lifecycle.
            self._adapter=None
            self._loop=None
            self._ambiguous=True
            raise ChannelCapabilityUnavailable('multiple live channel handles require host reconciliation')
        self._adapter,self._loop=adapter_ref,loop_ref

    def adapter(self):
        """Current scoped handle only; not a recipient/authorization resolver."""
        self._require_home()
        adapter=self._adapter() if self._adapter else None
        loop=self._loop() if self._loop else None
        try:
            current_loop=asyncio.get_running_loop()
        except RuntimeError as exc:
            raise ChannelCapabilityUnavailable('channel access requires its Gateway loop') from exc
        if (self._ambiguous or adapter is None or loop is not current_loop or loop.is_closed()
                or getattr(adapter,'is_connected',False) is not True):
            raise ChannelCapabilityUnavailable('current connected channel unavailable; no fallback')
        return adapter

    def status(self):
        """Local capability diagnostic, not cross-process Gateway health."""
        self._require_home()
        adapter=self._adapter() if self._adapter else None
        loop=self._loop() if self._loop else None
        return {'platform':self.platform,'bound':adapter is not None,
            'ambiguous':self._ambiguous,
            'connected':adapter is not None and getattr(adapter,'is_connected',False) is True,
            'loop_available':loop is not None and not loop.is_closed(),
            'recipient_authorized':False,'external_delivery_proven':False}

    def close(self):
        self._closed=True
        self._adapter=None
        self._loop=None
        # Never disconnect/cancel the Core-owned adapter or mutate its registry.


def known_core_channels():
    """Read Core's names, never materialize config, SDKs or deferred adapters.

    Loading full Gateway config inside register() can request a deferred platform
    loader whose discovery lock is held by the thread waiting for register().
    Connection, not presence in this inventory, determines channel readiness.
    """
    from gateway.config import Platform
    from gateway.platform_registry import platform_registry
    return {p.value for p in Platform} | platform_registry.registered_names()


def register_core_channels(context, *, existing=None):
    """Inherit non-materializing Core inventory; refresh after discovery too."""
    result={} if existing is None else existing
    created=[]
    try:
        for name in sorted(known_core_channels()):
            if name in result:
                continue
            result[name]=CoreChannelHandle(context,name)
            created.append(name)
    except BaseException:
        for name in created:
            result.pop(name).close()
        raise
    return result
