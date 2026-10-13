#!/usr/bin/env python3
"""Synthetic causal feedback enters cognition; no real sends or user benefit claim."""
import asyncio
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ActionAuthority, ActionCandidate, ActionKind, AssessmentBasis,
    DecisionDimensions, DeliberationProjection, DimensionAssessment, EventEnvelope,
    ExperienceJournal, OutcomeKind, OutcomeProjection, PolicyContext, SelectionProposal,
    Sensitivity, SideEffect, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    OpportunitySynthesizer, OpportunitySynthesisError)
from alive_kernel.preference_learning import (PreferenceLearningProjection, PreferenceSignalProposal,
    PreferenceAxis, PreferenceDirection, PreferenceSignalOrigin)
from alive_kernel.learning_context import CognitionLearningReader
from alive_kernel.reflection import ReflectionProjection
from alive_kernel.content_vault import ContentVault
from alive_kernel_testkit import install_action_authorization, install_exploration_gate


def seed(journal, owner, direction):
    deliberation = DeliberationProjection(journal)
    outcomes = OutcomeProjection(journal)
    ReflectionProjection(journal)
    learning = PreferenceLearningProjection(journal)
    evidence = EventEnvelope(event_type='discovery.observed', source='synthetic-public-fixture',
        actor='system:test', subject=owner, payload={'fixture': True})
    journal.append(evidence)
    def score(value):
        return DimensionAssessment(value, AssessmentBasis.MEASURED, (evidence.event_id,), 'fixture')
    candidate = ActionCandidate(candidate_id='candidate:' + owner, action_kind=ActionKind.SHARE,
        side_effect=SideEffect.COMMUNICATION, authority=ActionAuthority.USER_DELEGATED,
        content_id='content:' + owner,
        dimensions=DecisionDimensions(score(.8),score(.2),score(.8),score(.8),score(.1),score(.1)))
    framed, frame = deliberation.append_frame((candidate,), PolicyContext(can_interrupt=True),
        actor='system:test', subject=owner, frame_id='frame:' + owner,
        candidate_contents={candidate.content_id: {'schema_version':1,'capability':'hermes.channel.send',
            'operation':{'text':'synthetic prior message','format':'plain'}}})
    deliberation.apply(framed)
    fixture = owner.replace(':','-')
    gate = install_exploration_gate(journal, deliberation, frame, subject=owner, fixture_name=fixture)
    selected = deliberation.append_selection(SelectionProposal(frame.frame_id, candidate.candidate_id,
        'synthetic-selector', 'fixture'), actor='system:test', subject=owner,
        selection_id='selection:' + owner, exploration_gate_event_id=gate)
    deliberation.apply(selected)
    authorization = install_action_authorization(journal, selection_event_id=selected.event.event_id,
        candidate_id=candidate.candidate_id, subject=owner, executor='hermes.channel.send', fixture_name=fixture)
    attempt = outcomes.append_attempt(authorization_event_id=authorization,
        selection_event_id=selected.event.event_id, candidate_id=candidate.candidate_id,
        executor='hermes.channel.send', idempotency_key='fixture:' + owner,
        actor='system:test', subject=owner, attempt_id='attempt:' + owner)
    outcomes.apply(attempt)
    inbound = EventEnvelope(event_type='conversation.inbound', source='synthetic-public-fixture',
        actor=owner, subject=owner, causation_id=attempt.event.event_id,
        payload={'user_outcome_kind':'explicit_feedback','fixture':True})
    journal.append(inbound)
    outcome = outcomes.append_outcome(attempt_id='attempt:' + owner, kind=OutcomeKind.EXPLICIT_FEEDBACK,
        source_event_id=inbound.event_id, details={'fixture':'prefer/dislike concise'}, actor=owner,
        subject=owner, outcome_id='feedback:' + owner)
    assert outcomes.apply(outcome).outcome == 'recorded'
    proposal = PreferenceSignalProposal(subject=owner, axis=PreferenceAxis.PRESENTATION,
        key='message_length', option='concise', direction=direction,
        origin=PreferenceSignalOrigin.EXPLICIT_FEEDBACK, source_id='feedback:' + owner,
        source_event_id=outcome.event.event_id, rationale='synthetic authored feedback', weight=.25,
        expires_at=datetime.now(timezone.utc)+timedelta(days=10), observation_id='signal:' + owner)
    observed = learning.append_observation(proposal, actor='system:test')
    assert learning.apply(observed).outcome == 'recorded'
    return proposal


