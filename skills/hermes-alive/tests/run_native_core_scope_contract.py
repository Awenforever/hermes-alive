"""Scope classification/currentness only; no Core, credentials or HTTP required."""
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.native_core_acquisition import CoreScopedModelAcquirer
from alive_kernel.native_host_caller import HostModelBinding
from alive_kernel.native_worker_protocol import NativeWorkerError

with tempfile.TemporaryDirectory(prefix='alive-scope-contract-') as folder:
    launch=Path(folder)/'launch';launch.mkdir()
    routed=Path(folder)/'routed';routed.mkdir()
    state=dict(scope={'OWNER_KEY':'synthetic-key'},stamp=None,override=launch,effective=launch,process=launch)
    constants=ModuleType('hermes_constants')
    constants.get_hermes_home=lambda:state['effective']
    constants.get_hermes_home_override=lambda:state['override']
    constants.get_routing_process_hermes_home=lambda:state['process']
    secrets=ModuleType('agent.secret_scope')
    secrets.current_secret_scope=lambda:state['scope']
    secrets.current_secret_scope_home=lambda:state['stamp']
    def acquire(home):
        return CoreScopedModelAcquirer(profile_home=home,
            read_binding=lambda:HostModelBinding('user:synthetic','profile:synthetic','operation:test','revision:1'),
            read_configuration=lambda:{'model':{'default':'synthetic','provider':'custom:owner'}},
            read_credential_names=lambda **_:('OWNER_KEY',))(task='synthetic',model=None)
    def reject(home):
        try:acquire(home)
        except NativeWorkerError:return
        raise AssertionError('unavailable or foreign scope admitted')
    with patch.dict(sys.modules,{'hermes_constants':constants,'agent.secret_scope':secrets}):
        cap=acquire(launch)
        assert cap.is_current(cap.binding)
        assert cap.read_secret(cap.binding,'OWNER_KEY')=='synthetic-key'
        state['override']=None
        assert not cap.is_current(cap.binding)
        reject(launch)
        state.update(stamp=launch,override=None)
        assert acquire(launch).is_current(cap.binding)
        state.update(stamp=routed,override=routed,effective=routed)
        assert acquire(routed).is_current(cap.binding)
        reject(launch)
        state['stamp']=None
        reject(routed)
        state.update(effective=launch,override=launch,stamp=routed)
        reject(launch)
        state.update(stamp=None,scope=None)
        reject(launch)
        state['scope']={'OWNER_KEY':'synthetic-key'}
        cap=acquire(launch)
        state['scope']={'OWNER_KEY':'synthetic-key'}
        assert not cap.is_current(cap.binding)
        try:cap.read_secret(cap.binding,'OWNER_KEY')
        except NativeWorkerError:pass
        else:raise AssertionError('expired mapping remained readable')
print('HERMES_ALIVE_NATIVE_CORE_SCOPE_CONTRACT_OK')
