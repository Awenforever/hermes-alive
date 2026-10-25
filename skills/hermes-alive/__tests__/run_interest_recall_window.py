"""Actual fair source admission before model interest judgment; no real model/send."""
import asyncio
from dataclasses import replace
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ExperienceJournal,DiscoveryOpportunityIngestor,DiscoveryCandidate,
    OpportunitySynthesizer,OpportunitySynthesisError,MemoryProjection,MemoryProposal,
    MemoryKind,MemoryAuthority,EventEnvelope,Sensitivity)
from alive_kernel.source_support import SourceSupportReviewer


def response(document):
    return SimpleNamespace(model='synthetic/interest-judgment',choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(document)))])


def seed(root,count,*,long=False):
    journal=ExperienceJournal(root/'experience.sqlite3')
    reader=DiscoveryOpportunityIngestor(journal)
    reader.ingest(DiscoveryCandidate(source='synthetic',title='FOREIGN_PRIVATE_RESOURCE',
        summary='Foreign-owner content',url='https://example.invalid/foreign',priority_hint=1,
        observed_at=datetime.now(timezone.utc)),subject='user:other')
    titles=[]
    for index in range(count):
        title='DESIRED_REPAIR_RESOURCE' if index==count-1 else 'Unrelated listing '+str(index)
        reader.ingest(DiscoveryCandidate(source='synthetic',title=title,
            summary=('x'*1500+' IMPORTANT_QUALIFICATION') if long else 'Synthetic reference, not a real news event.',
            url='https://example.invalid/material/'+str(index),priority_hint=.01 if index==count-1 else .99,
            observed_at=datetime.now(timezone.utc)),subject='user:synthetic')
        titles.append(title)
    inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-user',
        actor='user:synthetic',subject='user:synthetic',payload={'synthetic':True}))
    MemoryProjection(journal).append_proposal(MemoryProposal(subject='user:synthetic',kind=MemoryKind.PREFERENCE,
        predicate='profile.interest',value='Practical repair interests, not a sending grant.',
        authority=MemoryAuthority.USER_EXPLICIT,confidence=1,source_event_ids=(inbound.event.event_id,)),actor='user:synthetic')
    return journal,reader,titles


async def nine(root):
    journal,reader,_=seed(root,9)
    calls=[]
    async def choose(**kwargs):
        data=json.loads(kwargs['messages'][1]['content']); calls.append(data)
        assert data['user_context'] and len(data['opportunities'])==9
        assert 'FOREIGN_PRIVATE_RESOURCE' not in kwargs['messages'][1]['content']
        source=next(v for v in data['opportunities'] if v['title']=='DESIRED_REPAIR_RESOURCE')
        dimensions={k:dict(value=.1 if k in ('risk','interruption_cost') else .8,reason='Synthetic relevance judgment.')
            for k in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}
        return response(dict(candidates=[dict(agenda_item_id=source['agenda_item_id'],kind='share',
            text='SYNTHETIC_REPAIR_PROPOSAL',topic='repair',dimensions=dimensions)]))
    synth=OpportunitySynthesizer(journal,content_vault=reader.vault)
    result=await synth.run(subject='user:synthetic',operation_id='nine',call=choose)
    assert len(calls)==1 and len(result.candidates)==1 and result.candidates[0].action.authority.value=='none'
    from alive_kernel.agenda import AgendaItemKind,AgendaState
    last_high=journal.get(calls[0]['opportunities'][-2]['observation_event_id']).sequence
    one=reader.agenda.list_items(subject='user:synthetic',clearance=Sensitivity.PRIVATE,
        kinds=(AgendaItemKind.OPPORTUNITY,),states=(AgendaState.ACTIVE,),source_cursor=last_high,limit=1)
    assert len(one)==1 and one[0].item_id==result.candidates[0].action.agenda_item_id
    recovered=OpportunitySynthesizer(ExperienceJournal(journal.path),content_vault=reader.vault).load_completed(
        subject='user:synthetic',operation_id='nine')
    assert recovered==result and len(calls)==1
    snapshot,_=SourceSupportReviewer(journal,content_vault=reader.vault).snapshot(
        subject='user:synthetic',interpretation_id='nine',candidate_id=result.candidates[0].action.candidate_id)
    assert len(snapshot['evidence'])==9
    start=journal.get('opportunity.synthesis:nine:started')
    original_get=journal.get
    altered=replace(start,event=replace(start.event,payload={**dict(start.event.payload),
        'source_scan':{**dict(start.event.payload['source_scan']),'next_sequence':999999}}))
    with patch.object(journal,'get',side_effect=lambda identity: altered if identity==start.event.event_id else original_get(identity)):
        try: synth.load_completed(subject='user:synthetic',operation_id='nine')
        except OpportunitySynthesisError: pass
        else: raise AssertionError('tampered cursor lineage accepted')


