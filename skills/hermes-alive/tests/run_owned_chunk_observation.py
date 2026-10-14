#!/usr/bin/env python3
"""Owned task observation/restoration; no transport or canonical receipts."""
import asyncio
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.chunk_observation import OwnedChunkObserver
from alive_kernel.privacy import LocalIdentityProtector


async def exercise(root):
    protector = LocalIdentityProtector(root / 'identity.key')
    route = {'platform':'weixin', 'profile':'synthetic', 'chat_id':'chat', 'thread_id':None}
    class Adapter:
        def __init__(self): self.calls = []
        async def _send_text_chunk(self, **kwargs):
            self.calls.append(kwargs['client_id'])
            if kwargs['client_id'] == 'failure': raise RuntimeError('PRIVATE_ERROR')
            if kwargs['client_id'] == 'cancel': raise asyncio.CancelledError()
    adapter = Adapter()
    def observe(current=adapter, current_protector=protector, **extra):
        return OwnedChunkObserver(current, protector=current_protector, subject='user:test',
                                  route=route, qualified=True, **extra)
    def send(identifier, chat='chat'):
        return adapter._send_text_chunk(chat_id=chat, chunk='PRIVATE_BODY',
                                       context_token='PRIVATE_TOKEN', client_id=identifier)
    observer = observe()
    async with observer:
        assert await send('one') is None
        await asyncio.create_task(send('other-task'))
        await send('other-chat', 'elsewhere')
        try: await send('failure')
        except RuntimeError as exc: assert str(exc) == 'PRIVATE_ERROR'
        else: raise AssertionError('original exception was swallowed')
        try: await send('cancel')
        except asyncio.CancelledError: pass
        else: raise AssertionError('original cancellation was swallowed')
        dormant = send('after-exit')
        assert len(observer.observations) == 1
        assert observer.failures == observer.cancellations == 1
        assert observer.unscoped_same_chat_calls
    await dormant
    assert len(adapter.calls) == 6 and len(observer.observations) == 1
    assert '_send_text_chunk' not in vars(adapter)
    assert observer.adapter is observer.task is observer.wrapper is None
    assert 'PRIVATE' not in repr(observer.observations)
    other = OwnedChunkObserver(adapter, protector=protector, subject='user:other', route=route, qualified=True)
    async with other:
        await send('one')
    assert other.observations[0].scoped_client_reference != observer.observations[0].scoped_client_reference
    bounded = observe(limit=1)
    async with bounded:
        await send('one'); await send('two')
    assert bounded.capacity_exceeded and len(bounded.observations) == 1
    assert bounded.observations[0].scoped_client_reference == observer.observations[0].scoped_client_reference
    class BrokenProtector:
        def authenticate_json(self, *args): raise ValueError('PRIVATE_ERROR')
    broken = observe(current_protector=BrokenProtector())
    async with broken:
        assert await send('normal') is None
    assert broken.observation_failed and not broken.observations
    replacement = observe()
    async def later_owner(**kwargs): return 'later-owner-result'
    async with replacement:
        adapter._send_text_chunk = later_owner
    assert replacement.restoration_conflicted
    assert await send('untouched') == 'later-owner-result'
    assert adapter._send_text_chunk is later_owner
    del adapter._send_text_chunk
    try:
        async with OwnedChunkObserver(adapter, protector=protector, subject='user:test', route=route):
            pass
    except ValueError: pass
    else: raise AssertionError('unqualified hook installation allowed')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-chunk-observer-') as folder:
        asyncio.run(exercise(Path(folder)))
    print('HERMES_ALIVE_OWNED_CHUNK_OBSERVATION_OK')
