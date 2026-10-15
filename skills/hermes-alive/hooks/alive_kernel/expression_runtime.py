"""Compose current planning with retained natural expression; never send."""
from dataclasses import dataclass
import re

from .event_store import EventConflictError
from .events import EventEnvelope, _thaw_json
from .opportunity_expression import OpportunityExpressionStore
from .planning_runtime import PlanningRuntime, PlanningRuntimeResult
from .semantic_comparator import SemanticComparator


class ExpressionRuntimeError(ValueError):
    """Expression recovery is incomplete, stale or outside the current intent."""


@dataclass(frozen=True, slots=True)
class ExpressionRuntimeResult:
    planning: PlanningRuntimeResult
    expression_event_id: str | None = None
    review_event_id: str | None = None
    text: str | None = None
    review_disposition: str | None = None
    # Review quality and current wording are not delivery authorization.
    delivery_authorized: bool = False


class ExpressionRuntime:
    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.planning = PlanningRuntime(journal, content_vault=content_vault,
                                        context_vault=context_vault)
        self.store = OpportunityExpressionStore(journal,
            content_vault=self.planning.synth.vault, context_vault=context_vault)
        self.comparator = SemanticComparator(self.store)

    def _bound_record(self, event_id, kind, subject, sensitivity, cause, payload):
        existing = self.journal.get(event_id)
        if existing is None:
            event = EventEnvelope(event_id=event_id, event_type=kind,
                source='alive.expression-runtime', actor='system:alive-runtime',
                subject=subject, sensitivity=sensitivity, causation_id=cause, payload=payload)
            try:
                self.journal.append(event)
            except EventConflictError:
                pass
            existing = self.journal.get(event_id)
        if (existing is None or existing.event.event_type != kind
                or existing.event.source != 'alive.expression-runtime'
                or existing.event.actor != 'system:alive-runtime'
                or existing.event.subject != subject or existing.event.sensitivity is not sensitivity
                or existing.event.causation_id != cause
                or _thaw_json(existing.event.payload) != payload):
            raise ExpressionRuntimeError('expression operation binding changed')
        return existing

    async def run(self, *, resolve_domain, renderer_model=None, reviewer_model=None,
                  language=None, **planning_parameters):
        # Reject malformed host options before planning can spend on a provider.
        for model in (renderer_model, reviewer_model):
            if model is not None and (not isinstance(model, str) or not re.fullmatch(
                    r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}', model)):
                raise ExpressionRuntimeError('invalid expression model')
        if language is not None and (not isinstance(language, str) or not re.fullmatch(
                r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8}){0,3}', language)):
            raise ExpressionRuntimeError('invalid expression language')
        if not callable(resolve_domain):
            raise ExpressionRuntimeError('missing host independence resolver')
        planned = await self.planning.run(**planning_parameters)
        if planned.action_kind == 'silence':
            return ExpressionRuntimeResult(planned)
        subject = planning_parameters['subject']
        meaning = self.store.define_for_selection(selection_event_id=planned.selection_event_id,
                                                   subject=subject)
        digest = self.store.content_vault.digest_json({'selection': planned.selection_event_id})[:40]
        operation = 'runtime-expression:' + digest
        start_id = 'expression.runtime:' + digest + ':started'
        done_id = 'expression.runtime:' + digest + ':completed'
        style = self.comparator._style(subject, 'proactive_social')
        independent = (planning_parameters.get('require_independent_grounding', False)
                       if planning_parameters.get('grounding', False) else True)
        binding = {'selection_event_id': planned.selection_event_id,
            'meaning_event_id': meaning.event.event_id,
            'renderer_model': renderer_model, 'reviewer_model': reviewer_model, 'language': language,
            'style_digest': self.store.content_vault.digest_json(style), 'delivery_authorized': False}
        if planning_parameters.get('grounding', False):
            binding['require_independence'] = independent
        self._bound_record(start_id, 'expression.runtime_started', subject,
            meaning.event.sensitivity, planned.selection_event_id, binding)
        completed = self.journal.get(done_id)
        if completed is None:
            if self.journal.get('semantic.comparison:' + operation + ':started') is not None:
                native_done = self.journal.get('semantic.comparison:' + operation + ':completed')
                native_failed = self.journal.get('semantic.comparison:' + operation + ':failed')
                review_record = self.journal.get('message.semantic_review:comparison:' + operation)
                recovered_review = self.store.verify_review(review_record, allow_correlated=not independent) if review_record is not None else None
                if (native_done is None or native_failed is not None or recovered_review is None
                        or native_done.event.event_type != 'semantic.comparison_stage'
                        or native_done.event.source != 'alive.semantic-comparator'
                        or native_done.event.actor != 'system:alive-shadow-comparator'
                        or native_done.event.subject != subject
                        or native_done.event.sensitivity is not meaning.event.sensitivity
                        or native_done.event.causation_id != planned.selection_event_id
                        or native_done.event.payload.get('stage') != 'completed'
                        or native_done.event.payload.get('status') != recovered_review.assessment.disposition.value):
                    raise ExpressionRuntimeError('expression operation unresolved; no implicit provider retry')
                candidate_id, review_id = recovered_review.candidate_event_id, recovered_review.event_id
            else:
                comparison = await self.comparator.run(selection_event_id=planned.selection_event_id,
                    meaning_event_id=meaning.event.event_id, subject=subject,
                    call=planning_parameters['call'], resolve_domain=resolve_domain,
                    renderer_model=renderer_model, reviewer_model=reviewer_model,
                    language=language, operation_id=operation, require_independence=independent)
                candidate_id, review_id = comparison.candidate.event_id, comparison.review.event_id
            completed = self._bound_record(done_id, 'expression.runtime_completed', subject,
                meaning.event.sensitivity, start_id,
                {'expression_event_id': candidate_id,
                 'review_event_id': review_id, 'delivery_authorized': False})
        # Current intent/evidence and current style remain authoritative on recovery.
        candidate = self.store.resolve_model_candidate(str(completed.event.payload.get('expression_event_id', '')))
        review_record = self.journal.get(str(completed.event.payload.get('review_event_id', '')))
        review = self.store.verify_review(review_record, allow_correlated=not independent) if review_record is not None else None
        if (candidate is None or review is None or candidate.selection_event_id != planned.selection_event_id
                or candidate.meaning_event_id != meaning.event.event_id
                or candidate.renderer_execution_id != 'execution:' + operation + ':render'
                or review.candidate_event_id != candidate.event_id
                or review.review_id != 'comparison:' + operation):
            raise ExpressionRuntimeError('retained expression/review is unavailable or foreign')
        self._bound_record(done_id, 'expression.runtime_completed', subject,
            meaning.event.sensitivity, start_id,
            {'expression_event_id': candidate.event_id, 'review_event_id': review.event_id,
             'delivery_authorized': False})
        return ExpressionRuntimeResult(planned, candidate.event_id, review.event_id,
            candidate.text, review.assessment.disposition.value)
