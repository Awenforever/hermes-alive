"""Native observation/reason/planning after real retained rejection; synthetic IO.

No Core ABI replacement, external delivery, real model or quality-round claim.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch
from datetime import datetime,timedelta

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'hooks'),str(Path(__file__).resolve().parent)]
from run_qualified_content_rejection import make_rejection
from alive_kernel import DiscoveryOpportunityIngestor
from alive_kernel.configured_discovery_cycle import ConfiguredDiscoveryCycle
from alive_kernel.core_discovery_tools import CoreDiscoveryTools
from alive_kernel.content_vault import ContentReference
from alive_kernel.native_cognition_host import NativeCognitionHost
from alive_kernel.rejection_eligibility import RejectionEligibility


async def exercise(root,*,alternative):
    journal,runtime,host,_,_,_,rejected,_=await make_rejection(root,'unsupported',retry_window=3600)
    assert rejected.content_rejection is not None
    bad='https://example.invalid/workshop';other='https://example.invalid/other'
    reads=[];models=[];unload=[]
    def dispatch(name,args):
        reads.append((name,args))
        if name=='web_search':
            items=[dict(url=bad,title='Existing workshop',description='Existing synthetic material.')]
            if alternative:items.append(dict(url=other,title='Different public topic',description='Different synthetic material.'))
            return dict(success=True,data=dict(web=items))
        assert name=='web_extract'
        assert args['urls']==[other if alternative else bad]
        return dict(results=[dict(url=args['urls'][0],title='Public source',content='A synthetic public account without a communication obligation.')])
    ctx=NS(_manager=NS(scope_key=str(root)),on_unload=unload.append,dispatch_tool=dispatch)
    class Caller:
        pending=()
        def __init__(self,cycle,read_binding):self.calls=0;self.binding=read_binding
        async def reap_pending(self,**_):return dict(closed=0,remaining=0)
        async def __call__(self,**kw):
            self.binding();self.calls+=1;models.append(kw['task'])
            data=json.loads(kw['messages'][1]['content'])
            if kw['task']=='alive_discovery_reading':
                assert all(source['url']!=bad for source in data['sources']) if alternative else True
                value=dict(source_refs=[data['sources'][0]['source_ref']],question='What is worth understanding?',
                    value_hypothesis='Read the actual source before deciding.')
            elif kw['task']=='alive_opportunity_candidates':
                if alternative:
                    allowed=set(data['stage_contract']['eligible_primary_agenda_ids'])
                    assert allowed and all(source['url']!=bad for source in data['opportunities']
                        if source['agenda_item_id'] in allowed)
                value=dict(candidates=[])
            else:raise AssertionError('unexpected model '+kw['task'])
            return NS(model='synthetic/caller',choices=[NS(message=NS(content=json.dumps(value)))])
    def native():
        prep=ConfiguredDiscoveryCycle(ctx,DiscoveryOpportunityIngestor(journal,content_vault=runtime.preparation.vault),
            subject=host.subject,approved_queries=('synthetic public',),validate_consent=lambda:None)
        return NativeCognitionHost(host,profile_id='profile:test',profile_home=root,
            read_configuration=lambda:{},read_credential_names=lambda **_:(),interpreter=sys.executable,
            core=root,private_root=root,environment={},resolve_domain=lambda *labels:'synthetic-family',
            caller_factory=lambda **kw:Caller(**kw),preparation=prep)
    options=dict(expression_parameters=dict(model_timeout_seconds=30),resolve_binding=lambda _:None,reconsider_after_seconds=300)
    async def allow(self,url):return url in (bad,other)
    with patch.dict(sys.modules,hermes_constants=NS(get_hermes_home=lambda:root)),patch.object(CoreDiscoveryTools,'allow_url',allow):
        runner=native()
        first=await runner.step(options)
        assert first.disposition==('silence' if alternative else 'content_deferred')
        assert len(models)==(2 if alternative else 0)
        if alternative:assert journal.read(event_type='cognition.wait_recorded'),'eligible abstention did not retain wait'
        second=await runner.step(options)
        assert second.disposition==('waiting_for_change' if alternative else 'content_deferred'),(second.disposition,models)
        assert len(models)==(2 if alternative else 0),'unchanged held material repeated model work'
        assert not any(name=='web_extract' and args['urls']==[bad] for name,args in reads)
        assert runtime.preparation.restore_rejection(rejected.content_rejection.to_event_payload(),
            dict(subject=host.subject,operation_id=rejected.content_rejection.operation_id)) is not None
        # Restore the host/reader, not a grant, and leave original negative proof unchanged.
        for close in unload:close()
        runner=native()
        assert (await runner.step(options)).disposition==second.disposition
        assert len(models)==(2 if alternative else 0)
        if alternative:
            # An unrelated held source is only original decision provenance.
            # Its later erasure cannot invalidate another retained interpretation.
            for identity in rejected.content_rejection.source_event_ids:
                record=journal.get(identity)
                ref=ContentReference.from_event_payload(record.event.payload['content'])
                runtime.preparation.vault.erase_item(ref.content_id)
            receipt=first.expression.planning.interpretation_event_id
            retained=runtime.preparation.expression.planning.synth.load_completed(
                subject=host.subject,clearance='private',
                operation_id=receipt.removeprefix('opportunity.synthesis:').removesuffix(':completed'))
            assert not retained.candidate_deferred and not retained.candidates
            assert len(models)==2
        if not alternative:
            deadline=next(journal.iter_reverse(event_types=('autonomous.host.closed',),subject=host.subject,
                max_records=32)).event.observed_at
            original=RejectionEligibility
            with patch('alive_kernel.rejection_eligibility.RejectionEligibility',
                    side_effect=lambda current:original(current,clock=lambda:deadline+timedelta(hours=1,seconds=1))):
                assert (await runner.step(options)).disposition=='silence'
            assert len(models)==2,'expiry did not make material eligible again'
        assert not journal.read(event_type='action.attempted')
        assert not journal.read(event_type='dispatch.externally_delivered')
        assert not runner.pending


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-native-content-recovery-') as temporary:
        for alternative in (False,True):
            root=Path(temporary)/('alternative' if alternative else 'all-held');root.mkdir()
            with patch.dict(os.environ,HERMES_HOME=str(root),HERMES_ALIVE_SHARED_DIR=str(root/'runtime')):
                print('NATIVE_CONTENT_RECOVERY_CASE='+root.name,flush=True)
                asyncio.run(exercise(root,alternative=alternative))
    print('HERMES_ALIVE_NATIVE_CONTENT_RECOVERY_OK')
