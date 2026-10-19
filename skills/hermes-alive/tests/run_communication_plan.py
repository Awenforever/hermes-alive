#!/usr/bin/env python3
"""Recipient meaning boundaries; structural tests are not semantic quality proof."""
from copy import deepcopy
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.communication_plan import validate_communication_plan, plan_atoms, expression_context, communication_situation
from alive_kernel.cognition_opportunities import CognitionOpportunityReader
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.events import Sensitivity, _freeze_json, _thaw_json
from alive_kernel.discovery_opportunities import OpportunityEvidence
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer,OpportunitySynthesisError
from alive_kernel.deliberation import ActionAuthority
from alive_kernel.deliberation import PolicyContext
from alive_kernel.planning_runtime import PlanningRuntime, PlanningRuntimeError
from alive_kernel.events import EventEnvelope
from alive_kernel.agenda import AgendaProjection, AgendaProposal, AgendaItemKind, AgendaAuthority
from alive_kernel.discovery_opportunities import DiscoveryOpportunityIngestor,DiscoveryCandidate
from alive_kernel.deliberation_synthesis import DeliberationSynthesizer,DeliberationContextChanged
from alive_kernel.cognition_cycle import CognitionCycleCoordinator
from types import SimpleNamespace


async def rejected_plan(root):
    journal=ExperienceJournal(root/'malformed.sqlite3'); subject='user:synthetic'
    source=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=subject,subject=subject,payload={'synthetic':True}))
    agenda=AgendaProjection(journal)
    item=agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.COMMITMENT,subject=subject,
        details={'request':'请提醒我核对记录'},source_event_ids=(source.event.event_id,),confidence=1,
        authority=AgendaAuthority.USER_EXPLICIT),actor=subject)
    agenda.apply(item)
    calls=[]
    async def call(**kwargs):
        calls.append(kwargs['task'])
        proposal=dict(agenda_item_id=item.event.payload['item_id'],kind='share',text='legacy only',topic='synthetic',
            dimensions={key:dict(value=.5,reason='synthetic') for key in (
                'user_value','urgency','novelty','confidence','risk','interruption_cost')})
        import json
        return SimpleNamespace(model='synthetic/fixture',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(dict(candidates=[proposal]))))])
    for _ in range(2):
        try:
            await PlanningRuntime(journal).run(operation_id='bad-plan',subject=subject,call=call,
                policy_context=PolicyContext(can_interrupt=True),recipient_meaning=True)
        except (PlanningRuntimeError,OpportunitySynthesisError):
            pass
        else: raise AssertionError('malformed plan became qualified silence')
    assert calls==['alive_opportunity_candidates']*2


def temporal_boundaries(root):
    journal=ExperienceJournal(root/'timing.sqlite3'); owner='user:timing'
    event=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor=owner,subject=owner,payload={'synthetic':True}))
    agenda=AgendaProjection(journal); now=datetime.now(timezone.utc)
    for item_id,available in (('within-window',None),('not-yet-ready',now+timedelta(hours=1))):
        proposal=agenda.append_proposal(AgendaProposal(item_id=item_id,kind=AgendaItemKind.COMMITMENT,
            subject=owner,details={'request':'synthetic timing'},source_event_ids=(event.event.event_id,),
            confidence=1,authority=AgendaAuthority.USER_EXPLICIT,available_at=available,
            due_at=now+timedelta(hours=2)),actor=owner)
        agenda.apply(proposal)
    values=CognitionOpportunityReader(journal).active_evidence(subject=owner,clearance=Sensitivity.PRIVATE)
    assert len(values)==1 and values[0].agenda_item_id=='within-window'
    bounds=json.loads(values[0].content['summary'])['temporal_bounds']
    assert bounds['not_before'] is None and datetime.fromisoformat(bounds['target_deadline'])>now


