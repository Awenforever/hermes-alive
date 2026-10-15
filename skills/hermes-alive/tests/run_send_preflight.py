#!/usr/bin/env python3
"""Route availability before inference; final authorization remains necessary."""
import asyncio
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import AutonomyPolicyProjection,PolicyContext,Sensitivity
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario


async def test(root):
    journal,params,expression=await scenario(root,'share',return_ready=True)
    runtime=SendPreparationRuntime(journal)
    calls=[]
    async def forbidden(**kwargs):
        calls.append(kwargs)
        raise AssertionError('invalid route spent on inference')
    args={**params,'operation_id':'new-preflight-operation','call':forbidden,
          'authorization_operation_id':'prepare','route_binding_id':'missing-route'}
    started=len(journal.read(event_type='opportunity.synthesis_started'))
    async def refuse(parameters):
        try: await runtime.prepare(**parameters)
        except ValueError as error:
            assert str(error)=='host route unavailable before planning'
        else: raise AssertionError('invalid host route was admitted')
        assert not calls
        assert len(journal.read(event_type='opportunity.synthesis_started'))==started
    await refuse(args)
    foreign=install_terminal_route(journal,subject='user:foreign',content_vault=runtime.vault)
    with patch.object(runtime.authorizer.host.vault,'resolve_json',
                      side_effect=AssertionError('foreign private locator accessed')):
        await refuse({**args,'route_binding_id':foreign})
    own=install_terminal_route(journal,subject='user:test',content_vault=runtime.vault)
    original=runtime.authorizer.host.get_binding(own)
    # A valid preflight cannot authorize a route erased during model work.
    policy=AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test',actor='user:test',expected_revision=0,
        enabled=True,context=PolicyContext(can_interrupt=True),operation_id='policy'))
    grant=ActionDelegationStore(journal).grant(subject='user:test',actor='user:test',
        policy_event_id=policy.current('user:test').event_id,route_binding_id=own,
        action_kinds=('share',),maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc)+timedelta(hours=1),operation_id='grant',allow_natural_expression=True)
    async def erase_after_preflight(**kwargs):
        runtime.vault.erase_item(original.route_reference.content_id)
        return expression
    with patch.object(runtime.expression,'run',erase_after_preflight):
        result=await runtime.prepare(**{**params,'call':forbidden},authorization_operation_id='late',
            route_binding_id=own,delegation_event_id=grant.event.event_id)
    assert result.authorization is not None and not result.authorization.authorized
    assert 'route_binding_content_unavailable' in result.authorization.reasons
    assert result.attempt_event_id is None and not calls
    await refuse({**args,'route_binding_id':own})
    assert not journal.read(event_type='dispatch.started')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-send-preflight-') as directory:
        asyncio.run(test(Path(directory)))
    print('HERMES_ALIVE_SEND_PREFLIGHT_OK')
