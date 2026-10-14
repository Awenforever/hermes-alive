#!/usr/bin/env python3
"""Actual scoped SDK delivery with synthetic pinned routing identity, no service."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from run_host_admitted_inbound_probe import forbid_network


async def run(transport, runtime):
    from gateway.config import GatewayConfig, Platform
    from gateway.platforms.event import MessageEvent
    from gateway.run import GatewayRunner, _profile_runtime_scope
    from gateway.run_inbound_consumer import run_post_admission_hook
    from gateway.session import SessionSource
    from gateway.session_identity import RoutingIdentity
    from hermes_cli.lifecycle import ainvoke_hook
    from hermes_cli.plugins import get_plugin_manager
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(multiplex_profiles=True)
    source = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-chat', user_id='synthetic-user',
                           profile='runtime-b')
    source._identity = RoutingIdentity(transport_profile='transport-a', runtime_profile='runtime-b',
        authorization_home=transport, runtime_home=runtime)
    event = MessageEvent(source=source, text='synthetic routed body', message_id='routed-1',
                         reply_to_message_id='synthetic-target', reply_to_is_own_message=True)
    with _profile_runtime_scope(transport):
        first_manager = get_plugin_manager()
        await ainvoke_hook('pre_gateway_dispatch', event=event, gateway=runner, session_store=None)
    assert await run_post_admission_hook(runner, event, source, 'synthetic-routed-session') == (False, None)
    with _profile_runtime_scope(runtime):
        second_manager = get_plugin_manager()
    assert first_manager is not second_manager
    observations = [json.loads(line) for line in (runtime / 'synthetic-metadata.jsonl').read_text().splitlines()]
    assert observations == [{'is_bot':False, 'quoted_message_id':'synthetic-target', 'quote_is_own_message':True}], \
        'actual scoped plugin instances lost the metadata handoff'
    assert not (transport / 'synthetic-metadata.jsonl').exists()
    return {'distinct_real_profile_managers':True, 'cross_profile_handoff':True,
            'routing_identity':'synthetic_pinned_not_live_canonicalizer',
            'actual_gateway_auth_proven':False, 'sends':0, 'model_calls':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--alive-root', required=True, type=Path)
    parser.add_argument('--task-mode', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-metadata-profiles-') as directory:
        root = Path(directory).resolve()
        homes = (root / 'transport-a', root / 'runtime-b')
        for home in homes:
            installed = home / 'plugins/alive-metadata-fixture'
            shutil.copytree(Path(__file__).parent / 'fixtures/admission-metadata-observer', installed)
            shutil.copy2(args.alive_root / 'skills/hermes-alive/hooks/alive_kernel/admission_metadata.py', installed / 'cache.py')
            (home / 'config.yaml').write_text(json.dumps({'plugins':{'enabled':['alive-metadata-fixture']}}))
            (home / '.env').write_text('')
        os.environ['HERMES_HOME'] = str(root)
        os.environ['HERMES_BUNDLED_PLUGINS'] = str(root / 'empty-bundled')
        os.environ['HERMES_ALIVE_TEST_METADATA_MODE'] = 'task' if args.task_mode else 'profile-cache'
        sys.path.insert(0, str(args.hermes_root.resolve(strict=True)))
        sys.addaudithook(forbid_network)
        print(json.dumps(asyncio.run(run(*homes))))
    print('HERMES_ALIVE_HOST_METADATA_PROFILE_PROBE_OK')


if __name__ == '__main__':
    main()
