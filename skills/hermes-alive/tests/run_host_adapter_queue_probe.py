#!/usr/bin/env python3
"""Real base-adapter queue/drain with local-only transport and replaced worker."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from run_host_admitted_inbound_probe import forbid_network


async def run(mode):
    from gateway.config import GatewayConfig, Platform, PlatformConfig
    from gateway.platforms.base import BasePlatformAdapter, SendResult
    from gateway.platforms.event import MessageEvent
    from gateway.run import GatewayRunner
    class LocalAdapter(BasePlatformAdapter):
        async def connect(self, *, is_reconnect=False): self._running = True; return True
        async def disconnect(self): await self.cancel_background_tasks(); self._running = False
        async def get_chat_info(self, chat_id): return {'name':'synthetic', 'type':'group'}
        async def send(self, chat_id, content, reply_to=None, metadata=None):
            assert chat_id == 'synthetic-chat'
            self.effects.append({'content':content, 'reply_to':reply_to})
            self.changed.set()
            return SendResult(success=True, message_id='local-only-' + str(len(self.effects)))
    class WorkerRunner(GatewayRunner):
        async def _handle_message_with_agent(self, event, source, key, generation):
            self.inputs.append({'message_id':event.message_id, 'text':event.text,
                                'quoted_target':event.reply_to_message_id})
            if event.message_id == 'incoming-1':
                self.entered.set()
                await self.release.wait()
            return 'fixture response:' + event.message_id
    runner = WorkerRunner(GatewayConfig(multiplex_profiles=False, group_sessions_per_user=False))
    runner.inputs = []; runner.entered = asyncio.Event(); runner.release = asyncio.Event()
    adapter = LocalAdapter(PlatformConfig(enabled=True, extra={'group_sessions_per_user':False}), Platform.FEISHU)
    adapter.effects = []; adapter.changed = asyncio.Event(); adapter.gateway_runner = runner
    runner.adapters[Platform.FEISHU] = adapter
    runner._wire_adapter_handlers(adapter)
    # Public setter, delegating the installed gateway handler exactly once.
    # Test-only observation; it does not decide auth, queue, drain or consume.
    original_busy = adapter._busy_session_handler
    busy_inputs = []
    busy_calls = []
    async def observe_busy(event, key):
        busy_calls.append(event.message_id)
        handled = await original_busy(event, key)
        if (getattr(event, '_bot_loop_admitted', False) is True
                and runner._is_user_authorized_for_source(event.source)):
            busy_inputs.append({'message_id':event.message_id, 'text':event.text,
                                'quoted_target':event.reply_to_message_id})
        return handled
    adapter.set_busy_session_handler(observe_busy)
    await adapter.connect()
    def incoming(index):
        identifier = 'incoming-' + str(index)
        source = adapter.build_source('synthetic-chat', chat_type='group', user_id='synthetic-user', message_id=identifier)
        return MessageEvent(source=source, message_id=identifier, text='synthetic text ' + str(index),
            reply_to_message_id='synthetic-outbound-' + str(index), reply_to_is_own_message=True)
    await adapter.handle_message(incoming(1))
    await asyncio.wait_for(runner.entered.wait(), 5)
    await adapter.handle_message(incoming(2))
    await adapter.handle_message(incoming(3))
    denied = MessageEvent(source=adapter.build_source('synthetic-chat', chat_type='group',
        user_id='synthetic-denied', message_id='denied-4'), text='synthetic unauthorized busy input', message_id='denied-4')
    assert adapter._event_session_key(denied) == adapter._event_session_key(incoming(1))
    await adapter.handle_message(denied)
    assert busy_inputs == [{'message_id':'incoming-2', 'text':'synthetic text 2', 'quoted_target':'synthetic-outbound-2'},
                           {'message_id':'incoming-3', 'text':'synthetic text 3', 'quoted_target':'synthetic-outbound-3'}]
    assert busy_calls == ['incoming-2','incoming-3','denied-4']
    assert len(runner.inputs) == 1
    runner.release.set()
    expected = 3 if mode == 'interrupt' else 2
    async def completed():
        while len([row for row in adapter.effects if row['content'].startswith('fixture response:')]) < expected:
            adapter.changed.clear()
            await adapter.changed.wait()
        while any(not task.done() for task in adapter._background_tasks):
            await asyncio.sleep(.01)
    await asyncio.wait_for(completed(), 10)
    replies = [row['content'] for row in adapter.effects if row['content'].startswith('fixture response:')]
    if mode == 'interrupt':
        assert replies == ['fixture response:incoming-1','fixture response:incoming-2','fixture response:incoming-3']
        assert [row['text'] for row in runner.inputs] == ['synthetic text 1','synthetic text 2','synthetic text 3']
    else:
        assert replies == ['fixture response:incoming-1','fixture response:incoming-3']
        assert runner.inputs[1]['text'] == 'synthetic text 2\nsynthetic text 3'
        assert runner.inputs[1]['quoted_target'] == 'incoming-3'
    profile = Path(os.environ['HERMES_HOME'])
    metadata = [json.loads(line) for line in (profile / 'synthetic-metadata.jsonl').read_text().splitlines()]
    assert len(metadata) == expected and all(row is not None for row in metadata)
    if mode == 'default':
        assert metadata[1]['quoted_message_id'] == 'incoming-3' and metadata[1]['quote_is_own_message'] is True
    assert not adapter._pending_messages
    assert not runner._is_session_running(runner._session_key_for_source(incoming(1).source))
    sys.path.insert(0, str(profile / 'plugins/hermes-alive/skills/hermes-alive/hooks'))
    from alive_kernel.event_store import ExperienceJournal
    journal = ExperienceJournal(profile / 'plugin-data/hermes-alive/runtime/kernel/experience.sqlite3')
    native = journal.read(event_type='conversation.admitted')
    assert len(native) == expected and not journal.read(event_type='outcome.recorded')
    assert all(row.event.payload['wire_message_count'] is None for row in native)
    await runner.stop()
    return {'actual_base_adapter':True, 'actual_queue_and_drain':True, 'mode':mode,
            'worker_entries':len(runner.inputs), 'local_reply_effects':len(replies),
            'queued_messages_bundled':mode == 'default', 'quote_origin_proven':False,
            'authorized_busy_wire_observations':len(busy_inputs), 'denied_busy_wire_observations':0,
            'agent_worker_replaced':True, 'external_delivery_proven':False,
            'real_sends':0, 'model_calls':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--alive-root', required=True, type=Path)
    parser.add_argument('--busy-text-mode', choices=('default','interrupt'), default='default')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-adapter-queue-') as directory:
        profile = Path(directory).resolve()
        installed = profile / 'plugins/alive-metadata-fixture'
        shutil.copytree(Path(__file__).parent / 'fixtures/admission-metadata-observer', installed)
        shutil.copy2(args.alive_root / 'skills/hermes-alive/hooks/alive_kernel/admission_metadata.py', installed / 'cache.py')
        shutil.copytree(args.alive_root.resolve(strict=True), profile / 'plugins/hermes-alive',
                        ignore=shutil.ignore_patterns('.git', '__pycache__'))
        display = {'busy_input_mode':'queue'}
        if args.busy_text_mode != 'default': display['busy_text_mode'] = args.busy_text_mode
        (profile / 'config.yaml').write_text(json.dumps({'plugins':{'enabled':['alive-metadata-fixture','hermes-alive']}, 'display':display}))
        (profile / '.env').write_text('')
        for key in tuple(os.environ):
            if key.endswith(('_ALLOWED_USERS', '_ALLOW_ALL_USERS', '_ALLOW_BOTS',
                             '_GROUP_ALLOWED_USERS', '_GROUP_ALLOWED_CHATS')):
                os.environ.pop(key)
        os.environ['FEISHU_ALLOWED_USERS'] = 'synthetic-user'
        os.environ['HERMES_HOME'] = str(profile)
        os.environ['HERMES_BUNDLED_PLUGINS'] = str(profile / 'empty-bundled')
        os.environ['HERMES_ALIVE_TEST_METADATA_MODE'] = 'task'
        os.environ.pop('HERMES_ALIVE_SHARED_DIR', None)
        os.environ['HERMES_ALIVE_KERNEL_SHADOW_ENABLED'] = 'true'
        sys.path.insert(0, str(args.hermes_root.resolve(strict=True)))
        sys.addaudithook(forbid_network)
        print(json.dumps(asyncio.run(run(args.busy_text_mode))))
    print('HERMES_ALIVE_HOST_ADAPTER_QUEUE_PROBE_OK')


if __name__ == '__main__': main()
