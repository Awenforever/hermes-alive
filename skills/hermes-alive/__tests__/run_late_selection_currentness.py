"""Slow cognition is not an expired physical permit; synthetic review clock/IO."""
import asyncio,json,sys,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from dataclasses import replace
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'hooks'),str(Path(__file__).resolve().parent)]
from alive_kernel import ExperienceJournal,DiscoveryCandidate,DiscoveryOpportunityIngestor,PolicyContext,AutonomyPolicyProjection,ActionAuthority,EventEnvelope,Sensitivity
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from alive_kernel.source_support import SourceSupportReviewer
from alive_kernel_testkit import install_terminal_route
from run_discovery_authoring import proposal,response

async def exercise(root,*,historical=False,protected=False,window=False,review_seconds=0,supported=True,
                   window_seconds=600,selection_delay_seconds=360):
    journal=ExperienceJournal(root/'experience.sqlite3')
    source=DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic public',
        title='Synthetic observation memory',summary='The model can revisit past visual observations.'
            +(' Charges of 5 yuan begin on 2026-11-01.' if protected else ''),
        url='https://example.invalid/visual-memory'),subject='user:test')
    runtime=SendPreparationRuntime(journal)
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='synthetic-policy'))
    route=install_terminal_route(journal,subject='user:test',content_vault=runtime.vault)
    grant=ActionDelegationStore(journal).grant(subject='user:test',actor='user:test',
        policy_event_id=policy.current('user:test').event_id,route_binding_id=route,
        action_kinds=('share',),maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc)+timedelta(hours=1),operation_id='synthetic-grant',allow_natural_expression=True)
    calls=[];final_calls=[]
    plan=(dict(version=2,recipient_goal='Warn about the dated service charge.',speech_act='warn',
        contents=[dict(kind='fact',text='The model can revisit past visual observations.'),
            dict(kind='fact',text='Charges of 5 yuan begin on 2026-11-01.',
                 protected_literals=['5 yuan','2026-11-01'])],behavior_constraints=[])
        if protected else dict(version=3,recipient_goal='Share the concrete capability.',
            speech_act='share',contents=[],behavior_constraints=[]))
    async def call(**kw):
        task=kw['task'];calls.append(task)
        data=json.loads(kw['messages'][1]['content']) if task!='alive_deliberation' else None
        if kw.get('route_info') is not None:kw['route_info']['provider']='synthetic-provider'
        if task=='alive_opportunity_candidates':
            return response(proposal(source.agenda_item_id,plan))
        if task=='alive_deliberation':
            choices=json.loads(kw['messages'][1]['content'].split('\n',1)[1])
            return response(dict(candidate_id=next(c['candidate_id'] for c in choices
                if c['candidate_id'].startswith('opportunity-candidate:')),rationale='Synthetic useful choice.'))
        if task=='alive_semantic_render':return response('The model can revisit past visual observations. '
            +('Charges of 5 yuan begin on 2026-11-01. ' if protected else '')
            +'[Source](https://example.invalid/visual-memory)')
        if task=='alive_semantic_review':return response(dict(atom_reviews=[dict(atom_id=a['atom_id'],preserved=True,risks=[])
            for a in data['meaning']['atoms']],added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True))
        assert task=='alive_source_support'
        if 'expression_binding' in data:
            final_calls.append(task)
            assert ('review_as_of' in data) is not historical
            assert ('review_valid_until' in data) is window
            if window:
                assert 'throughout [review_as_of, review_valid_until]' in kw['messages'][0]['content']
            if protected:
                assert data['candidate']['communication_plan']==plan
                assert data['assessment_scope']['kind']=='final_source_and_recipient_purpose'
                assert 'protected recipient meaning' in kw['messages'][0]['content']
        final='expression_binding' in data
        return response(dict(verdict='unsupported' if final and not supported else 'supported',
            unsupported_claims=['Synthetic interval does not support recipient purpose.'] if final and not supported else [],
            uncertainties=[],reason='Synthetic source/value assessment.'))
    expressed=await runtime.expression.run(subject='user:test',operation_id='synthetic-expression',call=call,
        policy_context=policy.current('user:test').context,authority=ActionAuthority.USER_DELEGATED,
        recipient_meaning=True,grounding=True,require_independent_grounding=False,
        resolve_domain=lambda *args:'synthetic-family')
    selected=journal.get(expressed.planning.selection_event_id)
    later=selected.event.observed_at+timedelta(seconds=selection_delay_seconds)
    origin=expressed.planning.interpretation_event_id.removeprefix('opportunity.synthesis:').removesuffix(':completed')
    reviewer=ExpressionSourceSupportReviewer(journal,content_vault=runtime.vault)
    completed=later+timedelta(seconds=review_seconds)
    clocks=iter((later,completed))
    with patch.object(SourceSupportReviewer,'_assessment_now',lambda self:next(clocks)),patch.object(
            SourceSupportReviewer,'_review_clock_enabled',lambda self,data:not historical):
        receipt=await reviewer.run(subject='user:test',interpretation_id=origin,candidate_id=expressed.expression_event_id,
            operation_id='synthetic-final-value',call=call,resolve_domain=lambda *args:'synthetic-family',
            require_independence=False,timeout_seconds=600,discovery_window_seconds=window_seconds if window else None)
    witness=dict(review_event_id=receipt.event_id,interpretation_id=origin,require_independence=False)
    args=dict(selection_event_id=selected.event.event_id,subject='user:test',capability='hermes.channel.send',
        route_binding_id=route,delegation_event_id=grant.event.event_id,
        expression_event_id=expressed.expression_event_id,final_wording_witness=witness)
    def authorize(name,at=completed,**changes):return runtime.authorizer.evaluate(
        **{**args,'operation_id':name,'now':at,**changes})
    decision=authorize('synthetic-first')
    eligible=not historical and supported and review_seconds<(window_seconds if window else 300)
    assert decision.authorized is eligible,decision.reasons
    assert journal.get(selected.event.event_id)==selected,'fresh value review rewrote an old selection'
    if not eligible:
        assert ('selection_stale' in decision.reasons or 'final_wording_not_current' in decision.reasons),decision.reasons
    else:
        until=later+timedelta(seconds=window_seconds if window else 300)
        assert decision.valid_until==min(completed+timedelta(seconds=30),until)
        almost=authorize('synthetic-near-boundary',until-timedelta(seconds=10))
        assert almost.authorized and almost.valid_until==until
        expired=authorize('synthetic-first',completed+timedelta(seconds=31))
        assert not expired.authorized and 'permit_expired' in expired.reasons
        old=authorize('synthetic-old-review',until)
        assert not old.authorized and ('selection_stale' in old.reasons or
            'final_value_assessment_expired' in old.reasons)
        future=authorize('synthetic-future',completed-timedelta(seconds=1))
        assert not future.authorized and 'final_value_assessment_from_future' in future.reasons
        missing=authorize('synthetic-missing-final',final_wording_witness=None)
        assert not missing.authorized and ('selection_stale' if protected else 'final_wording_required') in missing.reasons
        undelegated=authorize('synthetic-no-delegation',delegation_event_id=None)
        assert not undelegated.authorized and 'user_delegation_unproven' in undelegated.reasons
        record=journal.get(receipt.event_id);start=journal.get(record.event.causation_id)
        alias='opportunity.source-support:synthetic-forged-clock'
        journal.append(replace(start.event,event_id=alias+':started',observed_at=later+timedelta(seconds=1)))
        journal.append(replace(record.event,event_id=alias+':completed',causation_id=alias+':started',observed_at=later+timedelta(seconds=1)))
        forged=authorize('synthetic-forged',completed+timedelta(seconds=2),final_wording_witness={**witness,'review_event_id':alias+':completed'})
        assert not forged.authorized and 'final_wording_not_current' in forged.reasons
        if window and window_seconds<600:
            alias='opportunity.source-support:synthetic-extended-window'
            payload={**dict(start.event.payload),'assessment_window_seconds':window_seconds+1}
            journal.append(replace(start.event,event_id=alias+':started',payload=payload))
            payload={**dict(record.event.payload),'assessment_window_seconds':window_seconds+1}
            journal.append(replace(record.event,event_id=alias+':completed',causation_id=alias+':started',payload=payload))
            widened=authorize('synthetic-extended-window',final_wording_witness={**witness,'review_event_id':alias+':completed'})
            assert not widened.authorized and 'final_wording_not_current' in widened.reasons
        journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
            actor='system:alive-configured-input',subject='user:other',payload={'raw_content_stored':False}))
        assert authorize('synthetic-other-owner').authorized
        journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
            actor='system:alive-configured-input',subject='user:test',payload={'raw_content_stored':False}))
        changed=authorize('synthetic-new-input')
        assert not changed.authorized and ('selection_stale' in changed.reasons or
            'final_wording_not_current' in changed.reasons)
        if window:
            cached=authorize('synthetic-first',completed+timedelta(seconds=1))
            assert not cached.authorized and 'final_wording_not_current' in cached.reasons
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.started')
    assert len(final_calls)==1

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-late-selection-') as d:
        for protected in (False,True):
            for historical in (False,True):
                print('LATE_SELECTION_CASE='+str((protected,historical)),flush=True)
                asyncio.run(exercise(Path(d)/str(protected)/str(historical),
                    historical=historical,protected=protected))
        for window,seconds,supported in ((False,360,True),(True,360,True),
                (True,601,True),(True,360,False)):
            print('LATE_SELECTION_INTERVAL_CASE='+str((window,seconds,supported)),flush=True)
            asyncio.run(exercise(Path(d)/('interval-'+str((window,seconds,supported))),
                window=window,review_seconds=seconds,supported=supported))
        print('LATE_SELECTION_INTERVAL_CASE=protected-discovery-warning',flush=True)
        asyncio.run(exercise(Path(d)/'protected-window',protected=True,window=True,review_seconds=360))
        print('LATE_SELECTION_INTERVAL_CASE=short-window-fresh-selection',flush=True)
        asyncio.run(exercise(Path(d)/'short-window',window=True,window_seconds=40,selection_delay_seconds=60))
    print('HERMES_ALIVE_LATE_SELECTION_CURRENTNESS_OK')