async def selected_meaning(root,modern):
    """Select the reviewed plan, never let a polished illustrative draft mask it."""
    root=root/('modern' if modern else 'legacy')
    journal=ExperienceJournal(root/'experience.sqlite3')
    owner='user:synthetic'; reader=DiscoveryOpportunityIngestor(journal)
    source=reader.ingest(DiscoveryCandidate(source='synthetic',title='Synthetic learning resource',
        summary='A public learning resource, eligibility unknown.',url='https://example.invalid/learning',
        observed_at=datetime.now(timezone.utc)),subject=owner)
    plan=dict(version=2,recipient_goal='Explain the known participation limit',speech_act='inform',
        contents=[dict(kind='caveat',text='PRIVATE_ACTUAL_MEANING: eligibility is unknown.')],
        behavior_constraints=[])
    async def generate(**kwargs):
        proposal=dict(agenda_item_id=source.agenda_item_id,kind='share',
            text='PRIVATE_ILLUSTRATIVE_DRAFT: everyone can attend.',topic='synthetic',
            dimensions={k:dict(value=.5,reason='synthetic') for k in (
                'user_value','urgency','novelty','confidence','risk','interruption_cost')})
        if modern:
            proposal['communication_plan']=plan
            del proposal['text']
            assert 'Do NOT write a draft text' in kwargs['messages'][0]['content']
            assert len(kwargs['messages'][0]['content']) < 7000
            prompt=json.loads(kwargs['messages'][1]['content'])
            assert prompt['opportunities'][0]['communication_situation']==dict(
                kind='discovery_share',default_presentation='conversational_contribution',
                requested_detail='consult_explicit_context')
        return SimpleNamespace(model='synthetic/generator',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(dict(candidates=[proposal]))))])
    synth=OpportunitySynthesizer(journal,content_vault=reader.vault)
    generated=await synth.run(subject=owner,operation_id='interpret',call=generate,recipient_meaning=modern)
    candidate=generated.candidates[0]
    if modern:
        assert candidate.content['recipient_intent_version']==1
        assert 'operation' not in candidate.content
        from alive_kernel.action_contract import parse_action_contract,ActionContractError
        try: parse_action_contract(dict(candidate.content),capability='hermes.channel.send')
        except ActionContractError: pass
        else: raise AssertionError('internal meaning admitted as a channel contract')
        from alive_kernel.opportunity_expression import OpportunityExpressionStore
    selector=DeliberationSynthesizer(journal,content_vault=reader.vault)
    try:
        selector.validate_candidate_sources((candidate.action,),{candidate.action.content_id:candidate.content},
            'user:foreign',Sensitivity.PRIVATE)
    except DeliberationContextChanged: pass
    else: raise AssertionError('foreign owner resolved a recipient plan')
    calls=[]
    async def choose(**kwargs):
        calls.append(kwargs)
        items=json.loads(kwargs['messages'][1]['content'].split('\n',1)[-1])
        actual=next(item for item in items if item['candidate_id']==candidate.action.candidate_id)
        if modern:
            assert actual['content']=={'communication_plan':plan}
            assert 'PRIVATE_ILLUSTRATIVE_DRAFT' not in kwargs['messages'][1]['content']
        else:
            assert actual['content']==dict(candidate.content)
        return SimpleNamespace(model='synthetic/selector',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(dict(candidate_id=candidate.action.candidate_id,
                rationale='synthetic contribution, not a real quality judgment'))))])
    coordinator=CognitionCycleCoordinator(journal,content_vault=reader.vault)
    selected=await coordinator.plan_with_model(cycle_id='meaning',subject=owner,candidates=generated.candidates,
        policy_context=PolicyContext(can_interrupt=True),call=choose)
    assert len(calls)==1 and selected.selection_event_id
    # Prompt-only view: retained frame/action still equals its original contract.
    stored=coordinator.deliberation.inspect(selected.frame_event_id.removeprefix('deliberation.frame:'),
        clearance=Sensitivity.PRIVATE)
    assert _thaw_json(dict(stored.candidate_contents)[candidate.action.content_id])==_thaw_json(candidate.content)
    assert synth.load_completed(subject=owner,operation_id='interpret')==generated
    if modern:
        meaning=OpportunityExpressionStore(journal,content_vault=reader.vault).define_for_selection(
            selection_event_id=selected.selection_event_id,subject=owner)
        assert meaning.event.event_type=='message.meaning_defined'
        assert 'text' not in synth.retained_proposal(receipt_event_id=generated.receipt_event_id,
            candidate_id=candidate.action.candidate_id,subject=owner,clearance=Sensitivity.PRIVATE)
    assert synth.requires_expression(receipt_event_id=generated.receipt_event_id,
        subject=owner,clearance=Sensitivity.PRIVATE) is modern
    from alive_kernel.source_support import SourceSupportReviewer
    snapshot,_=SourceSupportReviewer(journal,content_vault=reader.vault).snapshot(
        subject=owner,interpretation_id='interpret',candidate_id=candidate.action.candidate_id)
    if modern:
        assert snapshot['candidate']['communication_plan']==plan
        assert snapshot['communication_situation']==dict(kind='discovery_share',
            default_presentation='conversational_contribution',requested_detail='consult_explicit_context')
        assert 'text' not in snapshot['candidate']
        assert 'PRIVATE_ILLUSTRATIVE_DRAFT' not in json.dumps(snapshot)
    else:
        assert 'PRIVATE_ILLUSTRATIVE_DRAFT' in snapshot['candidate']['text']
    selector.validate_selection_sources(selected.selection_event_id,owner=owner,sensitivity=Sensitivity.PRIVATE)
    if modern:
        try:
            selector.validate_selection_sources(selected.selection_event_id,owner=owner,
                sensitivity=Sensitivity.PRIVATE,execution=True)
        except DeliberationContextChanged as error:
            assert 'requires a validated final expression' in str(error)
        else: raise AssertionError('internal recipient intent admitted as executable draft')
    else:
        selector.validate_selection_sources(selected.selection_event_id,owner=owner,
            sensitivity=Sensitivity.PRIVATE,execution=True)
    # Supplied IDs still require independent exact-expression verification in the
    # authorizer/outbox; this provenance check only establishes content mode.
    selector.validate_selection_sources(selected.selection_event_id,owner=owner,
        sensitivity=Sensitivity.PRIVATE,execution=True,expression_event_id='expression:synthetic')
    from alive_kernel.action_authorization import SendTimeAuthorizer
    authorizer=SendTimeAuthorizer(journal,content_vault=reader.vault)
    decision=authorizer.evaluate(selection_event_id=selected.selection_event_id,subject=owner,
        capability='hermes.channel.send',operation_id='no-expression')
    assert not decision.authorized
    assert ('generated_inputs_not_current' in decision.reasons) is modern
    replay=authorizer.evaluate(selection_event_id=selected.selection_event_id,subject=owner,
        capability='hermes.channel.send',operation_id='no-expression')
    assert replay.authorized is False
    forged=authorizer.evaluate(selection_event_id=selected.selection_event_id,subject=owner,
        capability='hermes.channel.send',operation_id='fake-expression',
        expression_event_id='expression:synthetic')
    assert not forged.authorized and 'exact_expression_confirmation_required' in forged.reasons
    from alive_kernel.dispatch_outbox import DispatchOutbox,DispatchOutboxError
    outbox=DispatchOutbox(journal,content_vault=reader.vault)
    authorization=journal.get(decision.event_id)
    if modern:
        try: outbox._validate_selection_inputs(authorization)
        except DispatchOutboxError: pass
        else: raise AssertionError('dispatch accepted an internal recipient intent')
    else: outbox._validate_selection_inputs(authorization)
    for path in root.glob('*.sqlite3*'):
        assert b'PRIVATE_ACTUAL_MEANING' not in path.read_bytes()
        assert b'PRIVATE_ILLUSTRATIVE_DRAFT' not in path.read_bytes()


