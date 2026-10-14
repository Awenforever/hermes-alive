"""Opt-in bounded host lifetime with durable cycle identity, no installed daemon.

Journal state owns identity/progress, not permission. Model/transport recovery is
delegated to the composed runtime; failed active work never becomes a new cycle.
"""
import asyncio
from dataclasses import dataclass
import re

from .events import EventEnvelope,Sensitivity,_thaw_json


@dataclass(frozen=True,slots=True)
class HostCycle:
    event_id: str
    operation_id: str
    reconciliation_cursor: int


class AutonomousHostRuntime:
    def __init__(self,runtime,*,subject,configuration_id,execute=False):
        if (type(execute) is not bool or any(not isinstance(x,str) or not re.fullmatch(
                r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}',x) for x in (subject,configuration_id))):
            raise ValueError('explicit host owner/configuration required')
        self.runtime,self.journal,self.protector = runtime,runtime.outbox.journal,runtime.outbox.protector
        self.subject,self.configuration_id,self.execute = subject,configuration_id,execute
        self.lane = 'alive-host:' + self.protector.authenticate_json('autonomous.host.lane.v1',subject)
        self.lock = asyncio.Lock()
        self.running = False

    def _validate(self,event):
        payload = _thaw_json(event.payload)
        signature = payload.pop('integrity_authenticator',None)
        if (event.source!='alive.autonomous-host' or event.actor!='system:alive-host'
                or event.event_type not in ('autonomous.host.opened','autonomous.host.closed')
                or event.subject!=self.subject or event.correlation_id!=self.lane
                or event.sensitivity is not Sensitivity.PRIVATE
                or payload.get('subject')!=self.subject or payload.get('lane')!=self.lane
                or not self.protector.verify_json(event.event_type+'.v1',payload,signature)):
            raise ValueError('host history lacks canonical owner provenance')
        if event.event_type=='autonomous.host.opened':
            identity_payload = dict(payload)
            operation = identity_payload.pop('operation_id',None)
            identity = self.protector.authenticate_json('autonomous.host.identity.v1',identity_payload)
            if (event.event_id!='host-cycle:'+identity or operation!='host-cycle:'+identity[:40]
                    or event.causation_id!=payload.get('previous_closed_event_id')):
                raise ValueError('host cycle identity differs from canonical state')
        elif event.event_id!=(event.causation_id or '')+':closed':
            raise ValueError('host completion identity differs from its open cycle')
        return payload

    def open_cycle(self):
        def factory(connection):
            row = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE subject=? AND correlation_id=? AND event_type IN (?,?) ORDER BY sequence DESC LIMIT 1',
                (self.subject,self.lane,'autonomous.host.opened','autonomous.host.closed')).fetchone()
            previous,cursor = None,0
            if row is not None:
                event = self.journal._record(row).event
                payload = self._validate(event)
                if event.event_type=='autonomous.host.opened':
                    if payload['configuration_id']!=self.configuration_id or payload['execute'] is not self.execute:
                        raise ValueError('active cycle configuration changed; explicit recovery required')
                    return event
                previous = event.event_id
                cursor = payload['next_reconciliation_cursor']
                opened = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_id=?',(event.causation_id,)).fetchone()
                if opened is None or self._validate(self.journal._record(opened).event)['operation_id']!=payload['operation_id']:
                    raise ValueError('completion references a missing/different open cycle')
            if type(cursor) is not int or cursor<0:
                raise ValueError('invalid host scan cursor')
            payload = {'subject':self.subject,'lane':self.lane,'configuration_id':self.configuration_id,'execute':self.execute,
                'previous_closed_event_id':previous,'reconciliation_cursor':cursor,'authority_granted':False}
            identity = self.protector.authenticate_json('autonomous.host.identity.v1',payload)
            payload['operation_id'] = 'host-cycle:'+identity[:40]
            payload['integrity_authenticator'] = self.protector.authenticate_json('autonomous.host.opened.v1',payload)
            return EventEnvelope(event_id='host-cycle:'+identity,event_type='autonomous.host.opened',
                source='alive.autonomous-host',actor='system:alive-host',subject=self.subject,
                sensitivity=Sensitivity.PRIVATE,correlation_id=self.lane,causation_id=previous,payload=payload)
        record = self.journal.append(factory)
        payload = record.event.payload
        return HostCycle(record.event.event_id,payload['operation_id'],payload['reconciliation_cursor'])

    def close_cycle(self,cycle,result):
        cursor = result.reconciliation['next_after_sequence']
        if (type(cursor) is not int or cursor<0 or result.external_delivery_proven is not False
                or result.disposition not in ('paused','reconciliation_attention','silence','shadow_selected',
                    'not_authorized','attempt_unavailable','submitted')):
            raise ValueError('cycle completion exceeds qualified contract')
        payload = {'subject':self.subject,'lane':self.lane,'operation_id':cycle.operation_id,'disposition':result.disposition,
            'next_reconciliation_cursor':cursor,'external_delivery_proven':False,'authority_granted':False}
        payload['integrity_authenticator'] = self.protector.authenticate_json('autonomous.host.closed.v1',payload)
        def factory(connection):
            row = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_id=?',(cycle.event_id,)).fetchone()
            if row is None or self._validate(self.journal._record(row).event)['operation_id']!=cycle.operation_id:
                raise ValueError('canonical open cycle required')
            existing = connection.execute('SELECT sequence,canonical_json,integrity_hash FROM experience_events WHERE event_id=?',(cycle.event_id+':closed',)).fetchone()
            if existing:
                event = self.journal._record(existing).event
                if self._validate(event)!= {k:v for k,v in payload.items() if k!='integrity_authenticator'}:
                    raise ValueError('host completion changed')
                return event
            return EventEnvelope(event_id=cycle.event_id+':closed',event_type='autonomous.host.closed',
                source='alive.autonomous-host',actor='system:alive-host',subject=self.subject,
                sensitivity=Sensitivity.PRIVATE,correlation_id=self.lane,causation_id=cycle.event_id,payload=payload)
        return self.journal.append(factory)

    async def step(self,parameters):
        if any(key in parameters for key in ('subject','operation_id','execute','reconciliation_cursor')):
            raise ValueError('host owns cycle identity/mode/cursor')
        async with self.lock:
            cycle = self.open_cycle()
            result = await self.runtime.cycle(**parameters,subject=self.subject,operation_id=cycle.operation_id,
                execute=self.execute,reconciliation_cursor=cycle.reconciliation_cursor)
            self.close_cycle(cycle,result)
            return result

    async def run(self,*,build_parameters,stop,max_cycles,interval_seconds=60):
        if (self.running or type(max_cycles) is not int or not 1<=max_cycles<=1000
                or type(interval_seconds) not in (int,float) or not 0<=interval_seconds<=86400
                or not callable(build_parameters) or not isinstance(stop,asyncio.Event)):
            raise ValueError('explicit bounded cooperative host lifetime required')
        self.running = True
        completed = 0
        try:
            while completed<max_cycles and not stop.is_set():
                async def invoke():
                    parameters = build_parameters()
                    if hasattr(parameters,'__await__'): parameters = await parameters
                    return await self.step(parameters)
                active = asyncio.create_task(invoke())
                stopped = asyncio.create_task(stop.wait())
                try:
                    await asyncio.wait((active,stopped),return_when=asyncio.FIRST_COMPLETED)
                    if not active.done():
                        return {'completed_cycles':completed,'exit_reason':'stopped','external_delivery_proven':False}
                    try: active.result()
                    except Exception:
                        return {'completed_cycles':completed,'exit_reason':'cycle_failed','external_delivery_proven':False}
                    completed += 1
                finally:
                    for task in (active,stopped):
                        if not task.done(): task.cancel()
                    await asyncio.gather(active,stopped,return_exceptions=True)
                if completed<max_cycles and not stop.is_set():
                    try: await asyncio.wait_for(stop.wait(),timeout=interval_seconds)
                    except TimeoutError: pass
            return {'completed_cycles':completed,'exit_reason':'stopped' if stop.is_set() else 'budget',
                    'external_delivery_proven':False}
        finally:
            self.running = False
