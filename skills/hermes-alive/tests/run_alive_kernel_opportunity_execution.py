#!/usr/bin/env python3
"""Selected generated input lifetime through real authorization/outbox APIs.

All user/model/host fixtures are synthetic. No transport is called or qualified.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
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
from alive_kernel.opportunity_expression import OpportunityExpressionStore
from alive_kernel.action_authorization import ActionAuthorizationError
from alive_kernel.action_delegation import ActionDelegationStore


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
            'text': 'Free repair recording. Notice unverified.' if mode in ('source-provenance', 'expression-source-provenance')
                    else 'Free repair recording. Notice unverified. https://example.invalid/repair',
            'topic': 'repair', 'dimensions': {name: {'value': .1 if name in
            ('risk','urgency','interruption_cost') else .9, 'reason': 'synthetic judgment'}
            for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')}}]})
    # Trusted test-host metadata, NOT permission inferred by a model or installed
    # as a public default. The authorizer still requires a later exact confirmation.
    generated = await OpportunitySynthesizer(journal, context_vault=context_vault).run(subject=owner, operation_id='generate',
        authority=ActionAuthority.USER_DELEGATED if mode.startswith('delegated') else ActionAuthority.USER_CONFIRMED, call=generate)
    async def choose(**kwargs):
        return response({'candidate_id': generated.candidates[0].action.candidate_id,
                         'rationale': 'synthetic useful candidate'})
    coordinator = CognitionCycleCoordinator(journal, context_vault=context_vault)
    selected = await coordinator.plan_with_model(cycle_id='cycle', subject=owner,
        candidates=generated.candidates, policy_context=PolicyContext(can_interrupt=True), call=choose)
    original_frame_bytes = journal.get(selected.frame_event_id).event.canonical_json()
    if mode in ('source-provenance', 'expression-source-provenance'):
        assert generated.candidates[0].content['operation']['text'] == (
            'Free repair recording. Notice unverified.\n\n[来源](<https://example.invalid/repair>)')
    policy = AutonomyPolicyProjection(journal)
    assert policy.apply(policy.append_update(subject=owner, actor=owner, expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy')).outcome == 'recorded'
    route = install_terminal_route(journal, subject=owner, content_vault=coordinator.vault)
    delegation = None
    if mode.startswith('delegated'):
        delegation = ActionDelegationStore(journal).grant(subject=owner, actor=owner,
            policy_event_id=policy.current(owner).event_id,
            route_binding_id='other-route' if mode == 'delegated-wrong-route' else route,
            action_kinds=('ask',) if mode == 'delegated-wrong-kind' else ('share',),
            maximum_sensitivity=Sensitivity.PUBLIC if mode == 'delegated-wrong-clearance' else Sensitivity.PRIVATE,
            minimum_interval_seconds=0 if mode.startswith('delegated-concurrent') else 3600,
            max_starts_per_24h=1 if mode == 'delegated-concurrent-cadence' else 3,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1), operation_id='delegation')
    expression = None
    expressed_text = 'You might like this free repair recording; the notice is unverified. https://example.invalid/repair'
    if mode.startswith('expression'):
        expressions = OpportunityExpressionStore(journal, content_vault=coordinator.vault,
                                                context_vault=context_vault)
        meaning = expressions.define_for_selection(selection_event_id=selected.selection_event_id, subject=owner)
        expression = expressions.record_model_candidate(selection_event_id=selected.selection_event_id,
            meaning_event_id=meaning.event.event_id, subject=owner, text=expressed_text,
            renderer_execution_id='synthetic-expression', renderer_model='synthetic-renderer',
            renderer_independence_domain='synthetic-family')
    confirmation_payload = {'synthetic': True, 'authorizes_selection_event_id': selected.selection_event_id}
    if expression is not None and mode != 'expression-unconfirmed':
        confirmation_payload['authorizes_expression_event_id'] = expression.event_id
    confirmation = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
        actor=owner, subject=owner, payload=confirmation_payload))
    authorizer = SendTimeAuthorizer(journal, content_vault=coordinator.vault, route_binding_id=route,
                                   context_vault=context_vault)
    def invalidate():
        if mode.startswith('delegated-revoke'):
            ActionDelegationStore(journal).revoke(delegation_event_id=delegation.event.event_id,
                                                 subject=owner, actor=owner)
        elif mode.startswith('forget'):
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
        confirmation_event_id=None if delegation else confirmation.event.event_id,
        expression_event_id=expression.event_id if expression else None,
        delegation_event_id=delegation.event.event_id if delegation else None)
    if mode in ('delegated-wrong-route', 'delegated-wrong-kind', 'delegated-wrong-clearance'):
        assert not decision.authorized and 'delegation_not_current' in decision.reasons
        return
    if mode == 'expression-unconfirmed':
        assert not decision.authorized and 'exact_expression_confirmation_required' in decision.reasons
        assert not journal.read(event_type='action.attempted')
        return
    if mode.endswith('before-authorize'):
        assert not decision.authorized, 'stale generated inputs were authorized'
        assert not journal.read(event_type='action.attempted')
        return
    assert decision.authorized, decision.reasons
    if mode == 'delegated-revoke-replay':
        ActionDelegationStore(journal).revoke(delegation_event_id=delegation.event.event_id,
                                             subject=owner, actor=owner)
        replay = authorizer.evaluate(selection_event_id=selected.selection_event_id, subject=owner,
            capability='hermes.channel.send', operation_id='authorize',
            confirmation_event_id=None, delegation_event_id=delegation.event.event_id)
        assert not replay.authorized and 'delegation_not_current' in replay.reasons
        return
    if mode == 'expression':
        try:
            authorizer.evaluate(selection_event_id=selected.selection_event_id, subject=owner,
                capability='hermes.channel.send', operation_id='authorize',
                confirmation_event_id=confirmation.event.event_id)
        except ActionAuthorizationError:
            pass
        else:
            raise AssertionError('authorization operation silently changed from expression to original draft')
    if mode == 'replay-after-forget':
        memory.forget_item(pref.proposal_id, actor=owner, request_id='forget-replay')
        replay = authorizer.evaluate(selection_event_id=selected.selection_event_id, subject=owner,
            capability='hermes.channel.send', operation_id='authorize',
            confirmation_event_id=confirmation.event.event_id)
        assert not replay.authorized and 'selection_inputs_not_current' in replay.reasons
        assert replay.event_id == decision.event_id
        return
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
    if mode.startswith('delegated-concurrent'):
        second = outcomes.append_attempt(authorization_event_id=decision.event_id,
            selection_event_id=selected.selection_event_id, candidate_id=decision.candidate_id,
            executor='hermes.channel.send', idempotency_key='synthetic-attempt-2',
            actor='system:synthetic-test', subject=owner, attempt_id='attempt-2')
        assert outcomes.apply(second).outcome == 'recorded'
        outbox.reconcile()
        second_lease = outbox.acquire(worker_id='synthetic-worker-2')
        assert second_lease is not None
        def start(item):
            try:
                worker = DispatchOutbox(journal, content_vault=coordinator.vault)
                execution = worker.begin_execution(item, clearance=Sensitivity.PRIVATE)
                worker.validate_execution_for_launch(execution)
                return execution
            except DispatchOutboxError as exc:
                assert 'budget exhausted' in str(exc), str(exc)
                return None
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(start, (lease, second_lease)))
        expected_starts = 1 if mode == 'delegated-concurrent-cadence' else 2
        assert sum(result is not None for result in results) == expected_starts
        assert len(journal.read(event_type='dispatch.started')) == expected_starts
        assert not journal.read(event_type='delivery.succeeded')
        return
    if mode.endswith('before-begin'):
        invalidate()
        try:
            outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
        except DispatchOutboxError:
            assert not journal.read(event_type='dispatch.started')
            return
        raise AssertionError('stale generated inputs crossed the start boundary')
    execution = outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
    if mode == 'expression-erased-before-launch':
        header = journal.get(expression.event_id)
        coordinator.vault.erase_item(header.event.payload['content']['content_id'])
        try:
            outbox.validate_execution_for_launch(execution)
        except DispatchOutboxError:
            assert len(journal.read(event_type='dispatch.started')) == 1
            return
        raise AssertionError('erased expression launched from retained executable copy')
    if mode.endswith('before-launch'):
        invalidate()
        try:
            outbox.validate_execution_for_launch(execution)
        except DispatchOutboxError:
            assert len(journal.read(event_type='dispatch.started')) == 1
            return
        raise AssertionError('stale generated inputs passed the launch boundary')
    outbox.validate_execution_for_launch(execution)
    assert journal.get(selected.frame_event_id).event.canonical_json() == original_frame_bytes
    assert 'https://example.invalid/repair' in execution.content['operation']['text']
    if mode == 'source-provenance':
        assert execution.content == generated.candidates[0].content
    if expression:
        assert execution.content['operation']['text'] == expressed_text
        original = coordinator.deliberation.inspect(journal.get(selected.selection_event_id).event.payload['frame_id'],
                                                    clearance=Sensitivity.PRIVATE)
        assert dict(original.candidate_contents)[generated.candidates[0].action.content_id]['operation']['text'].startswith('Free repair recording.')
    else:
        assert execution.content['operation']['text'].startswith('Free repair recording.')
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert not journal.read(event_type='delivery.succeeded')
    assert not journal.read(event_type='dispatch.externally_started')


async def main(root):
    for mode in ('clean','source-provenance','expression-source-provenance','unrelated-ranking','forget-before-authorize','erase-before-authorize',
                 'forget-before-begin','erase-before-begin','forget-before-launch','erase-before-launch'):
        await scenario(root / mode, mode)
    for mode in ('clean', 'forget-before-authorize', 'forget-before-begin', 'forget-before-launch'):
        await scenario(root / ('custom-' + mode), mode, custom_context=True)
    for mode in ('expression', 'expression-unconfirmed', 'expression-erased-before-launch', 'replay-after-forget'):
        await scenario(root / mode, mode)
    for mode in ('delegated-clean', 'delegated-revoke-before-authorize', 'delegated-revoke-before-begin',
                 'delegated-revoke-before-launch', 'delegated-revoke-replay', 'delegated-wrong-route',
                 'delegated-wrong-kind', 'delegated-wrong-clearance', 'delegated-concurrent-cadence',
                 'delegated-concurrent-allowed'):
        await scenario(root / mode, mode)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-opportunity-execution-') as folder:
        asyncio.run(main(Path(folder)))
    print('HERMES_ALIVE_KERNEL_OPPORTUNITY_EXECUTION_OK')
