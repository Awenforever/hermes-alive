"""Retire authenticated Alive work without deleting Core history or results.

The trusted bridge supplies explicit deactivation authority. This controller
only observes, pauses and requests cancellation through existing Core APIs.
It never supplies a replacement job, a retry timer or a claimed owner chat turn.
"""
from contextlib import closing

from .core_work import CoreWorkStore
from .core_work_control import CoreWorkControl


class CoreWorkRetirement:
    def __init__(self,store):
        self.store=store;self.work=CoreWorkStore(store);self.control=CoreWorkControl(store)

    def prepare(self,*,authority,validate,subject=None):
        if (not callable(validate) or not isinstance(authority,dict)
                or authority.get('kind')!='operator_plugin_deactivation'):
            raise ValueError('trusted explicit deactivation required')
        self.work._home();validate()
        # Fence new handoffs before taking the inventory. Stopping a host loop
        # alone cannot revoke an already in-flight planning step's authority.
        from .autonomy_policy import AutonomyPolicyProjection
        from uuid import uuid4
        configured=self.store.configuration()
        if configured is not None and (subject is None or configured.subject==subject):
            policies=AutonomyPolicyProjection(self.store.journal)
            previous=policies.current(configured.subject)
            if previous is not None and previous.enabled:
                policies.apply(policies.append_update(subject=configured.subject,actor=configured.subject,
                    expected_revision=previous.revision,enabled=False,context=previous.context,
                    operation_id='operator-deactivate:'+uuid4().hex))
        from cron.jobs import list_jobs,is_terminal_job
        jobs={job['id']:job for job in list_jobs(include_disabled=True)}
        with closing(self.store.journal._connect()) as c:
            rows=c.execute("SELECT event_id,subject FROM experience_events WHERE event_type='work.requested' "
                +("AND subject=? " if subject is not None else '')+"ORDER BY sequence DESC",
                (subject,) if subject is not None else ()).fetchall()
        candidates=[];latest_items=set();errors=[];included=set();verified=[]
        for row in rows:
            work_id=row['event_id'].removesuffix(':requested');owner=row['subject']
            try:
                request=self.work._read(work_id,'requested',owner)
                if request is None:raise ValueError('owned request unavailable')
                key=(owner,request['item_id'])
                latest=request.get('work_kind','perform')=='perform' and key not in latest_items
                if request.get('work_kind','perform')=='perform':latest_items.add(key)
                bound=self.work._read(work_id,'core_bound',owner)
                job=jobs.get(bound['job_id']) if bound else None
                # Keep the last step fenced against automatic continuation after
                # re-enable. Older terminal steps need no schedule mutation.
                if not latest and job is not None and is_terminal_job(job):continue
                verified.append((owner,work_id,request))
            except (ValueError,OSError,RuntimeError) as error:
                errors.append({'error_class':type(error).__name__,'work_stopped_proven':False})
        # Parents first: a newer inspection belongs to its parent's stop group,
        # rather than becoming a second cancellation attempt for the same work.
        verified.sort(key=lambda entry:entry[2].get('work_kind','perform')=='inspection')
        for owner,work_id,request in verified:
            if (owner,work_id) in included:continue
            try:
                targets=self.control.group(work_id,subject=owner)
                included.update((owner,target) for target in targets)
                candidates.append((owner,work_id))
            except (ValueError,OSError,RuntimeError) as error:
                errors.append({'error_class':type(error).__name__,'work_stopped_proven':False})
        groups=[]
        for owner,work_id in candidates:
            try:
                validate();self.work._home()
                value=self.control.stop_for_deactivation(owner,work_id,authority=authority,validate=validate)
                groups.append({'subject':owner,'prepared':value})
            except (ValueError,OSError,RuntimeError,TimeoutError) as error:
                errors.append({'error_class':type(error).__name__,'work_stopped_proven':False})
        return {'groups':groups,'errors':errors,'authority':authority,
            'new_work_submitted':False,'effects_undone':False,'results_deleted':False}

    async def settle(self,prepared,*,validate):
        groups=[];errors=list(prepared['errors'])
        for group in prepared['groups']:
            try:
                value=await self.control.dispatch_deactivation(group['subject'],group['prepared'],
                    authority=prepared['authority'],validate=validate)
                groups.append({'subject':group['subject'],'prepared':value})
            except (ValueError,OSError,RuntimeError,TimeoutError) as error:
                errors.append({'error_class':type(error).__name__,'work_stopped_proven':False})
        return self.summary({**prepared,'groups':groups,'errors':errors})

    @staticmethod
    def summary(prepared):
        targets=[target for group in prepared['groups'] for target in group['prepared']['targets']]
        pending=sum(bool(v.get('stop_dispatch_required')) for v in targets)
        attention=bool(prepared['errors']) or any(v.get('needs_attention') for v in targets)
        return {'status':'needs_attention' if attention else 'stop_requests_observed',
            'owned_work_count':len(targets),'schedule_paused_count':sum(bool(v.get('schedule_paused')) for v in targets),
            'core_cancellation_acknowledged_count':sum(bool(v.get('cancel_acknowledged')) for v in targets),
            'core_terminal_observed_count':sum(bool(v.get('execution_stopped_proven')) for v in targets),
            'pending_core_stop_requests':pending,'needs_attention':attention,
            'error_count':len(prepared['errors']),'new_work_submitted':False,
            'effects_undone':False,'results_deleted':False}
