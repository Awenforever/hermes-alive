"""Real owned child handles on this OS, not mocked process/PID liveness."""
import asyncio
import os
import signal
from pathlib import Path
import sys
import tempfile


async def exercise(root):
    from alive_kernel.model_process import ManagedModelProcess,ModelProcessError,ModelProcessUncertain
    fixture=Path(__file__).resolve().parent/'fixtures'/'model-process-worker.py'
    def lease(mode,*,timeout=2,output_limit=65536):
        return ManagedModelProcess(command=(str(Path(sys.executable).absolute()),'-B',str(fixture),mode,str(root/'ready')),
            cwd=root,environment=dict(os.environ),private_tmp_dir=root,timeout_seconds=timeout,
            termination_grace_seconds=.05,output_limit_bytes=output_limit)
    async def closed(worker):
        assert await worker.wait_closed(timeout_seconds=3)
        status=worker.status
        assert status['closed'] and status['returncode'] is not None and status['phase']=='terminal'
    async def wait_ready():
        for _ in range(200):
            if (root/'ready').exists(): return
            await asyncio.sleep(.01)
        raise AssertionError('owned synthetic worker did not reach ready')
    echo=lease('echo')
    result=await echo.run(b'PRIVATE_SYNTHETIC_PAYLOAD')
    assert result.stdout==b'PRIVATE_SYNTHETIC_PAYLOAD' and result.returncode==0
    assert result.direct_child_terminal and not result.process_tree_terminal_proven
    assert 'PRIVATE_SYNTHETIC_PAYLOAD' not in repr(result)
    await closed(echo)
    try: await echo.run(b'no second spawn')
    except ModelProcessError: pass
    else: raise AssertionError('single-use lease repeated a worker')
    fail=lease('fail'); result=await fail.run(b'PRIVATE_FAILURE')
    assert result.returncode==7 and result.stderr==b'PRIVATE_FAILURE' and 'PRIVATE_FAILURE' not in repr(result)
    await closed(fail)
    flood=lease('flood',output_limit=1024)
    try: await flood.run(b'')
    except ModelProcessError as error: assert 'output limit' in str(error)
    else: raise AssertionError('oversized worker output admitted')
    await closed(flood)

    for mode in ('slow','ignore-term'):
        if (root/'ready').exists(): (root/'ready').unlink()
        timeout=lease(mode,timeout=.5)
        try: await timeout.run(b'')
        except ModelProcessError as error: assert 'timed out' in str(error)
        else: raise AssertionError('deadline silently became success')
        assert (root/'ready').exists()
        await closed(timeout)
        if mode=='ignore-term' and os.name=='posix':
            assert timeout.status['returncode']==-signal.SIGKILL
    (root/'ready').unlink()
    cancel=lease('ignore-term',timeout=10)
    caller=asyncio.create_task(cancel.run(b''))
    await wait_ready(); caller.cancel()
    try: await caller
    except asyncio.CancelledError: pass
    else: raise AssertionError('caller cancellation became a normal model result')
    await closed(cancel)
    (root/'ready').unlink()
    repeated=lease('ignore-term',timeout=10)
    caller=asyncio.create_task(repeated.run(b''))
    await wait_ready(); caller.cancel(); await asyncio.sleep(0); caller.cancel()
    try: await caller
    except asyncio.CancelledError: pass
    else: raise AssertionError('repeated cancellation became a normal result')
    await closed(repeated)

    # Delay actual process creation. An observation deadline is not terminal and
    # must not close its files or issue another spawn. Resume the same lease.
    delayed=lease('echo',timeout=.05)
    gate=asyncio.Event(); entered=asyncio.Event(); spawned=[]; captures=[]
    original=delayed._spawn
    async def delayed_spawn(source,output,errors):
        captures.extend((source,output,errors))
        entered.set(); await gate.wait()
        assert not any(stream.closed for stream in (source,output,errors))
        process=await original(source,output,errors); spawned.append(process.pid); return process
    delayed._spawn=delayed_spawn
    caller=asyncio.create_task(delayed.run(b'PRIVATE_DELAYED'))
    await entered.wait()
    try: await caller
    except ModelProcessUncertain: pass
    else: raise AssertionError('pending startup falsely called terminal')
    assert not delayed.status['closed'] and delayed.status['pid'] is None
    assert not any(stream.closed for stream in captures)
    assert not await delayed.wait_closed(timeout_seconds=0)
    try: await delayed.run(b'retry forbidden')
    except ModelProcessError: pass
    else: raise AssertionError('unknown worker restarted')
    gate.set(); await closed(delayed)
    assert len(spawned)==1
    assert all(stream.closed for stream in captures)
    # Invalid input is rejected before any process capability is consumed.
    invalid=lease('echo')
    try: await invalid.run(b'x'*131073)
    except ValueError: pass
    else: raise AssertionError('input limit ignored')
    assert not invalid.status['used'] and await invalid.wait_closed(timeout_seconds=0)
    mirrors={'SYNTHETIC_CASE_MIRROR':'same','synthetic_case_mirror':'same'}
    mirrored=ManagedModelProcess(command=(str(Path(sys.executable).absolute()),'-V'),cwd=root,
        environment=mirrors,private_tmp_dir=root)
    mirrors['SYNTHETIC_CASE_MIRROR']='changed-after-binding'
    assert mirrored.environment['SYNTHETIC_CASE_MIRROR']=='same'
    try: ManagedModelProcess(command=(str(Path(sys.executable).absolute()),'-V'),cwd=root,
        environment=mirrors,private_tmp_dir=root)
    except ValueError: pass
    else: raise AssertionError('conflicting case aliases admitted')
    missing=ManagedModelProcess(command=(str(root/'missing-worker-executable'),),cwd=root,
        environment=dict(os.environ),private_tmp_dir=root)
    try: await missing.run(b'')
    except ModelProcessError: pass
    else: raise AssertionError('failed launch admitted as a completion')
    assert await missing.wait_closed(timeout_seconds=0) and missing.status['phase']=='launch_or_capture_failed'


with tempfile.TemporaryDirectory(prefix='alive-model-process-') as folder:
    root=Path(folder)
    previous=os.environ.get('HERMES_HOME'); os.environ['HERMES_HOME']=str(root/'profile')
    previous_shared=os.environ.get('HERMES_ALIVE_SHARED_DIR')
    os.environ['HERMES_ALIVE_SHARED_DIR']=str(root/'runtime')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
    try: asyncio.run(exercise(root))
    finally:
        if previous is None: os.environ.pop('HERMES_HOME',None)
        else: os.environ['HERMES_HOME']=previous
        if previous_shared is None: os.environ.pop('HERMES_ALIVE_SHARED_DIR',None)
        else: os.environ['HERMES_ALIVE_SHARED_DIR']=previous_shared
print('HERMES_ALIVE_MODEL_PROCESS_OK')
