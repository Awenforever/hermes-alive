"""Explicit model-only host projection, resolved by Core inside a private worker.

This is not profile discovery: the trusted owner supplies config and only the
credentials permitted for this operation. Neither mapping is diagnostic output.
"""
import json
import re

from .native_worker_protocol import NativeWorkerError, canonical, validate_text_overrides


CONFIG_FIELDS={'model','model_aliases','providers','custom_providers','fallback_model',
    'fallback_providers','provider_routing','agent','openrouter'}
AGENT_FIELDS={'reasoning_effort','reasoning_overrides','service_tier'}


def validate_host_snapshot(snapshot):
    if (not isinstance(snapshot,dict) or set(snapshot)-{'config','secrets','selected_model','unauthenticated_endpoints'}
            or not {'config','secrets','selected_model'}<=set(snapshot)
            or not isinstance(snapshot['config'],dict) or set(snapshot['config'])-CONFIG_FIELDS
            or not isinstance(snapshot['config'].get('model'),dict)
            or not isinstance(snapshot['secrets'],dict) or len(snapshot['secrets'])>128
            or any(not isinstance(k,str) or not re.fullmatch(r'[A-Z_][A-Z0-9_]{0,127}',k)
                or not isinstance(v,str) or len(v)>16000 for k,v in snapshot['secrets'].items())
            or snapshot['selected_model'] is not None and (not isinstance(snapshot['selected_model'],str)
                or not snapshot['selected_model'].strip() or len(snapshot['selected_model'])>512)):
        raise NativeWorkerError('invalid model-only host snapshot')
    config=snapshot['config']
    keyless=snapshot.get('unauthenticated_endpoints',[])
    if (not isinstance(keyless,list) or len(keyless)>9
            or any(not isinstance(endpoint,str) or not endpoint.strip() for endpoint in keyless)):
        raise NativeWorkerError('invalid explicit unauthenticated endpoint capability')
    if not isinstance(config.get('agent',{}),dict) or set(config.get('agent',{}))-AGENT_FIELDS:
        raise NativeWorkerError('host agent settings exceed model capability scope')
    # No callable/pool/client/path handles cross this boundary. Top-level Core
    # plugins, tools, memory, auth stores and unrelated services are never copied.
    if len(canonical(snapshot))>96000:
        raise NativeWorkerError('host snapshot exceeds private model boundary')
    _validate_model_overrides(config)
    return snapshot


def _validate_model_overrides(value):
    # Core may read these again during fallback/client rebuild, not just initial
    # resolution. Check the entire projected model graph before the first HTTP.
    if isinstance(value,dict):
        if 'request_overrides' in value: validate_text_overrides(value['request_overrides'])
        if 'extra_body' in value: validate_text_overrides({'extra_body':value['extra_body']})
        for child in value.values(): _validate_model_overrides(child)
    elif isinstance(value,list):
        for child in value: _validate_model_overrides(child)


def private_snapshot_config(snapshot):
    validate_host_snapshot(snapshot)
    config=json.loads(canonical(snapshot['config']))
    config['model']['streaming']=False
    return config


