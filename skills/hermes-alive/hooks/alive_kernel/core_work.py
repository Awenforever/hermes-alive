"""Owned handoff to native Hermes jobs; no scheduler, shell or model executor.

Job lifecycle facts never establish task success. Uncertain handoffs are not
retried. The caller supplies current owner/turn/item authority on every launch.
"""
from dataclasses import replace
from contextlib import closing
import json
import re

from .events import EventEnvelope,Sensitivity,_thaw_json
from .file_locks import file_lock


def owns_commitment(journal,*,subject,item_id):
    """Verify a handoff without turning the task into a user-to-do reminder."""
    with closing(journal._connect()) as connection:
        row=connection.execute("SELECT event_id FROM experience_events WHERE subject=? AND event_type=? "
            "AND json_extract(canonical_json,'$.payload.item_id')=? ORDER BY sequence DESC LIMIT 1",
            (subject,'work.requested',item_id)).fetchone()
    if row is None:return False
    from .kernel_setup import KernelSetupStore
    store=KernelSetupStore(journal.path.parent,journal=journal)
    return CoreWorkStore(store)._read(row['event_id'].removesuffix(':requested'),'requested',subject) is not None


class CoreWorkStore:
    SOURCE='alive.core-work'

    def __init__(self,store):
        self.store,self.journal,self.protector=store,store.journal,store.protector
        self.home=store.root.parents[3]

    def _home(self):
        from hermes_constants import get_hermes_home
        if get_hermes_home().resolve()!=self.home:raise ValueError('Core work profile changed')

    def _append(self,work_id,suffix,owner,payload,*,causation=None,event_type=None):
        event=EventEnvelope(event_id=work_id+':'+suffix,event_type=event_type or 'work.'+suffix,
            source=self.SOURCE,actor='system:alive-core-work',subject=owner,
            causation_id=causation,sensitivity=Sensitivity.PRIVATE,payload=payload)
        document=json.loads(event.canonical_json())
        event=replace(event,payload={**payload,'integrity_authenticator':
            self.protector.authenticate_json('alive.core-work.event.v1',document)})
        return self.journal.append(event)

    def _read(self,work_id,suffix,owner,*,event_type=None):
        if not isinstance(work_id,str) or not re.fullmatch(r'core-work:[a-f0-9]{64}',work_id):
            raise ValueError('exact Core work identifier required')
        record=self.journal.get(work_id+':'+suffix)
        if record is None:return None
        event=record.event;payload=_thaw_json(event.payload)
        signature=payload.pop('integrity_authenticator',None)
        document=json.loads(event.canonical_json());document['payload']=payload
        if (event.source!=self.SOURCE or event.actor!='system:alive-core-work' or event.subject!=owner
                or event.event_type!=(event_type or 'work.'+suffix) or event.sensitivity is not Sensitivity.PRIVATE
                or not self.protector.verify_json('alive.core-work.event.v1',document,signature)):
            raise ValueError('Core work ownership or integrity changed')
        return payload

    @staticmethod
    def toolsets(values):
        if (not isinstance(values,list) or len(values)>8
                or any(not isinstance(v,str) or not v or len(v)>128
                       or any(c.isspace() or ord(c)<32 for c in v) for v in values)
                or len(set(values))!=len(values) or 'no_mcp' in values):
            raise ValueError('explicit bounded Core toolsets required')
        return sorted(values)

    @staticmethod
    def native_toolsets(sets):
        from cron.scheduler import _resolve_cron_enabled_toolsets
        from hermes_cli.config import load_config_readonly
        # Core otherwise adds every enabled MCP server to a nonempty native
        # allowlist, including servers enabled after the job was prepared.
        native=sets+['no_mcp'] if sets else []
        resolved=_resolve_cron_enabled_toolsets({'enabled_toolsets':native},load_config_readonly())
        if set(resolved)!=set(sets):raise ValueError('Core cannot preserve the exact requested tool scope')
        return native

    def identifier(self,configured,*,item,turn_evidence,toolsets):
        identity=dict(owner=configured.subject,configuration=configured.event_id,
            item=item['item_id'],version=item['item_version'],turn=turn_evidence,toolsets=self.toolsets(toolsets))
        return 'core-work:'+self.protector.authenticate_json('alive.core-work.identity.v1',identity)

    def launch(self,configured,*,item,turn_evidence,toolsets,validate,explicit_confirmation=False):
        """Only a trusted bridge may supply the owner-confirmation boolean."""
        sets=self.toolsets(toolsets)
        if type(explicit_confirmation) is not bool or not callable(validate):
            raise ValueError('trusted owner-confirmation and current authority validator required')
        if configured.options.get('core_background_work') is not True:
            raise ValueError('guided Core background/context grant required')
        native_sets=self.native_toolsets(sets)
        if not explicit_confirmation and not set(sets)<=set(configured.options.get('automatic_core_toolsets',[])):
            raise ValueError('this operation needs owner confirmation')
        work_id=self.identifier(configured,item=item,turn_evidence=turn_evidence,toolsets=sets)
        with file_lock(self.store.root/'core-work.lock',timeout=0):
            self._home()
            if self._read(work_id,'requested',configured.subject) is not None:
                return self.status(work_id,subject=configured.subject)
            previous=self.previous(item['item_id'],subject=configured.subject)
            if previous and not explicit_confirmation:
                return {**previous,'new_work_submitted':False,'new_attempt_confirmation_required':True}
            if previous and previous['status'] not in ('core_completed_result_unverified','core_failed_result_unverified'):
                raise ValueError('prior Core work must be reconciled before another attempt')
            validate()
            plan={'task':item['details'],'due_at':item.get('due_at'),
                  'toolsets':sets,'configuration':configured.event_id,'item_version':item['item_version']}
            source_id='agenda.proposal:'+item['item_id']
            self._append(work_id,'requested',configured.subject,{
                'configuration_event_id':configured.event_id,'item_id':item['item_id'],
                'item_version':item['item_version'],'source_event_id':source_id,
                'turn_evidence':dict(turn_evidence),
                'assignment_fingerprint':self.protector.authenticate_json('alive.core-work.assignment.v1',plan),
                'task_body_copied_into_alive_journal':False,'task_body_retention_owned_by_core':True,
                'toolsets':sets,'literal_operation_confirmation':explicit_confirmation,
                'authority':'user_confirmed' if explicit_confirmation else 'user_delegated',
                'task_success_proven':False},causation=source_id)
            self._append(work_id,'handoff_started',configured.subject,{'replacement_job_allowed':False},
                causation=work_id+':requested')
            # The durable intent precedes Core IO. A crash before binding keeps
            # this operation uncertain instead of creating another job on replay.
            try:self._handoff(work_id,configured,plan,native_sets,validate)
            except Exception as error:
                # Report the durable stage and identity, not a generic failed
                # action that could invite replay after an already-created job.
                return {**self.status(work_id,subject=configured.subject),
                        'needs_attention':True,'handoff_error_type':type(error).__name__}
            return self.status(work_id,subject=configured.subject)

    def _handoff(self,work_id,configured,plan,native_sets,validate):
        from cron.jobs import create_job,get_job,trigger_job
        validate();self._home()
        prompt=('Perform the following ongoing owner-assigned work. Preserve all constraints. '
            'Use only the enabled Core toolsets and existing Core permissions. '
            'Return the actual work/result and unresolved issues locally; do not send proactive '
            'messages, schedule replacement jobs or claim an effect that you did not verify.\n'
            +json.dumps({'assignment':plan['task'],'due_at':plan['due_at']},ensure_ascii=False,allow_nan=False))
        job=create_job(prompt=prompt,schedule='1h',name='alive-'+work_id.split(':')[1][:32],
            repeat=1,deliver='local',enabled_toolsets=native_sets,paused=True)
        if (job.get('state')!='paused' or job.get('enabled_toolsets')!=native_sets
                or job.get('deliver')!='local' or job.get('script') or job.get('no_agent')
                or (job.get('repeat') or {}).get('times')!=1
                or any(job.get(k) for k in ('model','provider','base_url','context_from','skills','skill','workdir'))):
            raise ValueError('Core prepared job differs from authorized work')
        fingerprint=self._definition(job)
        self._append(work_id,'core_bound',configured.subject,{
            'job_id':job['id'],'definition_fingerprint':fingerprint},causation=work_id+':handoff_started')
        validate();self._home()
        current=get_job(job['id'])
        if current is None or current.get('state')!='paused' or self._definition(current)!=fingerprint:
            raise ValueError('prepared Core job changed before activation')
        self._append(work_id,'activation_started',configured.subject,{'job_id':job['id']},causation=work_id+':core_bound')
        validate();self._home()
        activated=trigger_job(job['id'])
        if activated is None:raise ValueError('Core activation not acknowledged')
        from cron.scheduler_provider import resolve_cron_scheduler
        resolve_cron_scheduler().register_job(activated)
        self._append(work_id,'activated',configured.subject,{
            'job_id':job['id'],'scheduler_registration_acknowledged':True},causation=work_id+':activation_started')

    def _definition(self,job):
        from cron.job_definition import JOB_DEFINITION_FIELDS
        return self.protector.authenticate_json('alive.core-work.definition.v1',{
            **{k:job.get(k) for k in sorted(JOB_DEFINITION_FIELDS)},
            'repeat_times':(job.get('repeat') or {}).get('times')})

    def previous(self,item_id,*,subject):
        if not isinstance(item_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}',item_id):
            raise ValueError('exact bounded agenda identifier required')
        with closing(self.journal._connect()) as connection:
            row=connection.execute("SELECT event_id FROM experience_events WHERE subject=? AND event_type=? "
                "AND json_extract(canonical_json,'$.payload.item_id')=? ORDER BY sequence DESC LIMIT 1",
                (subject,'work.requested',item_id)).fetchone()
        return self.status(row['event_id'].removesuffix(':requested'),subject=subject) if row else None

    def refresh_observations(self,configured,*,validate):
        """Existing host-cycle read; no poller, result-body ingestion or retry.

        Record changed lifecycle facts only. Neither Core completion nor its
        model's local output establishes the assigned outcome. This bounded
        scan does not claim an exhaustive work inventory.
        """
        validate();self._home()
        if configured.options.get('core_background_work') is not True:return ()
        with closing(self.journal._connect()) as connection:
            rows=connection.execute("SELECT e.event_id FROM experience_events e "
                "JOIN agenda_items_v1 a ON a.item_id=json_extract(e.canonical_json,'$.payload.item_id') "
                "AND a.subject=e.subject WHERE e.subject=? AND e.event_type='work.requested' "
                "AND a.state IN ('active','snoozed') ORDER BY e.sequence DESC LIMIT 128",
                (configured.subject,)).fetchall()
        observed=[];seen=set()
        for row in rows:
            validate();self._home()
            work_id=row['event_id'].removesuffix(':requested')
            request=self._read(work_id,'requested',configured.subject)
            if request['item_id'] in seen:continue
            seen.add(request['item_id'])
            if request['configuration_event_id']!=configured.event_id:continue
            state=self.status(work_id,subject=configured.subject)
            suffix='observation:'+self.protector.authenticate_json('alive.core-work.observation.v1',state)
            if self._read(work_id,suffix,configured.subject,event_type='work.observed') is None:
                validate();self._home()
                self._append(work_id,suffix,configured.subject,state,causation=work_id+':requested',
                    event_type='work.observed')
            observed.append(work_id+':'+suffix)
        return tuple(observed)

    def current_observation(self,item_id,*,subject):
        """Use a signed host observation only while its Core facts still match."""
        current=self.previous(item_id,subject=subject)
        if current is None:return None
        work_id=current['work_id']
        configured=self.store.configuration()
        request=self._read(work_id,'requested',subject)
        if (configured is None or configured.subject!=subject
                or configured.options.get('core_background_work') is not True
                or configured.event_id!=request['configuration_event_id']):return None
        suffix='observation:'+self.protector.authenticate_json('alive.core-work.observation.v1',current)
        saved=self._read(work_id,suffix,subject,event_type='work.observed')
        return (work_id+':'+suffix,saved) if saved==current else None

    def status(self,work_id,*,subject):
        self._home()
        request=self._read(work_id,'requested',subject)
        if request is None:raise ValueError('owned Core work unavailable')
        result={'work_id':work_id,'item_id':request['item_id'],'task_success_proven':False,
                'agenda_completed':False,'automatic_retry_allowed':False,
                'automatic_result_followup_enabled':False,
                'core_profile_context_authorized':True,'physical_channel_send_requested':False}
        bound=self._read(work_id,'core_bound',subject)
        if bound is None:return {**result,'status':'handoff_uncertain','needs_attention':True}
        from cron.jobs import get_job
        from cron.executions import latest_execution
        job=get_job(bound['job_id'])
        if job is None:return {**result,'status':'core_job_missing_outcome_unknown','needs_attention':True}
        if self._definition(job)!=bound['definition_fingerprint']:
            return {**result,'status':'core_job_definition_changed','needs_attention':True}
        execution=latest_execution(bound['job_id'])
        if execution:
            state=execution['status']
            return {**result,'job_id':bound['job_id'],'execution_id':execution['id'],
                    'status':'core_'+state+'_result_unverified','core_execution_state':state,
                    'needs_attention':state in ('unknown','failed')}
        activated=self._read(work_id,'activated',subject)
        attempted=self._read(work_id,'activation_started',subject)
        return {**result,'job_id':bound['job_id'],
                'status':'submitted_to_core' if activated else
                         ('activation_unconfirmed' if attempted else 'prepared_not_activated_by_alive'),
                'core_job_state':job.get('state'),'needs_attention':activated is None}
