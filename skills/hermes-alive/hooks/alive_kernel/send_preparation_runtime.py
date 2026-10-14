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


class SendPreparationRuntime:
    """Compose planning/expression with existing exact send-time checks.

The host supplies route and confirmation/delegation records. This runtime never
manufactures them from model output or reviews, nor falls back to another body.
"""

    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.expression = ExpressionRuntime(journal, content_vault=content_vault,
                                             context_vault=context_vault)
        self.vault = self.expression.planning.synth.vault
        self.authorizer = SendTimeAuthorizer(journal, content_vault=self.vault,
                                            context_vault=context_vault)
        self.outcomes = OutcomeProjection(journal, content_vault=self.vault)

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
        decision = self.authorizer.evaluate(selection_event_id=expressed.planning.selection_event_id,
            subject=subject, capability='hermes.channel.send', operation_id=authorization_operation_id,
            route_binding_id=route_binding_id, confirmation_event_id=confirmation_event_id,
            delegation_event_id=delegation_event_id, expression_event_id=expressed.expression_event_id)
        if not decision.authorized:
            return SendPreparationResult(expressed, decision)
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
        return SendPreparationResult(expressed, decision, attempt.event.event_id)
