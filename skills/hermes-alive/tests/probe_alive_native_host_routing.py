"""Actual Core profile/alias/credential boundary; synthetic profiles, no sends."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core', type=Path, required=True)
args = parser.parse_args()
core = args.core.resolve(strict=True)


def main(root):
    ambient = root/'ambient'
    ambient.mkdir()
    os.environ.update(HERMES_HOME=str(ambient), HOME=str(ambient),
                      PRIMARY_KEY='synthetic-ambient-not-an-owner',
                      ALIAS_KEY='synthetic-ambient-not-an-owner',
                      BACKUP_KEY='synthetic-ambient-not-an-owner',
                      UNDECLARED_OWNER_KEY='synthetic-ambient-must-not-leak')
    original_env = dict(os.environ)
    sys.path.insert(0, str(core))
    network_attempts = []

    def deny_external(event, values):
        if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen'):
            network_attempts.append(event)
            raise RuntimeError('routing qualification forbids external IO')

    sys.addaudithook(deny_external)
    # Only metadata HTTP is controlled. Never replace config/auth/alias resolvers.
    import httpx
    original_send = httpx.Client.send
    httpx.Client.send = lambda client, request, **kwargs: httpx.Response(503, request=request)
    try:
        from hermes_constants import (get_hermes_home, set_hermes_home_override,
                                      reset_hermes_home_override)
        from agent.secret_scope import (build_profile_secret_scope, set_secret_scope,
                                       reset_secret_scope, set_multiplex_context,
                                       reset_multiplex_context, get_secret,
                                       current_secret_scope, is_multiplex_active)
        from hermes_cli.config import load_config_readonly
        from hermes_cli.model_switch import resolve_startup_model_route
        from hermes_cli.runtime_provider import (frozen_runtime_config,
            resolve_runtime_provider, resolve_runtime_with_fallback)
        from hermes_cli.fallback_config import get_fallback_chain, resolve_entry_api_key

        @contextmanager
        def bound(home):
            home_token = set_hermes_home_override(home)
            multiplex_token = set_multiplex_context(True)
            secret_token = None
            try:
                secret_token = set_secret_scope(build_profile_secret_scope(home), profile_home=str(home))
                yield
            finally:
                if secret_token is not None:
                    reset_secret_scope(secret_token)
                reset_multiplex_context(multiplex_token)
                reset_hermes_home_override(home_token)

        homes = {}
        for label in ('A', 'B'):
            home = root/label
            home.mkdir(mode=0o700)
            configuration = dict(model=dict(default='primary-'+label, provider='custom:owner-'+label),
                custom_providers=[dict(name='owner-'+label, model='primary-'+label,
                    base_url='https://primary-'+label.lower()+'.invalid/v1', key_env='PRIMARY_KEY',
                    api_mode='chat_completions')],
                model_aliases=dict(chosen=dict(model='alias-'+label, provider='custom',
                    base_url='https://alias-'+label.lower()+'.invalid/v1', key_env='ALIAS_KEY')),
                fallback_providers=[dict(provider='custom', model='backup-'+label,
                    base_url='https://backup-'+label.lower()+'.invalid/v1', key_env='BACKUP_KEY')])
            (home/'config.yaml').write_text(json.dumps(configuration), encoding='utf-8')
            (home/'.env').write_text('\n'.join(name+'=synthetic-'+label+'-'+name for name in
                                      ('PRIMARY_KEY', 'ALIAS_KEY', 'BACKUP_KEY')), encoding='utf-8')
            homes[label] = home

        # Interleaved owners reuse the same alias spelling; no cache-reset patch.
        for label in ('A', 'B', 'A'):
            home = homes[label]
            before = {name: (home/name).read_bytes() for name in ('config.yaml', '.env')}
            with bound(home):
                assert get_hermes_home().resolve() == home.resolve()
                config = load_config_readonly()
                cfg_model = config['model']
                with frozen_runtime_config(config):
                    runtime, fallback = resolve_runtime_with_fallback(config,
                        requested=cfg_model['provider'], target_model=cfg_model['default'])
                    assert fallback is None
                    assert runtime['api_key'] == 'synthetic-'+label+'-PRIMARY_KEY'
                    assert runtime['base_url'] == 'https://primary-'+label.lower()+'.invalid/v1'
                    alias = resolve_startup_model_route('chosen',
                        current_provider=cfg_model['provider'], user_providers=config.get('providers'),
                        custom_providers=config.get('custom_providers'))
                    assert alias.model == 'alias-'+label
                    resolved_alias = resolve_runtime_provider(requested=alias.provider,
                        target_model=alias.model, explicit_base_url=alias.base_url,
                        explicit_api_key=alias.api_key or None)
                    assert resolved_alias['api_key'] == 'synthetic-'+label+'-ALIAS_KEY'
                    assert resolved_alias['base_url'] == 'https://alias-'+label.lower()+'.invalid/v1'
                    entry, = get_fallback_chain(config)
                    fallback_runtime = resolve_runtime_provider(requested=entry['provider'],
                        target_model=entry['model'], explicit_base_url=entry['base_url'],
                        explicit_api_key=resolve_entry_api_key(entry))
                    assert fallback_runtime['api_key'] == 'synthetic-'+label+'-BACKUP_KEY'
                    assert fallback_runtime['base_url'] == 'https://backup-'+label.lower()+'.invalid/v1'
                assert get_secret('UNDECLARED_OWNER_KEY') is None
            # Core's "readonly" loader means a borrowed config mapping, not
            # filesystem-read-only: its successful parse creates LKG backups.
            # Preserve that observation rather than patching out the writer.
            assert {name: (home/name).read_bytes() for name in before} == before
            extra = sorted(set(path.name for path in home.iterdir()) - set(before))
            print('HOST_ROUTING_CREATED_NAMES='+json.dumps(extra), flush=True)
            assert set(extra) <= {'SOUL.md', 'audio_cache', 'backups', 'cron', 'hooks',
                                  'image_cache', 'logs', 'memories', 'pairing', 'sessions', 'skills'}
            for name in ('sessions', 'memories', 'pairing', 'cron'):
                assert not any((home/name).rglob('*'))
            assert get_hermes_home().resolve() == ambient.resolve()
            assert current_secret_scope() is None and not is_multiplex_active()
            assert dict(os.environ) == original_env
        try:
            with bound(homes['B']):
                raise ValueError('synthetic cancelled binding')
        except ValueError:
            pass
        assert get_hermes_home().resolve() == ambient.resolve()
        assert not network_attempts
    finally:
        httpx.Client.send = original_send


with tempfile.TemporaryDirectory(prefix='alive-host-routing-') as raw:
    main(Path(raw))
print('HERMES_ALIVE_ACTUAL_HOST_ROUTING_SCOPE_OK')
