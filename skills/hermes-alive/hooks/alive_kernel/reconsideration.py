"""Bounded change-sensitive reuse of verified silence, never action or FIFO."""
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import re

from .events import EventEnvelope, Sensitivity, _thaw_json


@dataclass(frozen=True, slots=True)
class ReconsiderationContext:
    semantic_digest: str
    owner_frontier: int
    valid_until: datetime


class ReconsiderationStore:
    METHOD = 'alive-reconsideration-v3'
    EVENT = 'cognition.wait_recorded'

    def __init__(self, preparation, protector, *, clock=None):
        self.preparation = preparation
        self.synth = preparation.expression.planning.synth
        self.journal = self.synth.journal
        self.protector = protector
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def now(self):
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('reconsideration clock must be timezone aware')
        return now.astimezone(timezone.utc)

    def capture(self, *, subject, configuration_id, execute, policy, parameters, window_seconds,
                listing_fingerprint=None):
        if (not isinstance(configuration_id, str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}', configuration_id)
                or type(window_seconds) is not int or not 1 <= window_seconds <= 3600
                or listing_fingerprint is not None and (not isinstance(listing_fingerprint,str)
                    or not re.fullmatch(r'[0-9a-f]{64}',listing_fingerprint))):
            raise ValueError('bounded reconsideration needs explicit host configuration')
        clearance = Sensitivity(parameters.get('sensitivity', Sensitivity.PRIVATE))
        now = self.now()
        evidence = self.synth.reader.active_evidence(subject=subject, clearance=clearance, limit=32,
            source_cursor=self.synth._source_cursor(subject,clearance))
        # A completed scan may rotate the same fair window. Its order is not
        # new evidence; different window membership/content still wakes us.
        evidence=tuple(sorted(evidence,key=lambda item:item.observation_event_id))
        readers = (self.synth.context_reader, self.synth.learning_reader, self.synth.history_reader,
                   self.synth.action_reader, self.synth.feedback_reader)
        # Callback identity cannot certify model routing. Host configuration must
        # change when callback semantics or effective inherited routing changes.
        options = {k:v for k,v in parameters.items() if k not in
                   ('call', 'resolve_domain', 'resolve_grounding_domain', 'read_context', 'operation_id', 'subject', 'policy_context')}
        scope=options.get('candidate_material_scope')
        if scope is not None and scope.get('method')=='bound-material-pool-v2':
            # IDs/order/eligibility remain semantic; the original cursor and
            # sequence ceiling are still verified on retained plan replay.
            options['candidate_material_scope']={k:v for k,v in scope.items() if k not in ('origin_frontier','cursor')}
        state = dict(method=self.METHOD, subject=subject, configuration=configuration_id,
            window_seconds=window_seconds,
            execute=execute, policy_event=policy.event_id, policy={**asdict(policy.context),
                'allowed_side_effects':sorted(s.value for s in policy.context.allowed_side_effects)},
            options=options, evidence=[dict(event=e.observation_event_id,
                content=_thaw_json(e.content), expires_at=e.expires_at.isoformat()) for e in evidence],
            context=[[c.to_prompt() for c in reader.read(subject=subject, clearance=clearance)]
                     for reader in readers])
        if listing_fingerprint is not None:state['listing_fingerprint']=listing_fingerprint
        with closing(self.journal._connect()) as connection:
            # Observe new inbound even before memory/feedback projection. Do not
            # read private message bodies merely to decide whether to wake up.
            inbound = connection.execute('SELECT MAX(sequence) FROM experience_events WHERE subject=? AND event_type=?',
                (subject, 'conversation.inbound')).fetchone()[0]
            ignored=(self.EVENT,'autonomous.host.opened','autonomous.host.closed')
            if listing_fingerprint is not None:
                # Only the already-observed listing protocol's control records
                # are non-semantic. New source versions, failures, inbound,
                # memory, feedback and unknown events still wake the owner.
                ignored+=('discovery.host_read_started','discovery.host_read_completed',
                    'discovery.research_cycle_opened','discovery.citation_selection_opened',
                    'discovery.research_group_opened','discovery.reading_assessment_opened')
            frontier = connection.execute('SELECT MAX(sequence) FROM experience_events WHERE subject=? AND event_type NOT IN ('+
                ','.join('?' for _ in ignored)+')',(subject,*ignored)).fetchone()[0]
            allowed = tuple(s.value for s in Sensitivity)[:tuple(Sensitivity).index(clearance)+1]
            placeholders = ','.join('?' for _ in allowed)
            deadlines = connection.execute('SELECT item_id,state,available_at,due_at,expires_at FROM agenda_items_v1 '
                'WHERE subject=? AND state IN (?,?) AND sensitivity IN ('+placeholders+') '
                'AND (expires_at IS NULL OR expires_at>?) ORDER BY item_id LIMIT 129',
                (subject, 'active', 'snoozed', *allowed,now.isoformat())).fetchall()
        state['inbound_sequence'] = inbound or 0
        state['agenda_boundaries'] = [list(row) for row in deadlines]
        # A bounded incomplete agenda must not silently claim no upcoming deadline.
        valid_until = now + timedelta(seconds=window_seconds)
        if len(deadlines)>128:
            valid_until = now
        for row in deadlines:
            for value in row[2:]:
                if value:
                    boundary = datetime.fromisoformat(value)
                    if now < boundary < valid_until:
                        valid_until = boundary
        for item in evidence:
            valid_until = min(valid_until, item.expires_at)
        recalled=parameters.get('recalled_feedback_event_ids',())
        if recalled:
            pairs=self.synth.feedback_reader.context(subject=subject,clearance=clearance,recalled_ids=recalled)
            state['exact_recalled_feedback']=[v.to_prompt() for v in pairs]
            valid_until=min(valid_until,*(datetime.fromisoformat(v.retention_until) for v in pairs))
        if parameters.get('semantic_feedback_recall') is True:
            from .feedback_recall import FeedbackRecallSelector
            pages=[]
            for window in FeedbackRecallSelector(self.synth.feedback_reader).windows(subject=subject,clearance=clearance):
                page=window['page']
                pages.append(self.synth.vault.digest_json(page))
                for entry in page['entries']:
                    valid_until=min(valid_until,datetime.fromisoformat(entry['retention_until']))
            # Include content availability, not merely unchanged reference IDs.
            # Match the selector's bounded horizon; this is not all-life recall.
            state['semantic_feedback_archive']=pages
        digest = self.protector.authenticate_json(self.METHOD+'.context', state)
        return ReconsiderationContext(digest, int(frontier or 0), valid_until)

    def current(self, *, subject, configuration_id, context):
        records = self.journal.iter_reverse(event_types=(self.EVENT,), subject=subject, max_records=1)
        record = next(iter(records), None)
        if record is None:
            return None
        event = record.event
        payload = _thaw_json(event.payload)
        signature = payload.pop('integrity_authenticator', None)
        method = payload.get('method')
        if method not in ('alive-reconsideration-v1','alive-reconsideration-v2',self.METHOD):
            raise ValueError('unknown reconsideration history method')
        identity = self.protector.authenticate_json(method+'.identity',
            dict(subject=subject,configuration_id=payload.get('configuration_id'),
                 operation_id=payload.get('operation_id')))
        if (event.source!='alive.reconsideration' or event.actor!='system:alive-runtime'
                or event.event_id!='cognition-wait:'+identity
                or event.sensitivity is not Sensitivity.PRIVATE
                or payload.get('subject')!=subject
                or event.causation_id!=payload.get('selection_event_id')
                or not self.protector.verify_json(self.EVENT+'.v1',payload,signature)):
            raise ValueError('reconsideration history lacks canonical provenance')
        now = self.now()
        if (payload['configuration_id']!=configuration_id or payload['method']!=self.METHOD
                or payload['semantic_digest']!=context.semantic_digest
                or payload['owner_frontier']!=context.owner_frontier
                or not event.observed_at <= now < datetime.fromisoformat(payload['valid_until'])
                or datetime.fromisoformat(payload['valid_until']) > context.valid_until
                or context.valid_until <= now):
            return None
        return record

    def timing(self, planning, *, subject):
        """Bind internal revisit suggestions to retained source-linked decisions."""
        values = []
        for receipt_id in (planning.interpretation_event_id,planning.repair_interpretation_event_id):
            if receipt_id is None:
                continue
            record = self.journal.get(receipt_id)
            if record is None or record.event.subject!=subject:
                raise ValueError('reconsideration interpretation unavailable or foreign')
            operation = receipt_id.removeprefix('opportunity.synthesis:').removesuffix(':completed')
            result = self.synth.load_completed(subject=subject,operation_id=operation,
                                              clearance=record.event.sensitivity)
            for hint in result.reconsiderations:
                values.append(dict(interpretation_event_id=receipt_id,agenda_item_id=hint.agenda_item_id,
                    observation_event_id=hint.observation_event_id,reconsider_at=hint.reconsider_at.isoformat()))
        return values

    def remember(self, *, subject, configuration_id, before, after, planning):
        if (planning.action_kind!='silence' or before.semantic_digest!=after.semantic_digest
                or min(before.valid_until,after.valid_until) <= self.now()):
            return None
        timing = self.timing(planning,subject=subject)
        deadline = min([before.valid_until,after.valid_until]+
                       [datetime.fromisoformat(h['reconsider_at']) for h in timing])
        if deadline<=self.now():
            # An already-due suggestion cannot restart its relative countdown.
            return None
        payload = dict(method=self.METHOD, subject=subject, configuration_id=configuration_id,
            semantic_digest=after.semantic_digest, owner_frontier=after.owner_frontier,
            valid_until=deadline.isoformat(),timing=timing,
            operation_id=planning.operation_id, selection_event_id=planning.selection_event_id,
            authority_granted=False)
        identity = self.protector.authenticate_json(self.METHOD+'.identity',
            dict(subject=subject,configuration_id=configuration_id,operation_id=planning.operation_id))
        existing = self.journal.get('cognition-wait:'+identity)
        if existing is not None:
            # Reopening an old completion never extends its reconsideration window.
            return existing
        payload['integrity_authenticator'] = self.protector.authenticate_json(self.EVENT+'.v1', payload)
        return self.journal.append(EventEnvelope(event_id='cognition-wait:'+identity,
            event_type=self.EVENT, source='alive.reconsideration', actor='system:alive-runtime',
            subject=subject, sensitivity=Sensitivity.PRIVATE,
            causation_id=planning.selection_event_id, payload=payload))
