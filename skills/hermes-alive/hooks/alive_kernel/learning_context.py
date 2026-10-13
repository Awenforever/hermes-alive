"""Owner-scoped learned advice for cognition; never preference or action authority."""
from dataclasses import dataclass
import json

from .outcomes import OutcomeProjection
from .reflection import ReflectionProjection
from .preference_learning import PreferenceLearningProjection, PreferenceContentStatus


@dataclass(frozen=True, slots=True)
class LearnedCognitionEvidence:
    target_digest: str
    axis: str
    key: str
    option: str
    support_mass: float
    opposition_mass: float
    evidence_event_ids: tuple[str, ...]

    def to_prompt(self):
        return {'axis': self.axis, 'key': self.key, 'option': self.option,
            'support_mass': self.support_mass, 'opposition_mass': self.opposition_mass,
            'evidence_event_ids': list(self.evidence_event_ids), 'advisory_only': True}


class CognitionLearningReader:
    def __init__(self, journal, *, content_vault=None):
        self.journal = journal
        self.outcomes = OutcomeProjection(journal, content_vault=content_vault)
        self.reflections = ReflectionProjection(journal, content_vault=content_vault)
        self.learning = PreferenceLearningProjection(journal, content_vault=content_vault)

    def read(self, *, subject, clearance):
        target = self.journal.last_sequence()
        for projection in (self.outcomes, self.reflections, self.learning):
            while self.journal.checkpoint(projection.CHECKPOINT) < target:
                before = self.journal.checkpoint(projection.CHECKPOINT)
                projection.project_new(limit=1000)
                if self.journal.checkpoint(projection.CHECKPOINT) <= before:
                    raise ValueError('learning evidence projection made no progress')
        values = []
        for estimate in self.learning.estimates(subject=subject, clearance=clearance):
            if estimate.content_status is not PreferenceContentStatus.AVAILABLE:
                continue
            value = LearnedCognitionEvidence(estimate.target_digest, estimate.axis.value,
                estimate.key, estimate.option, estimate.support_mass, estimate.opposition_mass,
                tuple('preference.observation:' + item for item in estimate.evidence_ids))
            if len(json.dumps(value.to_prompt(), ensure_ascii=False)) > 1500:
                continue
            values.append(value)
            if len(values) == 8:
                break
        return tuple(values)
