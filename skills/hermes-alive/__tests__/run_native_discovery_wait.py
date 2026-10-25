"""Actual native host/cycle wait composition; synthetic model and public IO only."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'hooks'),str(Path(__file__).resolve().parent)]
from alive_kernel import AutonomyPolicyProjection,DiscoveryOpportunityIngestor,EventEnvelope,PolicyContext
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
from alive_kernel.configured_discovery_cycle import ConfiguredDiscoveryCycle
from alive_kernel.core_discovery_tools import CoreDiscoveryTools
from alive_kernel.native_cognition_host import NativeCognitionHost
from run_alive_kernel_expression_runtime import scenario


async def exercise(root,*,selected=False):
    journal,initial,_=await scenario(root/'kernel','share',return_ready=True)
    runtime=AutonomousCycleRuntime(journal)
    policies=AutonomyPolicyProjection(journal)
    def policy(enabled):
        current=policies.current('user:test')
        policies.apply(policies.append_update(subject='user:test',actor='user:test',
            expected_revision=current.revision if current else 0,enabled=enabled,
            context=PolicyContext(can_interrupt=enabled),operation_id='wait-policy:'+str(journal.last_sequence())))
    policy(True)
    state=dict(title='Synthetic public finding',failed=False)
    models=[];reads=[];unload=[];reconciliations=[]
    def dispatch(name,args):
        assert name in ('web_search','web_extract')
        reads.append(args)
        if name=='web_extract':
            return dict(results=[dict(url='https://example.invalid/new-listing',title=state['title'],
                content='A synthetic public page with no independently verified new result.')])
        if state['failed']:return dict(success=False,error='synthetic temporary failure')
        return dict(success=True,data=dict(web=[dict(url='https://example.invalid/new-listing',
            title=state['title'],description='A synthetic listing, not a whole page.')]))
    ctx=NS(_manager=NS(scope_key=str(root)),on_unload=unload.append,dispatch_tool=dispatch)
    class Caller:
        pending=()
        def __init__(self,cycle,read_binding):self.calls=0;self.binding=read_binding
        async def reap_pending(self,**kw):return dict(closed=0,remaining=0)
        async def __call__(self,**kw):
            self.binding();self.calls+=1;models.append(kw['task'])
            if kw['task']=='alive_discovery_reading':
                sources=json.loads(kw['messages'][1]['content'])['sources']
                value=dict(source_refs=[sources[0]['source_ref']] if selected else [],
                    question='What did this source actually report?' if selected else None,
                    value_hypothesis='Read before deciding.' if selected else 'No reading is worthwhile in this synthetic case.')
            elif kw['task']=='alive_opportunity_candidates':value=dict(candidates=[])
            else:raise AssertionError('unexpected model stage '+kw['task'])
            return NS(model='synthetic/silence',choices=[NS(message=NS(content=json.dumps(value)))])
    original_tick=runtime.reconciliation.tick
    async def tick(**kw):
        reconciliations.append(kw)
        return await original_tick(**kw)
    runtime.reconciliation.tick=tick
    def native():
        preparation=ConfiguredDiscoveryCycle(ctx,DiscoveryOpportunityIngestor(journal,
            content_vault=runtime.preparation.vault),subject='user:test',approved_queries=('synthetic public',),
            validate_consent=lambda:None,follow_citations=not selected,record_reading_assessment=not selected)
        host=AutonomousHostRuntime(runtime,subject='user:test',configuration_id='native-wait-fixture')
        return NativeCognitionHost(host,profile_id='profile:test',profile_home=root,
            read_configuration=lambda:{},read_credential_names=lambda **_:(),interpreter=sys.executable,
            core=root,private_root=root,environment={},resolve_domain=lambda *labels:'synthetic-family',
            caller_factory=lambda **kw:Caller(**kw),preparation=preparation)
    expression={k:v for k,v in initial.items() if k not in
        ('subject','operation_id','policy_context','call','resolve_domain','read_context')}
    parameters=dict(expression_parameters=expression,resolve_binding=lambda _:None,reconsider_after_seconds=300)
    async def allow(self,url):return url=='https://example.invalid/new-listing'
    with patch.dict(sys.modules,hermes_constants=NS(get_hermes_home=lambda:root)),patch.object(
            CoreDiscoveryTools,'allow_url',allow):
        runner=native()
        assert (await runner.step(parameters)).disposition=='silence'
        assert models==['alive_discovery_reading','alive_opportunity_candidates']
        assert journal.read(event_type='cognition.wait_recorded'),'first real composed cycle did not retain wait'
        first=journal.read(event_type='cognition.wait_recorded')[-1]
        assert (await runner.step(parameters)).disposition=='waiting_for_change'
        assert len(models)==2 and len(reads)==(3 if selected else 2) and len(reconciliations)==2
        assert runner.last_call_count==0
        # Rebuild every host/reader capability, retaining only ordinary durable state.
        for close in unload:close()
        runner=native()
        assert (await runner.step(parameters)).disposition=='waiting_for_change'
        assert len(models)==2 and journal.read(event_type='cognition.wait_recorded')[-1].event==first.event
        if selected:
            prior=first.event.payload['operation_id']
            prepared=journal.get(runner.preparation._prepared_identity(prior))
            content=runtime.preparation.vault.resolve_json(prepared.event.payload['content']['content_id'],
                expected_subject='user:test',expected_purpose='discovery.prepared-parameters')
            assert content['parameters']['inquiry_item_ids'],'only empty argument restoration was tested'
            state['title']='A changed selected source'
            assert (await runner.step(parameters)).disposition=='silence' and len(models)==4
            assert (await runner.step(parameters)).disposition=='waiting_for_change' and len(models)==4
            assert not runner.pending
            return
        state['title']='Changed public finding'
        assert (await runner.step(parameters)).disposition=='silence'
        assert len(models)==4
        assert (await runner.step(parameters)).disposition=='waiting_for_change' and len(models)==4
        # This observes inbound identity only, not any private message body.
        journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
            actor='user:test',subject='user:test',payload=dict(synthetic=True)))
        assert (await runner.step(parameters)).disposition=='silence' and len(models)==6
        assert (await runner.step(parameters)).disposition=='waiting_for_change' and len(models)==6
        journal.append(EventEnvelope(event_type='synthetic.unknown_owner_change',source='synthetic',
            actor='user:test',subject='user:test',payload=dict(synthetic=True)))
        assert (await runner.step(parameters)).disposition=='silence' and len(models)==8
        policy(False)
        before=(len(models),len(reads))
        assert (await runner.step(parameters)).disposition=='paused'
        assert (len(models),len(reads))==before
        policy(True)
        assert (await runner.step(parameters)).disposition=='silence' and len(models)==10
        # A missing derived-argument receipt never justifies reuse, even when
        # the previously selected argument delta happened to be empty.
        previous=journal.read(event_type='discovery.parameters_retained')[-1]
        runtime.preparation.vault.erase_item(previous.event.payload['content']['content_id'])
        assert (await runner.step(parameters)).disposition=='silence' and len(models)==12
        # Loss of the actual generation proof is also a wake, not a resumed spend.
        proof=journal.read(event_type='opportunity.synthesis_completed')[-1]
        runtime.preparation.vault.erase_item(proof.event.payload['content']['content_id'])
        assert (await runner.step(parameters)).disposition=='silence' and len(models)==14
        state['failed']=True
        failed=await runner.step(parameters)
        assert failed.disposition!='waiting_for_change' and len(models)>14
        state['failed']=False
        assert (await runner.step(parameters)).disposition=='silence'
        old=journal.read(event_type='cognition.wait_recorded')[-1]
        deadline=datetime.fromisoformat(old.event.payload['valid_until'])
        runtime.reconsideration.clock=lambda:deadline+timedelta(seconds=1)
        before=len(models)
        assert (await runner.step(parameters)).disposition=='silence' and len(models)==before+2
        runtime.reconsideration.clock=lambda:datetime.now(timezone.utc)
        assert not journal.read(event_type='action.attempted')
        assert not journal.read(event_type='dispatch.externally_delivered')
        assert not runner.pending


with tempfile.TemporaryDirectory(prefix='alive-native-discovery-wait-') as folder:
    for selected in (False,True):
        root=Path(folder)/('selected' if selected else 'abstained');root.mkdir()
        with patch.dict(os.environ,HERMES_HOME=str(root),HERMES_ALIVE_SHARED_DIR=str(root/'runtime')):
            asyncio.run(exercise(root,selected=selected))
print('HERMES_ALIVE_NATIVE_DISCOVERY_WAIT_OK')