async def rotation(root,long=False):
    journal,reader,titles=seed(root,43,long=long)
    seen=set(); windows=[]
    async def capture(**kwargs):
        data=json.loads(kwargs['messages'][1]['content'])
        assert len(kwargs['messages'][1]['content'])<=24000
        window=[v['title'] for v in data['opportunities']]
        assert 'FOREIGN_PRIVATE_RESOURCE' not in window
        windows.append(window); seen.update(window)
        if long:
            assert all(v['summary_excerpt'].endswith('IMPORTANT_QUALIFICATION') for v in data['opportunities'])
        return response(dict(candidates=[]))
    for index in range(6 if long else 2):
        synth=OpportunitySynthesizer(ExperienceJournal(journal.path),content_vault=reader.vault)
        result=await synth.run(subject='user:synthetic',operation_id='rotation:'+str(index),call=capture)
        assert len(result.unassessed_agenda_item_ids)==len(windows[-1])
        assert not result.abstentions
    assert seen==set(titles)
    assert windows[0]!=windows[1]  # Not just eight→thirty-two with the same permanent prefix.
    if long: assert len(windows[0])<32
    cursor=synth._source_cursor('user:synthetic',Sensitivity.PRIVATE)
    assert cursor>0
    inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-user',
        actor='user:synthetic',subject='user:synthetic',payload={'synthetic':True}))
    memory=MemoryProjection(journal)
    for index in range(10):
        memory.append_proposal(MemoryProposal(subject='user:synthetic',kind=MemoryKind.FACT,
            predicate='temporary.task.'+str(index),value='A temporary task fact, not an interest change.',
            authority=MemoryAuthority.USER_EXPLICIT,confidence=1,source_event_ids=(inbound.event.event_id,)),actor='user:synthetic')
    assert synth._source_cursor('user:synthetic',Sensitivity.PRIVATE)==cursor
    prior=next(v for v in synth.context_reader.read(subject='user:synthetic',clearance=Sensitivity.PRIVATE)
        if v.kind=='preference')
    memory.forget_item(prior.memory_id,actor='user:synthetic',request_id='replace-interest')
    memory.append_proposal(MemoryProposal(subject='user:synthetic',kind=MemoryKind.PREFERENCE,
        predicate='profile.interest',value='A changed explicit interest.',
        authority=MemoryAuthority.USER_EXPLICIT,confidence=1,source_event_ids=(inbound.event.event_id,)),actor='user:synthetic')
    assert synth._source_cursor('user:synthetic',Sensitivity.PRIVATE)==0
    assert not journal.read(event_type='action.attempted')


async def failure(root):
    journal,reader,_=seed(root,9)
    synth=OpportunitySynthesizer(journal,content_vault=reader.vault)
    calls=[]
    async def failed(**kwargs):
        calls.append(kwargs)
        raise ConnectionError('synthetic-failure')
    try: await synth.run(subject='user:synthetic',operation_id='failed',call=failed)
    except OpportunitySynthesisError: pass
    else: raise AssertionError('provider failure became a scan completion')
    assert len(calls)==1 and synth._source_cursor('user:synthetic',Sensitivity.PRIVATE)==0


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-interest-recall-') as folder:
        root=Path(folder)
        asyncio.run(nine(root/'nine'))
        asyncio.run(rotation(root/'rotation'))
        asyncio.run(rotation(root/'budget',long=True))
        asyncio.run(failure(root/'failure'))
    print('HERMES_ALIVE_INTEREST_RECALL_WINDOW_OK')
