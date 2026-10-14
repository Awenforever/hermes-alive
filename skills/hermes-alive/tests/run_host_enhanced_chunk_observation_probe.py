#!/usr/bin/env python3
"""Measure the actual enhance queue seam using synthetic transport only.

The external module is an operator-supplied source snapshot, never imported from
a live profile. No credentials, private queue files or network IO are used.
"""
import argparse
import asyncio
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.chunk_observation import OwnedChunkObserver


class Protector:
    def authenticate_json(self, domain, value):
        # Synthetic observation identity only, not a real kernel signature.
        import json
        return hashlib.sha256((domain + json.dumps(value, sort_keys=True)).encode()).hexdigest()


class Adapter:
    _account_id = 'synthetic-account'
    _token = ''
    MAX_MESSAGE_LENGTH = 2000

    def __init__(self):
        self.physical_calls = []
        self.fail = True
        self._token_store = SimpleNamespace(get=lambda *args: 'synthetic-token')
        self._dedup = SimpleNamespace(is_duplicate=lambda *args: False)

    def format_message(self, text): return text
    def _split_text(self, text): return [text]
    async def _process_message(self, message): return None

    async def _send_text_chunk(self, **kwargs):
        self.physical_calls.append(kwargs['client_id'])
        if self.fail: raise RuntimeError('synthetic expired token')

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        await self._send_text_chunk(chat_id=chat_id, chunk=content,
            context_token='synthetic-token', client_id='synthetic-client-id')
        return SimpleNamespace(success=True, message_id='synthetic-client-id')


async def probe(module):
    adapter = Adapter()
    assert module.patch_adapter(adapter)
    observer = OwnedChunkObserver(adapter, protector=Protector(), subject='user:synthetic',
        route={'platform':'weixin','profile':'synthetic','chat_id':'synthetic-chat','thread_id':None},
        qualified=True)
    queue = adapter._hermes_wechat_v021_pending_queue
    try:
        async with observer: raise AssertionError('queued seam admitted as direct acknowledgement')
    except ValueError as exc:
        assert str(exc) == 'deferred transport requires its own qualified receipt publisher'
    assert not observer._entered and not observer.active
    outer = adapter._send_text_chunk
    returns = []
    async def unsafe_normal_return_counter(**kwargs):
        result = await outer(**kwargs)
        returns.append(kwargs['client_id'])
        return result
    adapter._send_text_chunk = unsafe_normal_return_counter
    try:
        result = await adapter.send('synthetic-chat', 'synthetic body')
        assert result.success is True
        assert len(adapter.physical_calls) == 1 and queue.count(adapter._account_id, 'synthetic-chat') == 1
        assert len(returns) == 1
        # The normal return is queue submission, NOT a physical acknowledgement.
        adapter.fail = False
        drained = await adapter._drain_pending('synthetic-chat')
        assert drained == {'ok':True, 'sent':1, 'pending':0}
        assert len(adapter.physical_calls) == 2
        # Drain bypasses the observed outer method even in the SAME asyncio task.
        assert len(returns) == 1
    finally:
        adapter._send_text_chunk = outer
    assert '_send_text_chunk' in vars(adapter)
    assert adapter._send_text_chunk.__func__.__name__ == 'send_text_chunk'
    assert not adapter._hermes_wechat_v021_retry_tasks
    print('HERMES_ALIVE_ENHANCED_QUEUE_OBSERVATION_GAP_CONFIRMED')


def forbid_network(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen'):
        raise RuntimeError('network/process IO forbidden in synthetic queue probe')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enhance-module', type=Path, required=True)
    args = parser.parse_args()
    source = args.enhance_module.resolve()
    print('enhance_source_sha256=' + hashlib.sha256(source.read_bytes()).hexdigest())
    with asyncio.Runner() as runner:
        # Windows creates a local socketpair for its loop wakeup mechanism.
        # Create only that infrastructure before forbidding ALL test network IO.
        runner.get_loop()
        sys.addaudithook(forbid_network)
        spec = importlib.util.spec_from_file_location('isolated_enhance_source', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='alive-enhanced-queue-') as folder:
            os.environ['HERMES_HOME'] = folder
            runner.run(probe(module))
