"""Explicit opt-in real Core main-agent continuation, public synthetic data only.

Run with --core PATH in a Core-PM environment, never against production HOME.
The operator supplies a private model-only projection outside the repository.
No messaging adapter connects to an external account; model tools are disabled.
Outputs include complete original responses and actual Core request messages,
NOT an automatic semantic verdict or a consumer-install/quality qualification.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import stat
import tempfile

if os.environ.get('ALIVE_CORE_FOLLOWUP_AUTHORIZATION') != 'public_synthetic_main_turns_no_delivery':
    raise SystemExit('explicit isolated real-model authorization required')
projection = Path(os.environ['ALIVE_CORE_FOLLOWUP_MODEL_PROJECTION']).resolve(strict=True)
evidence = Path(os.environ['ALIVE_CORE_FOLLOWUP_EVIDENCE']).resolve(strict=True)
if not projection.is_file() or not evidence.is_dir() or not evidence.is_absolute():
    raise SystemExit('private projection and evidence directory required')
if os.name == 'posix' and (stat.S_IMODE(projection.stat().st_mode) & 0o077
                         or stat.S_IMODE(evidence.stat().st_mode) & 0o077):
    raise SystemExit('model projection/evidence permissions must be private')

import run_share_conversation_continuity as fixture
core = fixture.core
report = {'contract':'alive-core-main-followup-probe-v1', 'turns':[],
          'external_delivery_proven':False, 'quality_round_credited':False,
          'semantic_verdict':'pending_original_response_review', 'auxiliary_events':[]}
secret_values = ()


def save():
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if any(value in text for value in secret_values):
        raise RuntimeError('credential disclosure refused in diagnostic report')
    (evidence/'report.json').write_text(text, encoding='utf-8')


def contains_share(value, exact_share):
    if isinstance(value, dict):
        return any(contains_share(item, exact_share) for item in value.values())
    if isinstance(value, list):
        return any(contains_share(item, exact_share) for item in value)
    if not isinstance(value, str):
        return False
    if value == exact_share:
        return True
    # The sidecar is JSON data embedded in the user API content; its text's
    # newlines are escaped. Compare decoded exact content, not a raw substring.
    marker = '{"alive_shares":'
    offset = value.find(marker)
    if offset < 0:
        return False
    try:
        document, _ = json.JSONDecoder().raw_decode(value[offset:])
    except ValueError:
        return False
    return any(item.get('text') == exact_share for item in document.get('alive_shares', []))


async def exercise(*, home, context, runner, scope, source, entry, exact_share, **_):
    global secret_values
    from hermes_cli.config import load_config_readonly
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_cli.fallback_config import get_fallback_chain
    from run_agent import AIAgent
    from hermes_cli.version_info import get_version_info
    projected = json.loads(projection.read_text(encoding='utf-8'))
    keys = list(projected['environment'].values())
    for model_entry in (projected['config']['model'], *projected['config'].get('custom_providers', []),
                        *projected['config'].get('fallback_providers', [])):
        keys.extend(model_entry.get(name) for name in ('api_key','access_token','token'))
    secret_values = tuple(value for value in keys if isinstance(value,str) and len(value)>8)
    settings = json.loads((home/'config.yaml').read_text(encoding='utf-8'))
    settings.update(projected['config'])
    # Only the isolated temporary profile is written. No owner interests, memory,
    # mailbox, route or gateway credentials are copied from production.
    (home/'config.yaml').write_text(json.dumps(settings), encoding='utf-8')
    previous_environment = {key:os.environ.get(key) for key in projected['environment']}
    os.environ.update(projected['environment'])
    observed = []
    def observe(**values):
        observed.append({key:copy.deepcopy(values.get(key)) for key in
            ('session_id','model','provider','api_mode','user_message','request_messages',
             'api_call_count','retry_count','tool_count')})
    context.register_hook('pre_api_request', observe)
    context.register_hook('pre_auxiliary_call', lambda **v: report['auxiliary_events'].append(
        {key:v.get(key) for key in ('aux_task','model','provider')}))
    report['exact_share'] = exact_share
    version = get_version_info()
    report['core_version'] = version.display_version
    report['core_commit'] = version.commit
    report['core_identity_source'] = version.source
    if version.dirty:
        raise RuntimeError('Core supply unexpectedly dirty')
    report['scope_kind'] = 'synthetic Core routing fixture; not consumer installation'
    save()

    def turn(label, question, target_entry, target_source, expected_context):
        variables = core.set_session_vars(platform='telegram', chat_id=target_source.chat_id,
            user_id=target_source.user_id, session_key=target_entry.session_key,
            session_id=target_entry.session_id)
        agent = None
        before = len(observed)
        try:
            config = load_config_readonly()
            model = config['model']
            runtime = resolve_runtime_provider(requested=model.get('provider'), target_model=model['default'])
            agent = AIAgent(model=runtime.get('model') or model['default'],
                provider=runtime['provider'], requested_provider=model.get('provider'),
                base_url=runtime.get('base_url'), api_key=runtime.get('api_key'),
                api_mode=runtime.get('api_mode'), fallback_model=get_fallback_chain(config),
                enabled_toolsets=[], max_iterations=2, max_tokens=2048, run_budget_seconds=480,
                quiet_mode=True, save_trajectories=False, skip_context_files=True,
                load_soul_identity=False, skip_memory=True, skip_background_review=True,
                session_id=target_entry.session_id, gateway_session_key=target_entry.session_key,
                platform='telegram', user_id=target_source.user_id, chat_id=target_source.chat_id,
                chat_type='dm', thread_id=target_source.thread_id, cwd=str(home))
            if agent.tools:
                raise RuntimeError('isolated main turn unexpectedly has tools')
            result = agent.run_conversation(question, conversation_history=[], task_id='public-probe-' + label)
            requests = observed[before:]
            item = {'label':label, 'question':question, 'requested_model':model['default'],
                'requested_provider':model.get('provider'), 'final_model':agent.model,
                'final_provider':agent.provider, 'fallback_activated':bool(agent._fallback_activated),
                'original_final_response':result.get('final_response'),
                'error_present':bool(result.get('error')), 'requests':requests,
                'expected_context_present':expected_context}
            report['turns'].append(item)
            save()
            if not requests:
                raise RuntimeError('actual Core API request observation missing')
            present = [contains_share(r['request_messages'],exact_share) for r in requests]
            if any(r['tool_count'] for r in requests) or any(v != expected_context for v in present):
                raise RuntimeError('actual Core request violated context/tool isolation')
            # Context must ride the admitted user's API content, not a synthetic
            # user turn, system-prompt patch or prefilled assistant transcript.
            for request in requests:
                messages = request['request_messages']
                if expected_context and any(contains_share(m,exact_share)
                                           for m in messages if m.get('role')!='user'):
                    raise RuntimeError('share context appeared outside the user API sidecar')
            if not result.get('final_response') or result.get('error'):
                raise RuntimeError('main turn did not produce a complete original response')
        finally:
            if agent is not None:
                agent.close()
            core.clear_session_vars(variables)

    try:
        await asyncio.to_thread(turn, 'ordinary', '你刚才分享的这个活动能修汽车吗？', entry, source, True)
        await asyncio.to_thread(turn, 'reading-limit', '你已经读过这个活动的完整网页了吗？', entry, source, True)
        other = core.SessionSource(platform=core.Platform.TELEGRAM, chat_id=source.chat_id,
            user_id=source.user_id, thread_id='different-thread', message_id='synthetic-other-thread')
        other_entry = runner.session_store.get_or_create_session(other)
        await asyncio.to_thread(turn, 'foreign-thread', '你刚才分享的那个活动能修汽车吗？', other_entry, other, False)
        report['structural_result'] = 'pass'
        save()
    finally:
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key] = value


try:
    with tempfile.TemporaryDirectory(prefix='alive-real-core-followup-') as directory:
        try:
            asyncio.run(fixture.test(Path(directory)/'profile','success',exercise=exercise))
        finally:
            from hermes_state_registry import close_all_under
            close_all_under(directory)
except BaseException as exc:
    report['structural_result'] = 'failed'
    report['exception_type'] = type(exc).__name__
    save()
    raise
print('HERMES_ALIVE_CORE_MAIN_FOLLOWUP_PROBE_FINISHED')
