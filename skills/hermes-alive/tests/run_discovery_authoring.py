"""Source-led discovery authorship, mandatory final gate, strict other purposes.

Actual encrypted planning/expression/authorization APIs, synthetic models/routes.
No network, real provider or channel sends. Not a recipient-quality round.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ExperienceJournal,DiscoveryCandidate,DiscoveryOpportunityIngestor,
    ActionAuthority,PolicyContext,AutonomyPolicyProjection,EventEnvelope,OpportunitySynthesizer,Sensitivity)
from alive_kernel.communication_plan import validate_communication_plan
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel.dispatch_outbox import DispatchOutbox,DispatchOutboxError
from alive_kernel.events import _thaw_json
from alive_kernel.semantic_review import SemanticReviewError
from alive_kernel_testkit import install_terminal_route
from alive_kernel.agenda import AgendaProjection,AgendaProposal,AgendaItemKind,AgendaAuthority
from alive_kernel.discovery_inquiry import DiscoveryInquiryContext


def brief():
    return dict(version=3,recipient_goal='PRIVATE_RESEARCH_GOAL: Ask the recipient to change their research method.',
        speech_act='share',contents=[],behavior_constraints=['PRIVATE_MODEL_CONSTRAINT: Frame this as a research assignment.'])


def response(value,model='synthetic/model'):
    return SimpleNamespace(model=model,choices=[SimpleNamespace(message=SimpleNamespace(
        content=value if isinstance(value,str) else json.dumps(value)))])


def proposal(item_id,plan):
    return dict(candidates=[dict(agenda_item_id=item_id,kind='share',topic='observation',communication_plan=plan,
        dimensions={n:dict(value=.1 if n in ('risk','urgency','interruption_cost') else .8,reason='synthetic judgment')
            for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')})])


async def exercise(root,mode,*,historical=False):
    journal=ExperienceJournal(root/'journal.sqlite3')
    ingestor=DiscoveryOpportunityIngestor(journal)
    source=ingestor.ingest(DiscoveryCandidate(source='synthetic public source',title='Observation design',
        url='https://example.invalid/design',summary='FAMILY_SPEC_OPTIONAL. The project describes continuing '
        'to observe when evidence is insufficient, rather than answering immediately.'),subject='user:test')
    interpreter=OpportunitySynthesizer(journal,content_vault=ingestor.vault)
    inquiries=DiscoveryInquiryContext(ingestor)
    inquiry=inquiries.remember(item_id='inquiry:private-research',subject='user:test',
        question='PRIVATE_READING_QUESTION: Should the recipient change their research method?',
        value_hypothesis='PRIVATE_VALUE_HYPOTHESIS: An internal research guess, not a recipient request.',
        source_event_ids=(source.observation_event_id,),model_actor='model:synthetic',
        expected_context_digest=inquiries.context_digest(subject='user:test'),
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))
    evidence=interpreter.reader.active_evidence(subject='user:test',clearance=Sensitivity.PRIVATE,limit=32)
    scope=dict(recipient_meaning=True,source_presentation='canonical_source_v1',
        as_of=datetime.now(timezone.utc),intent_only=True)
    check=(proposal(source.agenda_item_id,brief()),evidence,'scope-check',
           'opportunity.synthesis:scope-check:completed',ActionAuthority.USER_CONFIRMED)
    assert interpreter._structure_findings_v1(*check,**scope)
    assert not interpreter._structure_findings_v1(*check,**scope,allow_editorial_brief=True)
    for malformed in (None,[],True):
        assert interpreter._structure_findings_v1(
            proposal(source.agenda_item_id,malformed),*check[1:],**scope,allow_editorial_brief=True)
    calls=[]; semantic_calls=[]
    async def call(**kw):
        task=kw['task'];calls.append(task)
        data=json.loads(kw['messages'][1]['content']) if task!='alive_deliberation' else None
        if task=='alive_opportunity_candidates':
            assert data.get('original_evidence',data)['tentative_discovery_tasks']==[inquiry]
            if mode=='proposal-recovery' and calls.count(task)==1:
                return response(proposal(source.agenda_item_id,{**brief(),'contents':[{'kind':'claim','text':'invalid brief'}]}))
            return response(proposal(source.agenda_item_id,brief()))
        if task=='alive_deliberation':
            choices=json.loads(kw['messages'][1]['content'].split('\n',1)[1])
            return response(dict(candidate_id=next(c['candidate_id'] for c in choices
                if c['candidate_id'].startswith('opportunity-candidate:')),rationale='synthetic selected angle'))
        kw['route_info']['provider']='synthetic-provider'
        if task=='alive_semantic_render':
            assert data['expression_context']['method']=='discovery-source-authoring-v'+('1' if historical else '2')
            for marker in ('PRIVATE_RESEARCH_GOAL','PRIVATE_MODEL_CONSTRAINT','PRIVATE_READING_QUESTION','PRIVATE_VALUE_HYPOTHESIS'):
                assert (marker in json.dumps(data)) is historical
            assert len(data['meaning']['atoms'])==1 and data['meaning']['atoms'][0]['kind']=='link'
            assert 'FAMILY_SPEC_OPTIONAL' in data['expression_context']['source_evidence'][0]['excerpt']
            if mode=='source-withdrawn':
                original=journal.get(source.observation_event_id)
                ingestor.vault.erase_item(original.event.payload['content']['content_id'])
            # A selected sourced fact absent from required atoms is allowed; an
            # unused source specification and operational caveat need not appear.
            return response('The project describes keeping watch when evidence is insufficient: '
                '[observation design](https://example.invalid/design).')
        if task=='alive_semantic_review':
            semantic_calls.append(data)
            original=data.get('original_evidence',data)
            assert original['source_context']['method']=='discovery-source-authoring-v'+('1' if historical else '2')
            for marker in ('PRIVATE_RESEARCH_GOAL','PRIVATE_MODEL_CONSTRAINT','PRIVATE_READING_QUESTION','PRIVATE_VALUE_HYPOTHESIS'):
                assert (marker in json.dumps(original)) is historical
            if mode=='recovery' and len(semantic_calls)==1:return response('{}')
            return response(dict(atom_reviews=[dict(atom_id=a['atom_id'],preserved=True,risks=[])
                for a in original['meaning']['atoms']],added_claims_detected=False,
                speech_act_preserved=True,protected_literals_preserved=True))
        if task=='alive_source_support':
            assert data['expression_binding']['assessment_mode']=='discovery-source-and-value-v'+('1' if historical else '2')
            assert ('communication_plan' in data['candidate']) is historical
            for marker in ('PRIVATE_RESEARCH_GOAL','PRIVATE_MODEL_CONSTRAINT'):
                assert (marker in json.dumps(data)) is historical
            assert data['candidate']['id'].startswith('message.model_candidate:')
            assert data['assessment_scope']['kind']=='final_discovery_source_and_value'
            assert 'ACTUAL final discovery message' in kw['messages'][0]['content']
            return response(dict(verdict='unsupported' if mode=='unsupported' else 'supported',
                unsupported_claims=['Synthetic purpose mismatch'] if mode=='unsupported' else [],uncertainties=[],
                reason='Synthetic final assessment, not world truth or user satisfaction.'))
        raise AssertionError(task)
    runtime=SendPreparationRuntime(journal,content_vault=ingestor.vault)
    params=dict(subject='user:test',operation_id='one',call=call,
        policy_context=PolicyContext(can_interrupt=True),authority=ActionAuthority.USER_CONFIRMED,
        recipient_meaning=True,grounding=mode!='no-grounding',require_independent_grounding=False,
        resolve_domain=lambda *labels:'synthetic-same-family',inquiry_item_ids=('inquiry:private-research',))
    if mode=='source-withdrawn':
        try:await runtime.assess(allow_repair=False,**params)
        except SemanticReviewError:pass
        else:raise AssertionError('source-led authoring accepted a source erased during rendering')
        assert calls==['alive_opportunity_candidates','alive_deliberation','alive_semantic_render']
        assert not journal.read(event_type='message.model_candidate')
        assert not journal.read(event_type='action.attempted')
        return
    # Generate a historical fixture through actual old scoped mode; after the
    # patch ends, reopening under today's defaults must still reconstruct v1.
    with patch('alive_kernel.opportunity_synthesis._DISCOVERY_AUTHORING',
               'source-led-v1' if historical else 'source-led-v2'):
        assessed=await runtime.assess(allow_repair=False,**params)
    expressed=assessed.expression
    assert assessed.quality_disposition==('final_unsupported' if mode=='unsupported' else 'supported')
    assert 'FAMILY_SPEC_OPTIONAL' not in expressed.text and not expressed.delivery_authorized
    assert calls.count('alive_source_support')==1  # No plan-as-message preflight judges.
    assert len(calls)==(6 if mode in ('recovery','proposal-recovery') else 5)
    generated=interpreter.load_completed(subject='user:test',operation_id=expressed.planning.interpretation_event_id.removeprefix(
        'opportunity.synthesis:').removesuffix(':completed'))
    saved=interpreter.retained_proposal(receipt_event_id=generated.receipt_event_id,
        candidate_id=generated.candidates[0].action.candidate_id,subject='user:test',clearance=Sensitivity.PRIVATE)
    assert saved['communication_plan']==brief()  # Trace preserved, not rewritten/erased.
    assert inquiries.read(subject='user:test',clearance=Sensitivity.PRIVATE,item_ids=('inquiry:private-research',))==[inquiry]
    async def forbidden(**kw):raise AssertionError('completed authoring inferred again')
    reopened=SendPreparationRuntime(ExperienceJournal(journal.path),content_vault=ingestor.vault)
    assert await reopened.assess(allow_repair=False,**{**params,'call':forbidden})==assessed
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='enable'))
    route=install_terminal_route(journal,subject='user:test',content_vault=ingestor.vault)
    confirmation=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
        actor='user:test',subject='user:test',payload={
            'authorizes_selection_event_id':expressed.planning.selection_event_id,
            'authorizes_expression_event_id':expressed.expression_event_id}))
    args=dict(selection_event_id=expressed.planning.selection_event_id,subject='user:test',
        capability='hermes.channel.send',route_binding_id=route,expression_event_id=expressed.expression_event_id,
        confirmation_event_id=confirmation.event.event_id)
    denied=runtime.authorizer.evaluate(operation_id='missing-final',**args)
    assert not denied.authorized and 'final_wording_required' in denied.reasons
    witness=dict(review_event_id=assessed.final_review_event_id,
        interpretation_id=expressed.planning.interpretation_event_id.removeprefix(
            'opportunity.synthesis:').removesuffix(':completed'),require_independence=False)
    decision=runtime.authorizer.evaluate(operation_id='with-final',final_wording_witness=witness,**args)
    assert decision.authorized is (mode!='unsupported'),decision.reasons
    if decision.authorized:
        outbox=DispatchOutbox(journal,content_vault=ingestor.vault)
        authorized=journal.get(decision.event_id)
        outbox._validate_selection_inputs(authorized)
        payload=_thaw_json(authorized.event.payload);payload.pop('final_wording_witness')
        incomplete=replace(authorized,event=replace(authorized.event,payload=payload))
        try:outbox._validate_selection_inputs(incomplete)
        except DispatchOutboxError as error:
            assert 'requires current final wording review' in str(error.__cause__)
        else:raise AssertionError('lower dispatch layer accepted discovery without final review')
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')


async def strict_scope(root):
    for speech in ('ask','remind','warn'):
        try:validate_communication_plan({**brief(),'speech_act':speech},action_kind='ask' if speech=='ask' else 'share')
        except ValueError:pass
        else:raise AssertionError('editorial brief relaxed a strict-purpose message')
    journal=ExperienceJournal(root/'journal.sqlite3')
    agenda=AgendaProjection(journal)
    inbound=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic',
        actor='user:test',subject='user:test',payload={'synthetic':True}))
    record=agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.COMMITMENT,subject='user:test',
        details={'task':'Provide the requested detailed report'},authority=AgendaAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event.event_id,),confidence=1),actor='user:test')
    agenda.apply(record)
    synth=OpportunitySynthesizer(journal)
    async def invalid(**kw):return response(proposal(record.event.payload['item_id'],brief()))
    result=await synth.run(subject='user:test',operation_id='invalid-commitment',call=invalid,
                           recipient_meaning=True,protocol_recovery=False)
    assert not result.candidates and result.rejected_count==1


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-discovery-author-') as directory:
        for mode in ('supported','unsupported','recovery','proposal-recovery','no-grounding','source-withdrawn'):
            root=Path(directory)/mode;root.mkdir();asyncio.run(exercise(root,mode))
        for mode in ('supported','recovery','proposal-recovery'):
            root=Path(directory)/('historical-'+mode);root.mkdir();asyncio.run(exercise(root,mode,historical=True))
        root=Path(directory)/'strict';root.mkdir();asyncio.run(strict_scope(root))
    print('HERMES_ALIVE_DISCOVERY_AUTHORING_OK')
