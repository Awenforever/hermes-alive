"""Current discovery and user-admitted commitments in one bounded cognitive view.

Commitments remain agenda state, never web facts, completed work or action grants.
The established typed-agenda vault is explicit; no adjacent-vault probing occurs.
"""
from contextlib import closing
from datetime import datetime, timezone
import json
import re

from .agenda import AgendaProjection, AgendaAuthority, AgendaState, _ALLOWED_TRANSITIONS
from .content_vault import ContentReference, ContentUnavailableError, ContentIntegrityError
from .discovery_opportunities import DiscoveryOpportunityIngestor, OpportunityEvidence
from .events import Sensitivity, _freeze_json


class CognitionOpportunityReader(DiscoveryOpportunityIngestor):
    def __init__(self, journal, *, content_vault=None, commitment_vault=None):
        super().__init__(journal,content_vault=content_vault)
        self.commitment_vault = commitment_vault or AgendaProjection(journal).content_vault

    def _commitment(self, row, *, subject, now):
        origin = self.journal.get(row['proposal_event_id'])
        if origin is None:
            return None
        event,payload = origin.event,origin.event.payload
        if (event.event_type!='agenda.proposed' or event.source!='alive.agenda'
                or event.event_id!='agenda.proposal:'+row['item_id'] or event.subject!=subject
                or payload.get('subject')!=subject or payload.get('kind')!='commitment'
                or payload.get('item_id')!=row['item_id'] or event.sensitivity.value!=row['sensitivity']
                or payload.get('sensitivity')!=row['sensitivity']):
            return None
        sources = [self.journal.get(e) for e in payload.get('source_event_ids',())]
        if not sources or any(s is None or s.event.subject not in (None,subject) for s in sources):
            return None
        admitted = (payload.get('authority')==AgendaAuthority.USER_EXPLICIT.value and event.actor==subject
            and any(s.event.event_type=='conversation.inbound' and s.event.actor==subject and s.event.subject==subject
                    for s in sources))
        if not admitted and not (payload.get('authority')==AgendaAuthority.MODEL_PROPOSAL.value
                                 and event.actor.startswith('model:')):
            return None
        state = AgendaState.ACTIVE if admitted else AgendaState.PROPOSED
        available = payload.get('available_at')
        last_sequence = origin.sequence
        with closing(self.journal._connect()) as connection:
            transitions = connection.execute('SELECT * FROM agenda_transitions_v1 WHERE item_id=? ORDER BY transition_id LIMIT 65',
                (row['item_id'],)).fetchall()
        if not transitions or len(transitions)>64:
            return None
        initial=transitions[0]
        if initial['caused_by_event_id']!=event.event_id or initial['from_state'] is not None or initial['to_state']!=state.value:
            return None
        for transition in transitions[1:]:
            command = self.journal.get(transition['caused_by_event_id'])
            if command is None:
                return None
            change = command.event
            target = AgendaState(transition['to_state'])
            source = self.journal.get(change.payload.get('source_event_id',''))
            if (command.sequence<=last_sequence or change.event_type!='agenda.transitioned'
                    or change.source!='alive.agenda' or change.actor!=subject
                    or change.payload.get('item_id')!=row['item_id']
                    or change.payload.get('to_state')!=target.value or transition['from_state']!=state.value
                    or target not in _ALLOWED_TRANSITIONS[state]
                    or change.payload.get('authority')!=AgendaAuthority.USER_EXPLICIT.value
                    or source is None or source.sequence>=command.sequence
                    or source.event.event_type!='conversation.inbound' or source.event.actor!=subject
                    or source.event.subject!=subject):
                return None
            state,available,last_sequence = target,change.payload.get('available_at'),command.sequence
            admitted = True
        if (not admitted or state not in (AgendaState.ACTIVE,AgendaState.SNOOZED)
                or row['state']!=state.value or row['available_at']!=available
                or row['due_at']!=payload.get('due_at') or row['expires_at']!=payload.get('expires_at')):
            return None
        ref = ContentReference.from_event_payload(payload['content'])
        if ref.content_id!=row['content_id'] or ref.sensitivity is not event.sensitivity:
            return None
        try:
            details = self.commitment_vault.resolve_json(ref.content_id,expected_subject=subject,
                expected_purpose='agenda.commitment',expected_sensitivity=event.sensitivity)
        except (ContentUnavailableError,ContentIntegrityError):
            return None
        if self.commitment_vault.digest_json(details)!=ref.digest:
            return None
        summary = json.dumps(dict(commitment=details,state=state.value,available_at=available,
            due_at=payload.get('due_at'),expires_at=payload.get('expires_at'),
            temporal_bounds=dict(not_before=available,target_deadline=payload.get('due_at'),
                                 active_until=payload.get('expires_at'))),ensure_ascii=False)
        if len(summary)>1800:
            return None  # Never silently cut a commitment's condition or negation.
        expiry = datetime.max.replace(tzinfo=timezone.utc)
        for value in (payload.get('expires_at'),ref.retention_until):
            if value:
                expiry=min(expiry,datetime.fromisoformat(value) if isinstance(value,str) else value)
        if payload.get('due_at'):
            due=datetime.fromisoformat(payload['due_at'])
            if due>now: expiry=min(expiry,due)
        if expiry<=now:
            return None
        return OpportunityEvidence(row['item_id'],event.event_id,expiry,event.sensitivity,
            _freeze_json(dict(source='user-admitted agenda commitment',title='Current commitment',url='',
                summary=summary,published_at=None,origin_kind='commitment',
                authority_is_not_execution_permission=True)))

    def active_evidence(self, *, subject, clearance, limit=8, observation_event_ids=None):
        if (not isinstance(subject,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}',subject)
                or type(limit) is not int or not 1<=limit<=32):
            raise ValueError('invalid cognitive opportunity scope')
        clearance=Sensitivity(clearance)
        if observation_event_ids==():
            return ()
        discoveries = super().active_evidence(subject=subject,clearance=clearance,limit=limit,
                                              observation_event_ids=observation_event_ids)
        commitments=self.commitments(subject=subject,clearance=clearance,limit=limit,
                                     observation_event_ids=observation_event_ids)
        if observation_event_ids is not None:
            by_id={e.observation_event_id:e for e in (*discoveries,*commitments)}
            return tuple(by_id[e] for e in observation_event_ids if e in by_id)
        if not discoveries:
            return commitments[:limit]
        reserved=min(len(commitments),max(1,limit//2))
        combined=(*commitments[:reserved],*discoveries[:limit-reserved],*commitments[reserved:])
        return tuple(combined)[:limit]

    def commitments(self, *, subject, clearance, limit=32, observation_event_ids=None):
        # active_evidence projects the agenda before this bounded metadata reader.
        if (not isinstance(subject,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}',subject)
                or type(limit) is not int or not 1<=limit<=32):
            raise ValueError('invalid commitment reader scope')
        clearance=Sensitivity(clearance)
        allowed=tuple(s.value for s in Sensitivity)[:tuple(Sensitivity).index(clearance)+1]
        now=datetime.now(timezone.utc)
        with closing(self.journal._connect()) as connection:
            rows=connection.execute('SELECT * FROM agenda_items_v1 WHERE subject=? AND kind=? '
                'AND state IN (?,?) AND sensitivity IN ('+','.join('?' for _ in allowed)+') '
                'AND (available_at IS NULL OR available_at<=?) AND (expires_at IS NULL OR expires_at>?) '
                'ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,due_at,priority DESC,item_id LIMIT 128',
                (subject,'commitment','active','snoozed',*allowed,now.isoformat(),now.isoformat())).fetchall()
        commitments=[]
        for row in rows:
            if observation_event_ids is not None and row['proposal_event_id'] not in observation_event_ids:
                continue
            value=self._commitment(row,subject=subject,now=now)
            if value is not None:
                commitments.append(value)
                if len(commitments)==limit: break
        return tuple(commitments)
