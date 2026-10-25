"""Opt-in actual-model busy/wait/new-input shadow cycle; synthetic data only."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (AutonomyPolicyProjection, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    EventEnvelope, ExperienceJournal, MemoryAuthority, MemoryKind, MemoryProjection, MemoryProposal,
    PolicyContext, ActionAuthority)
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
import httpx


async def run(output, *, model_call=None):
    if model_call is None:
        from agent.auxiliary_client import async_call_llm
        model_call=async_call_llm
    root=Path(output)
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any(root.iterdir()):
        raise ValueError('temporal diagnostic requires empty private output')
    report=dict(scope='actual shadow cognition with synthetic sources and explicit context; no sending',
        logical_calls=0,http_requests=[],model_calls=[],stages=[],finished=False,sends=0,
        semantic_quality_qualified=False,longitudinal_utility_qualified=False)
    def save():
        path=root/'report.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        path.chmod(0o600)
    previous=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    original=httpx.AsyncClient.send
    async def tracked(client,request,*args,**kwargs):
        if len(report['http_requests'])>=48:
            raise RuntimeError('temporal diagnostic HTTP bound exhausted')
        item=dict(call=report['logical_calls'],host=request.url.host)
        report['http_requests'].append(item); save()
        try:
            result=await original(client,request,*args,**kwargs)
            item['status']=result.status_code
            return result
        except Exception as error:
            item['error_class']=type(error).__name__
            raise
        finally: save()
    async def call(**kwargs):
        if report['logical_calls']>=16:
            raise RuntimeError('temporal diagnostic logical-call bound exhausted')
        report['logical_calls']+=1
        item=dict(task=kwargs.get('task'),messages=kwargs['messages'])
        report['model_calls'].append(item); save()
        try:
            result=await model_call(**kwargs)
            item.update(actual_model=getattr(result,'model',None),raw_output=result.choices[0].message.content)
            return result
        except Exception as error:
            item['error_class']=type(error).__name__
            raise
        finally: save()
    def family(model):
        name=model.casefold()
        return 'deepseek-family' if 'deepseek' in name else 'qwen-family' if 'qwen' in name else model
    httpx.AsyncClient.send=tracked
    try:
        journal=ExperienceJournal(root/'kernel'/'experience.sqlite3')
        runtime=AutonomousCycleRuntime(journal)
        subject='user:temporal'
        policies=AutonomyPolicyProjection(journal)
        policies.apply(policies.append_update(subject=subject,actor=subject,expected_revision=0,
            enabled=True,context=PolicyContext(can_interrupt=True),operation_id='synthetic-enable'))
        DiscoveryOpportunityIngestor(journal,content_vault=runtime.preparation.vault).ingest(DiscoveryCandidate(
            source='public-listing-fixture',title='Vintage bicycle guide',
            summary='A public library listing describes a free online guide to vintage bicycle brake '
                    'adjustment and chain cleaning. Availability has not been independently verified.',
            url='https://example.invalid/vintage-bicycle-guide',observed_at=datetime.now(timezone.utc)),subject=subject)
        def statement(value, predicate, kind, *, supersedes_id=None, valid_until=None):
            source=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
                actor=subject,subject=subject,payload={'synthetic':True}))
            return MemoryProjection(journal).append_proposal(MemoryProposal(kind=kind,subject=subject,
                predicate=predicate,value=value,authority=MemoryAuthority.USER_EXPLICIT,
                source_event_ids=(source.event.event_id,),confidence=1,supersedes_id=supersedes_id,
                valid_until=valid_until),actor=subject)
        statement('I enjoy practical vintage bicycle maintenance guides. Useful unverified listings '
            'are welcome if clearly attributed; do not ask me to reconfirm this interest.',
            'profile.content_preferences',MemoryKind.PREFERENCE)
        busy=statement('我接下来45分钟要开会，这段时间请先不要给我分享新内容。只是现在忙，不是不感兴趣。',
            'context.current_availability',MemoryKind.FACT,valid_until=datetime.now(timezone.utc)+timedelta(minutes=45))
        expression=dict(call=call,resolve_domain=lambda provider,model:family(model),
            resolve_grounding_domain=family,grounding=True,authority=ActionAuthority.USER_DELEGATED,language='zh')
        def args(operation):
            return dict(subject=subject,operation_id=operation,expression_parameters=expression,
                resolve_binding=lambda record:None,reconsider_after_seconds=3600,
                cognition_configuration_id='synthetic-temporal-config')
        async def stage(name, parameters):
            item=dict(name=name)
            report['stages'].append(item); save()
            try:
                result=await runtime.cycle(**parameters)
                item.update(disposition=result.disposition,reconsideration_event_id=result.reconsideration_event_id)
                if result.expression is not None:
                    planning=result.expression.planning
                    item.update(text=result.expression.text,grounding_reviews=planning.grounding_reviews)
                    timing=runtime.reconsideration.timing(planning,subject=subject)
                    item['timing']=timing
                waits=journal.read(event_type='cognition.wait_recorded')
                if waits:
                    item['latest_wait_until']=waits[-1].event.payload['valid_until']
            except Exception as error:
                item['error_class']=type(error).__name__
            item['calls_so_far']=report['logical_calls']; save()
        before_memories=len(journal.read(event_type='memory.proposed'))
        await stage('busy',args('actual-busy'))
        reopened=AutonomousCycleRuntime(ExperienceJournal(journal.path))
        runtime=reopened
        forbidden_calls=[]
        async def forbidden(**kwargs):
            forbidden_calls.append(kwargs.get('task'))
            raise AssertionError('unchanged waiting attempted additional inference')
        await stage('unchanged-after-restart',{**args('actual-unchanged'),
            'expression_parameters':{**expression,'call':forbidden}})
        report['unchanged_provider_callback_attempts']=len(forbidden_calls)
        report['autonomous_memory_writes_while_busy']=len(journal.read(event_type='memory.proposed'))-before_memories
        statement('会议提前结束了，我现在有空，可以分享刚才提到的自行车保养资料。',
            'context.current_availability',MemoryKind.FACT,supersedes_id=busy.event.payload['proposal_id'],
            valid_until=datetime.now(timezone.utc)+timedelta(hours=1))
        await stage('new-user-availability',args('actual-new-availability'))
        assert not journal.read(event_type='action.attempted') and not journal.read(event_type='dispatch.started')
        assert not journal.read(event_type='preference.observed')
        report['finished']=True
    finally:
        httpx.AsyncClient.send=original
        logging.disable(previous)
        save()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=asyncio.run(run(args.output))
    print(json.dumps(dict(logical_calls=result['logical_calls'],http_starts=len(result['http_requests']),
                          finished=result['finished'],sends=0)))
