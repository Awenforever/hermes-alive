"""No-model observation boundary; real journal/vault/read wrapper, synthetic IO.

This is not a live Core/network or consumer-install qualification.
"""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal,DiscoveryOpportunityIngestor
from alive_kernel.content_vault import ContentVault
from alive_kernel.configured_discovery_cycle import ConfiguredDiscoveryCycle
from alive_kernel.core_discovery_tools import CoreDiscoveryTools
from alive_kernel.host_discovery import HostDiscoveryError


async def exercise(root):
    journal=ExperienceJournal(root/'journal.sqlite3')
    vault=ContentVault(root/'vault',backup_root=root/'backups')
    ingestor=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    state=dict(title='Synthetic public update',mode='normal',binding='owner-scope-1',consent=True)
    unload=[];reads=[];models=[]
    entered=threading.Event();release=threading.Event()
    def consent():
        if not state['consent']:raise HostDiscoveryError('synthetic consent withdrawn')
    def dispatch(name,args):
        assert name=='web_search','observation performed a linked-page extraction'
        reads.append((name,args))
        if state['mode']=='blocked':
            entered.set()
            assert release.wait(5),'synthetic read was not released'
        if state['mode']=='failed':return dict(success=False,error='synthetic unavailable')
        items=[] if state['mode']=='empty' else [dict(url='https://example.invalid/update',
            title=state['title'],description='A synthetic public listing, not a full page.')]
        if state['mode']=='partial':items.append(dict(title='Missing URL'))
        return dict(success=True,data=dict(web=items))
    ctx=NS(_manager=NS(scope_key=str(root)),on_unload=unload.append,dispatch_tool=dispatch)
    prep=ConfiguredDiscoveryCycle(ctx,ingestor,subject='user:test',approved_queries=('synthetic public',),
        validate_consent=consent)
    parameters=dict(expression_parameters=dict(model_timeout_seconds=30))
    binding=lambda:state['binding']
    async def model(**kw):
        models.append(kw['task'])
        return NS(choices=[NS(message=NS(content=json.dumps(dict(source_refs=[],question=None,
            value_hypothesis='No worthwhile new material in this synthetic listing.'))))],model='synthetic-model')
    serial=0
    async def observe():
        nonlocal serial
        serial+=1
        cycle=NS(operation_id='synthetic-observation-'+str(serial))
        result=await prep.observe(cycle=cycle,parameters=parameters,read_binding=binding)
        return cycle,result
    async def refused(observed,cycle,*,callback=binding):
        before=len(models)
        try:await prep.reason(observed,cycle=cycle,parameters=parameters,call=model,read_binding=callback)
        except HostDiscoveryError:pass
        else:raise AssertionError('stale, erased or unauthorized observation admitted')
        assert len(models)==before,'refusal happened after model spending'
    async def allow(self,url):return url=='https://example.invalid/update'
    with patch.dict(sys.modules,hermes_constants=NS(get_hermes_home=lambda:root)),patch.object(
            CoreDiscoveryTools,'allow_url',allow):
        first_cycle,first=await observe()
        second_cycle,second=await observe()
        assert first.found.receipt_id!=second.found.receipt_id
        assert first.listing_fingerprint==second.listing_fingerprint is not None
        assert not models and len(reads)==2
        assert not journal.read(event_type='discovery.reading_choice_started')
        assert not any((r.event.correlation_id or '').startswith('inquiry-context:')
            for r in journal.read(event_type='agenda.proposed'))
        await refused(first,first_cycle)
        await refused(replace(second),second_cycle)  # Equal-looking data is not the owning capability.
        await refused(second,NS(operation_id='foreign-cycle'))
        await refused(second,second_cycle,callback=lambda:'foreign-scope')
        # The unchanged source can still be reasoned about explicitly; there is
        # no automatic "unchanged" suppression or fabricated successful draft.
        assert await prep.reason(second,cycle=second_cycle,parameters=parameters,call=model,
            read_binding=binding)==parameters
        assert models==['alive_discovery_reading']
        state['title']='Changed synthetic title'
        third_cycle,third=await observe()
        assert third.listing_fingerprint!=second.listing_fingerprint
        assert len(models)==1
        original=journal.get(third.found.observation_ids[0])
        vault.erase_item(original.event.payload['content']['content_id'])
        await refused(third,third_cycle)
        state['mode']='empty'
        empty_cycle,empty=await observe()
        assert empty.listing_fingerprint is not None and not empty.found.observation_ids
        assert await prep.reason(empty,cycle=empty_cycle,parameters=parameters,call=model,
            read_binding=binding)==parameters
        _,empty_again=await observe()
        assert empty_again.listing_fingerprint==empty.listing_fingerprint
        state['mode']='failed'
        _,failed=await observe()
        assert failed.found.failures and failed.listing_fingerprint is None
        state.update(mode='partial',title='Another synthetic listing')
        _,partial=await observe()
        assert partial.found.failures and partial.found.observation_ids and partial.listing_fingerprint is None
        state.update(mode='normal',title='Final synthetic listing')
        current_cycle,current=await observe()
        state['consent']=False
        await refused(current,current_cycle)
        state['consent']=True
        state['binding']='changed-owner-scope'
        await refused(current,current_cycle)
        state['binding']='owner-scope-1'
        # The composed legacy entry still runs selection exactly once.
        composed=NS(operation_id='synthetic-composed-cycle')
        assert await prep(cycle=composed,parameters=parameters,call=model,read_binding=binding)==parameters
        assert len(models)==2
        closed_cycle,closed=await observe()
        for close in unload:close()
        await refused(closed,closed_cycle)
        count=len(reads)
        try:await observe()
        except HostDiscoveryError:pass
        else:raise AssertionError('unloaded observation resumed public IO')
        assert len(reads)==count
        # A real threaded dispatch remains owned after unload, not just a fake
        # pending flag. No replacement observation starts while it is alive.
        pending_prep=ConfiguredDiscoveryCycle(ctx,ingestor,subject='user:test',
            approved_queries=('synthetic public',),validate_consent=consent)
        state['mode']='blocked'
        pending_cycle=NS(operation_id='synthetic-unload-during-read')
        pending_task=asyncio.create_task(pending_prep.observe(cycle=pending_cycle,
            parameters=parameters,read_binding=binding))
        try:
            assert await asyncio.to_thread(entered.wait,2)
            for close in unload:close()
            assert pending_prep.pending and (await pending_prep.reap_pending())['remaining']==1
            before=len(reads)
            try:await pending_prep.observe(cycle=pending_cycle,parameters=parameters,read_binding=binding)
            except HostDiscoveryError:pass
            else:raise AssertionError('retired pending capability restarted a read')
            assert len(reads)==before
        finally:
            release.set()
            outcome=await asyncio.gather(pending_task,return_exceptions=True)
        assert isinstance(outcome[0],HostDiscoveryError)
        assert (await pending_prep.reap_pending())['remaining']==0
with tempfile.TemporaryDirectory(prefix='alive-observation-phase-') as temporary:
    asyncio.run(exercise(Path(temporary)))
print('HERMES_ALIVE_DISCOVERY_OBSERVATION_PHASE_OK')
