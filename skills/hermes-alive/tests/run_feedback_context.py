#!/usr/bin/env python3
"""Exact paired feedback reaches cognition without becoming a preference update."""
import asyncio
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (DiscoveryCandidate,DiscoveryOpportunityIngestor,EventEnvelope,OutcomeKind,
    MemoryProjection,MemoryProposal,MemoryKind,MemoryAuthority,Sensitivity)
from alive_kernel.feedback_context import FeedbackContextReader
from alive_kernel.feedback_synthesis import FeedbackSynthesisError
from alive_kernel.content_vault import ContentReference
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer,OpportunitySynthesisError
from probe_alive_live_feedback import prepare_case


async def test(root,*,source_days=30,feedback_days=29):
    case={'id':'literal','sent':'合成分享：公开修补演示。','reply':'谢谢，但我现在在开会，稍后再说；不是不喜欢这个主题。'}
    interpreter,subject,outcome_id=prepare_case(root/'main',case,feedback_retention_days=feedback_days)
    journal=interpreter.journal
    reader=FeedbackContextReader(journal,content_vault=interpreter.vault)
    def read(): return reader.read(subject=subject,clearance=Sensitivity.PRIVATE)
    context=read()
    assert len(context)==1 and context[0].delivered_text==case['sent'] and context[0].feedback_text==case['reply']
    assert case['reply'] not in repr(context[0]) and case['sent'] not in repr(context[0])
    with patch.object(reader.interpreter.vault,'resolve_json',side_effect=AssertionError('foreign body read')):
        assert not reader.read(subject='user:foreign',clearance=Sensitivity.PRIVATE)
    assert not reader.read(subject=subject,clearance=Sensitivity.PUBLIC)
    assert reader.read(subject=subject,clearance=Sensitivity.RESTRICTED)==context
    page=reader.catalog(subject=subject,clearance=Sensitivity.PRIVATE,item_limit=1)
    assert len(page['entries'])==1 and page['more_available']
    tail=reader.catalog(subject=subject,clearance=Sensitivity.PRIVATE,
        before_sequence=page['next_before_sequence'],item_limit=1)
    assert not tail['entries'] and not tail['more_available']
    assert page['entries'][0]['outcome_event_id']==outcome_id
    assert page['entries'][0]['complete_pair_required']
    assert not page['authority_granted']
    assert reader.resolve(subject=subject,clearance=Sensitivity.PRIVATE,
        outcome_event_ids=(outcome_id,))==context
    with patch.object(reader.interpreter.vault,'resolve_json',side_effect=AssertionError('mixed-owner body read')):
        try: reader.resolve(subject=subject,clearance=Sensitivity.PRIVATE,
            outcome_event_ids=(outcome_id,'outcome.record:missing'))
        except FeedbackSynthesisError: pass
        else: raise AssertionError('mixed references accepted')
    original=journal.get(outcome_id)
    # A copied outcome in a foreign owner envelope cannot expose paired text.
    from dataclasses import replace
    journal.append(replace(original.event,event_id='outcome.record:foreign',subject='user:foreign'))
    # Even another legitimate consenting owner cannot borrow this person's pair.
    journal.append(EventEnvelope(event_type='retention.consent_changed',source='hermes.command.memory',
        actor='user:foreign',subject='user:foreign',sensitivity=Sensitivity.PRIVATE,
        payload={'enabled':True,'retention_days':30,'directions':['inbound'],'content_sensitivity':'private'}))
    journal.append(EventEnvelope(event_type='consolidation.consent_changed',source='hermes.command.memory',
        actor='user:foreign',subject='user:foreign',sensitivity=Sensitivity.PRIVATE,payload={'enabled':True}))
    with patch.object(reader.interpreter.vault,'resolve_json',side_effect=AssertionError('copied-owner body read')):
        assert not reader.read(subject='user:foreign',clearance=Sensitivity.PRIVATE)
    memory_source=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=subject,subject=subject,payload={'synthetic':True}))
    MemoryProjection(journal).append_proposal(MemoryProposal(kind=MemoryKind.PREFERENCE,subject=subject,
        predicate='profile.content_preferences',value='合成明确偏好：欢迎修补技巧，但不要求频繁推送。',
        authority=MemoryAuthority.USER_EXPLICIT,source_event_ids=(memory_source.event.event_id,),confidence=1),actor=subject)
    observed=datetime.now(timezone.utc)
    DiscoveryOpportunityIngestor(journal,content_vault=interpreter.vault).ingest(DiscoveryCandidate(
        source='synthetic',title='Another repair method',summary='Synthetic new repair technique; no urgency.',
        url='https://example.invalid/new',observed_at=observed,expires_at=observed+timedelta(days=source_days)),subject=subject)
    before=tuple(journal.read(event_type='preference.observed'))
    memories=tuple(journal.read(event_type='memory.proposed'))
    synth=OpportunitySynthesizer(journal,content_vault=interpreter.vault)
    async def call(**kw):
        data=json.loads(kw['messages'][1]['content'])
        assert data['recent_feedback_context']==[c.to_prompt() for c in context]
        assert data['user_context'][0]['source_observations']==[{
            'event_id':memory_source.event.event_id,'observed_at':memory_source.event.observed_at.isoformat()}]
        value={'candidates':[{'agenda_item_id':data['opportunities'][0]['agenda_item_id'],
            'kind':'share','text':'Synthetic different repair method.','topic':'synthetic repair',
            'dimensions':{name:{'value':.2,'reason':'Synthetic model judgment.'} for name in
                ('user_value','urgency','novelty','confidence','interruption_cost','risk')}}]}
        return SimpleNamespace(model='synthetic/interpreter',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])
    generated=await synth.run(subject=subject,operation_id='literal-context',call=call)
    evidence=generated.candidates[0].action.dimensions.user_value.evidence_event_ids
    assert context[0].outcome_event_id in evidence and context[0].source_event_id in evidence
    assert generated.candidates[0].action.authority.value=='none'
    ref=ContentReference.from_event_payload(journal.get(generated.receipt_event_id).event.payload['content'])
    started=journal.get('opportunity.synthesis:literal-context:started').event
    as_of=datetime.fromisoformat(started.payload['interpretation_as_of'])
    assert ref.retention_until==min(as_of+timedelta(days=7),observed+timedelta(days=source_days),
        datetime.fromisoformat(context[0].retention_until))
    assert synth.load_completed(subject=subject,operation_id='literal-context')
    snapshot,_=interpreter.snapshot(subject=subject,outcome_event_id=outcome_id)
    async def erase_during_wait(**kw):
        response=await call(**kw)
        interpreter.vault.erase_item(snapshot['feedback_content_id'])
        return response
    try: await synth.run(subject=subject,operation_id='erase-in-flight',call=erase_during_wait)
    except OpportunitySynthesisError: pass
    else: raise AssertionError('erased feedback was accepted after model await')
    assert not read()
    assert not reader.catalog(subject=subject,clearance=Sensitivity.PRIVATE)['entries']
    try: reader.resolve(subject=subject,clearance=Sensitivity.PRIVATE,outcome_event_ids=(outcome_id,))
    except FeedbackSynthesisError: pass
    else: raise AssertionError('archive resolved erased feedback')
    try: synth.load_completed(subject=subject,operation_id='literal-context')
    except OpportunitySynthesisError: pass
    else: raise AssertionError('erased literal feedback remained usable on reopen')
    assert tuple(journal.read(event_type='preference.observed'))==before
    assert tuple(journal.read(event_type='memory.proposed'))==memories
    assert not journal.read(event_type='feedback.synthesis_started')
    assert not journal.read(event_type='dispatch.externally_started')
    # Independent fixture proves consent withdrawal and outcome-content erasure,
    # not merely absence caused by the first fixture's earlier erasure.
    other,owner,oid=prepare_case(root/'consent',{'id':'consent','sent':'Synthetic notice.','reply':'Thanks.'})
    second=FeedbackContextReader(other.journal,content_vault=other.vault)
    assert second.read(subject=owner,clearance=Sensitivity.PRIVATE)
    other.vault.erase_item(other.journal.get(oid).event.payload['content']['content_id'])
    assert not second.read(subject=owner,clearance=Sensitivity.PRIVATE)
    third,owner,oid=prepare_case(root/'withdraw',{'id':'withdraw','sent':'Synthetic notice.','reply':'Thanks.'})
    third_reader=FeedbackContextReader(third.journal,content_vault=third.vault)
    assert third_reader.read(subject=owner,clearance=Sensitivity.PRIVATE)
    third.journal.append(EventEnvelope(event_type='consolidation.consent_changed',source='hermes.command.memory',
        actor=owner,subject=owner,sensitivity=Sensitivity.PRIVATE,payload={'enabled':False}))
    with patch.object(third_reader.interpreter.vault,'resolve_json',side_effect=AssertionError('withdrawn body read')):
        assert not third_reader.read(subject=owner,clearance=Sensitivity.PRIVATE)
    large,owner,oid=prepare_case(root/'budget',{'id':'budget',
        'sent':'Synthetic notice: '+'A'*3500,'reply':'B'*3500+' Do not drop this final qualification.'})
    large_reader=FeedbackContextReader(large.journal,content_vault=large.vault)
    assert not large_reader.read(subject=owner,clearance=Sensitivity.PRIVATE)
    page=large_reader.catalog(subject=owner,clearance=Sensitivity.PRIVATE)
    assert page['entries'][0]['preview_truncated']
    exact=large_reader.resolve(subject=owner,clearance=Sensitivity.PRIVATE,outcome_event_ids=(oid,))
    assert exact[0].feedback_text.endswith('Do not drop this final qualification.')
    full,_=large.snapshot(subject=owner,outcome_event_id=oid)
    assert full['feedback_text'].endswith('Do not drop this final qualification.')


