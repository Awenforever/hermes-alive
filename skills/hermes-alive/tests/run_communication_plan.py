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
from alive_kernel.communication_plan import validate_communication_plan, plan_atoms, expression_context
from alive_kernel.cognition_opportunities import CognitionOpportunityReader
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.events import Sensitivity, _freeze_json
from alive_kernel.discovery_opportunities import OpportunityEvidence
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer
from alive_kernel.deliberation import ActionAuthority
from alive_kernel.deliberation import PolicyContext
from alive_kernel.planning_runtime import PlanningRuntime, PlanningRuntimeError
from alive_kernel.events import EventEnvelope
from alive_kernel.agenda import AgendaProjection, AgendaProposal, AgendaItemKind, AgendaAuthority
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
        except PlanningRuntimeError as error:
            assert 'malformed proposals' in str(error)
        else: raise AssertionError('malformed plan became qualified silence')
    assert calls==['alive_opportunity_candidates']


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


def main():
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
    print('HERMES_ALIVE_COMMUNICATION_PLAN_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
