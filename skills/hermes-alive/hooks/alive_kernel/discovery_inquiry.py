"""Tentative reading purposes in the existing encrypted agenda, not user memory.

The host pins tasks explicitly. Nothing here grants a search, a private-data
disclosure, a commitment or a send. Revision means a new proposal and withdrawal
of the old one, never rewriting the question behind a completed interpretation.
"""
from collections.abc import Mapping
from datetime import datetime, timezone
import re

from .agenda import (AgendaAuthority, AgendaContentStatus, AgendaItemKind,
                     AgendaProposal, AgendaState)
from .content_vault import ContentReference
from .events import Sensitivity, _thaw_json
from .native_worker_protocol import identifier


class DiscoveryInquiryError(ValueError):
    pass


class DiscoveryInquiryContext:
    def __init__(self, reader, *, context_vault=None):
        self.reader = reader
        self.agenda = reader.agenda
        self.journal = reader.journal
        self.vault = reader.vault
        from .cognition_context import CognitionContextReader
        self.owner_context = CognitionContextReader(self.journal,content_vault=context_vault)

    def context_digest(self, *, subject, clearance=Sensitivity.PRIVATE):
        return self.vault.digest_json([c.to_prompt() for c in
            self.owner_context.read(subject=subject,clearance=clearance)])

    @staticmethod
    def identities(item_ids):
        if (not isinstance(item_ids, tuple) or len(item_ids) > 4
                or any(not isinstance(i, str) for i in item_ids)
                or len(set(item_ids)) != len(item_ids)):
            raise DiscoveryInquiryError('invalid pinned reading tasks')
        for item_id in item_ids:
            identifier(item_id)
        return item_ids

    def remember(self, *, item_id, subject, question, value_hypothesis,
                 source_event_ids, model_actor, expires_at, expected_context_digest):
        """Record a settled model choice, without calling a model or executing IO."""
        self.identities((item_id,))
        if (not isinstance(expected_context_digest,str)
                or not re.fullmatch(r'[0-9a-f]{64}',expected_context_digest)
                or expected_context_digest != self.context_digest(subject=subject)):
            raise DiscoveryInquiryError('owner context changed since reading choice')
        if (not isinstance(model_actor, str) or not model_actor.startswith('model:')
                or not model_actor[6:] or not isinstance(question, str)
                or not 1 <= len(question.strip()) <= 1200
                or not isinstance(value_hypothesis, str)
                or not 1 <= len(value_hypothesis.strip()) <= 1200
                or not isinstance(source_event_ids, tuple) or not 1 <= len(source_event_ids) <= 4
                or len(set(source_event_ids)) != len(source_event_ids)
                or not isinstance(expires_at, datetime) or expires_at.tzinfo is None
                or expires_at <= datetime.now(timezone.utc)):
            raise DiscoveryInquiryError('invalid tentative reading purpose')
        evidence = self.reader.active_evidence(subject=subject, clearance=Sensitivity.PRIVATE,
            observation_event_ids=source_event_ids, limit=32)
        if {e.observation_event_id for e in evidence} != set(source_event_ids):
            raise DiscoveryInquiryError('reading task sources are not current')
        if expires_at > min(e.expires_at for e in evidence):
            raise DiscoveryInquiryError('reading task cannot outlive its sources')
        proposal = AgendaProposal(item_id=item_id, kind=AgendaItemKind.OPPORTUNITY,
            subject=subject, authority=AgendaAuthority.MODEL_PROPOSAL,
            details=dict(context_kind='discovery-inquiry-v2', question=question,
                         value_hypothesis=value_hypothesis,
                         owner_context_digest=expected_context_digest),
            source_event_ids=source_event_ids, confidence=.5, expires_at=expires_at)
        record = self.agenda.append_proposal(proposal, actor=model_actor,
            correlation_id='inquiry-context:'+expected_context_digest)
        self.agenda.apply(record)
        return self.read(subject=subject, clearance=Sensitivity.PRIVATE, item_ids=(item_id,))[0]

    def read(self, *, subject, clearance, item_ids=()):
        self.identities(item_ids)
        if not item_ids:
            return []
        current_context_digest = self.context_digest(subject=subject,clearance=clearance)
        # Check the context revision before the agenda decrypts derived text.
        for item_id in item_ids:
            origin = self.journal.get('agenda.proposal:'+item_id)
            if (origin is None or origin.event.subject != subject
                    or origin.event.correlation_id != 'inquiry-context:'+current_context_digest):
                raise DiscoveryInquiryError('reading task lacks current owner-context provenance')
        # Use the existing agenda checkpoint, not a second task projection.
        target = self.journal.last_sequence()
        while self.journal.checkpoint(self.agenda.CHECKPOINT) < target:
            before = self.journal.checkpoint(self.agenda.CHECKPOINT)
            self.agenda.project_new(limit=1000)
            if self.journal.checkpoint(self.agenda.CHECKPOINT) <= before:
                raise DiscoveryInquiryError('reading task projection made no progress')
        items = self.agenda.list_items(subject=subject, clearance=clearance,
            kinds=(AgendaItemKind.OPPORTUNITY,), states=(AgendaState.ACTIVE,),
            item_ids=item_ids, limit=4)
        by_id = {item.item_id: item for item in items}
        result = []
        for item_id in item_ids:
            item = by_id.get(item_id)
            origin = self.journal.get('agenda.proposal:' + item_id)
            if item is None or origin is None:
                raise DiscoveryInquiryError('reading task withdrawn, expired or outside owner scope')
            event, payload = origin.event, origin.event.payload
            details = _thaw_json(item.details)
            if (event.event_type != 'agenda.proposed' or event.source != 'alive.agenda'
                    or event.subject != subject or not event.actor.startswith('model:')
                    or not event.actor[6:] or event.sensitivity is not item.sensitivity
                    or payload.get('subject') != subject or payload.get('item_id') != item_id
                    or payload.get('kind') != AgendaItemKind.OPPORTUNITY.value
                    or payload.get('authority') != AgendaAuthority.MODEL_PROPOSAL.value
                    or item.authority is not AgendaAuthority.MODEL_PROPOSAL
                    or item.content_status is not AgendaContentStatus.AVAILABLE
                    or not isinstance(details, Mapping)
                    or set(details) != {'context_kind', 'question', 'value_hypothesis', 'owner_context_digest'}
                    or details.get('context_kind') != 'discovery-inquiry-v2'
                    or any(not isinstance(details.get(k), str) or not 1 <= len(details[k].strip()) <= 1200
                           for k in ('question', 'value_hypothesis'))):
                raise DiscoveryInquiryError('reading task provenance unavailable')
            if details['owner_context_digest'] != current_context_digest:
                raise DiscoveryInquiryError('reading task owner context changed or was forgotten')
            ref = ContentReference.from_event_payload(payload['content'])
            sources = tuple(payload.get('source_event_ids', ()))
            if (ref.content_id != 'agenda:' + item_id or ref.content_id != item.content_id
                    or ref.sensitivity is not item.sensitivity
                    or ref.digest != self.vault.digest_json(details)
                    or not 1 <= len(sources) <= 4 or len(set(sources)) != len(sources)
                    or tuple(sorted(sources)) != item.source_event_ids
                    or payload.get('sensitivity') != item.sensitivity.value
                    or item.expires_at is None or ref.retention_until != item.expires_at
                    or payload.get('expires_at') != item.expires_at.isoformat()):
                raise DiscoveryInquiryError('reading task content binding changed')
            evidence = self.reader.active_evidence(subject=subject, clearance=clearance,
                observation_event_ids=sources, limit=32)
            if ({e.observation_event_id for e in evidence} != set(sources)
                    or any(self.journal.get(s).sequence >= origin.sequence for s in sources)):
                raise DiscoveryInquiryError('reading task source evidence no longer current')
            result.append(dict(item_id=item_id, proposal_event_id=event.event_id,
                model_actor=event.actor, source_event_ids=list(sources),
                question=details['question'], value_hypothesis=details['value_hypothesis'],
                owner_context_digest=details['owner_context_digest'],
                updated_at=item.updated_at.isoformat(), expires_at=item.expires_at.isoformat(),
                authority='tentative_model_note_not_user_instruction', revisable_after_reading=True,
                grants_execution_or_disclosure=False))
        return result
