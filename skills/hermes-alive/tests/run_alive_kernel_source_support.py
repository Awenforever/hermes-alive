#!/usr/bin/env python3
"""Source support is independently bound and revocable, never delivery authority."""
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import (ExperienceJournal,DiscoveryCandidate,DiscoveryOpportunityIngestor,
                         OpportunitySynthesizer)
from alive_kernel.source_support import SourceSupportReviewer,SourceSupportError
import alive_kernel.source_support as support_module


async def exercise(root,mode):
    journal=ExperienceJournal(root/'experience.sqlite3')
    reader=DiscoveryOpportunityIngestor(journal)
    source=reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture',title='Repair recording',
        summary='Free recording, no registration. Notice unverified.',url='https://example.invalid/repair',
        observed_at=datetime.now(timezone.utc)),subject='user:test')
    async def generate(**kw):
        value={'candidates':[{'agenda_item_id':source.agenda_item_id,'kind':'share',
            'text':'Free recording, no registration. Notice unverified. https://example.invalid/repair',
            'topic':'repair','dimensions':{n:{'value':.1 if n in ('risk','interruption_cost') else .8,
                'reason':'synthetic judgment'} for n in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]}
        return SimpleNamespace(model='synthetic-generator',choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])
    drafted=await OpportunitySynthesizer(journal).run(subject='user:test',operation_id='generate',call=generate)
    reviewer=SourceSupportReviewer(journal)
    candidate_id=drafted.candidates[0].action.candidate_id
    calls=[]
    async def review(**kw):
        calls.append(kw)
        data=json.loads(kw['messages'][1]['content'])
        assert set(data)=={'interpretation_started_at','evidence','explicit_context','learned_advisory','recent_expression_history','candidate'}
        assert data['interpretation_started_at']==journal.get('opportunity.synthesis:generate:started').event.occurred_at.isoformat()
        assert 'published_at' in data['evidence'][0]
        assert data['evidence'][0]['excerpt'].endswith('unverified.')
        if mode=='source-changed':
            reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture',title='Repair recording',
                summary='Registration now required.',url='https://example.invalid/repair',
                observed_at=datetime.now(timezone.utc)),subject='user:test')
        findings={'verdict':'unsupported' if mode=='unsupported' else 'supported',
            'unsupported_claims':['unsupported guarantee'] if mode=='unsupported' else [],
            'uncertainties':[],'reason':'synthetic review'}
        if mode=='invalid':
            findings['unsupported_claims']=['contradictory verdict']
        kw['route_info'].update(provider='synthetic-provider')
        return SimpleNamespace(model='synthetic-generator' if mode=='self-review' else 'synthetic-reviewer',
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(findings)))])
    args=dict(subject='user:test',interpretation_id='generate',candidate_id=candidate_id,
        operation_id='review',call=review,resolve_domain=lambda model:model)
    if mode=='start-race':
        original_append=journal.append
        def competing_append(event):
            if event.event_type=='opportunity.source_support_started':
                original_append(event)
            return original_append(event)
        journal.append=competing_append
    try:
        receipt=await reviewer.run(**args)
    except Exception:
        assert mode in ('source-changed','invalid','self-review','start-race')
        assert not journal.read(event_type='opportunity.source_support_completed')
    else:
        assert mode in ('supported','unsupported','ambiguous-terminal')
        assert not receipt.safe_for_automatic_delivery
        assert reviewer.verify_current(receipt.event_id,subject='user:test',interpretation_id='generate',
            candidate_id=candidate_id)['verdict']==('supported' if mode=='ambiguous-terminal' else mode)
        assert reviewer.verify_current(receipt.event_id,subject='user:other',interpretation_id='generate',
            candidate_id=candidate_id) is None
        if mode=='supported':
            original=journal.get(receipt.event_id).event
            alias=journal.append(support_module.EventEnvelope(event_id='opportunity.source-support:alias:completed',
                event_type=original.event_type,source=original.source,actor=original.actor,
                subject=original.subject,sensitivity=original.sensitivity,
                causation_id=original.causation_id,payload=original.payload))
            assert reviewer.verify_current(alias.event.event_id,subject='user:test',interpretation_id='generate',
                candidate_id=candidate_id) is None
            assert reviewer.verify_current(receipt.event_id,subject='user:test',interpretation_id='generate',
                candidate_id=candidate_id)['verdict']=='supported'
        original_prompt=support_module.PROMPT
        try:
            support_module.PROMPT += '\nSynthetic method version change.'
            assert reviewer.verify_current(receipt.event_id,subject='user:test',interpretation_id='generate',
                candidate_id=candidate_id) is None
        finally:
            support_module.PROMPT=original_prompt
        if mode=='ambiguous-terminal':
            journal.append(support_module.EventEnvelope(event_id='opportunity.source-support:review:failed',
                event_type='opportunity.source_support_failed',source='alive.source-support',
                actor='system:alive-shadow-reviewer',subject='user:test',
                sensitivity=journal.get(receipt.event_id).event.sensitivity,
                causation_id='opportunity.source-support:review:started',
                payload={'error_class':'SyntheticInterruptedFinalization','delivery_authority_granted':False}))
            assert reviewer.verify_current(receipt.event_id,subject='user:test',interpretation_id='generate',
                candidate_id=candidate_id) is None
        reader.vault.erase_item(journal.get(source.observation_event_id).event.payload['content']['content_id'])
        assert reviewer.verify_current(receipt.event_id,subject='user:test',interpretation_id='generate',
            candidate_id=candidate_id) is None
    expected_calls=0 if mode=='start-race' else 1
    assert len(calls)==expected_calls
    try:
        await reviewer.run(**args)
    except Exception:
        pass
    else:
        raise AssertionError('source-support repeated a spent model operation')
    assert len(calls)==expected_calls and not journal.read(event_type='action.attempted')


async def main(root):
    for mode in ('supported','unsupported','invalid','self-review','source-changed','start-race','ambiguous-terminal'):
        await exercise(root/mode,mode)

with tempfile.TemporaryDirectory(prefix='alive-source-support-') as folder:
    asyncio.run(main(Path(folder)))
print('HERMES_ALIVE_KERNEL_SOURCE_SUPPORT_OK')
