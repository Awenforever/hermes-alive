"""Scoped native completion evidence, never a global last-model or action grant.

The host owns plugin registration and isolated agent/process lifetime. This hub
observes only explicitly opened random session/task pairs; foreground payloads are
not inspected or retained. No raw prompt, response text or credentials are stored.
"""
from dataclasses import dataclass, field
import hashlib
import re
import threading
from uuid import uuid4


class NativeCompletionError(ValueError):
    """A native final result lacks exact, current completion evidence."""


def _token(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/+\-]{0,255}',value):
        raise NativeCompletionError('invalid native completion identity')
    return value


def _label(value):
    # Provider-reported names are opaque labels, not our routing identifiers.
    # Preserve printable Unicode/spaces rather than invent a model-name grammar.
    if not isinstance(value,str) or not value.strip() or len(value)>256 or not value.isprintable():
        raise NativeCompletionError('invalid native completion label')
    return value


@dataclass(frozen=True,slots=True)
class NativeCompletionEvidence:
    subject: str
    session_id: str
    task_id: str
    turn_id: str
    api_request_id: str
    requested_model: str
    response_model: str
    route_model: str
    provider: str
    content_sha256: str
    content_chars: int
    source_contract: str = 'hermes.native.post_api_request.v1'
    authority_granted: bool = False


@dataclass(frozen=True,slots=True,eq=False)
class NativeCompletionScope:
    subject: str
    session_id: str
    task_id: str


@dataclass(slots=True)
class _Observation:
    scope: NativeCompletionScope
    requests: dict = field(default_factory=dict,repr=False)
    error: str | None = None


