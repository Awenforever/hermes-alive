"""Host-read boundary with synthetic capabilities, no network/model/sender."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))

async def exercise(root):
    from alive_kernel import ExperienceJournal, DiscoveryOpportunityIngestor, DiscoveryCandidate, Sensitivity
    from alive_kernel.host_discovery import HostDiscoveryReader, HostDiscoveryError, HostReadUncertainError, read_scope_metadata
    journal=ExperienceJournal(root/'experience.sqlite3')
    ingestor=DiscoveryOpportunityIngestor(journal)
    general=ingestor.ingest(DiscoveryCandidate(source='synthetic-general',title='Outside current interests',
        url='https://example.invalid/general',summary='A separate general observation.'),subject='user:test')
    calls=[]; current=[True]; body=['PRIVATE_PAGE_FACT']
    async def allowed(url): return url.startswith('https://example.invalid/')
    async def search(query,*,limit):
        calls.append(('search',query))
        if query=='exception': raise RuntimeError('PRIVATE_PROVIDER_SECRET')
        if query=='failure': return json.dumps(dict(success=False,data=dict(web=[])))
        if query=='empty': return json.dumps(dict(success=True,data=dict(web=[])))
        if query=='revoked': current[0]=False
        items=[dict(title='PRIVATE_TITLE',url='https://example.invalid/one',description='PRIVATE_SNIPPET',
                    future_optional_field=True),
               dict(title='unsafe',url='http://127.0.0.1/private',description='not admitted')]
        return json.dumps(dict(success=True,data=dict(web=items)))
    async def extract(urls,*,char_limit):
        calls.append(('extract',urls[0]))
        if urls[0].endswith('/empty'): return json.dumps(dict(results=[]))
        return json.dumps(dict(results=[dict(title='PRIVATE_TITLE',url=urls[0],content=body[0],error=None)]))
    def reader(owner='user:test'):
        return HostDiscoveryReader(ingestor,subject=owner,search=search,extract=extract,
            allow_url=allowed,is_current=lambda:current[0])
    async def uncertain_search(*args,**kwargs):
        raise HostReadUncertainError('physical worker still reading')
    uncertain=HostDiscoveryReader(ingestor,subject='user:test',search=uncertain_search,
        extract=extract,allow_url=allowed,is_current=lambda:True)
    done_before=len(journal.read(event_type='discovery.host_read_completed'))
    try:await uncertain.collect(operation_id='uncertain-physical-read',queries=('PUBLIC_QUERY',))
    except HostReadUncertainError:pass
    else:raise AssertionError('physical uncertainty treated as settled failure')
    assert len(journal.read(event_type='discovery.host_read_completed'))==done_before
    try:await uncertain.collect(operation_id='uncertain-physical-read',queries=('PUBLIC_QUERY',))
    except HostDiscoveryError:pass
    else:raise AssertionError('uncertain physical read replayed')
    host=reader()
    parameters=dict(queries=('PRIVATE_QUERY',),read_urls=('https://example.invalid/one',))
    result=await host.collect(operation_id='first',**parameters)
    assert len(result.observation_ids)==2 and result.failures==1
    assert await host.collect(operation_id='first',**parameters)==result
    assert len(calls)==2
    evidence=ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,limit=32)
    assert general.observation_event_id in {e.observation_event_id for e in evidence}
    web=[e for e in evidence if e.content['source'].startswith('hermes.web.')]
    assert {e.content['attributes']['read_scope'] for e in web}=={'webpage_extract','search_listing'}
    assert all(e.content['published_at'] is None and not e.content['attributes']['video_watched'] for e in web)
    assert {read_scope_metadata(e.content)['reported_read_scope'] for e in web}=={'webpage_extract','search_listing'}
    assert read_scope_metadata(dict(source='legacy',attributes=dict(read_scope='webpage_extract')))=={}
    asserted=read_scope_metadata(dict(source='hermes.web.extract',attributes=dict(read_scope='webpage_extract',
        independently_verified=True,video_watched=True)))
    assert not asserted['independent_verification_proven'] and not asserted['video_consumption_proven']
    later=await host.collect(operation_id='same-content-new-time',**parameters)
    assert set(later.observation_ids)==set(result.observation_ids)
    assert len(journal.read(event_type='discovery.opportunity_observed'))==3
    body[0]='PRIVATE_PAGE_MATERIAL_CHANGE'
    changed=await host.collect(operation_id='changed',**parameters)
    assert set(changed.observation_ids)!=set(result.observation_ids)
    assert len(journal.read(event_type='discovery.opportunity_observed'))==4
    count=len(calls)
    try: await host.collect(operation_id='first',**parameters)
    except ValueError: pass
    else: raise AssertionError('superseded evidence replayed as current')
    assert len(calls)==count
    # Current sources are owner-scoped; another owner's identical read is separate.
    other=await reader('user:other').collect(operation_id='first',**parameters)
    assert not set(other.observation_ids)&set(changed.observation_ids)
    empty=await host.collect(operation_id='empty',queries=('empty',))
    assert empty.failures==0 and not empty.observation_ids
    assert empty.read_outcomes==(('search',0,'empty'),)
    failed=await host.collect(operation_id='failure',queries=('failure',))
    assert failed.failures==1 and not failed.observation_ids
    assert failed.read_outcomes==(('search',0,'read_failed'),)
    exception=await host.collect(operation_id='exception',queries=('exception',))
    assert exception.failures==1 and not exception.observation_ids
    missing=await host.collect(operation_id='missing-extract',read_urls=('https://example.invalid/empty',))
    assert missing.failures==1 and not missing.observation_ids
    count=len(calls)
    blocked=await host.collect(operation_id='blocked',read_urls=('http://127.0.0.1/private',))
    assert blocked.failures==1 and len(calls)==count
    for raw in ('{"success":true,"success":false}', '{"value":NaN}', '['*70+'0'+']'*70):
        try: host._document(raw)
        except ValueError: pass
        else: raise AssertionError('ambiguous/nonfinite/deep host JSON admitted')
    try: await host.collect(operation_id='first',queries=('different',))
    except HostDiscoveryError: pass
    else: raise AssertionError('operation reused with different query')
    revoked=reader()
    try: await revoked.collect(operation_id='revoked',queries=('revoked',))
    except HostDiscoveryError: pass
    else: raise AssertionError('revoked read admitted observations')
    current[0]=True
    count=len(calls)
    try: await reader().collect(operation_id='revoked',queries=('revoked',))
    except HostDiscoveryError: pass
    else: raise AssertionError('uncertain operation blindly restarted')
    assert len(calls)==count
    started=asyncio.Event()
    async def held(*args,**kwargs):
        started.set(); await asyncio.sleep(10)
    cancelling=HostDiscoveryReader(ingestor,subject='user:test',search=held,extract=extract,
        allow_url=allowed,is_current=lambda:True)
    task=asyncio.create_task(cancelling.collect(operation_id='cancelled',queries=('public',)))
    await started.wait()
    try: await cancelling.collect(operation_id='concurrent',queries=('public',))
    except HostDiscoveryError: pass
    else: raise AssertionError('concurrent owned read admitted')
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass
    else: raise AssertionError('cancellation swallowed')
    try: await cancelling.collect(operation_id='not-a-retry',queries=('public',))
    except HostDiscoveryError: pass
    else: raise AssertionError('uncertain reader reused')
    broken=reader()
    with patch.object(ingestor,'ingest',side_effect=OSError('PRIVATE_STORAGE_FAILURE')):
        try: await broken.collect(operation_id='broken-storage',queries=('public',))
        except OSError: pass
        else: raise AssertionError('storage failure disguised as source failure')
    try: await broken.collect(operation_id='after-storage-failure',queries=('public',))
    except HostDiscoveryError: pass
    else: raise AssertionError('uncertain storage operation reused')
    for event in ('action.attempted','dispatch.externally_started','preference.observed'):
        assert not journal.read(event_type=event)
    # Identity equivalence is not fetch authority. A tool must still return the
    # exact requested URL, even when the two spellings canonicalize identically.
    transport_url='https://EXAMPLE.invalid:443/Original?utm_source=fixture#section'
    normalized_url='https://example.invalid/Original'
    async def substituted_extract(urls,*,char_limit):
        assert urls==[transport_url]
        return json.dumps(dict(results=[dict(title='Synthetic source',url=normalized_url,
            content='A substituted response must not be admitted.')]))
    exact_host=HostDiscoveryReader(ingestor,subject='user:test',search=search,
        extract=substituted_extract,allow_url=allow_synthetic_url,is_current=lambda:True)
    substituted=await exact_host.collect(operation_id='substituted-transport',read_urls=(transport_url,))
    assert substituted.failures==1 and not substituted.observation_ids
    # Representation is capture metadata, not extra editorial prose inserted
    # into the source. Unknown future fields do not invalidate usable content.
    async def represented_extract(urls,*,char_limit):
        return json.dumps({'results':[{'title':'Synthetic summary','url':urls[0],
            'content':'Only supplied source content.','content_representation':'operator_paraphrase'}]})
    represented=HostDiscoveryReader(ingestor,subject='user:test',search=search,
        extract=represented_extract,allow_url=allow_synthetic_url,is_current=lambda:True)
    captured=await represented.collect(operation_id='represented',read_urls=('https://example.invalid/summary',))
    material=ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
        observation_event_ids=captured.observation_ids,limit=32)[0]
    assert material.content['summary']=='Only supplied source content.'
    scope=read_scope_metadata(material.content)
    assert scope['reported_content_representation']=='operator_paraphrase'
    assert scope['independent_verification_proven'] is False
    assert read_scope_metadata({'source':'hermes.web.extract','attributes':{
        'read_scope':'webpage_extract','content_representation':'future-provider-format'}})[
            'reported_content_representation']=='unspecified'
    # Search snippets are query-dependent views. A second query must not revoke
    # the first query's reading task merely because it describes the same URL
    # differently. Actual changes within the SAME query still supersede it.
    views={'PUBLIC_VIEW_A':'First query view.','PUBLIC_VIEW_B':'Different query view.'}
    view_calls=[]
    async def view_search(query,*,limit):
        view_calls.append(query)
        return json.dumps({'success':True,'data':{'web':[{'url':'https://example.invalid/views',
            'title':'One original article','description':views[query]},
            {'url':'https://example.invalid/views?utm_source=duplicate','title':'Duplicate result',
             'description':'A second snippet in the same result batch is not another page revision.'}]}})
    scoped=HostDiscoveryReader(ingestor,subject='user:test',search=view_search,extract=extract,
        allow_url=allow_synthetic_url,is_current=lambda:True,scope_search_views=True)
    first=await scoped.collect(operation_id='view-a',queries=('PUBLIC_VIEW_A',))
    second=await scoped.collect(operation_id='view-b',queries=('PUBLIC_VIEW_B',))
    assert len(first.observation_ids)==len(second.observation_ids)==1
    both=(*first.observation_ids,*second.observation_ids)
    assert len(ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
        observation_event_ids=both,limit=32))==2
    assert await scoped.collect(operation_id='view-a',queries=('PUBLIC_VIEW_A',))==first
    assert len(view_calls)==2
    views['PUBLIC_VIEW_A']='A material update within the first query view.'
    changed=await scoped.collect(operation_id='view-a-updated',queries=('PUBLIC_VIEW_A',))
    assert changed.observation_ids!=first.observation_ids
    assert not ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
        observation_event_ids=first.observation_ids,limit=32)
    assert ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
        observation_event_ids=second.observation_ids,limit=32)
    before=len(view_calls)
    try:await scoped.collect(operation_id='view-a',queries=('PUBLIC_VIEW_A',))
    except HostDiscoveryError:pass
    else:raise AssertionError('real material change was ignored on scoped replay')
    assert len(view_calls)==before
    retained=journal.get(second.observation_ids[0]).event.payload['content']
    ingestor.vault.erase_item(retained['content_id'])
    assert not ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
        observation_event_ids=second.observation_ids,limit=32)
    try:await scoped.collect(operation_id='view-b',queries=('PUBLIC_VIEW_B',))
    except HostDiscoveryError:pass
    else:raise AssertionError('query-scoped evidence bypassed erasure')
    try:await scoped.collect(operation_id='first',**parameters)
    except HostDiscoveryError:pass
    else:raise AssertionError('a started legacy receipt was reinterpreted under new identity semantics')
    for path in root.glob('experience.sqlite3*'):
        data=path.read_bytes()
        assert b'PRIVATE_QUERY' not in data and b'PRIVATE_PAGE_FACT' not in data
        assert b'PRIVATE_PROVIDER_SECRET' not in data and b'PRIVATE_STORAGE_FAILURE' not in data

async def allow_synthetic_url(url):
    return True  # Synthetic capability; the test above targets exact response binding.

with tempfile.TemporaryDirectory(prefix='alive-host-discovery-') as folder:
    previous={key:os.environ.get(key) for key in ('HERMES_HOME','HERMES_ALIVE_SHARED_DIR')}
    os.environ['HERMES_HOME']=str(Path(folder)/'profile')
    os.environ['HERMES_ALIVE_SHARED_DIR']=str(Path(folder)/'runtime')
    try: asyncio.run(exercise(Path(folder)))
    finally:
        for key,value in previous.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
print('HERMES_ALIVE_HOST_DISCOVERY_OK')
