"""Operator-initiated, Core-conversation-confirmed setup; never an IO grant.

No legacy subject reassignment, transport, model call, active-policy enablement
or credential configuration. The authenticated configuration is a prerequisite
for ordinary live assembly, not evidence that such a runtime is operating.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import json
import secrets
from uuid import uuid4

from .content_vault import ContentReference, ContentVault
from .conversation_continuity import core_scope_identity
from .event_store import ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json, _freeze_json
from .privacy import LocalIdentityProtector
from .retention import RetentionProjection, RetentionDirection, RetentionValidationError


class KernelSetupError(ValueError):
    pass


@dataclass(frozen=True, slots=True, repr=False)
class KernelConfiguration:
    event_id: str
    subject: str
    scope: dict = field(repr=False)
    options: dict = field(repr=False)


def validate_options(options):
    if (not isinstance(options, dict) or set(options) != {'model_calls', 'delivery',
            'outbound_retention_days', 'outbound_retention_confirmed', 'model', 'public_queries', 'cited_reads'}
            or options['model_calls'] is not True or options['delivery'] is not True
            or options['outbound_retention_confirmed'] is not True
            or type(options['outbound_retention_days']) is not int
            or not 1 <= options['outbound_retention_days'] <= 365
            or type(options['cited_reads']) is not bool):
        raise KernelSetupError('explicit model/delivery/retention choices required')
    model = options['model']
    queries = options['public_queries']
    if (model is not None and (not isinstance(model,str) or not model.strip() or len(model)>512)
            or not isinstance(queries,list) or len(queries)>3
            or any(not isinstance(q,str) or not q.strip() or len(q)>128 for q in queries)
            or len(set(queries)) != len(queries) or options['cited_reads'] and not queries):
        raise KernelSetupError('bounded approved public queries and optional Core model alias required')
    return {**options, 'public_queries':list(queries)}


class KernelSetupStore:
    INTENT_TYPE = 'alive.setup.intent'
    CONFIRMED_TYPE = 'alive.setup.confirmed'
    SETUP_OWNER = 'system:alive-setup'

    def __init__(self, root, *, initialize=False):
        self.root = Path(root).resolve()
        expected = (self.root/'identity.key',self.root/'experience.sqlite3',
                    self.root/'content-vault/content.key',self.root/'content-vault/content.sqlite3')
        present = tuple(path.is_file() for path in expected)
        if type(initialize) is not bool or not all(present) and (any(path.exists() for path in expected) or not initialize):
            raise KernelSetupError('setup storage/key inventory incomplete; restore it, never replace its identity')
        self.protector = LocalIdentityProtector(self.root/'identity.key')
        self.journal = ExperienceJournal(self.root/'experience.sqlite3')
        self.vault = ContentVault(self.root/'content-vault', backup_root=self.root/'content-backups')
        # Complete the initial key inventory during explicit operator setup,
        # before publishing any intent. Read/status/startup paths never seed it.
        self.vault.digest_json({'contract':'alive.setup.bootstrap.v1'})

    @staticmethod
    def _now(value=None):
        value = value or datetime.now(timezone.utc)
        if value.tzinfo is None or value.utcoffset() is None:
            raise KernelSetupError('aware setup timestamp required')
        return value.astimezone(timezone.utc)

    def _payload(self, record, kind):
        if (record is None or record.event.event_type != kind
                or record.event.source != 'hermes.command.alive.setup'
                or record.event.sensitivity is not Sensitivity.PRIVATE):
            raise KernelSetupError('canonical setup record required')
        payload = _thaw_json(record.event.payload)
        signature = payload.pop('integrity_authenticator', None)
        document=json.loads(record.event.canonical_json())
        document['payload']=payload
        if not self.protector.verify_json(kind+'.v1', document, signature):
            raise KernelSetupError('setup authority changed')
        return payload

    def _seal(self,event):
        document=json.loads(event.canonical_json())
        payload=_thaw_json(event.payload)
        payload['integrity_authenticator']=self.protector.authenticate_json(event.event_type+'.v1',document)
        return replace(event,payload=payload)

    def latest_intent(self):
        return next(self.journal.iter_reverse(event_types=(self.INTENT_TYPE,), max_records=1), None)

    def stage(self, options, *, replace=False, now=None):
        options, current = validate_options(options), self._now(now)
        if type(replace) is not bool:
            raise KernelSetupError('explicit replacement choice required')
        previous = self.latest_intent()
        if previous is not None and not replace:
            raise KernelSetupError('setup already exists; explicit replacement required')
        identity = 'alive.setup:' + uuid4().hex
        token = secrets.token_urlsafe(24)
        expiry = current + timedelta(minutes=15)
        reference = self.vault.put_json(options, subject=self.SETUP_OWNER, purpose='setup.intent',
            sensitivity=Sensitivity.PRIVATE, retention_until=expiry, content_id=identity)
        payload = {'content':reference.to_event_payload(),
            'challenge':self.protector.authenticate_json('alive.setup.challenge.v1',
                                                       {'intent':identity,'token':token}),
            'replaces_intent_id':previous.event.event_id if previous else None,
            'model_calls_started':False, 'delivery_activated':False}
        event = self._seal(EventEnvelope(event_id=identity, event_type=self.INTENT_TYPE,
            source='hermes.command.alive.setup', actor='system:alive-installer',
            sensitivity=Sensitivity.PRIVATE, occurred_at=current, observed_at=current,
            expires_at=expiry, payload=payload))
        def check(connection):
            row = connection.execute('SELECT event_id FROM experience_events WHERE event_type=? ORDER BY sequence DESC LIMIT 1',
                                     (self.INTENT_TYPE,)).fetchone()
            if (row['event_id'] if row else None) != (previous.event.event_id if previous else None):
                raise KernelSetupError('setup changed concurrently; no implicit replacement')
        result = self.journal.append(event, precondition=check)
        return JournalRecord(result.sequence, result.event), token

    def _configuration(self, record):
        payload = self._payload(record, self.CONFIRMED_TYPE)
        if (record.event.actor != record.event.subject or not record.event.subject
                or record.event.causation_id != payload.get('intent_event_id')
                or record.event.event_id != record.event.causation_id + ':confirmed'
                or payload.get('delivery_activated') is not False):
            raise KernelSetupError('invalid setup confirmation authority')
        reference = ContentReference.from_event_payload(payload['content'])
        body = self.vault.resolve_json(reference.content_id, expected_subject=record.event.subject,
            expected_purpose='setup.configuration', expected_sensitivity=Sensitivity.PRIVATE)
        scope, owner, fingerprint = core_scope_identity(body['scope'], self.protector)
        if (self.vault.digest_json(body) != reference.digest or owner != record.event.subject
                or fingerprint != payload.get('scope_fingerprint')):
            raise KernelSetupError('protected setup scope changed')
        return KernelConfiguration(record.event.event_id, owner, _freeze_json(scope),
                                   _freeze_json(validate_options(body['options'])))

    def configuration(self):
        intent = self.latest_intent()
        if intent is None:
            return None
        self._payload(intent, self.INTENT_TYPE)
        record = self.journal.get(intent.event.event_id + ':confirmed')
        return self._configuration(record) if record else None

    def _retain_configuration(self, record, configured):
        """Recover a missing first write, never re-enable a later OFF choice."""
        retention = RetentionProjection(self.journal, content_vault=self.vault)
        intent_id = record.event.causation_id
        consent_id = 'retention.consent:' + intent_id
        later = next(self.journal.iter_reverse(event_types=('retention.consent_changed',),
                    subject=configured.subject,max_records=1),None)
        if self.journal.get(consent_id) is None and (later is None or later.sequence <= record.sequence):
            try:
                consent = retention.append_consent(subject=configured.subject, actor=configured.subject, enabled=True,
                    retention_days=configured.options['outbound_retention_days'], directions=(RetentionDirection.OUTBOUND,),
                    sensitivity=Sensitivity.PRIVATE, operation_id=intent_id, not_after_sequence=record.sequence)
                retention.apply(consent)
            except RetentionValidationError:
                raise KernelSetupError('retention changed after confirmation; newer choice preserved') from None
        intent = self.journal.get(intent_id)
        pending = ContentReference.from_event_payload(self._payload(intent,self.INTENT_TYPE)['content'])
        # The confirmed owner now has its protected configuration. Do not leave
        # an unowned duplicate of the operator's topics in the pending namespace.
        self.vault.erase_item(pending.content_id)
        return configured

    def confirm(self, intent_id, token, *, scope, now=None):
        """Trusted Core slash caller supplies the canonical current scope.

        Token possession is not pairing/admission proof. The caller must first
        use Core's authenticated command source and exact SessionStore route.
        """
        current = self._now(now)
        document, owner, fingerprint = core_scope_identity(scope, self.protector)
        intent = self.latest_intent()
        payload = self._payload(intent, self.INTENT_TYPE)
        if (intent.event.event_id != intent_id or intent.event.actor != 'system:alive-installer'
                or intent.event.expires_at is None or not intent.event.observed_at <= current < intent.event.expires_at
                or not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32}',token)
                or not self.protector.verify_json('alive.setup.challenge.v1',
                    {'intent':intent_id,'token':token},payload.get('challenge'))):
            raise KernelSetupError('setup confirmation expired, superseded or invalid')
        confirmed_id = intent_id + ':confirmed'
        prior = self.journal.get(confirmed_id)
        if prior is not None:
            configured = self._configuration(prior)
            if configured.subject != owner or configured.scope != document:
                raise KernelSetupError('setup already confirmed in another conversation')
            return self._retain_configuration(prior, configured)
        reference = ContentReference.from_event_payload(payload['content'])
        options = self.vault.resolve_json(reference.content_id, expected_subject=self.SETUP_OWNER,
            expected_purpose='setup.intent', expected_sensitivity=Sensitivity.PRIVATE)
        if self.vault.digest_json(options) != reference.digest:
            raise KernelSetupError('setup choices changed')
        options = validate_options(options)
        content = self.vault.put_json({'scope':document, 'options':options}, subject=owner,
            purpose='setup.configuration', sensitivity=Sensitivity.PRIVATE,
            content_id='setup-configuration:' + self.protector.authenticate_json('setup.configuration.id.v1',
                {'intent':intent_id,'scope':fingerprint}))
        confirmed = {'intent_event_id':intent_id, 'scope_fingerprint':fingerprint,
            'content':content.to_event_payload(), 'delivery_activated':False, 'model_calls_started':False,
            'legacy_subjects_migrated':False}
        event = self._seal(EventEnvelope(event_id=confirmed_id, event_type=self.CONFIRMED_TYPE,
            source='hermes.command.alive.setup', actor=owner, subject=owner,
            sensitivity=Sensitivity.PRIVATE, causation_id=intent_id,
            occurred_at=current, observed_at=current, payload=confirmed))
        def factory(connection):
            latest = connection.execute('SELECT event_id FROM experience_events WHERE event_type=? ORDER BY sequence DESC LIMIT 1',
                                        (self.INTENT_TYPE,)).fetchone()
            if latest is None or latest['event_id'] != intent_id:
                raise KernelSetupError('setup changed during confirmation')
            row = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_id=?',
                                     (confirmed_id,)).fetchone()
            if row is not None:
                existing = self.journal._record(row).event
                if (existing.subject != owner or existing.payload.get('scope_fingerprint') != fingerprint):
                    raise KernelSetupError('setup already confirmed in another conversation')
                return existing
            return event
        result = self.journal.append(factory)
        # This is only the separately confirmed retention choice. No enabled
        # autonomy policy, route binding or action delegation is minted here.
        record = JournalRecord(result.sequence,result.event)
        return self._retain_configuration(record,self._configuration(record))
