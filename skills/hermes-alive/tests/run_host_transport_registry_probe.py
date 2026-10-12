#!/usr/bin/env python3
"""Opt-in real SDK/registry probe in a credential-free child; never sends."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


CHILD = r'''
import argparse, hashlib, io, json, pathlib, sys
from contextlib import redirect_stdout, redirect_stderr
root, profile = map(pathlib.Path, sys.argv[1:])
sys.path.insert(0, str(root))

def forbid_effects(event, args):
    if event in {'socket.__new__', 'socket.connect', 'socket.bind', 'socket.getaddrinfo',
                 'subprocess.Popen', 'os.system', 'os.posix_spawn'}:
        raise RuntimeError('external effects forbidden in transport registry probe')
sys.addaudithook(forbid_effects)

# Prove the barriers are installed; audit refusal happens before OS effects.
import socket, subprocess
for operation in (socket.socket, lambda: subprocess.run([sys.executable, '-V'])):
    try:
        operation()
    except RuntimeError as refused:
        assert 'external effects forbidden' in str(refused)
    else:
        raise AssertionError('effect barrier was bypassed')

from hermes_cli import plugins
from tools.registry import registry
from hermes_constants import get_hermes_home, hermes_home_key
assert pathlib.Path(get_hermes_home()).resolve() == profile.resolve()
assert pathlib.Path(plugins.__file__).resolve().is_relative_to(root)
manager = plugins.PluginManager(scope_key=str(profile))
assert manager.scope_key == hermes_home_key(profile)
ctx = plugins.PluginContext(plugins.PluginManifest(name='alive-transport-probe'), manager)
assert registry.get_entry('send_message', scope=manager.scope_key) is None
before = json.loads(ctx.dispatch_tool('send_message', {}))
assert before.get('error') == 'Unknown tool: send_message', before

# Import the actual helper without calling it or registering a replacement.
from tools import send_message_tool
assert pathlib.Path(send_message_tool.__file__).resolve().is_relative_to(root)
assert registry.get_entry('send_message', scope=manager.scope_key) is None
after = json.loads(ctx.dispatch_tool('send_message', {}))
assert after == before

# Exercise the public command parser and handler with --list, not a send.
# Do not invoke CLI bootstrap: its interrupted-upgrade recovery may mutate
# the upstream source checkout. This probe qualifies only this command.
from hermes_cli.send_cmd import register_send_subparser
parser = argparse.ArgumentParser()
register_send_subparser(parser.add_subparsers())
args = parser.parse_args(['send', '--list', '--json'])
output, errors = io.StringIO(), io.StringIO()
with redirect_stdout(output), redirect_stderr(errors):
    try:
        args.func(args)
    except SystemExit as stopped:
        assert stopped.code == 0, (stopped.code, errors.getvalue())
    else:
        raise AssertionError('public send command did not return its exit code')
targets = json.loads(output.getvalue())
assert targets == {'platforms': {}}, targets
print(json.dumps({
    'sdk_invoked': True, 'profile_isolated': True,
    'helper_import_does_not_register_send': True,
    'result_before': before, 'result_after': after,
    'public_send_list_handler': targets,
    'network_and_process_barriers_tested': True,
    'scope': 'fresh manager and helper import, not full gateway discovery',
    'source_sha256': {str(p.relative_to(root)).replace(chr(92), '/'):
                      hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (pathlib.Path(plugins.__file__),
                                pathlib.Path(send_message_tool.__file__),
                                pathlib.Path(sys.modules['tools.registry'].__file__),
                                pathlib.Path(sys.modules['hermes_cli.send_cmd'].__file__))},
    'real_sends': 0, 'production_mutations': 0
}, sort_keys=True))
'''


def probe(core: Path, python: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="alive-registry-probe-") as directory:
        profile = Path(directory).resolve()
        # No provider/proxy/profile credentials inherited from the caller.
        env = {key: value for key, value in os.environ.items()
               if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}}
        env.update(HERMES_HOME=str(profile), HOME=str(profile), USERPROFILE=str(profile),
                   PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                   HERMES_BUNDLED_PLUGINS=str(profile / "empty-bundled"),
                   HERMES_PROACTIVE_PLATFORM_ENABLED="false")
        result = subprocess.run([str(python), "-B", "-c", CHILD, str(core), str(profile)],
                                cwd=profile, env=env, capture_output=True, text=True,
                                timeout=90)
        if result.returncode:
            # Credential-free child; diagnostics are needed to distinguish
            # absent dependencies from an actual API/registration regression.
            raise RuntimeError("registry probe failed:\n" + result.stderr[-4000:])
        document = json.loads(result.stdout)
        assert document["sdk_invoked"] is True
        return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-root", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    if args.hermes_root is None:
        print("SKIP host registry probe: explicit upstream snapshot required")
        return
    print(json.dumps(probe(args.hermes_root.resolve(), args.python.resolve()), sort_keys=True))
    print("HERMES_ALIVE_HOST_TRANSPORT_REGISTRY_PROBE_OK")


if __name__ == "__main__":
    main()
