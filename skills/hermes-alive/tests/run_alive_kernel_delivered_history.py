#!/usr/bin/env python3
"""Synthetic proven-delivery history, distinct consent and executable lifetime."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import ExperienceJournal, EventEnvelope, Sensitivity, OutcomeProjection, OutcomeKind
from alive_kernel.content_vault import ContentErasedError, ContentVault
from alive_kernel.delivered_history import DeliveredHistoryStore, DeliveredHistoryError
from alive_kernel.feedback_synthesis import FeedbackSynthesizer
from alive_kernel.opportunity_expression import OpportunityExpressionStore
from alive_kernel_testkit import authenticated_dispatch_receipt
from run_alive_kernel_opportunity_execution import scenario

def consent(journal, *, enabled=True, directions=('inbound','outbound')):
    return journal.append(EventEnvelope(event_type='retention.consent_changed',
        source='hermes.command.memory', actor='user:test', subject='user:test',
        sensitivity=Sensitivity.PRIVATE, payload={'enabled':enabled, 'retention_days':30,
            'directions':list(directions), 'content_sensitivity':'private'}))

async def exercise(root, mode):
    journal = ExperienceJournal(root / 'kernel/journal.sqlite3')
    consent(journal, directions=('inbound',) if mode == 'inbound-only' else ('inbound','outbound'))
    journal, outbox, lease, expression, text = await scenario(root / 'kernel', 'expression',
        return_ready=True, custom_context=mode == 'context-forget')
    context_vault = ContentVault(root / 'kernel/separate-profile-vault') if mode == 'context-forget' else None
    store = DeliveredHistoryStore(journal, content_vault=outbox.vault, context_vault=context_vault)
    try:
        store.capture(subject='user:test', delivery_outcome_event_id=expression.event_id)
    except DeliveredHistoryError:
        pass
    else:
        raise AssertionError('expression/CLI-shaped content treated as delivery')
    attempt = journal.get('action.attempt:attempt')
    receipt = authenticated_dispatch_receipt(journal, attempt, event_id='receipt:history')
    outcomes = OutcomeProjection(journal, content_vault=outbox.vault)
    delivered = outcomes.append_outcome(attempt_id='attempt', kind=OutcomeKind.DELIVERY_SUCCEEDED,
        source_event_id=receipt.event_id, details={'synthetic':True}, actor='system:test',
        subject='user:test', outcome_id='delivered')
    assert outcomes.apply(delivered).outcome == 'recorded'
    args = dict(subject='user:test', delivery_outcome_event_id=delivered.event.event_id)
    if mode == 'inbound-only':
        try:
            store.capture(**args)
        except DeliveredHistoryError:
            return
        raise AssertionError('inbound-only consent retained outbound history')
    history = store.capture(**args)
    assert store.capture(**args).event.event_id == history.event.event_id
    value = store.resolve(history.event.event_id, subject='user:test')
    assert value['text'] == text
    assert history.event.payload['execution_authority_granted'] is False
    assert history.event.payload['learning_authority_granted'] is False
    try:
        store.resolve(history.event.event_id, subject='user:foreign')
    except DeliveredHistoryError:
        pass
    else:
        raise AssertionError('foreign history disclosed')
    compiled_id = journal.get(attempt.event.payload['authorization_event_id']).event.payload['executable_content_id']
    if mode == 'expiry':
        outbox.vault.erase_expired(now=expression.expires_at + timedelta(seconds=1))
        assert not outbox.vault.explicit_erasure_recorded(compiled_id)
        assert OpportunityExpressionStore(journal, content_vault=outbox.vault).resolve_model_candidate(expression.event_id) is None
        assert store.for_delivery(**args)['text'] == text
        assert store.capture(**args).event.event_id == history.event.event_id
        journal.append(EventEnvelope(event_type='consolidation.consent_changed',
            source='hermes.command.memory', actor='user:test', subject='user:test',
            sensitivity=Sensitivity.PRIVATE, payload={'enabled':True}))
        retention = store._consent('user:test', Sensitivity.PRIVATE)
        reply = '谢谢，能再解释一下最后一段吗？'
        ref = outbox.vault.put_json({'text':reply, 'direction':'inbound', 'may_be_truncated':False},
            subject='user:test', purpose='conversation.inbound', sensitivity=Sensitivity.PRIVATE,
            retention_until=datetime.now(timezone.utc) + timedelta(days=29))
        inbound = journal.append(EventEnvelope(event_type='conversation.inbound', source='synthetic',
            actor='user:test', subject='user:test', causation_id=attempt.event.event_id,
            sensitivity=Sensitivity.PRIVATE, payload={'erasable_content_stored':True,
                'content_may_be_truncated':False, 'consent_event_id':retention.event.event_id,
                'content':ref.to_event_payload()}))
        feedback = outcomes.append_outcome(attempt_id='attempt', kind=OutcomeKind.USER_REPLIED,
            source_event_id=inbound.event.event_id, details={'synthetic':True}, actor='user:test',
            subject='user:test', outcome_id='reply')
        assert outcomes.apply(feedback).outcome == 'recorded'
        interpreter = FeedbackSynthesizer(journal, content_vault=outbox.vault)
        snapshot, _ = interpreter.snapshot(subject='user:test', outcome_event_id=feedback.event.event_id)
        assert snapshot['delivered_text'] == text and snapshot['executed_content_id'] == value['content_id']
        calls = []
        async def interpret(**kw):
            calls.append(kw)
            assert json.loads(kw['messages'][1]['content'])['delivered_text'] == text
            kw['route_info']['provider'] = 'synthetic-provider'
            return SimpleNamespace(model='synthetic-feedback', choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({'summary':'A situational request for clarification.', 'signals':[], 'unresolved':[]})))])
        result = await interpreter.run(subject='user:test', outcome_event_id=feedback.event.event_id,
            operation_id='after-executable-expiry', call=interpret)
        assert len(calls) == 1 and not result.safe_for_automatic_learning
    elif mode == 'explicit-forget':
        outbox.vault.erase_item(compiled_id)
        try:
            store.resolve(history.event.event_id, subject='user:test')
        except DeliveredHistoryError:
            pass
        else:
            raise AssertionError('explicit forgetting bypassed')
        try:
            outbox.vault.resolve_json(value['content_id'])
        except ContentErasedError:
            pass
        else:
            raise AssertionError('forgotten archive derivative not physically erased on verification')
    elif mode == 'revoke':
        consent(journal, enabled=False)
        try:
            store.resolve(history.event.event_id, subject='user:test')
        except DeliveredHistoryError:
            pass
        else:
            raise AssertionError('revoked history read')
    elif mode == 'context-forget':
        proposal = journal.read(event_type='memory.proposed')[0]
        context_vault.erase_item(proposal.event.payload['content']['content_id'])
        try:
            store.resolve(history.event.event_id, subject='user:test')
        except DeliveredHistoryError:
            pass
        else:
            raise AssertionError('separate context-vault forgetting bypassed')
    elif mode == 'archive-expiry':
        outbox.vault.erase_expired(now=value['retention_until'] + timedelta(seconds=1))
        try:
            store.resolve(history.event.event_id, subject='user:test')
        except ContentErasedError:
            pass
        else:
            raise AssertionError('expired history reconstructed')
    assert not journal.read(event_type='preference.observed')

async def main(root):
    for mode in ('unchanged','expiry','explicit-forget','revoke','inbound-only','archive-expiry','context-forget'):
        await exercise(root / mode, mode)

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-delivered-history-') as directory:
        asyncio.run(main(Path(directory)))
    print('HERMES_ALIVE_KERNEL_DELIVERED_HISTORY_OK')
