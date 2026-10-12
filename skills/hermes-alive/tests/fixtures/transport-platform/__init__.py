"""Public platform-plugin fixture. Records only synthetic local deliveries."""
import json

from hermes_constants import get_hermes_home


async def send(config, chat_id, message, *, thread_id=None, **kwargs):
    if chat_id != "fixture-chat":
        return {"error": "fixture refuses a non-test route"}
    mode = config.extra.get("mode", "success")
    if mode == "reject":
        return {"error": "synthetic transport refusal"}
    receipt = {"chat_id": chat_id, "message": message, "thread_id": thread_id,
               "effect": "partial" if mode == "partial" else "complete"}
    with (get_hermes_home() / "fixture-deliveries.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt) + "\n")
    if mode == "partial":
        return {"success": False, "partial_success": True, "error": "synthetic partial effect"}
    return {"success": True, "message_id": "fixture-local-receipt"}


def register(ctx):
    def no_gateway(config):
        raise AssertionError("fixture must not launch a gateway")
    ctx.register_platform(
        "alivefixture", "Local test sink", no_gateway, lambda: True,
        standalone_sender_fn=send,
        parse_target_ref_fn=lambda ref: (ref, None),
    )
