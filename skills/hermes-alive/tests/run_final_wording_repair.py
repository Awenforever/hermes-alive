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
from alive_kernel.events import EventEnvelope, _thaw_json
from alive_kernel.localized_correction import METHOD, CORRECTION_PROMPT
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
            assert kwargs['messages'][0]['content']==CORRECTION_PROMPT if mode!='legacy' else 'issues' not in data
            if mode=='legacy':
                value='\n'.join(atom['text'] for atom in data['meaning']['atoms'])
                return SimpleNamespace(model='synthetic/renderer',choices=[SimpleNamespace(message=SimpleNamespace(content=value))])
            assert data['issues']==correction['findings']['unsupported_claims']+correction['findings']['uncertainties']
            value={'edits':[dict(exact_text='I told you yesterday. ',claim_index=0,replacement='')]}
            if mode=='abstain':value={'abstain':True}
            if mode=='malformed':value={'edits':[]}
            if mode=='unanchored':value['edits'][0]['exact_text']='not in original'
            if mode=='whole-text':value['edits'][0]['exact_text']=original.text
            if mode=='protected':value['edits'][0]['exact_text']='https://example.invalid/workshop'
            if mode=='injected-offset':value['edits'][0]['start']=0
            return SimpleNamespace(model='synthetic/renderer', choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(value)))])
        elif task == 'alive_semantic_review':
            if mode=='review-cancel':raise asyncio.CancelledError()
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
    if mode in ('legacy','legacy-failed'):
        # Seed an actual historical start under its old contract before recovery,
        # not a caller-selected switch enabling whole-authoring for new starts.
        review_id,_=await runtime._review_final(original,{**params,'call':call})
        context=runtime.expression.comparator._correction(review_id,'user:test',original.planning.selection_event_id)
        original_start=journal.get('expression.runtime:'+runtime.vault.digest_json(
            {'selection':original.planning.selection_event_id})[:40]+':started')
        digest=runtime.vault.digest_json({'selection':original.planning.selection_event_id,'phase':'final-wording-repair-v1'})[:40]
        journal.append(EventEnvelope(event_id='expression.runtime:'+digest+':started',event_type='expression.runtime_started',
            source='alive.expression-runtime',actor='system:alive-runtime',subject='user:test',
            sensitivity=original_start.event.sensitivity,causation_id=original.planning.selection_event_id,
            payload={**_thaw_json(original_start.event.payload),'correction_review_event_id':review_id,
                'correction_digest':runtime.vault.digest_json(context),'previous_expression_event_id':original.expression_event_id}))
        if mode=='legacy-failed':
            operation='runtime-expression-repair:'+digest
            runtime.expression.comparator._receipt(operation,'started','user:test',
                original.planning.selection_event_id,original_start.event.sensitivity,status='started')
            runtime.expression.comparator._receipt(operation,'failed','user:test',
                original.planning.selection_event_id,original_start.event.sensitivity,
                status='render_failed',error='SyntheticHistoricalFailure')
    try:
        prepared = await runtime.prepare(**args)
    except asyncio.CancelledError:
        assert mode in ('cancel','review-cancel')
        prepared = None
    else:
        if mode in ('supported','proof-erased','legacy'):
            assert prepared.repair_disposition == 'completed'
            assert prepared.quality_disposition == 'supported' and prepared.authorization.authorized
            assert prepared.initial_final_review_event_id != prepared.final_review_event_id
            assert prepared.expression.expression_event_id != original.expression_event_id
            assert 'I told you yesterday.' not in prepared.expression.text
            if mode!='legacy':
                assert prepared.expression.text==original.text.removeprefix('I told you yesterday. ')
                proofs=journal.read(event_type='expression.local_correction_completed')
                assert len(proofs)==1 and proofs[0].event.payload['method']==METHOD
                assert 'I told you' not in json.dumps(_thaw_json(proofs[0].event.payload))
            else:assert not journal.read(event_type='expression.local_correction_completed')
            permit = journal.get(prepared.authorization.event_id)
            assert permit.event.payload['expression_event_id'] == prepared.expression.expression_event_id
            assert permit.event.payload['final_wording_witness']['review_event_id'] == prepared.final_review_event_id
        else:
            assert prepared.authorization is None and prepared.attempt_event_id is None
            if mode == 'confirmed': assert prepared.repair_disposition == 'requires_new_confirmation'
            elif mode in ('erase','abstain','malformed','unanchored','whole-text','protected','injected-offset','legacy-failed'):
                assert prepared.repair_disposition == 'unavailable'
            else:
                assert mode == 'rejected-again' and prepared.quality_disposition == 'final_unsupported'
                reviewer = ExpressionSourceSupportReviewer(journal, content_vault=runtime.vault)
                try:
                    reviewer.correction_context(prepared.final_review_event_id, subject='user:test',
                        selection_event_id=original.planning.selection_event_id)
                except SourceSupportError: pass
                else: raise AssertionError('repair of a repaired expression was allowed')
    count = len(calls)
    assert count == (1 if mode in ('confirmed','legacy-failed') else 3 if mode=='review-cancel' else 2 if mode in
        ('cancel','erase','abstain','malformed','unanchored','whole-text','protected','injected-offset') else 4)
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
        if mode in ('cancel','review-cancel'):
            assert reopened.attempt_event_id is None and reopened.repair_disposition == 'unavailable'
        else: assert reopened == prepared
    if mode=='review-cancel':
        assert len(journal.read(event_type='expression.local_correction_completed'))==1
        repair_starts=[r for r in journal.read(event_type='expression.runtime_started')
            if r.event.payload.get('correction_review_event_id')]
        assert len(repair_starts)==1 and repair_starts[0].event.payload['correction_method']==METHOD
        assert journal.get(repair_starts[0].event.event_id.removesuffix(':started')+':completed') is None
    if mode=='legacy-failed':
        assert not journal.read(event_type='expression.local_correction_completed')
    assert len(calls) == count
    assert not forbidden_calls, forbidden_calls
    if mode=='proof-erased':
        outbox=DispatchOutbox(journal,content_vault=runtime.vault)
        permit=journal.get(prepared.authorization.event_id)
        outbox._validate_selection_inputs(permit)
        proof=journal.read(event_type='expression.local_correction_completed')[0]
        runtime.vault.erase_item(proof.event.payload['content']['content_id'])
        try:outbox._validate_selection_inputs(permit)
        except DispatchOutboxError:pass
        else:raise AssertionError('dispatch ignored erased local reconstruction proof')
        recovered=await SendPreparationRuntime(ExperienceJournal(journal.path)).prepare(**{**args,'call':forbidden})
        assert recovered.authorization is None and recovered.repair_disposition=='unavailable'
        assert not forbidden_calls
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
    modes = ('supported','rejected-again','cancel','erase','confirmed','abstain','malformed',
        'unanchored','whole-text','protected','injected-offset','proof-erased','legacy','legacy-failed','review-cancel')
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=modes)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-final-repair-') as folder:
        for mode in ((args.mode,) if args.mode else modes):
            asyncio.run(test(Path(folder) / mode, mode))
    print('HERMES_ALIVE_FINAL_WORDING_REPAIR_OK')
