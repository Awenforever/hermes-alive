"""Single-start qualified adapter execution with closed trace publication.

Research runtime seam, not registered in production. No platform queue, retry,
receipt promotion or user-feedback inference. Operator callbacks must be bound
to this exact profile/adapter; current shared FIFO-worker tracing is unqualified.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .chunk_observation import OwnedChunkObserver
from .cli_send_contract import compile_text_cli_plan


@dataclass(frozen=True, slots=True)
class ObservedChannelExecution:
    execution: object = field(repr=False)
    adapter_result: object = field(repr=False)
    observation: object = field(default=None, repr=False)
    publication_error_class: str | None = None
    external_delivery_proven: bool = False


async def execute_observed_text_once(outbox, lease, *, adapter, clearance,
        profile_id, hermes_home, resolve_target, extract_media, observe_profile_home,
        qualified=False, clock=lambda: datetime.now(timezone.utc)):
    """Delegate exact text once; trace failure never retries an external action.

    Normal SDK result objects are returned unchanged, even false/partial results.
    Original exceptions/cancellation escape after best-effort closed publication.
    Publication is synchronous and bounded by the existing journal/SQLite gate;
    event-loop performance and asynchronous writer shutdown remain unqualified.
    """
    if qualified is not True or not callable(getattr(adapter, '_send_text_chunk', None)):
        raise ValueError('qualified adapter observation seam required')
    execution = outbox.begin_execution(lease, clearance=clearance, now=clock())
    plan = compile_text_cli_plan(execution.content, execution.route,
        profile_id=profile_id, hermes_home=hermes_home, resolve_target=resolve_target,
        extract_media=extract_media, observe_profile_home=observe_profile_home)
    observer = OwnedChunkObserver(adapter, protector=outbox.protector, subject=lease.subject,
        route=dict(execution.route), qualified=True, attempt_event_id='action.attempt:' + lease.attempt_id,
        start_event_id=execution.start_event_id)
    observation, publication_error = None, None
    try:
        async with observer:
            outbox.validate_execution_for_launch(execution, now=clock())
            metadata = {'thread_id': execution.route['thread_id']} if execution.route['thread_id'] else None
            result = await adapter.send(chat_id=execution.route['chat_id'], content=plan.stdin_text,
                                        metadata=metadata)
    finally:
        if observer._closed and observer._entered:
            try:
                observation = outbox.record_chunk_observation(execution, observer, now=clock())
            except Exception as exc:
                # Never log untrusted/private error details or turn observation
                # failure into another send. Original send exceptions still win.
                publication_error = type(exc).__name__
    return ObservedChannelExecution(execution, result, observation, publication_error)
