"""Owner-bound bridge to native workers; host owns model capability selection.

No profile discovery or competing model registry. The host adapter supplies an
exact model-only projection and credential read capabilities for each request.
"""
from dataclasses import dataclass, field
import json

from .native_host_snapshot import validate_host_snapshot
from .native_worker_caller import NativeWorkerCaller
from .native_worker_protocol import NativeWorkerError, canonical, identifier


@dataclass(frozen=True, slots=True)
class HostModelBinding:
    subject: str
    profile_id: str
    operation_id: str
    revision: str

    def __post_init__(self):
        for value in (self.subject,self.profile_id,self.operation_id,self.revision): identifier(value)


@dataclass(frozen=True, slots=True)
class HostModelCapability:
    binding: HostModelBinding
    configuration: dict = field(repr=False)
    credential_names: tuple[str,...] = field(repr=False)
    read_secret: object = field(repr=False)
    is_current: object = field(repr=False)
    identity: str = field(default='',repr=False)
    unauthenticated_endpoints: tuple[str,...] = ()


ENVIRONMENT_FIELDS=frozenset({'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT',
    'LANG','LC_ALL','LC_CTYPE','TZ','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE',
    'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY'})


def minimal_model_environment(source):
    """Explicit OS/network transport projection; credentials never ride the env."""
    if not isinstance(source,dict): raise NativeWorkerError('explicit model process environment required')
    result={}
    folded={}
    for key,value in source.items():
        if not isinstance(key,str) or key.upper() not in ENVIRONMENT_FIELDS: continue
        if not isinstance(value,str) or '\0' in value:
            raise NativeWorkerError('invalid model transport environment')
        if key.upper() in folded and folded[key.upper()]!=value:
            raise NativeWorkerError('ambiguous model transport environment')
        folded[key.upper()]=value
        result[key]=value
    return result


class HostNativeCaller:
    """One operation-bound model caller; no new work while an owned child is pending.

    acquire(task=..., model=...) must be the host's trusted, current-owner model
    adapter, not model-generated instructions. Its revision covers effective
    config, credentials, consent/identity and owner lifecycle, including ABA.
    """
    def __init__(self,*,subject,profile_id,operation_id,acquire,interpreter,core,
            private_root,environment,timeout_seconds=90,max_calls=16,entrypoint=None):
        self.subject,self.profile_id,self.operation_id=map(identifier,(subject,profile_id,operation_id))
        if not callable(acquire) or type(max_calls) is not int or not 1<=max_calls<=32:
            raise NativeWorkerError('bounded host acquisition capability required')
        self.acquire=acquire
        self.arguments=dict(interpreter=interpreter,core=core,private_root=private_root,
            environment=minimal_model_environment(environment),timeout_seconds=timeout_seconds,entrypoint=entrypoint)
        self.calls,self.max_calls=0,max_calls
        self._active=None
        self._busy=False

    @property
    def pending(self):
        return self._active.pending if self._active is not None else ()

    async def reap_pending(self,*,timeout_seconds=0):
        if self._active is None: return dict(closed=0,remaining=0)
        return await self._active.reap_pending(timeout_seconds=timeout_seconds)

    async def __call__(self,*,task,model,messages,temperature,max_tokens,route_info=None):
        if self._busy: raise NativeWorkerError('host model invocation is already active')
        self._busy=True
        try:
            await self.reap_pending()
            if self.pending or self.calls>=self.max_calls:
                raise NativeWorkerError('host model worker pending or budget exhausted')
            self.calls+=1
            try: capability=self.acquire(task=task,model=model)
            except Exception: raise NativeWorkerError('host model capability acquisition failed') from None
            if (not isinstance(capability,HostModelCapability)
                    or not isinstance(capability.binding,HostModelBinding)
                    or (capability.binding.subject,capability.binding.profile_id,capability.binding.operation_id)
                        !=(self.subject,self.profile_id,self.operation_id)
                    or not callable(capability.is_current) or not callable(capability.read_secret)):
                raise NativeWorkerError('host model capability belongs to another binding')
            def current():
                try: return capability.is_current(capability.binding) is True
                except Exception: return False
            def require_current():
                if not current(): raise NativeWorkerError('host model capability changed or revoked')
            require_current()
            names=capability.credential_names
            if (not isinstance(names,tuple) or len(names)>128
                    or any(not isinstance(name,str) for name in names)
                    or len(set(names))!=len(names)):
                raise NativeWorkerError('host credential manifest invalid')
            # Validate names/types/projection before invoking any secret getter.
            try:
                if not isinstance(capability.unauthenticated_endpoints,tuple):
                    raise ValueError('endpoint grants require explicit tuple')
                snapshot=dict(config=json.loads(canonical(capability.configuration)),
                    secrets={name:'' for name in names},selected_model=model,
                    unauthenticated_endpoints=list(capability.unauthenticated_endpoints))
                validate_host_snapshot(snapshot)
            except Exception:
                raise NativeWorkerError('host model projection invalid') from None
            secrets={}
            for name in names:
                require_current()
                try: value=capability.read_secret(capability.binding,name)
                except Exception: raise NativeWorkerError('bound model credential read failed') from None
                require_current()
                if value is not None: secrets[name]=value
            snapshot['secrets']=secrets
            snapshot=json.loads(canonical(validate_host_snapshot(snapshot)))
            require_current()
            worker=NativeWorkerCaller(subject=self.subject,operation_id=self.operation_id,
                resolve_runtime=lambda **_kw:dict(host_snapshot=snapshot),assert_current=current,
                identity=capability.identity,max_calls=1,**self.arguments)
            self._active=worker  # Retain its binding/workspace if cancellation leaves an uncertain lease.
            return await worker(task=task,model=model,messages=messages,temperature=temperature,
                max_tokens=max_tokens,route_info=route_info)
        finally:
            self._busy=False
            if self._active is not None and not self._active.pending: self._active=None
