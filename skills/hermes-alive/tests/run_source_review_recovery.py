#!/usr/bin/env python3
"""Bounded protocol recovery is not verdict normalization or replay authority."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor, OpportunitySynthesizer
from alive_kernel.source_support import SourceSupportReviewer, SourceSupportError
from alive_kernel.opportunity_synthesis import OpportunitySynthesisError


def response(value, model):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value)))])


async def exercise(root, mode):
    journal = ExperienceJournal(root / 'events.sqlite3')
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic-fixture', title='Public guide',
        summary='A synthetic free guide, not independently verified.',
        url='https://example.invalid/guide', observed_at=datetime.now(timezone.utc)), subject='user:test')
    async def generate(**kwargs):
        return response({'candidates':[{'agenda_item_id':source.agenda_item_id,'kind':'share',
            'text':'Synthetic free guide, not independently verified. https://example.invalid/guide',
            'topic':'guide','dimensions':{name:{'value':.2,'reason':'synthetic'} for name in
                ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}, 'generator')
    generated = await OpportunitySynthesizer(journal).run(subject='user:test', operation_id='generate', call=generate)
    reviewer = SourceSupportReviewer(journal)
    calls = []
    invalid = {'verdict':'unsupported','unsupported_claims':[],
               'uncertainties':['Evidence remains unclear.'],'reason':'synthetic invalid review'}
    verdict = mode if mode in ('supported','unsupported','uncertain') else 'supported'
    valid = {'verdict':verdict,'unsupported_claims':['unsupported fact'] if verdict=='unsupported' else [],
             'uncertainties':['unclear fact'] if verdict=='uncertain' else [],'reason':'fresh assessment'}
    async def review(**kwargs):
        calls.append(kwargs)
        kwargs['route_info'].update(provider='synthetic-provider')
        if mode=='provider-error':
            raise RuntimeError('synthetic provider failure')
        if len(calls)==1:
            return response(invalid, 'reviewer')
        data = json.loads(kwargs['messages'][1]['content'])
        assert data['invalid_review']==json.dumps(invalid)
        assert data['original_evidence']['candidate']['id']==generated.candidates[0].action.candidate_id
        if mode=='erase-during':
            reader.vault.erase_item(journal.get(source.observation_event_id).event.payload['content']['content_id'])
        if mode=='cancel':
            raise asyncio.CancelledError()
        return response(invalid if mode=='twice-invalid' else valid,
                        'generator' if mode=='lost-independence' else 'reviewer')
    args = dict(subject='user:test',interpretation_id='generate',
        candidate_id=generated.candidates[0].action.candidate_id, operation_id='review',
        call=review, resolve_domain=lambda model:model, protocol_recovery=mode!='disabled')
    success = mode in ('supported','unsupported','uncertain','erase-quarantine')
    try:
        receipt = await reviewer.run(**args)
    except (SourceSupportError, OpportunitySynthesisError, RuntimeError, asyncio.CancelledError):
        assert not success, mode
        assert not journal.read(event_type='opportunity.source_support_completed')
    else:
        assert success, mode
        assert reviewer.verify_current(receipt.event_id, subject='user:test', interpretation_id='generate',
            candidate_id=args['candidate_id'])==valid
        record = journal.get('opportunity.source-support:review:protocol-recovery')
        assert 'raw_review' not in dict(record.event.payload)
        ref = record.event.payload['content']
        retained = reviewer.vault.resolve_json(ref['content_id'], expected_subject='user:test',
            expected_purpose='opportunity.source-support-invalid', expected_sensitivity=record.event.sensitivity)
        assert retained['raw_review']==json.dumps(invalid)
        if mode=='erase-quarantine':
            reviewer.vault.erase_item(ref['content_id'])
            assert reviewer.verify_current(receipt.event_id, subject='user:test', interpretation_id='generate',
                candidate_id=args['candidate_id']) is None
    expected = 1 if mode in ('disabled','provider-error') else 2
    assert len(calls)==expected, (mode,len(calls))
    try:
        await SourceSupportReviewer(journal).run(**args)
    except Exception:
        pass
    else:
        raise AssertionError('reopened spent operation called provider')
    assert len(calls)==expected
    assert not journal.read(event_type='action.attempted')


async def main(root):
    for mode in ('supported','unsupported','uncertain','twice-invalid','disabled','provider-error',
                 'lost-independence','erase-during','erase-quarantine','cancel'):
        await exercise(root/mode, mode)


with tempfile.TemporaryDirectory(prefix='alive-review-recovery-') as folder:
    asyncio.run(main(Path(folder)))
print('HERMES_ALIVE_SOURCE_REVIEW_RECOVERY_OK')
