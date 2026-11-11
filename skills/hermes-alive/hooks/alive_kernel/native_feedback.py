"""Consented native-turn feedback associations, not literal quote receipts.

The Core-bound bridge supplies the current input and retained share. A main
model selects their relationship; this never proves human seeing, permanent
preference, tool permission or a wire-level reply. Bodies use the existing vault.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import json

from .content_vault import ContentReference, ContentUnavailableError
from .events import EventEnvelope, Sensitivity, _thaw_json
from .kernel_setup import KernelSetupStore
from .event_store import EventConflictError

FLAG = 'interpret_share_feedback'
EVENT = 'feedback.native_associated'
DOMAIN = 'alive.native.feedback.v1'
SOURCE = 'hermes.core.alive.feedback'


def _signed(store, event):
    payload = _thaw_json(event.payload)
    payload['authenticator'] = store.protector.authenticate_json(DOMAIN, json.loads(event.canonical_json()))
    return replace(event, payload=payload)


def _verified(store, event):
    document = json.loads(event.canonical_json())
    signature = document['payload'].pop('authenticator', None)
    return store.protector.verify_json(DOMAIN, document, signature)


def permission(store, configured):
    if configured.options.get(FLAG) is not True:
        return False, configured.event_id
    for row in store.journal.iter_reverse(event_types=('alive.feedback.permission',), subject=configured.subject):
        event = row.event
        if event.payload.get('configuration_event_id') != configured.event_id:
            continue
        if (event.source != 'hermes.command.alive.feedback' or event.actor != configured.subject
                or event.sensitivity is not Sensitivity.PRIVATE or not _verified(store, event)
                or type(event.payload.get('enabled')) is not bool):
            raise ValueError('feedback permission integrity unavailable')
        return event.payload['enabled'], event.event_id
    return True, configured.event_id


def set_permission(store, configured, enabled):
    if type(enabled) is not bool or enabled and configured.options.get(FLAG) is not True:
        raise ValueError('guided feedback capture and interpretation choice required')
    return store.journal.append(_signed(store, EventEnvelope(event_type='alive.feedback.permission',
        source='hermes.command.alive.feedback', actor=configured.subject, subject=configured.subject,
        sensitivity=Sensitivity.PRIVATE, payload={'configuration_event_id':configured.event_id,
            'enabled':enabled, 'automatic_profile_update':False})))


def admitted_input(store, configured, text, message_id):
    """Only the newest observed input may support the normal turn association."""
    from .admitted_inbound import configured_input_identity
    expected_id, fingerprint = configured_input_identity(store,configured,message_id,text)
    for row in store.journal.iter_reverse(event_types=('conversation.inbound',),
            subject=configured.subject, max_records=32):
        event = row.event
        if (event.source == 'hermes.plugin.post_gateway_admission'
                and event.payload.get('method') == 'configured-input-wake-v1'
                and event.payload.get('configuration_event_id') == configured.event_id):
            return row if event.event_id == expected_id and event.payload.get('text_fingerprint') == fingerprint else None
    return None


@dataclass(frozen=True, slots=True)
class NativeFeedbackEvidence:
    outcome_event_id: str
    source_event_id: str
    attempt_event_id: str
    observed_at: str
    retention_until: str
    delivered_text: str = field(repr=False)
    feedback_text: str = field(repr=False)
    evidence_span: str = field(repr=False)
    association_reason: str = field(repr=False)
    submission_report: str = 'submission_unconfirmed'

    def to_prompt(self):
        return dict(outcome_event_id=self.outcome_event_id, source_event_id=self.source_event_id,
            attempt_event_id=self.attempt_event_id, observed_at=self.observed_at,
            retention_until=self.retention_until, prepared_text=self.delivered_text,
            current_input=self.feedback_text, evidence_span=self.evidence_span,
            association_reason=self.association_reason, submission_report=self.submission_report,
            status='native_main_turn_semantic_association_not_quote_proof',
            actual_human_seeing_proven=False, automatic_profile_update=False,
            association_semantic_accuracy_proven=False, complete_feedback_inventory=False,
            action_authority=False)


class NativeFeedbackStore:
    def __init__(self, continuity):
        self.continuity = continuity
        self.journal, self.vault = continuity.journal, continuity.vault
        self.setup = KernelSetupStore(self.journal.path.parent, initialize=False, journal=self.journal)

    def record(self, *, configured, scope, admission_id, message_id, share_id, text, evidence_span,
               association_reason, permission_id, validate_current):
        if (not callable(validate_current) or not isinstance(text, str) or not 1 <= len(text) <= 8000
                or not isinstance(evidence_span, str) or not evidence_span.strip()
                or len(evidence_span) > 1500 or evidence_span not in text
                or not isinstance(association_reason, str) or not association_reason.strip()
                or len(association_reason) > 1000):
            raise ValueError('bounded exact current input and semantic association required')
        now = datetime.now(timezone.utc)
        def current():
            latest = self.setup.configuration()
            observed = admitted_input(self.setup, configured, text, message_id)
            if (latest is None or latest.event_id != configured.event_id
                    or permission(self.setup, latest) != (True, permission_id)
                    or observed is None or observed.event.event_id != admission_id):
                raise ValueError('feedback input or permission changed')
            validate_current()
        current()
        share = self.continuity.read_reference(scope=scope, clearance=Sensitivity.PRIVATE,
            share_id=share_id, include_sources=False)
        original = self.journal.get(share_id)
        observation = self.continuity._adapter_observation(original.event.causation_id,
            configured.subject, now) if original is not None else None
        admission = self.journal.get(admission_id)
        observed = self.journal.get(original.event.causation_id+':adapter-observation') if original else None
        if (share is None or observation is None or observation.get('report_kind') != 'success_reported'
                or original.event.expires_at <= now
                or admission is None or original.sequence >= admission.sequence
                or observed is None or observed.sequence >= admission.sequence):
            raise ValueError('retained submitted share required')
        identifier = self.setup.protector.authenticate_json(DOMAIN+'.identity', dict(
            configuration=configured.event_id, admission=admission_id, share=share_id))
        event_id = 'feedback.native:'+identifier
        existing = self.journal.get(event_id)
        if existing is not None:
            if self.read(existing, subject=configured.subject, clearance=Sensitivity.PRIVATE) is None:
                raise ValueError('previous feedback was withdrawn or expired')
            return existing
        grant = self.journal.get(permission_id)
        if grant is None or admission.sequence <= grant.sequence:
            raise ValueError('feedback must arrive after its current processing grant')
        until = min(now+timedelta(days=configured.options['outbound_retention_days']), original.event.expires_at)
        content = self.vault.put_json(dict(scope=scope, share_id=share_id, text=text,
            evidence_span=evidence_span, association_reason=association_reason),
            subject=configured.subject, purpose='feedback.native_association',
            sensitivity=Sensitivity.PRIVATE, retention_until=until)
        event = _signed(self.setup, EventEnvelope(event_id=event_id, event_type=EVENT,
            source=SOURCE, actor='system:alive-native-feedback', subject=configured.subject,
            sensitivity=Sensitivity.PRIVATE, observed_at=now, occurred_at=now, expires_at=until,
            causation_id=admission_id, payload=dict(configuration_event_id=configured.event_id,
                permission_id=permission_id, share_id=share_id, content=content.to_event_payload(),
                attribution='main_turn_semantic_association_not_quote_proof',
                automatic_profile_update=False, external_action_authorized=False)))
        def fence(_connection):
            current()
            if self.continuity.read_reference(scope=scope, clearance=Sensitivity.PRIVATE,
                    share_id=share_id, include_sources=False) is None:
                raise ValueError('feedback target withdrawn before publication')
        try:
            return self.journal.append(event, precondition=fence)
        except EventConflictError:
            self.vault.erase_item(content.content_id)
            existing = self.journal.get(event_id)
            if existing is not None and self.read(existing, subject=configured.subject,
                    clearance=Sensitivity.PRIVATE) is not None:
                return existing
            raise
        except Exception:
            self.vault.erase_item(content.content_id)
            raise

    def read(self, record, *, subject, clearance):
        event = record.event
        if (event.event_type != EVENT or event.source != SOURCE or event.subject != subject
                or event.actor != 'system:alive-native-feedback' or event.sensitivity is not Sensitivity.PRIVATE
                or Sensitivity(clearance) is Sensitivity.PUBLIC or not _verified(self.setup, event)):
            return None
        configured = self.setup.configuration()
        if (configured is None or configured.subject != subject
                or configured.event_id != event.payload.get('configuration_event_id')
                or not permission(self.setup, configured)[0]):
            return None
        now = datetime.now(timezone.utc)
        if event.expires_at is None or event.expires_at <= now or event.observed_at > now:
            return None
        try:
            ref = ContentReference.from_event_payload(event.payload['content'])
            body = self.vault.resolve_json(ref.content_id, expected_subject=subject,
                expected_purpose='feedback.native_association', expected_sensitivity=Sensitivity.PRIVATE)
            if self.vault.digest_json(body) != ref.digest or ref.retention_until != event.expires_at:
                return None
            share = self.continuity.read_reference(scope=body['scope'], clearance=Sensitivity.PRIVATE,
                share_id=event.payload['share_id'], include_sources=False)
            original = self.journal.get(event.payload['share_id'])
            if original is None:
                return None
            observation = self.continuity._adapter_observation(original.event.causation_id, subject, now)
            admission = self.journal.get(event.causation_id)
            if (share is None or observation is None or observation.get('report_kind') != 'success_reported'
                    or admission is None or admission.event.subject != subject
                    or admission.event.source != 'hermes.plugin.post_gateway_admission'
                    or admission.sequence >= record.sequence or original.sequence >= admission.sequence
                    or admission.event.payload.get('text_fingerprint') != self.setup.protector.authenticate_json(
                        'configured.input.text.v1', body['text'])
                    or body['evidence_span'] not in body['text']):
                return None
            return NativeFeedbackEvidence(event.event_id, admission.event.event_id,
                original.event.causation_id, event.observed_at.isoformat(), ref.retention_until.isoformat(),
                share['text'], body['text'], body['evidence_span'], body['association_reason'],
                observation['report_kind'])
        except (KeyError, TypeError, ValueError, ContentUnavailableError):
            return None
