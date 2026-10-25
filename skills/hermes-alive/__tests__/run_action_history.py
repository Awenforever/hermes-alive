#!/usr/bin/env python3
"""Recorded intent -> canonical outcome -> fresh cognition, synthetic IO only."""
import asyncio
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, Sensitivity
from alive_kernel.action_history import ActionHistoryReader
from alive_kernel.outcomes import OutcomeKind
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer, OpportunitySynthesisError
from alive_kernel_testkit import authenticated_dispatch_receipt
from run_alive_kernel_host_runtime_chain import prepare


async def test(root):
    journal,_,_,expression,text,_,prepared,runtime = await prepare(root,
        {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None})
    reader = ActionHistoryReader(journal,content_vault=runtime.vault)
    def read(): return reader.read(subject='user:test',clearance=Sensitivity.PRIVATE)
    initial = read()
    assert ActionHistoryReader(ExperienceJournal(journal.path),content_vault=runtime.vault).read(
        subject='user:test',clearance=Sensitivity.PRIVATE) == initial
    assert len(initial) == 1 and initial[0].attempt_event_id == prepared.attempt_event_id
    assert initial[0].expression_event_id == expression.event_id
    assert not initial[0].outcomes and text not in repr(initial[0])
    assert initial[0].to_prompt()['execution_and_queue_membership'] == 'not_assessed'
    assert not reader.read(subject='user:other',clearance=Sensitivity.PRIVATE)
    assert not reader.read(subject='user:test',clearance=Sensitivity.PUBLIC)
    attempt = journal.get(prepared.attempt_event_id)
    assert not reader.read(subject='user:test',clearance=Sensitivity.PRIVATE,
                           before_sequence=attempt.sequence)
    journal.append(replace(attempt.event,event_id='action.attempt:foreign',subject='user:other'))
    assert not reader.read(subject='user:other',clearance=Sensitivity.PRIVATE)
    with closing(runtime.outcomes._connect()) as connection:
        connection.execute('UPDATE action_attempts_v1 SET candidate_id=? WHERE event_id=?',
                           ('forged',attempt.event.event_id))
    assert not read()
    with closing(runtime.outcomes._connect()) as connection:
        connection.execute('UPDATE action_attempts_v1 SET candidate_id=? WHERE event_id=?',
                           (attempt.event.payload['candidate_id'],attempt.event.event_id))
    assert read() == initial
    synth = OpportunitySynthesizer(journal,content_vault=runtime.vault)
    async def call(**kw):
        data = json.loads(kw['messages'][1]['content'])
        assert data['recent_action_history'] == [a.to_prompt() for a in read()]
        return SimpleNamespace(model='synthetic/interpreter',choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"candidates":[]}'))])
    await synth.run(subject='user:test',operation_id='before-result',call=call)
    assert synth.load_completed(subject='user:test',operation_id='before-result')
    receipt = authenticated_dispatch_receipt(journal,attempt,event_id='synthetic:delivered')
    outcome = runtime.outcomes.append_outcome(attempt_id=attempt.event.payload['attempt_id'],
        kind=OutcomeKind.DELIVERY_SUCCEEDED,subject='user:test',source_event_id=receipt.event_id,
        details={'synthetic':True},actor='system:test',outcome_id='synthetic-delivered')
    assert runtime.outcomes.apply(outcome).outcome == 'recorded'
    current = read()
    assert current[0].outcomes == ((outcome.event.event_id,'delivery_succeeded',
                                   outcome.event.observed_at.isoformat()),)
    try: synth.load_completed(subject='user:test',operation_id='before-result')
    except OpportunitySynthesisError: pass
    else: raise AssertionError('new outcome left the old decision context current')
    await synth.run(subject='user:test',operation_id='after-result',call=call)
    assert synth.load_completed(subject='user:test',operation_id='after-result')
    async def erase_while_awaiting(**kw):
        response = await call(**kw)
        runtime.outcomes.content_vault.erase_item(outcome.event.payload['content']['content_id'])
        return response
    try:
        await synth.run(subject='user:test',operation_id='erase-during-await',call=erase_while_awaiting)
    except OpportunitySynthesisError: pass
    else: raise AssertionError('model completion ignored an outcome erased during await')
    assert journal.get('opportunity.synthesis:erase-during-await:completed') is None
    assert not read()[0].outcomes
    try: synth.load_completed(subject='user:test',operation_id='after-result')
    except OpportunitySynthesisError: pass
    else: raise AssertionError('erased outcome remained usable decision context')
    runtime.vault.erase_item(journal.get(expression.event_id).event.payload['content']['content_id'])
    assert not read()


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-action-history-') as folder:
        asyncio.run(test(Path(folder)))
    print('HERMES_ALIVE_ACTION_HISTORY_OK')
