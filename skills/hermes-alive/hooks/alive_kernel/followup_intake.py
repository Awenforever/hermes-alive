"""Owner-delegated interpretation receipts, distinct from literal confirmation.

Only the Core-bound host calls the writer. The main model selects meaning, not
identity or authority. Readers independently verify the protected setup grant
and receipt; metadata/fingerprints are not independent semantic proof.
"""
from dataclasses import replace
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json

from .events import EventEnvelope, Sensitivity, _thaw_json
from .content_vault import ContentReference,ContentVaultError
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
                   operation='record', target_item_id=None, from_state=None, available_at=None, now=None,source_message=None,
                   revision_binding=None,project_context=None,notify_owner=False):
    """Current configured Core host only, never a public/model-callable API."""
    current = store.configuration()
    if (current is None or current.event_id != configured.event_id
            or permission(store,configured)!=(True,permission_id)):
        raise ValueError('current owner intake grant required')
    if operation not in ('record','complete','cancel','snooze','resume','revise'):
        raise ValueError('bounded follow-up purpose required')
    if type(notify_owner) is not bool or (operation!='record' and notify_owner):
        raise ValueError('typed owner communication choice is creation-only')
    if operation=='revise':
        from .agenda_revisions import FLAG,FIELDS
        if (configured.options.get(FLAG) is not True or configured.options.get('retain_followup_source') is not True
                or not isinstance(revision_binding,dict) or set(revision_binding)!=set(FIELDS)):
            raise ValueError('guided revision and exact amendment binding required')
    elif revision_binding is not None:raise ValueError('unexpected amendment binding')
    context_fingerprint=None
    if operation=='record' and configured.options.get('core_work_context_version')==1:
        from .core_work_context import validate
        project_context=validate(project_context)
        context_fingerprint=store.protector.authenticate_json('alive.core-project-context.v1',project_context)
    elif project_context is not None:raise ValueError('project context was not admitted for this source purpose')
    if operation!='record' and (configured.options.get('manage_explicit_followups') is not True
            or not isinstance(target_item_id,str) or not target_item_id
            or from_state not in ('active','snoozed') and not (operation=='resume' and from_state in ('completed','dismissed'))):
        raise ValueError('guided management grant and exact current item required')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('aware intake time required')
    retain=configured.options.get('retain_followup_source') is True
    if retain:
        if (not isinstance(source_message,str) or not source_message.strip() or len(source_message)>6000
                or store.protector.authenticate_json('alive.intake.request.v1',source_message)!=request_fingerprint):
            raise ValueError('exact current owner message within 6000 characters required; no truncation')
    elif source_message is not None:
        raise ValueError('original follow-up source retention was not authorized')
    identity = {'configuration':configured.event_id, 'owner':configured.subject,
                'turn':turn_identity, 'request':request_fingerprint,'evidence':evidence_fingerprint,
                'operation':operation,'target':target_item_id,'from_state':from_state,'available_at':available_at}
    if revision_binding is not None:identity['revision_binding']=revision_binding
    if context_fingerprint is not None:identity['core_project_context']=context_fingerprint
    event_id = 'followup.request:' + store.protector.authenticate_json(DOMAIN, identity)
    existing = store.journal.get(event_id)
    if existing is not None:
        if existing.event.payload.get('notify_owner',False) is not notify_owner:
            raise ValueError('an intake replay cannot change its owner communication scope')
        return existing
    expiry=now+timedelta(days=configured.options['outbound_retention_days'])
    content=(store.vault.put_json({'message':source_message,
        **({'core_project_context':project_context} if context_fingerprint is not None else {})},subject=configured.subject,
        purpose='agenda.owner-request',sensitivity=Sensitivity.PRIVATE,retention_until=expiry,
        content_id=event_id+':source') if retain else None)
    event = EventEnvelope(event_id=event_id, event_type='agenda.revised' if operation=='revise' else 'conversation.inbound', source=SOURCE,
        actor=configured.subject, subject=configured.subject, observed_at=now, occurred_at=now,
        sensitivity=Sensitivity.PRIVATE, payload={
            'configuration_event_id':configured.event_id, 'permission_event_id':permission_id,'turn_identity':turn_identity,
            'request_fingerprint':request_fingerprint, 'evidence_fingerprint':evidence_fingerprint,
            'operation':operation,'target_item_id':target_item_id,'from_state':from_state,'available_at':available_at,
            'retention_until':expiry.isoformat(),
            'interpretation':'main_model_under_owner_grant', 'literal_owner_confirmation':False,
            'raw_content_stored':retain, 'external_action_authorized':False,
            **({'notify_owner':notify_owner} if operation=='record' else {}),
            **({'revision_binding':revision_binding} if revision_binding is not None else {}),
            **({'core_project_context_retained':True,'core_project_context_fingerprint':context_fingerprint}
               if context_fingerprint is not None else {}),
            **({'content':content.to_event_payload()} if content else {})})
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
    if (event.source!=SOURCE or event.event_type not in ('conversation.inbound','agenda.revised')
            or event.actor!=subject or event.subject!=subject
            or event.sensitivity is not Sensitivity.PRIVATE or event.observed_at>observed_at):
        raise ValueError('current owner source required')
    if event.event_type=='agenda.revised' and event.payload.get('operation')!='revise':
        raise ValueError('typed amendment receipt required')
    store=KernelSetupStore(journal.path.parent,journal=journal)
    grant=journal.get(event.payload.get('configuration_event_id',''))
    configured=store._configuration(grant)
    if (configured.subject!=subject or configured.options.get('accept_explicit_followups') is not True
            or grant.event.observed_at>event.observed_at or not _verified(store,event)):
        raise ValueError('source grant unavailable')
    payload=_thaw_json(event.payload)
    if 'notify_owner' in payload and type(payload['notify_owner']) is not bool:
        raise ValueError('owner communication scope changed')
    if (permission(store,configured,before_sequence=source.sequence)!=(True,payload.get('permission_event_id'))
            or payload.get('interpretation')!='main_model_under_owner_grant'
            or payload.get('literal_owner_confirmation') is not False
            or type(payload.get('raw_content_stored')) is not bool
            or payload.get('raw_content_stored') is not (configured.options.get('retain_followup_source') is True)
            or payload.get('external_action_authorized') is not False):
        raise ValueError('source authority changed')
    expiry=datetime.fromisoformat(payload['retention_until'])
    if (expiry.tzinfo is None or not event.observed_at<=observed_at<expiry
            or expiry>event.observed_at+timedelta(days=configured.options['outbound_retention_days'])):
        raise ValueError('source outside its admitted lifetime')
    if payload['raw_content_stored']:
        # Historical admission authority survives content expiry/erasure. The
        # signed reference proves the granted recording scope, not availability
        # or meaning of a body. Decryption belongs to the explicit source reader.
        _source_reference(event,expiry)
    elif 'content' in payload:raise ValueError('unexpected source retention')
    return source,configured,expiry


