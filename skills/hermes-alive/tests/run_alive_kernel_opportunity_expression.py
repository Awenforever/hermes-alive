#!/usr/bin/env python3
"""Interpret, select, bind and express without replacing intent or sending."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ActionAuthority, CognitionCycleCoordinator, DiscoveryCandidate,
    DiscoveryOpportunityIngestor, EventEnvelope, ExperienceJournal, MemoryAuthority,
    MemoryKind, MemoryProjection, MemoryProposal, OpportunitySynthesizer, PolicyContext,
    SemanticAtomKind, SemanticReviewError, SelectionProposal)
from alive_kernel.opportunity_expression import OpportunityExpressionStore
from alive_kernel.semantic_comparator import SemanticComparator


def response(text, model='actual/synthetic'):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


async def scenario(root, mode):
    journal = ExperienceJournal(root / 'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture', title='Repair',
        summary='Community repair workshop, attendance unknown.', url='https://example.invalid/repair',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    memory = MemoryProjection(journal)
    inbound = EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor='user:test', subject='user:test', payload={'synthetic': True})
    journal.append(inbound)
    pref = MemoryProposal(kind=MemoryKind.PREFERENCE, subject='user:test', predicate='profile.interest',
        value='repair', authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event_id,), confidence=1)
    memory.append_proposal(pref, actor='user:test')
    async def generate(**kw):
        return response(json.dumps({'candidates': [{'agenda_item_id': source.agenda_item_id,
            'kind': 'ask' if mode == 'ask' else 'share',
            'text': 'Want details? https://example.invalid/repair' if mode == 'ask' else
                    'Community repair workshop, attendance unknown. https://example.invalid/repair',
            'topic': 'repair', 'dimensions': {name: {'value': .1 if name in
            ('risk','interruption_cost','urgency') else .9, 'reason': 'synthetic judgment'}
            for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}))
    interpreter = OpportunitySynthesizer(journal, content_vault=reader.vault)
    draft = await interpreter.run(subject='user:test', operation_id='interpret', call=generate,
                                  authority=ActionAuthority.USER_DELEGATED)
    async def choose(**kw):
        return response(json.dumps({'candidate_id': draft.candidates[0].action.candidate_id,
                                    'rationale': 'synthetic useful candidate'}))
    coordinator = CognitionCycleCoordinator(journal, content_vault=reader.vault)
    selected = await coordinator.plan_with_model(cycle_id='cycle', subject='user:test',
        candidates=draft.candidates, policy_context=PolicyContext(can_interrupt=True), call=choose)
    original_frame = journal.get(selected.frame_event_id).event.canonical_json()
    store = OpportunityExpressionStore(journal, content_vault=reader.vault)
    meaning = store.define_for_selection(selection_event_id=selected.selection_event_id, subject='user:test')
    before = journal.last_sequence()
    assert store.define_for_selection(selection_event_id=selected.selection_event_id,
                                     subject='user:test') == meaning
    assert journal.last_sequence() == before
    document = store.meanings.resolve(meaning.event.event_id)
    assert document.atoms[0].kind is SemanticAtomKind.PROPOSED_CONTENT
    assert document.atoms[0].protected_literals == ('https://example.invalid/repair',)
    assert meaning.event.payload['truth_claimed'] is False
    assert meaning.event.payload['evidence_entailment_proven'] is False
    assert document.speech_act.value == ('ask' if mode == 'ask' else 'share')
    if mode == 'foreign-owner':
        try:
            store.define_for_selection(selection_event_id=selected.selection_event_id, subject='user:other')
        except SemanticReviewError:
            pass
        else:
            raise AssertionError('foreign owner copied a selected draft')
        return
    calls = []
    async def express(**kw):
        calls.append(kw['task'])
        if kw['task'] == 'alive_semantic_render':
            prompt = json.loads(kw['messages'][1]['content'])
            assert prompt['meaning']['atoms'][0]['kind'] == 'proposed_content'
            text, model = document.atoms[0].text, 'synthetic-renderer'
            if mode == 'withdraw-during-render':
                memory.forget_item(pref.proposal_id, actor='user:test', request_id='withdraw')
            elif mode == 'erase-during-render':
                ref = journal.get(source.observation_event_id).event.payload['content']
                reader.vault.erase_item(ref['content_id'])
            elif mode == 'superseded-during-render':
                coordinator.deliberation.append_selection(SelectionProposal(
                    journal.get(selected.selection_event_id).event.payload['frame_id'],
                    draft.candidates[0].action.candidate_id, 'actual/selector', 'synthetic newer intent'),
                    actor='system:synthetic', subject='user:test', selection_id='newer-selection',
                    exploration_gate_event_id=selected.exploration_event_id)
        else:
            text = json.dumps({'atom_reviews': [{'atom_id': 'proposed-message', 'preserved': True, 'risks': []}],
                'added_claims_detected': False, 'speech_act_preserved': True,
                'protected_literals_preserved': True})
            model = 'synthetic-reviewer'
        kw['route_info'].update(provider='synthetic-provider')
        return response(text, model)
    try:
        compared = await SemanticComparator(store).run(selection_event_id=selected.selection_event_id,
            meaning_event_id=meaning.event.event_id, subject='user:test', call=express,
            resolve_domain=lambda provider, model: model, operation_id='express')
    except SemanticReviewError:
        assert mode in ('withdraw-during-render','erase-during-render','superseded-during-render') and len(calls) == 1
        assert not journal.read(event_type='message.model_candidate')
    else:
        assert mode in ('unchanged','ask','withdraw-after-review') and len(calls) == 2
        assert compared.review.assessment.eligible_for_shadow_comparison
        assert not compared.review.assessment.safe_for_automatic_delivery
        if mode == 'withdraw-after-review':
            memory.forget_item(pref.proposal_id, actor='user:test', request_id='withdraw')
            assert store.resolve_model_candidate(compared.candidate.event_id) is None
            assert store.verify_review(journal.get(compared.review.event_id)) is None
    assert journal.get(selected.frame_event_id).event.canonical_json() == original_frame
    assert not journal.read(event_type='action.attempted')


async def main(root):
    for mode in ('unchanged','ask','withdraw-during-render','erase-during-render',
                 'superseded-during-render','withdraw-after-review','foreign-owner'):
        await scenario(root / mode, mode)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-opportunity-expression-') as folder:
        asyncio.run(main(Path(folder)))
    print('HERMES_ALIVE_KERNEL_OPPORTUNITY_EXPRESSION_OK')
