"""Opt-in ModelCaller using one private native worker per logical invocation.

Hermes/host supply route resolution, consented identity and current-binding check.
The caller does not discover models, read a foreground profile, or grant actions.
"""
import json
import os
import re
from pathlib import Path
import tempfile
from types import MappingProxyType, SimpleNamespace
from uuid import uuid4

from .model_process import ManagedModelProcess
from .native_worker_protocol import (NativeWorkerError,canonical,identifier,request_digest,
    validate_request,validate_completion)


class NativeWorkerCaller:
    def __init__(self,*,subject,operation_id,interpreter,core,private_root,environment,
            resolve_runtime,assert_current,identity='',entrypoint=None,timeout_seconds=90,max_calls=16):
        self.subject,self.operation_id=identifier(subject),identifier(operation_id)
        if not callable(resolve_runtime) or not callable(assert_current) or type(max_calls) is not int or not 1<=max_calls<=32:
            raise NativeWorkerError('explicit bounded host capability required')
        self.interpreter=Path(interpreter).absolute()  # Do not resolve a managed venv symlink into base Python.
        self.core=Path(core).resolve(strict=True)
        self.private_root=Path(private_root).resolve(strict=True)
        self.entrypoint=Path(entrypoint or Path(__file__).resolve().parents[1]/'native_model_worker.py').absolute()
        if not self.interpreter.is_file() or not self.entrypoint.is_file() or not self.core.is_dir() or not self.private_root.is_dir():
            raise NativeWorkerError('native worker runtime not admitted')
        if type(timeout_seconds) not in (int,float) or not 10<=timeout_seconds<=300:
            raise NativeWorkerError('native worker lifetime outside bound')
        self.environment=MappingProxyType(dict(environment))
        self.resolve_runtime,self.assert_current,self.identity=resolve_runtime,assert_current,identity
        self.timeout,self.max_calls,self.calls=timeout_seconds,max_calls,0
        self._jobs={}

    def _cleanup(self,key):
        job=self._jobs.get(key)
        if job is not None:
            job[1].cleanup()
            self._jobs.pop(key,None)

    def _current(self):
        try: valid=self.assert_current()
        except Exception: valid=False
        if valid is not True: raise NativeWorkerError('current host binding is unavailable or changed')

    @property
    def pending(self):
        return tuple(dict(request_id=key,**job[0].status) for key,job in self._jobs.items())

    async def reap_pending(self,*,timeout_seconds=0):
        closed=0
        for key,(lease,workspace) in tuple(self._jobs.items()):
            if await lease.wait_closed(timeout_seconds=timeout_seconds):
                self._cleanup(key); closed+=1
        return dict(closed=closed,remaining=len(self._jobs))

    async def __call__(self,*,task,model,messages,temperature,max_tokens,route_info=None):
        self._current()
        await self.reap_pending()
        if self._jobs or self.calls>=self.max_calls:
            raise NativeWorkerError('native caller has pending work or exhausted budget')
        self.calls+=1
        # Resolve afresh under the owning host scope; no route cache or default
        # model/fallback list is invented by Alive. Non-JSON capabilities reject.
        try: runtime=self.resolve_runtime(task=task,model=model)
        except Exception: raise NativeWorkerError('Hermes runtime resolution failed') from None
        request=dict(version=1,operation_id=self.operation_id,request_id=uuid4().hex,subject=self.subject,
            task=task,context_digest=request_digest(messages),messages=messages,runtime=runtime,
            identity=self.identity,temperature=temperature,max_tokens=max_tokens,budget_seconds=min(240,self.timeout-5))
        try: request=json.loads(canonical(validate_request(request)))
        except Exception: raise NativeWorkerError('Hermes runtime cannot cross the native worker boundary') from None
        self._current()
        workspace=tempfile.TemporaryDirectory(prefix='alive-native-worker-',dir=self.private_root)
        root=Path(workspace.name)
        child_root=root/'worker'; child_root.mkdir(mode=0o700)
        scratch=root/'temporary'; scratch.mkdir(mode=0o700)
        env={**self.environment,'HERMES_HOME':str(root/'bootstrap-profile'),
            'HERMES_ALIVE_SHARED_DIR':str(root/'bootstrap-runtime'),
            'TMPDIR':str(scratch),'TEMP':str(scratch),'TMP':str(scratch),'PYTHONDONTWRITEBYTECODE':'1'}
        try:
            lease=ManagedModelProcess(command=(str(self.interpreter),'-B',str(self.entrypoint),
                '--core',str(self.core),'--workspace',str(child_root)),cwd=root,environment=env,
                private_tmp_dir=root,timeout_seconds=self.timeout)
        except Exception:
            workspace.cleanup()
            raise
        self._jobs[request['request_id']]=(lease,workspace)
        try:
            result=await lease.run(canonical(request))
            if result.returncode!=0:
                error=NativeWorkerError('native worker did not complete')
                try:
                    failure=json.loads(result.stdout.decode('utf-8',errors='strict'))
                    label=failure.get('error_class')
                    if failure.get('status')=='failed' and isinstance(label,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',label):
                        error.worker_error_class=label
                        if label=='NativeCompletionError': error.worker_diagnostics=failure.get('diagnostics')
                except (ValueError,AttributeError,UnicodeError): pass
                raise error
            try: document=json.loads(result.stdout.decode('utf-8',errors='strict'))
            except (ValueError,UnicodeError): raise NativeWorkerError('native worker result is not a protocol document') from None
            text,evidence=validate_completion(document,request)
            self._current()
            if route_info is not None:
                route_info.update(provider=evidence.provider,model=evidence.response_model)
            return SimpleNamespace(model=evidence.response_model,choices=[SimpleNamespace(
                message=SimpleNamespace(content=text))],native_completion=evidence)
        finally:
            # On uncertain startup/exit, retain the lease and private workspace.
            # Cancellation is not permission to delete files or issue a retry.
            if await lease.wait_closed(timeout_seconds=0):
                self._cleanup(request['request_id'])
            else:
                # Task ownership keeps the workspace/caller alive even if its
                # original awaiter goes away. Do not rely on TemporaryDirectory
                # finalization while a worker might still be reading the files.
                lease._task.add_done_callback(lambda _task:self._cleanup(request['request_id']))