def main():
    assert communication_situation('commitment')==dict(kind='admitted_commitment',detail_from_original_request=True)
    assert communication_situation('unknown')==dict(kind='unclassified',requested_detail='unknown')
    for method,bundle in (
        (dict(recipient_execution='expression-required-v1',recipient_output='intent-only-v1',protocol='recipient-plan-v2'),
            dict(recipient_execution='expression-required-v1',recipient_output='intent-only-v1')),
        (dict(recipient_execution='expression-required-v1',recipient_output='intent-only-v1',protocol='recipient-plan-v3'),
            dict(recipient_execution='expression-required-v1')),
        (dict(recipient_output='intent-only-v1',protocol='recipient-plan-v3'),dict(recipient_output='intent-only-v1'))):
        start=SimpleNamespace(event=SimpleNamespace(payload=dict(recipient_meaning=True,interpreter_method=method)))
        try: OpportunitySynthesizer._validate_recipient_execution(start,bundle)
        except OpportunitySynthesisError: pass
        else: raise AssertionError('unbound draft-free output contract accepted')
    for mode,bundle_mode,meaning in ((None,'expression-required-v1',True),
            ('expression-required-v1',None,True),('future-mode','future-mode',True),
            ('expression-required-v1','expression-required-v1',False)):
        start=SimpleNamespace(event=SimpleNamespace(payload=dict(
            recipient_meaning=meaning,interpreter_method=dict(recipient_execution=mode))))
        try: OpportunitySynthesizer._validate_recipient_execution(start,dict(recipient_execution=bundle_mode))
        except OpportunitySynthesisError: pass
        else: raise AssertionError('unbound or unknown recipient execution mode accepted')
    plan = dict(version=1, recipient_goal='说明活动的适用范围', speech_act='inform', contents=[
        dict(kind='fact', text='这是受邀活动。'),
        dict(kind='negation', text='活动不向公众开放。', protected_literals=['不向公众开放'])],
        behavior_constraints=['不代替用户申请或登记'])
    assert validate_communication_plan(plan, action_kind='share') == plan
    atoms = plan_atoms(plan, evidence=('source:synthetic',))
    assert len(atoms) == 2 and atoms[1].protected_literals == ('不向公众开放',)
    assert all('代替' not in atom.text for atom in atoms)
    assert expression_context(plan)['authority_granted'] is False
    invalid = []
    for field, bad in (('version',True), ('recipient_goal','x'*513), ('speech_act','ask'),
                       ('behavior_constraints',[{'tool':'send'}]), ('contents',[])):
        value = deepcopy(plan); value[field] = bad; invalid.append(value)
    value = deepcopy(plan); value['contents'][1]['protected_literals'] = []; invalid.append(value)
    value = deepcopy(plan); value['contents'][0]['kind'] = 'proposed_content'; invalid.append(value)
    value = deepcopy(plan); value['contents'][0] = dict(kind='link',text='原文地址',
        protected_literals=['https://example.invalid/reference']); invalid.append(value)
    value = deepcopy(plan); value['contents'][0] = dict(kind='fact',text='公开的学习资料',
        protected_literals=['public learning resource']); invalid.append(value)
    for value in invalid:
        try: validate_communication_plan(value, action_kind='share')
        except (TypeError, ValueError): pass
        else: raise AssertionError('invalid plan accepted')
    with tempfile.TemporaryDirectory(prefix='alive-recipient-meaning-') as folder:
        synth = OpportunitySynthesizer(ExperienceJournal(Path(folder) / 'kernel.sqlite3'))
        evidence = (OpportunityEvidence('agenda:synthetic','source:synthetic',
            datetime.now(timezone.utc)+timedelta(hours=1),Sensitivity.PRIVATE,
            _freeze_json(dict(source='synthetic',title='invitation',url='',summary='受邀活动'))),)
        proposal = dict(agenda_item_id='agenda:synthetic',kind='share',text='旧格式草稿',topic='invitation',
            dimensions={key:dict(value=.5,reason='synthetic') for key in (
                'user_value','urgency','novelty','confidence','risk','interruption_cost')})
        args = (evidence,'synthetic','opportunity.synthesis:synthetic:completed',ActionAuthority.NONE)
        legacy = synth._candidates(dict(candidates=[proposal]),*args)
        assert len(legacy[0]) == 1 and legacy[2] == 0
        strict = synth._candidates(dict(candidates=[proposal]),*args,recipient_meaning=True)
        assert not strict[0] and strict[2] == 1
        good = {**proposal,'communication_plan':plan}
        bad = {**proposal,'communication_plan':invalid[-2]}
        mixed = synth._candidates(dict(candidates=[bad,good]),*args,recipient_meaning=True)
        assert len(mixed[0]) == 1 and mixed[2:] == (1,(1,))
        assert mixed[1][0]['communication_plan']['contents'][1]['kind'] == 'negation'
        asyncio.run(rejected_plan(Path(folder)))
        temporal_boundaries(Path(folder))
        asyncio.run(selected_meaning(Path(folder),True))
        asyncio.run(selected_meaning(Path(folder),False))
    print('HERMES_ALIVE_COMMUNICATION_PLAN_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
