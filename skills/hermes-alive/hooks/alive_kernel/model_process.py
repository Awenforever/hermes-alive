"""Single-use host-owned model worker lease with observed child termination.

This is not a sandbox, provider resolver, transport or process-tree supervisor.
The trusted native worker must prohibit spawning descendants before loading Core.
The host must drain retained leases before closing its event loop/profile.
"""
import asyncio
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import subprocess
import tempfile
from types import MappingProxyType


class ModelProcessError(RuntimeError):
    """Static diagnostic only; never include worker stderr, prompts or secrets."""


class ModelProcessUncertain(ModelProcessError):
    """The retained lease is not closed; do not restart or clean its workspace."""


@dataclass(frozen=True,slots=True)
class ModelProcessResult:
    returncode: int
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)
    direct_child_terminal: bool = True
    process_tree_terminal_proven: bool = False


class ManagedModelProcess:
    """One operation, one spawn; timeout/cancel requests stop, never a retry."""

    def __init__(self,*,command,cwd,environment,private_tmp_dir,timeout_seconds=60,
            termination_grace_seconds=1,input_limit_bytes=131072,output_limit_bytes=262144):
        command=tuple(command)
        cwd=Path(cwd).resolve(strict=True)
        private_tmp_dir=Path(private_tmp_dir).resolve(strict=True)
        if (not command or not all(isinstance(x,str) and x and '\0' not in x for x in command)
                or not Path(command[0]).is_absolute() or not cwd.is_dir() or not private_tmp_dir.is_dir()
                or type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds)
                or not .05<=timeout_seconds<=300
                or type(termination_grace_seconds) not in (int,float)
                or not math.isfinite(termination_grace_seconds) or not .05<=termination_grace_seconds<=10
                or type(input_limit_bytes) is not int or not 1<=input_limit_bytes<=1048576
                or type(output_limit_bytes) is not int or not 1<=output_limit_bytes<=1048576):
            raise ValueError('invalid model worker process capability')
        environment=dict(environment)
        if any(not isinstance(k,str) or not k or '=' in k or '\0' in k
                or not isinstance(v,str) or '\0' in v for k,v in environment.items()):
            raise ValueError('invalid model worker environment')
        folded={}
        for key,value in environment.items():
            if key.upper() in folded and folded[key.upper()]!=value:
                raise ValueError('ambiguous model worker environment')
            folded[key.upper()]=value
        self.command,self.cwd,self.private_tmp_dir=command,cwd,private_tmp_dir
        self.environment=MappingProxyType(environment)
        self.timeout_seconds,self.grace=timeout_seconds,termination_grace_seconds
        self.input_limit,self.output_limit=input_limit_bytes,output_limit_bytes
        self._task=None
        self._process=None
        self._stop=asyncio.Event()
        self._phase='unused'

    @property
    def status(self):
        return dict(phase=self._phase,used=self._task is not None,
            closed=self._task is not None and self._task.done(),
            pid=self._process.pid if self._process else None,
            returncode=self._process.returncode if self._process else None)

    async def _spawn(self,source,output,errors):
        return await asyncio.create_subprocess_exec(*self.command,cwd=self.cwd,env=dict(self.environment),
            stdin=source,stdout=output,stderr=errors,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    async def _stop_child(self):
        process=self._process
        if process.returncode is not None: return
        self._phase='stopping'
        try: process.terminate()
        except (ProcessLookupError,OSError): pass
        terminal=asyncio.create_task(process.wait())
        done,_=await asyncio.wait({terminal},timeout=self.grace)
        if done: return
        try: process.kill()
        except (ProcessLookupError,OSError): pass
        # No deadline can manufacture termination. The outer caller can return
        # uncertain while this retained supervisor awaits the actual OS handle.
        await terminal

    async def _supervise(self,payload):
        # Regular private temporary handles avoid inherited-pipe EOF/deadlock.
        # These transient bytes are not encrypted memory or secure-erasure proof.
        with tempfile.TemporaryFile(dir=self.private_tmp_dir) as source, \
                tempfile.TemporaryFile(dir=self.private_tmp_dir) as output, \
                tempfile.TemporaryFile(dir=self.private_tmp_dir) as errors:
            source.write(payload); source.seek(0)
            self._phase='starting'
            try:
                self._process=await self._spawn(source,output,errors)
                self._phase='running'
                exceeded=False
                while self._process.returncode is None and not self._stop.is_set():
                    if any(os.fstat(stream.fileno()).st_size>self.output_limit for stream in (output,errors)):
                        exceeded=True; self._stop.set(); break
                    await asyncio.sleep(.02)
                if self._stop.is_set(): await self._stop_child()
                await self._process.wait()
                self._phase='terminal'
                if exceeded or any(os.fstat(stream.fileno()).st_size>self.output_limit for stream in (output,errors)):
                    raise ModelProcessError('model worker output limit exceeded')
                output.seek(0); errors.seek(0)
                return ModelProcessResult(self._process.returncode,output.read(self.output_limit+1),
                    errors.read(self.output_limit+1))
            except asyncio.CancelledError:
                self._stop.set()
                if self._process is not None:
                    await asyncio.shield(self._stop_child())
                    self._phase='terminal'
                raise
            except OSError:
                if self._process is not None and self._process.returncode is None:
                    self._stop.set(); await self._stop_child()
                self._phase='launch_or_capture_failed'
                raise ModelProcessError('model worker launch or capture failed') from None

    @staticmethod
    def _observe_terminal(task):
        # Retain/observe failures even if the awaiter was cancelled or returned
        # uncertain. This does not suppress the same exception when awaited.
        if not task.cancelled(): task.exception()

    async def wait_closed(self,*,timeout_seconds=3):
        if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<=timeout_seconds<=30:
            raise ValueError('invalid worker observation timeout')
        if self._task is None: return True
        done,_=await asyncio.wait({self._task},timeout=timeout_seconds)
        return bool(done)

    async def run(self,payload):
        if self._task is not None: raise ModelProcessError('model worker lease already used')
        if not isinstance(payload,bytes) or len(payload)>self.input_limit:
            raise ValueError('model worker input outside bound')
        self._task=asyncio.create_task(self._supervise(payload))
        self._task.add_done_callback(self._observe_terminal)
        try:
            done,_=await asyncio.wait({self._task},timeout=self.timeout_seconds)
            if done: return self._task.result()
            self._stop.set()
            if not await self.wait_closed(timeout_seconds=2*self.grace+1):
                raise ModelProcessUncertain('model worker remains owned and not terminal')
            raise ModelProcessError('model worker timed out; owned lease is closed')
        except asyncio.CancelledError:
            self._stop.set()
            # Repeated cancellation may interrupt this bounded observation, but
            # the strongly retained supervisor still owns files and the child.
            await asyncio.shield(self.wait_closed(timeout_seconds=2*self.grace+1))
            raise
