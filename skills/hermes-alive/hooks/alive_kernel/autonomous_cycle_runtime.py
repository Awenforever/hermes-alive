"""Host-invoked autonomous cycle composition, not an activated production daemon.

Current models/context and authority come from the host/user, never this module.
Shadow is non-executing; opt-in execution consumes only the exact prepared attempt.
"""
from dataclasses import dataclass,field
from datetime import datetime,timezone
import re

from .dispatch_outbox import DispatchOutbox
from .send_preparation_runtime import SendPreparationRuntime
from .transport_reconciliation_runtime import TransportReconciliationRuntime
from .reconsideration import ReconsiderationStore
from .content_vault import ContentVaultError
from .feedback_assimilation import FeedbackAssimilationRuntime
from .core_context_read import context_value


@dataclass(frozen=True,slots=True)
class AutonomousCycleResult:
    disposition: str
    reconciliation: object = field(repr=False)
    expression: object = field(default=None,repr=False)
    prepared: object = field(default=None,repr=False)
    submission: object = field(default=None,repr=False)
    external_delivery_proven: bool = False
    reconsideration_event_id: str | None = None
    quality_assessment: object = field(default=None,repr=False)
    content_rejection: object = field(default=None,repr=False)


class AutonomousCycleRuntime:
    def __init__(self,journal,*,content_vault=None,context_vault=None):
        self.preparation = SendPreparationRuntime(journal,content_vault=content_vault,context_vault=context_vault)
        self.outbox = DispatchOutbox(journal,content_vault=self.preparation.vault,context_vault=context_vault)
        self.reconciliation = TransportReconciliationRuntime(self.outbox)
        self.reconsideration = ReconsiderationStore(self.preparation, self.outbox.protector)
        self.feedback = FeedbackAssimilationRuntime(journal,content_vault=self.preparation.vault,context_vault=context_vault)

    async def cycle(self,*,subject,operation_id,expression_parameters,resolve_binding,
            execute=False,authorization_parameters=None,send_parameters=None,worker_id=None,
            reconciliation_cursor=0,binding_limit=16,receipt_limit=128,
            reconsider_after_seconds=None,cognition_configuration_id=None,
            interpret_feedback=False,feedback_model=None,channel_execution='publisher',defer_until_eligible=False,
            prepare_expression=None,listing_fingerprint=None,reuse_reconsideration=True):
        if (type(execute) is not bool or type(interpret_feedback) is not bool or type(defer_until_eligible) is not bool
                or type(reuse_reconsideration) is not bool
                or defer_until_eligible and (not execute or channel_execution!='standard')
                or channel_execution not in ('publisher','standard')
                or (feedback_model is not None and (not interpret_feedback or not isinstance(feedback_model,str)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}',feedback_model)))
                or prepare_expression is not None and not callable(prepare_expression)
                or not isinstance(expression_parameters,dict)
                or not isinstance(operation_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}',operation_id)
                or any(key in expression_parameters for key in ('subject','operation_id','policy_context'))):
            raise ValueError('host cycle must own identity and current policy')
        if execute and (not isinstance(authorization_parameters,dict) or not isinstance(send_parameters,dict)
                or not isinstance(worker_id,str) or not worker_id):
            raise ValueError('explicit qualified execution contract required')
        reconciliation = await self.reconciliation.tick(subject=subject,resolve_binding=resolve_binding,
            after_sequence=reconciliation_cursor,binding_limit=binding_limit,receipt_limit=receipt_limit)
        policy = self.reconciliation._owner_policy(subject)
        if not policy.enabled:
            return AutonomousCycleResult('paused',reconciliation)
        if reconciliation['failed_bindings']:
            return AutonomousCycleResult('reconciliation_attention',reconciliation)
        if defer_until_eligible:
            now=datetime.now(timezone.utc)
            ready=self.outbox.next_delegated_start(authorization_parameters.get('delegation_event_id'),
                subject=subject,policy_event_id=policy.event_id,
                route_binding_id=authorization_parameters.get('route_binding_id'),now=now)
            if ready>now:return AutonomousCycleResult('waiting_for_change',reconciliation)
        if interpret_feedback:
            await self.feedback.tick(subject=subject,call=expression_parameters.get('call'),model=feedback_model,
                clearance=expression_parameters.get('sensitivity','private'))
        parameters = {**expression_parameters,'subject':subject,'operation_id':operation_id,
                      'policy_context':policy.context}
        capture = None
        if reconsider_after_seconds is not None:
            def snapshot():
                current_policy = self.reconciliation._owner_policy(subject)
                if current_policy.event_id!=policy.event_id:
                    raise ValueError('owner policy changed during reconsideration')
                return self.reconsideration.capture(subject=subject,
                    configuration_id=cognition_configuration_id, execute=execute, policy=current_policy,
                    parameters=expression_parameters, window_seconds=reconsider_after_seconds,
                    listing_fingerprint=listing_fingerprint)
            async def capture():
                return await context_value(expression_parameters.get('read_context'),snapshot)
            before = await capture()
            waiting = self.reconsideration.current(subject=subject,
                configuration_id=cognition_configuration_id, context=before)
            if reuse_reconsideration and waiting is not None and waiting.event.payload['operation_id']!=operation_id:
                async def forbidden(**_):
                    raise ValueError('reconsideration cannot repeat spent inference')
                try:
                    retained = await self.preparation.expression.run(**{**parameters,
                        'operation_id':waiting.event.payload['operation_id'], 'call':forbidden})
                except (ValueError, ContentVaultError):
                    # Lost/stale retained proof cannot justify waiting. The host's
                    # new operation may think afresh; never resume the old spend.
                    retained = None
                after = await capture()
                if (retained is not None and retained.planning.action_kind=='silence'
                        and before.semantic_digest==after.semantic_digest
                        and before.owner_frontier==after.owner_frontier
                        and self.reconsideration.timing(retained.planning,subject=subject)==
                            list(waiting.event.payload.get('timing',()))
                        and self.reconsideration.current(subject=subject,
                            configuration_id=cognition_configuration_id,context=after) is not None):
                    return AutonomousCycleResult('waiting_for_change',reconciliation,
                        reconsideration_event_id=waiting.event.event_id)
        if prepare_expression is not None:
            prepared_expression=await prepare_expression()
            if (not isinstance(prepared_expression,dict) or any(key in prepared_expression
                    for key in ('subject','operation_id','policy_context'))):
                raise ValueError('expression preparation exceeded current cycle scope')
            expression_parameters=prepared_expression
            if self.reconciliation._owner_policy(subject).event_id!=policy.event_id:
                raise ValueError('owner policy changed during expression preparation')
            parameters={**expression_parameters,'subject':subject,'operation_id':operation_id,
                'policy_context':policy.context}
            if capture is not None:before=await capture()
        if not execute:
            assessed=await self.preparation.assess(**parameters)
            expression=assessed.expression
            if assessed.quality_disposition.startswith('final_'):
                rejection=await context_value(expression_parameters.get('read_context'),
                    lambda:self.preparation.rejection_witness(assessed,parameters))
                return AutonomousCycleResult('content_review_attention',reconciliation,
                    expression=expression,quality_assessment=assessed,content_rejection=rejection)
            if capture is not None and expression.planning.action_kind=='silence':
                self.reconsideration.remember(subject=subject,configuration_id=cognition_configuration_id,
                    before=before,after=await capture(),planning=expression.planning)
            return AutonomousCycleResult('silence' if expression.planning.action_kind=='silence'
                else 'shadow_selected',reconciliation,expression=expression,
                quality_assessment=assessed if parameters.get('grounding',False) else None)
        if any(key in authorization_parameters for key in parameters):
            raise ValueError('authorization cannot override cycle planning')
        prepared = await self.preparation.prepare(**parameters,**authorization_parameters)
        if prepared.expression.planning.action_kind=='silence':
            if capture is not None:
                self.reconsideration.remember(subject=subject,configuration_id=cognition_configuration_id,
                    before=before,after=await capture(),planning=prepared.expression.planning)
            return AutonomousCycleResult('silence',reconciliation,prepared=prepared)
        if prepared.quality_disposition.startswith('final_'):
            rejection=await context_value(expression_parameters.get('read_context'),
                lambda:self.preparation.rejection_witness(prepared,parameters))
            return AutonomousCycleResult('content_review_attention',reconciliation,prepared=prepared,
                content_rejection=rejection)
        if prepared.authorization is None or not prepared.authorization.authorized:
            return AutonomousCycleResult('not_authorized',reconciliation,prepared=prepared)
        lease = self.outbox.acquire(worker_id=worker_id,subject=subject,
            attempt_id=prepared.attempt_event_id.removeprefix('action.attempt:'))
        if lease is None:
            return AutonomousCycleResult('attempt_unavailable',reconciliation,prepared=prepared)
        submit = (self.preparation.execute_prepared_with_channel if channel_execution == 'standard'
                  else self.preparation.execute_prepared_with_publisher)
        submission = await submit(prepared,lease,**send_parameters)
        return AutonomousCycleResult('submitted',reconciliation,prepared=prepared,submission=submission)
