"""Literal, consented, attributed feedback context; no preference projection.

Do not require a model paraphrase to remember what a person actually said.
The existing feedback snapshot validates delivery linkage, retention and scope.
"""
from dataclasses import dataclass,field
from contextlib import closing
import json

from .content_vault import ContentReference,ContentUnavailableError,ContentIntegrityError
from .events import Sensitivity
from .feedback_synthesis import FeedbackSynthesizer,FeedbackSynthesisError
from .outcomes import OutcomeProjection


@dataclass(frozen=True,slots=True)
class LiteralFeedback:
    outcome_event_id: str
    source_event_id: str
    attempt_event_id: str
    observed_at: str
    retention_until: str
    delivered_text: str = field(repr=False)
    feedback_text: str = field(repr=False)

    def to_prompt(self):
        return {'outcome_event_id':self.outcome_event_id,'source_event_id':self.source_event_id,
            'attempt_event_id':self.attempt_event_id,'observed_at':self.observed_at,
            'retention_until':self.retention_until,
            'delivered_text':self.delivered_text,'feedback_text':self.feedback_text,
            'status':'literal_attributed_feedback_not_profile_update',
            'interpretation_required':True,'complete_feedback_inventory':False,
            'action_authority':False}


class FeedbackContextReader:
    def __init__(self,journal,*,content_vault=None,context_vault=None):
        self.journal=journal
        self.interpreter=FeedbackSynthesizer(journal,content_vault=content_vault,
                                             context_vault=context_vault)

    def read(self,*,subject,clearance):
        if not isinstance(subject,str) or not subject.strip():
            raise ValueError('feedback owner is required')
        clearance=Sensitivity(clearance)
        accepted=[]
        size=0
        for record in self.journal.iter_reverse(event_types=('outcome.recorded',),
                subject=subject,batch_size=16,max_records=64):
            event=record.event
            if (list(Sensitivity).index(event.sensitivity)>list(Sensitivity).index(clearance)
                    or event.payload.get('kind') not in
                    ('user_replied','user_corrected','user_dismissed','explicit_feedback')):
                continue
            try:
                # Scope/consent must be established before even resolving the
                # outcome's private details, not merely before returning a pair.
                retention=self.interpreter._consent(subject,'retention.consent_changed')
                self.interpreter._consent(subject,'consolidation.consent_changed')
                days=retention.event.payload.get('retention_days')
                if ('inbound' not in retention.event.payload.get('directions',())
                        or retention.event.payload.get('content_sensitivity')!=event.sensitivity.value
                        or type(days) is not int or not 1<=days<=365):
                    continue
                with closing(self.interpreter.outcomes._connect()) as connection:
                    if not OutcomeProjection.canonical_evidence_valid_for(self.journal,connection,record):
                        continue
                ref=ContentReference.from_event_payload(event.payload['content'])
                details=self.interpreter.vault.resolve_json(ref.content_id,expected_subject=subject,
                    expected_purpose='outcome.'+event.payload['kind'],expected_sensitivity=event.sensitivity)
                if self.interpreter.vault.digest_json(details)!=ref.digest:
                    continue
                snapshot,until=self.interpreter.snapshot(subject=subject,
                    outcome_event_id=event.event_id,clearance=event.sensitivity)
            except (KeyError,TypeError,ValueError,FeedbackSynthesisError,ContentUnavailableError,ContentIntegrityError):
                continue
            value=LiteralFeedback(event.event_id,snapshot['source_event_id'],
                snapshot['attempt_event_id'],snapshot['observed_at'],until.isoformat(),
                snapshot['delivered_text'],snapshot['feedback_text'])
            length=len(json.dumps(value.to_prompt(),ensure_ascii=False))
            # Retain complete paired meaning or omit it; never truncate away a
            # negation, exception, antecedent, or qualification to fit a prompt.
            if size+length>6000:
                continue
            accepted.append(value)
            size+=length
            if len(accepted)==3:
                break
        return tuple(accepted)
