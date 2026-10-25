#!/usr/bin/env python3
"""Source presentation is fixed before selection, while model wording stays retained."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (DiscoveryCandidate, DiscoveryOpportunityIngestor, ExperienceJournal,
                          OpportunitySynthesizer, OpportunitySynthesisError, CognitionCycleCoordinator,
                          PolicyContext, SemanticAtomKind, CycleCandidate, CognitionCycleError)
from alive_kernel.opportunity_synthesis import _present_source
from alive_kernel.opportunity_expression import OpportunityExpressionStore


async def exercise(root):
    journal = ExperienceJournal(root / 'journal.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic', title='Recording',
        summary='Public synthetic recording information', url='https://example.invalid/recording_(public)',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    original = 'PRIVATE_MODEL_BODY No personal obligation is established.'
    async def generate(**kw):
        return SimpleNamespace(model='synthetic/test', choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'candidates': [{'agenda_item_id': source.agenda_item_id,
                'kind': 'share', 'text': original, 'topic': 'fixture',
                'dimensions': {name: {'value': .9 if name == 'confidence' else .2, 'reason': 'Synthetic uncertainty'} for name in
                    ('user_value','urgency','novelty','confidence','interruption_cost','risk')}}]})))])
    interpreter = OpportunitySynthesizer(journal)
    result = await interpreter.run(subject='user:test', operation_id='current', call=generate)
    expected = original + '\n\n[来源](<https://example.invalid/recording_(public)>)'
    assert result.candidates[0].content['operation']['text'] == expected
    assert result.candidates[0].action.authority.value == 'none'
    def contract(text):
        return {'schema_version': 1, 'capability': 'hermes.channel.send',
                'operation': {'text': text, 'format': 'markdown'}}
    bounded = CycleCandidate(result.candidates[0].action, contract('x' * 12000), 'fixture', 'synthetic')
    assert len(bounded.content['operation']['text']) == 12000
    for invalid in ({'generic': 'x' * 4001}, contract('x' * 12001),
                    {**contract('x' * 5000), 'recipient': 'not-a-host-route'}, contract('\x00' * 2500)):
        try:
            CycleCandidate(result.candidates[0].action, invalid, 'fixture', 'synthetic')
        except CognitionCycleError:
            pass
        else:
            raise AssertionError('invalid or oversized generic/channel envelope admitted')
    bundle = interpreter.vault.resolve_json('opportunity-proposals:current', expected_subject='user:test',
        expected_purpose='opportunity.candidates')
    assert bundle['proposals'][0]['text'] == original
    assert bundle['source_presentation'] == 'canonical_source_v1'
    before = journal.last_sequence()
    reopened = OpportunitySynthesizer(ExperienceJournal(root / 'journal.sqlite3'))
    assert reopened.load_completed(subject='user:test', operation_id='current') == result
    assert journal.last_sequence() == before
    class HistoricalFixtureSynthesizer(OpportunitySynthesizer):
        _SOURCE_PRESENTATION = 'model_text_v1'
    historical = await HistoricalFixtureSynthesizer(journal).run(subject='user:test',
        operation_id='historical', call=generate)
    assert historical.candidates[0].content['operation']['text'] == original
    assert reopened.load_completed(subject='user:test', operation_id='historical') == historical
    coordinator = CognitionCycleCoordinator(journal, content_vault=reader.vault)
    async def verify_meaning(value, cycle_id, url, *, planned=False):
        async def choose(**_kw):
            return SimpleNamespace(model='synthetic/selector', choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({'candidate_id': value.candidates[0].action.candidate_id,
                                    'rationale': 'Synthetic shape fixture, not measured usefulness'})))])
        selected = await coordinator.plan_with_model(cycle_id=cycle_id, subject='user:test',
            candidates=value.candidates, policy_context=PolicyContext(can_interrupt=True), call=choose)
        frame = journal.get(selected.frame_event_id).event.canonical_json()
        expressions = OpportunityExpressionStore(journal, content_vault=reader.vault)
        record = expressions.define_for_selection(selection_event_id=selected.selection_event_id, subject='user:test')
        meaning = expressions.meanings.resolve(record.event.event_id)
        assert meaning.atoms[0].text == ('这是公开的合成学习资料。' if planned else original)
        assert not meaning.atoms[0].protected_literals
        assert meaning.atoms[1].kind is SemanticAtomKind.LINK
        assert meaning.atoms[1].protected_literals == (url,)
        assert journal.get(selected.frame_event_id).event.canonical_json() == frame
    await verify_meaning(result, 'short-source', 'https://example.invalid/recording_(public)')
    # Exact model drafts containing the source remain unchanged, not double-linked.
    assert _present_source(expected, 'https://example.invalid/recording_(public)', 'canonical_source_v1') == expected
    long_url = 'https://example.invalid/' + 'x' * 4000
    assert long_url in _present_source(original, long_url, 'canonical_source_v1')
    source = reader.ingest(DiscoveryCandidate(source='synthetic', title='Long provenance',
        summary='A synthetic source with a long URL', url=long_url,
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    long_result = await interpreter.run(subject='user:test', operation_id='long-source', call=generate)
    assert len(long_result.candidates[0].content['operation']['text']) > 1600
    await verify_meaning(long_result, 'long-source', long_url)
    # Source protection is host-owned even when a model supplies only semantic
    # content, with no URL duplication or translated source phrase as a literal.
    plan=dict(version=2,recipient_goal='分享公开学习资料',speech_act='share',
        contents=[dict(kind='fact',text='这是公开的合成学习资料。')],behavior_constraints=[])
    async def semantic_generate(**kw):
        prompt=json.loads(kw['messages'][1]['content'])
        assert prompt['stage_contract']['source_link_binding']=='canonical_source_v1'
        assert 'canonical URL in a separate plan content' in kw['messages'][0]['content']
        response=await generate(**kw)
        document=json.loads(response.choices[0].message.content)
        document['candidates'][0]['communication_plan']=plan
        return SimpleNamespace(model='synthetic/meaning',choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(document)))])
    planned=await interpreter.run(subject='user:test',operation_id='meaning-source',
        call=semantic_generate,recipient_meaning=True)
    assert planned.rejected_count==0 and len(planned.candidates)==1
    assert long_url in planned.candidates[0].content['operation']['text']
    await verify_meaning(planned,'meaning-source-cycle',long_url,planned=True)
    retained=interpreter.vault.resolve_json('opportunity-proposals:meaning-source',
        expected_subject='user:test',expected_purpose='opportunity.candidates')
    assert retained['proposals'][0]['communication_plan']==plan
    checkpoint=journal.last_sequence()
    assert OpportunitySynthesizer(ExperienceJournal(root/'journal.sqlite3')).load_completed(
        subject='user:test',operation_id='meaning-source')==planned
    assert journal.last_sequence()==checkpoint
    assert _present_source(original, 'https://example.invalid/a>b', 'canonical_source_v1') == (
        original + '\n\n来源：https://example.invalid/a>b')
    try:
        _present_source(original, long_url, 'unknown-policy')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('unknown presentation policy accepted')
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')
    assert not journal.read(event_type='preference.observed')
    for path in root.glob('journal.sqlite3*'):
        assert b'PRIVATE_MODEL_BODY' not in path.read_bytes()


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-source-presentation-') as directory:
        asyncio.run(exercise(Path(directory)))
    print('HERMES_ALIVE_KERNEL_OPPORTUNITY_SOURCE_PRESENTATION_OK')
