"""Non-consuming observer at Hermes' authorized native ingress boundary."""
import logging

from .tool_receipt_bridge import _kernel_module, _shadow_enabled, _shared_dir

logger = logging.getLogger(__name__)


def on_post_gateway_admission(**values):
    if not _shadow_enabled():
        return None
    try:
        _kernel_module("admitted_inbound").record_admitted_inbound(_shared_dir(), values)
    except Exception as exc:
        # Do not log private payloads or provider/exception messages.
        logger.warning("Hermes Alive admitted input was not recorded: %s", type(exc).__name__)
    # A receipt, failure or consent decision never claims the message.
    return None


def register_admitted_inbound_hook(ctx, binding=None):
    if binding is None:
        ctx.register_hook("post_gateway_admission", on_post_gateway_admission)
        return
    def observe(**values):
        if binding.closed:return None
        try:
            from .kernel_execution_bridge import runtime_engine
            if runtime_engine(binding)!='kernel':return on_post_gateway_admission(**values)
            binding._require_home()
            from .kernel_setup_bridge import setup_store
            store=setup_store(binding)
            configured=store.configuration()
            if configured is None or store.activation() is None:return None
            # Resolve the current Core route on the ingress caller's Gateway
            # loop. No source field or arbitrary user text can select a profile.
            source=values.get('source')
            if not isinstance(source,dict) or values.get('platform')!=configured.scope['platform']:
                return None
            if values.get('session_key')!=configured.scope['session_key']:return None
            for name in ('chat_id','user_id','chat_type','thread_id','scope_id','guild_id','parent_chat_id'):
                if (source.get(name) or '')!=configured.scope[name]:return None
            router=binding.session_router(configured.scope['platform'])
            scope=router.capture_target(session_key=values.get('session_key'),
                user_id=source.get('user_id'),platform=values.get('platform'))
            actual=scope.binding_document();saved=dict(configured.scope)
            actual.pop('session_id');saved.pop('session_id')
            if actual!=saved:return None
            for name in ('chat_id','user_id','chat_type','thread_id','scope_id','guild_id','parent_chat_id'):
                if (source.get(name) or '')!=getattr(scope,name):return None
            _kernel_module('admitted_inbound').record_configured_input(
                store,configured,scope.binding_document(),values)
        except Exception as exc:
            logger.warning('Hermes Alive configured input was not recorded: %s',type(exc).__name__)
        # Observe only. Enhance and independent consumers keep their own ingress
        # behavior; Alive never returns handled, rewrites text or dispatches IO.
        return None
    ctx.register_hook('post_gateway_admission',observe)