def _source_reference(event,expiry):
    ref=ContentReference.from_event_payload(event.payload['content'])
    if (ref.retention_until!=expiry or ref.sensitivity is not Sensitivity.PRIVATE
            or ref.content_id!=event.event_id+':source'):
        raise ValueError('owner source retention scope changed')
    return ref


def _source_message(store,event,expiry):
    ref=_source_reference(event,expiry)
    document=store.vault.resolve_json(ref.content_id,expected_subject=event.subject,
        expected_purpose='agenda.owner-request',expected_sensitivity=Sensitivity.PRIVATE)
    message=document.get('message') if isinstance(document,dict) else None
    if (not isinstance(message,str) or not message.strip() or len(message)>6000
            or store.vault.digest_json(document)!=ref.digest
            or store.protector.authenticate_json('alive.intake.request.v1',message)!=event.payload['request_fingerprint']):
        raise ValueError('owner source contents changed')
    return message


def item_source_view(store,item_id,*,subject,include_message=False):
    """Separate original admitted source from the interpreted agenda description."""
    missing={'original_source_available':False,'original_owner_message_included':False,
             'owner_updates_allowed':False}
    proposal=store.journal.get('agenda.proposal:'+item_id)
    if proposal is None or proposal.event.subject!=subject:return missing
    ids=proposal.event.payload.get('source_event_ids',())
    if len(ids)!=1:return missing
    try:
        source,_configured,expiry=_validated_source(store.journal,ids[0],subject,datetime.now(timezone.utc))
        if source.event.payload.get('raw_content_stored') is not True:
            # A separate signed contact choice does not require consent to keep
            # the literal request body. Never reconstruct that absent body.
            return {**missing,'owner_updates_allowed':source.event.payload.get('notify_owner',False) is True}
        message=_source_message(store,source.event,expiry)
    except (ValueError,TypeError,KeyError,OSError,RuntimeError,ContentVaultError):return missing
    project={}
    from .core_work_context import from_source,binding_status
    try:
        context=from_source(store,source.event,expiry)
        if context is not None:project={'core_project_context':context,'core_project_context_status':binding_status(context)}
        elif store.configuration().options.get('core_work_context_version')==1:
            project={'core_project_context_status':'not_retained'}
    except (ValueError,TypeError,KeyError,OSError,RuntimeError):project={'core_project_context_status':'unavailable'}
    amendments=[];history={}
    try:
        with closing(store.journal._connect()) as c:
            transitions=c.execute('SELECT caused_by_event_id,from_state FROM agenda_transitions_v1 '
                'WHERE item_id=? ORDER BY transition_id LIMIT 65',(item_id,)).fetchall()
        if len(transitions)>64:raise ValueError('owner history exceeds bounded agenda view')
        previous=proposal.event.event_id;total=len(message)
        for transition in transitions[1:]:
            record=store.journal.get(transition['caused_by_event_id'])
            if record is None:raise ValueError('owner history unavailable')
            if record.event.event_type=='agenda.revised':
                from .agenda_revisions import validates
                if not validates(store.journal,record.event,subject=subject,from_state=transition['from_state'],
                        prior_transition_event_id=previous):raise ValueError('amendment authority unavailable')
                amendment,_grant,until=_validated_source(store.journal,record.event.event_id,
                    subject,datetime.now(timezone.utc))
                text=_source_message(store,amendment.event,until);total+=len(text)
                if total>6000:raise ValueError('complete retained owner history exceeds 6000 characters')
                amendments.append({'source_event_id':amendment.event.event_id,'message':text,
                    'recorded_at':amendment.event.observed_at.isoformat(),'retention_until':until.isoformat(),
                    'kind':'current_owner_amendment_at_recorded_time_not_a_new_turn'})
            previous=record.event.event_id
        if amendments:
            history={'owner_history_available':True,'owner_amendment_count':len(amendments),
                **({'owner_amendments':amendments} if include_message else {})}
    except (ValueError,TypeError,KeyError,OSError,RuntimeError,ContentVaultError):
        history={'owner_history_available':False,'owner_history_scope':'retained amendment history unavailable or exceeds its bounded view'}
    return {'original_source_available':True,'original_owner_message_included':include_message,
            'owner_updates_allowed':source.event.payload.get('notify_owner',False) is True,
            'source_event_id':source.event.event_id,'original_source_retention_until':expiry.isoformat(),
            'source_recorded_at':source.event.observed_at.isoformat(),
            'source_timestamp_kind':'intake_recorded_at_not_sender_timestamp',
            **history,
            **project,
            **({'original_owner_message':message} if include_message else {})}


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
