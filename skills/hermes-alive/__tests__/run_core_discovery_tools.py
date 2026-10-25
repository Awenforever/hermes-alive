"""Physical read settlement, revocation, profile and reload fencing; no network."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))


async def exercise(home):
    from alive_kernel.core_discovery_tools import CoreDiscoveryTools
    from alive_kernel.host_discovery import HostDiscoveryError,HostReadUncertainError
    state=['owner:revision1'];calls=[];unload=[]
    started=threading.Event();release=threading.Event()
    def dispatch(name,args):
        calls.append((name,args))
        if args.get('query')=='held':
            started.set()
            assert release.wait(5),'fixture failed to release physical worker'
        if args.get('query')=='revoked':state[0]='owner:revision2'
        return dict(success=True,data=dict(web=[]))
    ctx=SimpleNamespace(_manager=SimpleNamespace(scope_key=str(home)),
        on_unload=unload.append,dispatch_tool=dispatch)
    def make(timeout=2):
        return CoreDiscoveryTools(ctx,read_binding=lambda:state[0],
            approved_queries=('public','held','revoked'),timeout_seconds=timeout)
    host=make()
    default=CoreDiscoveryTools(ctx,read_binding=lambda:state[0],approved_queries=('public',))
    assert default.timeout_seconds==180  # Whole host stage must not cap Core's120s extraction at60s.
    default.close()
    assert json.loads(await host.search('public',limit=1))['success']
    try:await host.search('PRIVATE_MEMORY_NOT_APPROVED',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('unapproved query disclosed')
    assert len(calls)==1
    # A derived query needs a current host grant, not a model's permission flag.
    approved=[False];checks=[]
    def query_grant(query):
        checks.append(query)
        return approved[0] and query=='public original source'
    derived=CoreDiscoveryTools(ctx,read_binding=lambda:state[0],approved_queries=('public',),
        query_validator=query_grant)
    try:await derived.search('public original source',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('ungranted derived query disclosed')
    assert len(calls)==1
    approved[0]=True
    assert json.loads(await derived.search('public original source',limit=1))['success']
    assert checks.count('public original source')==3  # Denial, pre-schedule and inside physical worker.
    assert len(calls)==2
    approved[0]=False
    try:await derived.search('public original source',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('revoked derived query disclosed')
    derived.close()
    before_dispatch=len(calls);late_checks=[]
    def expiring_grant(query):
        late_checks.append(query)
        return len(late_checks)==1
    late=CoreDiscoveryTools(ctx,read_binding=lambda:state[0],approved_queries=('public',),
        query_validator=expiring_grant)
    try:await late.search('public original source',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('grant revocation between scheduling and IO was ignored')
    assert len(late_checks)==2 and len(calls)==before_dispatch and not late.pending
    validation_entered=threading.Event();validation_release=threading.Event();validation_calls=[]
    def slow_grant(query):
        validation_calls.append(query)
        if len(validation_calls)==2:
            validation_entered.set()
            assert validation_release.wait(5)
        return True
    slow=CoreDiscoveryTools(ctx,read_binding=lambda:state[0],approved_queries=('public',),
        query_validator=slow_grant,timeout_seconds=.1)
    try:
        try:await slow.search('public original source',limit=1)
        except HostReadUncertainError:pass
        else:raise AssertionError('slow grant validation did not remain physically pending')
        assert validation_entered.is_set() and slow.pending and len(calls)==before_dispatch
    finally:validation_release.set()
    assert (await slow.reap_pending(timeout_seconds=2))['remaining']==0
    assert len(calls)==before_dispatch,'HTTP dispatch began after scope retired during grant validation'
    # A timeout does not release the physical lock or permit a new generation.
    held=make(.03)
    try:
        try:await held.search('held',limit=1)
        except HostReadUncertainError:pass
        else:raise AssertionError('held read did not time out')
        assert started.is_set() and held.pending
        replacement=make()
        try:await replacement.search('public',limit=1)
        except TimeoutError:pass
        else:raise AssertionError('new generation bypassed pending physical read')
        assert len(calls)==3
    finally:release.set()
    assert (await held.reap_pending(timeout_seconds=2))==dict(remaining=0,retired=True)
    try:await held.search('public',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('retired capability reused')
    assert json.loads(await make().search('public',limit=1))['success']
    revoked=make()
    try:await revoked.search('revoked',limit=1)
    except HostDiscoveryError:pass
    else:raise AssertionError('revoked result admitted')
    # Cancellation retains the worker too; unload cannot start another read.
    release.clear();started.clear();cancelled=make()
    task=asyncio.create_task(cancelled.search('held',limit=1))
    try:
        for _ in range(100):
            if started.is_set():break
            await asyncio.sleep(.005)
        assert started.is_set()
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
        assert cancelled.pending
        unload[-1]()
    finally:release.set()
    assert (await cancelled.reap_pending(timeout_seconds=2))['remaining']==0
    count=len(calls)
    with patch.dict(sys.modules,hermes_constants=SimpleNamespace(get_hermes_home=lambda:home/'foreign')):
        try:await make().search('public',limit=1)
        except HostDiscoveryError:pass
        else:raise AssertionError('foreign profile read allowed')
    assert len(calls)==count


with tempfile.TemporaryDirectory(prefix='alive-core-reads-') as folder:
    home=Path(folder)/'profile';home.mkdir()
    os.environ['HERMES_HOME']=str(home)
    os.environ['HERMES_ALIVE_SHARED_DIR']=str(Path(folder)/'runtime')
    with patch.dict(sys.modules,hermes_constants=SimpleNamespace(get_hermes_home=lambda:home)):
        asyncio.run(exercise(home))
print('HERMES_ALIVE_CORE_DISCOVERY_TOOLS_OK')
