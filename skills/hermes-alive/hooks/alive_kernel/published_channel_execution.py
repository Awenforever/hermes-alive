"""Prepared, single-start text submission through a qualified host publisher.

The host owns deferred queue lifetime. This seam neither drains it nor retries;
the returned result is opaque and publication never becomes user-delivery proof.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .cli_send_contract import compile_text_cli_plan
from .transport_publisher_bridge import TransportPublisherBridge


@dataclass(frozen=True, slots=True)
class PublishedChannelExecution:
    execution: object = field(repr=False)
    adapter_result: object = field(repr=False)
    binding_event_id: str
    observations: object = field(default=None, repr=False)
    publication_error_class: str | None = None
    external_delivery_proven: bool = False


async def execute_published_text_once(outbox, lease, *, publisher, clearance,
        profile_id, hermes_home, resolve_target, extract_media, observe_profile_home,
        clock=lambda: datetime.now(timezone.utc)):
    # Validate source and profile before consuming the one-use start.
    publisher.validate({'platform':'weixin','profile':profile_id})
    if (publisher.profile_home.resolve() != Path(hermes_home).resolve()
            or Path(observe_profile_home()).resolve() != publisher.profile_home.resolve()):
        raise ValueError('publisher callbacks differ from qualified profile')
    execution = outbox.begin_execution(lease, clearance=clearance, now=clock())
    plan = compile_text_cli_plan(execution.content, execution.route,
        profile_id=profile_id, hermes_home=hermes_home, resolve_target=resolve_target,
        extract_media=extract_media, observe_profile_home=observe_profile_home)
    bridge = TransportPublisherBridge(outbox)
    binding = bridge.bind(execution, publisher, now=clock())
    metadata = {'_hermes_transport_binding_v1':binding.event.payload['transport_binding']}
    if execution.route['thread_id'] is not None:
        metadata['thread_id'] = execution.route['thread_id']
    observations, error = None, None
    try:
        # Binding records provenance but does not replace fresh launch authority.
        outbox.validate_execution_for_launch(execution, now=clock())
        result = await publisher.adapter.send(chat_id=execution.route['chat_id'],
            content=plan.stdin_text, metadata=metadata)
    finally:
        try:
            observations = bridge.ingest(binding.event.event_id, publisher=publisher,
                route=execution.route, now=clock())
        except Exception as exc:
            error = type(exc).__name__  # no private body/error details or retry
    return PublishedChannelExecution(execution,result,binding.event.event_id,observations,error)
