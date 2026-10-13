#!/usr/bin/env python3
"""Independent discourse/assertion contracts; no semantic completeness claim."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor, OpportunitySynthesizer
from alive_kernel.claim_support import FacetedClaimSupportReviewer, account_facets
from alive_kernel.source_support import SourceSupportError


def findings(text):
    return {'segments':[{'text':text, 'function':'recommendation',
        'assertion_ids':['free','backup'], 'scan_complete':True}],
        'assertions':[
            {'id':'free','anchor':'it is free','proposition':'The recording costs nothing.',
             'epistemic_role':'asserted','support':'supported', 'evidence':[
             {'source':'discovery','index':0,'field':'excerpt','quote':'Free recording.'}], 'reason':'Explicit source.'},
            {'id':'backup','anchor':'the backup was already checked',
             'proposition':'A completed backup check occurred.', 'epistemic_role':'asserted',
             'support':'unsupported','evidence':[], 'reason':'The source instead says backup not checked.'}],
        'coverage_note':'Synthetic assertions; lexical coverage is not semantic completeness.'}


def response(value, model):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])


async def exercise(root):
    journal = ExperienceJournal(root / 'journal.sqlite3')
    source = DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(source='synthetic-public-fixture',
        title='Repair recording', summary='Free recording. Backup not checked.',
        url='https://example.invalid/repair', observed_at=datetime.now(timezone.utc)), subject='user:test')
    text = 'Try the recording; it is free, and the backup was already checked.'
    async def generate(**kwargs):
        return response({'candidates':[{'agenda_item_id':source.agenda_item_id,'kind':'share','text':text,
            'topic':'repair', 'dimensions':{name:{'value':.2,'reason':'Synthetic judgment.'} for name in
            ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}, 'synthetic-generator')
    generated = await OpportunitySynthesizer(journal).run(subject='user:test', operation_id='generate', call=generate)
    reviewer = FacetedClaimSupportReviewer(journal)
    cid = generated.candidates[0].action.candidate_id
    snapshot, _ = reviewer.snapshot(subject='user:test', interpretation_id='generate', candidate_id=cid)
    base = findings(text)
    for function in ('statement','recommendation','question','social'):
        value = deepcopy(base)
        value['segments'][0]['function'] = function
        result = account_facets(json.dumps(value), snapshot)
        assert result['verdict'] == 'unsupported' and not result['semantic_coverage_proven']
    for mode in ('orphan','bad-anchor','not-applicable','duplicate-id','invented-quote'):
        value = deepcopy(base)
        if mode == 'orphan': value['segments'][0]['assertion_ids'] = ['free']
        elif mode == 'bad-anchor': value['assertions'][1]['anchor'] = 'Completely absent assertion.'
        elif mode == 'not-applicable': value['assertions'][1]['support'] = 'not_applicable'
        elif mode == 'duplicate-id': value['assertions'][1]['id'] = 'free'
        else: value['assertions'][0]['evidence'][0]['quote'] = 'Paid and independently checked.'
        try: account_facets(json.dumps(value), snapshot)
        except SourceSupportError: pass
        else: raise AssertionError('invalid facet accepted: ' + mode)
    # A missed extraction remains possible. Do not manufacture completeness proof
    # merely because the assessor links no assertions to full lexical coverage.
    missed = {'segments':[{'text':text, 'function':'social','assertion_ids':[], 'scan_complete':True}],
              'assertions':[], 'coverage_note':'Synthetic missed facts.'}
    assert not account_facets(json.dumps(missed), snapshot)['semantic_coverage_proven']
    missed['segments'][0]['scan_complete'] = False
    assert account_facets(json.dumps(missed), snapshot)['verdict'] == 'uncertain'
    async def review(**kwargs):
        assert kwargs['max_tokens'] == 5000
        kwargs['route_info'].update(provider='synthetic')
        return response(base, 'synthetic-reviewer')
    args = dict(subject='user:test', interpretation_id='generate', candidate_id=cid,
                operation_id='facets', call=review, resolve_domain=lambda model:model)
    receipt = await reviewer.run(**args)
    assert not receipt.safe_for_automatic_delivery
    assert reviewer.verify_current(receipt.event_id, subject='user:test',
        interpretation_id='generate', candidate_id=cid)['verdict'] == 'unsupported'
    assert not journal.read(event_type='action.attempted')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-claim-facets-') as directory:
        asyncio.run(exercise(Path(directory)))
    print('HERMES_ALIVE_KERNEL_FACETED_CLAIM_SUPPORT_OK')
