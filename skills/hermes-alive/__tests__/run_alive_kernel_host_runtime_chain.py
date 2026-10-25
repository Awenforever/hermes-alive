#!/usr/bin/env python3
"""Composed delegated runtime -> actual Hermes command -> synthetic local sink."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import AutonomyPolicyProjection, DispatchOutbox, PolicyContext, Sensitivity
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario


async def prepare(root, route_document):
    journal, params, result = await scenario(root, 'share', return_ready=True)
    policy = AutonomyPolicyProjection(journal)
    assert policy.apply(policy.append_update(subject='user:test', actor='user:test', expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy')).outcome == 'recorded'
    runtime = SendPreparationRuntime(journal)
    route = install_terminal_route(journal, subject='user:test', content_vault=runtime.vault,
                                   route_document=route_document)
    grant = ActionDelegationStore(journal).grant(subject='user:test', actor='user:test',
        policy_event_id=policy.current('user:test').event_id, route_binding_id=route,
        action_kinds=('share',), maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1), operation_id='grant',
        allow_natural_expression=True)
    async def forbidden(**_):
        raise AssertionError('host execution repeated model planning')
    prepared = await runtime.prepare(**{**params, 'call': forbidden},
        authorization_operation_id='prepare', route_binding_id=route,
        delegation_event_id=grant.event.event_id)
    assert prepared.authorization.authorized, prepared.authorization.reasons
    outbox = DispatchOutbox(journal, content_vault=runtime.vault)
    lease = outbox.acquire(worker_id='synthetic-host-worker')
    assert lease is not None
    expression = runtime.expression.store.resolve_model_candidate(result.expression_event_id)
    interpretation = result.planning.interpretation_event_id.removeprefix(
        'opportunity.synthesis:').removesuffix(':completed')
    return journal, outbox, lease, expression, result.text, interpretation, prepared, runtime


async def main(core, root):
    from run_alive_kernel_host_expression_chain import exercise
    return [await exercise(core, root / mode, mode, runtime_prepare=prepare)
            for mode in ('success', 'reject', 'partial', 'skip')]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-host-runtime-') as directory:
        print(json.dumps(asyncio.run(main(args.hermes_root.resolve(), Path(directory).resolve()))))
    print('HERMES_ALIVE_KERNEL_HOST_RUNTIME_CHAIN_OK')
