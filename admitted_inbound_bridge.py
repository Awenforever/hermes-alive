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


def register_admitted_inbound_hook(ctx):
    ctx.register_hook("post_gateway_admission", on_post_gateway_admission)
