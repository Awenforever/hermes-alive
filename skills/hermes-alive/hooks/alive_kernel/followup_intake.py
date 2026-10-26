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


def record_request(store, configured, *, turn_identity, request_fingerprint, evidence_fingerprint, permission_id,
                   operation='record', target_item_id=None, from_state=None, available_at=None, now=None):
    """Current configured Core host only, never a public/model-callable API."""
    current = store.configuration()
    if (current is None or current.event_id != configured.event_id
            or permission(store,configured)!=(True,permission_id)):
        raise ValueError('current owner intake grant required')
    if operation not in ('record','complete','cancel','snooze','resume'):
        raise ValueError('bounded follow-up purpose required')
    if operation!='record' and (configured.options.get('manage_explicit_followups') is not True
            or not isinstance(target_item_id,str) or not target_item_id
            or from_state not in ('active','snoozed')):
        raise ValueError('guided management grant and exact current item required')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('aware intake time required')
    identity = {'configuration':configured.event_id, 'owner':configured.subject,
                'turn':turn_identity, 'request':request_fingerprint,'evidence':evidence_fingerprint,
                'operation':operation,'target':target_item_id,'from_state':from_state,'available_at':available_at}
    event_id = 'followup.request:' + store.protector.authenticate_json(DOMAIN, identity)
    existing = store.journal.get(event_id)
    if existing is not None:
        return existing
    event = EventEnvelope(event_id=event_id, event_type='conversation.inbound', source=SOURCE,
        actor=configured.subject, subject=configured.subject, observed_at=now, occurred_at=now,
        sensitivity=Sensitivity.PRIVATE, payload={
            'configuration_event_id':configured.event_id, 'permission_event_id':permission_id,'turn_identity':turn_identity,
            'request_fingerprint':request_fingerprint, 'evidence_fingerprint':evidence_fingerprint,
            'operation':operation,'target_item_id':target_item_id,'from_state':from_state,'available_at':available_at,
            'retention_until':(now+timedelta(days=configured.options['outbound_retention_days'])).isoformat(),
            'interpretation':'main_model_under_owner_grant', 'literal_owner_confirmation':False,
            'raw_content_stored':False, 'external_action_authorized':False})
    def still_allowed(_connection):
        current=store.configuration()
        if current is None or current.event_id!=configured.event_id or permission(store,current)!=(True,permission_id):
            raise ValueError('intake permission changed')
    return store.journal.append(_signed(store,event),precondition=still_allowed)


def _validated_source(journal,source_id,subject,observed_at):
    """Protected historical grant; no new journal or opaque model authority."""
    source=journal.get(source_id)
    if source is None:raise ValueError('source unavailable')
    event=source.event
    if (event.source!=SOURCE or event.event_type!='conversation.inbound'
            or event.actor!=subject or event.subject!=subject
            or event.sensitivity is not Sensitivity.PRIVATE or event.observed_at>observed_at):
        raise ValueError('current owner source required')
    store=KernelSetupStore(journal.path.parent,journal=journal)
    grant=journal.get(event.payload.get('configuration_event_id',''))
    configured=store._configuration(grant)
    if (configured.subject!=subject or configured.options.get('accept_explicit_followups') is not True
            or grant.event.observed_at>event.observed_at or not _verified(store,event)):
        raise ValueError('source grant unavailable')
    payload=_thaw_json(event.payload)
    if (permission(store,configured,before_sequence=source.sequence)!=(True,payload.get('permission_event_id'))
            or payload.get('interpretation')!='main_model_under_owner_grant'
            or payload.get('literal_owner_confirmation') is not False
            or payload.get('raw_content_stored') is not False or payload.get('external_action_authorized') is not False):
        raise ValueError('source authority changed')
    expiry=datetime.fromisoformat(payload['retention_until'])
    if (expiry.tzinfo is None or not event.observed_at<=observed_at<expiry
            or expiry>event.observed_at+timedelta(days=configured.options['outbound_retention_days'])):
        raise ValueError('source outside its admitted lifetime')
    return source,configured,expiry


def validates_proposal(journal, proposal):
    """Read/rebuild verification, not authority inferred from a model label."""
    try:
        if (proposal.source!='alive.agenda' or proposal.actor!=ACTOR
                or proposal.payload.get('authority')!='user_delegated'
                or proposal.payload.get('kind')!='commitment'
                or proposal.sensitivity is not Sensitivity.PRIVATE):return False
        sources=proposal.payload.get('source_event_ids',())
        if len(sources)!=1:return False
        source,_configured,expiry=_validated_source(journal,sources[0],proposal.subject,proposal.observed_at)
        if source.event.payload.get('operation','record')!='record' or source.event.payload.get('target_item_id') is not None:return False
        target=datetime.fromisoformat(proposal.payload['expires_at'])
        return (expiry.tzinfo is not None and target.tzinfo is not None
                and proposal.observed_at<target<=expiry)
    except (ValueError,TypeError,KeyError,OSError,RuntimeError):
        return False


def validates_transition(journal,event,*,subject,from_state):
    try:
        if (event.event_type!='agenda.transitioned' or event.source!='alive.agenda'
                or event.actor!=ACTOR or event.subject is not None
                or event.sensitivity is not Sensitivity.INTERNAL
                or event.payload.get('authority')!='user_delegated'):return False
        source,configured,_expiry=_validated_source(journal,event.payload['source_event_id'],subject,event.observed_at)
        mapping={'complete':'completed','cancel':'dismissed','snooze':'snoozed','resume':'active'}
        payload=source.event.payload
        return (configured.options.get('manage_explicit_followups') is True
            and mapping.get(payload.get('operation'))==event.payload.get('to_state')
            and payload.get('target_item_id')==event.payload.get('item_id')
            and payload.get('from_state')==from_state
            and payload.get('available_at')==event.payload.get('available_at'))
    except (ValueError,TypeError,KeyError,OSError,RuntimeError):return False
