"""Bounded once-per-outcome interpretation and retractable advisory context.

This is not permission to admit preferences, update profile facts or send. Raw
paired feedback remains available to challenge a model's tentative interpretation.
"""
from contextlib import closing
from dataclasses import dataclass, field
import json
import re

from .content_vault import ContentUnavailableError
from .events import Sensitivity
from .feedback_synthesis import FeedbackSynthesizer, FeedbackSynthesisError


KINDS = ('user_replied','user_corrected','user_dismissed','explicit_feedback')


@dataclass(frozen=True, slots=True)
class FeedbackHypothesisEvidence:
    evidence_event_ids: tuple
    actual_model: str
    observed_at: str
    findings_json: str = field(repr=False)

    def to_prompt(self):
        return dict(kind='tentative_feedback_interpretation', evidence_event_ids=list(self.evidence_event_ids),
            actual_model=self.actual_model, observed_at=self.observed_at,
            findings=json.loads(self.findings_json), advisory_only=True, semantic_accuracy_proven=False,
            complete_feedback_inventory=False, automatic_learning_authority=False,
            duplicate_evidence_is_not_independent_support=True)


class FeedbackAssimilationRuntime:
    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.interpreter = FeedbackSynthesizer(journal,content_vault=content_vault,context_vault=context_vault)
        self.vault = self.interpreter.vault

    def operation(self, subject, outcome_event_id):
        return 'feedback-assimilation:'+self.vault.digest_json(dict(subject=subject,outcome=outcome_event_id))[:40]

    async def tick(self, *, subject, call, model=None, clearance=Sensitivity.PRIVATE, scan_limit=16, new_limit=1):
        if (not isinstance(subject,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}',subject)
                or not callable(call) or type(scan_limit) is not int or not 1<=scan_limit<=64
                or type(new_limit) is not int or not 1<=new_limit<=4):
            raise ValueError('bounded owner feedback interpretation required')
        clearance = Sensitivity(clearance)
        name = 'alive-feedback-assimilation:'+self.vault.digest_json(dict(subject=subject,clearance=clearance.value))
        after = self.journal.checkpoint(name)
        with closing(self.journal._connect()) as connection:
            rows = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events '
                'WHERE subject=? AND event_type=? AND sequence>? ORDER BY sequence LIMIT ?',
                (subject,'outcome.recorded',after,scan_limit+1)).fetchall()
        counts = dict(scanned=0,attempted=0,interpreted=0,retained=0,unavailable=0,unresolved=0,
                      next_after_sequence=after,coverage_uncertain=True,automatic_learning_authority=False)
        async def routed(**kwargs):
            return await call(task='alive_feedback_interpretation',**kwargs)
        for row in rows[:scan_limit]:
            record = self.journal._record(row)
            event = record.event
            eligible = (event.payload.get('kind') in KINDS and
                        list(Sensitivity).index(event.sensitivity)<=list(Sensitivity).index(clearance))
            operation = self.operation(subject,event.event_id)
            prefix = self.interpreter._prefix(subject,operation)
            if eligible and self.journal.get(prefix+':started') is None:
                if counts['attempted']>=new_limit:
                    break
                try:
                    # Snapshot checks consent/attribution before private body access.
                    self.interpreter.snapshot(subject=subject,outcome_event_id=event.event_id,clearance=event.sensitivity)
                except (FeedbackSynthesisError,ContentUnavailableError):
                    counts['unavailable'] += 1
                else:
                    counts['attempted'] += 1
                    try:
                        await self.interpreter.run(subject=subject,outcome_event_id=event.event_id,
                            operation_id=operation,call=routed,model=model,clearance=event.sensitivity)
                        counts['interpreted'] += 1
                    except Exception:
                        # One outcome cannot erase other current evidence. Never
                        # change the operation key to retry failed provider work.
                        if self.journal.get(prefix+':started') is None:
                            raise
                        counts['unresolved'] += 1
            elif eligible:
                try:
                    self.interpreter.load_completed(subject=subject,outcome_event_id=event.event_id,
                        operation_id=operation,clearance=event.sensitivity)
                    counts['retained'] += 1
                except (FeedbackSynthesisError,ContentUnavailableError):
                    counts['unresolved'] += 1
            counts['scanned'] += 1
            counts['next_after_sequence'] = self.journal.advance_checkpoint(name,record.sequence,coalesce=True)
        return counts

    def read(self, *, subject, clearance):
        clearance = Sensitivity(clearance)
        values, size = [], 0
        for record in self.journal.iter_reverse(event_types=('outcome.recorded',),subject=subject,max_records=64):
            event = record.event
            if (list(Sensitivity).index(event.sensitivity)>list(Sensitivity).index(clearance)
                    or event.payload.get('kind') not in KINDS):
                continue
            operation = self.operation(subject,event.event_id)
            prefix = self.interpreter._prefix(subject,operation)
            if self.journal.get(prefix+':completed') is None:
                continue
            try:
                findings = self.interpreter.load_completed(subject=subject,outcome_event_id=event.event_id,
                    operation_id=operation,clearance=event.sensitivity)
            except (FeedbackSynthesisError,ContentUnavailableError):
                continue
            if not findings['signals']:
                continue
            completed = self.journal.get(prefix+':completed')
            value = FeedbackHypothesisEvidence((completed.event.event_id,event.event_id,event.payload['source_event_id']),
                completed.event.payload['actual_model'],event.observed_at.isoformat(),
                json.dumps(findings,ensure_ascii=False))
            encoded = json.dumps(value.to_prompt(),ensure_ascii=False)
            if len(encoded)>6000 or size+len(encoded)>6000:
                continue  # Keep mixed signals/qualifications whole, never trim their scope.
            values.append(value); size += len(encoded)
            if len(values)==3:
                break
        return tuple(values)
