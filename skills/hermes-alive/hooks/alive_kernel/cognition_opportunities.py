"""Current discovery and user-admitted commitments in one bounded cognitive view.

Commitments remain agenda state, never web facts, completed work or action grants.
The established typed-agenda vault is explicit; no adjacent-vault probing occurs.
"""
from contextlib import closing
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
import json
import re

from .agenda import AgendaProjection, AgendaAuthority, AgendaState, _ALLOWED_TRANSITIONS
from .content_vault import ContentReference, ContentUnavailableError, ContentIntegrityError
from .discovery_opportunities import DiscoveryOpportunityIngestor, OpportunityEvidence
from .events import Sensitivity, _freeze_json


class CommitmentSummaryTooLarge(ValueError):
    code='alive_commitment_summary_too_large'


def commitment_summary(details,*,state,available_at,due_at,expires_at):
    """The same complete evidence window at admission and cognitive reading."""
    summary=json.dumps(dict(commitment=details,state=state,
        available_at=available_at,due_at=due_at,expires_at=expires_at,
        temporal_bounds=dict(not_before=available_at,target_deadline=due_at,active_until=expires_at)),ensure_ascii=False)
    if len(summary)>1800:raise CommitmentSummaryTooLarge('complete commitment does not fit the cognitive window')
    return summary


