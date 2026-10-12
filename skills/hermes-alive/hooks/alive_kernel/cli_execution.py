"""Single-start orchestration for an operator-qualified CLI transport.

No transport is installed by this module. The launcher and host callbacks are
trusted operator capabilities, not model-selected code or authorization proof.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .cli_send_contract import compile_text_cli_plan
from .dispatch_outbox import DispatchExecution, DispatchLease, DispatchOutbox
from .event_store import JournalRecord
from .events import Sensitivity


@dataclass(frozen=True, slots=True)
class CliExecutionObservation:
    execution: DispatchExecution = field(repr=False)
    observation: JournalRecord = field(repr=False)


def execute_text_cli_once(
    outbox: DispatchOutbox, lease: DispatchLease, *, clearance: Sensitivity,
    profile_id: str, hermes_home: Path, resolve_target: Callable,
    extract_media: Callable, observe_profile_home: Callable, launch: Callable,
    clock: Callable = lambda: datetime.now(timezone.utc),
) -> CliExecutionObservation:
    """Consume a start once, compile, recheck, launch once, observe only.

    Exceptions deliberately escape without releasing/retrying the consumed
    start. A launcher error or observation-write failure may follow an external
    effect. Qualified runtime checks must occur inside the trusted launcher;
    neither this bridge nor a caller-supplied clock qualifies a runtime.
    """
    execution = outbox.begin_execution(lease, clearance=clearance, now=clock())
    plan = compile_text_cli_plan(
        execution.content, execution.route, profile_id=profile_id,
        hermes_home=hermes_home, resolve_target=resolve_target,
        extract_media=extract_media, observe_profile_home=observe_profile_home)
    outbox.validate_execution_for_launch(execution, now=clock())
    stdout, exit_code = launch(plan)
    record = outbox.record_cli_observation(
        execution, stdout=stdout, exit_code=exit_code, now=clock())
    return CliExecutionObservation(execution, record)
