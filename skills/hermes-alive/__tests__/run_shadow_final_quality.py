"""Shadow cognition uses final-source quality without a route or send grant."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal,AutonomyPolicyProjection,PolicyContext
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime
from run_alive_kernel_expression_runtime import scenario


async def exercise(root,mode):
    journal,params,expression=await scenario(root,'share',return_ready=True,grounding=True,single_family=True)
    owner='user:test'
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject=owner,actor=owner,expected_revision=0,enabled=True,
        context=PolicyContext(can_interrupt=True),operation_id='synthetic-enable'))
    calls=[]
    async def call(**kwargs):
        calls.append(kwargs['task'])
        if kwargs['task']!='alive_source_support':
            raise RuntimeError('synthetic repair unavailable')
        data=json.loads(kwargs['messages'][1]['content'])
        assert data['expression_binding']['stage']=='final_expression'
        assert data['candidate']['text']==expression.text
        if mode=='unavailable': raise RuntimeError('synthetic reviewer unavailable')
        kwargs['route_info']['provider']='synthetic-provider'
        return SimpleNamespace(model='synthetic/renderer',choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps(dict(verdict='unsupported' if mode=='unsupported' else 'supported',
                unsupported_claims=['Unverified action attribution.'] if mode=='unsupported' else [],
                uncertainties=[],reason='Synthetic quality fixture, not a semantic grade.'))))])
    def forbidden_route(*_): raise AssertionError('shadow tried to acquire a route')
    expression_parameters={k:v for k,v in params.items() if k not in ('subject','operation_id','policy_context')}
    expression_parameters['call']=call
    args=dict(subject=owner,operation_id=params['operation_id'],expression_parameters=expression_parameters,
        resolve_binding=forbidden_route)
    runtime=AutonomousCycleRuntime(journal)
    with patch.object(runtime.preparation.authorizer,'evaluate',side_effect=AssertionError('shadow authorized send')):
        try: result=await runtime.cycle(**args)
        except (ValueError,RuntimeError):
            assert mode=='unavailable'
        else:
            assert result.prepared is None and result.submission is None and not result.external_delivery_proven
            assessed=result.quality_assessment
            assert assessed is not None and not hasattr(assessed,'authorization')
            assert result.disposition==('content_review_attention' if mode=='unsupported' else 'shadow_selected')
            assert assessed.quality_disposition==('final_repair_unavailable' if mode=='unsupported' else 'supported')
            if mode=='unsupported':
                before_disable=len(calls)
                no_repair=await runtime.preparation.assess(allow_repair=False,**{**params,'call':call})
                assert no_repair.repair_disposition=='disabled' and len(calls)==before_disable
    before=len(calls)
    retries=[]
    async def forbidden_model(**_):
        retries.append(True)
        raise AssertionError('retained final quality retried inference')
    try:
        replay=await AutonomousCycleRuntime(ExperienceJournal(journal.path)).cycle(**{**args,
            'expression_parameters':{**expression_parameters,'call':forbidden_model}})
    except ValueError: assert mode=='unavailable'
    else: assert replay.disposition==result.disposition and replay.quality_assessment==result.quality_assessment
    assert len(calls)==before and not retries
    assert not journal.read(event_type='action.attempted') and not journal.read(event_type='action.authorization_evaluated')
    assert not journal.read(event_type='dispatch.externally_started')


with tempfile.TemporaryDirectory(prefix='alive-shadow-quality-') as folder:
    for mode in ('supported','unsupported','unavailable'):
        asyncio.run(exercise(Path(folder)/mode,mode))
print('HERMES_ALIVE_SHADOW_FINAL_QUALITY_OK')
