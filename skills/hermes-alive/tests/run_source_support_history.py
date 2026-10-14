#!/usr/bin/env python3
"""Historical expression status reaches semantic review without send promotion."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.opportunity_synthesis import OpportunitySynthesizer
from alive_kernel.source_support import SourceSupportReviewer
from alive_kernel.events import Sensitivity
from run_alive_kernel_expression_runtime import scenario


def response(model, document):
    return SimpleNamespace(model=model, choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(document)))])


async def test(root):
    journal, _, _ = await scenario(root, 'share', return_ready=True)
    synth = OpportunitySynthesizer(journal)
    evidence = synth.reader.active_evidence(subject='user:test', clearance=Sensitivity.PRIVATE)
    async def generate(**_):
        return response('synthetic-generator', {'candidates':[{
            'agenda_item_id':evidence[0].agenda_item_id, 'kind':'share', 'topic':'repair',
            'text':'I already told you about this workshop.',
            'dimensions':{n:{'value':.5,'reason':'synthetic test'} for n in
                ('user_value','urgency','novelty','confidence','interruption_cost','risk')}}]})
    generated = await synth.run(subject='user:test', operation_id='history-review', call=generate)
    reviewer = SourceSupportReviewer(journal)
    async def review(**kwargs):
        snapshot = json.loads(kwargs['messages'][1]['content'])
        history = snapshot['recent_expression_history']
        assert len(history) == 1
        assert history[0]['status'] == 'generated_wording_only_delivery_unknown'
        assert 'Distinguish internal thought/draft' in kwargs['messages'][0]['content']
        kwargs['route_info']['provider'] = 'synthetic-review-provider'
        return response('synthetic-reviewer', {'verdict':'unsupported',
            'unsupported_claims':['Generated wording does not establish prior communication.'],
            'uncertainties':[], 'reason':'No sending evidence supplied.'})
    candidate_id = generated.candidates[0].action.candidate_id
    receipt = await reviewer.run(subject='user:test', interpretation_id='history-review',
        candidate_id=candidate_id, operation_id='review-history', call=review,
        resolve_domain=lambda model:model)
    assert receipt.verdict == 'unsupported' and not receipt.safe_for_automatic_delivery
    assert reviewer.verify_current(receipt.event_id, subject='user:test',
        interpretation_id='history-review', candidate_id=candidate_id)['verdict'] == 'unsupported'
    assert not journal.read(event_type='action.attempted')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-source-history-') as folder:
        asyncio.run(test(Path(folder)))
    print('HERMES_ALIVE_SOURCE_SUPPORT_HISTORY_OK')
