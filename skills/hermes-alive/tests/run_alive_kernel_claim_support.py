#!/usr/bin/env python3
"""Claim-accounting contracts, not factuality or semantic-extraction qualification."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import EventEnvelope, ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor, OpportunitySynthesizer
from alive_kernel.claim_support import ClaimSupportReviewer, account_claims
from alive_kernel.source_support import SourceSupportError, SourceSupportReviewer


def findings():
    return {'units': [
        {'text': 'Free recording.', 'role': 'verifiable_claim', 'support': 'supported',
         'evidence': [{'source': 'discovery', 'index': 0, 'field': 'excerpt', 'quote': 'Free recording.'}],
         'reason': 'Synthetic supported claim.'},
        {'text': 'Notice unverified.', 'role': 'verifiable_claim', 'support': 'supported',
         'evidence': [{'source': 'discovery', 'index': 0, 'field': 'excerpt', 'quote': 'Notice unverified.'}],
         'reason': 'Synthetic caveat preserved.'},
        {'text': 'Perhaps worth a look.', 'role': 'recommendation', 'support': 'not_applicable',
         'evidence': [], 'reason': 'Tentative suggestion, not an outcome guarantee.'}],
        'coverage_note': 'Synthetic role judgments; no semantic completeness proof.'}


def response(text, model='synthetic-generator'):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


async def exercise(root):
    journal = ExperienceJournal(root / 'journal.sqlite3')
    ingestor = DiscoveryOpportunityIngestor(journal)
    source = ingestor.ingest(DiscoveryCandidate(source='synthetic-public-fixture', title='Repair recording',
        summary='Free recording. Notice unverified.', url='https://example.invalid/repair',
        observed_at=datetime.now(timezone.utc)), subject='user:test')
    text = 'Free recording. Notice unverified. Perhaps worth a look.'
    async def generate(**kw):
        return response(json.dumps({'candidates': [{'agenda_item_id': source.agenda_item_id,
            'kind': 'share', 'text': text, 'topic': 'repair', 'dimensions': {name: {
            'value': .2, 'reason': 'synthetic'} for name in
            ('user_value', 'urgency', 'novelty', 'confidence', 'risk', 'interruption_cost')}}]}))
    generated = await OpportunitySynthesizer(journal).run(subject='user:test', operation_id='generate', call=generate)
    reviewer = ClaimSupportReviewer(journal)
    cid = generated.candidates[0].action.candidate_id
    snapshot, _ = reviewer.snapshot(subject='user:test', interpretation_id='generate', candidate_id=cid)
    base = findings()
    # Source presentation is part of the actual candidate, not the raw model
    # draft. Complete lexical accounting must also cover the host-added link.
    presented = snapshot['candidate']['text']
    assert presented.startswith(text)
    suffix = presented[len(text):].strip()
    assert suffix == '[来源](<https://example.invalid/repair>)'
    base['units'].append({'text':suffix, 'role':'verifiable_claim', 'support':'supported',
        'evidence':[{'source':'discovery', 'index':0, 'field':'url',
            'quote':'https://example.invalid/repair'}], 'reason':'Canonical provenance link.'})
    text = presented
    parsed = account_claims(json.dumps(base), snapshot)
    assert parsed['verdict'] == 'supported' and parsed['lexical_coverage_complete']
    assert not parsed['semantic_coverage_proven']
    for support in ('unsupported', 'uncertain'):
        value = deepcopy(base)
        value['units'][0].update(support=support, evidence=[])
        assert account_claims(json.dumps(value), snapshot)['verdict'] == support
    for mode in ('tail', 'reorder', 'paraphrase', 'invented-quote', 'bool-index', 'metadata', 'no-reference', 'advice-as-fact'):
        value = deepcopy(base)
        data = deepcopy(snapshot)
        if mode == 'tail':
            value['units'].pop()
        elif mode == 'reorder':
            value['units'].reverse()
        elif mode == 'paraphrase':
            value['units'][0]['text'] = 'A complimentary recording.'
        elif mode == 'invented-quote':
            value['units'][0]['evidence'][0]['quote'] = 'Already independently checked.'
        elif mode == 'bool-index':
            value['units'][0]['evidence'][0]['index'] = False
        elif mode == 'metadata':
            value['units'][0]['evidence'][0]['field'] = 'provenance_metadata'
        elif mode == 'no-reference':
            value['units'][0]['evidence'] = []
        elif mode == 'advice-as-fact':
            data['learned_advisory'] = [{'option': 'concise', 'advisory_only': True}]
            value['units'][0]['evidence'] = [{'source': 'learned_advisory', 'index': 0,
                'field': 'record', 'quote': 'concise'}]
        try:
            account_claims(json.dumps(value), data)
        except SourceSupportError:
            pass
        else:
            raise AssertionError('invalid claim accounting accepted: ' + mode)
    # Structural coverage cannot disprove a model's incorrect semantic role label.
    misclassified = {'units': [{'text': text, 'role': 'conversational', 'support': 'not_applicable',
        'evidence': [], 'reason': 'Synthetic wrong role label for diagnostic coverage.'}], 'coverage_note': 'Unproven.'}
    assert not account_claims(json.dumps(misclassified), snapshot)['semantic_coverage_proven']
    calls = []
    async def review(**kw):
        calls.append(kw)
        assert kw['max_tokens'] == 4000
        kw['route_info'].update(provider='synthetic-provider')
        return response(json.dumps(base), 'synthetic-reviewer')
    args = dict(subject='user:test', interpretation_id='generate', candidate_id=cid,
        operation_id='claim-accounting', call=review, resolve_domain=lambda model: model)
    receipt = await reviewer.run(**args)
    assert not receipt.safe_for_automatic_delivery
    assert reviewer.verify_current(receipt.event_id, subject='user:test', interpretation_id='generate', candidate_id=cid) == parsed
    assert reviewer.verify_current(receipt.event_id, subject='user:other', interpretation_id='generate', candidate_id=cid) is None
    assert SourceSupportReviewer(journal).verify_current(receipt.event_id, subject='user:test', interpretation_id='generate', candidate_id=cid) is None
    try:
        await reviewer.run(**args)
    except SourceSupportError:
        pass
    else:
        raise AssertionError('claim accounting repeated an attempted operation')
    assert len(calls) == 1 and not journal.read(event_type='action.attempted')
    other = await reviewer.run(**{**args, 'operation_id':'claim-accounting-ambiguous'})
    journal.append(EventEnvelope(event_id='opportunity.source-support:claim-accounting-ambiguous:failed',
        event_type='opportunity.source_support_failed',source='alive.source-support',
        actor='system:alive-shadow-reviewer',subject='user:test',
        sensitivity=journal.get(other.event_id).event.sensitivity,
        causation_id='opportunity.source-support:claim-accounting-ambiguous:started',
        payload={'error_class':'SyntheticInterruptedFinalization','delivery_authority_granted':False}))
    assert reviewer.verify_current(other.event_id,subject='user:test',interpretation_id='generate',candidate_id=cid) is None
    assert reviewer.verify_current(receipt.event_id,subject='user:test',interpretation_id='generate',candidate_id=cid) == parsed
    assert len(calls) == 2 and not journal.read(event_type='action.attempted')
    ingestor.vault.erase_item(journal.get(source.observation_event_id).event.payload['content']['content_id'])
    assert reviewer.verify_current(receipt.event_id, subject='user:test', interpretation_id='generate', candidate_id=cid) is None


with tempfile.TemporaryDirectory(prefix='alive-claim-support-') as folder:
    asyncio.run(exercise(Path(folder)))
print('HERMES_ALIVE_KERNEL_CLAIM_SUPPORT_OK')
