"""Retained Core-declared project identity, never a cwd guessed by Alive.

Core owns normalization, AGENTS/context loading and execution. Paths/identity are
private task data. No env/process/home fallback and no project-file reader here.
"""
from datetime import datetime,timezone
from pathlib import Path

from .content_vault import ContentReference
from .events import Sensitivity


VERSION='core_work_context_version'
PURPOSE='core-work.project-context'


class ProjectContextUnavailable(ValueError):pass


def validate(value):
    if (not isinstance(value,dict) or set(value)!={'version','status','source','declared_cwd','identity'}
            or value['version']!=1 or type(value['version']) is not int
            or value['source'] not in ('core_task','core_session','core_bound_session','core_durable_session','core_no_declared_project')):
        raise ProjectContextUnavailable('invalid retained Core project context')
    if value['status']=='no_declared_project':
        if value['declared_cwd'] is not None or value['identity'] is not None:
            raise ProjectContextUnavailable('unknown project cannot acquire a guessed directory')
    elif value['status'] in ('declared_local','declared_unavailable'):
        if (not isinstance(value['declared_cwd'],str) or not value['declared_cwd']
                or len(value['declared_cwd'])>4096 or '\0' in value['declared_cwd']):
            raise ProjectContextUnavailable('bounded Core project directory required')
        if value['status']=='declared_local':
            identity=value['identity']
            if (not isinstance(identity,dict) or set(identity)!={'resolved','device','inode'}
                    or not isinstance(identity['resolved'],str) or not Path(identity['resolved']).is_absolute()
                    or any(type(identity[k]) is not int for k in ('device','inode'))):
                raise ProjectContextUnavailable('local project identity required')
        elif value['identity'] is not None:raise ProjectContextUnavailable('unavailable project has no local identity')
    else:raise ProjectContextUnavailable('unknown project context state')
    return value


def identity(path):
    root=Path(path).expanduser()
    if not root.is_absolute() or not root.is_dir():raise ProjectContextUnavailable('recorded Core project is not an existing local directory')
    resolved=root.resolve(strict=True);stat=resolved.stat()
    return {'resolved':str(resolved),'device':stat.st_dev,'inode':stat.st_ino}


def capture(task_id,session_id):
    """Called only inside an authenticated current owner tool turn."""
    from tools.terminal_tool import get_session_cwd
    from agent.runtime_cwd import scoped_session_cwd
    from gateway.session_context import bound_session_key
    candidates=(('core_task',get_session_cwd(task_id)),('core_session',scoped_session_cwd()),
        ('core_bound_session',get_session_cwd(bound_session_key()) if bound_session_key() else None),
        ('core_durable_session',get_session_cwd(session_id) if session_id else None))
    for source,raw in candidates:
        if not isinstance(raw,str) or not raw.strip():continue
        raw=raw.strip();result={'version':1,'source':source,'declared_cwd':raw,
            'status':'declared_unavailable','identity':None}
        try:result.update(status='declared_local',identity=identity(raw))
        except (ValueError,OSError):pass
        return validate(result)
    return {'version':1,'source':'core_no_declared_project','declared_cwd':None,
        'status':'no_declared_project','identity':None}


def workdir(value):
    validate(value)
    if value['status']=='no_declared_project':return None
    if value['status']!='declared_local':raise ProjectContextUnavailable('Core project cannot be bound by this host; no cwd fallback')
    try:current=identity(value['declared_cwd'])
    except OSError:raise ProjectContextUnavailable('recorded Core project is unavailable') from None
    if current!=value['identity']:raise ProjectContextUnavailable('recorded Core project directory identity changed')
    return current['resolved']


def from_source(store,event,expiry):
    from .followup_intake import _source_reference,_verified
    configured=store._configuration(store.journal.get(event.payload['configuration_event_id']))
    if not event.payload.get('core_project_context_retained'):return None
    if configured.options.get(VERSION)!=1 or not _verified(store,event):
        raise ProjectContextUnavailable('project context source grant changed')
    ref=_source_reference(event,expiry)
    document=store.vault.resolve_json(ref.content_id,expected_subject=event.subject,
        expected_purpose='agenda.owner-request',expected_sensitivity=Sensitivity.PRIVATE)
    if store.vault.digest_json(document)!=ref.digest:raise ProjectContextUnavailable('project source contents changed')
    value=validate(document['core_project_context'])
    if store.protector.authenticate_json('alive.core-project-context.v1',value)!=event.payload.get('core_project_context_fingerprint'):
        raise ProjectContextUnavailable('project source fingerprint changed')
    return value


def binding_status(value):
    if value is None:return 'not_retained'
    try:
        directory=workdir(value)
        return 'available' if directory is not None else 'no_declared_project'
    except (ValueError,OSError,RuntimeError):return 'unavailable'


def retain(store,configured,item,work_id,*,origin='recorded_task'):
    if configured.options.get(VERSION)!=1:return {}
    value=item.get('core_project_context')
    if value is None:raise ProjectContextUnavailable('recorded project context unavailable; an explicit workspace choice is required')
    workdir(value)
    expiry=datetime.fromisoformat(item['expires_at']) if item.get('expires_at') else None
    if expiry is None:
        from datetime import timedelta
        expiry=datetime.now(timezone.utc)+timedelta(days=configured.options['outbound_retention_days'])
    ref=store.vault.put_json(validate(value),subject=configured.subject,purpose=PURPOSE,
        sensitivity=Sensitivity.PRIVATE,retention_until=expiry,content_id=work_id+':project-context')
    return {'project_context_reference':ref.to_event_payload(),'project_context_work_id':work_id,
        'project_context_origin':origin,'project_context_protocol':1}


def read(work,work_id,request,subject):
    if 'project_context_reference' not in request:return None
    ref=ContentReference.from_event_payload(request['project_context_reference'])
    owner=request.get('project_context_work_id')
    if (request.get('project_context_protocol')!=1 or owner not in (work_id,request.get('parent_work_id'))
            or not isinstance(owner,str) or ref.content_id!=owner+':project-context'
            or ref.sensitivity is not Sensitivity.PRIVATE):
        raise ProjectContextUnavailable('project context ownership changed')
    if owner!=work_id:
        parent=work._read(owner,'requested',subject)
        if parent is None or parent.get('project_context_reference')!=request['project_context_reference']:
            raise ProjectContextUnavailable('inspector project differs from producer')
    value=work.store.vault.resolve_json(ref.content_id,expected_subject=subject,
        expected_purpose=PURPOSE,expected_sensitivity=Sensitivity.PRIVATE)
    if work.store.vault.digest_json(value)!=ref.digest:raise ProjectContextUnavailable('project context contents changed')
    return validate(value)


def expected_workdir(work,work_id,request,subject):
    value=read(work,work_id,request,subject)
    return workdir(value) if value is not None else None
