#!/usr/bin/env python3
"""Real planning/review/repair composition, synthetic model outputs and no IO."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor, PolicyContext
from alive_kernel.planning_runtime import PlanningRuntime, PlanningRuntimeError
from alive_kernel.source_support import SourceSupportReviewer


async def test(root, mode):
    journal = ExperienceJournal(root / 'experience.sqlite3')
    source = DiscoveryOpportunityIngestor(journal).ingest(DiscoveryCandidate(
        source='synthetic organizer', title='Workshop', summary='Free online hand-sewing recording.',
        url='https://example.invalid/repair', observed_at=datetime.now(timezone.utc)), subject='user:test')
    calls = []
    async def call(**kwargs):
        task = kwargs['task']
        calls.append(task)
        data = json.loads(kwargs['messages'][1]['content'].split('\n', 1)[-1]) if task == 'alive_deliberation' else json.loads(kwargs['messages'][1]['content'])
        if task == 'alive_opportunity_candidates':
            repair = bool(data['corrective_reviews'])
            if repair:
                if mode == 'repair-failure': raise RuntimeError('synthetic repair provider failure')
                assert len(data['corrective_reviews']) == 1
                assert data['corrective_reviews'][0]['advisory_only']
                texts = ['Free online hand-sewing recording.'] if mode == 'repair' else ['Bad invented history.']
            else:
                texts = ['Bad invented history.']
                if mode in ('mixed', 'partial-failure', 'repair-failure'): texts += ['Free online hand-sewing recording.']
            document = {'candidates':[{'agenda_item_id':source.agenda_item_id, 'kind':'share',
                'text':text, 'topic':'repair', 'dimensions':{name:{'value':.1 if name in
                    ('risk','urgency','interruption_cost') else .8, 'reason':'synthetic judgment'}
                    for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}
                for text in texts]}
        elif task == 'alive_source_support':
            bad = data['candidate']['text'].startswith('Bad')
            if mode in ('failure', 'partial-failure') and bad: raise RuntimeError('synthetic provider unavailable')
            if mode == 'cancel': raise asyncio.CancelledError()
            kwargs['route_info']['provider'] = 'synthetic-provider'
            document = {'verdict':'unsupported' if bad else 'supported',
                'unsupported_claims':['Invented prior communication.'] if bad else [],
                'uncertainties':[], 'reason':'Synthetic evidence comparison.'}
        elif task == 'alive_deliberation':
            assert all(not (c.get('content') or {}).get('operation', {}).get('text', '').startswith('Bad') for c in data)
            document = {'candidate_id':next(c['candidate_id'] for c in data
                if c['candidate_id'].startswith('opportunity-candidate:')), 'rationale':'supported contribution'}
        else:
            raise AssertionError(task)
        return SimpleNamespace(model='synthetic/main', choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(document)))])
    params = dict(subject='user:test', operation_id='grounded', policy_context=PolicyContext(can_interrupt=True),
        call=call, grounding=True, require_independent_grounding=mode == 'strict')
    if mode == 'strict': params['resolve_grounding_domain'] = lambda model:'synthetic-family'
    runtime = PlanningRuntime(journal)
    try:
        result = await runtime.run(**params)
    except asyncio.CancelledError:
        assert mode == 'cancel'
    except PlanningRuntimeError:
        assert mode in ('failure', 'strict')
    else:
        assert mode not in ('failure', 'cancel', 'strict')
        assert result.action_kind == ('silence' if mode == 'rejected' else 'share')
        if mode == 'repair': assert result.repair_interpretation_event_id
        if mode == 'repair-failure': assert result.repair_disposition == 'unavailable'
        if mode == 'partial-failure': assert any(v == 'review_unavailable' for _, v, _ in result.grounding_reviews)
        # Same-model reflection is not misrepresented as independent review.
        receipts = journal.read(event_type='opportunity.source_support_completed')
        assert receipts and all(not r.event.payload['independent_review'] for r in receipts)
        first = receipts[0]
        start = journal.get(first.event.causation_id)
        operation = start.event.causation_id.removeprefix('opportunity.synthesis:').removesuffix(':completed')
        assert SourceSupportReviewer(journal).verify_current(first.event.event_id,
            subject='user:test', interpretation_id=operation, candidate_id=first.event.payload['candidate_id']) is None
    count = len(calls)
    try:
        replay = await PlanningRuntime(ExperienceJournal(journal.path)).run(**params)
    except PlanningRuntimeError:
        assert mode in ('failure', 'cancel', 'strict')
    else:
        assert replay == result
    assert len(calls) == count, 'reopen implicitly repeated provider work'
    try:
        await runtime.run(**{**params, 'grounding':False, 'require_independent_grounding':False,
                             'resolve_grounding_domain':None})
    except PlanningRuntimeError:
        pass
    else:
        raise AssertionError('reopen silently bypassed grounded planning')
    assert len(calls) == count
    assert calls.count('alive_opportunity_candidates') <= 2
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.started')


async def preserve_original_repair_window(root):
    """Targeted correction retains admitted sibling evidence, never later reads."""
    journal=ExperienceJournal(root/'experience.sqlite3');owner='user:test'
    reader=DiscoveryOpportunityIngestor(journal)
    def ingest(source,title,summary,url,subject=owner):
        return reader.ingest(DiscoveryCandidate(source=source,title=title,summary=summary,
            url=url,observed_at=datetime.now(timezone.utc)),subject=subject)
    listing=ingest('synthetic listing','Workshop listing','Workshop exists; no venue metadata.',
        'https://example.invalid/workshop')
    page=ingest('synthetic page','Original workshop page','The confirmed venue is Site V.',
        'https://example.invalid/workshop')
    foreign=ingest('foreign source','FOREIGN_PRIVATE_SOURCE','Not part of this owner grant.',
        'https://example.invalid/foreign',subject='user:foreign')
    original_ids={listing.observation_event_id,page.observation_event_id}
    calls=[];future=[]
    async def call(**kwargs):
        task=kwargs['task'];calls.append(task)
        if task=='alive_deliberation':
            data=json.loads(kwargs['messages'][1]['content'].split('\n',1)[-1])
            assert all(c['agenda_item_id']==listing.agenda_item_id for c in data
                if c['candidate_id'].startswith('opportunity-candidate:'))
            value=dict(candidate_id=next(c['candidate_id'] for c in data
                if c['candidate_id'].startswith('opportunity-candidate:')),rationale='synthetic corrected contribution')
        else:
            data=json.loads(kwargs['messages'][1]['content'])
            assert 'FOREIGN_PRIVATE_SOURCE' not in kwargs['messages'][1]['content']
            if task=='alive_opportunity_candidates':
                repair=bool(data['corrective_reviews'])
                ids={e['observation_event_id'] for e in data['opportunities']}
                assert ids==original_ids,('repair lost admitted original evidence',repair,ids)
                assert not any(e.observation_event_id in ids for e in future)
                text='The venue is Site V.' if repair else 'The workshop has an invented organizer.'
                value=dict(candidates=[dict(agenda_item_id=listing.agenda_item_id,kind='share',
                    text=text,topic='synthetic',communication_plan=dict(version=2,recipient_goal='Explain the venue',
                        speech_act='inform',contents=[dict(kind='fact',text=text)],behavior_constraints=[]),
                    dimensions={k:dict(value=.1 if k in ('risk','urgency','interruption_cost') else .8,
                        reason='synthetic judgment') for k in (
                        'user_value','urgency','novelty','confidence','risk','interruption_cost')})])
                if repair:
                    # This sibling is admitted evidence, but was not a rejected
                    # action target. Corrective planning must not promote it.
                    value['candidates'].append({**value['candidates'][0],'agenda_item_id':page.agenda_item_id})
            elif task=='alive_source_support':
                assert {e['event_id'] for e in data['evidence']}==original_ids
                bad='invented' in data['candidate']['communication_plan']['contents'][0]['text']
                if bad and not future:
                    # Arrives during the original review but was never admitted
                    # into its source window. Must not join the corrective scope.
                    future.append(ingest('later source','LATER_UNADMITTED_SOURCE','New unrelated reading.',
                        'https://example.invalid/later'))
                kwargs['route_info']['provider']='synthetic-provider'
                value=dict(verdict='unsupported' if bad else 'supported',
                    unsupported_claims=['Organizer not evidenced.'] if bad else [],
                    uncertainties=[],reason='Synthetic original-page evidence comparison.')
            else:raise AssertionError(task)
        return SimpleNamespace(model='synthetic/reviewer' if task=='alive_source_support' else 'synthetic/generator',
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(value)))])
    params=dict(subject=owner,operation_id='retained-window',call=call,grounding=True,recipient_meaning=True,
        policy_context=PolicyContext(can_interrupt=True))
    result=await PlanningRuntime(journal).run(**params)
    assert result.action_kind=='share' and result.repair_disposition=='completed'
    assert result.repair_interpretation_event_id and len(future)==1
    repair_start=journal.get(result.repair_interpretation_event_id.removesuffix(':completed')+':started')
    assert set(repair_start.event.payload['observation_event_ids'])==original_ids
    assert foreign.observation_event_id not in repair_start.event.payload['observation_event_ids']
    assert future[0].observation_event_id not in repair_start.event.payload['observation_event_ids']
    spent=len(calls);before=journal.last_sequence()
    async def forbidden(**_):raise AssertionError('retained correction repeated inference')
    assert await PlanningRuntime(ExperienceJournal(journal.path)).run(**{**params,'call':forbidden})==result
    assert len(calls)==spent and journal.last_sequence()==before
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_started')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-grounded-planning-') as folder:
        for mode in ('repair','mixed','rejected','failure','partial-failure','cancel','strict','repair-failure'):
            asyncio.run(test(Path(folder) / mode, mode))
        asyncio.run(preserve_original_repair_window(Path(folder)/'retained-window'))
    print('HERMES_ALIVE_GROUNDED_PLANNING_RUNTIME_OK')
