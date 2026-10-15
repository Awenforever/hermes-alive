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
    grounding_reviews: tuple = ()
    repair_interpretation_event_id: str | None = None
    repair_disposition: str | None = None


class PlanningRuntime:
    """Compose retained opportunities and model selection without sending.

This is the planning part of the autonomous runtime, not a replacement legacy
watcher and not a complete production loop. It creates no channel queues.
"""

    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.context_vault = context_vault
        self.synth = OpportunitySynthesizer(journal, content_vault=content_vault,
                                           context_vault=context_vault)
        self.coordinator = CognitionCycleCoordinator(journal,
            content_vault=self.synth.vault, context_vault=context_vault)

    async def _ground_candidates(self, generated, *, subject, interpretation_id,
            call, reviewer_model, sensitivity, resolve_domain, require_independence):
        from .source_support import SourceSupportReviewer
        reviewer = SourceSupportReviewer(self.journal, content_vault=self.synth.vault,
                                         context_vault=self.context_vault)
        eligible, reviews, failures = [], [], 0
        for candidate in generated.candidates:
            candidate_id = candidate.action.candidate_id
            key = 'planning-ground:' + self.synth.vault.digest_json({
                'interpretation':interpretation_id, 'candidate':candidate_id})[:40]
            prefix = 'opportunity.source-support:' + key
            event_id = prefix + ':completed'
            if self.journal.get(prefix + ':started') is None:
                try:
                    await reviewer.run(subject=subject, interpretation_id=interpretation_id,
                        candidate_id=candidate_id, operation_id=key, call=call,
                        reviewer_model=reviewer_model, clearance=sensitivity,
                        resolve_domain=resolve_domain, require_independence=require_independence,
                        protocol_recovery=True)
                except Exception:
                    # Isolate one provider/proposal failure, never retry it implicitly.
                    pass
            findings = reviewer.verify_current(event_id, subject=subject,
                interpretation_id=interpretation_id, candidate_id=candidate_id,
                clearance=sensitivity, allow_correlated=not require_independence)
            record = self.journal.get(event_id)
            if findings is not None and record is not None:
                payload = record.event.payload
                if (resolve_domain(payload['generator_model']) != payload['generator_domain']
                        or resolve_domain(payload['reviewer_model']) != payload['reviewer_domain']
                        or payload.get('require_independence', True) is not require_independence):
                    findings = None
            if findings is None:
                failures += 1
                evidence_id = next((e for e in (prefix + ':failed', prefix + ':started')
                    if self.journal.get(e) is not None), generated.receipt_event_id)
                reviews.append((candidate_id, 'review_unavailable', evidence_id))
                continue
            reviews.append((candidate_id, findings['verdict'], event_id))
            if findings['verdict'] == 'supported':
                eligible.append(candidate)
        return tuple(eligible), tuple(reviews), failures

    async def run(self, *, operation_id, subject, policy_context: PolicyContext,
                  call, requested_model=None, authority=ActionAuthority.NONE,
                  sensitivity=Sensitivity.PRIVATE, grounding=False,
                  grounding_model=None, resolve_grounding_domain=None,
                  require_independent_grounding=False):
        if type(grounding) is not bool or type(require_independent_grounding) is not bool:
            raise PlanningRuntimeError('invalid grounding mode')
        if grounding_model is not None and (not isinstance(grounding_model, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', grounding_model)):
            raise PlanningRuntimeError('invalid grounding model')
        if resolve_grounding_domain is not None and not callable(resolve_grounding_domain):
            raise PlanningRuntimeError('invalid grounding domain resolver')
        if require_independent_grounding and resolve_grounding_domain is None:
            raise PlanningRuntimeError('independent grounding requires a trusted domain resolver')
        if not grounding and (grounding_model is not None or resolve_grounding_domain is not None
                              or require_independent_grounding):
            raise PlanningRuntimeError('grounding options require explicit grounding mode')
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
        if grounding:
            binding['grounding'] = {'model':grounding_model,
                'require_independence':require_independent_grounding, 'method':'source-support-v1'}
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
        candidates, reviews, repair, repair_disposition = generated.candidates, (), None, None
        repair_id = 'runtime-repair:' + digest
        if grounding:
            review_parameters = dict(subject=subject, call=call,
                reviewer_model=grounding_model or requested_model, sensitivity=sensitivity,
                resolve_domain=resolve_grounding_domain or (lambda model:'unqualified-family'),
                require_independence=require_independent_grounding)
            candidates, reviews, failures = await self._ground_candidates(generated,
                interpretation_id=interpret_id, **review_parameters)
            rejected = tuple(event for _, verdict, event in reviews if verdict in ('unsupported', 'uncertain'))
            if rejected:
                targets = {c.action.agenda_item_id for c in generated.candidates if any(
                    cid == c.action.candidate_id and verdict in ('unsupported', 'uncertain')
                    for cid, verdict, _ in reviews)}
                try:
                    if self.journal.get('opportunity.synthesis:' + repair_id + ':started') is not None:
                        repair = self.synth.load_completed(subject=subject, operation_id=repair_id,
                            authority=authority, clearance=sensitivity)
                    else:
                        repair = await self.synth.run(subject=subject, operation_id=repair_id,
                            call=call, requested_model=requested_model, authority=authority,
                            clearance=sensitivity, revision_event_ids=rejected)
                    # A repair can address rejected intents, not expand the host's work scope.
                    from dataclasses import replace
                    repaired = replace(repair, candidates=tuple(c for c in repair.candidates
                        if c.action.agenda_item_id in targets))
                    replacements, repair_reviews, repair_failures = await self._ground_candidates(
                        repaired, interpretation_id=repair_id, **review_parameters)
                    candidates += replacements
                    reviews += repair_reviews
                    failures += repair_failures
                    repair_disposition = 'review_unavailable' if repair_failures else 'completed'
                except Exception:
                    if not candidates:
                        raise PlanningRuntimeError('corrective planning unresolved; no implicit retry') from None
                    failures += 1  # Preserve separately grounded candidates.
                    repair_disposition = 'unavailable'
            if failures and not candidates:
                raise PlanningRuntimeError('no grounded candidate; unresolved review is not qualified silence')
        params = dict(cycle_id=cycle_id, subject=subject, candidates=candidates,
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
        if grounding:
            from .source_support import SourceSupportReviewer
            verifier = SourceSupportReviewer(self.journal, content_vault=self.synth.vault,
                                             context_vault=self.context_vault)
            if repair is not None:
                self.synth.load_completed(subject=subject, operation_id=repair_id,
                    authority=authority, clearance=sensitivity)
            for cid, verdict, event_id in reviews:
                if verdict == 'review_unavailable':
                    continue
                record = self.journal.get(event_id)
                start = self.journal.get(record.event.causation_id)
                origin = start.event.causation_id.removeprefix('opportunity.synthesis:').removesuffix(':completed')
                current = verifier.verify_current(event_id, subject=subject,
                    interpretation_id=origin, candidate_id=cid, clearance=sensitivity,
                    allow_correlated=not require_independent_grounding)
                resolver = resolve_grounding_domain or (lambda model:'unqualified-family')
                payload = record.event.payload
                if (current is None or current['verdict'] != verdict
                        or resolver(payload['generator_model']) != payload['generator_domain']
                        or resolver(payload['reviewer_model']) != payload['reviewer_domain']):
                    raise PlanningRuntimeError('grounding evidence changed during selection')
        self.coordinator.deliberation.project_new()
        if self.coordinator.deliberation.latest_selection_event_id(prepared.frame.frame_id) != expected:
            raise PlanningRuntimeError('planning selection was superseded')
        stored = self.coordinator.deliberation.inspect(prepared.frame.frame_id, clearance=sensitivity)
        if stored is None or stored.selection is None or stored.selection_outcome != 'validated':
            raise PlanningRuntimeError('current planning selection is unavailable')
        return PlanningRuntimeResult(operation_id, generated.receipt_event_id,
            prepared.frame_event_id, expected, stored.selection.candidate.action_kind.value,
            stored.selection.selected_by, reviews, repair.receipt_event_id if repair is not None else None,
            repair_disposition)
