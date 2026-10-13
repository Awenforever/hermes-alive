"""Bind natural shadow expression to an unchanged selected opportunity draft."""
from datetime import datetime, timedelta, timezone

from .action_contract import parse_action_contract
from .content_vault import ContentReference
from .deliberation import ActionKind, SideEffect
from .deliberation_synthesis import DeliberationSynthesizer
from .events import _thaw_json
from .opportunity_synthesis import OpportunitySynthesizer
from .semantic_rendering import (MeaningDocument, MessageSpeechAct, SemanticAtom,
                                 SemanticAtomKind, SemanticRenderingError)
from .semantic_review import SemanticReviewError, SemanticReviewStore


class OpportunityExpressionStore(SemanticReviewStore):
    """A draft is a proposed message, not a fact, replacement intent or send grant.

    The original frame/action contract remains immutable. This specialized store
    verifies the selection-to-meaning binding whenever a candidate or review is
    created/resolved, including comparator async boundaries. No dispatch exists.
    """

    def __init__(self, journal, *, content_vault=None, context_vault=None, protector=None):
        super().__init__(journal, content_vault=content_vault, protector=protector)
        self.context_vault = context_vault

    def _selected_draft(self, selection_event_id, subject):
        source = self.journal.get(selection_event_id)
        if (source is None or source.event.event_type != 'deliberation.selected'
                or source.event.subject != subject):
            raise SemanticReviewError('selected opportunity is missing or foreign')
        frame_id = str(source.event.payload.get('frame_id') or '')
        self.deliberation.project_new()
        if self.deliberation.latest_selection_event_id(frame_id) != selection_event_id:
            raise SemanticReviewError('opportunity is no longer the current intent')
        stored = self.deliberation.inspect(frame_id, clearance=source.event.sensitivity)
        if stored is None or stored.selection is None:
            raise SemanticReviewError('selected opportunity is unavailable')
        candidate = stored.selection.candidate
        if (candidate.action_kind not in (ActionKind.SHARE, ActionKind.ASK)
                or candidate.side_effect is not SideEffect.COMMUNICATION
                or not candidate.candidate_id.startswith('opportunity-candidate:')):
            raise SemanticReviewError('selection is not a generated communication draft')
        try:
            DeliberationSynthesizer(self.journal, content_vault=self.content_vault,
                context_vault=self.context_vault).validate_candidate_sources(
                    (candidate,), dict(stored.candidate_contents), subject, source.event.sensitivity)
            contract = parse_action_contract(
                _thaw_json(dict(stored.candidate_contents)[candidate.content_id]),
                capability='hermes.channel.send')
            evidence = tuple(dict.fromkeys((selection_event_id, *(e
                for name in ('user_value','urgency','novelty','confidence','risk','interruption_cost')
                for e in getattr(candidate.dimensions, name).evidence_event_ids))))
            completed = next(e for e in evidence
                if e.startswith('opportunity.synthesis:') and e.endswith(':completed'))
            receipt = self.journal.get(completed)
            expiry = ContentReference.from_event_payload(receipt.event.payload['content']).retention_until
            original_start = self.journal.get(receipt.event.causation_id)
            if (original_start is None or original_start.event.subject != subject
                    or original_start.event.event_type != 'opportunity.synthesis_started'):
                raise SemanticReviewError('original interpretation input is unavailable')
            # Current ranking is for new search, not revalidation of retained intent.
            active = OpportunitySynthesizer(self.journal, content_vault=self.content_vault,
                context_vault=self.context_vault).reader.active_evidence(
                    subject=subject, clearance=source.event.sensitivity, limit=8,
                    observation_event_ids=tuple(original_start.event.payload['observation_event_ids']))
            original_url = next(item.content['url'] for item in active
                                if item.agenda_item_id == candidate.agenda_item_id)
            text = str(contract.operation['text'])
            literals = (original_url,) if original_url and original_url in text else ()
        except Exception:
            raise SemanticReviewError('original opportunity evidence is unavailable') from None
        if expiry is None or expiry <= datetime.now(timezone.utc):
            raise SemanticReviewError('original opportunity draft expired')
        atom = SemanticAtom('proposed-message', SemanticAtomKind.PROPOSED_CONTENT,
                            text, evidence, literals)
        return source, stored, atom, expiry

    def _message_id(self, selection_event_id):
        return 'selected-opportunity:' + self.content_vault.digest_json(
            {'selection_event_id': selection_event_id})[:40]

    def action_contract_for_expression(self, *, expression_event_id,
                                       selection_event_id, subject, as_of=None):
        """Resolve exact proposed wording, never infer approval from a review.

        The caller must require explicit confirmation of this expression event.
        Model fidelity assessments are not qualified automatic delivery gates.
        """
        header = self.journal.get(expression_event_id)
        selection = self.journal.get(selection_event_id)
        if (header is None or selection is None
                or header.event.subject != subject or selection.event.subject != subject
                or header.event.sensitivity != selection.event.sensitivity):
            raise SemanticReviewError('expression scope unavailable')
        candidate = self.resolve_model_candidate(expression_event_id, as_of=as_of)
        if candidate is None or candidate.selection_event_id != selection_event_id:
            raise SemanticReviewError('expression is unavailable or belongs to another intent')
        return parse_action_contract({'schema_version': 1,
            'capability': 'hermes.channel.send',
            'operation': {'text': candidate.text, 'format': 'markdown'}},
            capability='hermes.channel.send'), candidate.expires_at

    def define_for_selection(self, *, selection_event_id, subject):
        source, stored, atom, expiry = self._selected_draft(selection_event_id, subject)
        message_id = self._message_id(selection_event_id)
        event_id = 'message.meaning:' + message_id
        existing = self.journal.get(event_id)
        if existing is not None:
            self._selection_context(selection_event_id=selection_event_id,
                meaning_event_id=event_id, subject=subject, observed_at=datetime.now(timezone.utc))
            return existing
        now = datetime.now(timezone.utc)
        speech = (MessageSpeechAct.SHARE if stored.selection.candidate.action_kind is ActionKind.SHARE
                  else MessageSpeechAct.ASK)
        document = MeaningDocument(message_id, subject, speech, (atom,), now,
            min(expiry, now + timedelta(hours=1)), source.event.sensitivity)
        record = self.meanings.define(document, actor='system:alive-opportunity-expression', observed_at=now)
        self._selection_context(selection_event_id=selection_event_id,
            meaning_event_id=record.event.event_id, subject=subject, observed_at=now)
        return record

    def _selection_context(self, *, selection_event_id, meaning_event_id, subject, observed_at):
        source, stored, atom, expiry = self._selected_draft(selection_event_id, subject)
        message_id = self._message_id(selection_event_id)
        record = self.journal.get(meaning_event_id)
        # Scope checked before decrypting retained meaning.
        if (record is None or record.event.subject != subject
                or record.event.event_type != 'message.meaning_defined'
                or record.event.actor != 'system:alive-opportunity-expression'
                or record.event.payload.get('message_id') != message_id
                or record.event.sensitivity is not source.event.sensitivity):
            raise SemanticReviewError('meaning does not bind this selected opportunity')
        try:
            document = self.meanings.resolve(meaning_event_id)
        except SemanticRenderingError:
            raise SemanticReviewError('bound opportunity meaning is unavailable') from None
        speech = (MessageSpeechAct.SHARE if stored.selection.candidate.action_kind is ActionKind.SHARE
                  else MessageSpeechAct.ASK)
        if (document.message_id != message_id or document.subject != subject
                or document.speech_act is not speech or document.atoms != (atom,)
                or document.expires_at > expiry
                or document.created_at < source.event.observed_at
                or observed_at < document.created_at or observed_at >= document.expires_at):
            raise SemanticReviewError('selected draft and expression meaning diverged')
        return source, document, stored.frame.frame_id, stored.selection.candidate.candidate_id
