#!/usr/bin/env python3
"""Actual Hermes ingress authorization gates with synthetic, local-only sources.

Not a running/paired external transport or full _handle_message qualification.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

from run_host_admitted_inbound_probe import forbid_network


async def run():
    from gateway.config import GatewayConfig, Platform
    from gateway.pairing import PairingStore
    from gateway.platforms.event import MessageEvent
    from gateway.run import GatewayRunner
    from gateway.run_inbound_consumer import run_post_admission_hook
    from gateway.session import SessionSource
    from hermes_cli.plugins import discover_plugins, has_hook

    discover_plugins()
    assert has_hook('post_gateway_admission')
    # Use real authorization, pre-dispatch and bot-admission methods. No patch
    # manufactures a positive/negative auth verdict. No adapters/agent start.
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(multiplex_profiles=False)
    runner.adapters = {}
    runner._primary_profile_name = 'default'
    runner._profile_adapters = {}
    runner.pairing_stores = {}
    runner.pairing_store = PairingStore()
    profile = Path(os.environ['HERMES_HOME'])
    journal_path = profile / 'plugin-data/hermes-alive/runtime/kernel/experience.sqlite3'
    source = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-chat',
                           chat_type='group', user_id='synthetic-user')
    event = MessageEvent(source=source, message_id='synthetic-unknown-1',
                         text='Synthetic full admission text ' + 'x' * 1200)
    assert runner._is_user_authorized_for_source(source) is False
    assert await runner._hm_admit_event(event) is None
    assert not journal_path.exists()
    code = runner.pairing_store.generate_code('telegram', 'synthetic-user')
    assert code and runner.pairing_store.approve_code('telegram', code)['user_id'] == 'synthetic-user'
    assert runner._is_user_authorized_for_source(source) is True
    admitted = await runner._hm_admit_event(event)
    assert admitted is not None and admitted[2] is False
    # Deliberately compose only the actual admission gates and public consumer
    # helper; session/control/busy lanes of _handle_message are not exercised.
    assert await run_post_admission_hook(runner, admitted[0], admitted[1], 'synthetic-session') == (False, None)
    assert journal_path.exists()
    sys.path.insert(0, str(profile / 'plugins/hermes-alive/skills/hermes-alive/hooks'))
    from alive_kernel.event_store import ExperienceJournal
    journal = ExperienceJournal(journal_path)
    captured = journal.read(event_type='conversation.admitted')
    assert len(captured) == 1 and captured[0].event.payload['erasable_content_stored'] is False
    other = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-chat',
                          chat_type='group', user_id='synthetic-other-user')
    assert await runner._hm_admit_event(MessageEvent(source=other, text='synthetic foreign', message_id='other-1')) is None
    assert len(journal.read(event_type='conversation.admitted')) == 1
    rejected_route = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-chat',
        chat_type='group', user_id='synthetic-user', profile_route_rejected=True)
    assert await runner._hm_admit_event(MessageEvent(source=rejected_route, text='synthetic rejected route',
        message_id='route-1')) is None
    assert runner.pairing_store.revoke('telegram', 'synthetic-user') is True
    assert runner._is_user_authorized_for_source(source) is False
    assert await runner._hm_admit_event(event) is None
    assert len(journal.read(event_type='conversation.admitted')) == 1
    # Authorized is not synonymous with human/paired. The SDK's native source
    # snapshot currently drops this bot bit; do not certify human feedback.
    os.environ['TELEGRAM_ALLOW_BOTS'] = 'all'
    bot_source = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-bot-chat',
        chat_type='group', user_id='synthetic-bot', is_bot=True)
    assert runner.pairing_store.is_approved('telegram', 'synthetic-bot') is False
    bot_event = MessageEvent(source=bot_source, text='synthetic authorized bot', message_id='bot-1')
    bot_admitted = await runner._hm_admit_event(bot_event)
    assert bot_admitted is not None and bot_admitted[2] is False
    assert 'is_bot' not in bot_source.to_dict()
    assert await run_post_admission_hook(runner, bot_admitted[0], bot_admitted[1], 'synthetic-bot-session') == (False, None)
    captures = journal.read(event_type='conversation.admitted')
    assert len(captures) == 2
    assert all(row.event.payload['learning_authority_granted'] is False for row in captures)
    assert all(row.event.payload['principal_kind'] == 'not_exposed_by_host' for row in captures)
    os.environ.pop('TELEGRAM_ALLOW_BOTS')
    assert not journal.read(event_type='outcome.recorded')
    return {'actual_auth_gates':True, 'actual_pairing_store':True,
            'authorized_human_source_structural_captures':1, 'unauthorized_captures':0,
            'revocation_enforced':True, 'rejected_route_blocked':True,
            'authorized_bot_capture':True, 'native_bot_marker_available':False,
            'full_gateway_session_path':False, 'external_paired_transport':False,
            'sends':0, 'model_calls':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--alive-root', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-host-auth-') as directory:
        profile = Path(directory).resolve()
        shutil.copytree(args.alive_root.resolve(strict=True), profile / 'plugins/hermes-alive',
                        ignore=shutil.ignore_patterns('.git', '__pycache__'))
        (profile / 'config.yaml').write_text(json.dumps({'plugins':{'enabled':['hermes-alive']}}))
        (profile / '.env').write_text('')
        # The disposable host's admission may not inherit an ambient allow-all.
        for key in tuple(os.environ):
            if key.endswith(('_ALLOWED_USERS', '_ALLOW_ALL_USERS', '_ALLOW_BOTS',
                             '_GROUP_ALLOWED_USERS', '_GROUP_ALLOWED_CHATS')):
                os.environ.pop(key)
        os.environ['HERMES_HOME'] = str(profile)
        os.environ['HERMES_BUNDLED_PLUGINS'] = str(profile / 'empty-bundled')
        os.environ.pop('HERMES_ALIVE_SHARED_DIR', None)
        os.environ['HERMES_ALIVE_KERNEL_SHADOW_ENABLED'] = 'true'
        sys.path.insert(0, str(args.hermes_root.resolve(strict=True)))
        sys.addaudithook(forbid_network)
        for operation in (lambda:socket.getaddrinfo('example.invalid', 443),
                          lambda:subprocess.run([sys.executable, '-V'])):
            try: operation()
            except RuntimeError: pass
            else: raise AssertionError('authorization-probe effect barrier failed')
        print(json.dumps(asyncio.run(run())))
    print('HERMES_ALIVE_HOST_INGRESS_AUTHORIZATION_PROBE_OK')


if __name__ == '__main__':
    main()
