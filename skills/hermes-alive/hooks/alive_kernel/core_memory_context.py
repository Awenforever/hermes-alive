"""Separately granted semantic reads through Core's configured external memory.

No provider-specific query rewriting, database access, model routing or permanent
memory import. Empty Core output is deliberately not a claim of absent memories.
The caller owns Native lifetime and must revalidate its current read authority.
"""
from datetime import datetime,timezone
from pathlib import Path
from contextlib import contextmanager
from contextvars import ContextVar

from .events import EventEnvelope,Sensitivity

_CURRENT_RECALL=ContextVar('alive_current_core_recall',default=None)


@contextmanager
def core_memory_cycle():
    """A shared slot for one private cycle, including its child async contexts.

    Captured async/thread contexts share a close flag. They cannot retain access
    after the originating scope exits. No raw recall text enters a durable store.
    """
    holder={'closed':False,'published':False,'capability':None,'evidence':None}
    token=_CURRENT_RECALL.set(holder)
    try:yield
    finally:
        holder['closed']=True;holder['evidence']=None
        _CURRENT_RECALL.reset(token)


def publish_core_memory_context(capability,result):
    """Publish once after Core IO, without changing a child's ContextVar token."""
    if not isinstance(capability,CoreMemoryRecall) or not isinstance(result,dict):
        raise ValueError('Core memory capability and result required')
    holder=_CURRENT_RECALL.get()
    if holder is None or holder['closed'] or holder['published']:
        raise ValueError('an open unpublished private cycle is required')
    evidence=result.get('evidence') if result.get('status')=='recalled' else None
    verified=capability.checked_evidence(evidence) if evidence is not None else None
    if holder['closed'] or holder['published']:raise ValueError('private cycle changed during publication')
    holder.update(capability=capability,evidence=verified,published=True)


@contextmanager
def core_memory_context(capability,result):
    with core_memory_cycle():
        publish_core_memory_context(capability,result)
        yield


def current_core_memory_evidence(journal,*,subject):
    holder=_CURRENT_RECALL.get()
    if holder is None or holder['closed'] or not holder['published'] or holder['evidence'] is None:return None
    capability=holder['capability']
    if (capability.configured.subject!=subject
            or capability.store.journal.path.resolve()!=journal.path.resolve()):return None
    saved=holder['evidence']
    verified=capability.checked_evidence(saved)
    if holder['closed'] or holder['evidence'] is not saved:return None
    return verified


