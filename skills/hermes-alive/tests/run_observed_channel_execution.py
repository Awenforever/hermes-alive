#!/usr/bin/env python3
"""Single-start lifecycle with synthetic IO and optional actual stock SDK send."""
import argparse
import asyncio
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel import DispatchOutboxError, Sensitivity
from alive_kernel.observed_channel_execution import execute_observed_text_once
from run_alive_kernel_host_runtime_chain import prepare


async def exercise(root, mode, core=None):
    route = {'platform':'weixin','profile':'synthetic','chat_id':'synthetic-chat','thread_id':None}
    journal, outbox, lease, _, expected, _, prepared, runtime = await prepare(root / 'kernel', route)
    home = root / 'profile'
    home.mkdir()
    os.environ['HERMES_HOME'] = str(home)
    if core:
        from gateway.config import PlatformConfig
        from gateway.platforms.weixin import WeixinAdapter
        base = WeixinAdapter
    else:
        class base:
            async def send(self, chat_id, content, metadata=None):
                self.sent_text = content
                await self._send_text_chunk(chat_id=chat_id, client_id='one', chunk=content)
                if mode in ('error','cancel'):
                    await self._send_text_chunk(chat_id=chat_id, client_id='two', chunk=content)
                return self.result
    class Adapter(base):
        async def _send_text_chunk(self, **kwargs):
            self.calls += 1
            if mode == 'error': raise RuntimeError('PRIVATE_SEND_ERROR')
            if mode == 'cancel': raise asyncio.CancelledError()
    adapter = Adapter(PlatformConfig(enabled=True, token='synthetic-token', extra={
        'account_id':'synthetic','send_chunk_delay_seconds':0})) if core else Adapter()
    if core: adapter._send_session = object()
    adapter.calls = 0
    adapter.result = SimpleNamespace(success=True, message_id='synthetic')
    params = dict(adapter=adapter, clearance=Sensitivity.PRIVATE, profile_id='synthetic',
        hermes_home=home, resolve_target=lambda p,t:(t,None,None), extract_media=lambda text:([],text),
        observe_profile_home=lambda:home, qualified=True)
    if mode == 'deferred-seam':
        adapter._hermes_wechat_v021_pending_queue = object()
        try:
            await runtime.execute_prepared_with_adapter(prepared, lease, **params)
        except ValueError as exc:
            assert str(exc) == 'deferred transport requires its own qualified receipt publisher'
        else:
            raise AssertionError('deferred seam consumed an execution lease')
        assert adapter.calls == 0 and not journal.read(event_type='dispatch.started')
        return
    if mode == 'publication-failure':
        def broken(*args, **kwargs): raise OSError('PRIVATE_STORAGE_ERROR')
        outbox.record_chunk_observation = broken
    # Exercise the prepared-runtime adapter entry for normal/exception/cancel;
    # the low-level publication-failure injection owns its explicit outbox.
    async def execute():
        if mode == 'publication-failure':
            return await execute_observed_text_once(outbox, lease, **params)
        return await runtime.execute_prepared_with_adapter(prepared, lease, **params)
    try:
        observed = await execute()
    except RuntimeError as exc:
        assert mode == 'error' and not core and str(exc) == 'PRIVATE_SEND_ERROR'
    except asyncio.CancelledError:
        assert mode == 'cancel'
    else:
        if mode == 'error': assert core and observed.adapter_result.success is False
        else:
            assert mode in ('success','publication-failure')
            assert observed.adapter_result.success
            if not core: assert observed.adapter_result is adapter.result and adapter.sent_text == expected
        assert observed.external_delivery_proven is False
        if mode == 'publication-failure':
            assert observed.publication_error_class == 'OSError' and observed.observation is None
            assert 'PRIVATE' not in repr(observed)
    records = journal.read(event_type='transport.chunk.observed')
    assert len(records) == (0 if mode == 'publication-failure' else 1)
    assert len(journal.read(event_type='dispatch.started')) == 1
    count = adapter.calls
    try: await execute()
    except DispatchOutboxError: pass
    else: raise AssertionError('consumed attempt called adapter twice')
    assert adapter.calls == count and '_send_text_chunk' not in vars(adapter)
    assert not journal.read(event_type='outcome.recorded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', type=Path)
    args = parser.parse_args()
    if args.hermes_root:
        sys.path.insert(0, str(args.hermes_root.resolve()))
        from run_host_admitted_inbound_probe import forbid_network
        sys.addaudithook(forbid_network)
    with tempfile.TemporaryDirectory(prefix='alive-observed-execution-') as folder:
        for mode in ('success','error','cancel','publication-failure','deferred-seam'):
            asyncio.run(exercise(Path(folder) / mode, mode, args.hermes_root))
    print('HERMES_ALIVE_OBSERVED_CHANNEL_EXECUTION_OK')
