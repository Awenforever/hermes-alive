"""Source review of exact retained expression, not just its drafting ancestor."""
from dataclasses import dataclass
import json
import re

from .events import Sensitivity
from .content_vault import ContentReference
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

    def correction_context(self, review_event_id, *, subject, selection_event_id):
        """One retained negative review can correct the original runtime wording.

        Findings are advisory, not new facts, preferences or authority. A review
        of a repaired expression cannot open another repair generation.
        """
        record = self.journal.get(review_event_id)
        if (record is None or record.event.subject != subject
                or record.event.event_type != 'opportunity.source_support_completed'):
            raise SourceSupportError('correction review unavailable or foreign')
        try:
            ref = ContentReference.from_event_payload(record.event.payload['content'])
            retained = self.vault.resolve_json(ref.content_id, expected_subject=subject,
                expected_purpose='opportunity.source-support', expected_sensitivity=record.event.sensitivity)
            snapshot = retained['snapshot']
            expression_id = snapshot['candidate']['id']
            origin = snapshot['expression_binding']['interpretation_receipt_event_id']
            origin = origin.removeprefix('opportunity.synthesis:').removesuffix(':completed')
            findings = self.verify_current(review_event_id, subject=subject,
                interpretation_id=origin, candidate_id=expression_id,
                clearance=record.event.sensitivity, allow_correlated=True)
            expression = self.expressions.resolve_model_candidate(expression_id)
            operation = 'runtime-expression:' + self.vault.digest_json({'selection':selection_event_id})[:40]
            if (findings is None or findings['verdict'] not in ('unsupported', 'uncertain')
                    or expression is None or expression.selection_event_id != selection_event_id
                    or expression.renderer_execution_id != 'execution:' + operation + ':render'):
                raise SourceSupportError('correction must concern one original negative final review')
            return {'review_event_id':review_event_id, 'previous_expression_event_id':expression_id,
                    'findings':findings, 'grounding_context':snapshot,
                    'findings_are_not_new_facts':True, 'delivery_authority_granted':False}
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceSupportError('correction context unavailable or stale') from exc

    def current_correction_binding(self, expression, *, subject, selection_event_id):
        prefix = 'execution:runtime-expression-repair:'
        if not expression.renderer_execution_id.startswith(prefix):
            return None
        digest = expression.renderer_execution_id.removeprefix(prefix).removesuffix(':render')
        expected = self.vault.digest_json({'selection':selection_event_id,
                                          'phase':'final-wording-repair-v1'})[:40]
        if not re.fullmatch(r'[0-9a-f]{40}', digest) or digest != expected:
            raise SourceSupportError('invalid correction operation scope')
        start_id = 'expression.runtime:' + digest + ':started'
        start = self.journal.get(start_id)
        done = self.journal.get('expression.runtime:' + digest + ':completed')
        for record, kind, cause in ((start, 'expression.runtime_started', selection_event_id),
                                   (done, 'expression.runtime_completed', start_id)):
            if (record is None or record.event.event_type != kind
                    or record.event.subject != subject or record.event.causation_id != cause
                    or record.event.source != 'alive.expression-runtime'
                    or record.event.actor != 'system:alive-runtime'):
                raise SourceSupportError('correction runtime receipt unavailable')
        context = self.correction_context(start.event.payload.get('correction_review_event_id'),
                                         subject=subject, selection_event_id=selection_event_id)
        if (self.vault.digest_json(context) != start.event.payload.get('correction_digest')
                or context['previous_expression_event_id'] != start.event.payload.get('previous_expression_event_id')
                or done.event.payload.get('expression_event_id') != expression.event_id):
            raise SourceSupportError('correction runtime evidence changed')
        return {'runtime_start_event_id':start_id, 'review_event_id':context['review_event_id'],
                'context_digest':self.vault.digest_json(context)}

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
        correction = self.current_correction_binding(expression, subject=subject,
                                                     selection_event_id=expression.selection_event_id)
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
        if correction is not None:
            data['expression_binding']['correction'] = correction
        if len(json.dumps(data, ensure_ascii=False)) > 40000:
            raise SourceSupportError('expression source review exceeds prompt boundary')
        # Independence and retention are checked against the actual renderer and
        # expression event, not the original drafter or longer-lived source bundle.
        return data, _ExpressionAnchor(expression.event_id, expression.renderer_model)