def resolve_host_snapshot(snapshot):
    """Call only in an owned private process with the projected config installed.

    The caller keeps Core's secret/multiplex scope alive through AIAgent.close,
    because fallbacks and client rebuilds also use it, not only this resolver.
    """
    validate_host_snapshot(snapshot)
    from hermes_cli.runtime_provider import resolve_runtime_provider, resolve_runtime_with_fallback
    from hermes_cli.model_switch import resolve_startup_model_route
    from hermes_cli.fallback_config import get_fallback_chain, resolve_entry_api_key, effective_runtime_provider
    from hermes_cli.config import get_custom_provider_extra_headers, get_custom_provider_tls_settings
    from hermes_constants import resolve_reasoning_config
    from hermes_cli.cli_config_load import _parse_service_tier_config
    config=snapshot['config']
    model_cfg=config['model']
    selected=snapshot['selected_model'] or model_cfg.get('default')
    requested=model_cfg.get('provider','auto')
    if not isinstance(selected,str) or not selected.strip():
        raise NativeWorkerError('host default model unavailable')
    alias=resolve_startup_model_route(selected,current_provider=requested,
        user_providers=config.get('providers'),custom_providers=config.get('custom_providers'))
    explicit={}
    if alias is not None:
        selected,requested=alias.model,alias.provider
        explicit=dict(explicit_base_url=alias.base_url or None,explicit_api_key=alias.api_key or None)
    runtime,used=resolve_runtime_with_fallback(config,requested=requested,target_model=selected,**explicit)
    if used is not None:
        selected,requested=used['model'],used['provider']
    keyless=snapshot.get('unauthenticated_endpoints',[])
    route=_route(runtime,requested,selected,effective_runtime_provider,keyless)
    chain=get_fallback_chain(config)
    if used is not None:
        chain=chain[chain.index(used)+1:]
    fallbacks=[]
    for entry in chain:
        resolved=resolve_runtime_provider(requested=entry['provider'],target_model=entry['model'],
            explicit_base_url=entry.get('base_url'),explicit_api_key=resolve_entry_api_key(entry))
        capability=_route(resolved,entry['provider'],entry['model'],effective_runtime_provider,keyless)
        fallbacks.append({k:capability[k] for k in ('provider','model','api_key','base_url','api_mode')})
    route['fallback_model']=fallbacks
    routing=config.get('provider_routing') or {}
    fields={'only':'providers_allowed','ignore':'providers_ignored','order':'providers_order',
        'sort':'provider_sort','require_parameters':'provider_require_parameters','data_collection':'provider_data_collection'}
    route.update({target:routing[key] for key,target in fields.items() if key in routing})
    if 'min_coding_score' in (config.get('openrouter') or {}):
        route['openrouter_min_coding_score']=config['openrouter']['min_coding_score']
    route['reasoning_config']=resolve_reasoning_config(config,route['model'])
    route['service_tier']=_parse_service_tier_config(config.get('agent',{}).get('service_tier',''))
    policies=[]
    for capability in [route,*fallbacks]:
        endpoint=capability['base_url']
        if endpoint in {p['base_url'] for p in policies}: continue
        headers=get_custom_provider_extra_headers(endpoint,config=config)
        tls=get_custom_provider_tls_settings(endpoint,config=config)
        if tls.get('ssl_ca_cert'):
            raise NativeWorkerError('host CA file requires explicit worker materialization')
        if headers or tls:
            policies.append(dict(base_url=endpoint,extra_headers=headers,**tls))
    policy=dict(default_headers=model_cfg.get('default_headers',{}),routes=policies)
    if policy['default_headers'] or policies: route['client_policy']=policy
    from .native_client_policy import validate_client_policy
    validate_client_policy(route)
    return route


def _route(runtime,requested,model,effective,keyless):
    if runtime.get('command') or runtime.get('args'):
        raise NativeWorkerError('native host process capability needs qualification')
    if not isinstance(runtime.get('api_key'),str) or not runtime['api_key']:
        raise NativeWorkerError('native host needs an admitted API credential')
    # Core pads missing custom credentials with this SDK placeholder, including
    # authenticated remote routes. Missing authorization is not a no-auth grant.
    if runtime['api_key']=='no-key-required' and runtime.get('base_url') not in keyless:
        raise NativeWorkerError('host has not granted an unauthenticated endpoint')
    route={k:runtime[k] for k in ('api_key','base_url','api_mode','capabilities','request_overrides') if k in runtime}
    route.update(model=model,
        provider=effective({'provider':requested},runtime),requested_provider=requested)
    if runtime.get('credential_pool') is not None:
        # Created by Core inside this private process/profile, never supplied by
        # the parent or serialized across the protocol. Keep its native lifecycle.
        route['credential_pool']=runtime['credential_pool']
    if runtime.get('extra_body'):
        overrides=route.get('request_overrides') or {}
        route['request_overrides']={**overrides,'extra_body':{
            **runtime['extra_body'],**overrides.get('extra_body',{})}}
    validate_text_overrides(route.get('request_overrides'))
    return route
