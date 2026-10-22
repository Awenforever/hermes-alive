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

    @staticmethod
    def _scope(record,subject,clearance):
        return (record is not None and record.event.subject==subject
            and record.event.event_type=='outcome.recorded'
            and list(Sensitivity).index(record.event.sensitivity)<=list(Sensitivity).index(clearance)
            and record.event.payload.get('kind') in
                ('user_replied','user_corrected','user_dismissed','explicit_feedback'))

    def _value(self,record,subject,clearance):
        if not self._scope(record,subject,clearance):return None
        event=record.event
        try:
            # Authorize before resolving any private body, not only on return.
            retention=self.interpreter._consent(subject,'retention.consent_changed')
            self.interpreter._consent(subject,'consolidation.consent_changed')
            days=retention.event.payload.get('retention_days')
            if ('inbound' not in retention.event.payload.get('directions',())
                    or retention.event.payload.get('content_sensitivity')!=event.sensitivity.value
                    or type(days) is not int or not 1<=days<=365):
                return None
            with closing(self.interpreter.outcomes._connect()) as connection:
                if not OutcomeProjection.canonical_evidence_valid_for(self.journal,connection,record):
                    return None
            ref=ContentReference.from_event_payload(event.payload['content'])
            details=self.interpreter.vault.resolve_json(ref.content_id,expected_subject=subject,
                expected_purpose='outcome.'+event.payload['kind'],expected_sensitivity=event.sensitivity)
            if self.interpreter.vault.digest_json(details)!=ref.digest:
                return None
            snapshot,until=self.interpreter.snapshot(subject=subject,
                outcome_event_id=event.event_id,clearance=event.sensitivity)
        except (KeyError,TypeError,ValueError,FeedbackSynthesisError,ContentUnavailableError,ContentIntegrityError):
            return None
        return LiteralFeedback(event.event_id,snapshot['source_event_id'],
                snapshot['attempt_event_id'],snapshot['observed_at'],until.isoformat(),
                snapshot['delivered_text'],snapshot['feedback_text'])

    def read(self,*,subject,clearance):
        """Historical recent-window contract; archive recall is separate."""
        if not isinstance(subject,str) or not subject.strip():
            raise ValueError('feedback owner is required')
        clearance=Sensitivity(clearance)
        accepted=[]
        size=0
        for record in self.journal.iter_reverse(event_types=('outcome.recorded',),
                subject=subject,batch_size=16,max_records=64):
            value=self._value(record,subject,clearance)
            if value is None:continue
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

    def catalog(self,*,subject,clearance,before_sequence=None,scan_limit=32,item_limit=8):
        """Bounded paged discovery, not facts or a complete memory inventory.

        Only previews go to a recall selector. A selected reference must be
        resolved in full and rechecked after model waits; no preview supports a
        profile fact, sender identity, consent change or action permission.
        """
        from .native_worker_protocol import identifier
        identifier(subject)
        clearance=Sensitivity(clearance)
        if (type(scan_limit) is not int or not 1<=scan_limit<=64
                or type(item_limit) is not int or not 1<=item_limit<=16
                or before_sequence is not None and (type(before_sequence) is not int or before_sequence<1)):
            raise ValueError('bounded owner feedback page required')
        rows=tuple(self.journal.iter_reverse(event_types=('outcome.recorded',),subject=subject,
            batch_size=16,max_records=scan_limit+1,before_sequence=before_sequence))
        entries=[];size=0;inspected=0;cursor=before_sequence
        for record in rows[:scan_limit]:
            value=self._value(record,subject,clearance)
            if value is not None:
                item=dict(outcome_event_id=value.outcome_event_id,source_event_id=value.source_event_id,
                    observed_at=value.observed_at,retention_until=value.retention_until,
                    delivered_preview=value.delivered_text[:256],reply_preview=value.feedback_text[:512],
                    preview_truncated=len(value.delivered_text)>256 or len(value.feedback_text)>512,
                    preview_is_not_profile_fact=True,complete_pair_required=True,action_authority=False)
                length=len(json.dumps(item,ensure_ascii=False))
                if size+length>24000:break
                entries.append(item);size+=length
            inspected+=1;cursor=record.sequence
            if len(entries)==item_limit:break
        more=inspected<len(rows)
        return dict(entries=entries,inspected=inspected,more_available=more,
            next_before_sequence=cursor if more else None,
            bounded_visibility_only=True,authority_granted=False)

    def context(self,*,subject,clearance,recalled_ids=()):
        """Keep recent corrections alongside exact recalled pairs; no trimming.

        References select evidence, not profile facts or action authority. Empty
        references retain the historical recent-window contract exactly.
        """
        recent=self.read(subject=subject,clearance=clearance)
        if recalled_ids==():return recent
        recalled=self.resolve(subject=subject,clearance=clearance,outcome_event_ids=recalled_ids)
        values=tuple({v.outcome_event_id:v for v in (*recent,*recalled)}.values())
        if len(values)>8 or sum(len(json.dumps(v.to_prompt(),ensure_ascii=False)) for v in values)>12000:
            raise FeedbackSynthesisError('complete recalled feedback exceeds context budget')
        if self.resolve(subject=subject,clearance=clearance,
                outcome_event_ids=tuple(v.outcome_event_id for v in values))!=values:
            raise FeedbackSynthesisError('recent or recalled feedback changed during context assembly')
        return values

    def resolve(self,*,subject,clearance,outcome_event_ids):
        """Resolve exact current owner references atomically, never a recent guess."""
        from .native_worker_protocol import identifier
        identifier(subject)
        clearance=Sensitivity(clearance)
        if (not isinstance(outcome_event_ids,tuple) or not 1<=len(outcome_event_ids)<=8
                or any(not isinstance(i,str) for i in outcome_event_ids)
                or len(set(outcome_event_ids))!=len(outcome_event_ids)):
            raise ValueError('bounded unique feedback references required')
        for identity in outcome_event_ids:identifier(identity)
        records=tuple(self.journal.get(i) for i in outcome_event_ids)
        # Scope the WHOLE request before any record's private body is resolved.
        if not all(self._scope(r,subject,clearance) for r in records):
            raise FeedbackSynthesisError('feedback references outside current owner scope')
        values=tuple(self._value(r,subject,clearance) for r in records)
        if any(v is None for v in values):
            raise FeedbackSynthesisError('feedback reference expired, withdrawn or unavailable')
        if tuple(self._value(r,subject,clearance) for r in records)!=values:
            raise FeedbackSynthesisError('feedback changed during exact resolution')
        return values
