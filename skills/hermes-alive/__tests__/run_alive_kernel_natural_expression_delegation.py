#!/usr/bin/env python3
"""Explicit natural-expression grants through real authorization/start checks."""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (AutonomyPolicyProjection, DispatchOutbox, DispatchOutboxError,
                          ExperienceJournal, PolicyContext, Sensitivity)
from alive_kernel.action_delegation import ActionDelegationStore, ActionDelegationError
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario


async def exercise(root, mode):
    journal, params, expression = await scenario(root, 'share', return_ready=True)
    policy = AutonomyPolicyProjection(journal)
    assert policy.apply(policy.append_update(subject='user:test', actor='user:test', expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy')).outcome == 'recorded'
    runtime = SendPreparationRuntime(journal)
    route = install_terminal_route(journal, subject='user:test', content_vault=runtime.vault)
    grants = ActionDelegationStore(journal)
    grant_params = dict(subject='user:test', actor='user:test',
        policy_event_id=policy.current('user:test').event_id, route_binding_id=route,
        action_kinds=('share',), maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1), operation_id='grant')
    if mode == 'invalid':
        before = journal.last_sequence()
        try:
            grants.grant(**grant_params, allow_natural_expression='true')
        except ActionDelegationError:
            pass
        else:
            raise AssertionError('nonliteral permission accepted')
        assert journal.last_sequence() == before
        return
    grant = grants.grant(**grant_params, allow_natural_expression=mode != 'historical')
    if mode == 'historical':
        assert 'allow_natural_expression' not in grant.event.payload
    async def forbidden(**_):
        raise AssertionError('delegated preparation repeated models')
    prepared_params = dict(params, call=forbidden, authorization_operation_id='prepare',
        route_binding_id=route, delegation_event_id=grant.event.event_id)
    prepared = await runtime.prepare(**prepared_params)
    if mode == 'historical':
        assert not prepared.authorization.authorized and prepared.attempt_event_id is None
        assert not journal.read(event_type='action.attempted')
        return
    assert prepared.authorization.authorized, prepared.authorization.reasons
    assert prepared.attempt_event_id and not prepared.sent
    outbox = DispatchOutbox(journal, content_vault=runtime.vault)
    outbox.reconcile()
    lease = outbox.acquire(worker_id='synthetic-worker')
    assert lease is not None
    if mode == 'revoke':
        grants.revoke(delegation_event_id=grant.event.event_id, subject='user:test', actor='user:test')
        refused = await runtime.prepare(**prepared_params)
        assert not refused.authorization.authorized and refused.attempt_event_id is None
        try:
            outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError('revoked expression delegation started an action')
    else:
        execution = outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
        assert execution.content['operation']['text'] == expression.text
        if mode == 'revoke-after-start':
            grants.revoke(delegation_event_id=grant.event.event_id, subject='user:test', actor='user:test')
            try:
                outbox.validate_execution_for_launch(execution)
            except DispatchOutboxError:
                pass
            else:
                raise AssertionError('revocation between start and host launch was ignored')
        assert not journal.read(event_type='outcome.recorded')
    # Internal start evidence is not an actual host/channel launch or delivery.
    assert not journal.read(event_type='dispatch.externally_started')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-expression-delegation-') as folder:
        for mode in ('historical', 'allowed', 'revoke', 'invalid', 'revoke-after-start'):
            asyncio.run(exercise(Path(folder) / mode, mode))
    print('HERMES_ALIVE_KERNEL_NATURAL_EXPRESSION_DELEGATION_OK')
