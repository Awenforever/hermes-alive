#!/usr/bin/env python3
"""Actual stock Weixin send, synthetic per-chunk IO, no login or network.

Characterizes the adapter result contract; not production queue/plugin behavior.
"""
import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from run_host_admitted_inbound_probe import forbid_network


async def exercise():
    from gateway.config import PlatformConfig
    from gateway.platforms.weixin import WeixinAdapter
    class LocalIOAdapter(WeixinAdapter):
        async def _send_text_chunk(self, *, chat_id, chunk, context_token, client_id):
            self.calls.append((chat_id, chunk, client_id))
            if self.cancel_after is not None and len(self.acknowledged) >= self.cancel_after:
                raise asyncio.CancelledError()
            if self.fail_after is not None and len(self.acknowledged) >= self.fail_after:
                raise RuntimeError('synthetic send failure after accepted chunks')
            self.acknowledged.append(client_id)
    def adapter(fail_after=None, cancel_after=None):
        value = LocalIOAdapter(PlatformConfig(enabled=True, token='synthetic-token',
            extra={'account_id': 'synthetic-account', 'send_chunk_delay_seconds': 0}))
        value._send_session = object()  # No connect(), HTTP session or QR flow.
        value.calls, value.acknowledged, value.fail_after = [], [], fail_after
        value.cancel_after = cancel_after
        return value
    content = 'Synthetic public fixture words. ' * 400
    complete = adapter()
    expected = complete._split_text(complete.format_message(content))
    assert len(expected) >= 3
    result = await complete.send('synthetic-chat', content)
    assert result.success and len(complete.calls) == len(expected)
    assert [item[1] for item in complete.calls] == expected
    assert result.message_id == complete.acknowledged[-1]
    # Stock result exposes one locally generated client id, not every bubble.
    assert len(set(complete.acknowledged)) == len(expected)
    incomplete = adapter(fail_after=1)
    failure = await incomplete.send('synthetic-chat', content)
    assert not failure.success and len(incomplete.acknowledged) == 1
    assert len(incomplete.calls) == 2
    assert failure.message_id is None
    first_failure_adapter = adapter(fail_after=0)
    first_failure = await first_failure_adapter.send('synthetic-chat', content)
    assert not first_failure_adapter.acknowledged and len(first_failure_adapter.calls) == 1
    assert not first_failure.success and first_failure.message_id is None
    assert first_failure.error == failure.error
    # Public error fields cannot distinguish no effect from prior accepted text.
    cancelled = adapter(cancel_after=1)
    try:
        await cancelled.send('synthetic-chat', content)
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError('cancelled partial send became a completed result')
    assert len(cancelled.acknowledged) == 1 and len(cancelled.calls) == 2
    # The false result does not establish zero effects or permission to retry.
    return {'actual_adapter_constructor': True, 'actual_send_method': True,
        'chunk_io_replaced': True, 'complete_chunk_count': len(expected),
        'returned_last_client_id_only': True, 'failed_send_has_prior_local_effect': True,
        'failed_result_has_no_message_id': True, 'external_delivery_proven': False,
        'zero_effect_and_partial_error_fields_identical': True,
        'cancellation_can_follow_prior_effect': True,
        'production_wechat_enhance_tested': False, 'model_calls': 0, 'real_sends': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-weixin-receipt-') as directory:
        os.environ['HERMES_HOME'] = directory
        os.environ['HERMES_BUNDLED_PLUGINS'] = str(Path(directory) / 'empty-bundled')
        sys.path.insert(0, str(args.hermes_root.resolve()))
        logging.disable(logging.CRITICAL)
        sys.addaudithook(forbid_network)
        print(json.dumps(asyncio.run(exercise())))
    print('HERMES_ALIVE_HOST_WEIXIN_SEND_RECEIPT_PROBE_OK')
