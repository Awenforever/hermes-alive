"""Consented historical delivered text, never a renewed executable intention."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .action_contract import parse_action_contract
from .content_vault import ContentReference, ContentVault
from .deliberation_store import DeliberationProjection
from .event_store import EventConflictError
from .events import EventEnvelope, Sensitivity, _thaw_json
from .outcomes import OutcomeProjection, OutcomeKind
from .memory import MemoryProjection


class DeliveredHistoryError(ValueError):
    pass


class DeliveredHistoryStore:
    NAMESPACE = 'message.delivery-history.v1'

    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.vault = content_vault or ContentVault(journal.path.parent / 'content-vault',
            backup_root=journal.path.parent / 'content-backups')
        self.outcomes = OutcomeProjection(journal, content_vault=self.vault)
        self.protector = self.outcomes.receipt_protector
        self.context_vault = MemoryProjection(journal, content_vault=context_vault).content_vault

    def _dependency_vault(self, alias):
        if alias == 'action':
            return self.vault
        if alias == 'context':
            return self.context_vault
        raise DeliveredHistoryError('unknown dependency vault')

    def _check_dependencies(self, dependencies, subject):
        forgotten = False
        for dependency in dependencies:
            vault = self._dependency_vault(dependency['vault'])
            content_id = dependency['content_id']
            with closing(vault._connect()) as connection:
                live = connection.execute('SELECT subject FROM content_items WHERE content_id=?', (content_id,)).fetchone()
                erased = connection.execute('SELECT 1 FROM erasure_items WHERE content_id=? LIMIT 1', (content_id,)).fetchone()
            if (live is not None and live['subject'] != subject) or (live is None and erased is None):
                raise DeliveredHistoryError('dependency storage scope unavailable')
            forgotten |= vault.explicit_erasure_recorded(content_id)
        return forgotten

    def _consent(self, subject, clearance):
        records = tuple(self.journal.iter_reverse(event_types=('retention.consent_changed',),
            subject=subject, max_records=1))
        record = records[0] if records else None
        directions = record.event.payload.get('directions') if record is not None else None
        if (record is None or record.event.actor != subject
                or record.event.source != 'hermes.command.memory'
                or record.event.sensitivity is not Sensitivity.PRIVATE
                or record.event.payload.get('enabled') is not True
                or not isinstance(directions, (tuple, list))
                or not 1 <= len(directions) <= 2
                or any(not isinstance(value, str) or value not in ('inbound','outbound') for value in directions)
                or len(set(directions)) != len(directions) or 'outbound' not in directions
                or record.event.payload.get('content_sensitivity') != Sensitivity(clearance).value
                or type(record.event.payload.get('retention_days')) is not int
                or not 1 <= record.event.payload['retention_days'] <= 365
                or (record.event.expires_at is not None
                    and record.event.expires_at <= datetime.now(timezone.utc))):
            raise DeliveredHistoryError('outbound retention consent unavailable')
        return record

    def _delivery(self, subject, delivery_outcome_event_id, clearance):
        outcome = self.journal.get(delivery_outcome_event_id)
        if (outcome is None or outcome.event.subject != subject
                or outcome.event.sensitivity != Sensitivity(clearance)
                or outcome.event.event_type != 'outcome.recorded'
                or outcome.event.payload.get('kind') != OutcomeKind.DELIVERY_SUCCEEDED.value):
            raise DeliveredHistoryError('canonical delivery outcome unavailable')
        with closing(self.outcomes._connect()) as connection:
            if not self.outcomes.canonical_evidence_valid_for(self.journal, connection, outcome):
                raise DeliveredHistoryError('delivery provenance unavailable')
        attempt = self.journal.get('action.attempt:' + outcome.event.payload['attempt_id'])
        receipt = self.journal.get(outcome.event.payload['source_event_id'])
        authorization = self.journal.get(attempt.event.payload['authorization_event_id'])
        if (attempt.event.payload.get('executor') != 'hermes.channel.send'
                or receipt.event.observed_at > datetime.now(timezone.utc)
                or authorization is None or authorization.event.subject != subject
                or authorization.event.sensitivity != Sensitivity(clearance)):
            raise DeliveredHistoryError('delivered action scope unavailable')
        data = _thaw_json(authorization.event.payload)
        signature = data.pop('integrity_authenticator', None)
        if not self.protector.verify_json('action.authorization.v1', data, signature):
            raise DeliveredHistoryError('original authorization binding unavailable')
        return outcome, attempt, receipt, authorization

    def _event_id(self, attempt, receipt):
        return 'message.delivery-history:' + self.protector.authenticate_json(self.NAMESPACE + '.identity',
            {'attempt':attempt.event.event_id, 'start':receipt.event.payload['start_event_id']})

    def capture(self, *, subject, delivery_outcome_event_id, clearance=Sensitivity.PRIVATE):
        clearance = Sensitivity(clearance)
        consent = self._consent(subject, clearance)
        outcome, attempt, receipt, authorization = self._delivery(subject, delivery_outcome_event_id, clearance)
        if consent.sequence >= receipt.sequence or consent.event.observed_at > receipt.event.observed_at:
            raise DeliveredHistoryError('retention consent did not precede delivery')
        event_id = self._event_id(attempt, receipt)
        existing = self.journal.get(event_id)
        if existing is not None:
            self.resolve(event_id, subject=subject, clearance=clearance)
            return existing
        stored = DeliberationProjection(self.journal, content_vault=self.vault).inspect(
            authorization.event.payload['frame_id'], clearance=clearance)
        if stored is None:
            raise DeliveredHistoryError('original frame unavailable')
        candidate = next((c for c in stored.frame.candidates
            if c.candidate_id == attempt.event.payload['candidate_id']), None)
        if candidate is None:
            raise DeliveredHistoryError('original candidate unavailable')
        content_id = authorization.event.payload.get('executable_content_id') or candidate.content_id
        contract = parse_action_contract(self.vault.resolve_json(content_id, expected_subject=subject,
            expected_purpose='deliberation.candidate', expected_sensitivity=clearance),
            capability='hermes.channel.send')
        if not self.protector.verify_json('action.contract.v1', contract.to_document(),
                authorization.event.payload.get('action_contract_binding')):
            raise DeliveredHistoryError('delivered text binding unavailable')
        dependency_ids = {('action', content_id)}
        evidence_ids = {authorization.event.payload.get('expression_event_id'),
                        'deliberation.frame:' + authorization.event.payload['frame_id']}
        if candidate.dimensions is not None:
            evidence_ids.update(e for dimension in ('user_value','urgency','novelty','confidence','risk','interruption_cost')
                for e in getattr(candidate.dimensions, dimension).evidence_event_ids)
        for evidence_id in evidence_ids:
            record = self.journal.get(evidence_id) if evidence_id else None
            if record is not None and record.event.subject == subject and record.event.payload.get('content'):
                alias = 'context' if record.event.event_type == 'memory.proposed' else 'action'
                dependency_ids.add((alias, ContentReference.from_event_payload(record.event.payload['content']).content_id))
        dependencies = [{'vault':alias, 'content_id':value} for alias, value in sorted(dependency_ids)]
        if self._check_dependencies(dependencies, subject):
            raise DeliveredHistoryError('delivered text dependency was explicitly erased')
        until = receipt.event.observed_at + timedelta(days=consent.event.payload['retention_days'])
        if until <= datetime.now(timezone.utc):
            raise DeliveredHistoryError('historical retention already expired')
        ref = self.vault.put_json({'contract':contract.to_document()}, subject=subject,
            purpose='message.delivered-history', sensitivity=clearance, retention_until=until,
            content_id='delivery-history-content:' + uuid4().hex)
        payload = {'attempt_id':attempt.event.payload['attempt_id'],
            'delivery_outcome_event_id':outcome.event.event_id, 'delivery_event_id':receipt.event.event_id,
            'consent_event_id':consent.event.event_id, 'dependencies':dependencies,
            'authorization_event_id':authorization.event.event_id, 'content':ref.to_event_payload(),
            'execution_authority_granted':False, 'learning_authority_granted':False}
        payload['integrity_authenticator'] = self.protector.authenticate_json(self.NAMESPACE, payload)
        def still_consented(connection):
            row = connection.execute("SELECT event_id FROM experience_events WHERE subject=? "
                "AND event_type='retention.consent_changed' ORDER BY sequence DESC LIMIT 1", (subject,)).fetchone()
            if row is None or row['event_id'] != consent.event.event_id:
                raise DeliveredHistoryError('retention changed during capture')
        try:
            result = self.journal.append(EventEnvelope(event_id=event_id,
                event_type='message.delivery_history', source='alive.delivered-history',
                actor='system:alive-history', subject=subject, sensitivity=clearance,
                causation_id=outcome.event.event_id, expires_at=until, payload=payload),
                precondition=still_consented)
        except EventConflictError:
            self.vault.erase_item(ref.content_id)
            self.resolve(event_id, subject=subject, clearance=clearance)
            return self.journal.get(event_id)
        except Exception:
            self.vault.erase_item(ref.content_id)
            raise
        self.resolve(result.event.event_id, subject=subject, clearance=clearance)
        return self.journal.get(result.event.event_id)

    def resolve(self, event_id, *, subject, clearance=Sensitivity.PRIVATE):
        header = self.journal.get(event_id)
        if (header is None or header.event.subject != subject
                or header.event.sensitivity != Sensitivity(clearance)
                or header.event.event_type != 'message.delivery_history'
                or header.event.source != 'alive.delivered-history'
                or header.event.actor != 'system:alive-history'):
            raise DeliveredHistoryError('historical message scope unavailable')
        payload = _thaw_json(header.event.payload)
        signature = payload.pop('integrity_authenticator', None)
        if not self.protector.verify_json(self.NAMESPACE, payload, signature):
            raise DeliveredHistoryError('historical message integrity unavailable')
        consent = self._consent(subject, clearance)
        outcome, attempt, receipt, authorization = self._delivery(subject,
            payload['delivery_outcome_event_id'], clearance)
        ref = ContentReference.from_event_payload(payload['content'])
        if (self._event_id(attempt, receipt) != event_id
                or header.event.causation_id != outcome.event.event_id
                or payload['delivery_event_id'] != receipt.event.event_id
                or payload['attempt_id'] != attempt.event.payload['attempt_id']
                or payload['authorization_event_id'] != authorization.event.event_id
                or payload['consent_event_id'] != consent.event.event_id
                or consent.sequence >= receipt.sequence
                or ref.sensitivity != Sensitivity(clearance)
                or ref.retention_until != header.event.expires_at
                or ref.retention_until != receipt.event.observed_at + timedelta(days=consent.event.payload['retention_days'])
                or ref.retention_until <= datetime.now(timezone.utc)
                or payload['execution_authority_granted'] is not False
                or payload['learning_authority_granted'] is not False):
            raise DeliveredHistoryError('historical message boundary changed')
        if self._check_dependencies(payload['dependencies'], subject):
            self.vault.erase_item(ref.content_id)
            raise DeliveredHistoryError('historical dependency was explicitly forgotten')
        value = self.vault.resolve_json(ref.content_id, expected_subject=subject,
            expected_purpose='message.delivered-history', expected_sensitivity=Sensitivity(clearance))
        if self.vault.digest_json(value) != ref.digest:
            raise DeliveredHistoryError('historical text changed')
        contract = parse_action_contract(value['contract'], capability='hermes.channel.send')
        if not self.protector.verify_json('action.contract.v1', contract.to_document(),
                authorization.event.payload.get('action_contract_binding')):
            raise DeliveredHistoryError('historical text is not the authorized message')
        return {'text':contract.operation['text'], 'content_id':ref.content_id,
                'delivery_event_id':receipt.event.event_id, 'attempt_id':payload['attempt_id'],
                'event_id':event_id, 'retention_until':ref.retention_until}

    def for_delivery(self, *, subject, delivery_outcome_event_id, clearance=Sensitivity.PRIVATE):
        _, attempt, receipt, _ = self._delivery(subject, delivery_outcome_event_id, clearance)
        event_id = self._event_id(attempt, receipt)
        if self.journal.get(event_id) is None:
            return None
        return self.resolve(event_id, subject=subject, clearance=clearance)

    def reconcile_erasure(self, *, subject=None):
        """Operator-owned metadata sweep; never decrypt or recreate old content.

        Walk all relevant history, not a latest-N window. Verify ownership and
        canonical signed history before allowing a dependency to erase its copy.
        Broken locators/integrity remain visible, never guessed or ignored.
        """
        report = {'examined':0, 'erased':0, 'unresolved':0}
        for record in self.journal.iter_reverse(event_types=('message.delivery_history',), subject=subject):
            report['examined'] += 1
            try:
                if record.event.source != 'alive.delivered-history' or record.event.actor != 'system:alive-history':
                    raise DeliveredHistoryError('history producer unavailable')
                payload = _thaw_json(record.event.payload)
                signature = payload.pop('integrity_authenticator', None)
                if not self.protector.verify_json(self.NAMESPACE, payload, signature):
                    raise DeliveredHistoryError('history integrity unavailable')
                outcome = self.journal.get(payload['delivery_outcome_event_id'])
                attempt = self.journal.get('action.attempt:' + payload['attempt_id'])
                receipt = self.journal.get(payload['delivery_event_id'])
                if (attempt is None or receipt is None or outcome is None
                        or attempt.event.subject != record.event.subject
                        or receipt.event.subject != record.event.subject
                        or record.event.causation_id != outcome.event.event_id
                        or self._event_id(attempt, receipt) != record.event.event_id
                        or payload['execution_authority_granted'] is not False
                        or payload['learning_authority_granted'] is not False):
                    raise DeliveredHistoryError('history scope unavailable')
                ref = ContentReference.from_event_payload(payload['content'])
                with closing(self.vault._connect()) as connection:
                    row = connection.execute('SELECT * FROM content_items WHERE content_id=?', (ref.content_id,)).fetchone()
                if row is None:
                    # Erasure resumption/backup completion is handled by the
                    # vault maintenance, not by reconstructing a missing copy.
                    continue
                if (row['subject'] != record.event.subject or row['purpose'] != 'message.delivered-history'
                        or self.vault._reference(row) != ref
                        or ref.sensitivity != record.event.sensitivity
                        or ref.retention_until != record.event.expires_at):
                    raise DeliveredHistoryError('history storage scope unavailable')
                if self._check_dependencies(payload['dependencies'], record.event.subject):
                    report['erased'] += self.vault.erase_item(ref.content_id).newly_erased
            except Exception:
                report['unresolved'] += 1
        return report
