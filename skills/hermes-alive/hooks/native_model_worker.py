"""Private native API worker. Execute as a script, never import into a live gateway."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys


class DiscardDiagnostics(io.TextIOBase):
    def write(self,text): return len(text)
    def flush(self): pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args()
    output=sys.stdout
    request=None
    diagnostics=None
    sink=DiscardDiagnostics()
    os.umask(0o077)
    with contextlib.redirect_stdout(sink),contextlib.redirect_stderr(sink):
        try:
            workspace=args.workspace.resolve(strict=True)
            if not workspace.is_dir() or any(workspace.iterdir()): raise ValueError('worker workspace must be empty')
            profile=workspace/'profile'; profile.mkdir(mode=0o700)
            scratch=workspace/'temporary'; scratch.mkdir(mode=0o700)
            home=workspace/'home'; home.mkdir(mode=0o700)
            os.environ.update(HERMES_HOME=str(profile),HOME=str(home),TMPDIR=str(scratch),TEMP=str(scratch),TMP=str(scratch),
                XDG_CACHE_HOME=str(home/'cache'),XDG_CONFIG_HOME=str(home/'config'),
                HERMES_ALIVE_SHARED_DIR=str(profile/'plugin-data'/'hermes-alive'/'runtime'),
                HERMES_BUNDLED_PLUGINS=str(profile/'empty-bundled'),PYTHONDONTWRITEBYTECODE='1')
            os.chdir(workspace)
            def no_descendants(event,values):
                if event in ('subprocess.Popen','os.fork','os.forkpty','os.posix_spawn','os.exec'):
                    raise RuntimeError('native API worker does not admit descendants')
            sys.addaudithook(no_descendants)
            hooks=Path(__file__).resolve().parent
            sys.path[:0]=[str(args.core.resolve(strict=True)),str(hooks)]
            from alive_kernel.native_worker_protocol import validate_request,canonical,completion_document
            from alive_kernel.native_completion import NativeCompletionHub
            from types import SimpleNamespace
            raw=sys.stdin.buffer.read(131073)
            if len(raw)>131072: raise ValueError('worker input exceeds bound')
            request=validate_request(json.loads(raw))
            # The route is a trusted, already-resolved Hermes capability. No
            # provider/model/credential discovery is reimplemented by Alive.
            route=dict(request['runtime'])
            from alive_kernel.native_client_policy import private_client_config
            config=dict(**private_client_config(route),
                plugins=dict(enabled=['hermes-alive-native-worker']),compression=dict(enabled=False),
                memory=dict(memory_enabled=False,user_profile_enabled=False))
            route.pop('client_policy',None)
            (profile/'config.yaml').write_bytes(canonical(config))
            if request['identity']: (profile/'SOUL.md').write_text(request['identity'],encoding='utf-8')
            shutil.copytree(hooks/'native_worker_observer',profile/'plugins'/'hermes-alive-native-worker')
            hub=NativeCompletionHub()
            sys.modules['_alive_native_worker_bus']=SimpleNamespace(hub=hub)
            from hermes_cli.plugins import discover_plugins
            discover_plugins()
            scope=hub.open(subject=request['subject'])
            from run_agent import AIAgent
            overrides={**(route.pop('request_overrides',None) or {}),'temperature':request['temperature']}
            agent=AIAgent(**route,request_overrides=overrides,enabled_toolsets=[],disabled_toolsets=[],
                max_iterations=1,run_budget_seconds=request['budget_seconds'],max_tokens=request['max_tokens'],
                quiet_mode=True,save_trajectories=False,skip_context_files=True,load_soul_identity=True,
                skip_memory=True,skip_background_review=True,session_id=scope.session_id,cwd=str(workspace),
                ephemeral_system_prompt=request['messages'][0]['content'])
            try:
                if agent.tools or agent._memory_store is not None or agent._memory_manager is not None:
                    raise ValueError('worker acquired unadmitted capability')
                result=agent.run_conversation(request['messages'][1]['content'],conversation_history=[],task_id=scope.task_id)
                diagnostics=dict(api_calls=result.get('api_calls'),observations=[dict(error=s.error,
                    requests=len(s.requests),states=[a['state'] for r in s.requests.values()
                        for a in r['attempts'].values()]) for s in hub._scopes.values()])
                evidence=hub.finish(scope,result)
                document=completion_document(request,evidence,result['final_response'])
            finally:
                agent.close(); hub.close()
            exitcode=0
        except BaseException as error:
            document=dict(version=1,status='failed',error_class=type(error).__name__,authority_granted=False)
            if type(error).__module__=='alive_kernel.native_completion': document['diagnostics']=diagnostics
            exitcode=2
    # Exactly one protocol document. Never print a traceback, provider exception,
    # key, raw SDK debug output or a partially generated response on failure.
    encoded=json.dumps(document,ensure_ascii=False,separators=(',',':'))
    if len(encoded.encode('utf-8'))>262144:
        encoded='{"version":1,"status":"failed","error_class":"OutputBound","authority_granted":false}'
        exitcode=2
    output.write(encoded); output.flush()
    return exitcode


if __name__=='__main__': raise SystemExit(main())
