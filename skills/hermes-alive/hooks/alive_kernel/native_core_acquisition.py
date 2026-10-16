"""Capture an explicitly bound Core model scope without profile/env discovery.

The embedding host supplies its current lifecycle binding, loaded configuration
and permitted model credential names. Core remains the resolver in the child.
This adapter never installs a scope or opens a profile/auth file by itself.
"""
import hashlib
import json
from pathlib import Path
import re

from .native_host_caller import HostModelBinding, HostModelCapability
from .native_host_snapshot import CONFIG_FIELDS, AGENT_FIELDS, validate_host_snapshot
from .native_worker_protocol import NativeWorkerError, canonical


class CoreScopedModelAcquirer:
    def __init__(self, *, profile_home, read_binding, read_configuration,
                 read_credential_names, identity='', unauthenticated_endpoints=()):
        if not all(callable(fn) for fn in (read_binding, read_configuration, read_credential_names)):
            raise NativeWorkerError('explicit current host readers required')
        self.profile_home=Path(profile_home).resolve(strict=True)
        self.read_binding=read_binding
        self.read_configuration=read_configuration
        self.read_credential_names=read_credential_names
        self.identity=identity
        self.unauthenticated_endpoints=unauthenticated_endpoints

    def _scope(self):
        from hermes_constants import get_hermes_home
        from agent.secret_scope import current_secret_scope, current_secret_scope_home
        # A launch-profile environment alone is not a credential capability.
        scope=current_secret_scope()
        home=current_secret_scope_home()
        if (scope is None or home is None
                or Path(home).resolve()!=self.profile_home
                or Path(get_hermes_home()).resolve()!=self.profile_home):
            raise NativeWorkerError('current Core profile scope is unavailable or foreign')
        return scope

    def _configuration(self):
        value=self.read_configuration()
        if not isinstance(value,dict):
            raise NativeWorkerError('loaded host configuration required')
        result={key:value[key] for key in CONFIG_FIELDS if key in value and key!='agent'}
        if 'agent' in value:
            if not isinstance(value['agent'],dict):
                raise NativeWorkerError('invalid host agent model settings')
            result['agent']={key:val for key,val in value['agent'].items() if key in AGENT_FIELDS}
        return json.loads(canonical(result))

    @staticmethod
    def _credentials(scope,names):
        # Only explicitly permitted names are read, never enumerate the scope.
        values={}
        for name in names:
            value=scope.get(name)
            if value is not None:
                if not isinstance(value,str) or len(value)>16000:
                    raise NativeWorkerError('nontransferable host model credential')
                values[name]=value
        return values

    def __call__(self, *, task, model):
        try:
            binding=self.read_binding()
            if not isinstance(binding,HostModelBinding):
                raise NativeWorkerError('current host lifecycle binding required')
            scope=self._scope()
            configuration=self._configuration()
            names=self.read_credential_names(task=task,model=model,configuration=configuration)
            if (not isinstance(names,tuple) or len(names)>128
                    or any(not isinstance(name,str) or not re.fullmatch(r'[A-Z_][A-Z0-9_]{0,127}',name) for name in names)
                    or len(set(names))!=len(names)):
                raise NativeWorkerError('host model credential grant invalid')
            validate_host_snapshot(dict(config=configuration,secrets={name:'' for name in names},
                selected_model=model,unauthenticated_endpoints=list(self.unauthenticated_endpoints)))
            def fingerprint():
                return hashlib.sha256(canonical(dict(config=self._configuration(),
                    secrets=self._credentials(scope,names)))).digest()
            revision=fingerprint()
            def current(candidate):
                try:
                    return (candidate==binding and self.read_binding()==binding
                        and self._scope() is scope
                        and self.read_credential_names(task=task,model=model,
                            configuration=self._configuration())==names
                        and fingerprint()==revision)
                except Exception:
                    return False
            if not current(binding):
                raise NativeWorkerError('Core model scope changed during acquisition')
            def read_secret(candidate,name):
                if name not in names or not current(candidate):
                    raise NativeWorkerError('model credential read is no longer authorized')
                return scope.get(name)
            return HostModelCapability(binding=binding,configuration=configuration,
                credential_names=names,read_secret=read_secret,is_current=current,
                identity=self.identity,unauthenticated_endpoints=self.unauthenticated_endpoints)
        except NativeWorkerError:
            raise
        except Exception:
            raise NativeWorkerError('current Core model acquisition failed') from None
