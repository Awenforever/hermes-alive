"""Actual purpose assessment of fixed synthetic contrasts, not live generation."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal, EventEnvelope, ActionAuthority
from alive_kernel.agenda import AgendaProjection, AgendaProposal, AgendaItemKind, AgendaAuthority
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer
from alive_kernel.communication_purpose import CommunicationPurposeReviewer
import httpx


async def run(output, *, model_call=None):
    if model_call is None:
        from agent.auxiliary_client import async_call_llm
        model_call=async_call_llm
    root=Path(output); root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if any(root.iterdir()): raise ValueError('purpose probe requires empty private output')
    report=dict(scope='fixed synthetic proposal contrasts; only purpose reviews use actual models',
        logical_calls=0,http_starts=0,stages=[],sends=0,finished=False,semantic_quality_qualified=False)
    def save():
        file=root/'report.json'
        file.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); file.chmod(0o600)
    previous=logging.root.manager.disable; logging.disable(logging.CRITICAL)
    send=httpx.AsyncClient.send
    async def http(client,request,*args,**kwargs):
        if report['http_starts']>=16: raise RuntimeError('purpose HTTP bound exhausted')
        report['http_starts']+=1; save()
        return await send(client,request,*args,**kwargs)
    httpx.AsyncClient.send=http
    try:
        for name,request,contents,constraints,expected in (
            ('operational-recital','请提醒我核对实验记录，只提醒，不代填、不发邮件。',
                [('request','请核对实验记录。'),('caveat','我不会代填记录、不会发邮件，也没有替你检查完成。')],
                ['不代填记录、不发邮件'],'unsupported'),
            ('useful-reminder','请提醒我核对实验记录，只提醒，不代填、不发邮件。',
                [('request','请核对实验记录。')],['不代填记录、不发邮件'],'supported'),
            ('material-eligibility','请提醒我查看活动通知：活动仅限受邀人员，不对公众开放。不要替我报名。',
                [('request','请查看活动通知。'),('caveat','活动仅限受邀人员，不对公众开放。')],
                ['不替用户报名'],'supported'),
            ('hidden-eligibility','请提醒我查看活动通知：活动仅限受邀人员，不对公众开放。不要替我报名。',
                [('request','请查看活动通知。')],['仅限受邀人员，不对公众开放','不替用户报名'],'unsupported')):
            stage=dict(name=name,expected=expected,fixture_generation_calls=0)
            report['stages'].append(stage); save()
            journal=ExperienceJournal(root/name/'kernel.sqlite3'); subject='user:purpose-fixture'
            inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
                actor=subject,subject=subject,payload={'synthetic':True}))
            agenda=AgendaProjection(journal)
            proposed=agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.COMMITMENT,subject=subject,
                details={'request':request},source_event_ids=(inbound.event.event_id,),confidence=1,
                authority=AgendaAuthority.USER_EXPLICIT,due_at=datetime.now(timezone.utc)+timedelta(hours=1)),actor=subject)
            agenda.apply(proposed)
            plan=dict(version=1,recipient_goal='提醒用户处理其明确要求的事项',speech_act='remind',
                contents=[dict(kind=k,text=t) for k,t in contents],behavior_constraints=constraints)
            async def fixture(**kwargs):
                stage['fixture_generation_calls']+=1
                value=dict(candidates=[dict(agenda_item_id=proposed.event.payload['item_id'],kind='share',
                    text='\n'.join(t for _,t in contents),topic='synthetic contrast',communication_plan=plan,
                    dimensions={k:dict(value=.5,reason='synthetic') for k in (
                        'user_value','urgency','novelty','confidence','risk','interruption_cost')})])
                return SimpleNamespace(model='synthetic/fixture',choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(value,ensure_ascii=False)))])
            generated=await OpportunitySynthesizer(journal).run(subject=subject,operation_id='fixture',
                call=fixture,recipient_meaning=True,authority=ActionAuthority.NONE)
            assert len(generated.candidates)==1
            async def actual(**kwargs):
                if report['logical_calls']>=4: raise RuntimeError('purpose model bound exhausted')
                report['logical_calls']+=1; stage['messages']=kwargs['messages']; save()
                result=await model_call(**kwargs)
                stage['raw_output']=result.choices[0].message.content
                stage['actual_model']=result.model; save()
                return result
            try:
                result=await CommunicationPurposeReviewer(journal).run(subject=subject,
                    interpretation_id='fixture',candidate_id=generated.candidates[0].action.candidate_id,
                    operation_id='planning-purpose:fixture',call=actual,resolve_domain=lambda _: 'diagnostic',
                    require_independence=False)
                stage.update(verdict=result.verdict,expected_matched=result.verdict==expected)
            except Exception as error: stage['error_class']=type(error).__name__
            save()
        report['finished']=True
    finally:
        httpx.AsyncClient.send=send; logging.disable(previous); save()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    report=asyncio.run(run(parser.parse_args().output))
    print(json.dumps({k:report[k] for k in ('logical_calls','http_starts','finished','sends')}))
