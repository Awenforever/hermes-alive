"""Bound discovery -> actual kernel expression/recovery; synthetic IO/models only."""
import asyncio
import argparse
from dataclasses import replace
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
from alive_kernel.events import Sensitivity
from alive_kernel.host_discovery import HostDiscoveryError,HostReadUncertainError
from alive_kernel.native_cognition_host import NativeCognitionHost
from alive_kernel.native_worker_protocol import NativeWorkerError
from alive_kernel.research_evidence import research_scan,validate_research_scan,resolve_research_reads
from alive_kernel.discovery_opportunities import DiscoveryCandidate
from alive_kernel.semantic_comparator import SemanticComparator


base=dict(enabled=True,consent='model_calls_no_delivery',subject='user:test')
assert 'public_discovery' not in normalize_settings(base)
for value in (None,{},dict(consent='model_calls_no_delivery',queries=['public']),
              dict(consent='approved_public_queries_no_delivery',queries=[]),
              dict(consent='approved_public_queries_no_delivery',queries=['same','same']),
              dict(consent='approved_public_queries_no_delivery',queries=['public'],follow_citations=1)):
    try:normalize_settings({**base,'public_discovery':value})
    except ValueError:pass
    else:raise AssertionError('model-only or invalid disclosure consent admitted')
assert normalize_settings({**base,'public_discovery':dict(consent='approved_public_queries_no_delivery',
    queries=['public'])})['public_discovery']==dict(consent='approved_public_queries_no_delivery',queries=['public'])

reference='retained-public-page'
linked='https://example.invalid/original?version=2'
refs={reference:NS(content=dict(source='hermes.web.extract',summary='[Original]('+linked+')',
                               attributes=dict(read_scope='webpage_extract')))}
def decision(url=linked,source_ref=reference):
    return dict(read_targets=[dict(source_ref=source_ref,url=url)],reason='Resolve the cited original claim.')
assert ConfiguredDiscoveryCycle._followup_choice(decision(),refs,())==decision()
for invalid,visited in ((decision(linked.split('?')[0]),()),(decision(),(linked,)),
                        (dict(read_targets=decision()['read_targets']*2,reason='duplicate'),()),
                        (decision(source_ref='foreign'),()),(decision('https://example.invalid/invented'),())):
    try:ConfiguredDiscoveryCycle._followup_choice(invalid,refs,visited)
    except HostDiscoveryError:pass
    else:raise AssertionError('invented/truncated/repeated/foreign follow-up admitted')

fake_records={str(i):NS(sequence=i,event=NS(event_type='discovery.opportunity_observed',
    subject='user:test',source='alive.discovery',actor='system:alive-discovery')) for i in range(1,7)}
fake_journal=NS(get=fake_records.get)
fake_sources={i:NS(observation_event_id=i) for i in fake_records}
for cursor,order,admitted,expected in ((0,('1','2','3','4','5','6'),('6','1','2'),2),
                                      (4,('5','6','1','2','3','4'),('6','5','1'),1)):
    scan=research_scan(fake_journal,focus=(fake_sources['6'],),fair_pool=tuple(fake_sources[i] for i in order),
        evidence=tuple(fake_sources[i] for i in admitted),cursor=cursor,preference_digest='synthetic')
    assert scan['next_sequence']==expected,'priority evidence advanced past unseen background'
    started=NS(sequence=10,event=NS(subject='user:test',payload=dict(observation_event_ids=admitted)))
    validate_research_scan(fake_journal,started,scan,('6',))
    try:validate_research_scan(fake_journal,started,{**scan,'next_sequence':6},('6',))
    except HostDiscoveryError:pass
    else:raise AssertionError('forged priority cursor accepted')
for context,expected in ((dict(method='discovery-source-authoring-v3'),'semantic-findings-v1'),
        (dict(method='discovery-source-authoring-v3',semantic_source_contract='bounded-group-source-v1'),'semantic-source-findings-v1')):
    original,system,protocol=SemanticComparator._review_contract({'atoms':[]},'Synthetic text',context)
    assert protocol==expected
    assert ('source_context' in original)==(expected=='semantic-source-findings-v1')


