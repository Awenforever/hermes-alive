"""Source review of exact retained expression, not just its drafting ancestor."""
from dataclasses import dataclass
import json

from .events import Sensitivity
from .opportunity_expression import OpportunityExpressionStore
from .source_support import SourceSupportError, SourceSupportReviewer


@dataclass(frozen=True, slots=True)
class _ExpressionAnchor:
    receipt_event_id: str
    actual_model: str


class ExpressionSourceSupportReviewer(SourceSupportReviewer):
    """Reuse review lifecycle, substituting a verified final expression snapshot.

    candidate_id names the expression event, not the earlier opportunity candidate.
    Source approval of an ancestor cannot be inherited by later model wording.
    This is a shadow assessment, never confirmation or delivery authorization.
    """

    def __init__(self, journal, *, content_vault=None, context_vault=None):
        super().__init__(journal, content_vault=content_vault, context_vault=context_vault)
        self.expressions = OpportunityExpressionStore(journal,
            content_vault=self.vault, context_vault=context_vault)

    def require_current_witness(self, witness, *, subject, expression_event_id,
                                selection_event_id):
        """Revalidate a permit-bound quality requirement, never mint authority."""
        if (not isinstance(witness, dict) or set(witness) != {
                'review_event_id', 'interpretation_id', 'require_independence'}
                or type(witness['require_independence']) is not bool
                or any(not isinstance(witness[key], str) or not witness[key]
                       for key in ('review_event_id', 'interpretation_id'))):
            raise SourceSupportError('invalid final-wording witness')
        if not isinstance(expression_event_id, str) or not expression_event_id:
            raise SourceSupportError('final-wording witness needs an expression')
        expression = self.expressions.resolve_model_candidate(expression_event_id)
        header = self.journal.get(expression_event_id)
        if (expression is None or header is None or header.event.subject != subject
                or expression.selection_event_id != selection_event_id):
            raise SourceSupportError('final-wording witness expression mismatch')
        findings = self.verify_current(witness['review_event_id'], subject=subject,
            interpretation_id=witness['interpretation_id'], candidate_id=expression_event_id,
            allow_correlated=not witness['require_independence'], clearance=header.event.sensitivity)
        record = self.journal.get(witness['review_event_id'])
        if (findings is None or findings['verdict'] != 'supported' or record is None
                or record.event.payload.get('require_independence') != witness['require_independence']):
            raise SourceSupportError('final wording is no longer supported')

    def snapshot(self, *, subject, interpretation_id, candidate_id,
                 clearance=Sensitivity.PRIVATE):
        # Scope before resolving encrypted content. Resolution then verifies the
        # retained signature, selection/meaning binding, current source and expiry.
        header = self.journal.get(candidate_id)
        if (header is None or header.event.subject != subject
                or header.event.sensitivity != Sensitivity(clearance)
                or header.event.event_type != 'message.model_candidate'):
            raise SourceSupportError('expression scope unavailable')
        expression = self.expressions.resolve_model_candidate(candidate_id)
        if expression is None:
            raise SourceSupportError('expression is no longer current')
        data, generated = super().snapshot(subject=subject,
            interpretation_id=interpretation_id, candidate_id=expression.candidate_id,
            clearance=clearance)
        # The selected candidate's identity cryptographically binds its synthesis
        # operation. A caller cannot supply another interpretation as evidence.
        data['candidate'] = {**data['candidate'], 'id':candidate_id, 'text':expression.text}
        data['expression_binding'] = {
            'stage':'final_expression', 'selection_event_id':expression.selection_event_id,
            'meaning_event_id':expression.meaning_event_id,
            'opportunity_candidate_id':expression.candidate_id,
            'interpretation_receipt_event_id':generated.receipt_event_id,
            'draft_is_not_evidence':True,
        }
        if len(json.dumps(data, ensure_ascii=False)) > 40000:
            raise SourceSupportError('expression source review exceeds prompt boundary')
        # Independence and retention are checked against the actual renderer and
        # expression event, not the original drafter or longer-lived source bundle.
        return data, _ExpressionAnchor(expression.event_id, expression.renderer_model)
