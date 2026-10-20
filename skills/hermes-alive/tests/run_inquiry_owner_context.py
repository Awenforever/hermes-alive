"""Derived reading rationale must not revive a forgotten owner preference."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ExperienceJournal, DiscoveryOpportunityIngestor, DiscoveryCandidate,
    MemoryProjection, MemoryProposal, MemoryKind, MemoryAuthority, EventEnvelope, Sensitivity,
    OpportunitySynthesizer)
from alive_kernel.discovery_inquiry import DiscoveryInquiryContext, DiscoveryInquiryError
from alive_kernel.content_vault import ContentVault
from alive_kernel.agenda import AgendaProposal, AgendaAuthority, AgendaItemKind
from alive_kernel.host_discovery import HostDiscoveryReader


async def exercise(root, custom=False):
    journal = ExperienceJournal(root/'journal.sqlite3')
    ingestor = DiscoveryOpportunityIngestor(journal)
    context_vault = ContentVault(root/'custom-memory',backup_root=root/'memory-backups') if custom else None
    memory = MemoryProjection(journal,content_vault=context_vault)
    inbound = journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
        actor='user:test',subject='user:test',payload={'synthetic':True}))
    pref = MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.interest',
        value='PRIVATE_OWNER_PREFERENCE',authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event.event_id,),confidence=1)
    memory.apply(memory.append_proposal(pref,actor='user:test'))
    source = ingestor.ingest(DiscoveryCandidate(source='synthetic',title='Public source',
        url='https://example.invalid/source',summary='A public observation.'),subject='user:test')
    inquiry = DiscoveryInquiryContext(ingestor,context_vault=context_vault)
    args = dict(item_id='inquiry:derived',subject='user:test',question='What does this method change?',
        value_hypothesis='PRIVATE_OWNER_PREFERENCE makes this potentially interesting, not a user instruction.',
        model_actor='model:synthetic',source_event_ids=(source.observation_event_id,),
        expected_context_digest=inquiry.context_digest(subject='user:test'),
        expires_at=datetime.now(timezone.utc)+timedelta(hours=1))
    inquiry.remember(**args)
    tool_calls=[]
    async def search(*a,**kw): raise AssertionError('no search granted')
    async def allow(url): return url=='https://example.invalid/source'
    async def extract(urls,**kw):
        tool_calls.append(urls)
        return json.dumps({'results':[{'url':urls[0],'title':'Public source','content':'A public page excerpt.'}]})
    host = HostDiscoveryReader(ingestor,subject='user:test',search=search,extract=extract,
        allow_url=allow,is_current=lambda:True,context_vault=context_vault)
    await host.collect(operation_id='read-before-forget',read_urls=('https://example.invalid/source',),
                       inquiry_item_ids=('inquiry:derived',))
    # Other owners' memory changes do not revoke this owner's reading task.
    other_source = journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
        actor='user:other',subject='user:other',payload={'synthetic':True}))
    other = MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:other',predicate='profile.interest',
        value='OTHER_PRIVATE',authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(other_source.event.event_id,),confidence=1)
    memory.apply(memory.append_proposal(other,actor='user:other'))
    memory.forget_item(other.proposal_id,actor='user:other',request_id='forget-other')
    assert inquiry.read(subject='user:test',clearance=Sensitivity.PRIVATE,item_ids=('inquiry:derived',))
    legacy = AgendaProposal(item_id='inquiry:unbound-prototype',subject='user:test',
        kind=AgendaItemKind.OPPORTUNITY,authority=AgendaAuthority.MODEL_PROPOSAL,
        details=dict(context_kind='discovery-inquiry-v1',question='Old question',value_hypothesis='Old derived reason'),
        source_event_ids=(source.observation_event_id,),confidence=.5,expires_at=args['expires_at'])
    ingestor.agenda.apply(ingestor.agenda.append_proposal(legacy,actor='model:synthetic'))
    try: inquiry.read(subject='user:test',clearance=Sensitivity.PRIVATE,item_ids=(legacy.item_id,))
    except DiscoveryInquiryError: pass
    else: raise AssertionError('unbound prototype task silently reattached to current owner memory')
    memory.forget_item(pref.proposal_id,actor='user:test',request_id='forget-owner-pref')
    try: inquiry.remember(**{**args,'item_id':'inquiry:stale-choice'})
    except DiscoveryInquiryError: pass
    else: raise AssertionError('reading choice bound to context captured only after owner forget')
    assert journal.get('agenda.proposal:inquiry:stale-choice') is None
    try: inquiry.read(subject='user:test',clearance=Sensitivity.PRIVATE,item_ids=('inquiry:derived',))
    except DiscoveryInquiryError: pass
    else: raise AssertionError('forgotten owner preference remains reusable inside a derived reading rationale')
    calls=[]
    async def forbidden(**kw):
        calls.append(kw)
        return SimpleNamespace(model='synthetic',choices=[SimpleNamespace(message=SimpleNamespace(content='{"candidates":[]}'))])
    try:
        await OpportunitySynthesizer(journal,content_vault=ingestor.vault,context_vault=context_vault).run(subject='user:test',
            operation_id='new-after-forget',call=forbidden,inquiry_item_ids=('inquiry:derived',))
    except DiscoveryInquiryError: pass
    else: raise AssertionError('new interpretation reused a forgotten derived rationale')
    assert not calls
    try:
        await host.collect(operation_id='read-after-forget',read_urls=('https://example.invalid/source',),
                           inquiry_item_ids=('inquiry:derived',))
    except DiscoveryInquiryError: pass
    else: raise AssertionError('forgotten derived task initiated a new host read')
    assert len(tool_calls)==1
    new_source = journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
        actor='user:test',subject='user:test',payload={'synthetic':True}))
    repeated = MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.interest',
        value='PRIVATE_OWNER_PREFERENCE',authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(new_source.event.event_id,),confidence=1)
    memory.apply(memory.append_proposal(repeated,actor='user:test'))
    try: inquiry.read(subject='user:test',clearance=Sensitivity.PRIVATE,item_ids=('inquiry:derived',))
    except DiscoveryInquiryError: pass
    else: raise AssertionError('identical newly supplied words resurrected an old derived task')


with tempfile.TemporaryDirectory(prefix='alive-inquiry-owner-') as directory:
    for custom in (False,True):
        root = Path(directory)/str(custom); root.mkdir()
        asyncio.run(exercise(root,custom))
print('HERMES_ALIVE_INQUIRY_OWNER_CONTEXT_OK')
