"""Atomic evidence from completed owned reads, not a research-note authority.

No IO, source scoring, model call or memory writes. The host supplies the exact
read receipts; original content remains in the existing encrypted source vault.
"""
from .content_vault import ContentReference
from .events import Sensitivity
from .host_discovery import HostDiscoveryError, read_scope_metadata
from .discovery_opportunities import canonicalize_discovery_url
from urllib.parse import urlsplit
from . import source_reading_depth


RESEARCH_SOURCE_BUDGET = 64000  # <=4 retained8192-char reads plus bounded context/background.
RESEARCH_MESSAGE_BUDGET = 120000  # Reserve framing below Core's131072-char message admission.
RESEARCH_SCAN = 'atomic-research-source-budget-v1'


def research_read_headers(journal, *, subject, clearance, receipt_ids, before_sequence=None):
    """Historical scope only: cursor validation must not decrypt forgotten notes."""
    if (not isinstance(receipt_ids,tuple) or not 1<=len(receipt_ids)<=2
            or any(not isinstance(r,str) for r in receipt_ids)
            or len(set(receipt_ids))!=len(receipt_ids)):
        raise HostDiscoveryError('bounded research reads require current inquiry provenance')
    headers=[];last=0
    for identity in receipt_ids:
        done=journal.get(identity)
        start=journal.get(done.event.causation_id) if done is not None else None
        if (start is None or done.event.event_type!='discovery.host_read_completed'
                or start.event.event_type!='discovery.host_read_started'
                or not last<start.sequence<done.sequence
                or before_sequence is not None and done.sequence>=before_sequence):
            raise HostDiscoveryError('research read lacks original completed chronology')
        for record in (start,done):
            if (record.event.source!='alive.host-discovery'
                    or record.event.actor!='system:alive-host-reader'
                    or record.event.subject!=subject
                    or record.event.sensitivity is not Sensitivity(clearance)
                    or record.event.payload.get('delivery_authority_granted') is not False):
                raise HostDiscoveryError('research read has foreign scope or authority')
        ids=tuple(done.event.payload['observations'])
        if len(ids)>2 or len(set(ids))!=len(ids) or any(not isinstance(i,str) for i in ids):
            raise HostDiscoveryError('research read source count changed')
        headers.append((start,done));last=done.sequence
    return tuple(headers)


def resolve_research_reads(reader, *, subject, clearance, receipt_ids, inquiries,
                           before_sequence=None):
    if not inquiries:raise HostDiscoveryError('research reads require current inquiry provenance')
    journal,vault=reader.journal,reader.vault
    observations=[]
    for start,done in research_read_headers(journal,subject=subject,clearance=clearance,
            receipt_ids=receipt_ids,before_sequence=before_sequence):
        ref=ContentReference.from_event_payload(start.event.payload['request'])
        request=vault.resolve_json(ref.content_id,expected_subject=subject,
            expected_purpose='discovery.host-request',expected_sensitivity=start.event.sensitivity)
        expanded=request.get('read_window_policy')==source_reading_depth.WINDOW
        keys={'queries','read_urls','limit','tentative_discovery_tasks'}
        if expanded:keys.add('read_window_policy')
        if (ref.digest!=vault.digest_json(request)
                or set(request)!=keys
                or request['queries']!=[] or not isinstance(request['read_urls'],list)
                or not 1<=len(request['read_urls'])<=2
                or request['tentative_discovery_tasks']!=inquiries):
            raise HostDiscoveryError('research read does not belong to the current inquiry')
        ids=tuple(done.event.payload['observations'])
        if len(ids)>2 or len(set(ids))!=len(ids):
            raise HostDiscoveryError('research read source count changed')
        evidence=reader.active_evidence(subject=subject,clearance=clearance,
            limit=32,observation_event_ids=ids) if ids else ()
        if tuple(e.observation_event_id for e in evidence)!=ids:
            raise HostDiscoveryError('part of the research evidence was withdrawn or erased')
        try:
            requested_identities=set()
            for original_url in request['read_urls']:
                identity=canonicalize_discovery_url(original_url)
                parts=urlsplit(original_url)
                if parts.username is not None or parts.password is not None:
                    raise ValueError('credentialed URL is not an original public read')
                requested_identities.add(identity)
        except (TypeError,ValueError):
            raise HostDiscoveryError('research read request has invalid resource identity') from None
        for item in evidence:
            if (read_scope_metadata(item.content).get('reported_read_scope')!='webpage_extract'
                    or (item.content.get('attributes',{}).get('read_window_policy')==source_reading_depth.WINDOW)!=expanded
                    # Observations store canonical identities. Transport/citation
                    # authorization still uses exact original URLs in HostReader;
                    # never use this identity comparison to permit another fetch.
                    or item.content['url'] not in requested_identities
                    or journal.get(item.observation_event_id).sequence>=done.sequence):
                raise HostDiscoveryError('research read has no matching original page evidence')
            if item.observation_event_id not in observations:observations.append(item.observation_event_id)
    if not observations:raise HostDiscoveryError('research group contains no retained page evidence')
    resolved=reader.active_evidence(subject=subject,clearance=clearance,limit=32,
        observation_event_ids=tuple(observations))
    if tuple(e.observation_event_id for e in resolved)!=tuple(observations):
        raise HostDiscoveryError('research group changed during final resolution')
    return resolved


