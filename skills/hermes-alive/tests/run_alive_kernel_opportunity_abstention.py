#!/usr/bin/env python3
"""Per-source non-action is retained but never dispatched or learned as feedback."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (DiscoveryCandidate, DiscoveryOpportunityIngestor,
                          ExperienceJournal, OpportunitySynthesizer, OpportunitySynthesisError, Sensitivity)


def response(document):
    return SimpleNamespace(model='synthetic/test', choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(document)))])


async def exercise(root):
    journal = ExperienceJournal(root / 'kernel.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    items = [reader.ingest(DiscoveryCandidate(source='synthetic', title='Fixture ' + str(i),
        summary='Synthetic public evidence', url='https://example.invalid/item/' + str(i),
        observed_at=datetime.now(timezone.utc)), subject='user:test') for i in range(3)]
    foreign = reader.ingest(DiscoveryCandidate(source='synthetic', title='Other owner',
        summary='Other owner evidence', url='https://example.invalid/foreign',
        observed_at=datetime.now(timezone.utc)), subject='user:other')
    synth = OpportunitySynthesizer(journal)
    evidence = reader.active_evidence(subject='user:test', clearance=Sensitivity.PRIVATE)
    def abstain(item, reason='PRIVATE_ABSTENTION_REASON'):
        return {'agenda_item_id': item.agenda_item_id, 'reason': reason}
    def draft(item):
        return {'agenda_item_id': item.agenda_item_id, 'kind': 'share', 'text': 'Synthetic draft',
            'topic': 'fixture', 'dimensions': {name: {'value': .2, 'reason': 'Synthetic judgment'}
            for name in ('user_value', 'urgency', 'novelty', 'confidence', 'interruption_cost', 'risk')}}
    async def call(**kw):
        assert 'abstentions' in kw['messages'][0]['content']
        return response({
            'candidates': [draft(items[0])], 'abstentions': [abstain(items[1])]
        })
    before = tuple(journal.read(event_type='preference.observed'))
    result = await synth.run(subject='user:test', operation_id='mixed', call=call)
    assert len(result.candidates) == len(result.abstentions) == 1
    assert result.rejected_count == result.rejected_abstention_count == 0
    assert result.abstentions[0].observation_event_id == items[1].observation_event_id
    assert result.abstentions[0].reason == 'PRIVATE_ABSTENTION_REASON'
    assert result.unassessed_agenda_item_ids == (items[2].agenda_item_id,)
    reopened = OpportunitySynthesizer(ExperienceJournal(root / 'kernel.sqlite3'))
    assert reopened.load_completed(subject='user:test', operation_id='mixed') == result
    assert tuple(journal.read(event_type='preference.observed')) == before
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')
    receipt = journal.get(result.receipt_event_id)
    assert 'PRIVATE_ABSTENTION_REASON' not in repr(receipt.event.payload)
    # No keyword rules: arbitrary reasons are preserved, not judged as true.
    for reason in ('x' * 512, 'Meaning remains uncertain; no interruption justified.'):
        accepted, rejected = synth._abstentions([abstain(items[1], reason)], evidence, [])
        assert accepted[0].reason == reason and rejected == 0
    invalid = [abstain(foreign), abstain(items[1], ''), abstain(items[1], ' '),
               abstain(items[1], 'x' * 513), {'agenda_item_id': [], 'reason': 'bad'},
               {**abstain(items[1]), 'authority': 'user_confirmed'}]
    for value in invalid:
        accepted, rejected = synth._abstentions([value], evidence, [])
        assert not accepted and rejected == 1
    accepted, rejected = synth._abstentions([abstain(items[1]), abstain(items[1])], evidence, [])
    assert not accepted and rejected == 2
    accepted, rejected = synth._abstentions([abstain(items[0]), abstain(items[1])], evidence, [draft(items[0])])
    assert len(accepted) == 1 and rejected == 1
    # Missing/invalid non-actions are not synthesized as abstentions.
    async def partial(**_kw):
        return response({
            'candidates': [], 'abstentions': [abstain(items[1]), abstain(foreign)]
        })
    partial_result = await synth.run(subject='user:test', operation_id='partial', call=partial)
    assert not partial_result.candidates and partial_result.rejected_abstention_count == 1
    assert set(partial_result.unassessed_agenda_item_ids) == {items[0].agenda_item_id, items[2].agenda_item_id}
    assert reopened.load_completed(subject='user:test', operation_id='partial') == partial_result
    for invalid_envelope in (None, {}, [abstain(items[1])] * 9):
        try:
            synth._abstentions(invalid_envelope, evidence, [])
        except OpportunitySynthesisError:
            pass
        else:
            raise AssertionError('invalid abstention envelope admitted')
    async def malformed(**_kw):
        return SimpleNamespace(model='synthetic/test', choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"abstentions":[],"candidates":['))])
    try:
        await synth.run(subject='user:test', operation_id='malformed', call=malformed)
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('malformed JSON converted to successful abstention')
    assert journal.get('opportunity.synthesis:malformed:failed') is not None
    assert journal.get('opportunity.synthesis:malformed:completed') is None
    try:
        reopened.load_completed(subject='user:test', operation_id='malformed')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('failed operation recovered as a skip')
    reader.vault.erase_item('opportunity-proposals:mixed')
    try:
        reopened.load_completed(subject='user:test', operation_id='mixed')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('erased non-action recovered')
    reader.vault.erase_subject('user:test')
    try:
        reopened.load_completed(subject='user:test', operation_id='partial')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('stale source reused for non-action')
    for path in root.glob('kernel.sqlite3*'):
        assert b'PRIVATE_ABSTENTION_REASON' not in path.read_bytes()


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-opportunity-abstention-') as directory:
        asyncio.run(exercise(Path(directory)))
    print('HERMES_ALIVE_KERNEL_OPPORTUNITY_ABSTENTION_OK')
