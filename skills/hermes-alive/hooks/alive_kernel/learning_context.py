"""Owner-scoped learned advice for cognition; never preference or action authority."""
from dataclasses import dataclass
import json

from .outcomes import OutcomeProjection
from .reflection import ReflectionProjection
from .preference_learning import PreferenceLearningProjection, PreferenceContentStatus, PreferenceEvidenceNote


@dataclass(frozen=True, slots=True)
class LearnedCognitionEvidence:
    target_digest: str
    axis: str
    key: str
    option: str
    support_mass: float
    opposition_mass: float
    evidence_event_ids: tuple[str, ...]
    evidence_notes: tuple[PreferenceEvidenceNote, ...] = ()

    def to_prompt(self):
        return {'axis': self.axis, 'key': self.key, 'option': self.option,
            'support_mass': self.support_mass, 'opposition_mass': self.opposition_mass,
            'evidence_event_ids': list(self.evidence_event_ids), 'advisory_only': True,
            'mass_semantics': 'bounded evidence support/opposition for the named option, not enthusiasm or action permission',
            'evidence_notes': [{'observation_event_id': 'preference.observation:' + note.observation_id,
                'source_event_id': note.source_event_id, 'origin': note.origin,
                'direction': note.direction, 'rationale': note.rationale} for note in self.evidence_notes]}


class CognitionLearningReader:
    def __init__(self, journal, *, content_vault=None, hypothesis_vault=None, context_vault=None):
        self.journal = journal
        self.outcomes = OutcomeProjection(journal, content_vault=content_vault)
        self.reflections = ReflectionProjection(journal, content_vault=content_vault)
        self.learning = PreferenceLearningProjection(journal, content_vault=content_vault)
        from .feedback_assimilation import FeedbackAssimilationRuntime
        self.hypotheses = FeedbackAssimilationRuntime(journal,content_vault=hypothesis_vault,context_vault=context_vault)

    def read(self, *, subject, clearance):
        target = self.journal.last_sequence()
        for projection in (self.outcomes, self.reflections, self.learning):
            while self.journal.checkpoint(projection.CHECKPOINT) < target:
                before = self.journal.checkpoint(projection.CHECKPOINT)
                projection.project_new(limit=1000)
                after = self.journal.checkpoint(projection.CHECKPOINT)
                if after < target and after <= before:
                    raise ValueError('learning evidence projection made no progress')
        values = []
        for estimate in self.learning.estimates(subject=subject, clearance=clearance):
            if estimate.content_status is not PreferenceContentStatus.AVAILABLE:
                continue
            value = LearnedCognitionEvidence(estimate.target_digest, estimate.axis.value,
                estimate.key, estimate.option, estimate.support_mass, estimate.opposition_mass,
                tuple('preference.observation:' + item for item in estimate.evidence_ids),
                estimate.evidence_notes)
            if len(json.dumps(value.to_prompt(), ensure_ascii=False)) > 1500:
                continue
            values.append(value)
            if len(values) == 8:
                break
        hypotheses = self.hypotheses.read(subject=subject,clearance=clearance)
        if not hypotheses:
            return tuple(values)
        combined = list(hypotheses)
        size = sum(len(json.dumps(v.to_prompt(),ensure_ascii=False)) for v in combined)
        for value in values:
            length = len(json.dumps(value.to_prompt(),ensure_ascii=False))
            if len(combined)<8 and size+length<=8000:
                combined.append(value); size += length
        return tuple(combined)
