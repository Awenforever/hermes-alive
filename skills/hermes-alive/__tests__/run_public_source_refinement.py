"""Real kernel/read capabilities and durable receipts; synthetic public IO/models.

Not real web retrieval, model quality, native installation or physical delivery.
"""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ExperienceJournal, DiscoveryOpportunityIngestor, EventEnvelope,
    MemoryProjection, MemoryProposal, MemoryKind, MemoryAuthority, Sensitivity)
from alive_kernel.configured_discovery_cycle import ConfiguredDiscoveryCycle
from alive_kernel.core_discovery_tools import CoreDiscoveryTools
from alive_kernel.host_discovery import HostDiscoveryError, HostDiscoveryReader
from alive_kernel.kernel_setup import validate_options, KernelSetupError
from alive_kernel.research_evidence import resolve_research_reads
from alive_kernel import public_source_refinement as selection


def contracts():
    good=selection.normalize({'search_query':' public original project ','read_targets':[],
        'reason':'Find the original.','future_non_action_metadata':True},{})
    assert good['search_query']=='public original project'
    assert selection.validate(good,{})==good
    for raw in (None,{'future_non_action_metadata':True},{'search_query':'x'*129},{'search_query':'bad\nquery'},
                {'search_query':True},{'search_query':'public original project','read_targets':[{}]},
                {'search_query':'already public'}):
        value=selection.normalize(raw,{},('already public',))
        assert value['search_query'] is None and not value['read_targets']
        assert value['decision_status']=='invalid'
        selection.validate(value,{},('already public',))
    for changed in ({**good,'search_query':'already public'}, {**good,'rejected_count':1},
                    {**good,'search_query':None}):
        try:selection.validate(changed,{},('already public',))
        except HostDiscoveryError:pass
        else:raise AssertionError('retained query could broaden or change its action')
    options=dict(model_calls=True,delivery=True,outbound_retention_days=30,
        outbound_retention_confirmed=True,model=None,public_queries=['public seed'],cited_reads=False)
    assert 'refine_public_sources' not in validate_options(options)
    for extra in (dict(refine_public_sources=True),dict(refine_public_sources=1,cited_reads=True)):
        try:validate_options({**options,**extra})
        except KernelSetupError:pass
        else:raise AssertionError('additional public scope lacked explicit valid consent')
    assert validate_options({**options,'cited_reads':True,'refine_public_sources':True})['refine_public_sources']


