"""Bound discovery -> actual kernel expression/recovery; synthetic IO/models only."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal,DiscoveryOpportunityIngestor,AutonomyPolicyProjection,PolicyContext
from alive_kernel import MemoryProjection,MemoryProposal,MemoryKind,MemoryAuthority,EventEnvelope
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.autonomous_host_runtime import AutonomousHostRuntime
from alive_kernel.configured_discovery_cycle import ConfiguredDiscoveryCycle
from alive_kernel.core_discovery_tools import CoreDiscoveryTools
from alive_kernel.core_shadow_assembly import normalize_settings
from alive_kernel.content_vault import ContentVault
from alive_kernel.host_discovery import HostDiscoveryError,HostReadUncertainError
from alive_kernel.native_cognition_host import NativeCognitionHost
from alive_kernel.native_worker_protocol import NativeWorkerError


base=dict(enabled=True,consent='model_calls_no_delivery',subject='user:test')
assert 'public_discovery' not in normalize_settings(base)
for value in (None,{},dict(consent='model_calls_no_delivery',queries=['public']),
              dict(consent='approved_public_queries_no_delivery',queries=[]),
              dict(consent='approved_public_queries_no_delivery',queries=['same','same'])):
    try:normalize_settings({**base,'public_discovery':value})
    except ValueError:pass
    else:raise AssertionError('model-only or invalid disclosure consent admitted')


async def exercise(root,mode):
    journal=ExperienceJournal(root/'journal.sqlite3')
    vault=ContentVault(root/'vault',backup_root=root/'backups')
    ingestor=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    memory=MemoryProjection(journal)
    preference=None
    if mode=='forgotten-choice':
        inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
            actor='user:test',subject='user:test',payload={'synthetic':True}))
        preference=MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.interest',
            value='PRIVATE_OWNER_PREFERENCE',authority=MemoryAuthority.USER_EXPLICIT,
            source_event_ids=(inbound.event.event_id,),confidence=1)
        memory.apply(memory.append_proposal(preference,actor='user:test'))
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=mode!='paused',context=PolicyContext(can_interrupt=True),operation_id='enable'))
    state={'consent':True,'interrupt':mode=='replay'}
    tools=[];models=[];unload=[];release=threading.Event();entered=threading.Event()
    url='https://example.invalid/conservation'
    def dispatch(name,args):
        assert journal.read(event_type='autonomous.host.opened'),'read happened before durable cycle binding'
        assert name in ('web_search','web_extract')
        tools.append((name,args))
        if name=='web_search':
            assert args==dict(query='public museum methods',limit=3)
            return json.dumps(dict(success=True,data=dict(web=[dict(url=url,title='Conservation update',
                description='A public non-invasive conservation method is described.')])) )
        assert args['urls']==[url]
        if mode=='uncertain-read':
            entered.set();assert release.wait(5)
        if mode=='page-failed':return json.dumps(dict(results=[dict(url=url,error='synthetic unavailable')]))
        return json.dumps(dict(results=[dict(url=url,title='Conservation update',
            content='The museum uses non-invasive observation before intervention. DEEP_READ_EVIDENCE.')]))
    ctx=NS(_manager=NS(scope_key=str(root)),on_unload=unload.append,dispatch_tool=dispatch)
    def consent():
        if not state['consent']:raise HostDiscoveryError('synthetic disclosure consent withdrawn')
    def preparation():return ConfiguredDiscoveryCycle(ctx,ingestor,subject='user:test',
        approved_queries=('public museum methods',),validate_consent=consent)
    class Runtime(AutonomousCycleRuntime):
        async def cycle(self,**kw):
            result=await super().cycle(**kw)
            if state['interrupt']:
                state['interrupt']=False
                raise RuntimeError('synthetic interruption after completed expression before host close')
            return result
    runtime=Runtime(journal,content_vault=vault)
    host=AutonomousHostRuntime(runtime,subject='user:test',configuration_id='configured-public-discovery')
    class Caller:
        def __init__(self,cycle,read_binding):self.calls=0;self.read_binding=read_binding;self.cycle=cycle
        pending=()
        async def reap_pending(self,**kw):return dict(closed=0,remaining=0)
        async def __call__(self,**kw):
            assert self.read_binding().operation_id==self.cycle.operation_id
            self.calls+=1;models.append(kw['task'])
            task=kw['task'];raw=kw['messages'][1]['content']
            data=json.loads(raw) if task!='alive_deliberation' else None
            if task=='alive_discovery_reading':
                refs=[s['source_ref'] for s in data['sources']]
                if mode=='invalid-choice':refs=['https://private.invalid/not-a-supplied-reference']
                value=dict(source_refs=[] if mode=='abstain' else refs[:1],
                    question=None if mode=='abstain' else 'INTERNAL_RESEARCH_QUESTION: What changed in observation?',
                    value_hypothesis='A tentative interesting conservation insight, not a user request.')
                if mode=='revoked-choice':state['consent']=False
                if mode=='forgotten-choice':
                    assert 'PRIVATE_OWNER_PREFERENCE' in raw
                    memory.forget_item(preference.proposal_id,actor='user:test',request_id='forget-during-choice')
                if mode=='erased-choice':
                    original=journal.get(refs[0])
                    ingestor.vault.erase_item(original.event.payload['content']['content_id'])
            elif task=='alive_opportunity_candidates':
                sources=data['opportunities']
                if mode=='abstain':value=dict(candidates=[],abstentions=[dict(agenda_item_id=e['agenda_item_id'],reason='No worthwhile contribution.') for e in sources])
                else:
                    assert data['tentative_discovery_tasks']
                    if mode!='page-failed':assert any('DEEP_READ_EVIDENCE' in e['summary_excerpt'] for e in sources)
                    e=next((e for e in sources if 'DEEP_READ_EVIDENCE' in e['summary_excerpt']),sources[0])
                    value=dict(candidates=[dict(agenda_item_id=e['agenda_item_id'],kind='share',topic='conservation',
                        communication_plan=dict(version=3,recipient_goal='INTERNAL_GOAL',speech_act='share',contents=[],behavior_constraints=[]),
                        dimensions={n:dict(value=.1 if n in ('risk','urgency','interruption_cost') else .9,reason='Synthetic judgment')
                            for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})])
            elif task=='alive_deliberation':
                choices=json.loads(raw.split('\n',1)[1])
                value=dict(candidate_id=next(c['candidate_id'] for c in choices if c['candidate_id'].startswith('opportunity-candidate:')),rationale='Synthetic contribution')
            elif task=='alive_semantic_render':
                assert 'INTERNAL_GOAL' not in raw and 'INTERNAL_RESEARCH_QUESTION' not in raw
                value='The museum describes observing without intervention: [conservation method]('+url+').'
            elif task=='alive_semantic_review':
                value=dict(atom_reviews=[dict(atom_id=a['atom_id'],preserved=True,risks=[]) for a in data['meaning']['atoms']],
                    added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
            elif task=='alive_source_support':
                assert data['expression_binding']['assessment_mode']=='discovery-source-and-value-v2'
                value=dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='Synthetic, not recipient satisfaction.')
            else:raise AssertionError(task)
            if 'route_info' in kw:kw['route_info']['provider']='synthetic'
            return NS(model='synthetic-model',choices=[NS(message=NS(content=value if isinstance(value,str) else json.dumps(value)))])
    def native(prep=None):return NativeCognitionHost(host,profile_id='profile:test',profile_home=root,
        read_configuration=lambda:{},read_credential_names=lambda **_:(),interpreter=sys.executable,
        core=root,private_root=root,environment={},resolve_domain=lambda *labels:'synthetic-family',
        caller_factory=lambda *,cycle,read_binding:Caller(cycle,read_binding),preparation=prep or preparation())
    parameters=dict(expression_parameters=dict(recipient_meaning=True,grounding=True,
        require_independent_grounding=False,model_timeout_seconds=30),resolve_binding=lambda _:None)
    async def allow(self,target):return target==url
    original_tools=CoreDiscoveryTools
    def bounded_tools(*args,**kw):return original_tools(*args,**kw,timeout_seconds=.03 if mode=='uncertain-read' else 2)
    with patch.dict(sys.modules,hermes_constants=NS(get_hermes_home=lambda:root)),patch.object(CoreDiscoveryTools,'allow_url',allow),patch(
            'alive_kernel.configured_discovery_cycle.CoreDiscoveryTools',side_effect=bounded_tools):
        runner=native()
        if mode in ('invalid-choice','revoked-choice','forgotten-choice','erased-choice','uncertain-read'):
            try:await runner.step(parameters)
            except (HostDiscoveryError,NativeWorkerError):pass
            else:raise AssertionError('invalid/revoked/uncertain discovery succeeded')
            assert not journal.read(event_type='autonomous.host.closed')
            failure=journal.read(event_type='autonomous.host.failed')[-1].event
            assert failure.payload['phase']=='preparation'
            assert failure.payload['failure_class'] in ('HostDiscoveryError','HostReadUncertainError')
            assert 'message' not in failure.payload and failure.payload['authority_granted'] is False
            if mode=='uncertain-read':
                assert entered.is_set() and runner.pending
                try:await runner.step(parameters)
                except NativeWorkerError:pass
                else:raise AssertionError('pending physical read allowed another cycle')
                release.set();assert (await runner.reap_pending(timeout_seconds=2))['remaining']==0
            state['consent']=True
            before=(len(tools),len(models))
            try:await native().step(parameters)
            except HostDiscoveryError:pass
            else:raise AssertionError('incomplete/failed operation silently repeated')
            assert (len(tools),len(models))==before
        else:
            if mode=='replay':
                try:await runner.step(parameters)
                except RuntimeError:pass
                else:raise AssertionError('synthetic interruption did not occur')
                before=(len(tools),len(models));runner=native()
            result=await runner.step(parameters)
            if mode=='replay':assert (len(tools),len(models))==before
            assert result.disposition==('paused' if mode=='paused' else 'silence' if mode=='abstain' else 'shadow_selected')
            assert len(journal.read(event_type='autonomous.host.closed'))==1
            if mode=='paused':assert not tools and not models
            elif mode!='abstain':
                assert url in result.expression.text
                assert len(tools)==2 and models.count('alive_discovery_reading')==1
                assert models.count('alive_source_support')==1
            else:assert len(tools)==1
        assert not journal.read(event_type='action.attempted')
        assert not journal.read(event_type='dispatch.externally_delivered')
        assert not runner.pending
    release.set()


with tempfile.TemporaryDirectory(prefix='alive-configured-discovery-') as folder:
    for mode in ('share','replay','page-failed','abstain','paused','invalid-choice','revoked-choice','forgotten-choice','erased-choice','uncertain-read'):
        root=Path(folder)/mode;root.mkdir()
        with patch.dict(os.environ,HERMES_HOME=str(root),HERMES_ALIVE_SHARED_DIR=str(root/'runtime')):
            asyncio.run(exercise(root,mode))
print('HERMES_ALIVE_CONFIGURED_DISCOVERY_CYCLE_OK')
