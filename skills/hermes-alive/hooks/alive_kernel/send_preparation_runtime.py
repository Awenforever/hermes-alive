"""Current expression to send-time authorization; no channel IO or FIFO."""
from dataclasses import dataclass
import re

from .action_authorization import SendTimeAuthorizer, ActionAuthorizationDecision
from .expression_runtime import ExpressionRuntime, ExpressionRuntimeResult
from .outcomes import OutcomeProjection


@dataclass(frozen=True, slots=True)
class SendPreparationResult:
    expression: ExpressionRuntimeResult
    authorization: ActionAuthorizationDecision | None = None
    attempt_event_id: str | None = None
    # Preparing an attempt never claims an external delivery.
    sent: bool = False
    final_review_event_id: str | None = None
    quality_disposition: str = 'not_reviewed'


class SendPreparationRuntime:
    """Compose planning/expression with existing exact send-time checks.

The host supplies route and confirmation/delegation records. This runtime never
manufactures them from model output or reviews, nor falls back to another body.
"""

    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.context_vault = context_vault
        self.expression = ExpressionRuntime(journal, content_vault=content_vault,
                                             context_vault=context_vault)
        self.vault = self.expression.planning.synth.vault
        self.authorizer = SendTimeAuthorizer(journal, content_vault=self.vault,
                                            context_vault=context_vault)
        self.outcomes = OutcomeProjection(journal, content_vault=self.vault)

    def _expression_origin(self, expressed):
        candidate = self.expression.store.resolve_model_candidate(expressed.expression_event_id)
        if candidate is None:
            raise ValueError('final expression provenance is unavailable')
        subject = self.journal.get(candidate.event_id).event.subject
        for receipt in (expressed.planning.interpretation_event_id,
                        expressed.planning.repair_interpretation_event_id):
            if receipt is None:
                continue
            operation = receipt.removeprefix('opportunity.synthesis:').removesuffix(':completed')
            generated = self.expression.planning.synth.load_completed(subject=subject, operation_id=operation)
            if any(c.action.candidate_id == candidate.candidate_id for c in generated.candidates):
                return subject, operation, self.journal.get(candidate.event_id).event.sensitivity
        raise ValueError('final expression does not belong to its planning evidence')

    async def _review_final(self, expressed, parameters):
        from .expression_support import ExpressionSourceSupportReviewer
        subject, origin, clearance = self._expression_origin(expressed)
        reviewer = ExpressionSourceSupportReviewer(self.journal, content_vault=self.vault,
                                                   context_vault=self.context_vault)
        required = parameters.get('require_independent_grounding', False)
        resolver = parameters.get('resolve_grounding_domain') or (lambda model:'unqualified-family')
        operation = 'final-ground:' + self.vault.digest_json({'expression':expressed.expression_event_id,
            'required':required, 'model':parameters.get('grounding_model') or parameters.get('requested_model')})[:40]
        prefix = 'opportunity.source-support:' + operation
        if self.journal.get(prefix + ':started') is None:
            await reviewer.run(subject=subject, interpretation_id=origin,
                candidate_id=expressed.expression_event_id, operation_id=operation,
                call=parameters['call'], resolve_domain=resolver,
                reviewer_model=parameters.get('grounding_model') or parameters.get('requested_model'),
                require_independence=required, clearance=clearance)
        event_id = prefix + ':completed'
        findings = reviewer.verify_current(event_id, subject=subject, interpretation_id=origin,
            candidate_id=expressed.expression_event_id, allow_correlated=not required, clearance=clearance)
        if findings is None:
            raise ValueError('final review unresolved or stale; no implicit provider retry')
        payload = self.journal.get(event_id).event.payload
        if (resolver(payload['generator_model']) != payload['generator_domain']
                or resolver(payload['reviewer_model']) != payload['reviewer_domain']):
            raise ValueError('final review model scope changed')
        return event_id, findings['verdict']

    async def prepare(self, *, authorization_operation_id, route_binding_id,
                      confirmation_event_id=None, delegation_event_id=None,
                      **expression_parameters):
        # Fail before any model spend on malformed host execution contracts.
        for name, value, maximum, optional in (
            ('authorization operation', authorization_operation_id, 127, False),
            ('route binding', route_binding_id, 127, False),
            ('confirmation', confirmation_event_id, 254, True),
            ('delegation', delegation_event_id, 254, True)):
            if value is None and optional:
                continue
            if not isinstance(value, str) or not re.fullmatch(
                    rf'[A-Za-z0-9][A-Za-z0-9._:@/-]{{0,{maximum}}}', value):
                raise ValueError('invalid host ' + name)
        expressed = await self.expression.run(**expression_parameters)
        if expressed.planning.action_kind == 'silence':
            return SendPreparationResult(expressed)
        subject = expression_parameters['subject']
        final_event, quality = None, 'not_reviewed'
        if expression_parameters.get('grounding', False):
            if expressed.review_disposition == 'rejected':
                return SendPreparationResult(expressed, final_review_event_id=expressed.review_event_id,
                                              quality_disposition='final_semantic_rejected')
            final_event, quality = await self._review_final(expressed, expression_parameters)
            if quality != 'supported':
                return SendPreparationResult(expressed, final_review_event_id=final_event,
                                              quality_disposition='final_' + quality)
        witness = None
        if final_event is not None:
            _subject, origin, _clearance = self._expression_origin(expressed)
            witness = {'review_event_id':final_event, 'interpretation_id':origin,
                       'require_independence':expression_parameters.get('require_independent_grounding', False)}
        decision = self.authorizer.evaluate(selection_event_id=expressed.planning.selection_event_id,
            subject=subject, capability='hermes.channel.send', operation_id=authorization_operation_id,
            route_binding_id=route_binding_id, confirmation_event_id=confirmation_event_id,
            delegation_event_id=delegation_event_id, expression_event_id=expressed.expression_event_id,
            final_wording_witness=witness)
        if not decision.authorized:
            return SendPreparationResult(expressed, decision, final_review_event_id=final_event,
                                          quality_disposition=quality)
        identity = 'runtime-attempt:' + self.vault.digest_json({
            'selection': expressed.planning.selection_event_id,
            'expression': expressed.expression_event_id, 'subject': subject})[:40]
        attempt = self.outcomes.append_attempt(authorization_event_id=decision.event_id,
            selection_event_id=expressed.planning.selection_event_id,
            candidate_id=decision.candidate_id, executor='hermes.channel.send',
            idempotency_key=identity, actor='system:alive-runtime', subject=subject,
            attempt_id=identity)
        projected = self.outcomes.apply(attempt)
        if projected.outcome != 'recorded':
            raise ValueError('authorized runtime attempt was not admitted')
        return SendPreparationResult(expressed, decision, attempt.event.event_id,
            final_review_event_id=final_event, quality_disposition=quality)

    def _validate_prepared_lease(self, prepared, lease):
        from .dispatch_outbox import DispatchOutboxError
        if prepared.expression.planning.grounding_reviews:
            from .expression_support import ExpressionSourceSupportReviewer
            subject, origin, clearance = self._expression_origin(prepared.expression)
            record = self.journal.get(prepared.final_review_event_id) if prepared.final_review_event_id else None
            findings = ExpressionSourceSupportReviewer(self.journal, content_vault=self.vault,
                context_vault=self.context_vault).verify_current(prepared.final_review_event_id,
                    subject=subject, interpretation_id=origin,
                    candidate_id=prepared.expression.expression_event_id, allow_correlated=True,
                    clearance=clearance) if record else None
            if (prepared.quality_disposition != 'supported' or findings is None
                    or findings['verdict'] != 'supported'):
                raise DispatchOutboxError('prepared action lacks current final-wording support')
        attempt = self.journal.get(prepared.attempt_event_id) if prepared.attempt_event_id else None
        if (prepared.authorization is None or not prepared.authorization.authorized
                or attempt is None
                or prepared.attempt_event_id != 'action.attempt:' + lease.attempt_id
                or lease.subject != attempt.event.subject):
            raise DispatchOutboxError('lease does not belong to the prepared attempt')
        if (attempt.event.payload.get('authorization_event_id') != prepared.authorization.event_id
                or attempt.event.payload.get('selection_event_id') != prepared.expression.planning.selection_event_id):
            raise DispatchOutboxError('prepared attempt differs from canonical authorization')

    def execute_prepared_with_cli(self, prepared, lease, **host_parameters):
        """Consume this exact attempt through the qualified host CLI seam once."""
        from .cli_execution import execute_text_cli_once
        from .dispatch_outbox import DispatchOutbox
        self._validate_prepared_lease(prepared, lease)
        return execute_text_cli_once(DispatchOutbox(self.journal, content_vault=self.vault,
            context_vault=self.context_vault),
            lease, **host_parameters)

    async def execute_prepared_with_adapter(self, prepared, lease, **host_parameters):
        """Exact prepared action -> qualified adapter -> closed local trace."""
        from .observed_channel_execution import execute_observed_text_once
        from .dispatch_outbox import DispatchOutbox
        self._validate_prepared_lease(prepared, lease)
        return await execute_observed_text_once(DispatchOutbox(self.journal, content_vault=self.vault,
            context_vault=self.context_vault), lease, **host_parameters)

    async def execute_prepared_with_publisher(self, prepared, lease, **host_parameters):
        """Submit once to a qualified deferred publisher; do not drain its FIFO."""
        from .published_channel_execution import execute_published_text_once
        from .dispatch_outbox import DispatchOutbox
        self._validate_prepared_lease(prepared, lease)
        return await execute_published_text_once(DispatchOutbox(self.journal,
            content_vault=self.vault,context_vault=self.context_vault),lease,**host_parameters)