async def exercise(root,mode,*,primary_url=None):
    pressure=mode in ('budget-pressure','fair-budget-pressure','reading-assessment-budget-pressure')
    journal=ExperienceJournal(root/'journal.sqlite3')
    vault=ContentVault(root/'vault',backup_root=root/'backups')
    ingestor=DiscoveryOpportunityIngestor(journal,content_vault=vault)
    memory=MemoryProjection(journal)
    preference=None
    if pressure:
        for i in range(6):
            event=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
                actor='user:test',subject='user:test',payload=dict(synthetic=True,index=i)))
            proposal=MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.synthetic.'+str(i),
                value='SYNTHETIC_PREFERENCE_LONG '+('neutral contextual preference. '*35),
                authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(event.event.event_id,),confidence=1)
            memory.apply(memory.append_proposal(proposal,actor='user:test'))
        if mode=='fair-budget-pressure':
            for i in range(26):
                ingestor.ingest(DiscoveryCandidate(source='synthetic-public-background',title='Background '+str(i),
                    url='https://example.invalid/background/'+str(i),summary='Unrelated public baseline. '*100,
                    observed_at=datetime.now(timezone.utc)),subject='user:test')
    if mode in ('forgotten-choice','forgotten-followup','private-followup'):
        inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
            actor='user:test',subject='user:test',payload={'synthetic':True}))
        preference=MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.interest',
            value='PRIVATE_OWNER_PREFERENCE',authority=MemoryAuthority.USER_EXPLICIT,
            source_event_ids=(inbound.event.event_id,),confidence=1)
        memory.apply(memory.append_proposal(preference,actor='user:test'))
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=mode!='paused',context=PolicyContext(can_interrupt=True),operation_id='enable'))
    state={'consent':True,'interrupt':mode in ('replay','legacy-replay','historical-followup-replay')}
    tools=[];models=[];unload=[];release=threading.Event();entered=threading.Event()
    url='https://example.invalid/conservation'
    primary=primary_url or 'https://example.invalid/original-observations'
    backgrounds=(url+'/context-1',url+'/context-2')
    def dispatch(name,args):
        assert journal.read(event_type='autonomous.host.opened'),'read happened before durable cycle binding'
        assert name in ('web_search','web_extract')
        tools.append((name,args))
        if name=='web_search':
            assert args==dict(query='public museum methods',limit=3)
            entries=[dict(url=url,title='Conservation update',description='A public non-invasive conservation method is described.')]
            if pressure:
                entries[0]['description']+=' Neutral listing.'*100
                entries.extend(dict(url=u,title='Background context',description='Independent background. '*75) for u in backgrounds)
            return json.dumps(dict(success=True,data=dict(web=entries)))
        assert args['urls'] in ([url],[primary])
        if args['urls']==[primary]:
            if mode=='followup-failed':return json.dumps(dict(results=[dict(url=primary,error='synthetic unavailable')]))
            return json.dumps(dict(results=[dict(url=primary,title='Original observation protocol',
                content='PRIMARY_READ_EVIDENCE: Authors describe a protocol, not independent validation.'
                    +(' Original evidence.'*420 if pressure else ''))] ))
        if mode=='uncertain-read':
            entered.set();assert release.wait(5)
        if mode=='page-failed':return json.dumps(dict(results=[dict(url=url,error='synthetic unavailable')]))
        return json.dumps(dict(results=[dict(url=url,title='Conservation update',
            content='The museum uses non-invasive observation before intervention. DEEP_READ_EVIDENCE.'
                +' Navigation text.'*(410 if pressure else 150)+' [Original observations]('+primary+').')]))
    ctx=NS(_manager=NS(scope_key=str(root)),on_unload=unload.append,dispatch_tool=dispatch)
    def consent():
        if not state['consent']:raise HostDiscoveryError('synthetic disclosure consent withdrawn')
    def preparation():return ConfiguredDiscoveryCycle(ctx,ingestor,subject='user:test',
        approved_queries=('public museum methods',),validate_consent=consent,
        follow_citations=mode not in ('unconsented-followup','reading-assessment-no-followup'),
        record_reading_assessment=mode.startswith('reading-assessment'))
    class Runtime(AutonomousCycleRuntime):
        async def cycle(self,**kw):
            if mode=='budget-pressure' and os.getenv('ALIVE_REPRODUCE_OLD_RECALL')=='1':
                # Negative control: same completed reads, old unchanged packing
                # path without explicit bundle propagation. Must lose evidence.
                parameters=dict(kw['expression_parameters']);parameters.pop('research_read_receipt_ids',None)
                kw={**kw,'expression_parameters':parameters}
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
            if task=='alive_opportunity_candidates' and isinstance(data,dict) and 'original_evidence' in data:
                data=data['original_evidence']
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
            elif task=='alive_discovery_followup':
                assert 'PRIVATE_OWNER_PREFERENCE' not in raw
                assert 'SYNTHETIC_PREFERENCE_LONG' not in raw
                assert 'INTERNAL_RESEARCH_QUESTION' not in raw
                assert 'user_context' not in data and 'owner_context_digest' not in data
                assert primary in data['sources'][0]['excerpt'], 'follow-up silently truncated deep read'
                target=dict(source_ref=data['sources'][0]['source_ref'],url=primary)
                if data['method']=='cited-public-followup-v2':
                    target=dict(source_ref=target['source_ref'],citation_ref=next(c['citation_ref']
                        for c in data['sources'][0]['citations'] if c['url']==primary))
                if mode in ('invented-followup','historical-invalid-followup'):target['url']='https://example.invalid/never-cited'
                if mode=='foreign-followup':target['source_ref']='another-owner-source'
                if mode=='revoked-followup':state['consent']=False
                if mode=='forgotten-followup':memory.forget_item(preference.proposal_id,actor='user:test',request_id='forget-followup')
                if mode=='erased-followup':
                    original=journal.get(target['source_ref'])
                    ingestor.vault.erase_item(original.event.payload['content']['content_id'])
                if mode=='interrupted-followup':raise RuntimeError('synthetic follow-up inference interrupted')
                value=dict(read_targets=[target] if 'followup' in mode or pressure or mode in ('primary-read','replay','erase-group-after-final') else [],
                    reason='Read the cited original protocol, or stop when current scope is adequate.')
                if mode=='mixed-followup':
                    value['read_targets'].append(dict(source_ref=target['source_ref'],citation_ref='invented'))
                if mode=='malformed-followup':value={'unusable':'not a source selection'}
                if mode=='nonjson-followup':value='not JSON; no authority'
            elif task=='alive_opportunity_candidates':
                sources=[{**e,'summary_excerpt':e.get('summary_excerpt') or ''.join(p['text'] for p in e.get('summary_passages',[]))}
                         for e in data['opportunities']]
                if mode=='abstain':value=dict(candidates=[],abstentions=[dict(agenda_item_id=e['agenda_item_id'],reason='No worthwhile contribution.') for e in sources])
                else:
                    assert data['tentative_discovery_tasks']
                    if pressure or mode in ('primary-read','replay','private-followup','erase-group-after-final','historical-followup-replay','mixed-followup'):
                        if os.getenv('ALIVE_REPRODUCE_OLD_RECALL')=='1' and not any('PRIMARY_READ_EVIDENCE' in e['summary_excerpt'] for e in sources):
                            print('REGRESSION_OLD_RECALL_DROPPED_PRIMARY pool='+str(data['recall_window']['pool_size'])+' window='+str(len(sources)),flush=True)
                        assert any('PRIMARY_READ_EVIDENCE' in e['summary_excerpt'] for e in sources)
                    if pressure:
                        assert len(raw)>24000, 'fixture did not recreate the old packing pressure'
                    if mode!='page-failed':assert any('DEEP_READ_EVIDENCE' in e['summary_excerpt'] for e in sources)
                    e=next((e for e in sources if 'DEEP_READ_EVIDENCE' in e['summary_excerpt']),sources[0])
                    value=dict(candidates=[dict(agenda_item_id=e['agenda_item_id'],kind='share',topic='conservation',
                        communication_plan=dict(version=3,recipient_goal='INTERNAL_GOAL',speech_act='share',contents=[],behavior_constraints=[]),
                        dimensions={n:dict(value=.1 if n in ('risk','urgency','interruption_cost') else .9,reason='Synthetic judgment')
                            for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})])
                    if mode.startswith('reading-assessment'):
                        assert 'reading_assessments' in kw['messages'][0]['content']
                        value['reading_assessments']=[dict(item_id=data['tentative_discovery_tasks'][0]['item_id'],
                            status='partial',findings=[dict(observation_event_id=e['observation_event_id'],
                                passage_id=e['summary_passages'][0]['passage_id'],
                                interpretation='The extract describes observations, not independent validation.')],
                            open_questions=['What independent evidence tests the claimed improvement?'])]
                        if mode=='reading-assessment-invalid':
                            value['reading_assessments'][0]['findings'][0]['passage_id']='NOT_AN_ADMITTED_PASSAGE'
                        if mode=='reading-assessment-missing':value.pop('reading_assessments')
                        if mode=='reading-assessment-recovery' and models.count('alive_opportunity_candidates')==1:
                            value['candidates']=[{}]
            elif task=='alive_deliberation':
                choices=json.loads(raw.split('\n',1)[1])
                value=dict(candidate_id=next(c['candidate_id'] for c in choices if c['candidate_id'].startswith('opportunity-candidate:')),rationale='Synthetic contribution')
            elif task=='alive_semantic_render':
                assert 'INTERNAL_GOAL' not in raw
                if mode.startswith('reading-assessment'):
                    assessment=data['expression_context']['reading_assessment']
                    if mode in ('reading-assessment-invalid','reading-assessment-missing'):
                        assert not assessment['entries'] and len(assessment['unassessed_questions'])==1
                        assert assessment['rejected_count']==int(mode=='reading-assessment-invalid')
                    else:
                        assert assessment['entries'][0]['status']=='partial'
                        assert 'INTERNAL_RESEARCH_QUESTION' in assessment['entries'][0]['question']
                    assert not assessment['agenda_completion_proven'] and not assessment['source_truth_proven']
                    assert 'unanswered question does not oblige' in kw['messages'][0]['content']
                else:assert 'INTERNAL_RESEARCH_QUESTION' not in raw
                if pressure or mode in ('primary-read','replay','private-followup','erase-group-after-final'):
                    assert 'PRIMARY_READ_EVIDENCE' in raw and 'DEEP_READ_EVIDENCE' in raw
                value='The museum describes observing without intervention: [conservation method]('+url+').'
            elif task=='alive_semantic_review':
                if mode not in ('page-failed','legacy-replay','unconsented-followup','historical-followup-replay'):
                    assert data['source_context']['semantic_source_contract']=='bounded-group-source-v1'
                    assert 'AND original source_context' in kw['messages'][0]['content']
                    if pressure or mode in ('primary-read','replay','private-followup','erase-group-after-final'):
                        assert 'PRIMARY_READ_EVIDENCE' in json.dumps(data['source_context'])
                value=dict(atom_reviews=[dict(atom_id=a['atom_id'],preserved=True,risks=[]) for a in data['meaning']['atoms']],
                    added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True)
            elif task=='alive_source_support':
                assert data['expression_binding']['assessment_mode']==('discovery-source-and-value-v2'
                    if mode in ('page-failed','legacy-replay','unconsented-followup','historical-followup-replay') else 'discovery-source-and-value-v3')
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
    baseline_memory_proposals=len(journal.read(event_type='memory.proposed'))
    async def allow(self,target):return target in (url,primary,*backgrounds)
    original_tools=CoreDiscoveryTools
    def bounded_tools(*args,**kw):return original_tools(*args,**kw,timeout_seconds=.03 if mode=='uncertain-read' else 2)
    with patch.dict(sys.modules,hermes_constants=NS(get_hermes_home=lambda:root)),patch.object(CoreDiscoveryTools,'allow_url',allow),patch(
            'alive_kernel.configured_discovery_cycle.CoreDiscoveryTools',side_effect=bounded_tools):
        runner=native()
        if mode=='legacy-replay':
            # Emulate an operation begun before the new durable research mode.
            # Reopen with the actual new code, not the patched historical mode.
            runner.preparation._research_enabled=lambda cycle:False
        if mode in ('historical-followup-replay','historical-invalid-followup'):
            runner.preparation._bundle_enabled=lambda cycle:False
            runner.preparation._citation_references_enabled=lambda cycle:False
        if mode in ('invalid-choice','revoked-choice','forgotten-choice','erased-choice','uncertain-read',
                    'revoked-followup','forgotten-followup','erased-followup','interrupted-followup','historical-invalid-followup'):
            try:await runner.step(parameters)
            except (HostDiscoveryError,NativeWorkerError,RuntimeError):pass
            else:raise AssertionError('invalid/revoked/uncertain discovery succeeded: '+mode+
                ' model_stages='+repr(models)+' tools='+repr([name for name,_ in tools]))
            assert not journal.read(event_type='autonomous.host.closed')
            failure=journal.read(event_type='autonomous.host.failed')[-1].event
            # Public observation is still preparation; selection/page reasoning
            # is now deferred inside cognition after reconciliation/wait checks.
            assert failure.payload['phase']=='cognition'
            assert failure.payload['failure_class'] in ('HostDiscoveryError','HostReadUncertainError','RuntimeError')
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
            if mode=='historical-invalid-followup':
                assert not journal.read(event_type='discovery.citation_selection_opened')
        else:
            if mode in ('replay','legacy-replay','historical-followup-replay'):
                try:await runner.step(parameters)
                except RuntimeError:pass
                else:raise AssertionError('synthetic interruption did not occur')
                before=(len(tools),len(models));upgraded=preparation()
                upgraded.record_reading_assessment=True
                runner=native(upgraded)
            result=await runner.step(parameters)
            if mode in ('replay','legacy-replay','historical-followup-replay'):
                assert (len(tools),len(models))==before
                assert not journal.read(event_type='discovery.reading_assessment_opened')
            assert result.disposition==('paused' if mode=='paused' else 'silence' if mode=='abstain' else 'shadow_selected')
            assert len(journal.read(event_type='autonomous.host.closed'))==1
            if mode=='paused':assert not tools and not models
            elif mode!='abstain':
                assert url in result.expression.text
                assert len(tools)==(3 if pressure or mode in ('primary-read','replay','followup-failed','private-followup','erase-group-after-final','historical-followup-replay','mixed-followup') else 2)
                assert models.count('alive_discovery_reading')==1
                assert models.count('alive_discovery_followup')==(0 if mode in ('page-failed','legacy-replay','unconsented-followup','reading-assessment-no-followup') else 1)
                assert models.count('alive_source_support')==1
                if mode in ('invented-followup','foreign-followup','malformed-followup','nonjson-followup','mixed-followup'):
                    rows=journal.read(event_type='discovery.reading_choice_completed')
                    retained=vault.resolve_json(rows[-1].event.payload['content']['content_id'],
                        expected_subject='user:test',expected_purpose='discovery.reading-choice',
                        expected_sensitivity=Sensitivity.PRIVATE)['choice']
                    assert retained['rejected_count']==1
                    assert retained['decision_status']==('selected' if mode=='mixed-followup' else 'invalid')
                    assert len(tools)==(3 if mode=='mixed-followup' else 2)
                if mode.startswith('reading-assessment'):
                    synth=runtime.preparation.expression.planning.synth
                    done=journal.read(event_type='opportunity.synthesis_completed')[-1]
                    before=len(models)
                    retained=synth.reading_assessment_context(subject='user:test',
                        receipt_event_id=done.event.event_id,clearance=Sensitivity.PRIVATE)
                    assert len(models)==before
                    if mode in ('reading-assessment-invalid','reading-assessment-missing'):
                        assert not retained['entries'] and len(retained['unassessed_item_ids'])==1
                    else:assert retained['entries'][0]['status']=='partial'
                    assert len(journal.read(event_type='memory.proposed'))==baseline_memory_proposals
                    try:synth.reading_assessment_context(subject='user:foreign',
                        receipt_event_id=done.event.event_id,clearance=Sensitivity.PRIVATE)
                    except ValueError:pass
                    else:raise AssertionError('foreign reading findings disclosed')
                    original=next(r for r in journal.read(event_type='discovery.opportunity_observed')
                        if 'DEEP_READ_EVIDENCE' in str(ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
                            observation_event_ids=(r.event.event_id,),limit=1)[0].content.get('summary','')))
                    vault.erase_item(original.event.payload['content']['content_id'])
                    try:synth.reading_assessment_context(subject='user:test',
                        receipt_event_id=done.event.event_id,clearance=Sensitivity.PRIVATE)
                    except ValueError:pass
                    else:raise AssertionError('erased source survived in reading findings')
                if mode=='fair-budget-pressure':
                    admitted=journal.read(event_type='opportunity.synthesis_started')[-1].event.payload
                    scan=admitted['source_scan']
                    assert set(scan['fair_pool_observation_ids'])-set(admitted['observation_event_ids'])
                    assert scan['next_sequence']<max(journal.get(i).sequence for i in scan['focus_observation_ids'])
                    assert runtime.preparation.expression.planning.synth._source_cursor('user:test',Sensitivity.PRIVATE)==scan['next_sequence']
                if mode=='primary-read':
                    closed=journal.read(event_type='discovery.host_read_completed')
                    receipt_ids=tuple(r.event.event_id for r in closed[1:])
                    opened=journal.read(event_type='autonomous.host.opened')[-1].event.payload['operation_id']
                    item='inquiry:'+vault.digest_json(dict(cycle=opened,subject='user:test'))[:40]
                    inquiries=runner.preparation.inquiries.read(subject='user:test',clearance=Sensitivity.PRIVATE,item_ids=(item,))
                    assert len(resolve_research_reads(ingestor,subject='user:test',clearance=Sensitivity.PRIVATE,
                        receipt_ids=receipt_ids,inquiries=inquiries))==2
                    original_active=ingestor.active_evidence;resolutions=[0]
                    if primary_url is not None:
                        # Fetch/citation retain the exact spelling; stored source
                        # identity normalizes only the shared URL identity rules.
                        assert ('web_extract',dict(urls=[primary],char_limit=6000)) in tools
                        canonical='https://example.invalid/Original-Observations?version=2'
                        retained=resolve_research_reads(ingestor,subject='user:test',clearance=Sensitivity.PRIVATE,
                            receipt_ids=receipt_ids,inquiries=inquiries)
                        assert canonical in {e.content['url'] for e in retained}
                        for other_url in (canonical.replace('Original','original'),
                                          canonical.replace('version=2','version=3'),
                                          canonical.replace('example.invalid','foreign.invalid')):
                            def changed_resource(**kw):
                                return tuple(replace(e,content={**e.content,'url':other_url})
                                    if e.content['url']==canonical else e for e in original_active(**kw))
                            with patch.object(ingestor,'active_evidence',side_effect=changed_resource):
                                try:resolve_research_reads(ingestor,subject='user:test',clearance=Sensitivity.PRIVATE,
                                    receipt_ids=receipt_ids,inquiries=inquiries)
                                except HostDiscoveryError:pass
                                else:raise AssertionError('different path/query/host admitted as the read resource')
                    def withdraw_during_resolution(**kw):
                        result=original_active(**kw);resolutions[0]+=1
                        return result[:-1] if resolutions[0]==3 else result
                    with patch.object(ingestor,'active_evidence',side_effect=withdraw_during_resolution):
                        try:resolve_research_reads(ingestor,subject='user:test',clearance=Sensitivity.PRIVATE,
                            receipt_ids=receipt_ids,inquiries=inquiries)
                        except HostDiscoveryError:pass
                        else:raise AssertionError('concurrent withdrawal silently reduced an atomic group')
                    assert resolutions[0]==3
                    for owner,ids,notes in (('user:foreign',receipt_ids,inquiries),
                            ('user:test',tuple(reversed(receipt_ids)),inquiries),
                            ('user:test',(closed[0].event.event_id,),inquiries),('user:test',receipt_ids,[])):
                        try:resolve_research_reads(ingestor,subject=owner,clearance=Sensitivity.PRIVATE,receipt_ids=ids,inquiries=notes)
                        except HostDiscoveryError:pass
                        else:raise AssertionError('foreign/reordered/search/unbound research receipt admitted')
                if mode=='erase-group-after-final':
                    candidate=journal.read(event_type='message.model_candidate')[-1].event.event_id
                    original=next(e for e in ingestor.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,
                        limit=32) if e.content['url']==primary)
                    vault.erase_item(journal.get(original.observation_event_id).event.payload['content']['content_id'])
                    assert runtime.preparation.expression.store.resolve_model_candidate(candidate) is None
                    # Historical fairness is metadata, not permission to decrypt
                    # a forgotten/erased research group into the next cycle.
                    runtime.preparation.expression.planning.synth._source_cursor('user:test',Sensitivity.PRIVATE)
                    fresh=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
                        actor='user:test',subject='user:test',payload=dict(synthetic=True)))
                    change=MemoryProposal(kind=MemoryKind.PREFERENCE,subject='user:test',predicate='profile.synthetic.changed',
                        value='An explicitly changed synthetic preference.',authority=MemoryAuthority.USER_EXPLICIT,
                        source_event_ids=(fresh.event.event_id,),confidence=1)
                    memory.apply(memory.append_proposal(change,actor='user:test'))
                    assert runtime.preparation.expression.planning.synth._source_cursor('user:test',Sensitivity.PRIVATE)==0
            else:assert len(tools)==1
        assert not journal.read(event_type='action.attempted')
        assert not journal.read(event_type='dispatch.externally_delivered')
        assert not runner.pending
    release.set()


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case',action='append',default=[],help='Run only named synthetic cases (not the full-suite marker).')
selected_cases=parser.parse_args().case
with tempfile.TemporaryDirectory(prefix='alive-configured-discovery-') as folder:
    modes=('budget-pressure',) if os.getenv('ALIVE_REPRODUCE_OLD_RECALL')=='1' else (
                 'share','reading-assessment','reading-assessment-no-followup','reading-assessment-budget-pressure','reading-assessment-invalid','reading-assessment-missing','reading-assessment-recovery','primary-read','private-followup','budget-pressure','fair-budget-pressure','erase-group-after-final','followup-failed','replay','legacy-replay','historical-followup-replay','unconsented-followup','page-failed','abstain','paused',
                 'invalid-choice','revoked-choice','forgotten-choice','erased-choice','uncertain-read',
                 'invented-followup','foreign-followup','mixed-followup','malformed-followup','nonjson-followup',
                 'revoked-followup','forgotten-followup','erased-followup','interrupted-followup','historical-invalid-followup')
    if selected_cases:
        if set(selected_cases)-set(modes):raise ValueError('unknown configured-discovery test case')
        modes=tuple(selected_cases)
    for mode in modes:
        print('CONFIGURED_DISCOVERY_CASE='+mode,flush=True)
        root=Path(folder)/mode;root.mkdir()
        with patch.dict(os.environ,HERMES_HOME=str(root),HERMES_ALIVE_SHARED_DIR=str(root/'runtime')):
            asyncio.run(exercise(root,mode))
    if not selected_cases and os.getenv('ALIVE_REPRODUCE_OLD_RECALL')!='1':
        root=Path(folder)/'canonical-resource-identity';root.mkdir()
        with patch.dict(os.environ,HERMES_HOME=str(root),HERMES_ALIVE_SHARED_DIR=str(root/'runtime')):
            asyncio.run(exercise(root,'primary-read',primary_url=
                'https://EXAMPLE.invalid:443/Original-Observations?utm_source=fixture&version=2#section'))
print('HERMES_ALIVE_CONFIGURED_DISCOVERY_CASE_OK' if selected_cases else 'HERMES_ALIVE_CONFIGURED_DISCOVERY_CYCLE_OK')
