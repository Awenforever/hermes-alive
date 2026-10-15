"""Actual configured models interpret synthetic feedback before shadow cognition."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ActionAuthority, AutonomyPolicyProjection, DiscoveryCandidate, DiscoveryOpportunityIngestor, PolicyContext, Sensitivity
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from probe_alive_live_feedback import prepare_case
import httpx


CASES=(dict(id='courtesy',sent='Synthetic share: a public bicycle-repair guide.',reply='谢谢，收到。'),
       dict(id='mixed',sent='Synthetic share: a long general summary of bicycle maintenance.',
            reply='这个题材我有兴趣，不过请先给具体做法和适用条件，不要空泛摘要。今天先别发，正在开会。'))


async def run(output, *, model_call=None):
    if model_call is None:
        from agent.auxiliary_client import async_call_llm
        model_call=async_call_llm
    root=Path(output)
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any(root.iterdir()): raise ValueError('assimilation probe requires empty private output')
    report=dict(scope='actual-model hypotheses and shadow cognition; all history/authority synthetic',
        logical_calls=0,http_requests=[],cases=[],finished=False,sends=0,
        semantic_quality_qualified=False,longitudinal_utility_qualified=False)
    def save():
        path=root/'report.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); path.chmod(0o600)
    previous=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    original=httpx.AsyncClient.send
    async def tracked(client,request,*args,**kwargs):
        if len(report['http_requests'])>=48: raise RuntimeError('assimilation HTTP-start bound exhausted')
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
    def family(model):
        name=model.casefold()
        return 'deepseek-family' if 'deepseek' in name else 'qwen-family' if 'qwen' in name else model
    httpx.AsyncClient.send=tracked
    try:
        for fixture in CASES:
            entry=dict(fixture=fixture,model_calls=[])
            report['cases'].append(entry); save()
            interpreter,subject,outcome=prepare_case(root/fixture['id'],fixture)
            journal=interpreter.journal
            runtime=AutonomousCycleRuntime(journal,content_vault=interpreter.vault)
            policy=AutonomyPolicyProjection(journal)
            current=policy.current(subject)
            if current is None or not current.enabled:
                policy.apply(policy.append_update(subject=subject,actor=subject,
                    expected_revision=current.revision if current else 0,enabled=True,
                    context=PolicyContext(can_interrupt=True),operation_id='synthetic-enable'))
            DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(
                source='public-listing-fixture',title='New practical bicycle demonstration',
                summary='A public listing describes a free guide demonstrating how to inspect bicycle '
                        'brake pads and when replacement may be appropriate. Availability is unverified.',
                url='https://example.invalid/brake-pad-demonstration',observed_at=datetime.now(timezone.utc)),subject=subject)
            before={kind:len(journal.read(event_type=kind)) for kind in
                ('memory.proposed','preference.observed','action.attempted','dispatch.started')}
            async def call(**kwargs):
                if report['logical_calls']>=16: raise RuntimeError('assimilation logical-call bound exhausted')
                report['logical_calls']+=1
                item=dict(task=kwargs.get('task'),messages=kwargs['messages'])
                entry['model_calls'].append(item); save()
                try:
                    result=await model_call(**kwargs)
                    item.update(actual_model=getattr(result,'model',None),raw_output=result.choices[0].message.content)
                    return result
                except Exception as error:
                    item['error_class']=type(error).__name__
                    raise
                finally: save()
            expression=dict(call=call,resolve_domain=lambda provider,model:family(model),
                resolve_grounding_domain=family,grounding=True,language='zh',authority=ActionAuthority.USER_DELEGATED)
            parameters=dict(subject=subject,operation_id='actual-assimilation-cycle',expression_parameters=expression,
                resolve_binding=lambda record:None,interpret_feedback=True,reconsider_after_seconds=1800,
                cognition_configuration_id='synthetic-assimilation-config')
            try:
                result=await runtime.cycle(**parameters)
                entry.update(disposition=result.disposition,
                    text=result.expression.text if result.expression is not None else None,
                    hypotheses=[v.to_prompt() for v in runtime.feedback.read(subject=subject,clearance=Sensitivity.PRIVATE)])
                operation=runtime.feedback.operation(subject,outcome)
                completed=journal.get(runtime.feedback.interpreter._prefix(subject,operation)+':completed')
                if completed is not None:
                    entry.update(accepted_signals=completed.event.payload['accepted_signal_count'],
                                 rejected_signals=completed.event.payload['rejected_signal_count'])
                if result.disposition=='silence':
                    attempted=[]
                    async def forbidden(**kwargs):
                        attempted.append(kwargs.get('task'))
                        raise AssertionError('unchanged assimilation repeated inference')
                    reopened=await AutonomousCycleRuntime(journal,content_vault=interpreter.vault).cycle(
                        **{**parameters,'operation_id':'unchanged-assimilation-cycle',
                           'expression_parameters':{**expression,'call':forbidden}})
                    entry.update(reopened_disposition=reopened.disposition,reopened_callback_attempts=len(attempted))
            except Exception as error:
                entry['error_class']=type(error).__name__
            entry['new_records']={kind:len(journal.read(event_type=kind))-count for kind,count in before.items()}
            assert not any(entry['new_records'].values())
            save()
        report['finished']=True
    finally:
        httpx.AsyncClient.send=original
        logging.disable(previous); save()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=asyncio.run(run(args.output))
    print(json.dumps(dict(logical_calls=result['logical_calls'],http_starts=len(result['http_requests']),
                          finished=result['finished'],sends=0)))
