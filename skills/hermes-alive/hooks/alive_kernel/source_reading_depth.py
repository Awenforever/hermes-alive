"""A bounded alternative inside the existing public followup, never a crawler."""
METHOD = 'public-source-depth-v2'
WINDOW = 'expanded-public-extract-v1'
EXTRACT_CHARS = 15000
RETURNED_CHARS = 16384  # Reserve Core's head/tail framing around the requested text.
EXCERPT_POLICY = 'retained-web-extract-v2'

GUIDANCE = '''
You may instead deepen ONE supplied webpage_extract by returning its exact
source_ref in deepen_source_ref. This uses the same optional followup allowance,
not another step after searching or following a citation. Search listings cannot
be deepened. The host re-extracts that resource with a larger bounded window;
you cannot choose a file path, request an arbitrary URL, or promise a whole-page
read. Existing extracts may omit methods, qualifications or dated context.
Newly selected followup resources also receive the larger bounded window: the
first read is orientation, while this step is focused reading. This does not
prove completeness or grant a further step after the result.
Choose the read that could establish the proposed explanation's actual scope;
successful retrieval or repeated introductory wording is not enough by itself.
You may still stop when a useful bounded claim is already supported. Do not
request more reading merely to fill a report or force a critique.
Return search_query, read_targets, deepen_source_ref and reason. At most ONE
action may be nonempty. For example:
{"search_query":null,"read_targets":[],"deepen_source_ref":"source1","reason":"read the qualification to the central claim"}.
The returned window may remain incomplete. Facts outside it stay unknown.
'''

PUBLIC_COPY_GUIDANCE = '''
If the available direct link may be a landing page or incomplete extract, you
may search once for accessible substantive evidence, such as the author copy
of a named work or the technical record behind a release. In that case you
may also reserve ONE existing cited resource in read_targets as an anchor.
This is the only exception to the one-nonempty-action rule above.
The host can then read that anchor and at most one distinct result. You still
have at most one new query and two reads in this entire follow-up. A search
without an anchor still allows at most two result reads. When a cited page
already provides the relevant substantive material, a search is unnecessary.
Never assume a DOI, abstract label or publisher name means the result contains
the part needed. Use the exact public title or identifier if it is supplied.
'''

LISTING_OPTIONS_GUIDANCE = '''
unread_search_listings contains other eligible results from the original public
search. They are listings, not pages you have read. If an initial page was too
thin, inaccessible or off topic, choose up to two distinct listing references
in listing_source_refs to read those pages instead. Compare their likely
evidence against a deeper read or cited link, not only the publisher's name.
This uses the same follow-up allowance. Do not combine listing_source_refs
with a query, citations, or deepen_source_ref. Leave it empty when choosing
another action. Never reconstruct the missing page from a listing's preview.
'''

SEPARATED_SCOPE_GUIDANCE = '''
Only sources contains what the initial page reads actually returned.
initial_search_listings contains search snippets for those attempted pages,
including attempts that returned no extract. A snippet can identify a candidate
or contain a link worth reading, but cannot fill a gap in the page extract.
Before stopping, identify the relevant passage actually present in sources.
Headings, clipping markers, an unrelated index, and missing article text do not
establish the proposed substantive claim. If a material passage is missing,
choose a bounded follow-up likely to supply it, or stop with that gap explicit.
'''


def normalize_with_listings(raw, catalogs, already_queried, eligible, listings, *, allow_query_with_citation=False):
    from . import public_source_refinement as legacy
    options = raw.get('listing_source_refs', []) if isinstance(raw, dict) else []
    if options == []:
        return {**normalize(raw, catalogs, already_queried, eligible,
                            allow_query_with_citation=allow_query_with_citation), 'listing_source_refs': []}
    rejected = {**legacy._invalid(), 'deepen_source_ref': None, 'listing_source_refs': []}
    if (not isinstance(options, list) or not 1 <= len(options) <= 2
            or any(not isinstance(ref, str) or ref not in listings for ref in options)
            or len(set(options)) != len(options)
            or len({listings[ref] for ref in options}) != len(options)
            or raw.get('search_query') is not None or raw.get('read_targets', []) != []
            or raw.get('deepen_source_ref') is not None):
        return rejected
    reason = raw.get('reason')
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 1200:
        return rejected
    return dict(search_query=None, read_targets=[], deepen_source_ref=None, listing_source_refs=options,
                reason=reason, rejected_count=0, decision_status='unread_listings_selected')


def validate_with_listings(value, catalogs, already_queried, eligible, listings, *, allow_query_with_citation=False):
    from .host_discovery import HostDiscoveryError
    if not isinstance(value, dict) or 'listing_source_refs' not in value:
        raise HostDiscoveryError('invalid retained unread-listing decision')
    if value['listing_source_refs'] != []:
        if normalize_with_listings(value, catalogs, already_queried, eligible, listings) != value:
            raise HostDiscoveryError('retained unread-listing choice changed or lost its source')
    else:
        validate({key: item for key, item in value.items() if key != 'listing_source_refs'},
                 catalogs, already_queried, eligible, allow_query_with_citation=allow_query_with_citation)
    return value


def eligible_sources(evidence, read_scope):
    return {e.observation_event_id:e.content['url'] for e in evidence
            if read_scope(e.content).get('reported_read_scope')=='webpage_extract'}


def normalize(raw, catalogs, already_queried, eligible, *, allow_query_with_citation=False):
    from . import public_source_refinement as legacy
    if not isinstance(raw,dict):
        return {**legacy._invalid(),'deepen_source_ref':None}
    target=raw.get('deepen_source_ref')
    if target is None:
        if allow_query_with_citation and raw.get('search_query') is not None and raw.get('read_targets'):
            query=legacy.normalize({**raw,'read_targets':[]},catalogs,already_queried)
            citation=legacy.normalize({**raw,'search_query':None},catalogs,already_queried)
            if (query['search_query'] is None or citation['rejected_count']
                    or len(citation['read_targets'])!=1):
                return {**legacy._invalid(),'deepen_source_ref':None}
            return {**query,'read_targets':citation['read_targets'],'deepen_source_ref':None}
        return {**legacy.normalize(raw,catalogs,already_queried),'deepen_source_ref':None}
    reason=raw.get('reason')
    if (not isinstance(target,str) or target not in eligible
            or raw.get('search_query') is not None or raw.get('read_targets',[])!=[]
            or not isinstance(reason,str) or not 1<=len(reason.strip())<=1200):
        return {**legacy._invalid(),'deepen_source_ref':None}
    return dict(search_query=None,read_targets=[],deepen_source_ref=target,
                reason=reason,rejected_count=0,decision_status='deeper_read_selected')


def validate(value,catalogs,already_queried,eligible,*,allow_query_with_citation=False):
    from .host_discovery import HostDiscoveryError
    if (not isinstance(value,dict) or set(value)!={
            'search_query','read_targets','deepen_source_ref','reason','rejected_count','decision_status'}):
        raise HostDiscoveryError('invalid retained reading-depth decision')
    if value.get('deepen_source_ref') is not None:
        if normalize(value,catalogs,already_queried,eligible)!=value:
            raise HostDiscoveryError('retained deeper read changed or lost its source')
    elif allow_query_with_citation and value['search_query'] is not None and value['read_targets']:
        if normalize(value,catalogs,already_queried,eligible,allow_query_with_citation=True)!=value:
            raise HostDiscoveryError('retained public copy search lost its cited anchor')
    else:
        from . import public_source_refinement as legacy
        legacy.validate({k:v for k,v in value.items() if k!='deepen_source_ref'},catalogs,already_queried)
    return value