async def exercise(root,mode):
    root.mkdir()
    journal=ExperienceJournal(root/'journal.sqlite3')
    ingestor=DiscoveryOpportunityIngestor(journal)
    memory=MemoryProjection(journal)
    inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
        actor='user:test',subject='user:test',payload={'synthetic':True}))
    preference=MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.interest',
        value='PRIVATE_OWNER_PREFERENCE',authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event.event_id,),confidence=1)
    memory.apply(memory.append_proposal(preference,actor='user:test'))
    state={'consent':True};network=[];models=[];unload=[]
    release=threading.Event();entered=threading.Event()
    seed='https://example.invalid/aggregator'
    original='https://example.invalid/original'
    def dispatch(name,args):
        network.append((name,dict(args)))
        assert 'PRIVATE_' not in json.dumps(args)
        if name=='web_search':
            assert args['query'] in ('public seed','public original project')
            if args['query']=='public original project' and mode=='uncertain-search':
                entered.set();assert release.wait(10),'fixture did not release public query worker'
            if args['query']=='public original project' and mode=='search-failed':
                return {'success':False,'error':'synthetic public search unavailable'}
            if args['query']=='public original project' and mode in ('overlap','only-overlap'):
                items=[dict(url=seed,title='Public method',description='A different query gives another excerpt of the SAME source.')]
                if mode=='overlap':
                    items.append(dict(url=seed+'?utm_source=duplicate',title='Duplicate result',description='Another snippet in the SAME result batch.'))
                    items.append(dict(url=original,title='Original method',description='Original supporting evidence.'))
                return {'success':True,'data':{'web':items}}
            url=seed if args['query']=='public seed' else original
            return {'success':True,'data':{'web':[dict(url=url,title='Public method',
                description='A public account names a method whose original evidence is worth reading.')]}}
        assert name=='web_extract' and args['urls'] in ([seed],[original])
        url=args['urls'][0]
        if url==original and mode=='refined-page-failed':return {'results':[dict(url=url,error='unavailable')]}
        if url==seed and mode not in ('cited','overlap','only-overlap'):
            return {'results':[dict(url=url,error='unavailable')]}
        content=('PUBLIC_PRIMARY_BODY: The method compares two observation conditions.' if url==original else
                 'Public material. [Original]('+original+')')
        return {'results':[dict(url=url,title='Public observations',content=content)]}
    context=NS(_manager=NS(scope_key=str(root)),on_unload=unload.append,dispatch_tool=dispatch)
    def consent():
        if not state['consent']:raise HostDiscoveryError('synthetic consent withdrawn')
    def make(enabled):
        return ConfiguredDiscoveryCycle(context,ingestor,subject='user:test',approved_queries=('public seed',),
            validate_consent=consent,follow_citations=True,refine_public_sources=enabled,
            record_reading_assessment=True)
    preparation=make(mode not in ('off','old-cycle'))
    cycle=NS(operation_id='synthetic-source-refinement')
    parameters={'expression_parameters':{'model_timeout_seconds':30}}
    binding=lambda:'synthetic-current-owner'
    if mode=='legacy-search':
        legacy_tools=CoreDiscoveryTools(context,read_binding=binding,approved_queries=('public seed',))
        legacy=HostDiscoveryReader(ingestor,subject='user:test',search=legacy_tools.search,
            extract=legacy_tools.extract,allow_url=legacy_tools.allow_url,is_current=lambda:True)
        await legacy.collect(operation_id=cycle.operation_id+':search',queries=('public seed',))
        legacy_tools.close()
    observed=await preparation.observe(cycle=cycle,parameters=parameters,read_binding=binding)
    assert observed.reader.scope_search_views is (mode!='legacy-search')
    if mode=='old-cycle':
        preparation.close();preparation=make(True)
        observed=await preparation.observe(cycle=cycle,parameters=parameters,read_binding=binding)
        assert not observed.public_refinement
    async def call(**kw):
        data=json.loads(kw['messages'][1]['content']);models.append(kw['task'])
        if data['method']==selection.METHOD:
            assert 'PRIVATE_OWNER_PREFERENCE' not in json.dumps(kw['messages'])
            assert 'PRIVATE_INQUIRY' not in json.dumps(kw['messages'])
            assert 'user_context' not in data and 'owner_context_digest' not in data
            assert data['already_queried']==['public seed']
            assert data['collection_as_of'] and data['collection_clock_is_not_publication_date'] is True
            if mode=='cited':
                source=next(s for s in data['sources'] if s.get('citations'))
                value=dict(search_query=None,read_targets=[dict(source_ref=source['source_ref'],
                    citation_ref=source['citations'][0]['citation_ref'])],reason='Read the original link.')
            elif mode=='malformed':value={'unknown_action':'no authorized network action'}
            else:
                value=dict(search_query='public original project',read_targets=[],reason='Find the original evidence.')
                if mode=='revoked':state['consent']=False
                if mode=='erased':
                    source=journal.get(data['sources'][0]['source_ref'])
                    ingestor.vault.erase_item(source.event.payload['content']['content_id'])
        else:
            assert kw['task']=='alive_discovery_reading'
            if data['method']=='public-source-read-choice-v1':
                assert 'PRIVATE_' not in json.dumps(kw['messages']) and 'user_context' not in data
            else:assert 'PRIVATE_OWNER_PREFERENCE' in json.dumps(data)
            value=dict(source_refs=[data['sources'][0]['source_ref']],
                question='PRIVATE_INQUIRY: internal tentative task, not a public search input.',
                value_hypothesis='A tentative useful comparison.')
        return NS(model='synthetic/model',choices=[NS(message=NS(content=json.dumps(value)))])
    task=asyncio.create_task(preparation.reason(observed,cycle=cycle,parameters=parameters,call=call,read_binding=binding))
    if mode=='uncertain-search':
        for _ in range(2000):
            if entered.is_set() or task.done():break
            await asyncio.sleep(.005)
        assert entered.is_set()
        task.cancel()
    try:
        result=await task
    except asyncio.CancelledError:
        replacement=make(True)
        try:
            assert mode=='uncertain-search' and entered.is_set() and preparation.pending
            assert len(network)==3 and len(models)==2
            blocked=await replacement.observe(cycle=NS(operation_id='replacement'),parameters=parameters,read_binding=binding)
            assert blocked.found.failures and not blocked.found.observation_ids
            assert blocked.listing_fingerprint is None
        finally:release.set()
        assert len(network)==3
        assert (await preparation.reap_pending(timeout_seconds=2))['remaining']==0
        assert all(e.content['url']==seed for e in ingestor.active_evidence(
            subject='user:test',clearance=Sensitivity.PRIVATE,limit=32))
        preparation.close();replacement.close()
        return
    except HostDiscoveryError:
        assert mode in ('revoked','erased')
        assert len(network)==2 and len(models)==2
        assert not preparation.pending
        return
    assert mode not in ('revoked','erased')
    if mode in ('off','old-cycle','legacy-search'):
        assert len(network)==2 and len(models)==1
    elif mode=='malformed':
        assert len(network)==2 and len(models)==2
    elif mode=='cited':
        assert len(network)==3 and len(models)==2
        assert len(result['expression_parameters']['research_read_receipt_ids'])==2
    elif mode=='search-failed':
        assert len(network)==3 and len(models)==2
        assert not result['expression_parameters'].get('research_read_receipt_ids')
    elif mode=='refined-page-failed':
        assert len(network)==4 and len(models)==3
        assert not result['expression_parameters'].get('research_read_receipt_ids')
    elif mode=='only-overlap':
        assert len(network)==3 and len(models)==2
        assert len(result['expression_parameters']['research_read_receipt_ids'])==1
        assert tuple(ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
            observation_event_ids=observed.found.observation_ids,limit=32))==observed.evidence
        before=list(network)
        async def forbidden(**kw):raise AssertionError('overlapping-result replay repeated inference')
        assert await preparation.reason(observed,cycle=cycle,parameters=parameters,call=forbidden,read_binding=binding)==result
        assert network==before
    else:
        assert len(network)==4 and len(models)==3
        assert len(result['expression_parameters']['research_read_receipt_ids'])==(2 if mode=='overlap' else 1)
        assert any('PUBLIC_PRIMARY_BODY' in e.content['summary'] for e in ingestor.active_evidence(
            subject='user:test',clearance=Sensitivity.PRIVATE,limit=32))
        before=list(network)
        async def forbidden(**kw):raise AssertionError('replay repeated model inference')
        repeated=await preparation.reason(observed,cycle=cycle,parameters=parameters,call=forbidden,read_binding=binding)
        assert repeated==result and network==before
    receipts=result['expression_parameters'].get('research_read_receipt_ids',())
    if receipts:
        inquiries=preparation.inquiries.read(subject='user:test',clearance=Sensitivity.PRIVATE,
            item_ids=result['expression_parameters']['inquiry_item_ids'])
        material=resolve_research_reads(ingestor,subject='user:test',clearance=Sensitivity.PRIVATE,
            receipt_ids=receipts,inquiries=inquiries)
        assert len(material)==len(receipts)
    if mode in ('overlap','only-overlap'):
        before=list(network)
        preparation.close()
        preparation=make(True)
        restored=await preparation.observe(cycle=cycle,parameters=parameters,read_binding=binding)
        async def forbidden_cold(**kw):raise AssertionError('cold research recovery repeated inference')
        assert await preparation.reason(restored,cycle=cycle,parameters=parameters,
            call=forbidden_cold,read_binding=binding)==result
        assert network==before,'cold research recovery replenished query/read budget'
    try:await preparation.tools.search('public original project',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('additional query grant survived its single canonical search')
    async def forbidden_private(**kw):raise AssertionError('private material reached query planning')
    before_private=(len(network),len(models))
    try:
        await preparation._select(operation_id='private-not-public',
            evidence=(NS(content=dict(source='private-memory',summary='PRIVATE_NOT_PUBLIC')),),
            search_receipt_id='not-public',parameters=parameters,call=forbidden_private,current=lambda:None,
            followup=True,citation_references=True,source_refinement=True)
    except HostDiscoveryError:pass
    else:raise AssertionError('private memory admitted as public source material')
    assert (len(network),len(models))==before_private
    preparation.close()


async def allow_synthetic_url(self,url):
    self._current()
    return url.startswith('https://example.invalid/')


contracts()
with tempfile.TemporaryDirectory(prefix='alive-public-refinement-') as folder:
    parent=Path(folder)
    for mode in ('off','old-cycle','legacy-search','on','overlap','only-overlap','cited','malformed','revoked','erased','search-failed','refined-page-failed','uncertain-search'):
        home=parent/mode
        with patch.dict(sys.modules,hermes_constants=NS(get_hermes_home=lambda:home)):
            with patch.object(CoreDiscoveryTools,'allow_url',allow_synthetic_url):
                asyncio.run(exercise(home,mode))
        print('public_refinement_case='+mode+':PASS',flush=True)
print('HERMES_ALIVE_PUBLIC_SOURCE_REFINEMENT_OK')
