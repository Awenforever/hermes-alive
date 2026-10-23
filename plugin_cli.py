"""Profile-aware installer and status CLI for Hermes Alive."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _home() -> Path:
    from hermes_constants import get_hermes_home

    return get_hermes_home()


def _source() -> Path:
    return Path(__file__).resolve().parent / "skills" / "hermes-alive"


def _hook_target() -> Path:
    return _home() / "hooks" / "hermes-alive"


def _shared_target() -> Path:
    return _home() / "plugin-data" / "hermes-alive" / "runtime"


def register_cli(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="alive_action")
    actions.add_parser("status", help="Show installation and enablement state")
    install=actions.add_parser("install-runtime", help="Install or refresh the profile-scoped gateway hook")
    install.add_argument('--engine',choices=('legacy','kernel-shadow'),default=None)
    kernel=actions.add_parser('kernel-setup',help='Configure non-sending experimental kernel; model consent required')
    owner=kernel.add_mutually_exclusive_group(required=True)
    owner.add_argument('--subject',help='Existing private kernel owner identity')
    owner.add_argument('--user-id',help='Current authorized Hermes user ID; stored only as a local pseudonym')
    kernel.add_argument('--confirm-model-calls',action='store_true')
    kernel.add_argument('--max-cycles',type=int,default=1)
    kernel.add_argument('--interval-seconds',type=float,default=600)
    kernel.add_argument('--model',default=None,help='Optional Hermes model alias; empty inherits Core')
    kernel.add_argument('--public-query',action='append',help='Approved public search text; repeat up to three times')
    kernel.add_argument('--confirm-public-reads',action='store_true',help='Authorize only these public queries and reading their results')
    kernel.add_argument('--confirm-cited-reads',action='store_true',help='Additionally authorize one bounded follow-up of actual public citations')
    setup=actions.add_parser('setup',help='Prepare explicit kernel choices; confirm the target in its authorized conversation (not activated yet)')
    setup.add_argument('--confirm-model-calls',action='store_true')
    setup.add_argument('--confirm-delivery',action='store_true')
    setup.add_argument('--confirm-outbound-retention',action='store_true',help='Separately approve saving shares for conversation continuation')
    setup.add_argument('--retention-days',type=int,default=30,help='Explicitly approved outbound discussion history retention')
    setup.add_argument('--model',default=None,help='Optional Core-configured alias; default inherits Hermes')
    setup.add_argument('--public-query',action='append',default=[])
    setup.add_argument('--confirm-public-reads',action='store_true')
    setup.add_argument('--confirm-cited-reads',action='store_true')
    setup.add_argument('--replace',action='store_true',help='Explicitly replace a prior pending/configured setup; preserves history')
    actions.add_parser("uninstall-runtime", help="Remove owned runtime code while preserving user state")
    actions.add_parser("enable", help="Enable proactive delivery")
    actions.add_parser("disable", help="Disable proactive delivery")
    parser.set_defaults(func=alive_command)


def _install_runtime(engine=None) -> int:
    lifecycle = _source() / "scripts" / "hermes-alive-lifecycle.py"
    result = subprocess.run(
        [sys.executable, str(lifecycle), "install", "--hermes-home", str(_home()),
         *(['--engine',engine] if engine is not None else [])],
        text=True,
        capture_output=True,
        timeout=180,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "lifecycle installation failed").strip()
        print(detail, file=sys.stderr)
        return result.returncode
    manifest_path = _shared_target() / "install" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        print("Hermes Alive lifecycle did not publish a valid manifest", file=sys.stderr)
        return 2
    print(json.dumps({
        "ok": True,
        "hook": str(_hook_target()),
        "source": str(_home() / "skills" / "hermes-alive"),
        "manifest": str(manifest_path),
        "backup_tag": manifest.get("backup_tag"),
        "engine": manifest.get('engine','legacy'),
        "restart_required": True,
    }))
    return 0


def _uninstall_runtime() -> int:
    lifecycle = _source() / "scripts" / "hermes-alive-lifecycle.py"
    result = subprocess.run(
        [sys.executable, str(lifecycle), "uninstall", "--hermes-home", str(_home())],
        text=True,
        capture_output=True,
        timeout=180,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "lifecycle uninstall failed").strip()
        print(detail, file=sys.stderr)
        return result.returncode
    print(json.dumps({
        "ok": True,
        "hook_removed": not _hook_target().exists(),
        "runtime_source_removed": not (_home() / "skills" / "hermes-alive").exists(),
        "user_state_preserved": _shared_target().exists(),
        "restart_required": True,
    }))
    return 0


def _enabled_file() -> Path:
    return _shared_target() / "enabled"


def _config_file() -> Path:
    return _shared_target() / "config" / "hermes-alive.json"


def _control_file() -> Path:
    return _shared_target() / "control.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _read_config() -> dict:
    try:
        value = json.loads(_config_file().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _set_enabled(enabled: bool) -> None:
    from hermes_cli.config import load_config_readonly
    core=load_config_readonly()
    shadow=(((core.get('plugins') or {}).get('entries') or {}).get('hermes-alive') or {}).get('settings',{}).get('kernel_shadow')
    if isinstance(shadow,dict) and shadow.get('consent')=='model_calls_no_delivery':
        from hermes_cli.plugins_state import save_plugin_setting
        save_plugin_setting('hermes-alive',('kernel_shadow',),{**shadow,'enabled':enabled})
    config = _read_config()
    values = config.get("values") if isinstance(config.get("values"), dict) else {}
    values["enabled"] = enabled
    config["values"] = values
    config.setdefault("schema_version", 1)
    _atomic_write(
        _config_file(),
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _atomic_write(_enabled_file(), "true\n" if enabled else "false\n")
    try:
        control = json.loads(_control_file().read_text(encoding="utf-8"))
        if not isinstance(control, dict):
            control = {}
    except Exception:
        control = {}
    control["enabled_override"] = enabled
    control["reason"] = "plugin CLI enable" if enabled else "plugin CLI disable"
    control["updated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _atomic_write(
        _control_file(),
        json.dumps(control, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _effective_enabled() -> bool:
    manifest_path=_shared_target()/'install/manifest.json'
    if manifest_path.is_file():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('engine')=='kernel-shadow':
            from hermes_cli.config import load_config_readonly
            shadow=(((load_config_readonly().get('plugins') or {}).get('entries') or {}).get('hermes-alive') or {}).get('settings',{}).get('kernel_shadow',{})
            return shadow.get('enabled') is True and shadow.get('consent')=='model_calls_no_delivery'
    marker = _enabled_file()
    if marker.is_file():
        try:
            return marker.read_text(encoding="utf-8").strip().lower() in {
                "1", "true", "yes", "on", "enabled",
            }
        except OSError:
            return False
    values = _read_config().get("values")
    return bool(values.get("enabled", False)) if isinstance(values, dict) else False


def alive_command(args: argparse.Namespace) -> int:
    action = getattr(args, "alive_action", None)
    if action == "install-runtime":
        return _install_runtime(getattr(args,'engine',None))
    if action == 'setup':
        if (not args.confirm_model_calls or not args.confirm_delivery or not args.confirm_outbound_retention
                or bool(args.public_query) != args.confirm_public_reads
                or args.confirm_cited_reads and not args.public_query):
            print(json.dumps({'ok':False,'confirmation_required':True,'delivery_enabled':False}))
            return 2
        if _effective_enabled():
            print(json.dumps({'ok':False,'existing_runtime_must_be_paused':True,'delivery_enabled':False}))
            return 2
        from .tool_receipt_bridge import _kernel_module
        module=_kernel_module('kernel_setup')
        from hermes_cli.config import load_config_readonly
        profile_settings=(((load_config_readonly().get('plugins') or {}).get('entries') or {}).get('hermes-alive') or {}).get('settings',{})
        try:
            setup=module.KernelSetupStore(_shared_target()/'kernel',initialize=not bool(profile_settings.get('kernel_setup')))
        except (module.KernelSetupError,RuntimeError):
            print(json.dumps({'ok':False,'configuration_recovery_required':True,
                'delivery_enabled':False,'identity_replaced':False}))
            return 2
        intent,code=setup.stage({'model_calls':True,'delivery':True,
            'outbound_retention_days':args.retention_days,'outbound_retention_confirmed':True,'model':args.model,
            'public_queries':args.public_query,'cited_reads':args.confirm_cited_reads},replace=args.replace)
        from hermes_cli.plugins_state import save_plugin_setting
        save_plugin_setting('hermes-alive',('kernel_setup',),{'pending_intent_id':intent.event.event_id})
        print(json.dumps({'ok':True,'confirmation_command':'/alive confirm '+code,
            'expires_in_seconds':900,'restart_required':True,'delivery_enabled':False,'model_calls_started':False,
            'confirmation_summary':{'model':args.model or 'inherit_hermes','outbound_history_days':args.retention_days,
                'inbound_history':False,'automatic_profile_learning':False,'public_queries':args.public_query,
                'configuration_kept_until_removed':True},
            'phase':'awaiting_authorized_conversation_confirmation'}))
        return 0
    if action == 'kernel-setup':
        if not getattr(args,'confirm_model_calls',False):
            print(json.dumps({'ok':False,'confirmation_required':True,'physical_delivery':False}))
            return 2
        queries=getattr(args,'public_query',None)
        public_consent=getattr(args,'confirm_public_reads',False)
        cited_consent=getattr(args,'confirm_cited_reads',False)
        if bool(queries)!=bool(public_consent) or cited_consent and not (queries and public_consent):
            print(json.dumps({'ok':False,'public_query_confirmation_required':True,'physical_delivery':False}))
            return 2
        from .tool_receipt_bridge import _kernel_module
        assembly=_kernel_module('core_shadow_assembly')
        subject=(assembly.subject_for_user(_home(),args.user_id) if getattr(args,'user_id',None)
                 else getattr(args,'subject',None))
        settings=dict(enabled=True,consent='model_calls_no_delivery',subject=subject,
            max_cycles=args.max_cycles,interval_seconds=args.interval_seconds,model=args.model)
        if queries:
            settings['public_discovery']=dict(consent='approved_public_queries_no_delivery',queries=queries)
            if cited_consent:settings['public_discovery']['follow_citations']=True
        assembly.validate_settings(settings)
        from hermes_cli.plugins_state import save_plugin_setting
        save_plugin_setting('hermes-alive',('kernel_shadow',),settings)
        print(json.dumps({'ok':True,'model_calls_authorized':True,'physical_delivery':False,'restart_required':True}))
        return 0
    if action == "uninstall-runtime":
        return _uninstall_runtime()
    if action == "enable":
        from hermes_cli.config import load_config_readonly
        settings=(((load_config_readonly().get('plugins') or {}).get('entries') or {}).get('hermes-alive') or {}).get('settings',{})
        if settings.get('kernel_setup'):
            print(json.dumps({'ok':False,'enabled':False,'kernel_activation_not_qualified':True,
                'legacy_fallback_allowed':False}))
            return 2
        _set_enabled(True)
        print(json.dumps({"ok": True, "enabled": True, "restart_required": True}))
        return 0
    if action == "disable":
        _set_enabled(False)
        print(json.dumps({"ok": True, "enabled": False, "restart_required": True}))
        return 0
    if action in {None, "status"}:
        from hermes_cli.config import load_config_readonly
        settings=(((load_config_readonly().get('plugins') or {}).get('entries') or {}).get('hermes-alive') or {}).get('settings',{})
        setup_status={}
        if settings.get('kernel_setup'):
            try:
                from .tool_receipt_bridge import _kernel_module
                configured=_kernel_module('kernel_setup').KernelSetupStore(_shared_target()/'kernel').configuration()
                setup_status={'setup_phase':'configured_not_activated' if configured else 'awaiting_confirmation',
                              'delivery_authority_activated':False,'legacy_identity_migrated':False}
            except Exception:
                setup_status={'setup_phase':'recovery_required','delivery_authority_activated':False}
        print(
            json.dumps(
                {
                    "ok": True,
                    "hermes_home": str(_home()),
                    "hook_installed": (_hook_target() / "HOOK.yaml").is_file(),
                    "enabled": _effective_enabled(),
                    "state_root": str(_shared_target()),
                    "live_runtime_verified": False,
                    **setup_status,
                },
                indent=2,
            )
        )
        return 0
    print(f"Unknown action: {action}")
    return 2
