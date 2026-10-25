"""Bind natural shadow expression to an unchanged selected opportunity draft."""
from datetime import datetime, timedelta, timezone

from .action_contract import parse_action_contract
from .content_vault import ContentReference
from .communication_plan import validate_communication_plan, plan_atoms, expression_context, validate_recipient_intent
from .host_discovery import source_prompt_excerpt, read_scope_metadata
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
            selected_content = _thaw_json(dict(stored.candidate_contents)[candidate.content_id])
            if 'recipient_intent_version' in selected_content:
                validate_recipient_intent(selected_content, action_kind=candidate.action_kind.value)
            else:
                parse_action_contract(selected_content, capability='hermes.channel.send')
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
                    subject=subject, clearance=source.event.sensitivity, limit=32,
                    observation_event_ids=tuple(original_start.event.payload['observation_event_ids']))
            original_url = next(item.content['url'] for item in active
                                if item.agenda_item_id == candidate.agenda_item_id)
            ref = ContentReference.from_event_payload(receipt.event.payload['content'])
            bundle = self.content_vault.resolve_json(ref.content_id, expected_subject=subject,
                expected_purpose='opportunity.candidates', expected_sensitivity=source.event.sensitivity)
            if self.content_vault.digest_json(bundle) != ref.digest:
                raise SemanticReviewError('original model proposal bundle changed')
            operation = completed.removeprefix('opportunity.synthesis:').removesuffix(':completed')
            indices = bundle.get('proposal_indices', tuple(range(len(bundle['proposals']))))
            original = next(raw for index, raw in zip(indices, bundle['proposals'])
                if 'opportunity-candidate:' + self.content_vault.digest_json(
                    {'operation': operation, 'index': index})[:40] == candidate.candidate_id)
            # Source-aware action presentation can exceed the 1600-character model
            # wording budget. Keep the original wording and canonical link as
            # separate atoms, not one oversized alleged model utterance.
            text = original.get('text')
            literals = (original_url,) if original_url and isinstance(text, str) and original_url in text else ()
        except Exception:
            raise SemanticReviewError('original opportunity evidence is unavailable') from None
        if expiry is None or expiry <= datetime.now(timezone.utc):
            raise SemanticReviewError('original opportunity draft expired')
        plan = original.get('communication_plan')
        if plan is not None:
            validate_communication_plan(plan, action_kind=candidate.action_kind.value)
            if plan['version'] == 3:
                selected_source = next(item for item in active if item.agenda_item_id == candidate.agenda_item_id)
                if selected_source.content.get('origin_kind','discovery') != 'discovery':
                    raise SemanticReviewError('editorial brief lacks discovery provenance')
            atoms = plan_atoms(plan, evidence=evidence)
        else:
            # Retained legacy proposals keep the exact old draft binding. Never
            # retroactively reinterpret a confirmed or historic draft as a plan.
            if not isinstance(text, str) or not text:
                raise SemanticReviewError('legacy proposal has no original draft')
            atoms = (SemanticAtom('proposed-message', SemanticAtomKind.PROPOSED_CONTENT,
                                 text, evidence, literals),)
        if original_url and not any(original_url in a.protected_literals for a in atoms):
            # Immutable selected wording remains the first atom. Provenance is
            # supplied by the host from canonical evidence, never guessed by the
            # renderer or conditional on the drafting model remembering a link.
            atoms += (SemanticAtom('source-link', SemanticAtomKind.LINK,
                                   original_url, evidence, (original_url,)),)
        return source, stored, atoms, expiry, plan

    def continuity_sources_for_selection(self, selection_event_id, subject):
        """Original, currently validated source references for a share snapshot.

        Called before submission, never to re-authorize historical discussion.
        Retain references, not the recipient's entire private planning context.
        """
        source, stored, _atoms, _expiry, plan = self._selected_draft(selection_event_id, subject)
        candidate = stored.selection.candidate
        completion = next(e for name in ('user_value', 'urgency', 'novelty',
            'confidence', 'risk', 'interruption_cost')
            for e in getattr(candidate.dimensions, name).evidence_event_ids
            if e.startswith('opportunity.synthesis:') and e.endswith(':completed'))
        start = self.journal.get(self.journal.get(completion).event.causation_id)
        original = OpportunitySynthesizer(self.journal, content_vault=self.content_vault,
            context_vault=self.context_vault).reader.active_evidence(subject=subject,
                clearance=source.event.sensitivity, limit=32,
                observation_event_ids=tuple(start.event.payload['observation_event_ids']))
        selected = {e.observation_event_id for e in original
                    if e.agenda_item_id == candidate.agenda_item_id}
        if plan is not None and plan['version'] == 3:
            context = self.expression_context_for_selection(selection_event_id, subject)
            selected.update(e['event_id'] for e in context['source_evidence'])
        references = []
        for evidence in original:
            if evidence.observation_event_id in selected:
                record = self.journal.get(evidence.observation_event_id)
                references.append({'event_id': record.event.event_id,
                    'content': _thaw_json(record.event.payload['content']),
                    'excerpt_policy': start.event.payload.get('interpreter_method',{}).get('source_excerpt_policy')})
        return references

    def expression_context_for_selection(self, selection_event_id, subject):
        *_, plan = self._selected_draft(selection_event_id, subject)
        if plan is None or plan['version'] != 3:
            return expression_context(plan) if plan is not None else None
        source, stored, _atoms, _expiry, _plan = self._selected_draft(selection_event_id,subject)
        candidate = stored.selection.candidate
        # Recover only the immutable original evidence window, not today's pool.
        completion = next(e for e in candidate.dimensions.user_value.evidence_event_ids
                          if e.startswith('opportunity.synthesis:') and e.endswith(':completed'))
        start = self.journal.get(self.journal.get(completion).event.causation_id)
        interpreter = OpportunitySynthesizer(self.journal,content_vault=self.content_vault,
            context_vault=self.context_vault)
        interpreter.load_completed(subject=subject,operation_id=completion.removeprefix(
            'opportunity.synthesis:').removesuffix(':completed'),clearance=source.event.sensitivity)
        original = interpreter.reader.active_evidence(subject=subject,clearance=source.event.sensitivity,
            limit=32,observation_event_ids=tuple(start.event.payload['observation_event_ids']))
        url = next(e.content['url'] for e in original if e.agenda_item_id == candidate.agenda_item_id)
        policy = start.event.payload.get('interpreter_method',{}).get('source_excerpt_policy')
        mode=start.event.payload.get('interpreter_method',{}).get('discovery_authoring')
        focus_ids=set()
        if mode=='source-led-v3':
            from .research_evidence import resolve_research_reads
            focus=resolve_research_reads(interpreter.reader,subject=subject,clearance=source.event.sensitivity,
                receipt_ids=tuple(start.event.payload['research_read_receipt_ids']),
                inquiries=interpreter.inquiries.read(subject=subject,clearance=source.event.sensitivity,
                    item_ids=tuple(start.event.payload.get('discovery_inquiry_item_ids',()))),before_sequence=start.sequence)
            focus_ids={e.observation_event_id for e in focus}
        context = dict(method='discovery-source-authoring-v1',recipient_goal=plan['recipient_goal'],
            behavior_constraints=plan['behavior_constraints'],brief_is_advisory=True,
            authority_granted=False,final_source_and_value_review_required=True,
            user_context=[c.to_prompt() for c in interpreter.context_reader.read(
                subject=subject,clearance=source.event.sensitivity)],
            tentative_reading_tasks=interpreter.inquiries.read(subject=subject,clearance=source.event.sensitivity,
                item_ids=tuple(start.event.payload.get('discovery_inquiry_item_ids',()))),
            source_evidence=[dict(event_id=e.observation_event_id,title=e.content['title'],
                url=e.content['url'],excerpt=source_prompt_excerpt(e.content,policy=policy),
                provenance_metadata={'collector':e.content['source'],**read_scope_metadata(e.content)},
                published_at=e.content.get('published_at')) for e in original
                if e.content['url']==url or e.observation_event_id in focus_ids])
        if mode in ('source-led-v2','source-led-v3'):
            # Research rationale remains in the encrypted agenda/proposal trace.
            # Do not promote it into the recipient's purpose by asking the author
            # (or its reviewer) to satisfy an agent-invented research assignment.
            context['method'] = 'discovery-source-authoring-v3' if mode=='source-led-v3' else 'discovery-source-authoring-v2'
            for field in ('recipient_goal','behavior_constraints','tentative_reading_tasks','brief_is_advisory'):
                context.pop(field, None)
        from .review_contracts import SPLIT_SOURCE_REVIEW
        review_contract=start.event.payload.get('interpreter_method',{}).get('discovery_source_review')
        if review_contract in ('bounded-group-source-v1',SPLIT_SOURCE_REVIEW):
            context['semantic_source_contract']=review_contract
        if start.event.payload.get('interpreter_method',{}).get('reading_assessment'):
            context['reading_assessment']=interpreter.reading_assessment_context(
                subject=subject,receipt_event_id=completion,clearance=source.event.sensitivity)
        if start.event.payload.get('feedback_recall') is not None:
            context['literal_feedback_context']=[v.to_prompt() for v in interpreter.feedback_for_start(
                start,subject=subject,clearance=source.event.sensitivity)]
            context['feedback_scope']='Attributed prior pairs, not profile facts, current instructions or action permission.'
        return context

    def requires_final_source_review(self, *, selection_event_id, subject):
        *_, plan = self._selected_draft(selection_event_id,subject)
        return plan is not None and plan['version'] == 3

    @staticmethod
    def _speech(stored, plan):
        if plan is not None:
            return MessageSpeechAct(plan['speech_act'])
        return (MessageSpeechAct.SHARE if stored.selection.candidate.action_kind is ActionKind.SHARE
                else MessageSpeechAct.ASK)

    def _message_id(self, selection_event_id):
        return 'selected-opportunity:' + self.content_vault.digest_json(
            {'selection_event_id': selection_event_id})[:40]

    def action_contract_for_expression(self, *, expression_event_id,
                                       selection_event_id, subject, as_of=None):
        """Resolve exact proposed wording, never infer approval from a review.

        The caller must require exact confirmation or a current explicit grant
        covering natural expression, through the send-time authorizer.
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
        source, stored, atoms, expiry, plan = self._selected_draft(selection_event_id, subject)
        message_id = self._message_id(selection_event_id)
        event_id = 'message.meaning:' + message_id
        existing = self.journal.get(event_id)
        if existing is not None:
            self._selection_context(selection_event_id=selection_event_id,
                meaning_event_id=event_id, subject=subject, observed_at=datetime.now(timezone.utc))
            return existing
        now = datetime.now(timezone.utc)
        speech = self._speech(stored, plan)
        document = MeaningDocument(message_id, subject, speech, atoms, now,
            min(expiry, now + timedelta(hours=1)), source.event.sensitivity)
        record = self.meanings.define(document, actor='system:alive-opportunity-expression', observed_at=now)
        self._selection_context(selection_event_id=selection_event_id,
            meaning_event_id=record.event.event_id, subject=subject, observed_at=now)
        return record

    def _selection_context(self, *, selection_event_id, meaning_event_id, subject, observed_at):
        source, stored, atoms, expiry, plan = self._selected_draft(selection_event_id, subject)
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
        speech = self._speech(stored, plan)
        if (document.message_id != message_id or document.subject != subject
                or document.speech_act is not speech or document.atoms != atoms
                or document.expires_at > expiry
                or document.created_at < source.event.observed_at
                or observed_at < document.created_at or observed_at >= document.expires_at):
            raise SemanticReviewError('selected draft and expression meaning diverged')
        return source, document, stored.frame.frame_id, stored.selection.candidate.candidate_id