async def exercise(root):
    journal = ExperienceJournal(root/'experience.sqlite3')
    own = seed(journal, 'user:one', PreferenceDirection.SUPPORT)
    seed(journal, 'user:two', PreferenceDirection.OPPOSE)
    reader = CognitionLearningReader(journal)
    context = reader.read(subject='user:one', clearance=Sensitivity.PRIVATE)
    assert len(context)==1 and context[0].support_mass==.25 and context[0].opposition_mass==0
    foreign = reader.read(subject='user:two', clearance=Sensitivity.PRIVATE)
    assert len(foreign)==1 and foreign[0].support_mass==0 and foreign[0].opposition_mass==.25
    assert reader.read(subject='user:missing', clearance=Sensitivity.PRIVATE)==()
    assert reader.read(subject='user:one', clearance=Sensitivity.PUBLIC)==()
    with closing(reader.learning._connect()) as connection:
        connection.execute('UPDATE preference_observations_v1 SET content_id=? WHERE observation_id=?',
            ('preference-observation:signal:user:two', own.observation_id))
    assert reader.read(subject='user:one', clearance=Sensitivity.PRIVATE)==()
    with closing(reader.learning._connect()) as connection:
        connection.execute('UPDATE preference_observations_v1 SET content_id=? WHERE observation_id=?',
            ('preference-observation:' + own.observation_id, own.observation_id))
    assert reader.read(subject='user:one', clearance=Sensitivity.PRIVATE)==context
    reader.learning.content_vault.erase_item('preference-observation:signal:user:two')
    assert reader.read(subject='user:two', clearance=Sensitivity.PRIVATE)==()
    assert reader.read(subject='user:one', clearance=Sensitivity.PRIVATE)==context
    discovery = DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic',
        title='Public workshop', summary='Public information', url='https://example.invalid/workshop',
        observed_at=datetime.now(timezone.utc)), subject='user:one')
    interpreter = OpportunitySynthesizer(journal, context_vault=ContentVault(root/'custom-typed-memory-vault'))
    calls=[]
    async def generate(**kw):
        data=json.loads(kw['messages'][1]['content'])
        calls.append(data)
        assert data['learned_advisory'][0]['advisory_only']
        assert 'user:two' not in kw['messages'][1]['content']
        if len(calls)==2:
            request=EventEnvelope(event_type='conversation.inbound', source='synthetic-public-fixture',
                actor='user:one', subject='user:one', payload={'fixture':True})
            journal.append(request)
            record=reader.learning.append_retraction(own.observation_id, source_event_id=request.event_id,
                actor='user:one', subject='user:one', operation_id='withdraw')
            reader.learning.apply(record)
        return SimpleNamespace(model='synthetic-interpreter', choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'candidates':[{'agenda_item_id':discovery.agenda_item_id,'kind':'share',
                'text':'Concise synthetic message informed by advisory','topic':'workshop','dimensions':{
                n:{'value':.1 if n in ('risk','interruption_cost') else .8,'reason':'synthetic judgment'}
                for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]})))])
    draft=await interpreter.run(subject='user:one',operation_id='learned',call=generate)
    assert draft.candidates[0].action.authority is ActionAuthority.NONE
    assert 'preference.observation:signal:user:one' in draft.candidates[0].action.dimensions.user_value.evidence_event_ids
    assert interpreter.load_completed(subject='user:one',operation_id='learned')==draft
    try:
        await interpreter.run(subject='user:one',operation_id='withdraw-during-model',call=generate)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('withdrawn advice accepted after model wait')
    assert reader.read(subject='user:one',clearance=Sensitivity.PRIVATE)==()
    try:
        interpreter.load_completed(subject='user:one',operation_id='learned')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('old learned interpretation survived retraction')
    assert len(calls)==2
    assert not journal.read(event_type='dispatch.externally_started')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-learning-context-') as folder:
        asyncio.run(exercise(Path(folder)))
    print('HERMES_ALIVE_KERNEL_LEARNING_CONTEXT_OK')
