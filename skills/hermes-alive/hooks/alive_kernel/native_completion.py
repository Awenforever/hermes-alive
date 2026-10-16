"""Scoped native completion evidence, never a global last-model or action grant.

The host owns plugin registration and isolated agent/process lifetime. This hub
observes only explicitly opened random session/task pairs; foreground payloads are
not inspected or retained. No raw prompt, response text or credentials are stored.
"""
from dataclasses import dataclass, field
import hashlib
import math
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
    source_content_sha256: str
    source_content_chars: int
    text_projection: str = 'outer-whitespace-v1'
    request_attempt: int = 1
    api_started_at: float = 0.0
    source_contract: str = 'hermes.native.post_api_request.v3'
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
    terminal_shapes: list = field(default_factory=list,repr=False)


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

    @staticmethod
    def _attempt_start(values):
        value=values.get('started_at')
        if type(value) not in (int,float) or not math.isfinite(value):
            raise NativeCompletionError('native attempt start marker unavailable')
        # Exact Core event marker, not clock ordering, age, or a time window.
        return value

    def pre(self,**values):
        with self._lock:
            scope=self._current(values)
            if scope is None or scope.error: return None
            try:
                key=self._coordinates(values)
                started=self._attempt_start(values)
                expected=dict(requested_model=_label(values.get('model')),provider=_label(values.get('provider')))
                request=scope.requests.get(key)
                if request is not None and started in request['attempts']:
                    if request['attempts'][started]['pre']!=expected:
                        raise NativeCompletionError('conflicting request replay')
                else:
                    if sum(len(r['attempts']) for r in scope.requests.values())>=self.max_requests:
                        raise NativeCompletionError('native attempt bound exhausted')
                    if request is None:
                        request=dict(attempts={}); scope.requests[key]=request
                    elif any(a['state']!='failed' for a in request['attempts'].values()):
                        raise NativeCompletionError('new attempt overlaps a nonfailed request')
                    request['attempts'][started]=dict(pre=expected,state='started',completion=None,
                        ordinal=len(request['attempts'])+1)
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
                attempt=request['attempts'].get(self._attempt_start(values)) if request else None
                if attempt is None: raise NativeCompletionError('completion has no request attempt')
                message=values.get('assistant_message')
                text=getattr(message,'content',None)
                reason=values.get('finish_reason')
                count=values.get('assistant_tool_call_count')
                scope.terminal_shapes.append(dict(
                    finish_reason=reason if reason in ('stop','length','tool_calls','content_filter',None) else 'other',
                    has_text=isinstance(text,str) and bool(text),content_chars=len(text) if isinstance(text,str) else 0,
                    has_tool_calls=bool(getattr(message,'tool_calls',None)),
                    tool_count=count if type(count) is int and 0<=count<=10000 else None))
                del scope.terminal_shapes[:-16]
                # Core passes its NormalizedResponse, whose assistant role is
                # implicit in post_api_request (it has no role attribute).
                if (values.get('finish_reason')!='stop' or getattr(message,'role','assistant')!='assistant'
                        or getattr(message,'tool_calls',None)
                        or type(values.get('assistant_tool_call_count')) is not int
                        or values['assistant_tool_call_count']!=0
                        or not isinstance(text,str) or not text or len(text)>self.max_content_chars):
                    raise NativeCompletionError('completion is not bounded final text')
                projected=text.strip()  # Core turn_final_response's outer whitespace step only.
                if not projected:
                    raise NativeCompletionError('completion has no visible final text')
                evidence=NativeCompletionEvidence(scope.scope.subject,scope.scope.session_id,scope.scope.task_id,*key,
                    attempt['pre']['requested_model'],_label(values.get('response_model')),
                    _label(values.get('model')),_label(values.get('provider')),
                    hashlib.sha256(projected.encode('utf-8')).hexdigest(),len(projected),
                    hashlib.sha256(text.encode('utf-8')).hexdigest(),len(text),
                    request_attempt=attempt['ordinal'],api_started_at=self._attempt_start(values))
                if attempt['state']=='completed' and attempt['completion']==evidence: return None
                if attempt['state']!='started': raise NativeCompletionError('conflicting terminal completion')
                attempt.update(state='completed',completion=evidence,
                    stripped_sha256=hashlib.sha256(text.strip().encode('utf-8')).hexdigest())
            except NativeCompletionError as error: scope.error='post:'+str(error)
            except (TypeError,AttributeError): scope.error='invalid_post_shape'
        return None

    def error(self,**values):
        with self._lock:
            scope=self._current(values)
            if scope is None or scope.error: return None
            try:
                request=scope.requests.get(self._coordinates(values))
                attempt=request['attempts'].get(self._attempt_start(values)) if request else None
                if attempt is None or attempt['state']=='completed':
                    raise NativeCompletionError('error lacks current request')
                attempt['state']='failed'
            except NativeCompletionError as error: scope.error='error:'+str(error)
            except (TypeError,AttributeError): scope.error='invalid_error_shape'
        return None

    def diagnostics(self,scope,result):
        """Bounded shape and equality checks; never return provider text/labels."""
        with self._lock:
            state=self._scopes.get((scope.session_id,scope.task_id))
            if state is None or state.scope is not scope: return None
            result=result if isinstance(result,dict) else {}
            attempts=[a for r in state.requests.values() for a in r['attempts'].values()]
            completed=[a for a in attempts if a['state']=='completed']
            evidence=completed[0]['completion'] if len(completed)==1 else None
            text=result.get('final_response')
            digest=hashlib.sha256(text.encode('utf-8')).hexdigest() if isinstance(text,str) else None
            return dict(
                final_text_chars=len(text) if isinstance(text,str) else None,
                exact_text_match=evidence is not None and digest==evidence.source_content_sha256,
                stripped_text_match=evidence is not None and digest==completed[0].get('stripped_sha256'),
                coordinate_matches={k:evidence is not None and result.get(k)==getattr(evidence,field)
                    for k,field in (('session_id','session_id'),('turn_id','turn_id'),
                                    ('model','route_model'),('provider','provider'))},
                observations=[dict(error=state.error,terminal_shapes=list(state.terminal_shapes),
                    requests=len(state.requests),states=[a['state'] for a in attempts])])

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
            attempts=[a for r in state.requests.values() for a in r['attempts'].values()]
            completions=[a['completion'] for a in attempts if a['state']=='completed']
            if len(completions)!=1 or any(a['state']=='started' for a in attempts):
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
