"""Host-invoked autonomous cycle composition, not an activated production daemon.

Current models/context and authority come from the host/user, never this module.
Shadow is non-executing; opt-in execution consumes only the exact prepared attempt.
"""
from dataclasses import dataclass,field
import re

from .dispatch_outbox import DispatchOutbox
from .send_preparation_runtime import SendPreparationRuntime
from .transport_reconciliation_runtime import TransportReconciliationRuntime


@dataclass(frozen=True,slots=True)
class AutonomousCycleResult:
    disposition: str
    reconciliation: object = field(repr=False)
    expression: object = field(default=None,repr=False)
    prepared: object = field(default=None,repr=False)
    submission: object = field(default=None,repr=False)
    external_delivery_proven: bool = False


class AutonomousCycleRuntime:
    def __init__(self,journal,*,content_vault=None,context_vault=None):
        self.preparation = SendPreparationRuntime(journal,content_vault=content_vault,context_vault=context_vault)
        self.outbox = DispatchOutbox(journal,content_vault=self.preparation.vault,context_vault=context_vault)
        self.reconciliation = TransportReconciliationRuntime(self.outbox)

    async def cycle(self,*,subject,operation_id,expression_parameters,resolve_binding,
            execute=False,authorization_parameters=None,send_parameters=None,worker_id=None,
            reconciliation_cursor=0,binding_limit=16,receipt_limit=128):
        if (type(execute) is not bool or not isinstance(expression_parameters,dict)
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
        parameters = {**expression_parameters,'subject':subject,'operation_id':operation_id,
                      'policy_context':policy.context}
        if not execute:
            expression = await self.preparation.expression.run(**parameters)
            return AutonomousCycleResult('silence' if expression.planning.action_kind=='silence'
                else 'shadow_selected',reconciliation,expression=expression)
        if any(key in authorization_parameters for key in parameters):
            raise ValueError('authorization cannot override cycle planning')
        prepared = await self.preparation.prepare(**parameters,**authorization_parameters)
        if prepared.expression.planning.action_kind=='silence':
            return AutonomousCycleResult('silence',reconciliation,prepared=prepared)
        if prepared.quality_disposition.startswith('final_'):
            return AutonomousCycleResult('content_review_attention',reconciliation,prepared=prepared)
        if prepared.authorization is None or not prepared.authorization.authorized:
            return AutonomousCycleResult('not_authorized',reconciliation,prepared=prepared)
        lease = self.outbox.acquire(worker_id=worker_id,subject=subject,
            attempt_id=prepared.attempt_event_id.removeprefix('action.attempt:'))
        if lease is None:
            return AutonomousCycleResult('attempt_unavailable',reconciliation,prepared=prepared)
        submission = await self.preparation.execute_prepared_with_publisher(prepared,lease,**send_parameters)
        return AutonomousCycleResult('submitted',reconciliation,prepared=prepared,submission=submission)