def research_scan(journal, *, focus, fair_pool, evidence, cursor, preference_digest):
    """Only the covered chronological prefix advances background discovery."""
    admitted={e.observation_event_id for e in evidence}
    next_cursor=cursor
    for item in fair_pool:
        if item.observation_event_id not in admitted:break
        record=journal.get(item.observation_event_id)
        if record.event.event_type=='discovery.opportunity_observed':next_cursor=record.sequence
    return dict(method=RESEARCH_SCAN,after_sequence=cursor,next_sequence=next_cursor,
        pool_size=len({e.observation_event_id for e in (*focus,*fair_pool)}),
        window_size=len(evidence),budget_chars=RESEARCH_SOURCE_BUDGET,
        focus_observation_ids=[e.observation_event_id for e in focus],
        fair_pool_observation_ids=[e.observation_event_id for e in fair_pool],
        preference_digest=preference_digest,world_coverage_proven=False)


def validate_research_scan(journal, start, scan, focus_ids):
    """Validate the retained packing/cursor without resurrecting unseen content."""
    focus_ids=tuple(focus_ids)
    fair_ids=tuple(scan.get('fair_pool_observation_ids',()))
    admitted=tuple(start.event.payload['observation_event_ids'])
    rest=tuple(i for i in fair_ids if i not in focus_ids)
    if (scan.get('method')!=RESEARCH_SCAN or scan.get('budget_chars')!=RESEARCH_SOURCE_BUDGET
            or scan.get('world_coverage_proven') is not False
            or tuple(scan.get('focus_observation_ids',()))!=focus_ids
            or len(set(fair_ids))!=len(fair_ids) or len(fair_ids)>32-len(focus_ids)
            or scan.get('pool_size')!=len(set(fair_ids)|set(focus_ids))
            or scan.get('window_size')!=len(admitted) or not len(focus_ids)<=len(admitted)<=32
            or any(type(scan.get(k)) is not int for k in ('pool_size','window_size','budget_chars'))
            or admitted!=focus_ids+rest[:len(admitted)-len(focus_ids)]
            or any(type(scan.get(k)) is not int or scan[k]<0 for k in ('after_sequence','next_sequence'))):
        raise HostDiscoveryError('atomic research scope or packing changed')
    previous=(-1,-1);expected=scan['after_sequence']
    advancing=True
    for identity in fair_ids:
        record=journal.get(identity)
        key=(0 if record is not None and record.sequence>scan['after_sequence'] else 1,
             record.sequence if record is not None else -1)
        if (record is None or record.event.subject!=start.event.subject
                or record.sequence>=start.sequence or key<=previous):
            raise HostDiscoveryError('research background pool chronology changed')
        previous=key
        if identity not in admitted:advancing=False
        if record.event.event_type=='discovery.opportunity_observed':
            if record.event.source!='alive.discovery' or record.event.actor!='system:alive-discovery':
                raise HostDiscoveryError('research background lacks source-cursor provenance')
            if advancing:expected=record.sequence
    if expected!=scan['next_sequence']:
        raise HostDiscoveryError('research priority skipped unseen background evidence')
    return scan
