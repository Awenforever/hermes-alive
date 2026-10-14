#!/usr/bin/env python3
"""Generated wording context with real retained evidence, synthetic models only."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, Sensitivity
from alive_kernel.expression_history import ExpressionHistoryReader
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer, OpportunitySynthesisError
from run_alive_kernel_host_runtime_chain import prepare


async def test(root):
    route = {'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None}
    journal, outbox, lease, expression, text, _, prepared, runtime = await prepare(root, route)
    reader = ExpressionHistoryReader(journal, content_vault=runtime.vault)
    history = reader.read(subject='user:test', clearance=Sensitivity.PRIVATE)
    assert len(history) == 1 and history[0].event_id == expression.event_id
    assert history[0].excerpt == text[:480]
    assert history[0].to_prompt()['status'] == 'generated_wording_only_delivery_unknown'
    assert not reader.read(subject='user:other', clearance=Sensitivity.PRIVATE)
    assert not reader.read(subject='user:test', clearance=Sensitivity.PUBLIC)
    boundary = journal.get(expression.event_id).sequence
    assert not reader.read(subject='user:test', clearance=Sensitivity.PRIVATE, before_sequence=boundary)
    assert 'wording_excerpt' not in repr(history[0]) and text not in repr(history[0])
    # Copying a signed payload into a foreign owner's envelope cannot reveal text.
    original = journal.get(expression.event_id).event
    journal.append(replace(original, event_id='message.model_candidate:copied', subject='user:other'))
    assert not reader.read(subject='user:other', clearance=Sensitivity.PRIVATE)
    # Changing wording provenance without its authenticator is excluded.
    payload = dict(original.payload)
    payload['renderer_model'] = 'synthetic/spoof'
    journal.append(replace(original, event_id='message.model_candidate:forged', payload=payload))
    assert reader.read(subject='user:test', clearance=Sensitivity.PRIVATE) == history
    synthesizer = OpportunitySynthesizer(journal, content_vault=runtime.vault)
    async def call(**kw):
        prompt = json.loads(kw['messages'][1]['content'])
        assert prompt['recent_expression_history'] == [h.to_prompt() for h in history]
        assert 'NOT proof of send' in kw['messages'][0]['content']
        # Synthetic policy: prior wording exists, so no repeated contribution.
        return SimpleNamespace(model='synthetic/interpreter', choices=[SimpleNamespace(
            message=SimpleNamespace(content='{"candidates":[]}'))])
    result = await synthesizer.run(subject='user:test', operation_id='new-cycle', call=call)
    assert not result.candidates
    reopened = OpportunitySynthesizer(ExperienceJournal(journal.path), content_vault=runtime.vault)
    recovered = reopened.load_completed(subject='user:test', operation_id='new-cycle')
    assert recovered.receipt_event_id == result.receipt_event_id
    assert len(journal.read(event_type='dispatch.started')) == 0
    # Erasure invalidates the old context snapshot, never reconstructs wording.
    runtime.vault.erase_item(original.payload['content']['content_id'])
    assert not reader.read(subject='user:test', clearance=Sensitivity.PRIVATE)
    try:
        reopened.load_completed(subject='user:test', operation_id='new-cycle')
    except OpportunitySynthesisError:
        pass
    else:
        raise AssertionError('erased expression context recovered silently')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-expression-history-') as folder:
        asyncio.run(test(Path(folder)))
    print('HERMES_ALIVE_EXPRESSION_HISTORY_OK')
