"""Profile-scoped explicit deactivation; ordinary reload does not retire work."""
import asyncio
import logging

logger=logging.getLogger(__name__)


def _store(binding):
    root=binding.home/'plugin-data/hermes-alive/runtime/kernel'
    if not (root/'experience.sqlite3').is_file():return None
    if not all((root/name).is_file() for name in ('identity.key','content-vault/content.key','content-vault/content.sqlite3')):
        raise ValueError('existing kernel identity must be recovered before retiring work')
    from .tool_receipt_bridge import _kernel_module
    return _kernel_module('kernel_setup').KernelSetupStore(root)


def _controller(store):
    from importlib import import_module
    module=import_module(store.__class__.__module__.rsplit('.',1)[0]+'.core_work_retirement')
    return module.CoreWorkRetirement(store)


def _authority(store,*,cause,evidence):
    return {'kind':'operator_plugin_deactivation','cause':cause,
        'evidence_fingerprint':store.protector.authenticate_json('alive.core-work.deactivation.v1',evidence),
        'not_a_fabricated_owner_turn':True}


async def retire_current_owner(binding,scope):
    """Explicit paired-owner pause, not startup failure or ordinary upgrade."""
    from .kernel_execution_bridge import configured_owner
    store,configured=configured_owner(binding,scope)
    authority=_authority(store,cause='current_owner_pause',evidence=scope.binding_document())
    def validate():
        binding._require_home()
        current,current_owner=configured_owner(binding,scope)
        if current.root!=store.root or current_owner!=configured:
            raise ValueError('current configured owner changed')
    control=_controller(store)
    prepared=control.prepare(authority=authority,validate=validate,subject=configured.subject)
    result=await control.settle(prepared,validate=validate)
    binding._core_retirement_status=result
    return result


def retire_operator_profile(home):
    """Explicit profile CLI disable; no invented conversation principal."""
    from pathlib import Path
    from types import SimpleNamespace
    from hermes_constants import get_hermes_home
    home=Path(home).resolve()
    def validate():
        if Path(get_hermes_home()).resolve()!=home:raise ValueError('Hermes profile changed')
    validate();store=_store(SimpleNamespace(home=home))
    if store is None:return None
    authority=_authority(store,cause='operator_cli_disable',evidence={'profile':str(home)})
    control=_controller(store)
    prepared=control.prepare(authority=authority,validate=validate)
    return asyncio.run(control.settle(prepared,validate=validate))


def retire_if_deselected(binding):
    """Synchronous unload hook; only a positively deselected plugin retires jobs.

    The one-off async tail only requests cancellation from Core. It is not a
    work executor and has no retry loop; durable intents precede that request.
    """
    store=_store(binding)
    if store is None:return None
    from pm.plugins_state import read_home_selection
    from hermes_cli.plugins_manifest import manifest_key
    from hermes_cli.left_core_migration import legacy_plugin_keys
    selection=read_home_selection(binding.home)
    if selection is None:return None
    manifest=binding.context.manifest;key=manifest_key(manifest)
    names={key,manifest.name,*legacy_plugin_keys(key)}
    plugins=selection.get('plugins') or {};disabled=plugins.get('disabled') or []
    enabled=plugins.get('enabled')
    if not (names.intersection(disabled) or isinstance(enabled,list) and not names.intersection(enabled)):
        return None
    authority=_authority(store,cause='core_plugin_deselected',evidence={
        'plugin':key,'disabled':sorted(disabled),'enabled':sorted(enabled) if isinstance(enabled,list) else None})
    control=_controller(store)
    def validate():
        binding._require_home()
        if store.root.resolve()!=(binding.home/'plugin-data/hermes-alive/runtime/kernel').resolve():
            raise ValueError('retirement profile changed')
    prepared=control.prepare(authority=authority,validate=validate)
    summary=control.summary(prepared)
    if not summary['pending_core_stop_requests']:return summary
    try:loop=asyncio.get_running_loop()
    except RuntimeError:return asyncio.run(control.settle(prepared,validate=validate))
    # Cleanup must outlive the registrations being unloaded. Holding the task on
    # this binding prevents losing it; Core's RPC owns the actual cancellation.
    task=loop.create_task(control.settle(prepared,validate=validate),name='alive:retire-owned-core-work')
    binding._core_retirement_task=task
    def observed(done):
        try:binding._core_retirement_status=done.result()
        except asyncio.CancelledError:
            binding._core_retirement_status={**summary,'status':'stop_outcome_unknown','needs_attention':True}
        except Exception as error:
            binding._core_retirement_status={**summary,'status':'stop_outcome_unknown','needs_attention':True,
                'error_class':type(error).__name__}
        if binding._core_retirement_status.get('needs_attention'):
            logger.warning('Alive deactivation has unresolved Core work; inspect retained Core job state')
    task.add_done_callback(observed)
    return summary
