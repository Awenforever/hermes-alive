#!/usr/bin/env python3
"""Commitment-only planning/expression/preparation and no-spend empty agenda."""
import asyncio
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import hashlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ActionAuthority, AutonomyPolicyProjection, ExperienceJournal,
    EventEnvelope, OpportunitySynthesizer, OpportunitySynthesisError, PolicyContext, Sensitivity)
from alive_kernel.agenda import AgendaProjection, AgendaProposal, AgendaAuthority, AgendaItemKind, AgendaState
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel_testkit import install_terminal_route, authenticated_dispatch_receipt
from alive_kernel.outcomes import OutcomeKind
from alive_kernel.delivered_history import DeliveredHistoryStore, DeliveredHistoryError
from alive_kernel.communication_plan import validate_communication_plan
from alive_kernel.semantic_rendering import SemanticAtomKind
from alive_kernel.source_support import SourceSupportReviewer
from alive_kernel.communication_purpose import CommunicationPurposeReviewer


def reply(value,model='synthetic/drafter'):
    return SimpleNamespace(model=model,choices=[SimpleNamespace(message=SimpleNamespace(
        content=value if isinstance(value,str) else json.dumps(value)))])


def statement(journal,owner='user:test'):
    return journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=owner,subject=owner,payload={'synthetic':True}))


def commitment(journal,*,owner='user:test',model=False,details=None):
    agenda=AgendaProjection(journal)
    source=statement(journal,owner)
    proposal=agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.COMMITMENT,subject=owner,
        details=details or {'task':'核对实验记录','constraint':'只提醒，不代为提交'},
        authority=AgendaAuthority.MODEL_PROPOSAL if model else AgendaAuthority.USER_EXPLICIT,
        source_event_ids=(source.event.event_id,),confidence=1,due_at=datetime.now(timezone.utc)+timedelta(hours=1)),
        actor='model:synthetic' if model else owner)
    agenda.apply(proposal)
    return agenda,proposal


def transition(journal,agenda,proposal,state):
    source=statement(journal,proposal.event.subject)
    changed=agenda.append_transition(proposal.event.payload['item_id'],state,actor=proposal.event.subject,
        authority=AgendaAuthority.USER_EXPLICIT,source_event_id=source.event.event_id,reason='synthetic user update')
    assert agenda.apply(changed).outcome=='transitioned'


