#!/usr/bin/env python3
"""Confirmed synthetic intent -> real kernel -> actual Hermes command -> local sink.

Fake model/user/host authority; no real channel delivery or production qualification.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.cli_execution import execute_text_cli_once
from alive_kernel.cli_process import OperatorCliProcess
from alive_kernel.dispatch_outbox import DispatchOutboxError
from alive_kernel.events import Sensitivity
from alive_kernel.expression_support import ExpressionSourceSupportReviewer
from run_alive_kernel_opportunity_execution import scenario
from run_host_transport_command_probe import CHILD

CHUNK_CHARACTERIZATION = r'''
# Actual upstream aggregation, controlled per-chunk sender, no network.
import asyncio
from tools.send_message_tool import _send_chunks
chunk_calls = []
async def record_chunk(text, is_last):
    chunk_calls.append((text, is_last))
    return {'success': True, 'message_id': 'synthetic-chunk-' + str(len(chunk_calls))}
chunk_report = asyncio.run(_send_chunks(['first', 'second', 'third'], record_chunk))
assert chunk_calls == [('first', False), ('second', False), ('third', True)]
assert chunk_report == {'success': True, 'message_id': 'synthetic-chunk-3'}
'''

async def exercise(core, root, mode, *, runtime_prepare=None):
    profile = root / 'profile'
    profile.mkdir(parents=True)
    fixtures = Path(__file__).parent / 'fixtures/transport-platform'
    shutil.copytree(fixtures, profile / 'plugins/alive-transport-fixture')
    config = {'plugins':{'enabled':['alive-transport-fixture']},
        'gateway':{'platforms':{'alivefixture':{'enabled':True, 'extra':{'mode':mode}}}}}
    (profile / 'config.yaml').write_text(json.dumps(config))
    route = {'platform':'alivefixture', 'profile':'fixture', 'chat_id':'fixture-chat', 'thread_id':None}
    if runtime_prepare is None:
        journal, outbox, lease, expression, expected = await scenario(root / 'kernel', 'expression',
            transport_route=route, return_ready=True)
        interpretation, prepared, runtime = 'generate', None, None
    else:
        journal, outbox, lease, expression, expected, interpretation, prepared, runtime = await runtime_prepare(
            root / 'kernel', route)
    reviewer = ExpressionSourceSupportReviewer(journal)
    async def review(**kw):
        snapshot = json.loads(kw['messages'][1]['content'])
        assert snapshot['candidate']['text'] == expected
        kw['route_info']['provider'] = 'synthetic'
        return SimpleNamespace(model='synthetic-source-reviewer', choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({'verdict':'uncertain',
                'unsupported_claims':[], 'uncertainties':['Synthetic source is unverified.'],
                'reason':'Diagnostic fixture, not factuality qualification.'})))])
    support = await reviewer.run(subject=lease.subject, interpretation_id=interpretation,
        candidate_id=expression.event_id, operation_id='source-review', call=review,
        resolve_domain=lambda model:model)
    assert reviewer.verify_current(support.event_id, subject=lease.subject,
        interpretation_id=interpretation, candidate_id=expression.event_id)['verdict'] == 'uncertain'
    assert not support.safe_for_automatic_delivery
    # The fixture has separately supplied exact user confirmation. The review
    # cannot authorize anything; uncertainty is not silently turned into support.
    env = {k:v for k,v in os.environ.items() if k.upper() in
        {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','LANG'}}
    env.update(HERMES_HOME=str(profile), USERPROFILE=str(profile),
        PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTHONUTF8='1',
        PYTHONIOENCODING='utf-8', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
        HERMES_BUNDLED_PLUGINS=str(profile / 'empty-bundled'), HERMES_PROACTIVE_PLATFORM_ENABLED='false')
    if mode == 'skip':
        env.update(HERMES_CRON_AUTO_DELIVER_PLATFORM='alivefixture',
            HERMES_CRON_AUTO_DELIVER_CHAT_ID='fixture-chat')
    # Keep the managed venv entry. Resolving its symlink selects the base Python
    # instead, silently dropping the host's installed runtime dependencies.
    executable = Path(sys.executable).absolute()
    artifacts = [executable, *(core / path for path in (
        'hermes_cli/plugins.py','hermes_cli/send_cmd.py','tools/registry.py','tools/send_message_tool.py'))]
    pins = {path:hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts}
    characterized_child = CHILD.replace('payload = json.loads(output.getvalue())',
        CHUNK_CHARACTERIZATION + '\npayload = json.loads(output.getvalue())')
    assert characterized_child != CHILD
    diagnostic_child = ('try:\n    exec(compile(' + repr(characterized_child) + ", '<isolated-command-fixture>', 'exec'))\n"
        'except BaseException as error:\n    print(type(error).__name__ + ": " + str(error))\n    raise\n')
    process = OperatorCliProcess((str(executable), '-B', '-c', diagnostic_child, str(core), str(profile), mode,
        str(Path(__file__).resolve().parents[1] / 'hooks')), profile, 'fixture', profile, env, pins, 90)
    reports = []
    def launch(plan):
        assert plan.stdin_text == expected
        stdout, code = process(plan)
        if code != 0:
            raise RuntimeError('Synthetic command child failed: ' + stdout[-6000:])
        report = json.loads(stdout)
        assert report['network_and_process_barriers_tested'] is True
        assert report['external_delivery_proven'] is False
        reports.append(report)
        # Preserve the actual command's structured report and inner exit code.
        # Wrapper instrumentation is not itself a Hermes send result.
        return json.dumps(report['result']), report['exit_code']
    if runtime:
        from dataclasses import replace
        try:
            runtime.execute_prepared_with_cli(prepared, replace(lease, attempt_id='synthetic-other-attempt'))
        except DispatchOutboxError:
            pass
        else:
            raise AssertionError('foreign attempt lease reached the runtime host seam')
        assert not reports and not journal.read(event_type='dispatch.started')
    executor = (lambda box, item, **kwargs: runtime.execute_prepared_with_cli(prepared, item, **kwargs)) if runtime else execute_text_cli_once
    observation = executor(outbox, lease, clearance=Sensitivity.PRIVATE,
        profile_id='fixture', hermes_home=profile, observe_profile_home=lambda:profile,
        resolve_target=lambda platform, target:(target,None,None),
        extract_media=lambda text:([],text), launch=launch)
    assert observation.execution.content['operation']['text'] == expected
    effects = reports[0]['local_fixture_effects']
    assert len(effects) == (1 if mode in ('success','partial') else 0)
    for effect in effects:
        assert effect['message'] == expected and effect['chat_id'] == 'fixture-chat'
    expected_kind = {'success':'success_reported','partial':'partial_reported',
        'skip':'skip_reported','reject':'error_reported'}[mode]
    assert observation.observation.event.payload['report_kind'] == expected_kind
    if mode == 'success':
        from alive_kernel.transport_receipts import reported_message_reference
        expected_ref = reported_message_reference(outbox.protector, observation.execution.route,
                                                 'fixture-local-receipt')
        assert observation.observation.event.payload['reported_message_reference'] == expected_ref
        assert observation.observation.event.payload['canonical_quote_target_proven'] is False
        assert 'fixture-local-receipt' not in observation.observation.event.canonical_json()
    else:
        assert 'reported_message_reference' not in observation.observation.event.payload
    try:
        executor(outbox, lease, clearance=Sensitivity.PRIVATE,
            profile_id='fixture', hermes_home=profile, observe_profile_home=lambda:profile,
            resolve_target=lambda platform,target:(target,None,None), extract_media=lambda text:([],text), launch=launch)
    except DispatchOutboxError:
        pass
    else:
        raise AssertionError('consumed start launched twice')
    assert len(reports) == 1
    assert len(journal.read(event_type='dispatch.started')) == 1
    assert len(journal.read(event_type='transport.cli.observed')) == 1
    assert not journal.read(event_type='delivery.succeeded')
    assert not journal.read(event_type='preference.observed')
    return {'mode':mode, 'command_reports':1, 'local_effects':len(effects),
        'kind':expected_kind, 'external_delivery_proven':False, 'live_model_calls':0,
        'actual_chunk_helper_last_id_only':True}

async def main(core, root):
    return [await exercise(core, root / mode, mode) for mode in ('success','reject','partial','skip')]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hermes-root', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='alive-host-expression-') as directory:
        print(json.dumps(asyncio.run(main(args.hermes_root.resolve(), Path(directory).resolve()))))
    print('HERMES_ALIVE_KERNEL_HOST_EXPRESSION_CHAIN_OK')