class CoreMemoryRecall:
    def __init__(self,store,configured,*,validate):
        if not callable(validate):raise ValueError('current read authority required')
        self.store=store;self.configured=configured;self.validate=validate

    def _current(self):
        from hermes_constants import get_hermes_home
        self.validate()
        home=Path(get_hermes_home()).resolve()
        if self.store.root.resolve()!=(home/'plugin-data/hermes-alive/runtime/kernel').resolve():
            raise ValueError('Core memory read belongs to another profile')
        current=self.store.configuration()
        if (current is None or current!=self.configured or current.scope['chat_type']!='dm'
                or current.options.get('use_hermes_external_memory') is not True):
            raise ValueError('current personal external-memory grant required')
        confirmed=self.store.journal.get(current.event_id).sequence
        for record in self.store.journal.iter_reverse(
                event_types=('retention.erasure_requested',),subject=current.subject):
            event=record.event
            if (record.sequence>confirmed and event.actor==current.subject
                    and event.source=='hermes.command.memory' and event.payload.get('scope')=='subject'):
                raise ValueError('external-memory read grant was forgotten')
        from hermes_cli.config import load_config_readonly
        config=load_config_readonly()
        # A fingerprint binds config, including provider settings, without
        # persisting endpoint credentials or copying them into another client.
        snapshot=self.store.protector.authenticate_json('alive.core-memory.config.v1',{
            'memory':config.get('memory',{}),'plugins':config.get('plugins',{})})
        provider=(config.get('memory') or {}).get('provider','builtin')
        if not isinstance(provider,str) or len(provider)>128:raise ValueError('invalid Core memory selection')
        return home,provider,snapshot

    def read(self,query):
        if (not isinstance(query,str) or not query.strip() or query!=query.strip()
                or len(query)>512 or '\x00' in query):
            raise ValueError('a bounded semantic memory question is required')
        home,provider,snapshot=self._current()
        if provider=='builtin':return {'status':'no_external_provider','evidence':None}
        from plugins.memory import load_memory_provider
        from agent.memory_manager import MemoryManager
        try:
            memory=load_memory_provider(provider,register_skills=False)
            available=memory is not None and memory.is_available()
        except (ImportError,ValueError,RuntimeError,OSError):available=False
        if not available:
            self._unchanged(home,provider,snapshot)
            return {'status':'provider_unavailable','evidence':None}
        manager=MemoryManager()
        scope=self.configured.scope;answer='';active=False
        try:
            self._unchanged(home,provider,snapshot)
            manager.add_provider(memory)
            active=manager.initialize_for_agent(session_id=scope['session_id'],hermes_home=str(home),
                platform=scope['platform'],agent_context='cron',user_id=scope['user_id'],chat_id=scope['chat_id'])
            if active:
                self._unchanged(home,provider,snapshot)
                answer=manager.prefetch_all(query,session_id=scope['session_id'])
        finally:
            # Core owns provider IO and its bounded drains. In particular a
            # timed-out prefetch may still have a Core-owned physical thread;
            # releasing this client does not prove that thread terminated.
            manager.shutdown_all()
        self._unchanged(home,provider,snapshot)
        if not active or not answer:
            return {'status':'no_usable_context_returned','evidence':None}
        if not isinstance(answer,str) or len(answer)>6000:
            return {'status':'context_exceeds_bound','evidence':None}
        payload={'method':'core-semantic-recall-v1','configuration_event_id':self.configured.event_id,
            'provider':provider,'provider_config_fingerprint':snapshot,
            'query_fingerprint':self.store.protector.authenticate_json('alive.core-memory.query.v1',query),
            'context_fingerprint':self.store.protector.authenticate_json('alive.core-memory.context.v1',answer),
            'user_explicit_statement':False,'execution_authority_granted':False,
            'raw_content_stored':False,'physical_core_io_termination_proven':False}
        event_id='core.memory-context:'+self.store.protector.authenticate_json(
            'alive.core-memory.observation.v1',{'subject':self.configured.subject,**payload})
        existing=self.store.journal.get(event_id)
        if existing is None:
            self._unchanged(home,provider,snapshot)
            self.store.journal.append(EventEnvelope(event_id=event_id,
                event_type='memory.core_recall_observed',source='alive.core-memory-context',
                actor='system:alive-core-memory-reader',subject=self.configured.subject,
                sensitivity=Sensitivity.PRIVATE,causation_id=self.configured.event_id,payload=payload))
            existing=self.store.journal.get(event_id)
        event=existing.event
        if (event.event_type!='memory.core_recall_observed' or event.subject!=self.configured.subject
                or event.actor!='system:alive-core-memory-reader' or event.source!='alive.core-memory-context'
                or event.causation_id!=self.configured.event_id or dict(event.payload)!=payload
                or event.observed_at>datetime.now(timezone.utc)):
            raise ValueError('Core memory observation provenance changed')
        self._unchanged(home,provider,snapshot)
        return {'status':'recalled','evidence':{
            'memory_id':event_id,'proposal_event_id':event_id,
            'source_event_ids':(self.configured.event_id,event_id),
            'predicate':'context.hermes_external_recall','kind':'core_recalled_advisory','value':answer,
            'source_observations':((event_id,event.observed_at.isoformat()),)}}

    def _unchanged(self,home,provider,snapshot):
        if self._current()!=(home,provider,snapshot):raise ValueError('Core memory read authority changed')

    def checked_evidence(self,evidence):
        if (not isinstance(evidence,dict) or not isinstance(evidence.get('value'),str)
                or len(evidence['value'])>6000 or not isinstance(evidence.get('memory_id'),str)):
            raise ValueError('Core memory evidence required')
        _,provider,snapshot=self._current()
        record=self.store.journal.get(evidence.get('memory_id'))
        if record is None:raise ValueError('Core memory observation unavailable')
        event=record.event;payload=dict(event.payload)
        expected='core.memory-context:'+self.store.protector.authenticate_json(
            'alive.core-memory.observation.v1',{'subject':self.configured.subject,**payload})
        if (event.event_id!=expected or event.event_type!='memory.core_recall_observed'
                or event.actor!='system:alive-core-memory-reader' or event.source!='alive.core-memory-context'
                or event.subject!=self.configured.subject or event.sensitivity is not Sensitivity.PRIVATE
                or event.causation_id!=self.configured.event_id
                or payload.get('configuration_event_id')!=self.configured.event_id
                or payload.get('provider')!=provider or payload.get('provider_config_fingerprint')!=snapshot
                or payload.get('user_explicit_statement') is not False
                or payload.get('execution_authority_granted') is not False
                or payload.get('raw_content_stored') is not False
                or payload.get('context_fingerprint')!=self.store.protector.authenticate_json(
                    'alive.core-memory.context.v1',evidence['value'])):
            raise ValueError('Core memory evidence changed or lost its read grant')
        return {'memory_id':event.event_id,'proposal_event_id':event.event_id,
            'source_event_ids':(self.configured.event_id,event.event_id),
            'predicate':'context.hermes_external_recall','kind':'core_recalled_advisory','value':evidence['value'],
            'source_observations':((event.event_id,event.observed_at.isoformat()),)}
