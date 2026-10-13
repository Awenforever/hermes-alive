#!/usr/bin/env python3
"""Selected generated input lifetime through real authorization/outbox APIs.

All user/model/host fixtures are synthetic. No transport is called or qualified.
"""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (ActionAuthority, AutonomyPolicyProjection, CognitionCycleCoordinator,
    DiscoveryCandidate, DiscoveryOpportunityIngestor, DispatchOutbox, DispatchOutboxError,
    EventEnvelope, ExperienceJournal, MemoryAuthority, MemoryKind, MemoryProjection,
    MemoryProposal, OpportunitySynthesizer, OutcomeProjection, PolicyContext,
    SendTimeAuthorizer, Sensitivity)
from alive_kernel_testkit import install_terminal_route
from alive_kernel.content_vault import ContentVault


def response(value):
    return SimpleNamespace(model='synthetic-model', choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(value)))])


async def scenario(root, mode, custom_context=False):
    journal = ExperienceJournal(root / 'journal.sqlite3')
    owner = 'user:test'
    reader = DiscoveryOpportunityIngestor(journal)
    source = reader.ingest(DiscoveryCandidate(source='synthetic-public-fixture', title='Repair recording',
        summary='Free repair recording. Notice unverified.', url='https://example.invalid/repair',
        observed_at=datetime.now(timezone.utc)), subject=owner)
    context_vault = ContentVault(root / 'separate-profile-vault') if custom_context else None
    memory = MemoryProjection(journal, content_vault=context_vault)
    inbound = EventEnvelope(event_type='conversation.inbound', source='synthetic', actor=owner,
        subject=owner, payload={'synthetic': True})
    journal.append(inbound)
    pref = MemoryProposal(kind=MemoryKind.PREFERENCE, subject=owner, predicate='profile.interest',
        value='household repair', authority=MemoryAuthority.USER_EXPLICIT,
        source_event_ids=(inbound.event_id,), confidence=1)
    memory.append_proposal(pref, actor=owner)
    async def generate(**kwargs):
        return response({'candidates': [{'agenda_item_id': source.agenda_item_id, 'kind': 'share',
            'text': 'Free repair recording. Notice unverified. https://example.invalid/repair',
            'topic': 'repair', 'dimensions': {name: {'value': .1 if name in
            ('risk','urgency','interruption_cost') else .9, 'reason': 'synthetic judgment'}
            for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]})
    # Trusted test-host metadata, NOT permission inferred by a model or installed
    # as a public default. The authorizer still requires a later exact confirmation.
    generated = await OpportunitySynthesizer(journal, context_vault=context_vault).run(subject=owner, operation_id='generate',
        authority=ActionAuthority.USER_CONFIRMED, call=generate)
    async def choose(**kwargs):
        return response({'candidate_id': generated.candidates[0].action.candidate_id,
                         'rationale': 'synthetic useful candidate'})
    coordinator = CognitionCycleCoordinator(journal, context_vault=context_vault)
    selected = await coordinator.plan_with_model(cycle_id='cycle', subject=owner,
        candidates=generated.candidates, policy_context=PolicyContext(can_interrupt=True), call=choose)
    policy = AutonomyPolicyProjection(journal)
    assert policy.apply(policy.append_update(subject=owner, actor=owner, expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy')).outcome == 'recorded'
    route = install_terminal_route(journal, subject=owner, content_vault=coordinator.vault)
    confirmation = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor=owner, subject=owner, payload={'synthetic': True,
        'authorizes_selection_event_id': selected.selection_event_id}))
    authorizer = SendTimeAuthorizer(journal, content_vault=coordinator.vault, route_binding_id=route,
                                   context_vault=context_vault)
    def invalidate():
        if mode.startswith('forget'):
            memory.forget_item(pref.proposal_id, actor=owner, request_id='forget')
        elif mode.startswith('erase'):
            reader.vault.erase_item(journal.get(source.observation_event_id).event.payload['content']['content_id'])
        elif mode == 'unrelated-ranking':
            for index in range(12):
                reader.ingest(DiscoveryCandidate(source='synthetic', title=f'Noise {index}',
                    summary='Unrelated notice.', url=f'https://example.invalid/noise-{index}',
                    priority_hint=1.0, observed_at=datetime.now(timezone.utc)), subject=owner)
    if mode.endswith('before-authorize') or mode == 'unrelated-ranking':
        invalidate()
    decision = authorizer.evaluate(selection_event_id=selected.selection_event_id, subject=owner,
        capability='hermes.channel.send', operation_id='authorize',
        confirmation_event_id=confirmation.event.event_id)
    if mode.endswith('before-authorize'):
        assert not decision.authorized, 'stale generated inputs were authorized'
        assert not journal.read(event_type='action.attempted')
        return
    assert decision.authorized, decision.reasons
    outcomes = OutcomeProjection(journal, content_vault=coordinator.vault)
    attempt = outcomes.append_attempt(authorization_event_id=decision.event_id,
        selection_event_id=selected.selection_event_id, candidate_id=decision.candidate_id,
        executor='hermes.channel.send', idempotency_key='synthetic-attempt',
        actor='system:synthetic-test', subject=owner, attempt_id='attempt')
    assert outcomes.apply(attempt).outcome == 'recorded'
    outbox = DispatchOutbox(journal, content_vault=coordinator.vault, context_vault=context_vault)
    outbox.reconcile()
    lease = outbox.acquire(worker_id='synthetic-worker')
    assert lease is not None
    if mode.endswith('before-begin'):
        invalidate()
        try:
            outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
        except DispatchOutboxError:
            assert not journal.read(event_type='dispatch.started')
            return
        raise AssertionError('stale generated inputs crossed the start boundary')
    execution = outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
    if mode.endswith('before-launch'):
        invalidate()
        try:
            outbox.validate_execution_for_launch(execution)
        except DispatchOutboxError:
            assert len(journal.read(event_type='dispatch.started')) == 1
            return
        raise AssertionError('stale generated inputs passed the launch boundary')
    outbox.validate_execution_for_launch(execution)
    assert execution.content['operation']['text'].startswith('Free repair recording.')
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='delivery.succeeded')
    assert not journal.read(event_type='dispatch.externally_started')


async def main(root):
    for mode in ('clean','unrelated-ranking','forget-before-authorize','erase-before-authorize',
                 'forget-before-begin','erase-before-begin','forget-before-launch','erase-before-launch'):
        await scenario(root / mode, mode)
    for mode in ('clean', 'forget-before-authorize', 'forget-before-begin', 'forget-before-launch'):
        await scenario(root / ('custom-' + mode), mode, custom_context=True)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-opportunity-execution-') as folder:
        asyncio.run(main(Path(folder)))
    print('HERMES_ALIVE_KERNEL_OPPORTUNITY_EXECUTION_OK')
