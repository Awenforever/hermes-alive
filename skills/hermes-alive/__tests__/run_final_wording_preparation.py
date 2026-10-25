#!/usr/bin/env python3
"""Final exact wording is reviewed before an authorized attempt; no channel IO."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import AutonomyPolicyProjection, DispatchOutbox, DispatchOutboxError, ExperienceJournal, PolicyContext, Sensitivity
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel.events import _thaw_json
from alive_kernel.action_authorization import ActionAuthorizationError
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from alive_kernel.source_support import SourceSupportError
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario


async def test(root, mode):
    journal, params, expression = await scenario(root, 'share', return_ready=True,
        grounding=True, single_family=True)
    policy = AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test', actor='user:test', expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy'))
    runtime = SendPreparationRuntime(journal)
    route = install_terminal_route(journal, subject='user:test', content_vault=runtime.vault,
        route_document={'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None})
    grant = ActionDelegationStore(journal).grant(subject='user:test', actor='user:test',
        policy_event_id=policy.current('user:test').event_id, route_binding_id=route,
        action_kinds=('share',), maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1), operation_id='grant', allow_natural_expression=True)
    calls = []
    async def final_call(**kwargs):
        if mode == 'unsupported' and kwargs['task'] == 'alive_semantic_render':
            raise RuntimeError('synthetic repair provider unavailable')
        assert kwargs['task'] == 'alive_source_support'
        snapshot = json.loads(kwargs['messages'][1]['content'])
        assert snapshot['expression_binding']['stage'] == 'final_expression'
        assert snapshot['candidate']['text'] == expression.text
        calls.append(kwargs['task'])
        if mode == 'cancel': raise asyncio.CancelledError()
        kwargs['route_info']['provider'] = 'synthetic-provider'
        document = {'verdict':'unsupported' if mode == 'unsupported' else 'supported',
            'unsupported_claims':['Unsupported final wording.'] if mode == 'unsupported' else [],
            'uncertainties':[], 'reason':'Synthetic judgment only.'}
        return SimpleNamespace(model='synthetic/renderer', choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(document)))])
    args = {**params, 'call':final_call, 'authorization_operation_id':'prepare',
            'route_binding_id':route, 'delegation_event_id':grant.event.event_id}
    try:
        prepared = await runtime.prepare(**args)
    except asyncio.CancelledError:
        assert mode == 'cancel'
    else:
        assert prepared.final_review_event_id and len(calls) == 1
        if mode == 'unsupported':
            assert prepared.authorization is None and prepared.attempt_event_id is None
            assert prepared.quality_disposition == 'final_repair_unavailable'
            assert prepared.repair_disposition == 'unavailable'
        else:
            assert prepared.authorization.authorized and prepared.quality_disposition == 'supported'
    count = len(calls)
    async def forbidden(**_): raise AssertionError('reopen repeated final review')
    try:
        reopened = await SendPreparationRuntime(ExperienceJournal(journal.path)).prepare(**{**args, 'call':forbidden})
    except ValueError:
        assert mode == 'cancel'
    else:
        assert reopened == prepared
    assert len(calls) == count
    if mode in ('supported', 'launch'):
        outbox = DispatchOutbox(journal, content_vault=runtime.vault)
        lease = outbox.acquire(worker_id='synthetic-worker')
        runtime._validate_prepared_lease(prepared, lease)
        permit = journal.get(prepared.authorization.event_id)
        witness = _thaw_json(permit.event.payload['final_wording_witness'])
        assert witness['review_event_id'] == prepared.final_review_event_id
        outbox._validate_selection_inputs(permit)
        if mode == 'launch':
            execution = outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
            assert execution.lease == lease and len(journal.read(event_type='dispatch.started')) == 1
            # This only crosses the local outbox boundary; no adapter is invoked.
            return
        reviewer = ExpressionSourceSupportReviewer(journal, content_vault=runtime.vault)
        for altered in ({**witness, 'require_independence':True},
                        {**witness, 'interpretation_id':'foreign-origin'},
                        {**witness, 'review_event_id':expression.planning.grounding_reviews[0][2]}):
            try:
                reviewer.require_current_witness(altered, subject='user:test',
                    expression_event_id=expression.expression_event_id,
                    selection_event_id=expression.planning.selection_event_id)
            except SourceSupportError: pass
            else: raise AssertionError('substituted witness accepted')
        authorize = dict(selection_event_id=expression.planning.selection_event_id,
            subject='user:test', capability='hermes.channel.send', operation_id='prepare',
            route_binding_id=route, delegation_event_id=grant.event.event_id,
            expression_event_id=expression.expression_event_id)
        try: runtime.authorizer.evaluate(**authorize)
        except ActionAuthorizationError: pass
        else: raise AssertionError('reopened permit silently dropped quality requirement')
        record = journal.get(prepared.final_review_event_id)
        runtime.vault.erase_item(record.event.payload['content']['content_id'])
        try: runtime._validate_prepared_lease(prepared, lease)
        except DispatchOutboxError: pass
        else: raise AssertionError('erased final support remained executable')
        denied = runtime.authorizer.evaluate(**authorize, final_wording_witness=witness)
        assert not denied.authorized and 'final_wording_not_current' in denied.reasons
        # Bypassing SendPreparationRuntime still cannot launch the retained attempt.
        try: outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
        except DispatchOutboxError: pass
        else: raise AssertionError('core outbox bypassed erased final review')
    else:
        assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.started')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-final-wording-') as folder:
        for mode in ('supported', 'unsupported', 'cancel', 'launch'):
            asyncio.run(test(Path(folder) / mode, mode))
    print('HERMES_ALIVE_FINAL_WORDING_PREPARATION_OK')
