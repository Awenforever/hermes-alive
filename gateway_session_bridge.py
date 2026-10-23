"""Core-owned exact session/receiving-bot routing, not a permission or sender.

Construct only from the trusted Gateway assembly. Reads reuse Core SessionStore,
identity restoration and delivery metadata; no default-bot or latest-chat search.
Private identifiers must not enter logs or the unencrypted Alive journal.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass,replace
from pathlib import Path
from types import MappingProxyType
import weakref


class SessionScopeUnavailable(ValueError):
    pass


def _identifier(value,*,optional=False):
    if optional and value is None:return ''
    if (not isinstance(value,str) or (not optional and not value)
            or value!=value.strip() or len(value)>4096
            or any(ord(c)<32 or ord(c)==127 or 0xD800<=ord(c)<=0xDFFF for c in value)):
        raise SessionScopeUnavailable('canonical session identity unavailable')
    return value


@dataclass(frozen=True,slots=True,repr=False)
class CoreConversationScope:
    runtime_profile:str
    transport_profile:str
    platform:str
    chat_id:str
    chat_type:str
    thread_id:str
    user_id:str
    scope_id:str
    guild_id:str
    parent_chat_id:str
    session_key:str
    session_id:str

    def binding_document(self):
        """Private data for a protected binding, NOT execution authorization."""
        return {'contract':'hermes-core-conversation-v1',
            **{name:getattr(self,name) for name in self.__dataclass_fields__}}

    @property
    def route(self):
        return MappingProxyType({'profile':self.runtime_profile,'platform':self.platform,
            'chat_id':self.chat_id,'thread_id':self.thread_id or None})

    def principal(self,protector):
        """Namespace users by Core's receiving realm, not a bare raw user ID.

        The per-profile installation identity key is migratable; physical paths,
        transient adapters and session IDs must not change a person's identity.
        This never imports/reassigns any legacy raw-ID memory or grant.
        """
        return 'user:core-v2:'+protector.authenticate_json('core.principal.v2',{
            'platform':self.platform,'transport_profile':self.transport_profile,
            'scope_id':self.scope_id,'guild_id':self.guild_id,'user_id':self.user_id})


class CoreSessionRouter:
    def __init__(self,context,gateway):
        self.home=Path(context._manager.scope_key).resolve()
        self._closed=False
        self._gateway=weakref.ref(gateway)
        self._loop=weakref.ref(asyncio.get_running_loop())
        for name in ('_restored_source','_delivery_adapter_for','_thread_metadata_for_source'):
            if not callable(getattr(gateway,name,None)):
                raise SessionScopeUnavailable('supported canonical Core route capability required')
        self._current()
        context.on_unload(self.close)

    def _current(self):
        from hermes_constants import get_hermes_home
        gateway=self._gateway() if self._gateway is not None else None
        if self._closed or gateway is None or Path(get_hermes_home()).resolve()!=self.home:
            raise SessionScopeUnavailable('Core session router retired or belongs to another profile')
        store=getattr(gateway,'session_store',None)
        if not callable(getattr(store,'lookup_by_session_key',None)):
            raise SessionScopeUnavailable('current Core routing store unavailable')
        # In a multiplexed Gateway the index legitimately lives in the primary
        # home. Its canonical source identity below must name THIS runtime home.
        if not getattr(getattr(gateway,'config',None),'multiplex_profiles',False):
            routing_home=getattr(store,'_routing_home',None)
            if routing_home is None or Path(routing_home).resolve()!=self.home:
                raise SessionScopeUnavailable('standalone Gateway belongs to another profile')
        return gateway,store

    def close(self):
        self._closed=True
        self._gateway=None

    def _snapshot(self,*,session_key,user_id,platform,session_id=None,connected=True):
        from gateway.session import SessionEntry
        from gateway.session_identity import replace_source,canonical_identity
        session_key=_identifier(session_key);user_id=_identifier(user_id);platform=_identifier(platform)
        if session_id is not None:_identifier(session_id)
        gateway,store=self._current()
        entry=store.lookup_by_session_key(session_key)
        if (not isinstance(entry,SessionEntry) or entry.session_key!=session_key
                or entry.origin is None or (session_id is not None and entry.session_id!=session_id)):
            raise SessionScopeUnavailable('exact current Core session unavailable')
        # Core restoration pins an identity on the source. Work on a Core-owned
        # copy; resolving an Alive snapshot must not mutate the routing entry.
        copied=replace(entry,origin=replace_source(entry.origin))
        if (getattr(copied.origin.platform,'value',None)!=platform or copied.origin.user_id!=user_id):
            raise SessionScopeUnavailable('Core session belongs to a different principal or platform')
        multiplexed=bool(getattr(gateway.config,'multiplex_profiles',False))
        if multiplexed and not copied.transport_profile:
            raise SessionScopeUnavailable('Core receiving-bot provenance unavailable; no default fallback')
        source=gateway._restored_source(copied)
        adapter=gateway._delivery_adapter_for(source)
        if connected and (adapter is None or getattr(adapter,'is_connected',False) is not True):
            raise SessionScopeUnavailable('canonical receiving adapter disconnected; no fallback')
        identity=canonical_identity(source,runner=gateway,adapter=adapter)
        if (identity is None or Path(identity.runtime_home).resolve()!=self.home
                or (multiplexed and (identity.transport_inferred
                    or identity.transport_profile!=copied.transport_profile))):
            raise SessionScopeUnavailable('Core identity differs from the owning runtime or receiver')
        if adapter is not None and getattr(adapter.platform,'value',None)!=platform:
            raise SessionScopeUnavailable('Core resolved a different platform')
        scope=CoreConversationScope(_identifier(identity.runtime_profile),
            _identifier(identity.transport_profile),platform,_identifier(source.chat_id),_identifier(source.chat_type),
            _identifier(source.thread_id,optional=True),user_id,
            _identifier(source.scope_id,optional=True),_identifier(source.guild_id,optional=True),
            _identifier(source.parent_chat_id,optional=True),session_key,_identifier(copied.session_id))
        self._current()
        # Reject an explicit /new/reset which raced resolution. No session is
        # created/touched and no active turn is interrupted by this reader.
        current=store.lookup_by_session_key(session_key)
        if (current is None or current.session_id!=scope.session_id or current.origin is None
                or current.transport_profile!=copied.transport_profile
                or any(getattr(current.origin,name,None)!=getattr(copied.origin,name,None)
                    for name in ('platform','profile','chat_id','chat_type','thread_id','user_id',
                                 'scope_id','guild_id','parent_chat_id'))):
            raise SessionScopeUnavailable('Core conversation changed during resolution')
        return scope,adapter,source

    def capture_target(self,*,session_key,user_id,platform):
        """Trusted setup/background target capture; NOT user/route approval."""
        return self._snapshot(session_key=session_key,user_id=user_id,platform=platform)[0]

    def for_turn(self,*,session_key,session_id,user_id,platform):
        """Read-only on a Core hook worker; caller must use admitted turn fields."""
        _identifier(session_id)
        return self._snapshot(session_key=session_key,session_id=session_id,
                              user_id=user_id,platform=platform,connected=False)[0]

    def scope_for_hook(self,values):
        """Core pre_llm_call envelope only; never infer identity from message text.

        A task-local key is mandatory. Legacy process environment cannot select
        a conversation; delegated/cron work does not borrow its parent's share.
        This locates a scope, not content-retention/retrieval permission.
        """
        from gateway.session_context import bound_session_key,get_session_env
        if (values.get('parent_session_id') or get_session_env('HERMES_CRON_SESSION')=='1'
                or not bound_session_key()):return None
        for name,field in (('ID','session_id'),('USER_ID','sender_id'),('PLATFORM','platform')):
            if get_session_env('HERMES_SESSION_'+name)!=values.get(field):
                raise SessionScopeUnavailable('Core turn context differs from its hook envelope')
        return self.for_turn(session_key=bound_session_key(),session_id=values.get('session_id'),
                             user_id=values.get('sender_id'),platform=values.get('platform'))

    def resolve_channel(self,scope,route):
        """Current Core adapter/metadata for the exact authenticated outbox route."""
        if not isinstance(scope,CoreConversationScope) or dict(route)!=dict(scope.route):
            raise SessionScopeUnavailable('channel route differs from the bound Core conversation')
        loop=self._loop()
        try:running=asyncio.get_running_loop()
        except RuntimeError:
            raise SessionScopeUnavailable('channel submission requires its Gateway loop') from None
        if loop is None or loop.is_closed() or running is not loop:
            raise SessionScopeUnavailable('channel submission requires its Gateway loop')
        current,adapter,source=self._snapshot(session_key=scope.session_key,
            session_id=scope.session_id,user_id=scope.user_id,platform=scope.platform)
        if current!=scope:
            raise SessionScopeUnavailable('Core conversation realm changed since binding')
        gateway,_=self._current()
        metadata=gateway._thread_metadata_for_source(source)
        if metadata is not None and not isinstance(metadata,dict):
            raise SessionScopeUnavailable('Core routing metadata unavailable')
        return adapter,dict(metadata or {})

    def standard_send_parameters(self,scope,*,continuity,clearance):
        """Real Core parsers plus mandatory same-router conversation capture.

        This only assembles callbacks. It grants no route, lease or delivery
        authority and performs no model call or send.
        """
        from .gateway_conversation_bridge import CoreShareContinuity
        from gateway.platforms.base import BasePlatformAdapter
        from tools.send_message_targets import resolve_send_target
        from hermes_constants import get_hermes_home
        if (not isinstance(continuity,CoreShareContinuity) or continuity.router is not self
                or continuity._closed or continuity.clearance!=clearance):
            raise SessionScopeUnavailable('owning conversation continuity required')
        self.resolve_channel(scope,scope.route)
        return dict(resolve_channel=lambda route:self.resolve_channel(scope,route),
            clearance=clearance,profile_id=scope.runtime_profile,hermes_home=self.home,
            resolve_target=resolve_send_target,extract_media=BasePlatformAdapter.extract_media,
            observe_profile_home=get_hermes_home,continuity=continuity.for_target(scope))
