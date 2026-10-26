"""Owner-delegated interpretation receipts, distinct from literal confirmation.

Only the Core-bound host calls the writer. The main model selects meaning, not
identity or authority. Readers independently verify the protected setup grant
and receipt; metadata/fingerprints are not independent semantic proof.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

from .events import EventEnvelope, Sensitivity, _thaw_json
from .kernel_setup import KernelSetupStore


SOURCE = 'hermes.core.alive.followup_intake'
ACTOR = 'system:alive-delegated-intake'
DOMAIN = 'alive.followup.intake.v1'


def _signed(store, event):
    payload=_thaw_json(event.payload)
    payload['authority_authenticator']=store.protector.authenticate_json(DOMAIN,json.loads(event.canonical_json()))
    return replace(event,payload=payload)


def _verified(store,event):
    payload=_thaw_json(event.payload);signature=payload.pop('authority_authenticator',None)
    document=json.loads(event.canonical_json());document['payload']=payload
    return store.protector.verify_json(DOMAIN,document,signature)


def permission(store,configured,*,before_sequence=None):
    """Current permission, or the exact historical permission before a receipt."""
    for record in store.journal.iter_reverse(event_types=('alive.intake.permission',),
            subject=configured.subject,before_sequence=before_sequence):
        event=record.event
        if event.payload.get('configuration_event_id')!=configured.event_id:continue
        if (event.source!='hermes.command.alive.intake' or event.actor!=configured.subject
                or event.sensitivity is not Sensitivity.PRIVATE or not _verified(store,event)
                or type(event.payload.get('enabled')) is not bool):
            raise ValueError('intake permission integrity changed')
        return event.payload['enabled'],event.event_id
    return configured.options.get('accept_explicit_followups') is True,configured.event_id


def set_permission(store,configured,enabled):
    if type(enabled) is not bool:raise ValueError('explicit intake choice required')
    if enabled and configured.options.get('accept_explicit_followups') is not True:
        raise ValueError('complete guided intake/retention setup before enabling it')
    return store.journal.append(_signed(store,EventEnvelope(event_type='alive.intake.permission',
        source='hermes.command.alive.intake',actor=configured.subject,subject=configured.subject,
        sensitivity=Sensitivity.PRIVATE,payload={'configuration_event_id':configured.event_id,'enabled':enabled,
            'raw_content_stored':False,'external_action_authorized':False})))


def record_request(store, configured, *, turn_identity, request_fingerprint, evidence_fingerprint, permission_id, now=None):
    """Current configured Core host only, never a public/model-callable API."""
    current = store.configuration()
    if (current is None or current.event_id != configured.event_id
            or permission(store,configured)!=(True,permission_id)):
        raise ValueError('current owner intake grant required')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('aware intake time required')
    identity = {'configuration':configured.event_id, 'owner':configured.subject,
                'turn':turn_identity, 'request':request_fingerprint,'evidence':evidence_fingerprint}
    event_id = 'followup.request:' + store.protector.authenticate_json(DOMAIN, identity)
    existing = store.journal.get(event_id)
    if existing is not None:
        return existing
    event = EventEnvelope(event_id=event_id, event_type='conversation.inbound', source=SOURCE,
        actor=configured.subject, subject=configured.subject, observed_at=now, occurred_at=now,
        sensitivity=Sensitivity.PRIVATE, payload={
            'configuration_event_id':configured.event_id, 'permission_event_id':permission_id,'turn_identity':turn_identity,
            'request_fingerprint':request_fingerprint, 'evidence_fingerprint':evidence_fingerprint,
            'retention_until':(now+timedelta(days=configured.options['outbound_retention_days'])).isoformat(),
            'interpretation':'main_model_under_owner_grant', 'literal_owner_confirmation':False,
            'raw_content_stored':False, 'external_action_authorized':False})
    def still_allowed(_connection):
        current=store.configuration()
        if current is None or current.event_id!=configured.event_id or permission(store,current)!=(True,permission_id):
            raise ValueError('intake permission changed')
    return store.journal.append(_signed(store,event),precondition=still_allowed)


def validates_proposal(journal, proposal):
    """Read/rebuild verification, not authority inferred from a model label."""
    try:
        if (proposal.source!='alive.agenda' or proposal.actor!=ACTOR
                or proposal.payload.get('authority')!='user_delegated'
                or proposal.payload.get('kind')!='commitment'
                or proposal.sensitivity is not Sensitivity.PRIVATE):return False
        sources=proposal.payload.get('source_event_ids',())
        if len(sources)!=1:return False
        source=journal.get(sources[0])
        if source is None:return False
        event=source.event
        if (event.source!=SOURCE or event.event_type!='conversation.inbound'
                or event.actor!=proposal.subject or event.subject!=proposal.subject
                or event.sensitivity is not Sensitivity.PRIVATE
                or event.observed_at>proposal.observed_at):return False
        store=KernelSetupStore(journal.path.parent,journal=journal)
        grant=journal.get(event.payload.get('configuration_event_id',''))
        configured=store._configuration(grant)
        if (configured.subject!=proposal.subject
                or configured.options.get('accept_explicit_followups') is not True
                or grant.event.observed_at>event.observed_at):return False
        payload=_thaw_json(event.payload)
        if not _verified(store,event):return False
        if permission(store,configured,before_sequence=source.sequence)!=(True,payload.get('permission_event_id')):return False
        if (payload.get('interpretation')!='main_model_under_owner_grant'
                or payload.get('literal_owner_confirmation') is not False
                or payload.get('raw_content_stored') is not False
                or payload.get('external_action_authorized') is not False):return False
        expiry=datetime.fromisoformat(payload['retention_until'])
        target=datetime.fromisoformat(proposal.payload['expires_at'])
        return (expiry.tzinfo is not None and target.tzinfo is not None
                and proposal.observed_at<target<=expiry
                and expiry<=event.observed_at+timedelta(days=configured.options['outbound_retention_days']))
    except (ValueError,TypeError,KeyError,OSError,RuntimeError):
        return False
