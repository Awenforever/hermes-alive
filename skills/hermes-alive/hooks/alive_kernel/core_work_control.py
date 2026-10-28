"""Stop exact owned Core work through its existing schedule/admission authority.

No worker, model, replacement job or cancellation inferred from a local flag.
The signed stop intent fences later tool calls before contacting Core. An RPC
acknowledgment is not a terminal observation and cannot undo earlier effects.
"""
import asyncio
from contextlib import closing

from .core_work import CoreWorkStore
from .file_locks import file_lock


class CoreWorkControl:
    def __init__(self,store):
        self.store=store;self.work=CoreWorkStore(store)

    def group(self,work_id,*,subject):
        request=self.work._read(work_id,'requested',subject)
        if request is None:raise ValueError('exact owned work required')
        with closing(self.store.journal._connect()) as c:
            rows=c.execute("SELECT event_id FROM experience_events WHERE subject=? "
                "AND event_type='work.requested' AND json_extract(canonical_json,'$.payload.parent_work_id')=? "
                "AND json_extract(canonical_json,'$.payload.work_kind')='inspection' ORDER BY sequence DESC LIMIT 2",
                (subject,work_id)).fetchall()
        if len(rows)>1:raise ValueError('ambiguous owned inspection group')
        children=[]
        for row in rows:
            child=row[0].removesuffix(':requested')
            saved=self.work._read(child,'requested',subject)
            if saved['parent_work_id']!=work_id or saved['work_kind']!='inspection':
                raise ValueError('owned inspection group changed')
            children.append(child)
        return [work_id,*children]

    def stop(self,configured,work_id,*,authority,validate):
        """A trusted bridge supplies current owner command/turn authority."""
        if not callable(validate) or not isinstance(authority,dict) or not authority:
            raise ValueError('current owner stop authority required')
        self.work._home();validate()
        if self.store.configuration()!=configured:raise ValueError('current configured owner required')
        owner=configured.subject
        return self._stop_owned(owner,work_id,authority=authority,validate=validate)

    def stop_for_deactivation(self,subject,work_id,*,authority,validate):
        """Trusted profile-operator retirement, not a fabricated owner chat turn.

        Preparing the stop performs only local Core schedule control. Its caller
        settles any required owner cancellation asynchronously before claiming it.
        """
        if (not callable(validate) or not isinstance(authority,dict)
                or authority.get('kind')!='operator_plugin_deactivation'):
            raise ValueError('trusted explicit plugin deactivation required')
        self.work._home();validate()
        return self._stop_owned(subject,work_id,authority=authority,validate=validate,dispatch_owner=False)

    def _attempt_id(self,authority):
        attempt_authority=dict(authority)
        if authority.get('kind')=='current_owner_interpretation':
            # A different valid excerpt is still the same Core owner request,
            # not permission to dispatch another cancellation attempt.
            turn=authority.get('turn',{})
            attempt_authority['turn']={k:turn.get(k) for k in ('turn_identity','permission_id','request_fingerprint')}
        return self.store.protector.authenticate_json('alive.core-work.stop-attempt.v1',attempt_authority)

    def _stop_owned(self,owner,work_id,*,authority,validate,dispatch_owner=True):
        attempt_id=self._attempt_id(authority)
        with file_lock(self.store.root/'core-work.lock',timeout=0):
            targets=self.group(work_id,subject=owner)
            # Mark the entire exact group first. A crash or an unavailable owner
            # must not leave another inspection authorized to start new tools.
            for target in targets:
                validate();self.work._home()
                if self.work._read(target,'stop_requested',owner) is None:
                    self.work._append(target,'stop_requested',owner,
                        {'root_work_id':work_id,'owner_authority':authority,
                         'new_tools_authorized':False,'effects_undone':False},
                        causation=target+':requested',event_type='work.stop_requested')
            observations=[]
            for target in targets:
                validate();self.work._home()
                observations.append(self._stop_one(target,owner,validate,attempt_id,dispatch_owner=dispatch_owner))
            return {'work_id':work_id,'status':'stop_requested','targets':observations,
                'new_work_submitted':False,'effects_undone':False,'agenda_completed':False,
                'physical_channel_send_requested':False,
                'hint':'A stop request prevents further authorized work; inspect Core execution state for termination. '
                       'Earlier or already in-flight effects are not rolled back.'}

    def _stop_one(self,work_id,owner,validate,attempt_id,*,dispatch_owner=True):
        from cron.jobs import get_job,pause_job,is_terminal_job
        from cron.executions import latest_execution
        request=self.work._read(work_id,'requested',owner)
        result={'work_id':work_id,'work_kind':request.get('work_kind','perform'),
            'parent_work_id':request.get('parent_work_id'),
            'effects_undone':False,'execution_stopped_proven':False}
        bound=self.work._read(work_id,'core_bound',owner)
        if bound is None:return {**result,'status':'unbound_handoff_needs_reconciliation','needs_attention':True}
        job=get_job(bound['job_id'])
        if job is None or self.work._definition(job)!=bound['definition_fingerprint']:
            return {**result,'status':'job_missing_or_changed','needs_attention':True}
        execution=latest_execution(job['id'])
        if is_terminal_job(job):
            terminal=execution is not None and execution['status'] in ('completed','failed')
            return {**result,'status':'execution_already_terminal' if terminal else 'terminal_schedule_execution_unverified',
                'core_execution_state':execution['status'] if execution else None,
                'execution_stopped_proven':terminal,'schedule_already_terminal':True,'needs_attention':not terminal}
        validate();self.work._home()
        try:
            stop=self.work._read(work_id,'stop_requested',owner)
            deactivated=(stop or {}).get('owner_authority',{}).get('kind')=='operator_plugin_deactivation'
            paused=pause_job(job['id'],reason=('Alive deactivated: automatic execution stopped; existing records retained'
                if deactivated else 'Alive owner requested stop of this owned work'))
        except ValueError:
            current=get_job(job['id'])
            if (current is None or self.work._definition(current)!=bound['definition_fingerprint']
                    or not is_terminal_job(current)):raise
            # Core may finish between the read and pause. Re-enter only to
            # observe that terminal state, not to reactivate or repeat anything.
            return self._stop_one(work_id,owner,validate,attempt_id,dispatch_owner=dispatch_owner)

        if paused is None or self.work._definition(paused)!=bound['definition_fingerprint']:
            return {**result,'status':'schedule_pause_unverified','needs_attention':True}
        execution=latest_execution(job['id'])
        if execution is None:
            return {**result,'status':'schedule_paused_no_execution_observed','schedule_paused':True}
        if execution['job_id']!=job['id']:raise ValueError('Core execution owner changed')
        result.update(execution_id=execution['id'],core_execution_state=execution['status'],schedule_paused=True)
        if execution['status'] in ('completed','failed'):
            return {**result,'status':'execution_already_terminal','execution_stopped_proven':True}
        # One dispatch per current owner request. An ambiguous RPC is retained,
        # never replayed on a wake. A new explicit owner request may try again
        # against the same recovered Core admission, never a replacement job.
        dispatch='stop-dispatch:'+attempt_id;observation='stop-observed:'+attempt_id
        prior=self.work._read(work_id,dispatch,owner,event_type='work.stop_dispatch_started')
        if prior is not None:
            observed=self.work._read(work_id,observation,owner,event_type='work.stop_owner_observed')
            return {**result,'status':'stop_dispatch_previously_attempted',
                'owner_observation':observed,'needs_attention':observed is None or observed.get('needs_attention',False)}
        if not dispatch_owner:
            return {**result,'status':'owner_cancellation_pending','stop_dispatch_required':True,'needs_attention':True}
        try:asyncio.get_running_loop()
        except RuntimeError:pass
        else:raise ValueError('blocking Core stop must run outside the Gateway event loop')
        validate();self.work._home()
        self.work._append(work_id,dispatch,owner,
            {'job_id':job['id'],'execution_id':execution['id'],'automatic_redispatch_allowed':False},
            causation=work_id+':stop_requested',event_type='work.stop_dispatch_started')
        try:
            observed=asyncio.run(self._cancel_owner(job['id'],execution['id'],bound,validate))
        except Exception as error:
            observed={'status':'owner_stop_outcome_unknown','error_class':type(error).__name__,
                'cancel_acknowledged':False,'execution_stopped_proven':False,'needs_attention':True}
        self.work._append(work_id,observation,owner,observed,
            causation=work_id+':'+dispatch,event_type='work.stop_owner_observed')
        return {**result,**observed}

    async def dispatch_deactivation(self,subject,prepared,*,authority,validate):
        """One bounded canonical cancellation request per prepared owned work.

        No replacement job, timer or automatic redispatch. The Core IO happens
        outside the profile lock; reservation and observations remain durable.
        """
        if (not callable(validate) or not isinstance(authority,dict)
                or authority.get('kind')!='operator_plugin_deactivation'
                or not isinstance(prepared,dict) or not isinstance(prepared.get('targets'),list)):
            raise ValueError('prepared deactivation required')
        attempt_id=self._attempt_id(authority);observations=[]
        for saved in prepared['targets']:
            target=saved['work_id']
            if not saved.get('stop_dispatch_required'):
                observations.append(saved);continue
            validate();self.work._home()
            with file_lock(self.store.root/'core-work.lock',timeout=0):
                current=self._stop_one(target,subject,validate,attempt_id,dispatch_owner=False)
                if not current.get('stop_dispatch_required'):
                    observations.append(current);continue
                bound=self.work._read(target,'core_bound',subject)
                dispatch='stop-dispatch:'+attempt_id;observation='stop-observed:'+attempt_id
                self.work._append(target,dispatch,subject,{
                    'job_id':bound['job_id'],'execution_id':current['execution_id'],
                    'automatic_redispatch_allowed':False},causation=target+':stop_requested',
                    event_type='work.stop_dispatch_started')
            try:
                result=await self._cancel_owner(bound['job_id'],current['execution_id'],bound,validate)
            except Exception as error:
                result={'status':'owner_stop_outcome_unknown','error_class':type(error).__name__,
                    'cancel_acknowledged':False,'execution_stopped_proven':False,'needs_attention':True}
            self.work._append(target,observation,subject,result,
                causation=target+':'+dispatch,event_type='work.stop_owner_observed')
            observations.append({**current,**result,'stop_dispatch_required':False})
        return {**prepared,'targets':observations}

    async def _cancel_owner(self,job_id,execution_id,bound,validate):
        from hermes_cli.gateway_client import connect_gateway
        async with connect_gateway() as client:
            validate();self.work._home()
            # Recover only: never submit or reconstruct an absent admission,
            # guess session IDs, or trust an arbitrary receipt from model input.
            state=await client.rpc('cron.recover',job_id=job_id,request_id=execution_id,
                extra_prompt=None,_timeout=5)
            validate();self.work._home()
            if state.get('status')=='missing':
                return {'status':'owner_admission_not_observed','cancel_acknowledged':False,
                    'execution_stopped_proven':False,'needs_attention':True}
            job=state.get('job')
            if (not isinstance(job,dict) or job.get('id')!=job_id
                    or self.work._definition(job)!=bound['definition_fingerprint']):
                raise ValueError('Core recovered admission differs from owned work')
            receipt={k:state.get(k) for k in ('session_id','admission_id')}
            if any(not isinstance(v,str) or not v or len(v)>256 for v in receipt.values()):
                raise ValueError('Core returned an invalid admission receipt')
            if state.get('status')=='terminal':
                return {'status':'owner_terminal_observed','cancel_acknowledged':False,
                    'execution_stopped_proven':True,'effects_undone':False}
            if state.get('status') not in ('queued','started'):raise ValueError('Core admission outcome unavailable')
            validate();self.work._home()
            answer=await client.rpc('cron.cancel',**receipt,_timeout=5)
            validate();self.work._home()
            if answer!={'ok':True}:raise ValueError('Core cancellation acknowledgment unavailable')
            state=await client.rpc('cron.status',**receipt,_timeout=5)
            validate();self.work._home()
            terminal=state.get('status')=='terminal'
            return {'status':'owner_terminal_observed' if terminal else 'owner_cancellation_requested',
                'cancel_acknowledged':True,'owner_admission_state':state.get('status'),
                'execution_stopped_proven':terminal,'effects_undone':False,
                'needs_attention':state.get('status') not in ('queued','started','terminal')}
