"""Private policy boundary: no Core import, model call or channel IO."""
import copy
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.native_client_policy import private_client_config, validate_client_policy
from alive_kernel.native_worker_protocol import NativeWorkerError

route=dict(model='synthetic',provider='custom',api_mode='chat_completions',base_url='https://primary.invalid/v1',
    fallback_model=[dict(model='backup',provider='custom:owner-backup',base_url='https://backup.invalid/v1')],
    providers_allowed=['approved'],providers_ignored=['denied'],providers_order=[],
    provider_require_parameters=True,provider_data_collection='deny',
    openrouter_min_coding_score=.8,capabilities={'vision':False},
    client_policy=dict(default_headers={'X-Owner':'synthetic'},routes=[
        dict(base_url='https://primary.invalid/v1',extra_headers={'X-Route':'primary'},ssl_verify=True),
        dict(base_url='https://backup.invalid/v1',extra_headers={'X-Route':'backup'},ssl_verify=True)]))
original=copy.deepcopy(route)
config=private_client_config(route)
assert route==original
assert set(config)=={'model','custom_providers'}
assert config['custom_providers'][1]['name']=='owner-backup'
config['model']['default_headers']['X-Owner']='changed'
assert route==original
for patch in (
        {'providers_allowed':'approved'}, {'provider_require_parameters':'false'},
        {'api_mode':'anthropic_messages'},
        {'fallback_model':[dict(model='backup',provider='custom',base_url='https://backup.invalid/v1')]},
        {'provider_data_collection':False}, {'capabilities':{'vision':'false'}},
        {'openrouter_min_coding_score':float('nan')},
        {'client_policy':{'plugins':{'enabled':['untrusted']}}},
        {'client_policy':{'default_headers':{'X-Injected':'value\r\nAuthorization: other'}}},
        {'client_policy':{'routes':[{'base_url':'https://unbound.invalid','ssl_verify':False}]}},
        {'client_policy':{'routes':[{'base_url':route['base_url'],'ssl_ca_cert':'/private/file'}]}},
        {'client_policy':{'routes':[{'base_url':route['base_url'],'ssl_verify':'false'}]}},
        {'client_policy':{'routes':[route['client_policy']['routes'][0]]*2}}):
    try: validate_client_policy({**route,**patch})
    except NativeWorkerError: pass
    else: raise AssertionError('unadmitted client policy accepted')
print('HERMES_ALIVE_NATIVE_CLIENT_POLICY_OK')
