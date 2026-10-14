#!/usr/bin/env python3
"""Actual public SDK dispatch, not actual gateway authorization or user delivery."""
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
from types import SimpleNamespace

def forbid_network(event, args):
    if event in ('socket.getaddrinfo', 'socket.sendto', 'subprocess.Popen', 'os.system'):
        raise RuntimeError('external effects forbidden in admission probe')
    if event in ('socket.connect','socket.bind'):
        address = args[1]
        if not isinstance(address, tuple) or address[0] not in ('127.0.0.1','::1'):
            raise RuntimeError('external effects forbidden in admission probe')

async def run(alive_root=None):
    from hermes_cli.plugins import discover_plugins, has_hook
    from gateway.run_inbound_consumer import run_post_admission_hook
    discover_plugins()
    assert has_hook('post_gateway_admission')
    runner = SimpleNamespace(config=SimpleNamespace(multiplex_profiles=False))
    source_dict = {'platform':'weixin','user_id':'synthetic-user','chat_id':'synthetic-chat',
                   'profile':'synthetic-profile','thread_id':None}
    source = SimpleNamespace(platform=SimpleNamespace(value='weixin'), to_dict=lambda:source_dict)
    text = 'Synthetic full event ' + 'x' * 1200
    event = SimpleNamespace(message_id='synthetic-inbound-1', text=text,
        reply_to_message_id='synthetic-outbound-1', reply_to_text='synthetic quote',
        reply_to_is_own_message=True)
    assert await run_post_admission_hook(runner, event, source, 'synthetic-session') == (False, None)
    event.text = 'fixture-fail'
    assert await run_post_admission_hook(runner, event, source, 'synthetic-session') == (False, None)
    event.text = 'fixture-handle'
    assert await run_post_admission_hook(runner, event, source, 'synthetic-session') == (True, 'synthetic acknowledgement')
    profile = Path(os.environ['HERMES_HOME'])
    rows = [json.loads(line) for line in (profile / 'fixture-admissions.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 3
    print(json.dumps({'observed_fields':sorted(rows[0]), 'text_characters':len(rows[0].get('text',''))}))
    expected = {'session_key':'synthetic-session','platform':'weixin','source':source_dict,
                'message_id':'synthetic-inbound-1','text':text}
    assert {key:rows[0][key] for key in expected} == expected
    # SDK observers may add versioned telemetry. Additional plain fields do not
    # imply truncated text, quotation availability or new user authority.
    assert 'telemetry_schema_version' in rows[0]
    assert 'reply_to_message_id' not in rows[0] and 'reply_to_text' not in rows[0]
    alive_captures = 0
    if alive_root is not None:
        shared = profile / 'plugin-data/hermes-alive/runtime'
        assert not (shared / 'kernel/experience.sqlite3').exists()
        os.environ['HERMES_ALIVE_KERNEL_SHADOW_ENABLED'] = 'true'
        event.message_id = 'synthetic-native-1'
        event.text = text
        assert await run_post_admission_hook(runner, event, source, 'synthetic-session') == (False, None)
        # A separate internal import reads the same persisted consent/state;
        # the actual registered plugin owns observation, not a patched callback.
        sys.path.insert(0, str(alive_root / 'skills/hermes-alive/hooks'))
        from alive_kernel.event_store import ExperienceJournal
        from alive_kernel.content_vault import ContentVault
        from alive_kernel.events import Sensitivity
        from alive_kernel.privacy import LocalIdentityProtector
        from alive_kernel.retention import RetentionProjection
        root = shared / 'kernel'
        journal = ExperienceJournal(root / 'experience.sqlite3')
        first = journal.read(event_type='conversation.admitted')
        assert len(first) == 1 and first[0].event.payload['erasable_content_stored'] is False
        subject = LocalIdentityProtector(root / 'identity.key').pseudonym('user', 'synthetic-user')
        vault = ContentVault(root / 'content-vault', backup_root=root / 'content-backups')
        RetentionProjection(journal, content_vault=vault).append_consent(subject=subject, actor=subject,
            enabled=True, retention_days=2, directions=('inbound',), sensitivity=Sensitivity.PRIVATE)
        event.message_id = 'synthetic-native-2'
        assert await run_post_admission_hook(runner, event, source, 'synthetic-session') == (False, None)
        captures = journal.read(event_type='conversation.admitted')
        assert len(captures) == 2
        retained = captures[-1].event.payload['content']
        assert vault.resolve_json(retained['content_id'], expected_subject=subject,
            expected_purpose='conversation.inbound', expected_sensitivity=Sensitivity.PRIVATE)['text'] == text
        assert not journal.read(event_type='outcome.recorded')
        alive_captures = len(captures)
    return {'callbacks':len(rows),'alive_native_captures':alive_captures,'full_text_characters':len(rows[0]['text']),
        'stable_message_id_present':True, 'quote_metadata_present':False,
        'actual_gateway_admission_proven':False,'external_delivery_proven':False,
        'sends':0,'model_calls':0}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', required=True, type=Path)
    parser.add_argument('--alive-root', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-admission-probe-') as directory:
        profile = Path(directory).resolve()
        fixture = Path(__file__).parent / 'fixtures/admission-observer'
        shutil.copytree(fixture, profile / 'plugins/alive-admission-fixture')
        enabled = ['alive-admission-fixture']
        if args.alive_root:
            args.alive_root = args.alive_root.resolve(strict=True)
            shutil.copytree(args.alive_root, profile / 'plugins/hermes-alive',
                            ignore=shutil.ignore_patterns('.git', '__pycache__'))
            enabled.append('hermes-alive')
        (profile / 'config.yaml').write_text(json.dumps({'plugins':{'enabled':enabled}}))
        os.environ['HERMES_HOME'] = str(profile)
        os.environ.pop('HERMES_ALIVE_SHARED_DIR', None)
        os.environ['HERMES_ALIVE_KERNEL_SHADOW_ENABLED'] = 'false'
        os.environ['HERMES_BUNDLED_PLUGINS'] = str(profile / 'empty-bundled')
        sys.path.insert(0, str(args.hermes_root.resolve(strict=True)))
        sys.addaudithook(forbid_network)
        for operation in (lambda:socket.getaddrinfo('example.invalid', 443),
                          lambda:subprocess.run([sys.executable, '-V'])):
            try: operation()
            except RuntimeError: pass
            else: raise AssertionError('admission-probe external-effect barrier failed')
        print(json.dumps(asyncio.run(run(args.alive_root))))
    print('HERMES_ALIVE_HOST_ADMITTED_INBOUND_PROBE_OK')
