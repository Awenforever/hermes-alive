"""Physical read/lifecycle contracts with controlled Core scope, no model/network."""
import asyncio
import contextvars
from datetime import datetime,timedelta,timezone
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS
from unittest.mock import patch

skill=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(skill/'hooks'),str(skill/'scripts'),str(skill/'tests')]
from alive_kernel.core_context_read import CoreContextRead,ContextReadUncertainError
from alive_kernel.native_cognition_host import NativeCognitionHost
from alive_kernel.native_worker_protocol import NativeWorkerError
from alive_kernel.feedback_context import FeedbackContextReader
from alive_kernel.feedback_recall import FeedbackRecallSelector
from alive_kernel import Sensitivity
from run_feedback_recall import prepare_history,response

home_scope=contextvars.ContextVar('controlled_core_home')
def spawn(target,*,name):
    context=contextvars.copy_context()
    return threading.Thread(target=lambda:context.run(target),name=name,daemon=True)

async def test(root):
    home=root/'home';home.mkdir();home_scope.set(home)
    os.environ['HERMES_HOME']=str(home)
    callbacks=[];revision=['one']
    ctx=NS(_manager=NS(scope_key=str(home)),on_unload=callbacks.append)
    binding=lambda:revision[0]
    reader=CoreContextRead(ctx,timeout_seconds=2)
    assert await reader.invoke(lambda:home_scope.get(),read_binding=binding)==home
    entered=threading.Event();release=threading.Event()
    def held():entered.set();assert release.wait(5);return 'synthetic private result'
    task=asyncio.create_task(reader.invoke(held,read_binding=binding))
    try:
        for _ in range(200):
            if entered.is_set():break
            await asyncio.sleep(.005)
        assert entered.is_set();task.cancel()
        try:await task
        except asyncio.CancelledError:pass
        else:raise AssertionError('cancelled read became completed')
        assert reader.pending and (await reader.reap_pending())['remaining']==1
        callbacks[0]()  # Unload cannot release a worker-owned lock.
        spec=importlib.util.spec_from_file_location('alive_kernel._context_read_new_generation',
            skill/'hooks/alive_kernel/core_context_read.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        replacement=module.CoreContextRead(ctx,timeout_seconds=2)
        assert type(replacement) is not type(reader)
        try:replacement.ensure_available()
        except NativeWorkerError:pass
        else:raise AssertionError('replacement generation bypassed old physical lock')
        async def reap(**kwargs):return dict(closed=0,remaining=0)
        caller=NS(pending=(),calls=0,reap_pending=reap)
        class Host:
            subject='user:synthetic';running=False;configuration_id='synthetic-config'
            runtime=NS(reconciliation=NS(_owner_policy=lambda owner:NS(enabled=True,event_id='policy:one',revision=1)))
            started=0;saved=None
            async def step_bound(self,build):
                self.started+=1;parameters=build(NS(operation_id='read-cycle'))
                if inspect.isawaitable(parameters):parameters=await parameters
                self.saved=parameters['expression_parameters']['read_context']
                return await self.saved(lambda:home_scope.get())
        host=Host()
        native=NativeCognitionHost(host,profile_id='profile:synthetic',profile_home=home,
            read_configuration=lambda:{},read_credential_names=lambda **_:(),interpreter=sys.executable,
            core=root,private_root=root,environment={},resolve_domain=lambda *labels:'synthetic',
            context_reads=replacement,caller_factory=lambda **kwargs:caller)
        try:await native.step(dict(expression_parameters={}))
        except NativeWorkerError:pass
        else:raise AssertionError('host prepared public/model work before old read settled')
        assert host.started==0
    finally:release.set();assert (await reader.reap_pending(timeout_seconds=2))['remaining']==0
    try:await reader.invoke(lambda:'closed',read_binding=binding)
    except NativeWorkerError:pass
    else:raise AssertionError('unloaded read capability reused')
    assert await native.step(dict(expression_parameters={}))==home
    assert host.started==1 and not native.pending
    try:await host.saved(lambda:'expired cycle')
    except NativeWorkerError:pass
    else:raise AssertionError('cycle read capability escaped its native lifetime')
    # Native host rejects injected read capabilities rather than trusting them.
    try:await native.step(dict(expression_parameters=dict(read_context=lambda operation:operation())))
    except NativeWorkerError:pass
    else:raise AssertionError('untrusted read capability injected')
    assert host.started==1
    timeout=CoreContextRead(ctx,timeout_seconds=.02);entered.clear();release.clear()
    try:
        try:await timeout.invoke(held,read_binding=binding)
        except ContextReadUncertainError:pass
        else:raise AssertionError('wait timeout represented physical completion')
        assert entered.is_set() and timeout.pending
    finally:release.set();await timeout.reap_pending(timeout_seconds=2)
    def revoked():revision[0]='two';return 'must not be admitted'
    try:await replacement.invoke(revoked,read_binding=binding)
    except NativeWorkerError:pass
    else:raise AssertionError('revoked read result admitted')
    def private_error():raise ValueError('PRIVATE_BODY_MUST_NOT_ESCAPE')
    try:await replacement.invoke(private_error,read_binding=binding)
    except NativeWorkerError as error:
        assert 'PRIVATE_BODY' not in str(error) and error.__context__ is None
    else:raise AssertionError('worker failure hidden')
    foreign=root/'foreign';foreign.mkdir()
    token=home_scope.set(foreign)
    try:
        try:await replacement.invoke(lambda:'foreign',read_binding=binding)
        except NativeWorkerError:pass
        else:raise AssertionError('foreign profile entered owner reader')
    finally:home_scope.reset(token)
    # Actual feedback index queries use the delegated capability, not a mock
    # positive result. A heartbeat continues while the physical read is held.
    interpreter,owner,target=prepare_history(root/'case',noise=3)
    selector=FeedbackRecallSelector(FeedbackContextReader(interpreter.journal,content_vault=interpreter.vault))
    original=selector.windows;main_thread=threading.get_ident();reads=[]
    def windows(**kwargs):
        assert threading.get_ident()!=main_thread and home_scope.get()==home
        reads.append(True);time.sleep(.03);return original(**kwargs)
    query=dict(inquiry='Synthetic research relevance.');ticks=[];stop=False
    async def pulse():
        while not stop:ticks.append(time.monotonic());await asyncio.sleep(.005)
    pulse_task=asyncio.create_task(pulse())
    async def read_context(operation):return await replacement.invoke(operation,read_binding=binding)
    async def choose(**kwargs):
        data=json.loads(kwargs['messages'][1]['content'])
        assert target in {v['outcome_event_id'] for w in data['index_windows'] for v in w['entries']}
        return response(dict(outcome_event_ids=[target],continue_older=False,reason='Synthetic input routing.'))
    try:
        with patch.object(selector,'windows',side_effect=windows):
            result=await selector.run(subject=owner,operation_id='owned-index',query=query,validate_query=lambda:query,
                retention_until=datetime.now(timezone.utc)+timedelta(minutes=5),call=choose,read_context=read_context)
        assert result['outcome_event_ids']==[target] and reads and len(ticks)>10
    finally:stop=True;await pulse_task
    assert not replacement.pending

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-core-context-') as directory:
        modules={'hermes_constants':NS(get_hermes_home=lambda:home_scope.get()),
            'agent.memory_provider':NS(spawn_context_thread=spawn)}
        with patch.dict(sys.modules,modules):asyncio.run(test(Path(directory)))
    print('HERMES_ALIVE_CORE_CONTEXT_READ_OK')
