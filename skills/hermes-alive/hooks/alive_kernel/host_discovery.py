"""Bounded owner-bound reads through capabilities supplied by the Hermes host.

No provider selection, credentials, memory discovery, scheduler or transport.
The host owns read authorization, URL safety, deadlines and physical cancellation.
Queries must already be approved for external disclosure, not arbitrary memories.
"""
import asyncio
import json
from dataclasses import dataclass
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from .discovery_opportunities import DiscoveryCandidate, canonicalize_discovery_url
from .events import EventEnvelope, Sensitivity, _thaw_json
from .native_worker_protocol import identifier
from .model_json import parse_model_json


class HostDiscoveryError(ValueError):
    pass


class HostReadUncertainError(HostDiscoveryError):
    """Host wait ended without proving that its physical read settled."""


def read_scope_metadata(content):
    """Collector-reported scope, never a claim of independent verification."""
    attrs=content.get('attributes')
    if (content.get('source') not in ('hermes.web.search','hermes.web.extract')
            or not isinstance(attrs,Mapping)
            or attrs.get('read_scope') not in ('search_listing','webpage_extract')):
        return {}
    metadata=dict(reported_read_scope=attrs['read_scope'],independent_verification_proven=False,
        video_consumption_proven=False,page_may_contain_navigation=attrs['read_scope']=='webpage_extract')
    if 'content_representation' in attrs:
        representation=attrs['content_representation']
        metadata['reported_content_representation']=(representation if representation in
            ('source_extract','operator_paraphrase','machine_summary') else 'unspecified')
    return metadata


def provenance_metadata(content):
    metadata={'collector':content['source'],**read_scope_metadata(content)}
    if 'origin_kind' in content:metadata['origin_kind']=content['origin_kind']
    if content.get('origin_kind')=='commitment':
        metadata.update(original_proposal_authority=content.get('original_proposal_authority'),
            literal_owner_confirmation=content.get('literal_owner_confirmation') is True,
            original_user_message_preserved=content.get('original_owner_message_included') is True,
            agenda_description_is_verbatim=False,authority_is_not_execution_permission=True)
        if 'core_work' in content:metadata['core_work']=_thaw_json(content['core_work'])
        if 'core_work_outcome' in content:metadata['core_work_outcome']=_thaw_json(content['core_work_outcome'])
        if 'autonomous_work_wait' in content:metadata['autonomous_work_wait']=_thaw_json(content['autonomous_work_wait'])
    return metadata


SOURCE_EXCERPT_POLICY = 'retained-web-extract-v1'


def source_prompt_excerpt(content, *, policy=None):
    """Versioned evidence window shared by interpretation and factual review.

    The bound covers the stored extraction, not an entire page or independent
    verification. Ordinary listings and admitted commitments keep their existing
    window. Old operation receipts without a policy retain their exact scope.
    """
    if policy not in (None, SOURCE_EXCERPT_POLICY):
        raise HostDiscoveryError('unknown source excerpt policy')
    if 'core_work' in content or 'autonomous_work_wait' in content or content.get('original_owner_message_included') is True:
        # Preserve the same lifecycle qualifications for interpretation, factual
        # review and follow-on context. Guided record excerpts remain historical,
        # never an independent result or a new execution authority.
        return json.dumps(_thaw_json({'interpreted_assignment_context':content['summary'],
            **({'original_owner_message':content['original_owner_message'],
                'source_recorded_at':content['source_recorded_at'],'source_timestamp_kind':content['source_timestamp_kind']}
               if content.get('original_owner_message_included') is True else {}),
            **({'owner_amendments':content['owner_amendments'],'owner_history_available':True}
               if 'owner_amendments' in content else
               {'owner_history_available':False} if content.get('owner_history_available') is False else {}),
            **({'core_work_lifecycle':dict(content['core_work'])} if 'core_work' in content else {}),
            **({'autonomous_work_wait':dict(content['autonomous_work_wait'])} if 'autonomous_work_wait' in content else {}),
            **({'core_work_outcome':dict(content['core_work_outcome'])} if 'core_work_outcome' in content else {}),
            **({'core_work_record_review':dict(content['core_work_record_review'])}
               if 'core_work_record_review' in content else {})}),ensure_ascii=False)
    depth = (policy == SOURCE_EXCERPT_POLICY
             and read_scope_metadata(content).get('reported_read_scope') == 'webpage_extract')
    return content['summary'][:8192 if depth else 1800]


