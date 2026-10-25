"""Scoped completion evidence; synthetic events do not prove a provider model."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace


class Handle:
    def __init__(self,context,name): self.active=True; self.context=context; self.name=name
    def dispose(self):
        if self.active:
            self.active=False
            self.context.callbacks.pop(self.name,None)


class Context:
    def __init__(self): self.callbacks={}; self.handles=[]
    def register_hook(self,name,callback):
        self.callbacks[name]=callback
        handle=Handle(self,name); self.handles.append(handle); return handle
    def register_middleware(self,name,callback):
        return self.register_hook(name,callback)


def exercise():
    from alive_kernel.native_completion import NativeCompletionHub,NativeCompletionError
    def configured(**kwargs):
        hub=NativeCompletionHub(**kwargs); context=Context(); hub.install(context); return hub,context
    def values(scope,*,request='request:1',turn='turn:1',model='route-primary',provider='custom:synthetic',started=1.0):
        return dict(session_id=scope.session_id,task_id=scope.task_id,turn_id=turn,api_request_id=request,
            model=model,provider=provider,started_at=started)
    def post(hub,scope,*,text='PRIVATE_CANDIDATE',response_model='actual-response-label',**kwargs):
        event=dict(**values(scope,**kwargs),response_model=response_model,finish_reason='stop',
            assistant_tool_call_count=0,assistant_message=SimpleNamespace(role='assistant',content=text,tool_calls=None))
        hub.post(**event)
        return event
    def result(scope,*,text='PRIVATE_CANDIDATE',turn='turn:1',model='route-primary',api_calls=1,**kwargs):
        return dict(session_id=scope.session_id,turn_id=turn,model=model,provider='custom:synthetic',
            final_response=text,api_calls=api_calls,completed=True,failed=False,partial=False,interrupted=False,
            response_transformed=False,response_reused=False,**kwargs)
    def denied(hub,scope,value):
        try: hub.finish(scope,value)
        except NativeCompletionError: return
        raise AssertionError('unqualified native completion accepted')

    hub,context=configured()
    assert set(context.callbacks)=={'pre_api_request','post_api_request','api_request_error'}
    own=hub.open(subject='user:one'); other=hub.open(subject='user:other')
    class Bomb:
        @property
        def content(self): raise AssertionError('foreground body inspected')
    hub.post(session_id='foreground',task_id='foreground',assistant_message=Bomb())
    def events(scope,label):
        hub.pre(**values(scope))
        event=post(hub,scope,response_model=label)
        hub.post(**event)  # Exactly identical terminal re-delivery is harmless.
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda pair:events(*pair),((own,'family-a/model'),(other,'family-b/model'))))
    assert 'PRIVATE_CANDIDATE' not in repr(hub._scopes)
    # A structurally identical scope clone is not the caller's active capability.
    denied(hub,replace(own),result(own))
    first=hub.finish(own,result(own)); second=hub.finish(other,result(other))
    assert first.response_model=='family-a/model' and second.response_model=='family-b/model'
    assert first.content_sha256==hashlib.sha256(b'PRIVATE_CANDIDATE').hexdigest()
    assert not first.authority_granted and first.subject=='user:one'
    denied(hub,own,result(own))
    normalized=hub.open(subject='user:one'); hub.pre(**values(normalized))
    hub.post(**values(normalized),response_model='normalized-label',finish_reason='stop',assistant_tool_call_count=0,
        assistant_message=SimpleNamespace(content='PRIVATE_CANDIDATE',tool_calls=None))
    assert hub.finish(normalized,result(normalized)).response_model=='normalized-label'
    # Failure diagnostics disclose shape, never a partial answer or opaque
    # finish-reason text. Identical terminal replay cannot grow memory forever.
    diagnostic=hub.open(subject='user:one'); hub.pre(**values(diagnostic))
    for _ in range(24): post(hub,diagnostic)
    observed=hub._scopes[(diagnostic.session_id,diagnostic.task_id)]
    assert len(observed.terminal_shapes)==16
    assert observed.terminal_shapes[-1]==dict(finish_reason='stop',has_text=True,
        content_chars=len('PRIVATE_CANDIDATE'),has_tool_calls=False,tool_count=0)
    assert 'PRIVATE_CANDIDATE' not in repr(observed.terminal_shapes)
    checks=hub.diagnostics(diagnostic,result(diagnostic))
    assert checks['exact_text_match'] and all(checks['coordinate_matches'].values())
    assert 'PRIVATE_CANDIDATE' not in repr(checks)
    checks=hub.diagnostics(diagnostic,result(diagnostic,
        turn_exit_reason='local_processing_error(PRIVATE_PROVIDER_ERROR_AND_KEY)',
        error='PRIVATE_PROVIDER_ERROR_AND_KEY',reasoning_tokens=1234,
        output_tokens=True,total_tokens=1_000_000_001))
    assert checks['turn_exit_class']=='local_processing_error' and checks['result_error_present']
    assert checks['token_usage']['reasoning_tokens']==1234
    assert checks['token_usage']['output_tokens'] is None and checks['token_usage']['total_tokens'] is None
    assert 'PRIVATE_PROVIDER_ERROR_AND_KEY' not in repr(checks)
    assert hub.diagnostics(diagnostic,result(diagnostic,turn_exit_reason='PRIVATE_UNKNOWN_CODE'))['turn_exit_class']=='other'
    assert 'PRIVATE_UNKNOWN_CODE' not in repr(hub.diagnostics(diagnostic,result(diagnostic,
        turn_exit_reason='PRIVATE_UNKNOWN_CODE')))
    hub.finish(diagnostic,result(diagnostic))
    assert hub.diagnostics(diagnostic,result(diagnostic)) is None
    trimmed=hub.open(subject='user:one'); hub.pre(**values(trimmed))
    post(hub,trimmed,text='  PRIVATE_CANDIDATE\n')
    checks=hub.diagnostics(trimmed,result(trimmed))
    assert not checks['exact_text_match'] and checks['stripped_text_match']
    trimmed_evidence=hub.finish(trimmed,result(trimmed))
    assert trimmed_evidence.source_content_chars==len('  PRIVATE_CANDIDATE\n')
    assert trimmed_evidence.source_content_sha256==hashlib.sha256(b'  PRIVATE_CANDIDATE\n').hexdigest()
    assert trimmed_evidence.content_sha256==hashlib.sha256(b'PRIVATE_CANDIDATE').hexdigest()
    assert trimmed_evidence.text_projection=='outer-whitespace-v1'
    for original,final in (('A\n\nB','A\nB'),(' A B ','AB'),(' A ',' A '),
                           ('<think>secret</think>A','A'),(' \n\t ','x')):
        scope=hub.open(subject='user:one'); hub.pre(**values(scope)); post(hub,scope,text=original)
        denied(hub,scope,result(scope,text=final))
    preserved=hub.open(subject='user:one'); hub.pre(**values(preserved))
    post(hub,preserved,text=' \nA\n\nB\tC\n')
    assert hub.finish(preserved,result(preserved,text='A\n\nB\tC')).content_chars==len('A\n\nB\tC')
    for reason,count,expected_reason,expected_count in (
            ('length',0,'length',0),('PRIVATE_REASON',True,'other',None),
            (None,10001,None,None)):
        scope=hub.open(subject='user:one'); hub.pre(**values(scope))
        hub.post(**values(scope),response_model='actual-response-label',finish_reason=reason,
            assistant_message=SimpleNamespace(content='PRIVATE_PARTIAL',tool_calls=None),
            assistant_tool_call_count=count)
        shape=hub._scopes[(scope.session_id,scope.task_id)].terminal_shapes[-1]
        assert shape['finish_reason']==expected_reason and shape['tool_count']==expected_count
        assert 'PRIVATE_' not in repr(shape)
        denied(hub,scope,result(scope,text='PRIVATE_PARTIAL'))
    labelled=hub.open(subject='user:one')
    hub.pre(**values(labelled,model='模型 route A',provider='Custom Provider'))
    post(hub,labelled,model='模型 route A',provider='Custom Provider',response_model='厂商 / Model A')
    labelled_result=result(labelled,model='模型 route A'); labelled_result['provider']='Custom Provider'
    assert hub.finish(labelled,labelled_result).response_model=='厂商 / Model A'

    # Distinct explicitly failed request -> one completed backup request. This
    # counts native API identities, never physical HTTP attempts inside the SDK.
    retry=hub.open(subject='user:one')
    hub.pre(**values(retry)); hub.error(**values(retry),error={'message':'DO_NOT_RETAIN_SECRET'})
    hub.pre(**values(retry,request='request:2',model='route-backup'))
    post(hub,retry,request='request:2',model='route-backup',response_model='reported-backup')
    assert 'DO_NOT_RETAIN_SECRET' not in repr(hub._scopes)
    assert hub.finish(retry,result(retry,api_calls=2,model='route-backup')).response_model=='reported-backup'
    shared=hub.open(subject='user:one')
    hub.pre(**values(shared)); hub.error(**values(shared))
    # Core fallback reuses one logical API id and can reset retry_count. Exact
    # started_at is an attempt marker, not an age/order heuristic.
    hub.pre(**values(shared,started=.5,model='route-backup'))
    post(hub,shared,started=.5,model='route-backup',response_model='reported-backup')
    evidence=hub.finish(shared,result(shared,model='route-backup'))
    assert evidence.request_attempt==2 and evidence.api_started_at==.5

    for alteration in (
            {'final_response':'changed'}, {'model':'guessed-last-model'}, {'provider':'other'},
            {'turn_id':'turn:foreign'}, {'session_id':'session:foreign'}, {'api_calls':2},
            {'completed':False}, {'failed':True}, {'partial':True}, {'interrupted':True},
            {'response_transformed':True}, {'response_reused':True}):
        scope=hub.open(subject='user:one'); hub.pre(**values(scope)); post(hub,scope)
        value=result(scope); value.update(alteration); denied(hub,scope,value)
        denied(hub,scope,result(scope))  # Failed finish cannot be retried as qualified.
    for corruption in ('missing-pre','missing-post','missing-model','tool-call','ambiguous','wrong-task','conflict','unfinished'):
        scope=hub.open(subject='user:one')
        if corruption!='missing-pre': hub.pre(**values(scope))
        if corruption not in ('missing-post','wrong-task'):
            post(hub,scope,response_model=None if corruption=='missing-model' else 'actual-response-label')
        if corruption=='tool-call':
            hub.post(**values(scope),response_model='actual-response-label',finish_reason='tool_calls',
                assistant_message=SimpleNamespace(role='assistant',content='x',tool_calls=['tool']),assistant_tool_call_count=1)
        if corruption=='ambiguous':
            hub.pre(**values(scope,request='request:2')); post(hub,scope,request='request:2')
        if corruption=='conflict': post(hub,scope,text='changed')
        if corruption=='wrong-task':
            event={**values(scope),'task_id':'foreign-task'}
            hub.post(**event,response_model='x',finish_reason='stop',assistant_message=Bomb())
        if corruption=='unfinished': hub.pre(**values(scope,request='request:2'))
        denied(hub,scope,result(scope,api_calls=2 if corruption in ('ambiguous','unfinished') else 1))

    cancelled=hub.open(subject='user:one'); hub.pre(**values(cancelled)); hub.cancel(cancelled)
    post(hub,cancelled); denied(hub,cancelled,result(cancelled))
    bounded,_=configured(max_scopes=1,max_requests=1)
    scope=bounded.open(subject='user:one')
    try: bounded.open(subject='user:other')
    except NativeCompletionError: pass
    else: raise AssertionError('scope budget exceeded')
    bounded.pre(**values(scope)); bounded.pre(**values(scope,request='request:2'))
    denied(bounded,scope,result(scope))
    bounded.close()
    unloaded=hub.open(subject='user:one'); hub.pre(**values(unloaded)); post(hub,unloaded)
    context.handles[1].dispose()
    denied(hub,unloaded,result(unloaded))
    hub.close(); hub.close()
    assert not context.callbacks
    try: hub.open(subject='user:one')
    except NativeCompletionError: pass
    else: raise AssertionError('retired observer reopened')
    class BrokenContext(Context):
        def register_hook(self,name,callback):
            if name=='post_api_request': raise RuntimeError('synthetic registration failure')
            return super().register_hook(name,callback)
    failed=NativeCompletionHub(); broken=BrokenContext()
    try: failed.install(broken)
    except RuntimeError: pass
    else: raise AssertionError('partial registration became ready')
    assert not broken.callbacks

    # A raw reasoning-only length response is non-output, never final evidence.
    # Core may continue once; only the later exact post can qualify final text.
    continued,continuation_context=configured(observe_execution=True)
    assert 'llm_execution' in continuation_context.callbacks
    def raw_response(content=None,reason='length',role='assistant',tools=None,function=None):
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason,
            message=SimpleNamespace(role=role,content=content,tool_calls=tools,function_call=function))])
    scope=continued.open(subject='user:one'); continued.pre(**values(scope))
    original=raw_response(); requests=[]; original_request={'model':'synthetic'}
    def next_call(request):
        requests.append(request); return original
    assert continued.execution(request=original_request,next_call=next_call,**values(scope)) is original
    assert requests==[original_request] and requests[0] is original_request
    continued.pre(**values(scope,request='request:2')); post(continued,scope,request='request:2')
    final=continued.finish(scope,result(scope,api_calls=2))
    assert final.api_request_id=='request:2' and not final.authority_granted
    assert final.turn_identity_origin=='result-envelope-v1'
    for binding_kind in ('owned','absent','foreign-session','foreign-task','foreign-turn','wrong-result'):
        scope=continued.open(subject='user:one'); continued.pre(**values(scope))
        continued.execution(request={},next_call=lambda _:raw_response(),**values(scope))
        continued.pre(**values(scope,request='request:2')); post(continued,scope,request='request:2')
        document=result(scope,api_calls=2); document.pop('turn_id')
        binding=(scope.session_id,scope.task_id,'turn:1')
        if binding_kind=='absent': binding=None
        if binding_kind=='foreign-session': binding=('foreign',scope.task_id,'turn:1')
        if binding_kind=='foreign-task': binding=(scope.session_id,'foreign','turn:1')
        if binding_kind=='foreign-turn': binding=(scope.session_id,scope.task_id,'foreign')
        if binding_kind=='wrong-result': document['turn_id']='foreign'
        try: bound=continued.finish(scope,document,worker_turn_binding=binding)
        except NativeCompletionError:
            assert binding_kind!='owned'
        else:
            assert binding_kind=='owned'
            assert bound.turn_identity_origin=='isolated-worker-continuation-v1'
    # A foreign scope is never inspected; downstream errors are not retried.
    class RawBomb:
        @property
        def choices(self): raise AssertionError('foreign response inspected')
    foreign=RawBomb()
    assert continued.execution(request={},next_call=lambda _:foreign,
        session_id='foreign',task_id='foreign') is foreign
    def downstream_error(_): raise RuntimeError('synthetic downstream failure')
    try: continued.execution(request={},next_call=downstream_error)
    except RuntimeError: pass
    else: raise AssertionError('execution failure swallowed')
    # Partial text, tools/functions, role mismatch and unknown/missing response
    # shapes cannot close a missing post. A complete second reply is insufficient.
    for raw in (raw_response(content='partial'),raw_response(content=' '),
                raw_response(tools=['unadmitted']),raw_response(function={'name':'x'}),
                raw_response(role='user'),raw_response(reason='stop'),SimpleNamespace()):
        scope=continued.open(subject='user:one'); continued.pre(**values(scope))
        assert continued.execution(request={},next_call=lambda _,r=raw:r,**values(scope)) is raw
        continued.pre(**values(scope,request='request:2')); post(continued,scope,request='request:2')
        denied(continued,scope,result(scope,api_calls=2))
    scope=continued.open(subject='user:one'); continued.pre(**values(scope))
    continued.execution(request={},next_call=lambda _:raw_response(),**values(scope))
    # An auxiliary summary/uncompleted turn cannot be promoted to a completion.
    denied(continued,scope,{**result(scope),'completed':False,'turn_exit_reason':'max_iterations_reached(1/1)'})
    scope=continued.open(subject='user:one'); continued.pre(**values(scope))
    continued.execution(request={},next_call=lambda _:raw_response(),**values(scope,model='wrong-route'))
    continued.pre(**values(scope,request='request:2')); post(continued,scope,request='request:2')
    denied(continued,scope,result(scope,api_calls=2))
    scope=continued.open(subject='user:one'); continued.pre(**values(scope)); post(continued,scope)
    continuation_context.handles[-1].dispose()
    denied(continued,scope,result(scope))
    continued.close(); assert not continuation_context.callbacks


with tempfile.TemporaryDirectory(prefix='alive-native-completion-') as folder:
    previous=os.environ.get('HERMES_HOME'); os.environ['HERMES_HOME']=str(Path(folder)/'profile')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
    try: exercise()
    finally:
        if previous is None: os.environ.pop('HERMES_HOME',None)
        else: os.environ['HERMES_HOME']=previous
print('HERMES_ALIVE_NATIVE_COMPLETION_OK')
