"""Bounded retained wording for deliberation, never delivery or preference proof."""
from dataclasses import dataclass, field

from .events import Sensitivity
from .semantic_review import SemanticReviewStore, candidate_digest
from .content_vault import ContentReference, ContentUnavailableError, ContentErasedError, ContentIntegrityError


@dataclass(frozen=True, slots=True)
class PriorExpression:
    event_id: str
    selection_event_id: str
    observed_at: str
    excerpt: str = field(repr=False)
    truncated: bool = False

    def to_prompt(self):
        return {'expression_event_id': self.event_id,
            'selection_event_id': self.selection_event_id,
            'generated_at': self.observed_at, 'wording_excerpt': self.excerpt,
            'excerpt_truncated': self.truncated,
            'status': 'generated_wording_only_delivery_unknown',
            'user_preference_evidence': False, 'action_authority': False}


class ExpressionHistoryReader:
    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.store = SemanticReviewStore(journal, content_vault=content_vault)

    def read(self, *, subject, clearance, before_sequence=None):
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError('history owner is required')
        clearance = Sensitivity(clearance)
        if before_sequence is not None and (type(before_sequence) is not int or before_sequence < 1):
            raise ValueError('invalid history snapshot boundary')
        result = []
        # Filtering by owner happens in SQL, before resolving private content.
        # This is bounded retained evidence, not a complete lifetime inventory.
        for record in self.journal.iter_reverse(event_types=('message.model_candidate',),
                subject=subject, batch_size=32, max_records=64, before_sequence=before_sequence):
            event = record.event
            if list(Sensitivity).index(event.sensitivity) > list(Sensitivity).index(clearance):
                continue
            # Historical authenticity is not fresh execution validity. Do not
            # recursively re-run old planning, learning and current intent here.
            payload = event.payload
            output_id = self.store.protector.pseudonym('semantic-model-candidate',
                f"{payload.get('selection_event_id')}\0{payload.get('renderer_execution_id')}\0{payload.get('candidate_digest')}")
            if (event.source != 'alive.semantic-review' or event.actor != 'system:alive-model-renderer'
                    or not output_id or event.event_id != 'message.model_candidate:' + output_id.split(':', 1)[-1]
                    or event.causation_id != payload.get('selection_event_id')
                    or event.correlation_id != payload.get('frame_id')
                    or not self.store.protector.verify_json('message.model_candidate.v1',
                        self.store._authentication_document('message.model_candidate.v1', payload),
                        payload.get('integrity_authenticator'))):
                continue
            try:
                ref = ContentReference.from_event_payload(payload['content'])
                stored = self.store.content_vault.resolve_json(ref.content_id,
                    expected_subject=subject, expected_purpose='message.model_candidate',
                    expected_sensitivity=event.sensitivity)
                text = stored['text']
                if (ref.sensitivity is not event.sensitivity or not isinstance(text, str)
                        or self.store.content_vault.digest_json(stored) != ref.digest
                        or candidate_digest(text) != payload.get('candidate_digest')):
                    continue
            except (KeyError, TypeError, ValueError, ContentUnavailableError,
                    ContentErasedError, ContentIntegrityError):
                continue
            result.append(PriorExpression(event.event_id, str(payload['selection_event_id']),
                event.observed_at.isoformat(), text[:480], len(text) > 480))
            if len(result) == 6:
                break
        return tuple(result)
