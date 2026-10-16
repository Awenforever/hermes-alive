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
from alive_kernel import (DiscoveryCandidate,DiscoveryOpportunityIngestor,EventEnvelope,
    MemoryProjection,MemoryProposal,MemoryKind,MemoryAuthority,Sensitivity)
from alive_kernel.feedback_context import FeedbackContextReader
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
    full,_=large.snapshot(subject=owner,outcome_event_id=oid)
    assert full['feedback_text'].endswith('Do not drop this final qualification.')


if __name__=='__main__':
    for source_days,feedback_days in ((30,29),(1,29),(30,1)):
        with tempfile.TemporaryDirectory(prefix='alive-feedback-context-') as directory:
            asyncio.run(test(Path(directory),source_days=source_days,feedback_days=feedback_days))
    print('HERMES_ALIVE_FEEDBACK_CONTEXT_OK')
