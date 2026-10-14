#!/usr/bin/env python3
"""Actual gateway dispatcher/slot path; high-level agent worker replaced.

This is NOT provider/model/history-flush or external transport qualification.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from run_host_admitted_inbound_probe import forbid_network


async def run():
    from gateway.config import GatewayConfig, Platform
    from gateway.platforms.event import MessageEvent
    from gateway.run import GatewayRunner
    from gateway.session import SessionSource
    class SyntheticWorkerRunner(GatewayRunner):
        async def _handle_message_with_agent(self, event, source, key, generation):
            assert self._is_session_running(key)
            self.synthetic_calls.append(event.message_id)
            if event.text in ('synthetic hold', 'synthetic cancel'):
                self.synthetic_entered.set()
                await self.synthetic_release.wait()
            if event.text == 'synthetic error':
                raise RuntimeError('synthetic worker failure')
            return 'synthetic response'
    # Actual constructor, not a bare runner with fabricated slot state.
    runner = SyntheticWorkerRunner(GatewayConfig(multiplex_profiles=False))
    runner.synthetic_calls = []
    runner.synthetic_entered = asyncio.Event()
    runner.synthetic_release = asyncio.Event()
    source = SessionSource(platform=Platform.FEISHU, chat_id='synthetic-chat',
                           user_id='synthetic-user', chat_type='group')
    def message(identifier, text, current=source):
        return MessageEvent(source=current, message_id=identifier, text=text,
                            reply_to_message_id='synthetic-target', reply_to_is_own_message=True)
    profile = Path(os.environ['HERMES_HOME'])
    def observed():
        path = profile / 'synthetic-metadata.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    task = asyncio.create_task(runner._handle_message(message('normal-1', 'synthetic normal')))
    assert await task == 'synthetic response'
    await asyncio.sleep(0)
    assert len(observed()) == 1 and observed()[0]['quoted_message_id'] == 'synthetic-target'
    assert not runner._is_session_running(runner._session_key_for_source(source))
    assert not hasattr(task, '_hermes_alive_experimental_admission_metadata_v1')
    denied_source = SessionSource(platform=Platform.FEISHU, chat_id='synthetic-chat',
                                 user_id='synthetic-denied', chat_type='group')
    assert await asyncio.create_task(runner._handle_message(message('denied-2', 'synthetic denied', denied_source))) is None
    assert len(observed()) == 1 and runner.synthetic_calls == ['normal-1']
    help_result = await asyncio.create_task(runner._handle_message(message('help-3', '/help')))
    assert help_result is not None
    assert len(observed()) == 1 and runner.synthetic_calls == ['normal-1']
    holding = asyncio.create_task(runner._handle_message(message('hold-4', 'synthetic hold')))
    await asyncio.wait_for(runner.synthetic_entered.wait(), 5)
    busy = asyncio.create_task(runner._handle_message(message('busy-5', 'synthetic followup')))
    await busy
    await asyncio.sleep(0)
    assert runner.synthetic_calls == ['normal-1', 'hold-4']
    assert len(observed()) == 2
    assert not hasattr(busy, '_hermes_alive_experimental_admission_metadata_v1')
    runner.synthetic_release.set()
    assert await holding == 'synthetic response'
    assert not runner._is_session_running(runner._session_key_for_source(source))
    failed = asyncio.create_task(runner._handle_message(message('error-6', 'synthetic error')))
    try: await failed
    except RuntimeError as exc: assert str(exc) == 'synthetic worker failure'
    else: raise AssertionError('worker failure not observed')
    assert not runner._is_session_running(runner._session_key_for_source(source))
    runner.synthetic_entered.clear()
    runner.synthetic_release.clear()
    cancelled = asyncio.create_task(runner._handle_message(message('cancel-7', 'synthetic cancel')))
    await asyncio.wait_for(runner.synthetic_entered.wait(), 5)
    cancelled.cancel()
    try: await cancelled
    except asyncio.CancelledError: pass
    else: raise AssertionError('cancelled handler completed normally')
    await asyncio.sleep(0)
    assert not runner._is_session_running(runner._session_key_for_source(source))
    assert not hasattr(cancelled, '_hermes_alive_experimental_admission_metadata_v1')
    sys.path.insert(0, str(profile / 'plugins/hermes-alive/skills/hermes-alive/hooks'))
    from alive_kernel.event_store import ExperienceJournal
    journal = ExperienceJournal(profile / 'plugin-data/hermes-alive/runtime/kernel/experience.sqlite3')
    native = journal.read(event_type='conversation.admitted')
    assert len(native) == 4
    assert all(item.event.payload['erasable_content_stored'] is False for item in native)
    assert not journal.read(event_type='outcome.recorded')
    # The actual constructor owns background persistence/DB handles. A partial
    # executor shutdown races tempfile deletion and is not real teardown.
    await runner.stop()
    assert runner._shutdown_event.is_set()
    return {'actual_runner_constructor':True, 'actual_handle_message':True,
            'actual_runner_stop':True,
            'actual_alive_native_observations':len(native),
            'worker_error_slot_released':True, 'cancelled_slot_released':True,
            'normal_agent_calls':2, 'denied_agent_calls':0, 'slash_agent_calls':0,
            'busy_duplicate_agent_calls':0, 'post_admission_callbacks':len(observed()),
            'agent_worker_replaced':True, 'model_history_delivery_proven':False,
            'adapter_fifo_drain_proven':False, 'sends':0, 'model_calls':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--alive-root', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-full-dispatch-') as directory:
        profile = Path(directory).resolve()
        installed = profile / 'plugins/alive-metadata-fixture'
        shutil.copytree(Path(__file__).parent / 'fixtures/admission-metadata-observer', installed)
        shutil.copy2(args.alive_root / 'skills/hermes-alive/hooks/alive_kernel/admission_metadata.py', installed / 'cache.py')
        shutil.copytree(args.alive_root.resolve(strict=True), profile / 'plugins/hermes-alive',
                        ignore=shutil.ignore_patterns('.git', '__pycache__'))
        (profile / 'config.yaml').write_text(json.dumps({'plugins':{'enabled':['alive-metadata-fixture', 'hermes-alive']},
            'gateway':{'busy_input_mode':'queue'}}))
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
        print(json.dumps(asyncio.run(run())))
    print('HERMES_ALIVE_HOST_FULL_DISPATCH_PROBE_OK')


if __name__ == '__main__':
    main()