async def test(root, *, recipient_meaning=False, purpose_repair=False, plan_version=1):
    journal=ExperienceJournal(root/'main'/'kernel.sqlite3')
    synth=OpportunitySynthesizer(journal)
    forbidden_calls=[]
    async def forbidden(**kwargs):
        forbidden_calls.append(kwargs)
        raise AssertionError('empty or reopened context requested inference')
    empty=await synth.run(subject='user:test',operation_id='empty',call=forbidden)
    assert not empty.candidates and empty.actual_model=='system/alive-no-current-material'
    assert synth.load_completed(subject='user:test',operation_id='empty')==empty
    idle_method=journal.get('opportunity.synthesis:empty:started').event.payload['interpreter_method']
    assert idle_method['kind']=='system_no_material' and idle_method['system_prompt_sha256'] is None
    policies=AutonomyPolicyProjection(journal)
    policies.apply(policies.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable'))
    runtime=AutonomousCycleRuntime(journal)
    params=dict(subject='user:test',expression_parameters=dict(call=forbidden,resolve_domain=lambda provider,model:model),
        resolve_binding=lambda record:None,reconsider_after_seconds=300,cognition_configuration_id='commitment-fixture')
    assert (await runtime.cycle(operation_id='empty-cycle',**params)).disposition=='silence'
    assert (await runtime.cycle(operation_id='empty-wait',**params)).disposition=='waiting_for_change'
    assert not forbidden_calls
    agenda,proposal=commitment(journal,details={'task':'核对实验记录','constraint':'只提醒，不代为提交',
                                              'status':'尚未核对'})
    try: synth.load_completed(subject='user:test',operation_id='empty')
    except OpportunitySynthesisError: pass
    else: raise AssertionError('new commitment did not invalidate empty material')
    evidence=synth.reader.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE)
    assert len(evidence)==1 and evidence[0].content['origin_kind']=='commitment' and evidence[0].content['url']==''
    calls=[]
    purpose_attempts=[]
    async def model(**kwargs):
        task=kwargs['task']; calls.append(task)
        if task=='alive_opportunity_candidates':
            current_start=journal.read(event_type='opportunity.synthesis_started')[-1]
            method=current_start.event.payload['interpreter_method']
            assert method['kind']=='model_prompt'
            assert method['protocol']==('recipient-plan-v3' if recipient_meaning else 'legacy-draft-v1')
            if recipient_meaning:
                assert method['recipient_output']=='intent-only-v1'
                assert method['recipient_execution']=='expression-required-v1'
            assert method['system_prompt_sha256']==hashlib.sha256(kwargs['messages'][0]['content'].encode()).hexdigest()
            assert method['requested_model']==kwargs.get('model')
            item=json.loads(kwargs['messages'][1]['content'])['opportunities'][0]
            generation = json.loads(kwargs['messages'][1]['content'])
            if purpose_repair and generation['corrective_reviews']:
                assert generation['corrective_reviews'][0]['critique']['reason']=='synthetic-purpose-mismatch'
            assert item['origin_kind']=='commitment' and item['url']==''
            assert json.loads(item['summary_excerpt'])['commitment']['constraint']=='只提醒，不代为提交'
            bounds=json.loads(item['summary_excerpt'])['temporal_bounds']
            assert bounds['not_before'] is None
            assert bounds['target_deadline']==json.loads(item['summary_excerpt'])['due_at']
            proposed = dict(agenda_item_id=item['agenda_item_id'],kind='share',
                text='提醒你核对实验记录；我不会代为提交，也没有将事项标为完成。',topic='explicit commitment',
                dimensions={name:dict(value=.1 if name in ('risk','interruption_cost') else .8,reason='synthetic')
                    for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})
            if recipient_meaning:
                due = json.loads(item['summary_excerpt'])['due_at']
                proposed['communication_plan'] = dict(version=plan_version,
                    recipient_goal='帮助用户记得核对实验记录，不宣称代为处理',speech_act='remind',
                    contents=[dict(kind='request',text='请核对实验记录。',protected_literals=[]),
                        dict(kind='deadline',text='截止：'+due,protected_literals=[due])],
                    behavior_constraints=['只提醒，不代为提交','不能声称已替用户检查完成'])
                if plan_version==2:
                    proposed['communication_plan']['contents'].append(dict(kind='negation',text='记录尚未核对。'))
            return reply(dict(candidates=[proposed]))
        if task=='alive_source_support':
            kwargs['route_info']['provider']='synthetic-review-provider'
            data=json.loads(kwargs['messages'][1]['content'])
            assert data['evidence'][0]['provenance_metadata']['origin_kind']=='commitment'
            if recipient_meaning:
                assert data['candidate']['communication_plan']['speech_act']=='remind'
                assert datetime.fromisoformat(data['interpretation_as_of']).utcoffset() is not None
                assert data['time_anchor_is_not_delivery_time'] is True
            if data.get('assessment_kind')=='recipient-purpose-v2':
                assert data['assessment_scope']['kind']=='recipient_purpose'
                assert data['assessment_scope']['execution_authorization_evaluated'] is False
                assert 'text' not in data['candidate'] and data['candidate']['communication_plan']
                purpose_attempts.append(data)
                if purpose_repair and len(purpose_attempts)==1:
                    return reply(dict(verdict='unsupported',unsupported_claims=['synthetic purpose mismatch'],
                        uncertainties=[],reason='synthetic-purpose-mismatch'),'synthetic/reviewer')
            return reply(dict(verdict='supported',unsupported_claims=[],uncertainties=[],reason='synthetic review'),
                         'synthetic/reviewer')
        if task=='alive_deliberation':
            assert 'Host selection_as_of=' in kwargs['messages'][1]['content'].split('\n',1)[0]
            options=json.loads(kwargs['messages'][1]['content'].split('\n',1)[1])
            chosen=next(o['candidate_id'] for o in options if o['candidate_id'].startswith('opportunity-candidate:'))
            return reply(dict(candidate_id=chosen,rationale='synthetic'))
        if task=='alive_semantic_render':
            kwargs['route_info']['provider']='synthetic-render-provider'
            data=json.loads(kwargs['messages'][1]['content'])
            assert all(a['kind']!='link' for a in data['meaning']['atoms'])
            if recipient_meaning:
                assert data['meaning']['speech_act']=='remind'
                assert all(a['kind']!='proposed_content' for a in data['meaning']['atoms'])
                assert '我不会代为提交' not in json.dumps(data['meaning'],ensure_ascii=False)
                assert data['expression_context']['behavior_constraints']==['只提醒，不代为提交','不能声称已替用户检查完成']
            return reply('\n'.join(a['text'] for a in data['meaning']['atoms']),'synthetic/renderer')
        if task=='alive_semantic_review':
            kwargs['route_info']['provider']='synthetic-review-provider'
            data=json.loads(kwargs['messages'][1]['content'])
            return reply(dict(atom_reviews=[dict(atom_id=a['atom_id'],preserved=True,risks=[]) for a in data['meaning']['atoms']],
                added_claims_detected=False,speech_act_preserved=True,protected_literals_preserved=True),'synthetic/reviewer')
        raise AssertionError(task)
    expression=dict(call=model,resolve_domain=lambda provider,model:model,resolve_grounding_domain=lambda model:model,
        grounding=True,authority=ActionAuthority.USER_DELEGATED,language='zh',recipient_meaning=recipient_meaning)
    selected=await runtime.cycle(subject='user:test',operation_id='reminder',expression_parameters=expression,
        resolve_binding=lambda record:None)
    assert selected.disposition=='shadow_selected' and 'http' not in selected.expression.text
    if recipient_meaning:
        assert selected.expression.text.startswith('请核对实验记录。')
        assert '我不会代为提交' not in selected.expression.text
        meaning = runtime.preparation.expression.store.meanings.resolve(
            journal.get(selected.expression.expression_event_id).event.payload['meaning_event_id'])
        assert any(a.kind is SemanticAtomKind.DEADLINE for a in meaning.atoms)
        if plan_version==2:
            assert any(a.kind is SemanticAtomKind.NEGATION and not a.protected_literals for a in meaning.atoms)
        purpose_event=next(event for _,verdict,event in selected.expression.planning.grounding_reviews
            if 'planning-purpose:' in event and verdict=='supported')
        start=journal.get(journal.get(purpose_event).event.causation_id)
        origin=start.event.causation_id.removeprefix('opportunity.synthesis:').removesuffix(':completed')
        review_args=dict(subject='user:test',interpretation_id=origin,
            candidate_id=journal.get(purpose_event).event.payload['candidate_id'],
            clearance=Sensitivity.PRIVATE,allow_correlated=True)
        assert CommunicationPurposeReviewer(journal).verify_current(purpose_event,**review_args)
        assert SourceSupportReviewer(journal).verify_current(purpose_event,**review_args) is None
        assert len(purpose_attempts)==(2 if purpose_repair else 1)
        # Same retained intent cannot silently change its original binding mode.
        try:
            await runtime.preparation.expression.run(subject='user:test',operation_id='reminder',
                policy_context=policies.current('user:test').context,
                **{**expression,'recipient_meaning':False,'call':forbidden})
        except ValueError: pass
        else: raise AssertionError('recipient meaning downgraded on recovery')
    route=install_terminal_route(journal,subject='user:test',content_vault=runtime.preparation.vault)
    grant=ActionDelegationStore(journal).grant(subject='user:test',actor='user:test',policy_event_id=policies.current('user:test').event_id,
        route_binding_id=route,action_kinds=('share',),maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=30),operation_id='grant',allow_natural_expression=True)
    prepared=await runtime.preparation.prepare(subject='user:test',operation_id='reminder',policy_context=policies.current('user:test').context,
        **expression,authorization_operation_id='prepare-reminder',route_binding_id=route,delegation_event_id=grant.event.event_id)
    assert prepared.attempt_event_id is not None and prepared.authorization.authorized, (
        prepared.quality_disposition, prepared.authorization.reasons if prepared.authorization else None)
    # Synthetic authenticated receipt only: no adapter, socket or real message.
    journal.append(EventEnvelope(event_type='retention.consent_changed',source='hermes.command.memory',
        actor='user:test',subject='user:test',sensitivity=Sensitivity.PRIVATE,
        payload={'enabled':True,'retention_days':7,'directions':['inbound','outbound'],'content_sensitivity':'private'}))
    attempt=journal.get(prepared.attempt_event_id)
    receipt=authenticated_dispatch_receipt(journal,attempt,event_id='synthetic-commitment-delivery')
    delivered=runtime.preparation.outcomes.append_outcome(attempt_id=attempt.event.payload['attempt_id'],
        kind=OutcomeKind.DELIVERY_SUCCEEDED,subject='user:test',source_event_id=receipt.event_id,
        details={'synthetic':True},actor='system:test',outcome_id='synthetic-commitment-result')
    assert runtime.preparation.outcomes.apply(delivered).outcome=='recorded'
    history=DeliveredHistoryStore(journal,content_vault=runtime.preparation.vault)
    captured=history.capture(subject='user:test',delivery_outcome_event_id=delivered.event.event_id)
    assert any(d['vault']=='agenda' for d in captured.event.payload['dependencies'])
    transition(journal,agenda,proposal,AgendaState.COMPLETED)
    assert history.resolve(captured.event.event_id,subject='user:test')['text']==prepared.expression.text
    agenda.content_vault.erase_item(proposal.event.payload['content']['content_id'])
    try: history.resolve(captured.event.event_id,subject='user:test')
    except DeliveredHistoryError: pass
    else: raise AssertionError('erased commitment still exposed derived delivered text')
    count=len(calls)
    try:
        await runtime.preparation.expression.run(subject='user:test',operation_id='reminder',
            policy_context=policies.current('user:test').context,**{**expression,'call':forbidden})
    except ValueError: pass
    else: raise AssertionError('completed commitment still supported old reminder')
    assert (await runtime.cycle(operation_id='completed-idle',**params)).disposition=='silence'
    assert len(calls)==count and not forbidden_calls
    # Models cannot create a user obligation. Explicit adoption is a separate event.
    _,suggestion=commitment(journal,model=True)
    assert not synth.reader.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE)
    transition(journal,agenda,suggestion,AgendaState.ACTIVE)
    assert len(synth.reader.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE))==1
    transition(journal,agenda,suggestion,AgendaState.COMPLETED)
    # Completion during inference invalidates the old frame before any proposal persists.
    _,pending=commitment(journal)
    interrupted_calls=[]
    async def interrupted(**kwargs):
        interrupted_calls.append(kwargs)
        transition(journal,agenda,pending,AgendaState.COMPLETED)
        return reply(dict(candidates=[]))
    try: await synth.run(subject='user:test',operation_id='completion-race',call=interrupted)
    except OpportunitySynthesisError: pass
    else: raise AssertionError('completion during inference was missed')
    assert len(interrupted_calls)==1 and journal.get('opportunity.synthesis:completion-race:completed') is None
    assert len(journal.read(event_type='dispatch.started'))==1  # fixture above, not real IO

    # Corrupted owner projection cannot trigger access to another owner's body.
    foreign_journal=ExperienceJournal(root/'foreign'/'kernel.sqlite3')
    _,foreign=commitment(foreign_journal,owner='user:foreign')
    foreign_synth=OpportunitySynthesizer(foreign_journal)
    foreign_synth.reader.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE)
    with closing(foreign_journal._connect()) as connection:
        connection.execute('UPDATE agenda_items_v1 SET subject=? WHERE item_id=?',('user:test',foreign.event.payload['item_id']))
    with patch.object(foreign_synth.reader.commitment_vault,'resolve_json',side_effect=AssertionError('foreign commitment body read')):
        assert not foreign_synth.reader.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE)


for use_plan, repair_purpose, version in ((False,False,1),(True,False,1),(True,True,1),(True,False,2)):
    with tempfile.TemporaryDirectory(prefix='alive-commitment-cognition-') as folder:
        asyncio.run(test(Path(folder),recipient_meaning=use_plan,purpose_repair=repair_purpose,plan_version=version))
print('HERMES_ALIVE_COMMITMENT_COGNITION_OK')
