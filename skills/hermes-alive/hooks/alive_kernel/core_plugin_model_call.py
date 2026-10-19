"""Core-owned model/auth/fallback with strict raw SDK completion admission.

Uses the current PluginContext's facade and its existing gate/host/audit steps;
no provider registry, token export or auth-file clone. Private Core method ABI is
explicitly qualified by integration tests; unavailable ABI fails closed.
"""
import asyncio
import math
from pathlib import Path
from types import SimpleNamespace

from .native_worker_protocol import NativeWorkerError,canonical
from .native_host_snapshot import CONFIG_FIELDS,AGENT_FIELDS,_validate_model_overrides


class CorePluginModelCaller:
    def __init__(self,context,*,read_binding,max_calls=16,task_key='hermes_alive_kernel',refresh_task=None):
        if not callable(read_binding) or type(max_calls) is not int or not 1<=max_calls<=32:
            raise NativeWorkerError('explicit bounded Core model capability required')
        self.context=context;self.read_binding=read_binding
        self.task_key=task_key
        self.refresh_task=refresh_task
        self.calls=0;self.max_calls=max_calls;self._active=None

    @property
    def pending(self):
        return ({'phase':'in_flight','local_task_closed':False},) if self._active is not None and not self._active.done() else ()

    async def reap_pending(self,*,timeout_seconds=0):
        task=self._active
        if task is not None and not task.done() and timeout_seconds:
            await asyncio.wait((task,),timeout=timeout_seconds)
        return dict(closed=int(task is not None and task.done()),remaining=len(self.pending))

    def _configuration(self):
        from hermes_cli.config import load_config_readonly
        from agent.auxiliary_task_config import _get_auxiliary_task_config
        config=load_config_readonly()
        snapshot={key:config[key] for key in CONFIG_FIELDS if key in config and key!='agent'}
        snapshot['agent']={key:value for key,value in config.get('agent',{}).items() if key in AGENT_FIELDS}
        snapshot['task']=_get_auxiliary_task_config(self.task_key)
        shadow=self.context.get_config('kernel_shadow',{})
        if isinstance(shadow,dict) and shadow.get('enabled') is True:
            from .core_shadow_assembly import normalize_settings
            shadow=normalize_settings(shadow)
        snapshot['shadow_consent']=shadow
        _validate_model_overrides(snapshot)
        return canonical(snapshot)

    async def __call__(self,*,task,model,messages,temperature,max_tokens,route_info=None,timeout=None):
        if self.pending or self.calls>=self.max_calls:
            raise NativeWorkerError('Core model call pending or budget exhausted')
        if (type(max_tokens) is not int or not 1<=max_tokens<=8192
                or type(temperature) not in (int,float) or not math.isfinite(temperature)
                or not 0<=temperature<=2 or len(canonical(messages))>131072):
            raise NativeWorkerError('Core call exceeds the admitted text/budget boundary')
        from hermes_constants import get_hermes_home
        if Path(get_hermes_home()).resolve()!=Path(self.context._manager.scope_key).resolve():
            raise NativeWorkerError('Core model context belongs to another profile')
        binding=self.read_binding()
        if self.refresh_task is not None:self.refresh_task()
        configuration=self._configuration()
        from agent.secret_scope import current_secret_scope
        scope=current_secret_scope()
        if scope is None:raise NativeWorkerError('Core model call requires an explicit profile scope')
        def current():
            if (self.read_binding()!=binding or current_secret_scope() is not scope
                    or self._configuration()!=configuration):
                raise NativeWorkerError('Core model authority changed during call')
        facade=self.context.llm
        if any(not callable(getattr(facade,name,None)) for name in ('_gate','_invoke_async','_finish')):
            raise NativeWorkerError('Core raw completion contract unavailable')
        limits=90 if timeout is None else timeout
        if type(limits) not in (int,float) or not 0<limits<=240:
            raise NativeWorkerError('Core model call requires a bounded timeout')
        # Mirror Core's public acomplete pipeline, preserving raw metadata before
        # _finish drops it. Core still performs every override/task trust check.
        agent,kw=facade._gate(None,model,None,None,self.task_key,messages,temperature,max_tokens,limits)
        current();self.calls+=1
        self._active=asyncio.create_task(facade._invoke_async(kw))
        try:
            invoked=await asyncio.wait_for(self._active,timeout=limits)
            response=invoked[2]
            current()
            # Recheck current Core override permissions, without another request.
            facade._gate(None,model,None,None,self.task_key,messages,temperature,max_tokens,limits)
            choices=getattr(response,'choices',None)
            if not isinstance(choices,list) or len(choices)!=1:
                raise NativeWorkerError('Core response is not one native text choice')
            choice=choices[0];message=getattr(choice,'message',None)
            # Core compatibility shims sometimes synthesize stop. A plain
            # namespace/defaulted finish is not evidence from an SDK document.
            if ('model' not in getattr(response,'model_fields_set',set())
                    or not {'message','finish_reason'}<=getattr(choice,'model_fields_set',set())
                    or choice.finish_reason!='stop' or getattr(message,'tool_calls',None)
                    or getattr(choice,'index',None)!=0 or getattr(message,'role',None)!='assistant'
                    or 'content' not in getattr(message,'model_fields_set',set())
                    or not isinstance(getattr(message,'content',None),str)
                    or not message.content.strip() or not isinstance(getattr(response,'model',None),str)
                    or not response.model.strip()):
                raise NativeWorkerError('Core response lacks qualified native completion metadata')
            audited=facade._finish('acomplete',agent,kw,invoked,str(task))
            if audited.text!=message.content:
                raise NativeWorkerError('Core facade text differs from native SDK choice')
            if route_info is not None:route_info.update(provider=audited.provider,model=response.model)
            return SimpleNamespace(model=response.model,choices=choices)
        finally:
            if self._active is not None and self._active.done():
                if not self._active.cancelled():self._active.exception()
