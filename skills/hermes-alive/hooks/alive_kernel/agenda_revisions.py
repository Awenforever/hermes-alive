"""Current-owner amendments of an existing commitment, never execution grants.

Keep immutable original and amended sources. The agenda projection is rebuildable;
its rows are not authority. A revision invalidates an earlier work admission, but
does not undo effects, promise process cancellation or submit replacement work.
"""
from contextlib import closing
from collections.abc import Mapping
from datetime import datetime, timezone
import json

from .content_vault import ContentReference, ContentErasedError
from .events import Sensitivity, _thaw_json
from .kernel_setup import KernelSetupStore


FLAG = 'revise_explicit_followups'
FIELDS = ('item_id','prior_transition_event_id','item_version','from_state',
          'content','due_at','available_at','expires_at')


def content_identifier(store,configured,binding,digest):
    return 'agenda.revision.content:'+store.protector.authenticate_json('alive.agenda.revision.content.v1',{
        'configuration':configured.event_id,'owner':configured.subject,'item':binding['item_id'],
        'prior':binding['prior_transition_event_id'],'digest':digest,'due_at':binding['due_at']})


def after_submission(store,work_id,request):
    """Metadata-only fence, including a valid event awaiting projection.

    Never open unrelated chats or body content. A valid owner amendment fences
    old work even if its body cannot be materialised. This is not a claim that
    the projection succeeded. Unknown excess history fails closed for effects.
    """
    admitted=store.journal.get(work_id+':requested')
    if admitted is None:raise ValueError('owned work admission unavailable')
    with closing(store.journal._connect()) as c:
        rows=c.execute("SELECT e.event_id FROM experience_events e "
            "WHERE e.event_type='agenda.revised' AND e.sequence>? "
            "AND json_extract(e.canonical_json,'$.payload.revision_binding.item_id')=? ORDER BY e.sequence DESC LIMIT 65",
            (admitted.sequence,request['item_id'])).fetchall()
    if len(rows)>64:return True
    for row in rows:
        event=store.journal.get(row['event_id']).event
        binding=event.payload.get('revision_binding',{})
        if not isinstance(binding,Mapping):continue
        if validates(store.journal,event,subject=admitted.event.subject,
                from_state=binding.get('from_state'),
                prior_transition_event_id=binding.get('prior_transition_event_id')):
            return True
    return False


def validates(journal,event,*,subject,from_state,prior_transition_event_id):
    """Verify the protected, exact previous version and complete new content ref."""
    try:
        from .followup_intake import _validated_source, SOURCE
        if (event.event_type!='agenda.revised' or event.source!=SOURCE
                or event.actor!=subject or event.subject!=subject
                or event.sensitivity is not Sensitivity.PRIVATE):
            return False
        source,configured,expiry=_validated_source(journal,event.event_id,subject,event.observed_at)
        binding=_thaw_json(event.payload['revision_binding'])
        if set(binding)!=set(FIELDS):return False
        store=KernelSetupStore(journal.path.parent,journal=journal)
        version=store.protector.authenticate_json(
            'alive.agenda.item_version.v1',{'configuration':configured.event_id,'owner':subject,
                'item':binding['item_id'],'event':prior_transition_event_id})
        ref=ContentReference.from_event_payload(binding['content'])
        until=datetime.fromisoformat(binding['expires_at'])
        return (configured.options.get(FLAG) is True
            and configured.options.get('manage_explicit_followups') is True
            and configured.options.get('retain_followup_source') is True
            and source.event.payload.get('operation')=='revise'
            and source.event.payload.get('target_item_id')==binding['item_id']
            and source.event.payload.get('from_state')==from_state==binding['from_state']
            and from_state in ('active','snoozed')
            and binding['prior_transition_event_id']==prior_transition_event_id
            and binding['item_version']==version
            and ref.sensitivity is Sensitivity.PRIVATE and ref.retention_until==until
            and event.observed_at<until<=expiry
            and ref.content_id==content_identifier(store,configured,binding,ref.digest))
    except (ValueError,TypeError,KeyError,AttributeError,OSError,RuntimeError):
        return False


