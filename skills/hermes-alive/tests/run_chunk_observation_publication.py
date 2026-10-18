#!/usr/bin/env python3
"""Closed local trace publication with real kernel starts, no real transport."""
import asyncio
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import DispatchOutbox, DispatchOutboxError, ExperienceJournal, Sensitivity
from alive_kernel.chunk_observation import OwnedChunkObserver
from alive_kernel.dispatch_verifier import DispatchEvidenceVerifier
from alive_kernel.event_store import EventConflictError
from run_alive_kernel_opportunity_execution import scenario


async def exercise(root, interrupted=False):
    route = {'platform':'weixin', 'profile':'synthetic', 'chat_id':'synthetic-chat', 'thread_id':None}
    journal, outbox, lease, _, _ = await scenario(root, 'expression', transport_route=route, return_ready=True)
    execution = outbox.begin_execution(lease, clearance=Sensitivity.PRIVATE)
    class Adapter:
        async def _send_text_chunk(self, **kwargs):
            if kwargs.get('client_id') == 'cancelled': raise asyncio.CancelledError()
    adapter = Adapter()
    def observe(subject=lease.subject, current_route=route, attempt_id=None):
        return OwnedChunkObserver(adapter, protector=outbox.protector, subject=subject,
            route=current_route, qualified=True, attempt_event_id=attempt_id or 'action.attempt:' + lease.attempt_id,
            start_event_id=execution.start_event_id)
    observer = observe()
    async with observer:
        await adapter._send_text_chunk(chat_id='synthetic-chat', client_id='PRIVATE_CLIENT_ID',
            chunk='PRIVATE_BODY', context_token='PRIVATE_TOKEN')
        try: outbox.record_chunk_observation(execution, observer)
        except DispatchOutboxError: pass
        else: raise AssertionError('open trace was published as closed')
        if interrupted:
            try: await adapter._send_text_chunk(chat_id='synthetic-chat', client_id='cancelled')
            except asyncio.CancelledError: pass
            else: raise AssertionError('original cancellation changed')
    record = outbox.record_chunk_observation(execution, observer)
    assert record.event.payload['normal_return_count'] == 1
    assert record.event.payload['trace_state'] == ('interrupted' if interrupted else 'closed')
    assert record.event.payload['coverage_uncertain'] is interrupted
    assert record.event.payload['complete_inventory_proven'] is False
    assert record.event.payload['external_delivery_proven'] is False
    assert 'PRIVATE' not in record.event.canonical_json()
    before = journal.last_sequence()
    reopened = DispatchOutbox(ExperienceJournal(journal.path))
    replay = reopened.record_chunk_observation(execution, observer)
    assert replay.sequence == record.sequence and replay.event.canonical_json() == record.event.canonical_json()
    assert journal.last_sequence() == before
    original_get = reopened.journal.get
    damaged = replace(record, event=replace(record.event,
        observed_at=original_get(execution.start_event_id).event.observed_at-timedelta(seconds=1)))
    def damaged_read(event_id):
        return damaged if event_id == record.event.event_id else original_get(event_id)
    with patch.object(reopened.journal, 'get', side_effect=damaged_read):
        try: reopened.record_chunk_observation(execution, observer)
        except EventConflictError: pass
        else: raise AssertionError('observation predating authenticated start accepted')
    attempt = journal.get('action.attempt:' + lease.attempt_id)
    assert not DispatchEvidenceVerifier(journal, outbox.protector).verify(record, attempt)
    for bad in (observe(subject='user:other'), observe(current_route={**route,'chat_id':'elsewhere'}),
                observe(attempt_id='action.attempt:other')):
        async with bad: pass
        try: outbox.record_chunk_observation(execution, bad)
        except DispatchOutboxError: pass
        else: raise AssertionError('foreign owner/route trace accepted')
    try:
        outbox.record_chunk_observation(replace(execution, lease=replace(lease, token='wrong-token')), observer)
    except DispatchOutboxError: pass
    else: raise AssertionError('trace without live start ownership accepted')
    changed = observe()
    async with changed:
        await adapter._send_text_chunk(chat_id='synthetic-chat', client_id='another-id')
    try: outbox.record_chunk_observation(execution, changed)
    except EventConflictError: pass
    else: raise AssertionError('existing observation was rewritten')
    assert not journal.read(event_type='outcome.recorded')
    assert not journal.read(event_type='preference.observed')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-chunk-publication-') as folder:
        asyncio.run(exercise(Path(folder) / 'closed'))
        asyncio.run(exercise(Path(folder) / 'interrupted', interrupted=True))
    print('HERMES_ALIVE_CHUNK_OBSERVATION_PUBLICATION_OK')
