"""Observe Core's real chat streaming and transform order with a local adapter."""

import asyncio
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

import httpx
import run_core_session_routing as core


async def exercise(home, *, buffer_only, segment_break=False):
    from gateway.platforms.base import SendResult
    from gateway.stream_consumer import GatewayStreamConsumer, StreamConsumerConfig
    from hermes_state_registry import close_all_under
    from run_agent import AIAgent

    raw = 'The tool was independently validated and results are directly comparable.'
    revised = 'The source establishes reuse of an existing tool.'
    trace = []
    visible = threading.Event()

    class Adapter(core.Adapter):
        async def send(self, chat_id, content, **kwargs):
            trace.append(('adapter', content))
            visible.set()
            return SendResult(success=True, message_id='local-preview')

        async def edit_message(self, chat_id, message_id, content, **kwargs):
            trace.append(('adapter', content))
            visible.set()
            return SendResult(success=True, message_id=message_id)

    class Reply(httpx.SyncByteStream):
        def __iter__(self):
            yield chunk({'content': raw})
            if segment_break:
                # Core sends this marker before tool progress. Exercise the
                # stream consumer boundary without executing any tool.
                consumer.on_delta(None)
            if (not buffer_only or segment_break) and not visible.wait(10):
                raise AssertionError('Core did not expose a streamed preview')
            yield chunk({}, finish='stop')
            yield b'data: [DONE]\n\n'

    def chunk(delta, finish=None):
        value = {'id': 'synthetic', 'object': 'chat.completion.chunk', 'created': 1,
                 'model': 'synthetic-model',
                 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
        return f'data: {json.dumps(value)}\n\n'.encode()

    def http(request):
        assert request.url.host == 'provider.invalid'
        assert json.loads(request.content)['stream'] is True
        return httpx.Response(200, request=request, stream=Reply(), headers={'content-type': 'text/event-stream'})

    def transform(name, **values):
        if name != 'transform_llm_output':
            return []
        assert values['response_text'] == raw
        trace.append(('transform', revised))
        return [revised]

    home.mkdir()
    token = core.set_hermes_home_override(home)
    agent = None
    try:
        adapter = Adapter(core.Platform.TELEGRAM)
        consumer = GatewayStreamConsumer(adapter, 'local-fixture', StreamConsumerConfig(
            edit_interval=.01, buffer_threshold=1, cursor='', buffer_only=buffer_only))
        def run():
            nonlocal agent
            agent = AIAgent(api_key='test-key-only', base_url='https://provider.invalid/v1',
                model='synthetic-model', provider='custom', api_mode='chat_completions',
                stream_delta_callback=consumer.on_delta, platform='telegram', quiet_mode=True,
                enabled_toolsets=[], skip_context_files=True, skip_memory=True, skip_background_review=True,
                cwd=str(home), max_iterations=2)
            return agent.run_conversation('What does reuse of the tool establish?')

        # The real SDK parses the supplied SSE. Only the provider and transport
        # endpoint are fixtures. The gateway consumer handles the actual deltas.
        with patch.object(httpx.Client, 'send', lambda client, request, **kwargs: http(request)), \
             patch('hermes_cli.lifecycle.invoke_hook', side_effect=transform):
            worker = asyncio.create_task(consumer.run())
            try:
                result = await asyncio.to_thread(run)
            except BaseException:
                consumer.finish()
                await worker
                raise
            consumer.finish(final_text=result['final_response'])
            await worker
        assert result['final_response'] == revised and result['response_transformed'] is True
        before = trace[:trace.index(('transform', revised))]
        if segment_break:
            assert ('adapter', raw) in before, trace
        elif buffer_only:
            assert not before and trace[-1] == ('adapter', revised), trace
        else:
            assert ('adapter', raw) in before and trace[-1] == ('adapter', revised), trace
        print(json.dumps({'buffer_only': buffer_only, 'segment_break': segment_break,
                          'raw_visible_before_transform': ('adapter', raw) in before,
                          'revised_delivered_by_stream_consumer': ('adapter', revised) in trace}))
    finally:
        if agent is not None:
            agent.close()
        close_all_under(home)
        core.reset_hermes_home_override(token)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-followup-exposure-') as directory:
        for index, (buffered, boundary) in enumerate(((False, False), (True, False), (True, True))):
            asyncio.run(exercise(Path(directory) / str(index), buffer_only=buffered, segment_break=boundary))
    print('HERMES_ALIVE_CORE_FOLLOWUP_EXPOSURE_OK')
