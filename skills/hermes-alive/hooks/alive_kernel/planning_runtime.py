"""Recoverable discovery-to-intent runtime; never transport or action authority.

The host supplies the current policy, model capability and authority on every
entry. Started but uncompleted provider operations are not repeated implicitly.
"""
from dataclasses import dataclass
import re

from .cognition_cycle import CognitionCycleCoordinator
from .deliberation import ActionAuthority, PolicyContext
from .event_store import EventConflictError
from .events import EventEnvelope, Sensitivity, _thaw_json
from .opportunity_synthesis import OpportunitySynthesizer


class PlanningRuntimeError(ValueError):
    """A cycle cannot be recovered as the same current intent."""


@dataclass(frozen=True, slots=True)
class PlanningRuntimeResult:
    operation_id: str
    interpretation_event_id: str
    frame_event_id: str
    selection_event_id: str
    action_kind: str
    selected_by: str


class PlanningRuntime:
    """Compose retained opportunities and model selection without sending.

This is the planning part of the autonomous runtime, not a replacement legacy
watcher and not a complete production loop. It creates no channel queues.
"""

    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.synth = OpportunitySynthesizer(journal, content_vault=content_vault,
                                           context_vault=context_vault)
        self.coordinator = CognitionCycleCoordinator(journal,
            content_vault=self.synth.vault, context_vault=context_vault)

    async def run(self, *, operation_id, subject, policy_context: PolicyContext,
                  call, requested_model=None, authority=ActionAuthority.NONE,
                  sensitivity=Sensitivity.PRIVATE):
        if not isinstance(operation_id, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}', operation_id):
            raise PlanningRuntimeError('invalid planning operation')
        if not isinstance(subject, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}', subject):
            raise PlanningRuntimeError('invalid planning owner')
        if not isinstance(policy_context, PolicyContext) or type(policy_context.can_interrupt) is not bool:
            raise PlanningRuntimeError('invalid current host policy')
        if requested_model is not None and (not isinstance(requested_model, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', requested_model)):
            raise PlanningRuntimeError('invalid requested model')
        authority, sensitivity = ActionAuthority(authority), Sensitivity(sensitivity)
        binding = {'subject': subject, 'authority': authority.value,
            'sensitivity': sensitivity.value, 'requested_model': requested_model,
            'policy': {'can_interrupt': policy_context.can_interrupt,
                'minimum_confidence': policy_context.minimum_confidence,
                'maximum_risk': policy_context.maximum_risk,
                'allowed_side_effects': sorted(x.value for x in policy_context.allowed_side_effects)}}
        digest = self.synth.vault.digest_json({'operation': operation_id, 'subject': subject})[:40]
        start_id = 'planning.runtime:' + digest + ':started'
        prior = self.journal.get(start_id)
        if prior is None:
            event = EventEnvelope(event_id=start_id, event_type='planning.runtime_started',
                source='alive.planning-runtime', actor='system:alive-runtime',
                subject=subject, sensitivity=sensitivity, payload=binding)
            try:
                self.journal.append(event)
            except EventConflictError:
                # Concurrent entry must validate the canonical winner below.
                pass
            prior = self.journal.get(start_id)
        if (prior is None or prior.event.source != 'alive.planning-runtime'
                or prior.event.actor != 'system:alive-runtime'
                or prior.event.event_type != 'planning.runtime_started'
                or prior.event.subject != subject or prior.event.sensitivity is not sensitivity
                or self.synth.vault.digest_json(_thaw_json(prior.event.payload)) != self.synth.vault.digest_json(binding)):
            raise PlanningRuntimeError('planning operation reused with different host scope or policy')
        interpret_id = 'runtime-interpret:' + digest
        cycle_id = 'runtime-cycle:' + digest
        select_id = 'runtime-select:' + digest
        if self.journal.get('opportunity.synthesis:' + interpret_id + ':started') is not None:
            generated = self.synth.load_completed(subject=subject, operation_id=interpret_id,
                authority=authority, clearance=sensitivity)
        else:
            generated = await self.synth.run(subject=subject, operation_id=interpret_id,
                call=call, requested_model=requested_model, authority=authority, clearance=sensitivity)
        params = dict(cycle_id=cycle_id, subject=subject, candidates=generated.candidates,
            policy_context=policy_context, sensitivity=sensitivity,
            causation_id=generated.receipt_event_id)
        prepared = self.coordinator.prepare(**params)
        silence_only = prepared.gate.admissible_ids == (prepared.frame.silence_id,)
        if silence_only:
            expected = 'deliberation.selection:' + self.coordinator._identifier('cycle-selection', cycle_id)
        else:
            expected = 'deliberation.selection:model-selection:' + self.synth.vault.digest_json(
                {'operation_id': select_id, 'frame_id': prepared.frame.frame_id})[:40]
        existing = self.journal.get(expected)
        if existing is None:
            planned = await self.coordinator.plan_with_model(call=call, requested_model=requested_model,
                operation_id=select_id, **params)
            if planned.selection_event_id != expected:
                raise PlanningRuntimeError('unexpected planning selection identity')
        # Validate retained advice/context again after the selection provider wait.
        # A completion receipt never overrides withdrawal or authorizes delivery.
        self.synth.load_completed(subject=subject, operation_id=interpret_id,
            authority=authority, clearance=sensitivity)
        self.coordinator.deliberation.project_new()
        if self.coordinator.deliberation.latest_selection_event_id(prepared.frame.frame_id) != expected:
            raise PlanningRuntimeError('planning selection was superseded')
        stored = self.coordinator.deliberation.inspect(prepared.frame.frame_id, clearance=sensitivity)
        if stored is None or stored.selection is None or stored.selection_outcome != 'validated':
            raise PlanningRuntimeError('current planning selection is unavailable')
        return PlanningRuntimeResult(operation_id, generated.receipt_event_id,
            prepared.frame_event_id, expected, stored.selection.candidate.action_kind.value,
            stored.selection.selected_by)
