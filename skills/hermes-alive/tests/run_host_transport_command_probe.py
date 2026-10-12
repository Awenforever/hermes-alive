#!/usr/bin/env python3
"""Real public command -> config -> discovered plugin -> local synthetic sink.

This is an opt-in platform-fixture integration test, not Weixin or any real
provider delivery qualification. Only a disposable profile receives effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
from alive_kernel.transport_receipts import classify_cli_report
from alive_kernel.cli_process import OperatorCliProcess
from alive_kernel.cli_send_contract import compile_text_cli_plan

CHILD = r'''
import argparse, io, json, os, pathlib, re, shlex, sys
from contextlib import redirect_stdout, redirect_stderr
core, profile, mode = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(core))
sys.path.insert(0, sys.argv[4])  # Explicit test-package hooks, not caller PYTHONPATH.
def no_external_effects(event, args):
    if event == 'subprocess.Popen':
        executable, command, cwd, env = args
        parts = shlex.split(command) if isinstance(command, str) else list(command)
        fixed = {
            ('rev-parse', 'HEAD'), ('branch', '--show-current'),
            ('log', '-1', '--format=%ct', 'HEAD'),
            ('--no-optional-locks', 'status', '--porcelain', '-uno'),
            ('tag', '--merged', 'HEAD', '--list', 'v[0-9]*'),
            ('rev-parse', '--short=7', 'HEAD'),
            ('describe', '--tags', '--long', '--match', 'v2[0-9][0-9][0-9].*', 'HEAD'),
        }
        tail = tuple(parts[1:])
        version_read = (len(tail) == 3 and tail[:2] == ('rev-list', '--count')
                        and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+\.\.HEAD', tail[2]))
        tag_read = (len(tail) == 2 and tail[0] == 'show'
                    and re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+:pyproject\.toml', tail[1]))
        if (pathlib.Path(executable or parts[0]).name.lower() in {'git', 'git.exe'}
                and cwd and pathlib.Path(cwd).resolve() == core.resolve()
                and (tail in fixed or version_read or tag_read)):
            return  # Exact read-only source-provenance commands, no shell.
        raise RuntimeError('process launch forbidden in command probe')
    if event in {'os.system', 'os.posix_spawn'}:
        raise RuntimeError('process launch forbidden in command probe')
    if event in {'socket.connect', 'socket.bind'}:
        address = args[1]
        # CPython asyncio creates an internal loopback socketpair on Windows.
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1'}:
            raise RuntimeError('external network forbidden in command probe')
    if event == 'socket.getaddrinfo':
        raise RuntimeError('DNS forbidden in command probe')
    if event == 'socket.sendto':
        raise RuntimeError('datagram sends forbidden in command probe')
sys.addaudithook(no_external_effects)
import socket, subprocess
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
    try:
        probe_socket.connect(('192.0.2.1', 1))
    except RuntimeError as refused:
        assert 'external network forbidden' in str(refused)
    else:
        raise AssertionError('external connection barrier failed')
try:
    subprocess.run([sys.executable, '-V'])
except RuntimeError as refused:
    assert 'process launch forbidden' in str(refused)
else:
    raise AssertionError('process barrier failed')
from hermes_constants import get_hermes_home
assert pathlib.Path(get_hermes_home()).resolve() == profile.resolve()
from hermes_cli.plugins import discover_plugins
discover_plugins()
from gateway.platform_registry import platform_registry
entry = platform_registry.get('alivefixture')
assert entry is not None and entry.standalone_sender_fn is not None
assert entry.plugin_name == 'alive-transport-fixture'
from tools.registry import registry
assert registry.get_entry('send_message') is None
from hermes_cli.send_cmd import register_send_subparser
parser = argparse.ArgumentParser()
register_send_subparser(parser.add_subparsers())
if mode == 'skip':
    os.environ['HERMES_CRON_AUTO_DELIVER_PLATFORM'] = 'alivefixture'
    os.environ['HERMES_CRON_AUTO_DELIVER_CHAT_ID'] = 'fixture-chat'
from alive_kernel.cli_send_contract import CliSendContractError, compile_text_cli_plan
from gateway.platforms.base import BasePlatformAdapter
from tools.send_message_targets import resolve_send_target
chat = 'other-chat' if mode == 'wrong_route' else 'fixture-chat'
document = {'schema_version': 1, 'capability': 'hermes.channel.send',
            'operation': {'text': sys.stdin.read(), 'format': 'markdown'}}
route = {'platform': 'alivefixture', 'profile': 'fixture', 'chat_id': chat, 'thread_id': None}
# Characterize actual host interpretation before proving preflight rejection.
media_example = 'MEDIA:' + str(profile / 'synthetic-attachment.pdf')
assert BasePlatformAdapter.extract_media(media_example)[0]
for controlled_text in (media_example, '[[as_document]]body', '[[audio_as_voice]]body'):
    unsafe_document = {**document, 'operation': {'text': controlled_text, 'format': 'markdown'}}
    try:
        compile_text_cli_plan(
            unsafe_document, route, profile_id='fixture', hermes_home=profile,
            resolve_target=resolve_send_target, extract_media=BasePlatformAdapter.extract_media,
            observe_profile_home=get_hermes_home)
    except CliSendContractError:
        pass
    else:
        raise AssertionError('text compilation accepted a real host media directive')
assert not (profile / 'fixture-deliveries.jsonl').exists()
plan = compile_text_cli_plan(
    document, route, profile_id='fixture', hermes_home=profile,
    resolve_target=resolve_send_target, extract_media=BasePlatformAdapter.extract_media,
    observe_profile_home=get_hermes_home)
args = parser.parse_args(plan.arguments)
assert tuple(sys.argv[5:]) == plan.arguments
output, errors = io.StringIO(), io.StringIO()
original_stdin = sys.stdin
sys.stdin = io.StringIO(plan.stdin_text)
with redirect_stdout(output), redirect_stderr(errors):
    try:
        args.func(args)
    except SystemExit as stopped:
        code = stopped.code
    else:
        raise AssertionError('command did not return an exit code')
sys.stdin = original_stdin
payload = json.loads(output.getvalue())
if payload.get('error'):
    print(errors.getvalue(), file=sys.stderr)
receipt_path = profile / 'fixture-deliveries.jsonl'
effects = [json.loads(line) for line in receipt_path.read_text().splitlines()] if receipt_path.exists() else []
print(json.dumps({'mode': mode, 'exit_code': code, 'result': payload,
                  'local_fixture_effects': effects, 'external_delivery_proven': False,
                  'network_and_process_barriers_tested': True,
                  'source_revision_scope': 'explicit upstream checkout, no full CLI bootstrap'}, sort_keys=True))
'''


def run(core: Path) -> list[dict]:
    results = []
    fixture = Path(__file__).parent / "fixtures" / "transport-platform"
    for mode in ("success", "reject", "partial", "skip", "wrong_route", "disabled"):
        with tempfile.TemporaryDirectory(prefix="alive-command-probe-") as directory:
            profile = Path(directory).resolve()
            shutil.copytree(fixture, profile / "plugins" / "alive-transport-fixture")
            # JSON is valid YAML; both plugin discovery and the real config
            # loader read this file. No loader or registry function is patched.
            config = {"plugins": {"enabled": ["alive-transport-fixture"]},
                      "gateway": {"platforms": {"alivefixture": {
                          "enabled": mode != "disabled", "extra": {"mode": mode}}}}}
            (profile / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
            env = {k: v for k, v in os.environ.items()
                   if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG"}}
            env.update(HERMES_HOME=str(profile), HOME=str(profile), USERPROFILE=str(profile),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                       PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                       GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       HERMES_BUNDLED_PLUGINS=str(profile / "empty-bundled"),
                       HERMES_PROACTIVE_PLATFORM_ENABLED="false")
            # Parent callbacks are synthetic; child rechecks the same plan with
            # actual host callbacks before invoking the real command handler.
            chat = "other-chat" if mode == "wrong_route" else "fixture-chat"
            plan = compile_text_cli_plan(
                {"schema_version": 1, "capability": "hermes.channel.send",
                 "operation": {"text": "synthetic integration body", "format": "markdown"}},
                {"platform": "alivefixture", "profile": "fixture", "chat_id": chat, "thread_id": None},
                profile_id="fixture", hermes_home=profile, observe_profile_home=lambda: profile,
                extract_media=lambda text: ([], text), resolve_target=lambda p, r: (r, None, None))
            executable = Path(sys.executable).resolve()
            artifacts = [executable, *(core / path for path in (
                "hermes_cli/plugins.py", "hermes_cli/send_cmd.py", "tools/registry.py",
                "tools/send_message_tool.py"))]
            pins = {}
            for artifact in artifacts:
                with artifact.open("rb") as stream:
                    pins[artifact] = hashlib.file_digest(stream, "sha256").hexdigest()
            launcher = OperatorCliProcess(
                (str(executable), "-B", "-c", CHILD, str(core), str(profile), mode,
                 str(Path(__file__).resolve().parents[1] / "hooks")),
                profile, "fixture", profile, env, pins, 90)
            stdout, code = launcher(plan)
            if code:
                raise RuntimeError("command probe child failed; external effects remain unproven")
            result = json.loads(stdout)
            effects, payload = result["local_fixture_effects"], result["result"]
            if mode == "success":
                if payload.get("error"):
                    raise RuntimeError(str(payload["error"]))
                assert result["exit_code"] == 0 and payload.get("success") is True, result
                assert len(effects) == 1 and effects[0]["effect"] == "complete"
            elif mode == "partial":
                assert result["exit_code"] == 1 and payload.get("partial_success") is True, result
                assert len(effects) == 1 and effects[0]["effect"] == "partial"
            elif mode == "skip":
                assert result["exit_code"] == 0 and payload.get("skipped") is True, result
                assert effects == []
            else:
                assert result["exit_code"] == 1 and payload.get("error")
                assert effects == []
            for effect in effects:
                assert effect["chat_id"] == "fixture-chat"
                assert effect["message"] == "synthetic integration body"
            report = classify_cli_report(json.dumps(payload), result["exit_code"])
            expected = {"success": "success_reported", "partial": "partial_reported",
                        "skip": "skip_reported"}.get(mode, "error_reported")
            assert report.kind.value == expected, result
            result["kernel_cli_report"] = report.to_document()
            results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-root", type=Path)
    args = parser.parse_args()
    if args.hermes_root is None:
        print("SKIP command transport probe: explicit upstream snapshot required")
        return
    print(json.dumps(run(args.hermes_root.resolve()), sort_keys=True))
    print("HERMES_ALIVE_HOST_TRANSPORT_COMMAND_PROBE_OK")


if __name__ == "__main__":
    main()
