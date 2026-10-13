#!/usr/bin/env python3
"""Final wording review binds source, current intent, renderer and retention."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor,
    OpportunitySynthesizer, CognitionCycleCoordinator, PolicyContext, SelectionProposal)
from alive_kernel.content_vault import ContentReference
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from alive_kernel.opportunity_expression import OpportunityExpressionStore
from alive_kernel.source_support import SourceSupportError

def response(text, model):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

async def scenario(root, mode):
    subject = 'user:synthetic'
    journal = ExperienceJournal(root / 'journal.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture', title='Recording',
        summary='An unverified free introductory recording, medium unspecified.',
        url='https://example.invalid/01', observed_at=datetime.now(timezone.utc)), subject=subject)
    async def generate(**kw):
        return response(json.dumps({'candidates':[{'agenda_item_id':source.agenda_item_id,
            'kind':'share', 'text':'A free introductory recording, medium unspecified.', 'topic':'learning',
            'dimensions':{name:{'value':.1 if name in ('risk','interruption_cost','urgency') else .9,
                'reason':'synthetic judgment'} for name in
                ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}), 'synthetic-drafter')
    draft = await OpportunitySynthesizer(journal, content_vault=reader.vault).run(
        subject=subject, operation_id='interpret', call=generate)
    async def choose(**kw):
        return response(json.dumps({'candidate_id':draft.candidates[0].action.candidate_id,
            'rationale':'Synthetic selection'}), 'synthetic-selector')
    coordinator = CognitionCycleCoordinator(journal, content_vault=reader.vault)
    choice = await coordinator.plan_with_model(cycle_id='cycle', subject=subject,
        candidates=draft.candidates, policy_context=PolicyContext(can_interrupt=True), call=choose)
    store = OpportunityExpressionStore(journal, content_vault=reader.vault)
    meaning = store.define_for_selection(selection_event_id=choice.selection_event_id, subject=subject)
    final_text = '这里有一段免费的视频，可随时观看。[来源](https://example.invalid/01)'
    expressed = store.record_model_candidate(selection_event_id=choice.selection_event_id,
        meaning_event_id=meaning.event.event_id, subject=subject, text=final_text,
        renderer_execution_id='synthetic:render', renderer_model='synthetic-renderer',
        renderer_independence_domain='renderer-family')
    reviewer = ExpressionSourceSupportReviewer(journal, content_vault=reader.vault)
    args = dict(subject=subject, interpretation_id='interpret', candidate_id=expressed.event_id)
    calls = []
    async def review(**kw):
        calls.append(kw)
        snapshot = json.loads(kw['messages'][1]['content'])
        assert snapshot['candidate']['text'] == final_text
        assert snapshot['candidate']['id'] == expressed.event_id
        assert snapshot['expression_binding']['draft_is_not_evidence'] is True
        assert snapshot['evidence'][0]['excerpt'].endswith('medium unspecified.')
        if mode == 'supersede':
            coordinator.deliberation.append_selection(SelectionProposal(
                journal.get(choice.selection_event_id).event.payload['frame_id'],
                draft.candidates[0].action.candidate_id, 'synthetic-selector', 'Synthetic newer intent'),
                actor='system:synthetic', subject=subject, selection_id='newer-selection',
                exploration_gate_event_id=choice.exploration_event_id)
        if mode == 'erase-during':
            reader.vault.erase_item(journal.get(source.observation_event_id).event.payload['content']['content_id'])
        kw['route_info'].update(provider='synthetic-provider')
        return response(json.dumps({'verdict':'uncertain', 'unsupported_claims':[],
            'uncertainties':['The supplied source does not establish a video medium.'],
            'reason':'Synthetic diagnostic, not semantic truth.'}),
            'synthetic-renderer' if mode == 'self-review' else 'synthetic-reviewer')
    for bad in ({**args,'subject':'user:foreign'}, {**args,'interpretation_id':'other'},
                {**args,'candidate_id':draft.candidates[0].action.candidate_id}):
        try:
            reviewer.snapshot(**bad)
        except (SourceSupportError, ValueError):
            pass
        else:
            raise AssertionError('foreign/unbound expression accepted')
    try:
        receipt = await reviewer.run(**args, operation_id='source-review', call=review,
            resolve_domain=lambda model:model)
    except (SourceSupportError, ValueError):
        assert mode in ('self-review','supersede','erase-during')
        assert not journal.read(event_type='opportunity.source_support_completed')
    else:
        assert mode in ('unchanged','erase-after','expired-after')
        assert not receipt.safe_for_automatic_delivery
        assert reviewer.verify_current(receipt.event_id, **args)['verdict'] == 'uncertain'
        event = journal.get(receipt.event_id).event
        assert event.payload['generator_model'] == 'synthetic-renderer'
        assert journal.get(event.causation_id).event.causation_id == expressed.event_id
        ref = ContentReference.from_event_payload(event.payload['content'])
        assert ref.retention_until == expressed.expires_at
        if mode == 'erase-after':
            reader.vault.erase_item(journal.get(source.observation_event_id).event.payload['content']['content_id'])
            assert reviewer.verify_current(receipt.event_id, **args) is None
        if mode == 'expired-after':
            resolve = reviewer.expressions.resolve_model_candidate
            reviewer.expressions.resolve_model_candidate = lambda event_id:resolve(event_id, as_of=expressed.expires_at)
            assert reviewer.verify_current(receipt.event_id, **args) is None
    assert len(calls) == 1
    try:
        await reviewer.run(**args, operation_id='source-review', call=review, resolve_domain=lambda model:model)
    except (SourceSupportError, ValueError):
        pass
    else:
        raise AssertionError('spent review operation called model again')
    assert len(calls) == 1
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')

async def main(root):
    for mode in ('unchanged','self-review','supersede','erase-during','erase-after','expired-after'):
        await scenario(root / mode, mode)

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-expression-support-') as folder:
        asyncio.run(main(Path(folder)))
    print('HERMES_ALIVE_KERNEL_EXPRESSION_SUPPORT_OK')
