#!/usr/bin/env python3
"""Four reopened planning cycles: advice, explicit override and withdrawal.

Model responses and feedback attribution are synthetic fixtures. This proves
cross-cycle plumbing, NOT semantic intelligence, live delivery or user benefit.
No transport, channel queue or production configuration is involved.
"""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ActionAuthority, ActionKind, CognitionCycleCoordinator,
    DiscoveryCandidate, DiscoveryOpportunityIngestor, EventEnvelope,
    ExperienceJournal, MemoryAuthority, MemoryKind, MemoryProjection,
    MemoryProposal, OpportunitySynthesizer, OpportunitySynthesisError, PolicyContext)
from alive_kernel.preference_learning import PreferenceDirection, PreferenceLearningProjection
from run_alive_kernel_learning_context import seed


def response(value, model):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value, ensure_ascii=False)))])


async def exercise(root):
    owner = 'user:longitudinal'
    path = root / 'experience.sqlite3'
    journal = ExperienceJournal(path)
    source = DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(
        source='synthetic public collector', title='Community workshop',
        summary='Public repair workshop; attendance and usefulness unknown.',
        url='https://example.invalid/workshop', observed_at=datetime.now(timezone.utc)), subject=owner)
    prompts, decisions, selections = [], [], []

    async def cycle(number, expected_advice, expected_context):
        # Reopen every collaborator: no previous Python object carries memory.
        current = ExperienceJournal(path)
        synth = OpportunitySynthesizer(current)
        async def interpret(**kwargs):
            prompt = json.loads(kwargs['messages'][1]['content'])
            prompts.append(prompt)
            assert bool(prompt['learned_advisory']) == expected_advice
            assert bool(prompt['user_context']) == expected_context
            assert all(item['advisory_only'] for item in prompt['learned_advisory'])
            assert all('user:foreign' not in json.dumps(item) for item in
                       (*prompt['learned_advisory'], *prompt['user_context']))
            # A controlled model oracle, not a new deterministic product rule.
            # The test deliberately makes explicit context override old advice.
            offer = expected_advice and not expected_context
            value = {'candidates': [], 'abstentions': []}
            if offer:
                value['candidates'] = [{'agenda_item_id': source.agenda_item_id,
                    'kind': 'share', 'text': 'A concise workshop suggestion; usefulness uncertain.',
                    'topic': 'repair', 'dimensions': {name: {'value': .1 if name in
                    ('risk', 'urgency', 'interruption_cost') else .8,
                    'reason': 'synthetic planning oracle, not calibrated benefit'} for name in
                    ('user_value', 'urgency', 'novelty', 'confidence', 'risk', 'interruption_cost')}}]
            else:
                value['abstentions'] = [{'agenda_item_id': source.agenda_item_id,
                    'reason': 'Explicit boundary takes precedence.' if expected_context else
                              'No current interest evidence; usefulness remains unknown.'}]
            return response(value, 'synthetic/interpreter')
        generated = await synth.run(subject=owner, operation_id='longitudinal-' + str(number),
            call=interpret, authority=ActionAuthority.USER_DELEGATED)
        assert generated.rejected_count == 0
        coordinator = CognitionCycleCoordinator(current)
        async def choose(**kwargs):
            selections.append(kwargs['messages'])
            identifier = generated.candidates[0].action.candidate_id
            assert identifier in kwargs['messages'][1]['content']
            return response({'candidate_id': identifier, 'rationale': 'synthetic selected proposal'},
                            'synthetic/selector')
        planned = await coordinator.plan_with_model(cycle_id='longitudinal-' + str(number),
            subject=owner, candidates=generated.candidates,
            policy_context=PolicyContext(can_interrupt=True), call=choose)
        decisions.append(planned.selection.candidate.action_kind)
        expected = ActionKind.SHARE if expected_advice and not expected_context else ActionKind.SILENCE
        assert decisions[-1] is expected
        reread = OpportunitySynthesizer(ExperienceJournal(path)).load_completed(
            subject=owner, operation_id='longitudinal-' + str(number),
            authority=ActionAuthority.USER_DELEGATED)
        assert reread == generated
        ungranted = OpportunitySynthesizer(ExperienceJournal(path)).load_completed(
            subject=owner, operation_id='longitudinal-' + str(number))
        assert all(item.action.authority is ActionAuthority.NONE for item in ungranted.candidates)
        if generated.candidates:
            assert 'preference.observation:signal:' + owner in (
                generated.candidates[0].action.dimensions.user_value.evidence_event_ids)
        # Selection and advice are not dispatch grants or successful outcomes.
        assert not current.read(event_type='dispatch.externally_started')
        assert not current.read(event_type='dispatch.enqueued')
        return generated, planned

    await cycle(0, False, False)
    proposal = seed(journal, owner, PreferenceDirection.SUPPORT,
        rationale='Concise messages are acceptable, not a request for increased frequency.')
    seed(journal, 'user:foreign', PreferenceDirection.OPPOSE)
    generated, selected = await cycle(1, True, False)
    immutable_selection = journal.get(selected.selection_event_id).event.canonical_json()
    request = journal.append(EventEnvelope(event_type='conversation.inbound',
        source='synthetic-user-command', actor=owner, subject=owner,
        payload={'synthetic': True}))
    memory = MemoryProjection(journal)
    boundary = MemoryProposal(kind=MemoryKind.PREFERENCE, subject=owner,
        predicate='profile.interest', value='Do not share workshop suggestions.',
        authority=MemoryAuthority.USER_EXPLICIT, source_event_ids=(request.event.event_id,), confidence=1)
    memory.append_proposal(boundary, actor=owner)
    await cycle(2, True, True)
    memory.forget_item(boundary.proposal_id, actor=owner, request_id='withdraw-explicit')
    learning = PreferenceLearningProjection(journal)
    record = learning.append_retraction(proposal.observation_id,
        source_event_id=request.event.event_id, actor=owner, subject=owner,
        operation_id='withdraw-advice')
    retracted = learning.apply(record)
    assert retracted.outcome == 'retracted', retracted
    await cycle(3, False, False)
    assert decisions == [ActionKind.SILENCE, ActionKind.SHARE, ActionKind.SILENCE, ActionKind.SILENCE]
    assert len(prompts) == 4 and len(selections) == 1
    assert journal.get(selected.selection_event_id).event.canonical_json() == immutable_selection
    try:
        OpportunitySynthesizer(ExperienceJournal(path)).load_completed(
            subject=owner, operation_id='longitudinal-1')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('withdrawn advice revived a previous executable draft')
    # Two seeded attempts belong to the explicit test fixture, none to the cycles.
    assert len(journal.read(event_type='action.attempted')) == 2
    assert not journal.read(event_type='dispatch.externally_started')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-longitudinal-') as folder:
        asyncio.run(exercise(Path(folder)))
    print('HERMES_ALIVE_KERNEL_LONGITUDINAL_PLANNING_OK')
