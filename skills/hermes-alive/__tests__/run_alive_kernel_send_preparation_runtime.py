#!/usr/bin/env python3
"""Composed expression/authorization with synthetic grants, never real sending."""
import asyncio
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ActionAuthority, AutonomyPolicyProjection, EventEnvelope,
                          ExperienceJournal, PolicyContext)
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel.action_authorization import ActionAuthorizationError
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario


async def exercise(root):
    journal, params, expressed = await scenario(root, 'share', return_ready=True,
                                              authority=ActionAuthority.USER_CONFIRMED)
    policy = AutonomyPolicyProjection(journal)
    record = policy.append_update(subject='user:test', actor='user:test', expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy')
    assert policy.apply(record).outcome == 'recorded'
    runtime = SendPreparationRuntime(journal)
    route = install_terminal_route(journal, subject='user:test', content_vault=runtime.vault)
    async def forbidden(**_):
        raise AssertionError('prepared expression caused new provider calls')
    current = {**params, 'call': forbidden}
    denied = await runtime.prepare(**current, authorization_operation_id='without-confirmation',
                                   route_binding_id=route)
    assert not denied.sent and not denied.authorization.authorized and denied.attempt_event_id is None
    assert not journal.read(event_type='action.attempted')
    wrong = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor='user:test', subject='user:test', payload={'synthetic': True,
        'authorizes_selection_event_id': expressed.planning.selection_event_id}))
    denied = await runtime.prepare(**current, authorization_operation_id='wrong-confirmation',
        route_binding_id=route, confirmation_event_id=wrong.event.event_id)
    assert not denied.authorization.authorized and not journal.read(event_type='action.attempted')
    confirmation = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor='user:test', subject='user:test', payload={'synthetic': True,
        'authorizes_selection_event_id': expressed.planning.selection_event_id,
        'authorizes_expression_event_id': expressed.expression_event_id}))
    valid = dict(current, authorization_operation_id='confirmed', route_binding_id=route,
                 confirmation_event_id=confirmation.event.event_id)
    prepared = await runtime.prepare(**valid)
    assert prepared.authorization.authorized, prepared.authorization.reasons
    assert prepared.attempt_event_id and not prepared.sent
    before = journal.last_sequence()
    reopened = SendPreparationRuntime(ExperienceJournal(journal.path))
    assert await reopened.prepare(**valid) == prepared
    assert journal.last_sequence() == before
    assert len(journal.read(event_type='action.attempted')) == 1
    revoked = policy.append_update(subject='user:test', actor='user:test', expected_revision=1,
        enabled=False, context=PolicyContext(can_interrupt=False), operation_id='disable')
    assert policy.apply(revoked).outcome == 'recorded'
    try:
        await reopened.prepare(**valid)
    except ActionAuthorizationError:
        pass
    else:
        raise AssertionError('changed canonical policy reused an old permit operation')
    refused = await reopened.prepare(**{**valid, 'authorization_operation_id': 'after-disable'})
    assert not refused.authorization.authorized and refused.attempt_event_id is None
    assert len(journal.read(event_type='action.attempted')) == 1
    assert not journal.read(event_type='dispatch.externally_started')
    assert not journal.read(event_type='outcome.recorded')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-send-preparation-') as folder:
        asyncio.run(exercise(Path(folder)))
    print('HERMES_ALIVE_KERNEL_SEND_PREPARATION_RUNTIME_OK')
