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


async def run(transport, runtime, canonical=False):
    from gateway.config import GatewayConfig, Platform
    from gateway.platforms.event import MessageEvent
    from gateway.run import GatewayRunner, _profile_runtime_scope
    from gateway.run_inbound_consumer import run_post_admission_hook
    from gateway.session import SessionSource
    from gateway.session_identity import RoutingIdentity, canonical_identity, identity_of
    from gateway.profile_routing import ProfileRoute
    from hermes_cli.lifecycle import ainvoke_hook
    from hermes_cli.plugins import get_plugin_manager
    if canonical:
        # A real gateway publishes this bootstrap mode before scoped gates
        # read .env. Merely constructing GatewayConfig is not activation.
        from agent.secret_scope import set_multiplex_active
        set_multiplex_active(True)
    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(multiplex_profiles=True)
    runner._primary_profile_name = 'default'
    runner.adapters = {}
    runner.pairing_store = None
    runner.pairing_stores = {}
    source = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-chat', user_id='synthetic-user',
                           chat_type='group', profile=None if canonical else 'runtime-b')
    if canonical:
        class FixtureReceiver:
            pass
        receiver = FixtureReceiver()
        runner._profile_adapters = {'transport-a':{Platform.TELEGRAM:receiver}}
        runner.config.profile_routes = [ProfileRoute(name='synthetic-route', platform='telegram',
            profile='runtime-b', chat_id='synthetic-chat', bot_profile='transport-a')]
        with _profile_runtime_scope(transport):
            resolved = canonical_identity(source, runner=runner, adapter=receiver)
        assert resolved is identity_of(source) and resolved.adapter() is receiver
        assert resolved.transport_profile == 'transport-a' and resolved.runtime_profile == 'runtime-b'
        assert resolved.authorization_home == transport and resolved.runtime_home == runtime
        assert source.profile == 'runtime-b' and not resolved.transport_inferred
    else:
        source._identity = RoutingIdentity(transport_profile='transport-a', runtime_profile='runtime-b',
            authorization_home=transport, runtime_home=runtime)
    event = MessageEvent(source=source, text='synthetic routed body', message_id='routed-1',
                         reply_to_message_id='synthetic-target', reply_to_is_own_message=True)
    with _profile_runtime_scope(transport):
        first_manager = get_plugin_manager()
        if canonical:
            assert runner._is_user_authorized_for_source(source) is True
            admitted = await runner._hm_admit_event(event)
            assert admitted is not None and admitted[2] is False
        else:
            await ainvoke_hook('pre_gateway_dispatch', event=event, gateway=runner, session_store=None)
    assert await run_post_admission_hook(runner, event, source, 'synthetic-routed-session') == (False, None)
    with _profile_runtime_scope(runtime):
        second_manager = get_plugin_manager()
    assert first_manager is not second_manager
    observations = [json.loads(line) for line in (runtime / 'synthetic-metadata.jsonl').read_text().splitlines()]
    assert observations == [{'is_bot':False, 'quoted_message_id':'synthetic-target', 'quote_is_own_message':True}], \
        'actual scoped plugin instances lost the metadata handoff'
    assert not (transport / 'synthetic-metadata.jsonl').exists()
    if canonical:
        other = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-chat', user_id='synthetic-other-user',
                              chat_type='group')
        with _profile_runtime_scope(transport):
            canonical_identity(other, runner=runner, adapter=receiver)
            assert runner._is_user_authorized_for_source(other) is False
            assert await runner._hm_admit_event(MessageEvent(source=other, text='synthetic denied', message_id='denied-2')) is None
        # Runtime's allowlist is deliberately different: the receiving
        # transport authorizes, not the destination's inherited credentials.
        assert len((runtime / 'synthetic-metadata.jsonl').read_text().splitlines()) == 1
        runner.config.profile_routes.append(ProfileRoute(name='synthetic-unserved', platform='telegram',
            profile='missing-runtime', chat_id='synthetic-unserved-chat', bot_profile='transport-a'))
        unserved = SessionSource(platform=Platform.TELEGRAM, chat_id='synthetic-unserved-chat',
                                 user_id='synthetic-user', chat_type='group')
        with _profile_runtime_scope(transport):
            assert canonical_identity(unserved, runner=runner, adapter=receiver) is None
            assert unserved.profile_route_rejected is True
            assert await runner._hm_admit_event(MessageEvent(source=unserved, text='synthetic unserved', message_id='unserved-3')) is None
        assert not (runtime.parent / 'missing-runtime').exists()
        assert len((runtime / 'synthetic-metadata.jsonl').read_text().splitlines()) == 1
    return {'distinct_real_profile_managers':True, 'cross_profile_handoff':True,
            'canonical_route_selector_executed':canonical,
            'routing_identity':'actual_resolver_fixture_receiver' if canonical else 'synthetic_pinned_not_live_canonicalizer',
            'actual_gateway_auth_gates_executed':canonical,
            'external_adapter_login_proven':False, 'full_gateway_session_path':False, 'sends':0, 'model_calls':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--alive-root', required=True, type=Path)
    parser.add_argument('--task-mode', action='store_true')
    parser.add_argument('--canonical-mode', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-metadata-profiles-') as directory:
        root = Path(directory).resolve()
        homes = (root / 'profiles/transport-a', root / 'profiles/runtime-b')
        for home in homes:
            installed = home / 'plugins/alive-metadata-fixture'
            shutil.copytree(Path(__file__).parent / 'fixtures/admission-metadata-observer', installed)
            shutil.copy2(args.alive_root / 'skills/hermes-alive/hooks/alive_kernel/admission_metadata.py', installed / 'cache.py')
            (home / 'config.yaml').write_text(json.dumps({'plugins':{'enabled':['alive-metadata-fixture']}}))
            (home / '.env').write_text('TELEGRAM_ALLOWED_USERS=' +
                ('synthetic-user' if home == homes[0] else 'synthetic-other-user') + '\n' if args.canonical_mode else '')
        for key in tuple(os.environ):
            if key.endswith(('_ALLOWED_USERS', '_ALLOW_ALL_USERS', '_ALLOW_BOTS',
                             '_GROUP_ALLOWED_USERS', '_GROUP_ALLOWED_CHATS')):
                os.environ.pop(key)
        os.environ['HERMES_HOME'] = str(root)
        os.environ['HERMES_BUNDLED_PLUGINS'] = str(root / 'empty-bundled')
        os.environ['HERMES_ALIVE_TEST_METADATA_MODE'] = 'task' if args.task_mode else 'profile-cache'
        sys.path.insert(0, str(args.hermes_root.resolve(strict=True)))
        # Core imports its cached source-version identity during Gateway startup.
        # Populate that known read-only Git probe before the stricter effect
        # guard; the guarded dispatch still cannot spawn arbitrary subprocesses.
        from hermes_cli import version_info
        assert Path(version_info.__file__).resolve().parents[1] == args.hermes_root.resolve()
        version_info.get_version_info()
        sys.addaudithook(forbid_network)
        print(json.dumps(asyncio.run(run(*homes, canonical=args.canonical_mode))))
    print('HERMES_ALIVE_HOST_METADATA_PROFILE_PROBE_OK')


if __name__ == '__main__':
    main()
