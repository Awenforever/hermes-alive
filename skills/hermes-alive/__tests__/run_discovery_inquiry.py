"""Reading-purpose continuity through actual agenda/read/planning composition.

Synthetic tools/models only; encrypted storage is real. Not a quality round.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ExperienceJournal, DiscoveryCandidate, DiscoveryOpportunityIngestor,
                          Sensitivity, PolicyContext)
from alive_kernel.agenda import AgendaAuthority, AgendaState
from alive_kernel.discovery_inquiry import DiscoveryInquiryContext, DiscoveryInquiryError
from alive_kernel.host_discovery import HostDiscoveryReader
from alive_kernel.opportunity_synthesis import OpportunitySynthesisError
from alive_kernel.planning_runtime import PlanningRuntime


async def exercise(root, mode):
    path = root / 'journal.sqlite3'
    journal = ExperienceJournal(path)
    ingestor = DiscoveryOpportunityIngestor(journal)
    seed = ingestor.ingest(DiscoveryCandidate(source='synthetic', title='Museum conservation',
        url='https://example.invalid/conservation', summary='A public conservation notice.'), subject='user:test')
    context = DiscoveryInquiryContext(ingestor)
    params = dict(item_id='inquiry:conservation', subject='user:test',
        question='PRIVATE_QUESTION: What changed in the conservation method?',
        value_hypothesis='A useful outside-profile history discovery, not an inferred preference.',
        source_event_ids=(seed.observation_event_id,), model_actor='model:synthetic',
        expected_context_digest=context.context_digest(subject='user:test'),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    expected = context.remember(**params)
    assert context.remember(**params) == expected  # Exact replay, no inference.
    assert expected['authority'] == 'tentative_model_note_not_user_instruction'
    assert not expected['grants_execution_or_disclosure']
    for changes in ({'subject':'user:other'}, {'clearance':Sensitivity.PUBLIC}):
        try:
            context.read(**dict(subject=changes.get('subject','user:test'),
                clearance=changes.get('clearance',Sensitivity.PRIVATE), item_ids=(params['item_id'],)))
        except DiscoveryInquiryError:
            pass
        else:
            raise AssertionError('reading task crossed owner/clearance boundary')

    tool_calls = []
    async def allowed(url): return url.startswith('https://example.invalid/')
    async def search(*args, **kwargs): raise AssertionError('no search granted')
    async def extract(urls, **kwargs):
        tool_calls.append(urls)
        return json.dumps(dict(results=[dict(url=urls[0], title='Museum conservation',
            content='The public notice describes a revised non-invasive method.')]))
    def host():
        return HostDiscoveryReader(ingestor,subject='user:test',search=search,extract=extract,
            allow_url=allowed,is_current=lambda:True)
    read_params = dict(operation_id='depth', read_urls=('https://example.invalid/conservation',),
                       inquiry_item_ids=(params['item_id'],))
    read_result = await host().collect(**read_params)
    assert await host().collect(**read_params) == read_result and len(tool_calls) == 1
    calls = []
    def withdraw():
        if mode == 'erasure':
            ingestor.vault.erase_item('agenda:' + params['item_id'])
        elif mode == 'source-erasure':
            source = journal.get(seed.observation_event_id)
            ingestor.vault.erase_item(source.event.payload['content']['content_id'])
        else:
            record = ingestor.agenda.append_transition(params['item_id'], AgendaState.DISMISSED,
                actor='model:synthetic',authority=AgendaAuthority.MODEL_PROPOSAL,
                source_event_id=seed.observation_event_id,reason='Question no longer useful')
            ingestor.agenda.apply(record)
    async def call(**kw):
        calls.append(kw['task'])
        data = json.loads(kw['messages'][1]['content'])
        assert data['tentative_discovery_tasks'] == [expected]
        assert not data['user_context']  # Reading rationale never becomes user memory.
        if mode == 'during-wait': withdraw()
        return SimpleNamespace(model='synthetic/model',choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"candidates":[]}'))])
    runtime = PlanningRuntime(journal, content_vault=ingestor.vault)
    run_params = dict(operation_id='compose',subject='user:test',call=call,
        policy_context=PolicyContext(can_interrupt=False),inquiry_item_ids=(params['item_id'],))
    if mode == 'during-wait':
        try: await runtime.run(**run_params)
        except OpportunitySynthesisError: pass
        else: raise AssertionError('withdrawn reading task admitted after model wait')
        assert len(calls) == 1
        assert not journal.read(event_type='opportunity.synthesis_completed')
    else:
        result = await runtime.run(**run_params)
        async def forbidden(**kw): raise AssertionError('completed interpretation called model again')
        reopened = PlanningRuntime(ExperienceJournal(path),content_vault=ingestor.vault)
        assert await reopened.run(**{**run_params,'call':forbidden}) == result
        assert len(calls) == 1
        withdraw()
        try: await reopened.run(**{**run_params,'call':forbidden})
        except (DiscoveryInquiryError, ValueError): pass
        else: raise AssertionError('withdrawn/erased reading context reused by planning')
    try: await host().collect(**read_params)
    except (DiscoveryInquiryError, ValueError): pass
    else: raise AssertionError('host read receipt reused withdrawn question')
    assert len(tool_calls) == 1
    for file in root.glob('journal.sqlite3*'):
        assert b'PRIVATE_QUESTION' not in file.read_bytes()
    assert not journal.read(event_type='action.attempted')


with tempfile.TemporaryDirectory(prefix='alive-inquiry-') as directory:
    for mode in ('withdrawal','erasure','source-erasure','during-wait'):
        root = Path(directory) / mode
        root.mkdir()
        asyncio.run(exercise(root, mode))
print('HERMES_ALIVE_DISCOVERY_INQUIRY_OK')