async def archive_test(root):
    """Old evidence beyond scan64 reaches interpretation and source review.

    All records and the model callback are synthetic. Explicit reference choice
    tests the consumer boundary, not the accuracy of an automatic recall model.
    """
    case={'id':'archive','sent':'Synthetic mixed research and promotion.',
        'reply':'Research is welcome; shopping promotions are not. This is not a request for more messages.'}
    interpreter,subject,first=prepare_case(root/'archive',case)
    journal,vault=interpreter.journal,interpreter.vault
    retention=journal.get('retention.consent:fixture')
    attempt=journal.get('action.attempt:attempt:'+subject)
    until=datetime.now(timezone.utc)+timedelta(days=29)
    for index in range(67):
        ref=vault.put_json(dict(text='Synthetic temporary meeting '+str(index),direction='inbound',
            may_be_truncated=False),subject=subject,purpose='conversation.inbound',
            sensitivity=Sensitivity.PRIVATE,retention_until=until,content_id='archive-input:'+str(index))
        inbound=journal.append(EventEnvelope(event_id='archive-input:'+str(index),event_type='conversation.inbound',
            source='synthetic-public-fixture',actor=subject,subject=subject,sensitivity=Sensitivity.PRIVATE,
            causation_id=attempt.event.event_id,payload=dict(erasable_content_stored=True,
                content_may_be_truncated=False,consent_event_id=retention.event.event_id,content=ref.to_event_payload())))
        outcome=interpreter.outcomes.append_outcome(attempt_id='attempt:'+subject,kind=OutcomeKind.USER_REPLIED,
            source_event_id=inbound.event.event_id,details=dict(classification='ordinary_reply',synthetic=True),
            actor=subject,subject=subject,outcome_id='archive-reply:'+str(index))
        assert interpreter.outcomes.apply(outcome).outcome=='recorded'
    reader=FeedbackContextReader(journal,content_vault=vault)
    original_resolve=vault.resolve_json
    def delivery_only(*args,**kwargs):
        assert kwargs.get('expected_purpose')!='outcome.user_replied', 'unrelated reply details decrypted'
        return original_resolve(*args,**kwargs)
    with patch.object(vault,'resolve_json',side_effect=delivery_only):
        assert interpreter.snapshot(subject=subject,outcome_event_id=first)[0]['feedback_text']==case['reply']
    recent=reader.read(subject=subject,clearance=Sensitivity.PRIVATE)
    assert len(recent)==3 and first not in [v.outcome_event_id for v in recent]
    cursor=None;ids=[];pages=0
    while True:
        page=reader.catalog(subject=subject,clearance=Sensitivity.PRIVATE,
            before_sequence=cursor,scan_limit=7,item_limit=3)
        pages+=1;ids.extend(v['outcome_event_id'] for v in page['entries'])
        assert pages<40
        if not page['more_available']:break
        next_cursor=page['next_before_sequence']
        assert cursor is None or next_cursor<cursor
        cursor=next_cursor
    assert len(ids)==len(set(ids))==68 and ids[-1]==first
    recalled=reader.context(subject=subject,clearance=Sensitivity.PRIVATE,recalled_ids=(first,))
    assert len(recalled)==4 and recalled[-1].feedback_text==case['reply']
    now=datetime.now(timezone.utc)
    DiscoveryOpportunityIngestor(journal,content_vault=vault).ingest(DiscoveryCandidate(
        source='synthetic',title='A public research finding',summary='Synthetic research, not a purchase.',
        url='https://example.invalid/archive',observed_at=now,expires_at=now+timedelta(days=1)),subject=subject)
    synth=OpportunitySynthesizer(journal,content_vault=vault)
    calls=[]
    async def call(**kw):
        data=json.loads(kw['messages'][1]['content']);calls.append(kw['task'])
        assert data['recent_feedback_context']==[v.to_prompt() for v in recalled]
        value={'candidates':[{'agenda_item_id':data['opportunities'][0]['agenda_item_id'],
            'kind':'share','text':'Synthetic research contribution.','topic':'synthetic research',
            'dimensions':{name:{'value':.2,'reason':'Synthetic controlled judgment.'} for name in
                ('user_value','urgency','novelty','confidence','interruption_cost','risk')}}]}
        return SimpleNamespace(model='synthetic/interpreter',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])
    result=await synth.run(subject=subject,operation_id='archive-context',call=call,
        recalled_feedback_event_ids=(first,))
    candidate=result.candidates[0].action
    assert first in candidate.dimensions.user_value.evidence_event_ids
    assert synth.load_completed(subject=subject,operation_id='archive-context')==result
    from alive_kernel.source_support import SourceSupportReviewer
    snapshot,_=SourceSupportReviewer(journal,content_vault=vault).snapshot(subject=subject,
        interpretation_id='archive-context',candidate_id=candidate.candidate_id)
    assert snapshot['recent_feedback_context']==[v.to_prompt() for v in recalled]
    assert len(calls)==1
    from alive_kernel.planning_runtime import PlanningRuntime,PlanningRuntimeError
    from alive_kernel import PolicyContext
    runtime=PlanningRuntime(journal,content_vault=vault)
    parameters=dict(operation_id='archive-planning',subject=subject,
        policy_context=PolicyContext(can_interrupt=False),call=call,recalled_feedback_event_ids=(first,))
    planned=await runtime.run(**parameters)
    assert planned.action_kind=='silence' and len(calls)==2
    async def forbidden(**_):raise AssertionError('reopened recall invoked a model')
    assert await runtime.run(**{**parameters,'call':forbidden})==planned
    try:await runtime.run(**{**parameters,'call':forbidden,'recalled_feedback_event_ids':()})
    except PlanningRuntimeError:pass
    else:raise AssertionError('planning reuse silently changed recall scope')
    original,_=interpreter.snapshot(subject=subject,outcome_event_id=first)
    async def erase_during_wait(**kw):
        response=await call(**kw)
        vault.erase_item(original['feedback_content_id'])
        return response
    try: await synth.run(subject=subject,operation_id='archive-erased',call=erase_during_wait,
        recalled_feedback_event_ids=(first,))
    except (OpportunitySynthesisError,FeedbackSynthesisError):pass
    else:raise AssertionError('recalled deleted feedback survived model wait')
    try:synth.load_completed(subject=subject,operation_id='archive-context')
    except (OpportunitySynthesisError,FeedbackSynthesisError):pass
    else:raise AssertionError('recalled deleted feedback survived restart')
    assert not journal.read(event_type='dispatch.externally_started')


if __name__=='__main__':
    for source_days,feedback_days in ((30,29),(1,29),(30,1)):
        with tempfile.TemporaryDirectory(prefix='alive-feedback-context-') as directory:
            asyncio.run(test(Path(directory),source_days=source_days,feedback_days=feedback_days))
    with tempfile.TemporaryDirectory(prefix='alive-feedback-archive-') as directory:
        asyncio.run(archive_test(Path(directory)))
    print('HERMES_ALIVE_FEEDBACK_CONTEXT_OK')
