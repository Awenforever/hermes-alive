"""Actual Core probe as one supervised worker; physical HTTP stays synthetic."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--core',type=Path,required=True)
args=parser.parse_args()
core=args.core.resolve(strict=True)
package=Path(__file__).resolve().parents[1]


async def exercise(root):
    from alive_kernel.model_process import ManagedModelProcess
    child_tmp=root/'child-temporary'; child_tmp.mkdir(mode=0o700)
    child_environment={**os.environ,'TMPDIR':str(child_tmp),'TEMP':str(child_tmp),'TMP':str(child_tmp),
        'HERMES_ALIVE_SHARED_DIR':str(root/'child-runtime')}
    child=ManagedModelProcess(command=(str(Path(sys.executable).absolute()),'-B',
        str(package/'tests'/'probe_alive_native_host.py'),'--core',str(core),
        '--kernel-package',str(package),'--scoped-completion','--deny-child-processes'),
        cwd=root,environment=child_environment,private_tmp_dir=root,timeout_seconds=30,termination_grace_seconds=1)
    result=await child.run(b'{"fixture":"synthetic-native-worker-no-tools"}')
    if result.returncode:
        # Only this synthetic/no-network probe emits bounded child diagnostics;
        # a production model caller must not relay arbitrary worker stderr.
        print(result.stdout[-2500:].decode('utf-8',errors='replace'),flush=True)
        print(result.stderr[-2500:].decode('utf-8',errors='replace'),flush=True)
    assert result.returncode==0 and child.status['closed'] and child.status['phase']=='terminal'
    lines=result.stdout.decode('utf-8',errors='strict').splitlines()
    for marker in ('HERMES_ALIVE_NATIVE_CONSTRUCTOR_PROMPT_BOUNDARY_OK',
            'HERMES_ALIVE_NATIVE_SHADOW_SOURCE_BOUNDARY_OK','HERMES_ALIVE_NATIVE_SCOPED_COMPLETION_OK'):
        assert marker in lines
        print(marker,flush=True)
    summaries=[json.loads(line) for line in lines if line.startswith('{"native_shadow_calls"')]
    assert len(summaries)==1 and summaries[0]['descendant_guard_verified'] is True
    assert summaries[0]['network_attempts']==summaries[0]['actual_model_calls']==summaries[0]['sends']==0
    assert not result.process_tree_terminal_proven
    assert await child.wait_closed(timeout_seconds=0)
    print('HERMES_ALIVE_MANAGED_NATIVE_HOST_OK',flush=True)
    # Also stop actual Core while its first controlled provider call is pending,
    # not merely a generic sleep helper. Never admit its partial stdout as a reply.
    ready=root/'native-request-ready'
    blocked=ManagedModelProcess(command=(*child.command,'--hold-first-request','--request-ready-file',str(ready)),
        cwd=root,environment=child_environment,private_tmp_dir=root,timeout_seconds=30,termination_grace_seconds=.1)
    caller=asyncio.create_task(blocked.run(b'{"fixture":"synthetic-pending-native-request"}'))
    try:
        for _ in range(1500):
            if ready.exists(): break
            if caller.done(): await caller; raise AssertionError('native pending request was not reached')
            await asyncio.sleep(.01)
        assert ready.exists() and int(ready.read_text())==blocked.status['pid']
        caller.cancel(); await asyncio.sleep(0); caller.cancel()
        try: await caller
        except asyncio.CancelledError: pass
        else: raise AssertionError('pending native cancellation became a model result')
        assert await blocked.wait_closed(timeout_seconds=3)
        assert blocked.status['phase']=='terminal' and blocked.status['returncode'] is not None
        partial=blocked._task.result()
        assert partial.returncode!=0 and b'HERMES_ALIVE_NATIVE_SCOPED_COMPLETION_OK' not in partial.stdout
    finally:
        if not caller.done(): caller.cancel()
        await asyncio.gather(caller,return_exceptions=True)
        assert await blocked.wait_closed(timeout_seconds=3)
    print('HERMES_ALIVE_MANAGED_NATIVE_CANCEL_OK',flush=True)


with tempfile.TemporaryDirectory(prefix='alive-managed-native-parent-') as folder:
    previous=os.environ.get('HERMES_HOME'); os.environ['HERMES_HOME']=str(Path(folder)/'parent-profile')
    previous_shared=os.environ.get('HERMES_ALIVE_SHARED_DIR')
    os.environ['HERMES_ALIVE_SHARED_DIR']=str(Path(folder)/'parent-runtime')
    sys.path.insert(0,str(package/'hooks'))
    try: asyncio.run(exercise(Path(folder)))
    finally:
        if previous is None: os.environ.pop('HERMES_HOME',None)
        else: os.environ['HERMES_HOME']=previous
        if previous_shared is None: os.environ.pop('HERMES_ALIVE_SHARED_DIR',None)
        else: os.environ['HERMES_ALIVE_SHARED_DIR']=previous_shared