class CognitionOpportunityReader(DiscoveryOpportunityIngestor):
    def __init__(self, journal, *, content_vault=None, commitment_vault=None, communication_only=False):
        super().__init__(journal,content_vault=content_vault)
        self.commitment_vault = commitment_vault or AgendaProjection(journal).content_vault
        self.communication_only = communication_only

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
        if payload.get('authority')==AgendaAuthority.USER_DELEGATED.value:
            from .followup_intake import validates_proposal
            admitted=validates_proposal(self.journal,event)
        if not admitted and not (payload.get('authority')==AgendaAuthority.MODEL_PROPOSAL.value
                                 and event.actor.startswith('model:')):
            return None
        state = AgendaState.ACTIVE if admitted else AgendaState.PROPOSED
        available = payload.get('available_at')
        effective_content=payload['content']
        effective_due=payload.get('due_at')
        last_sequence = origin.sequence
        last_transition_event_id=event.event_id
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
            if change.event_type=='agenda.revised':
                from .agenda_revisions import validates
                amendment=change.payload.get('revision_binding',{})
                if (not isinstance(amendment,Mapping) or command.sequence<=last_sequence or transition['from_state']!=state.value
                        or transition['to_state']!=state.value
                        or amendment.get('available_at')!=available
                        or amendment.get('expires_at')!=payload.get('expires_at')
                        or not validates(self.journal,change,subject=subject,from_state=state.value,
                            prior_transition_event_id=last_transition_event_id)):
                    return None
                effective_content=amendment['content'];effective_due=amendment['due_at']
                last_sequence=command.sequence;last_transition_event_id=change.event_id
                continue
            target = AgendaState(transition['to_state'])
            source = self.journal.get(change.payload.get('source_event_id',''))
            if change.payload.get('authority')==AgendaAuthority.USER_DELEGATED.value:
                from .followup_intake import validates_transition
                authority_valid=validates_transition(self.journal,change,subject=subject,from_state=state.value)
            elif change.payload.get('authority')==AgendaAuthority.USER_DELEGATED_OUTCOME.value:
                from .core_work_outcomes import validates_transition
                authority_valid=validates_transition(self.journal,change,subject=subject,from_state=state.value,
                    prior_transition_event_id=last_transition_event_id)
            else:
                authority_valid=(change.payload.get('authority')==AgendaAuthority.USER_EXPLICIT.value
                    and change.actor==subject and source is not None
                    and source.event.event_type=='conversation.inbound' and source.event.actor==subject
                    and source.event.subject==subject)
            if (command.sequence<=last_sequence or change.event_type!='agenda.transitioned'
                    or change.source!='alive.agenda'
                    or change.payload.get('item_id')!=row['item_id']
                    or change.payload.get('to_state')!=target.value or transition['from_state']!=state.value
                    or target not in _ALLOWED_TRANSITIONS[state]
                    or not authority_valid
                    or source is None or source.sequence>=command.sequence
                    ):
                return None
            state,available,last_sequence = target,change.payload.get('available_at'),command.sequence
            last_transition_event_id=change.event_id
            admitted = True
        if (not admitted or state not in (AgendaState.ACTIVE,AgendaState.SNOOZED)
                or row['state']!=state.value or row['available_at']!=available
                or row['due_at']!=effective_due or row['expires_at']!=payload.get('expires_at')):
            return None
        ref = ContentReference.from_event_payload(effective_content)
        if ref.content_id!=row['content_id'] or ref.sensitivity is not event.sensitivity:
            return None
        try:
            details = self.commitment_vault.resolve_json(ref.content_id,expected_subject=subject,
                expected_purpose='agenda.commitment',expected_sensitivity=event.sensitivity)
        except (ContentUnavailableError,ContentIntegrityError):
            return None
        if self.commitment_vault.digest_json(details)!=ref.digest:
            return None
        try:
            summary=commitment_summary(details,state=state.value,available_at=available,
                due_at=effective_due,expires_at=payload.get('expires_at'))
        except CommitmentSummaryTooLarge:
            return None  # Historical oversized items are not silently truncated.
        expiry = datetime.max.replace(tzinfo=timezone.utc)
        for value in (payload.get('expires_at'),ref.retention_until):
            if value:
                expiry=min(expiry,datetime.fromisoformat(value) if isinstance(value,str) else value)
        if effective_due:
            due=datetime.fromisoformat(effective_due)
            if due>now: expiry=min(expiry,due)
        if expiry<=now:
            return None
        from .followup_intake import item_source_view
        from .kernel_setup import KernelSetupStore
        source_view=(item_source_view(KernelSetupStore(self.journal.path.parent,journal=self.journal),
            row['item_id'],subject=subject,include_message=True)
            if payload.get('authority')==AgendaAuthority.USER_DELEGATED.value else
            {'original_source_available':False,'original_owner_message_included':False,
             'owner_updates_allowed':details.get('notify_owner',True) is True})
        # Private work remains available to task and memory reasoning. Only the
        # communication reader excludes it, including recovery before dispatch.
        # Historical explicitly confirmed reminders retain their confirmation;
        # old delegated records without a signed choice do not gain contact scope.
        if self.communication_only and source_view.get('owner_updates_allowed') is not True:
            return None
        return OpportunityEvidence(row['item_id'],event.event_id,expiry,event.sensitivity,
            _freeze_json(dict(source='user-admitted agenda commitment',title='Current commitment',url='',
                summary=summary,published_at=None,origin_kind='commitment',
                details_origin='agenda_description_not_verified_verbatim',**source_view,
                original_proposal_authority=payload.get('authority'),
                literal_owner_confirmation=payload.get('authority')==AgendaAuthority.USER_EXPLICIT.value,
                authority_is_not_execution_permission=True)))

    def active_evidence(self, *, subject, clearance, limit=8, observation_event_ids=None, source_cursor=None):
        if (not isinstance(subject,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}',subject)
                or type(limit) is not int or not 1<=limit<=32):
            raise ValueError('invalid cognitive opportunity scope')
        clearance=Sensitivity(clearance)
        if observation_event_ids==():
            return ()
        discoveries = super().active_evidence(subject=subject,clearance=clearance,limit=limit,
                                              observation_event_ids=observation_event_ids,source_cursor=source_cursor)
        commitments=self.commitments(subject=subject,clearance=clearance,limit=limit,
                                     observation_event_ids=observation_event_ids)
        if observation_event_ids is not None:
            by_id={e.observation_event_id:e for e in (*discoveries,*commitments)}
            return tuple(by_id[e] for e in observation_event_ids if e in by_id)
        return self._merge_candidate_evidence(discoveries,commitments,limit,source_cursor)

    def candidate_evidence(self,*,subject,clearance,limit=8,excluded_urls=(),source_cursor=None):
        discoveries=super().candidate_evidence(subject=subject,clearance=clearance,limit=limit,
            excluded_urls=excluded_urls,source_cursor=source_cursor)
        commitments=self.commitments(subject=subject,clearance=clearance,limit=limit)
        return self._merge_candidate_evidence(discoveries,commitments,limit,source_cursor)

    @staticmethod
    def _merge_candidate_evidence(discoveries,commitments,limit,source_cursor):
        if not discoveries:
            return commitments[:limit]
        reserved=min(len(commitments),max(1,limit//2))
        if source_cursor is not None:
            combined=[]
            for index in range(max(reserved,len(discoveries))):
                if index<reserved: combined.append(commitments[index])
                if index<len(discoveries): combined.append(discoveries[index])
            return tuple((*combined,*commitments[reserved:]))[:limit]
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
            from .core_work import owns_commitment
            value=self._commitment(row,subject=subject,now=now)
            if value is not None and owns_commitment(self.journal,subject=subject,item_id=row['item_id']):
                from .core_work import CoreWorkStore
                from .kernel_setup import KernelSetupStore
                work=CoreWorkStore(KernelSetupStore(self.journal.path.parent,journal=self.journal))
                observation=work.current_observation(row['item_id'],subject=subject)
                if observation is None:continue  # Never ask the user to do handed-off work.
                event_id,status=observation
                review=work.review_evidence(status,subject=subject)
                configured=work.store.configuration()
                from .core_work_outcomes import CoreWorkOutcomes
                assessment=(CoreWorkOutcomes(work.store).view(status['work_id'],configured)
                    if configured is not None and configured.options.get('manage_core_work_outcomes') is True else None)
                value=replace(value,observation_event_id=event_id,content=_freeze_json({
                    **dict(value.content),'source':'Core-owned work lifecycle observation',
                    'title':'Ongoing delegated work','core_work':status,
                    **({'core_work_outcome':assessment} if assessment is not None else {}),
                    **({'core_work_record_review':review} if review is not None else {})}))
            if value is not None:
                from .kernel_setup import KernelSetupStore
                try:setup=KernelSetupStore(self.journal.path.parent,journal=self.journal)
                except (ValueError,OSError,RuntimeError):setup=None
                configured=setup.configuration() if setup is not None else None
                if configured is not None and configured.subject==subject and configured.options.get('autonomous_core_work') is True:
                    from .core_autonomous_work import CoreAutonomousWork
                    waiting=CoreAutonomousWork(setup).wait_evidence(row['item_id'],configured)
                    if waiting is not None:value=replace(value,content=_freeze_json({
                        **dict(value.content),'autonomous_work_wait':waiting}))
            if value is not None and observation_event_ids is not None and value.observation_event_id not in observation_event_ids:
                continue
            if value is not None:
                commitments.append(value)
                if len(commitments)==limit: break
        return tuple(commitments)
