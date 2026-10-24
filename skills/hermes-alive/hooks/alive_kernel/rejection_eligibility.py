"""Bounded read-only attempt eligibility from authenticated cycle history.

No source dismissal, scheduling, model calls, transport FIFO or action authority.
This view does not itself make a continuous host safe to resume.
"""
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone

from .discovery_opportunities import canonicalize_discovery_url
from .events import Sensitivity


@dataclass(frozen=True,slots=True,repr=False)
class HeldDiscovery:
    source_url: str
    observation_event_id: str
    review_event_id: str
    until: datetime


@dataclass(frozen=True,slots=True,repr=False)
class RejectionEligibilityView:
    held: tuple[HeldDiscovery,...]
    history_complete: bool

    @property
    def excluded_urls(self):return tuple(dict.fromkeys(item.source_url for item in self.held))


class RejectionEligibility:
    def __init__(self,host,*,clock=None):
        self.host=host
        self.journal=host.journal
        self.preparation=host.runtime.preparation
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def _owner_inputs(self):
        policy=self.host.runtime.reconciliation._owner_policy(self.host.subject)
        if not policy.enabled:raise ValueError('owner policy is paused; no eligibility capture')
        record=self.journal.get(policy.event_id)
        if record is None:raise ValueError('current owner policy provenance unavailable')
        with closing(self.journal._connect()) as connection:
            frontier=connection.execute('SELECT COALESCE(MAX(sequence),0) FROM experience_events '
                'WHERE subject=? AND (actor=? OR event_type=?)',
                (self.host.subject,self.host.subject,'conversation.inbound')).fetchone()[0]
        return policy.event_id,record.sequence,int(frontier)

    def read(self,parameters,*,limit=64):
        if (type(limit) is not int or not 1<=limit<=64
                or parameters.get('subject',self.host.subject)!=self.host.subject
                or getattr(parameters.get('call'),'pending',())):
            raise ValueError('bounded current owner scope without pending work required')
        now=self.clock()
        if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('eligibility clock must be timezone aware')
        now=now.astimezone(timezone.utc)
        owner=self._owner_inputs()
        # Limit the usable rejection history, not ordinary wait/success cycles:
        # many quiet ticks must not push a still-live rejection out of view.
        with closing(self.journal._connect()) as connection:
            rows=connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events '
                'WHERE subject=? AND event_type=? AND json_extract(canonical_json,?)=? '
                'ORDER BY sequence DESC LIMIT ?',
                (self.host.subject,'autonomous.host.closed','$.payload.content_rejection.method',
                 'qualified-content-rejection-v2',limit)).fetchall()
        records=tuple(self.journal._record(row) for row in rows)
        held=[];seen=set()
        clearance=Sensitivity(parameters.get('sensitivity',Sensitivity.PRIVATE))
        for record in records:
            closed=self.host._validate(record.event)
            if closed['disposition']!='content_review_attention':continue
            payload=closed.get('content_rejection')
            if payload is None or 'content_rejection_retry_until' not in closed:continue
            opened=self.journal.get(record.event.causation_id)
            if opened is None:raise ValueError('rejection history lost its open cycle')
            original=self.host._validate(opened.event)
            if original['operation_id']!=closed['operation_id']:
                raise ValueError('rejection completion has a foreign open cycle')
            frontier=original.get('owner_event_frontier')
            if (original['configuration_id']!=self.host.configuration_id
                    or type(frontier) is not int or frontier<0
                    or owner[1]>frontier or owner[2]>frontier):continue
            until=datetime.fromisoformat(closed['content_rejection_retry_until'])
            if until.tzinfo is None or until.utcoffset() is None:
                raise ValueError('rejection retry boundary must be timezone aware')
            if not record.event.observed_at<=now<until:continue
            witness=self.preparation.restore_rejection(payload,{**parameters,
                'subject':self.host.subject,'operation_id':closed['operation_id']})
            if witness is None or until>witness.valid_until:continue
            review=self.journal.get(witness.review_event_id)
            if review is None or until>review.event.observed_at+timedelta(hours=1):continue
            candidate=self.preparation.expression.store.resolve_model_candidate(witness.expression_event_id)
            if candidate is None:continue
            frame=self.preparation.expression.planning.coordinator.deliberation.inspect(
                candidate.frame_id,clearance=clearance)
            if frame is None or frame.selection is None:continue
            sources=self.preparation.expression.planning.synth.reader.active_evidence(
                subject=self.host.subject,clearance=clearance,limit=32,
                observation_event_ids=witness.source_event_ids)
            primary=next((s for s in sources if s.agenda_item_id==frame.selection.candidate.agenda_item_id),None)
            if primary is None:continue
            url=canonicalize_discovery_url(primary.content['url'])
            if url not in seen:
                seen.add(url)
                held.append(HeldDiscovery(url,primary.observation_event_id,witness.review_event_id,until))
        if self._owner_inputs()!=owner:
            raise ValueError('owner inputs changed during eligibility capture')
        return RejectionEligibilityView(tuple(held),len(records)<limit)
