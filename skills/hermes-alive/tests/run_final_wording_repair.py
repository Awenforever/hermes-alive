#!/usr/bin/env python3
"""One evidence-bound final rewrite, re-review and recovery; no transport IO."""
import asyncio
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import (AutonomyPolicyProjection, DispatchOutbox, DispatchOutboxError,
                          ExperienceJournal, PolicyContext, Sensitivity)
from alive_kernel.action_delegation import ActionDelegationStore
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from alive_kernel.send_preparation_runtime import SendPreparationRuntime
from alive_kernel.expression_runtime import ExpressionRuntime
from alive_kernel.source_support import SourceSupportError
from alive_kernel_testkit import install_terminal_route
from run_alive_kernel_expression_runtime import scenario


async def test(root, mode):
    journal, params, original = await scenario(root, 'share', return_ready=True,
        grounding=True, single_family=True, render_prefix='I told you yesterday. ')
    policy = AutonomyPolicyProjection(journal)
    policy.apply(policy.append_update(subject='user:test', actor='user:test', expected_revision=0,
        enabled=True, context=PolicyContext(can_interrupt=True), operation_id='policy'))
    runtime = SendPreparationRuntime(journal)
    route = install_terminal_route(journal, subject='user:test', content_vault=runtime.vault,
        route_document={'platform':'weixin','profile':'synthetic','chat_id':'peer','thread_id':None})
    grant = ActionDelegationStore(journal).grant(subject='user:test', actor='user:test',
        policy_event_id=policy.current('user:test').event_id, route_binding_id=route,
        action_kinds=('share',), maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1), operation_id='grant',
        allow_natural_expression=True)
    calls = []

    async def call(**kwargs):
        task = kwargs['task']
        calls.append(task)
        data = json.loads(kwargs['messages'][1]['content'])
        kwargs['route_info']['provider'] = 'synthetic-provider'
        if task == 'alive_source_support':
            initial = data['candidate']['id'] == original.expression_event_id
            assert initial or 'I told you yesterday.' not in data['candidate']['text']
            bad = initial or mode == 'rejected-again'
            value = {'verdict':'unsupported' if bad else 'supported',
                'unsupported_claims':['Prior communication is not evidenced.'] if bad else [],
                'uncertainties':[], 'reason':'Synthetic source judgment, not real semantic proof.'}
        elif task == 'alive_semantic_render':
            correction = data['correction']
            assert correction['findings_are_not_new_facts']
            assert correction['previous_expression_event_id'] == original.expression_event_id
            if mode == 'cancel': raise asyncio.CancelledError()
            if mode == 'erase':
                review = journal.get(correction['review_event_id'])
                runtime.vault.erase_item(review.event.payload['content']['content_id'])
            value = '\n'.join(atom['text'] for atom in data['meaning']['atoms'])
            return SimpleNamespace(model='synthetic/renderer', choices=[SimpleNamespace(
                message=SimpleNamespace(content=value))])
        elif task == 'alive_semantic_review':
            value = {'atom_reviews':[{'atom_id':a['atom_id'], 'preserved':True, 'risks':[]}
                for a in data['meaning']['atoms']], 'added_claims_detected':False,
                'speech_act_preserved':True, 'protected_literals_preserved':True}
        else:
            raise AssertionError('unexpected additional model task: ' + task)
        return SimpleNamespace(model='synthetic/renderer', choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(value)))])

    args = {**params, 'call':call, 'authorization_operation_id':'prepare',
        'route_binding_id':route, 'delegation_event_id':grant.event.event_id}
    if mode == 'confirmed': args['confirmation_event_id'] = 'synthetic:exact-body-confirmation'
    try:
        prepared = await runtime.prepare(**args)
    except asyncio.CancelledError:
        assert mode == 'cancel'
        prepared = None
    else:
        if mode == 'supported':
            assert prepared.repair_disposition == 'completed'
            assert prepared.quality_disposition == 'supported' and prepared.authorization.authorized
            assert prepared.initial_final_review_event_id != prepared.final_review_event_id
            assert prepared.expression.expression_event_id != original.expression_event_id
            assert 'I told you yesterday.' not in prepared.expression.text
            permit = journal.get(prepared.authorization.event_id)
            assert permit.event.payload['expression_event_id'] == prepared.expression.expression_event_id
            assert permit.event.payload['final_wording_witness']['review_event_id'] == prepared.final_review_event_id
        else:
            assert prepared.authorization is None and prepared.attempt_event_id is None
            if mode == 'confirmed': assert prepared.repair_disposition == 'requires_new_confirmation'
            elif mode == 'erase': assert prepared.repair_disposition == 'unavailable'
            else:
                assert mode == 'rejected-again' and prepared.quality_disposition == 'final_unsupported'
                reviewer = ExpressionSourceSupportReviewer(journal, content_vault=runtime.vault)
                try:
                    reviewer.correction_context(prepared.final_review_event_id, subject='user:test',
                        selection_event_id=original.planning.selection_event_id)
                except SourceSupportError: pass
                else: raise AssertionError('repair of a repaired expression was allowed')
    count = len(calls)
    assert count == (1 if mode == 'confirmed' else 2 if mode in ('cancel','erase') else 4)
    forbidden_calls = []
    async def forbidden(**kwargs):
        # prepare() deliberately contains repair failures. A raised assertion
        # alone can therefore be swallowed and cannot prove zero provider spend.
        forbidden_calls.append(kwargs['task'])
        raise AssertionError('recovery repeated a provider call')
    try:
        reopened = await SendPreparationRuntime(ExperienceJournal(journal.path)).prepare(**{**args, 'call':forbidden})
    except ValueError:
        assert mode == 'erase'
    else:
        if mode == 'cancel':
            assert reopened.attempt_event_id is None and reopened.repair_disposition == 'unavailable'
        else: assert reopened == prepared
    assert len(calls) == count
    assert not forbidden_calls, forbidden_calls
    if mode == 'supported':
        reviewer = ExpressionSourceSupportReviewer(journal, content_vault=runtime.vault)
        _owner, origin, clearance = runtime._expression_origin(original)
        alternate = await reviewer.run(subject='user:test', interpretation_id=origin,
            candidate_id=original.expression_event_id, operation_id='alternate-negative',
            call=call, resolve_domain=lambda _:'unqualified-family', require_independence=False,
            clearance=clearance)
        try:
            await ExpressionRuntime(journal).run(**{**params, 'call':forbidden,
                'correction_review_event_id':alternate.event_id})
        except ValueError: pass
        else: raise AssertionError('another critique opened a sibling repair generation')
        assert len(calls) == count + 1
        assert not forbidden_calls, forbidden_calls
        try:
            reviewer.correction_context(prepared.final_review_event_id, subject='user:test',
                selection_event_id=original.planning.selection_event_id)
        except SourceSupportError: pass
        else: raise AssertionError('a positive review opened another correction')
        # Final support must retain the correction ancestry at the core boundary,
        # not merely while the rendering coroutine is active.
        outbox = DispatchOutbox(journal, content_vault=runtime.vault)
        permit = journal.get(prepared.authorization.event_id)
        outbox._validate_selection_inputs(permit)
        initial = journal.get(prepared.initial_final_review_event_id)
        runtime.vault.erase_item(initial.event.payload['content']['content_id'])
        try: outbox._validate_selection_inputs(permit)
        except DispatchOutboxError: pass
        else: raise AssertionError('dispatch ignored erased correction ancestry')
    assert not journal.read(event_type='dispatch.started')


if __name__ == '__main__':
    modes = ('supported','rejected-again','cancel','erase','confirmed')
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=modes)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-final-repair-') as folder:
        for mode in ((args.mode,) if args.mode else modes):
            asyncio.run(test(Path(folder) / mode, mode))
    print('HERMES_ALIVE_FINAL_WORDING_REPAIR_OK')
