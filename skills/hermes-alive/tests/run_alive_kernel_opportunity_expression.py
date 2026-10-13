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


async def scenario(root, mode, owner='user:test'):
    missing_link_modes = ('missing-link', 'drop-required-link', 'long-missing-link')
    source_url = ('https://example.invalid/' + 'x' * 3900 if mode == 'long-missing-link'
                  else 'https://example.invalid/repair')
    journal = ExperienceJournal(root / 'experience.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture', title='Repair',
        summary='Community repair workshop, attendance unknown.', url=source_url,
        observed_at=datetime.now(timezone.utc)), subject=owner)
    memory = MemoryProjection(journal)
    inbound = EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor=owner, subject=owner, payload={'synthetic': True})
    journal.append(inbound)
    pref = MemoryProposal(kind=MemoryKind.PREFERENCE, subject=owner, predicate='profile.interest',
        value='repair', authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event_id,), confidence=1)
    memory.append_proposal(pref, actor=owner)
    async def generate(**kw):
        return response(json.dumps({'candidates': [{'agenda_item_id': source.agenda_item_id,
            'kind': 'ask' if mode == 'ask' else 'share',
            'text': 'Community repair workshop, attendance unknown.' if mode in missing_link_modes else
                    'Want details? https://example.invalid/repair' if mode == 'ask' else
                    'Community repair workshop, attendance unknown. https://example.invalid/repair',
            'topic': 'repair', 'dimensions': {name: {'value': .1 if name in
            ('risk','interruption_cost','urgency') else .9, 'reason': 'synthetic judgment'}
            for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}))
    interpreter = OpportunitySynthesizer(journal, content_vault=reader.vault)
    draft = await interpreter.run(subject=owner, operation_id='interpret', call=generate,
                                  authority=ActionAuthority.USER_DELEGATED)
    async def choose(**kw):
        return response(json.dumps({'candidate_id': draft.candidates[0].action.candidate_id,
                                    'rationale': 'synthetic useful candidate'}))
    coordinator = CognitionCycleCoordinator(journal, content_vault=reader.vault)
    selected = await coordinator.plan_with_model(cycle_id='cycle', subject=owner,
        candidates=draft.candidates, policy_context=PolicyContext(can_interrupt=True), call=choose)
    original_frame = journal.get(selected.frame_event_id).event.canonical_json()
    def add_ranked_noise():
        for index in range(12):
            reader.ingest(DiscoveryCandidate(source='synthetic', title=f'Unrelated {index}',
                summary='new source unrelated to the selected repair draft',
                url=f'https://example.invalid/new-source-{index}',
                priority_hint=1.0,
                observed_at=datetime.now(timezone.utc)), subject=owner)
        assert source.observation_event_id not in {item.observation_event_id for item in
            reader.active_evidence(subject=owner, clearance=journal.get(source.observation_event_id).event.sensitivity)}
    if mode == 'unrelated-window-before-expression':
        add_ranked_noise()
    store = OpportunityExpressionStore(journal, content_vault=reader.vault)
    meaning = store.define_for_selection(selection_event_id=selected.selection_event_id, subject=owner)
    before = journal.last_sequence()
    assert store.define_for_selection(selection_event_id=selected.selection_event_id,
                                     subject=owner) == meaning
    assert journal.last_sequence() == before
    document = store.meanings.resolve(meaning.event.event_id)
    assert document.atoms[0].kind is SemanticAtomKind.PROPOSED_CONTENT
    if mode in missing_link_modes:
        assert not document.atoms[0].protected_literals and len(document.atoms) == 2
        assert document.atoms[1].kind is SemanticAtomKind.LINK
        assert document.atoms[1].protected_literals == (source_url,)
        assert document.atoms[0].text == draft.candidates[0].content['operation']['text']
    else:
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
            text, model = '\n'.join(atom.text for atom in document.atoms), 'synthetic-renderer'
            if mode == 'drop-required-link':
                text = document.atoms[0].text
            if mode == 'withdraw-during-render':
                memory.forget_item(pref.proposal_id, actor=owner, request_id='withdraw')
            elif mode == 'erase-during-render':
                ref = journal.get(source.observation_event_id).event.payload['content']
                reader.vault.erase_item(ref['content_id'])
            elif mode == 'superseded-during-render':
                coordinator.deliberation.append_selection(SelectionProposal(
                    journal.get(selected.selection_event_id).event.payload['frame_id'],
                    draft.candidates[0].action.candidate_id, 'actual/selector', 'synthetic newer intent'),
                    actor='system:synthetic', subject=owner, selection_id='newer-selection',
                    exploration_gate_event_id=selected.exploration_event_id)
            elif mode == 'unrelated-during-render':
                reader.ingest(DiscoveryCandidate(source='synthetic', title='Unrelated', summary='new source',
                    url='https://example.invalid/new-source', observed_at=datetime.now(timezone.utc)), subject=owner)
            elif mode == 'unrelated-window-during-render':
                add_ranked_noise()
        else:
            if mode == 'unrelated-during-review':
                reader.ingest(DiscoveryCandidate(source='synthetic', title='Unrelated', summary='new source',
                    url='https://example.invalid/new-source', observed_at=datetime.now(timezone.utc)), subject=owner)
            elif mode == 'unrelated-window-during-review':
                add_ranked_noise()
            text = json.dumps({'atom_reviews': [{'atom_id': atom.atom_id, 'preserved': True, 'risks': []} for atom in document.atoms],
                'added_claims_detected': False, 'speech_act_preserved': True,
                'protected_literals_preserved': True})
            model = 'synthetic-reviewer'
        kw['route_info'].update(provider='synthetic-provider')
        return response(text, model)
    try:
        compared = await SemanticComparator(store).run(selection_event_id=selected.selection_event_id,
            meaning_event_id=meaning.event.event_id, subject=owner, call=express,
            resolve_domain=lambda provider, model: model, operation_id='express')
    except SemanticReviewError:
        assert mode in ('withdraw-during-render','erase-during-render','superseded-during-render','drop-required-link') and len(calls) == 1
        assert not journal.read(event_type='message.model_candidate')
    else:
        assert mode in ('unchanged','ask','withdraw-after-review','probe-fixture','missing-link','long-missing-link',
                        'unrelated-during-render','unrelated-during-review',
                        'unrelated-window-before-expression','unrelated-window-during-render',
                        'unrelated-window-during-review') and len(calls) == 2
        assert compared.review.assessment.eligible_for_shadow_comparison
        assert not compared.review.assessment.safe_for_automatic_delivery
        if mode == 'withdraw-after-review':
            memory.forget_item(pref.proposal_id, actor=owner, request_id='withdraw')
            assert store.resolve_model_candidate(compared.candidate.event_id) is None
            assert store.verify_review(journal.get(compared.review.event_id)) is None
    assert journal.get(selected.frame_event_id).event.canonical_json() == original_frame
    assert not journal.read(event_type='action.attempted')
    if mode == 'probe-fixture':
        return journal.path, compared.candidate.event_id


async def main(root):
    for mode in ('unchanged','ask','withdraw-during-render','erase-during-render',
                 'missing-link','drop-required-link','long-missing-link',
                 'superseded-during-render','withdraw-after-review','foreign-owner',
                 'unrelated-during-render','unrelated-during-review',
                 'unrelated-window-before-expression','unrelated-window-during-render',
                 'unrelated-window-during-review'):
        await scenario(root / mode, mode)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-opportunity-expression-') as folder:
        asyncio.run(main(Path(folder)))
    print('HERMES_ALIVE_KERNEL_OPPORTUNITY_EXPRESSION_OK')