@dataclass(frozen=True)
class HostDiscoveryResult:
    observation_ids: tuple[str, ...]
    failures: int
    receipt_id: str
    read_outcomes: tuple[tuple[str,int,str], ...] = ()


class HostDiscoveryReader:
    """One reader per owner capability; never learns interests from search text.

    Async host callbacks must return only after their owned read has settled and
    must reject new work while any physical read lease is uncertain. Cancellation
    also retires this instance. An incomplete durable operation is not retried.
    """
    def __init__(self, ingestor, *, subject, search, extract, allow_url, is_current,
                 context_vault=None, scope_search_views=False):
        self.subject=identifier(subject)
        if not all(callable(f) for f in (search,extract,allow_url,is_current)):
            raise HostDiscoveryError('explicit host read capabilities required')
        if type(scope_search_views) is not bool:
            raise HostDiscoveryError('explicit public search-view identity required')
        self.ingestor=ingestor
        self.context_vault=context_vault
        self.scope_search_views=scope_search_views
        self.search,self.extract,self.allow_url,self.is_current=search,extract,allow_url,is_current
        self._busy=False
        self._uncertain=False

    def _current(self):
        try: current=self.is_current() is True
        except Exception: current=False
        if not current:
            raise HostDiscoveryError('host read capability changed or revoked')

    @staticmethod
    def _document(raw):
        if not isinstance(raw,str) or len(raw)>262144:
            raise HostDiscoveryError('host read output exceeds boundary')
        value=parse_model_json(raw,max_chars=262144)
        if not isinstance(value,dict): raise HostDiscoveryError('invalid host read output')
        return value

    async def _admit(self, item, *, kind, observed, expected_url=None, search_query=None):
        if not isinstance(item,dict): raise HostDiscoveryError('invalid source observation')
        url=item.get('url')
        title=item.get('title')
        content=item.get('description','') if kind=='search' else item.get('content')
        if (not isinstance(url,str) or len(url)>4096 or not isinstance(title,str)
                or not 1<=len(title)<=512 or not isinstance(content,str) or len(content)>8192
                or (kind=='extract' and not content)):
            raise HostDiscoveryError('invalid bounded source observation')
        try:
            parts=urlsplit(url)
            parts.port  # Reject an invalid port before invoking a read capability.
        except ValueError: raise HostDiscoveryError('invalid source URL') from None
        if (parts.scheme not in ('http','https') or not parts.hostname
                or parts.username is not None or parts.password is not None
                or (expected_url is not None and url!=expected_url)):
            raise HostDiscoveryError('unexpected source URL')
        self._current()
        if await self.allow_url(url) is not True:
            raise HostDiscoveryError('host refused source URL')
        self._current()
        # Distinct evidence scopes cannot overwrite one another on later fetches:
        # a new listing is not a retraction/replacement of a prior original read.
        # Different queries can describe the same page differently without a
        # material change to the page. Keep those search views separate too.
        view={}
        if kind=='search' and self.scope_search_views:
            if not isinstance(search_query,str) or not search_query.strip():
                raise HostDiscoveryError('public search view lacks its owning query')
            view['external_id']='query-view:'+self.ingestor.vault.digest_json(dict(
                query=search_query,url=canonicalize_discovery_url(url)))
        try:
            candidate=DiscoveryCandidate(source='hermes.web.'+kind,title=title,url=url,
                summary=content,observed_at=observed,published_at=None,**view,
                attributes=dict(read_scope='search_listing' if kind=='search' else 'webpage_extract',
                    publication_date_unresolved=True,independently_verified=False,
                    video_watched=False,page_may_contain_navigation=kind=='extract',
                    **({'content_representation':item['content_representation']
                        if isinstance(item['content_representation'],str) and item['content_representation'] in
                        ('source_extract','operator_paraphrase','machine_summary') else 'unspecified'}
                       if 'content_representation' in item else {})))
        except ValueError:
            raise HostDiscoveryError('invalid source candidate') from None
        ingested=self.ingestor.ingest(candidate,subject=self.subject)
        active=self.ingestor.active_evidence(subject=self.subject,clearance=Sensitivity.PRIVATE,
            limit=32,observation_event_ids=(ingested.observation_event_id,))
        if not active:
            raise HostDiscoveryError('read observation is not current')
        return ingested.observation_event_id

    async def collect(self, *, operation_id, queries=(), read_urls=(), limit=3,
                      inquiry_item_ids=()):
        identifier(operation_id)
        if (not isinstance(queries,tuple) or not isinstance(read_urls,tuple)
                or len(queries)>3 or len(read_urls)>2 or not queries and not read_urls
                or any(not isinstance(q,str) or not 1<=len(q)<=128 or not q.strip() for q in queries)
                or any(not isinstance(u,str) or not 1<=len(u)<=4096 for u in read_urls)
                or type(limit) is not int or not 1<=limit<=5):
            raise HostDiscoveryError('invalid bounded host discovery request')
        if self._busy or self._uncertain:
            raise HostDiscoveryError('owned host read is busy or uncertain')
        self._current()
        request=dict(queries=list(queries),read_urls=list(read_urls),limit=limit)
        if queries and self.scope_search_views:request['search_view_identity']='query-v1'
        from .discovery_inquiry import DiscoveryInquiryContext
        inquiry_context = DiscoveryInquiryContext(self.ingestor,context_vault=self.context_vault)
        inquiries = inquiry_context.read(subject=self.subject, clearance=Sensitivity.PRIVATE,
                                         item_ids=inquiry_item_ids)
        if inquiry_item_ids:
            request['tentative_discovery_tasks'] = inquiries
        def check_inquiries():
            if inquiry_context.read(subject=self.subject, clearance=Sensitivity.PRIVATE,
                                    item_ids=inquiry_item_ids) != inquiries:
                raise HostDiscoveryError('reading task changed during host read')
        vault=self.ingestor.vault
        operation=vault.digest_json(dict(subject=self.subject,operation_id=operation_id))[:40]
        prefix='discovery.host-read:'+operation
        journal=self.ingestor.journal
        start=journal.get(prefix+':started')
        if start is not None:
            ref=start.event.payload['request']
            retained=vault.resolve_json(ref['content_id'],expected_subject=self.subject,
                expected_purpose='discovery.host-request')
            if retained!=request: raise HostDiscoveryError('host discovery operation reused')
            done=journal.get(prefix+':completed')
            if done is None: raise HostDiscoveryError('incomplete host read requires reconciliation')
            if (start.event.subject!=self.subject or start.event.source!='alive.host-discovery'
                    or done.event.subject!=self.subject or done.event.source!=start.event.source
                    or done.event.actor!=start.event.actor or done.event.causation_id!=start.event.event_id
                    or done.event.payload.get('delivery_authority_granted') is not False):
                raise HostDiscoveryError('host discovery receipt has wrong binding')
            ids=tuple(done.event.payload['observations'])
            if ids:
                evidence=self.ingestor.active_evidence(subject=self.subject,clearance=Sensitivity.PRIVATE,
                    limit=32,observation_event_ids=ids)
                if {e.observation_event_id for e in evidence}!=set(ids):
                    raise HostDiscoveryError('host discovery receipt sources are no longer current')
            self._current()
            check_inquiries()
            return HostDiscoveryResult(tuple(done.event.payload['observations']),
                done.event.payload['failures'],done.event.event_id,
                tuple(tuple(x) for x in done.event.payload.get('read_outcomes',())))
        self._busy=True
        observed=datetime.now(timezone.utc)
        try:
            ref=vault.put_json(request,subject=self.subject,purpose='discovery.host-request',
                retention_until=observed+timedelta(days=7))
            common=dict(source='alive.host-discovery',actor='system:alive-host-reader',
                subject=self.subject,sensitivity=Sensitivity.PRIVATE)
            started=journal.append(EventEnvelope(event_id=prefix+':started',event_type='discovery.host_read_started',
                **common,payload=dict(request=ref.to_event_payload(),delivery_authority_granted=False)))
            if not started.created: raise HostDiscoveryError('host discovery operation already started')
            observations=[]; failures=0; outcomes=[]
            for kind,values in (('search',queries),('extract',read_urls)):
                for index,value in enumerate(values):
                    self._current()
                    check_inquiries()
                    try:
                        if kind=='extract':
                            parts=urlsplit(value)
                            if (parts.scheme not in ('http','https') or not parts.hostname
                                    or parts.username is not None or parts.password is not None
                                    or await self.allow_url(value) is not True):
                                raise HostDiscoveryError('host refused extraction URL')
                            self._current()
                        raw=await (self.search(value,limit=limit) if kind=='search'
                                   else self.extract([value],char_limit=6000))
                        self._current()
                        check_inquiries()
                        document=self._document(raw)
                        if kind=='search':
                            data=document.get('data')
                            if document.get('success') is not True or not isinstance(data,dict):
                                raise HostDiscoveryError('host search returned failure')
                            items=data.get('web')
                        else:
                            items=document.get('results')
                        if (not isinstance(items,list) or len(items)>(limit if kind=='search' else 1)
                                or kind=='extract' and len(items)!=1):
                            raise HostDiscoveryError('host source result count differs from request')
                    except asyncio.CancelledError:
                        self._uncertain=True
                        raise
                    except HostReadUncertainError:
                        self._uncertain=True
                        raise
                    except Exception:
                        self._current(); check_inquiries(); failures+=1
                        outcomes.append((kind,index,'read_failed')); continue
                    before_failures=failures
                    seen_search_urls=set()
                    for item in items:
                        if kind=='extract' and (not isinstance(item,dict) or item.get('error')):
                            failures+=1; continue
                        try:
                            view_url=None
                            if kind=='search' and self.scope_search_views and isinstance(item,dict):
                                try:view_url=canonicalize_discovery_url(item.get('url'))
                                except ValueError:pass  # _admit reports malformed items normally.
                                if view_url and view_url in seen_search_urls:continue
                            observations.append(await self._admit(item,kind=kind,observed=datetime.now(timezone.utc),
                                expected_url=value if kind=='extract' else None,
                                search_query=value if kind=='search' else None))
                            if view_url:seen_search_urls.add(view_url)
                        except HostDiscoveryError:
                            self._current(); failures+=1
                    outcomes.append((kind,index,'partial_or_refused' if failures>before_failures
                        else 'observed' if items else 'empty'))
            self._current()
            check_inquiries()
            done=journal.append(EventEnvelope(event_id=prefix+':completed',event_type='discovery.host_read_completed',
                causation_id=prefix+':started',**common,payload=dict(
                    observations=list(dict.fromkeys(observations)),failures=failures,read_outcomes=outcomes,
                    delivery_authority_granted=False)))
            return HostDiscoveryResult(tuple(done.event.payload['observations']),failures,done.event.event_id,
                tuple(outcomes))
        except BaseException:
            self._uncertain=True
            raise
        finally:
            self._busy=False
