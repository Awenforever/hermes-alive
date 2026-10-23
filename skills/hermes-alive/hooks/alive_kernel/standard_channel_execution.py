"""One authorized text submission to a host-resolved standard Hermes adapter.

No chunk hooks, Enhance dependency, physical queue, transport retry or delivery
claim. The resolver is a trusted host capability, never model-supplied routing.
It must use the host's canonical receiving-bot/profile route and fail closed.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import inspect
from collections.abc import Mapping
from types import MappingProxyType
from pathlib import Path

from .cli_send_contract import compile_text_cli_plan
from .published_channel_execution import _renderer_metadata


@dataclass(frozen=True, slots=True)
class StandardChannelExecution:
    execution: object = field(repr=False)
    adapter_result: object = field(repr=False)
    observation: object = field(repr=False)
    external_delivery_proven: bool = False


async def execute_standard_text_once(outbox, lease, *, resolve_channel, clearance,
        profile_id, hermes_home, resolve_target, extract_media, observe_profile_home,
        clock=lambda: datetime.now(timezone.utc)):
    """Consume a start, validate the exact body/route, submit once, observe return.

    Resolver callbacks must be synchronous and bound to the current Core profile
    and Gateway loop. A missing/disconnected/foreign transport is a refusal, not
    a default-bot/standalone fallback. Any failure after the durable start remains
    consumed; cancellation, a false result or journal failure never retry a send.
    An opaque normal return is retained as an observation, not acknowledged as
    external delivery. A physical publisher can supply stronger evidence through
    its separately qualified optional integration, never through this result.
    """
    if not callable(resolve_channel):
        raise ValueError('current canonical host channel resolver required')
    execution = outbox.begin_execution(lease, clearance=clearance, now=clock())
    plan = compile_text_cli_plan(execution.content, execution.route,
        profile_id=profile_id, hermes_home=hermes_home, resolve_target=resolve_target,
        extract_media=extract_media, observe_profile_home=observe_profile_home)
    resolved = resolve_channel(MappingProxyType(dict(execution.route)))
    if inspect.isawaitable(resolved):
        if inspect.iscoroutine(resolved):
            resolved.close()
        raise ValueError('canonical channel resolution must not suspend launch authority')
    if (not isinstance(resolved, tuple) or len(resolved) != 2
            or not isinstance(resolved[1], Mapping)):
        raise ValueError('canonical channel must supply adapter and host routing metadata')
    adapter, host_metadata = resolved
    if (adapter is None or getattr(adapter, 'is_connected', False) is not True
            or not callable(getattr(adapter, 'send', None))):
        raise ValueError('canonical connected adapter unavailable; no transport fallback')
    platform = getattr(adapter, 'platform', None)
    if getattr(platform, 'value', platform) != execution.route['platform']:
        raise ValueError('canonical adapter belongs to a different platform')
    launch_time = clock()
    # Thread/workspace/receiving-profile metadata comes from Core's canonical
    # route resolver. Do not invent a third resolver or discard new host fields.
    metadata = dict(host_metadata)
    if any(key in metadata for key in ('model_name', '_hermes_transport_binding_v1')):
        raise ValueError('routing metadata cannot override renderer/transport provenance')
    if metadata.get('thread_id') not in (None, execution.route['thread_id']):
        raise ValueError('host thread differs from the authorized route')
    metadata['_interim_send'] = True
    if execution.route['thread_id'] is not None:
        metadata['thread_id'] = execution.route['thread_id']
    metadata.update(_renderer_metadata(outbox, execution, plan.stdin_text, launch_time))
    # No intervening await: authority and body are checked immediately before
    # entering the platform's own coroutine. The platform owns its IO lifetime.
    if Path(observe_profile_home()).resolve() != plan.hermes_home:
        raise ValueError('canonical channel resolution changed the owning profile')
    outbox.validate_execution_for_launch(execution, now=clock())
    result = await adapter.send(chat_id=execution.route['chat_id'], content=plan.stdin_text,
                                metadata=metadata)
    observation = outbox.record_adapter_observation(execution, result=result, now=clock())
    return StandardChannelExecution(execution, result, observation)
