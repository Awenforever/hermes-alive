"""Explicit Core-scoped continuity attachment; no sending or model invocation.

The trusted live assembly supplies a store and the actual Core session router.
Merely installing this module does not enable retention or activate the kernel.
"""
from pathlib import Path


def _context_budget(store):
    """Respect Core's resolved per-hook cap without writing its configuration."""
    from hermes_cli.config import load_config_readonly
    from tools.hook_output_spill import DEFAULT_ENABLED, DEFAULT_MAX_CHARS
    from tools.tool_output_limits import _coerce_positive_int
    config = load_config_readonly() or {}
    hooks = config.get('hooks') if isinstance(config, dict) else None
    section = hooks.get('output_spill') if isinstance(hooks, dict) else None
    section = section if isinstance(section, dict) else {}
    enabled = section.get('enabled', DEFAULT_ENABLED)
    enabled = bool(enabled) if enabled is not None else DEFAULT_ENABLED
    return min(store.MAX_CONTEXT, _coerce_positive_int(section.get('max_chars'), DEFAULT_MAX_CHARS)) if enabled else store.MAX_CONTEXT


class CoreShareContinuity:
    def __init__(self, store, router, *, clearance):
        self.store, self.router, self.clearance = store, router, clearance
        self._closed = False
        expected = Path(router.home) / 'plugin-data/hermes-alive/runtime/kernel'
        if Path(store.journal.path).resolve().parent != expected.resolve():
            raise ValueError('continuity store belongs to another Core profile')

    def close(self):
        self._closed = True

    def for_target(self, scope):
        """Bind a trusted target, not a user/model-selected scope document."""
        if self._closed:
            raise ValueError('conversation continuity retired')
        current = self.router.for_turn(session_key=scope.session_key,
            session_id=scope.session_id, user_id=scope.user_id, platform=scope.platform)
        if current != scope:
            raise ValueError('conversation target changed')
        return _TargetContinuity(self, scope)

    def context(self, **values):
        if self._closed:
            return None
        scope = self.router.scope_for_hook(values)
        if scope is None:
            return None
        shares = self.store.read(scope=scope.binding_document(), clearance=self.clearance)
        # Use this exact embedded build, never import an unrelated installed one.
        from importlib import import_module
        module = import_module(self.store.__class__.__module__)
        text = module.continuation_context(shares, max_chars=_context_budget(self.store))
        if shares and not text:
            import logging
            logging.getLogger(__name__).warning('Alive conversation reference cannot fit the active Core hook budget')
        return {'context': text} if text else None


class _TargetContinuity:
    def __init__(self, bridge, scope):
        self.bridge, self.scope = bridge, scope

    def prepare(self, execution, *, clearance, now):
        if self.bridge._closed or clearance != self.bridge.clearance:
            raise ValueError('current conversation continuity clearance required')
        # Recheck the canonical receiving adapter, scope and Gateway loop now.
        self.bridge.router.resolve_channel(self.scope, execution.route)
        return self.bridge.store.prepare(execution, scope=self.scope.binding_document(),
                                         clearance=clearance, now=now)