class NativeCompletionHub:
    """One explicitly registered host observer; no default process-global hub."""

    def __init__(self,*,max_scopes=16,max_requests=4,max_content_chars=32000):
        if (type(max_scopes) is not int or not 1<=max_scopes<=64
                or type(max_requests) is not int or not 1<=max_requests<=16
                or type(max_content_chars) is not int or not 1<=max_content_chars<=64000):
            raise NativeCompletionError('invalid native observer bounds')
        self.max_scopes,self.max_requests,self.max_content_chars=max_scopes,max_requests,max_content_chars
        self._lock=threading.RLock()
        self._scopes={}
        self._handles=[]
        self._retired=False

    def install(self,context):
        with self._lock:
            if self._handles or self._retired:
                raise NativeCompletionError('native observer already installed or retired')
            try:
                for name,callback in (('pre_api_request',self.pre),('post_api_request',self.post),
                                      ('api_request_error',self.error)):
                    handle=context.register_hook(name,callback)
                    if not callable(getattr(handle,'dispose',None)) or getattr(handle,'active',None) is not True:
                        raise NativeCompletionError('native observer needs host-owned registration handles')
                    self._handles.append(handle)
            except Exception:
                self.close()
                raise

    def _ready(self):
        if self._retired or len(self._handles)!=3 or not all(h.active for h in self._handles):
            raise NativeCompletionError('native observer registration unavailable')

    def open(self,*,subject):
        subject=_token(subject)
        with self._lock:
            self._ready()
            if len(self._scopes)>=self.max_scopes:
                raise NativeCompletionError('native observer scope bound exhausted')
            identity=uuid4().hex
            scope=NativeCompletionScope(subject,'alive-native:'+identity,'alive-task:'+identity)
            self._scopes[(scope.session_id,scope.task_id)]=_Observation(scope)
            return scope

    def _current(self,values):
        # Scope match precedes any prompt, model or response access. Identifiers
        # correlate trusted host events; they do not authenticate hostile plugins.
        session,task=values.get('session_id'),values.get('task_id')
        if not isinstance(session,str) or not isinstance(task,str): return None
        return self._scopes.get((session,task))

    @staticmethod
    def _coordinates(values):
        return _token(values.get('turn_id')),_token(values.get('api_request_id'))

    def pre(self,**values):
        with self._lock:
            scope=self._current(values)
            if scope is None or scope.error: return None
            try:
                key=self._coordinates(values)
                expected=dict(requested_model=_label(values.get('model')),provider=_label(values.get('provider')))
                if key in scope.requests:
                    if scope.requests[key]['pre']!=expected or scope.requests[key]['state']!='started':
                        raise NativeCompletionError('conflicting request replay')
                else:
                    if len(scope.requests)>=self.max_requests:
                        raise NativeCompletionError('native request bound exhausted')
                    scope.requests[key]=dict(pre=expected,state='started',completion=None)
            except NativeCompletionError as error: scope.error='pre:'+str(error)
            except (TypeError,AttributeError): scope.error='invalid_pre_shape'
        return None

    def post(self,**values):
        with self._lock:
            scope=self._current(values)
            if scope is None or scope.error: return None
            try:
                key=self._coordinates(values)
                request=scope.requests.get(key)
                if request is None: raise NativeCompletionError('completion has no request')
                message=values.get('assistant_message')
                text=getattr(message,'content',None)
                # Core passes its NormalizedResponse, whose assistant role is
                # implicit in post_api_request (it has no role attribute).
                if (values.get('finish_reason')!='stop' or getattr(message,'role','assistant')!='assistant'
                        or getattr(message,'tool_calls',None)
                        or type(values.get('assistant_tool_call_count')) is not int
                        or values['assistant_tool_call_count']!=0
                        or not isinstance(text,str) or not text or len(text)>self.max_content_chars):
                    raise NativeCompletionError('completion is not bounded final text')
                evidence=NativeCompletionEvidence(scope.scope.subject,scope.scope.session_id,scope.scope.task_id,*key,
                    request['pre']['requested_model'],_label(values.get('response_model')),
                    _label(values.get('model')),_label(values.get('provider')),
                    hashlib.sha256(text.encode('utf-8')).hexdigest(),len(text))
                if request['state']=='completed' and request['completion']==evidence: return None
                if request['state']!='started': raise NativeCompletionError('conflicting terminal completion')
                request.update(state='completed',completion=evidence)
            except NativeCompletionError as error: scope.error='post:'+str(error)
            except (TypeError,AttributeError): scope.error='invalid_post_shape'
        return None

    def error(self,**values):
        with self._lock:
            scope=self._current(values)
            if scope is None or scope.error: return None
            try:
                request=scope.requests.get(self._coordinates(values))
                if request is None or request['state']=='completed':
                    raise NativeCompletionError('error lacks current request')
                request['state']='failed'
            except NativeCompletionError as error: scope.error='error:'+str(error)
            except (TypeError,AttributeError): scope.error='invalid_error_shape'
        return None

    def finish(self,scope,result):
        with self._lock:
            key=(scope.session_id,scope.task_id)
            state=self._scopes.get(key)
            if state is None or state.scope is not scope:
                raise NativeCompletionError('native completion scope is not active')
            # Every finalization, including denial, consumes the scope; a caller
            # cannot turn a failed proof into a successful second interpretation.
            del self._scopes[key]
            self._ready()
            if state.error or not isinstance(result,dict):
                raise NativeCompletionError('native completion evidence invalid')
            if (result.get('completed') is not True or any(result.get(k) is not False for k in (
                    'failed','partial','interrupted','response_transformed','response_reused'))
                    or result.get('session_id')!=scope.session_id
                    or type(result.get('api_calls')) is not int or result['api_calls']!=len(state.requests)):
                raise NativeCompletionError('native turn is not an exact completed result')
            completions=[r['completion'] for r in state.requests.values() if r['state']=='completed']
            if len(completions)!=1 or any(r['state']=='started' for r in state.requests.values()):
                raise NativeCompletionError('native final completion is missing or ambiguous')
            evidence=completions[0]
            text=result.get('final_response')
            if (not isinstance(text,str) or len(text)!=evidence.content_chars
                    or hashlib.sha256(text.encode('utf-8')).hexdigest()!=evidence.content_sha256
                    or result.get('turn_id')!=evidence.turn_id or result.get('model')!=evidence.route_model
                    or result.get('provider')!=evidence.provider):
                raise NativeCompletionError('native final text or route differs from observed completion')
            return evidence

    def cancel(self,scope):
        """Discard evidence; this does NOT stop an agent, thread or HTTP request."""
        with self._lock:
            key=(scope.session_id,scope.task_id)
            state=self._scopes.get(key)
            if state is not None and state.scope is scope:
                del self._scopes[key]
                state.requests.clear()
                state.error='cancelled'

    def close(self):
        with self._lock:
            self._retired=True
            for state in tuple(self._scopes.values()): self.cancel(state.scope)
            handles,self._handles=self._handles,[]
        # Host disposal may acquire other registry locks; never call it while
        # holding the observer lock needed by an in-flight callback.
        failures=[]
        for handle in reversed(handles):
            try: handle.dispose()
            except Exception as error: failures.append(type(error).__name__)
        if failures: raise NativeCompletionError('native observer disposal incomplete')
