"""Opt-in native cognition bound to real durable cycles and current owner policy.

Not a Gateway daemon or channel sender. The embedding Hermes host owns the
profile scope, loaded model configuration, credential grants and scheduling.
"""
import asyncio
import hashlib

from .native_core_acquisition import CoreScopedModelAcquirer
from .native_host_caller import HostModelBinding,HostNativeCaller
from .native_worker_protocol import NativeWorkerError,canonical,identifier


class NativeCognitionHost:
    def __init__(self,host,*,profile_id,profile_home,read_configuration,
                 read_credential_names,interpreter,core,private_root,environment,
                 resolve_domain,identity='',entrypoint=None,timeout_seconds=90,max_calls=16,
                 profile_scope=None,caller_factory=None):
        if not callable(resolve_domain):
            raise NativeWorkerError('host model family resolver required')
        self.host=host
        self.profile_id=identifier(profile_id)
        self.acquisition=dict(profile_home=profile_home,read_configuration=read_configuration,
            read_credential_names=read_credential_names,identity=identity)
        self.worker=dict(interpreter=interpreter,core=core,private_root=private_root,
            environment=environment,entrypoint=entrypoint,timeout_seconds=timeout_seconds,max_calls=max_calls)
        self.resolve_domain=resolve_domain
        if profile_scope is not None and not callable(profile_scope):
            raise NativeWorkerError('explicit host profile scope factory required')
        self.profile_scope=profile_scope
        if caller_factory is not None and not callable(caller_factory):
            raise NativeWorkerError('explicit current host caller factory required')
        self.caller_factory=caller_factory
        self._caller=None
        self._lock=asyncio.Lock()
        self.last_call_count=0
        self._background_task=None

    async def run(self,*,build_parameters,stop,max_cycles,interval_seconds=60):
        """Reuse the durable host's bounded loop, binding native authority each turn."""
        if self.host.running:
            raise NativeWorkerError('native host loop already active')
        try:
            return await self.host.run(build_parameters=build_parameters,stop=stop,
                max_cycles=max_cycles,interval_seconds=interval_seconds,cycle_step=self.step)
        finally:
            # The retained worker owns any uncertain child; do not clear its
            # lease or workspace merely because the plugin task was cancelled.
            await self.reap_pending(timeout_seconds=5)

    def start(self,context,*,build_parameters,stop,max_cycles,interval_seconds=60):
        """Explicit host entrypoint; Core supervises task cancellation on unload.

        Requires a running loop and an already-bound Core profile context. This
        does not register startup hooks, discover profiles or enable a daemon.
        """
        if (self._background_task is not None and not self._background_task.done()
                or self.host.running or not callable(getattr(context,'spawn_task',None))):
            raise NativeWorkerError('native host task already active or no supervisor')
        coroutine=self.run(build_parameters=build_parameters,stop=stop,max_cycles=max_cycles,
            interval_seconds=interval_seconds)
        try:
            task=context.spawn_task(coroutine,name='alive-native-cognition')
        except BaseException:
            coroutine.close()
            raise
        self._background_task=task
        return task

    @property
    def pending(self):
        return self._caller.pending if self._caller is not None else ()

    async def reap_pending(self,*,timeout_seconds=0):
        if self._caller is None: return dict(closed=0,remaining=0)
        return await self._caller.reap_pending(timeout_seconds=timeout_seconds)

    async def step(self,parameters):
        if self.profile_scope is None:
            return await self._step(parameters)
        async with self.profile_scope():
            return await self._step(parameters)

    async def _step(self,parameters):
        if self._lock.locked():
            raise NativeWorkerError('native host cycle already active')
        if not isinstance(parameters,dict):
            raise NativeWorkerError('explicit cycle parameters required')
        expression=parameters.get('expression_parameters',{})
        if not isinstance(expression,dict) or any(key in expression for key in ('call','resolve_domain')):
            raise NativeWorkerError('native host owns model invocation capability')
        async with self._lock:
            await self.reap_pending()
            if self.pending:
                raise NativeWorkerError('native host retains uncertain child work')
            self._caller=None
            active=[True]
            self.last_call_count=0
            def build(cycle):
                def read_binding():
                    if not active[0]:
                        raise NativeWorkerError('native cycle capability is closed')
                    policy=self.host.runtime.reconciliation._owner_policy(self.host.subject)
                    if not policy.enabled:
                        raise NativeWorkerError('owner autonomy policy is disabled')
                    revision=hashlib.sha256(canonical(dict(policy=policy.event_id,
                        revision=policy.revision,configuration=self.host.configuration_id))).hexdigest()
                    return HostModelBinding(self.host.subject,self.profile_id,cycle.operation_id,revision)
                if self.caller_factory is None:
                    acquire=CoreScopedModelAcquirer(read_binding=read_binding,**self.acquisition)
                    self._caller=HostNativeCaller(subject=self.host.subject,profile_id=self.profile_id,
                        operation_id=cycle.operation_id,acquire=acquire,**self.worker)
                else:
                    self._caller=self.caller_factory(cycle=cycle,read_binding=read_binding)
                return {**parameters,'expression_parameters':{**expression,'call':self._caller,
                    'resolve_domain':self.resolve_domain}}
            try:
                return await self.host.step_bound(build)
            finally:
                active[0]=False
                if self._caller is not None: self.last_call_count=self._caller.calls