def apply(projection,connection,event):
    """Apply in journal order, using existing agenda tables and private vault."""
    binding=event.payload.get('revision_binding',{})
    if not isinstance(binding,Mapping) or not isinstance(binding.get('item_id'),str):
        return projection._decision(connection,event,'rejected','invalid_owner_revision',None)
    item=binding.get('item_id')
    row=connection.execute('SELECT * FROM agenda_items_v1 WHERE item_id=?',(item,)).fetchone()
    prior=connection.execute('SELECT caused_by_event_id FROM agenda_transitions_v1 WHERE item_id=? '
        'ORDER BY transition_id DESC LIMIT 1',(item,)).fetchone()
    if (row is None or prior is None or row['kind']!='commitment'
            or not validates(projection.journal,event,subject=row['subject'],from_state=row['state'],
                prior_transition_event_id=prior[0])):
        return projection._decision(connection,event,'rejected','invalid_owner_revision',item)
    try:
        payload=binding;ref=ContentReference.from_event_payload(payload['content'])
        if (payload['available_at']!=row['available_at'] or payload['expires_at']!=row['expires_at']):
            raise ValueError('revision cannot silently change attention or retention')
        due=projection._parse_time(payload['due_at'],'due_at')
        available=projection._parse_time(row['available_at'],'available_at')
        expires=projection._parse_time(row['expires_at'],'expires_at')
        if due is not None and (due>=expires or available is not None and available>due):
            raise ValueError('deadline conflicts with follow-up availability/retention')
        try:
            details=projection.content_vault.resolve_json(ref.content_id,expected_subject=row['subject'],
                expected_purpose='agenda.commitment',expected_sensitivity=Sensitivity.PRIVATE)
            if projection.content_vault.digest_json(details)!=ref.digest:
                raise ValueError('revision content changed')
            from .cognition_opportunities import commitment_summary
            commitment_summary(details,state=row['state'],available_at=row['available_at'],
                due_at=payload['due_at'],expires_at=row['expires_at'])
        except ContentErasedError:
            pass  # Historical metadata replay must not resurrect erased bodies.
    except (ValueError,TypeError,KeyError,OSError,RuntimeError) as error:
        return projection._decision(connection,event,'rejected','invalid_revision:'+type(error).__name__,item)
    connection.execute('UPDATE agenda_items_v1 SET content_id=?,due_at=?,updated_at=? WHERE item_id=?',
        (ref.content_id,payload['due_at'],event.observed_at.isoformat(),item))
    connection.execute('INSERT INTO agenda_sources_v1 VALUES (?,?)',(item,event.event_id))
    connection.execute('INSERT INTO agenda_transitions_v1 VALUES (NULL,?,?,?,?,?,?)',
        (item,row['state'],row['state'],'owner_revised',event.event_id,event.observed_at.isoformat()))
    return projection._decision(connection,event,'revised','owner_revised',item)


def append(store,configured,projection,*,item_id,item_version,details,due_at,source_writer,validate):
    """Called only by the authenticated Core main-turn bridge under its lock."""
    from .cognition_opportunities import CognitionOpportunityReader,commitment_summary
    if (configured.options.get(FLAG) is not True
            or configured.options.get('manage_explicit_followups') is not True
            or configured.options.get('retain_followup_source') is not True):
        raise ValueError('guided task revision/source-retention setup required')
    validate();projection.project_new()
    with closing(projection._connect()) as c:
        row=c.execute('SELECT * FROM agenda_items_v1 WHERE item_id=? AND subject=?',
            (item_id,configured.subject)).fetchone()
        prior=c.execute('SELECT caused_by_event_id FROM agenda_transitions_v1 WHERE item_id=? '
            'ORDER BY transition_id DESC LIMIT 1',(item_id,)).fetchone()
    if row is None or prior is None or row['state'] not in ('active','snoozed'):
        raise ValueError('current nonterminal commitment required')
    evidence=CognitionOpportunityReader(store.journal,content_vault=store.vault)._commitment(
        row,subject=configured.subject,now=datetime.now(timezone.utc))
    if evidence is None:raise ValueError('current commitment authority unavailable')
    version=store.protector.authenticate_json('alive.agenda.item_version.v1',{
        'configuration':configured.event_id,'owner':configured.subject,'item':item_id,'event':prior[0]})
    if version!=item_version:raise ValueError('current commitment version changed')
    due=due_at.isoformat() if due_at else None
    if due_at is not None and (due_at>=datetime.fromisoformat(row['expires_at'])
            or row['available_at'] and due_at<datetime.fromisoformat(row['available_at'])):
        raise ValueError('deadline conflicts with follow-up availability/retention')
    commitment_summary(details,state=row['state'],available_at=row['available_at'],due_at=due,expires_at=row['expires_at'])
    binding={'item_id':item_id,'prior_transition_event_id':prior[0],'item_version':version,
        'from_state':row['state'],'due_at':due,'available_at':row['available_at'],'expires_at':row['expires_at']}
    # Content identity is independent of the new source ID; no circular receipt.
    digest=projection.content_vault.digest_json(details)
    ref=projection.content_vault.put_json(details,subject=configured.subject,purpose='agenda.commitment',
        sensitivity=Sensitivity.PRIVATE,retention_until=datetime.fromisoformat(row['expires_at']),
        content_id=content_identifier(store,configured,binding,digest))
    binding['content']=ref.to_event_payload()
    # The protected intake receipt IS the revision event: no two-event crash gap.
    # Core's current-turn precondition runs inside the journal writer transaction.
    source=source_writer(binding)
    projection.project_new()
    with closing(projection._connect()) as c:
        decision=c.execute('SELECT outcome FROM agenda_decisions_v1 WHERE event_id=?',(source.event.event_id,)).fetchone()
    if decision is None or decision[0]!='revised':raise ValueError('revision rejected or projection remains pending')
    return source
