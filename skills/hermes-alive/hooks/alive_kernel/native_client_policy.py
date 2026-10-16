"""Bound model-only client policy for a private worker, never a whole profile.

The host projects resolved capabilities. Core still constructs the clients and
applies endpoint-specific headers/TLS. Secret-bearing mappings must not be logged.
"""
from .native_worker_protocol import NativeWorkerError, canonical


ROUTING_FIELDS = {'providers_allowed', 'providers_ignored', 'providers_order',
    'provider_sort', 'provider_require_parameters', 'provider_data_collection',
    'openrouter_min_coding_score', 'capabilities'}


def validate_client_policy(runtime):
    for field in ('providers_allowed', 'providers_ignored', 'providers_order'):
        value = runtime.get(field)
        if value is not None and (not isinstance(value, list) or len(value) > 64
                or any(not isinstance(item, str) or not item.strip() for item in value)):
            raise NativeWorkerError('invalid provider routing policy')
    for field in ('provider_sort', 'provider_data_collection'):
        value = runtime.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise NativeWorkerError('invalid provider routing policy')
    if 'provider_require_parameters' in runtime and type(runtime['provider_require_parameters']) is not bool:
        raise NativeWorkerError('invalid provider parameter policy')
    score = runtime.get('openrouter_min_coding_score')
    if score is not None and (type(score) not in (int, float) or not 0 <= score <= 1):
        raise NativeWorkerError('invalid provider quality policy')
    capabilities = runtime.get('capabilities')
    if capabilities is not None and (not isinstance(capabilities, dict)
            or any(not isinstance(k, str) or type(v) is not bool for k, v in capabilities.items())):
        raise NativeWorkerError('invalid model capabilities')
    policy = runtime.get('client_policy', {})
    if not isinstance(policy, dict) or set(policy) - {'default_headers', 'routes'}:
        raise NativeWorkerError('unadmitted private client configuration')
    if policy and (runtime.get('api_mode')!='chat_completions'
            or any(entry.get('api_mode','chat_completions')!='chat_completions' for entry in fallback_entries(runtime))):
        raise NativeWorkerError('client policy transport has not been qualified')
    _headers(policy.get('default_headers', {}))
    routes = policy.get('routes', [])
    if not isinstance(routes, list) or len(routes) > 9:
        raise NativeWorkerError('invalid endpoint client policies')
    fallback = fallback_entries(runtime)
    endpoints = {runtime['base_url'], *(entry.get('base_url') for entry in fallback)}
    seen = set()
    for route in routes:
        if (not isinstance(route, dict) or set(route) - {'base_url', 'extra_headers', 'ssl_verify'}
                or not isinstance(route.get('base_url'), str) or route['base_url'] not in endpoints
                or route['base_url'] in seen):
            raise NativeWorkerError('client policy is not bound to an admitted endpoint')
        seen.add(route['base_url'])
        _headers(route.get('extra_headers', {}))
        if 'ssl_verify' in route and type(route['ssl_verify']) is not bool:
            raise NativeWorkerError('invalid endpoint TLS policy')
        if route.get('extra_headers') and any(entry.get('provider')=='custom'
                and entry.get('base_url')==route['base_url'] for entry in fallback):
            # Actual Core's anonymous-custom fallback does not apply the named
            # endpoint header block. Refuse before any HTTP, never drop policy.
            raise NativeWorkerError('anonymous custom fallback headers need qualified host binding')
    canonical(policy)  # Reject opaque objects/non-finite values before process creation.


def fallback_entries(runtime):
    value = runtime.get('fallback_model') or []
    return [value] if isinstance(value, dict) else value


def _headers(headers):
    if (not isinstance(headers, dict) or len(headers) > 64
            or any(not isinstance(k, str) or not k or not k.isascii()
                or any(ch.isspace() or ord(ch) < 33 or ord(ch) > 126 for ch in k)
                or ':' in k or not isinstance(v, str) or '\r' in v or '\n' in v
                for k, v in headers.items())):
        raise NativeWorkerError('invalid private request headers')


def private_client_config(runtime):
    """Return a detached model-only Core projection; lifecycle settings stay local."""
    import json
    validate_client_policy(runtime)
    policy = json.loads(canonical(runtime.get('client_policy', {})))
    fallback = fallback_entries(runtime)
    bindings = [runtime, *fallback]
    entries = []
    for index, entry in enumerate(policy.get('routes', [])):
        names = {binding['provider'].removeprefix('custom:') for binding in bindings
            if binding.get('base_url')==entry['base_url']
            and binding.get('provider','').startswith('custom:')}
        for name in sorted(names or {'alive-route-'+str(index)}):
            entries.append(dict(name=name, **entry))
    return dict(model=dict(default=runtime['model'], provider=runtime['provider'],
                          streaming=False, default_headers=policy.get('default_headers', {})),
                custom_providers=entries)
