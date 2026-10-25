"""Narrow initial rejection -> existing bounded correction, never a review bypass."""
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from run_final_wording_repair import test
from run_alive_kernel_expression_runtime import scenario
from alive_kernel.send_preparation_runtime import SendPreparationRuntime


async def negative(root,*,critical=False):
    journal,parameters,original=await scenario(root,'share',return_ready=True,
        grounding=True,single_family=True,semantic_additions=not critical,semantic_speech_shift=critical)
    calls=[]
    async def source_only(**kw):
        assert not critical,'critical meaning rejection must not spend on repair'
        assert kw['task']=='alive_source_support'
        calls.append(kw['task']);kw['route_info']['provider']='synthetic-provider'
        return SimpleNamespace(model='synthetic/renderer',choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({'verdict':'supported','unsupported_claims':[],
                'uncertainties':[],'reason':'Synthetic conflict with the first review.'})))])
    result=await SendPreparationRuntime(journal).assess(**{**parameters,'call':source_only})
    assert result.quality_disposition=='final_semantic_rejected'
    assert result.expression.expression_event_id==original.expression_event_id
    assert len(calls)==(0 if critical else 1)
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.started')


async def main(root):
    for mode in ('supported','rejected-again','cancel','review-cancel','proof-erased'):
        await test(root/mode,mode,initial_semantic_rejected=True)
    await negative(root/'review-conflict')
    await negative(root/'critical',critical=True)


with tempfile.TemporaryDirectory(prefix='alive-initial-semantic-repair-') as directory:
    asyncio.run(main(Path(directory)))
print('HERMES_ALIVE_INITIAL_SEMANTIC_REPAIR_OK')
