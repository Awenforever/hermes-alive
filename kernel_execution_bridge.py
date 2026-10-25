"""Authenticated Core command -> existing native execution capabilities.

No legacy fallback, recipient discovery, provider router or physical queue.
Only the admitted command path may create grants; startup only restores them.
"""
from datetime import datetime,timezone
from uuid import uuid4
from importlib import import_module
import json

from .tool_receipt_bridge import _kernel_module
from .kernel_setup_bridge import setup_store,attach_configured_continuity


def kernel(name):
    """Dependencies of this exact embedded build, never another installed copy."""
    return import_module(_kernel_module('kernel_setup').__package__+'.'+name)


def configured_owner(binding,scope):
    store=setup_store(binding)
    configured=store.configuration()
    if configured is None:raise ValueError('confirmed setup required')
    saved=dict(configured.scope);current=scope.binding_document()
    saved.pop('session_id');current.pop('session_id')
    if saved!=current or scope.principal(store.protector)!=configured.subject:
        raise ValueError('current configured owner conversation required')
    return store,configured


def runtime_engine(binding):
    manifest=binding.home/'plugin-data/hermes-alive/runtime/install/manifest.json'
    if not manifest.is_file():return None
    return json.loads(manifest.read_text(encoding='utf-8')).get('engine')


def expression_language(configured):
    selected=configured.options.get('language')
    if selected is not None:return selected
    from agent.i18n import get_language
    return get_language().replace('_','-')


def _retired(binding):
    if binding.task is not None and not binding.task.done():
        raise ValueError('stop the previous host before enabling a new generation')
    if binding.native is not None and binding.native.pending:
        raise ValueError('previous host still owns uncertain child work')


def _unfinished(runtime,subject):
    inspector=kernel('autonomous_host_runtime').AutonomousHostRuntime(runtime,
        subject=subject,configuration_id='core-control-inspection',execute=True)
    for record in runtime.outbox.journal.iter_reverse(event_types=('autonomous.host.opened','autonomous.host.closed'),subject=subject):
        if record.event.correlation_id!=inspector.lane:continue
        inspector._validate(record.event)
        return record if record.event.event_type=='autonomous.host.opened' else None
    return None


def _complete_supersession(runtime,configured,active):
    """Finish an explicit enable transition; never infer a transport outcome."""
    target=active.get('supersedes_cycle_event_id')
    if not target:return
    record=runtime.outbox.journal.get(target)
    if record is None:raise ValueError('superseded cycle is unavailable')
    payload=record.event.payload
    Host=kernel('autonomous_host_runtime').AutonomousHostRuntime
    old=Host(runtime,subject=configured.subject,configuration_id=payload.get('configuration_id'),
             execute=payload.get('execute'))
    payload=old._validate(record.event)
    closed=runtime.outbox.journal.get(target+':closed')
    if closed is not None:
        old._validate(closed.event)
        return
    pending=_unfinished(runtime,configured.subject)
    if pending is None or pending.event.event_id!=target:
        raise ValueError('supersession no longer names the interrupted cycle')
    Cycle=kernel('autonomous_host_runtime').HostCycle
    result=kernel('autonomous_cycle_runtime').AutonomousCycleResult('paused',
        {'next_after_sequence':payload['reconciliation_cursor']})
    old.close_cycle(Cycle(target,payload['operation_id'],payload['reconciliation_cursor']),result)


def enable(binding,scope):
    """Caller has verified an actual admitted Core /alive enable command."""
    store,configured=configured_owner(binding,scope)
    if runtime_engine(binding)!='kernel':raise ValueError('explicit native kernel installation required')
    _retired(binding)
    if not configured.options['public_queries']:
        raise ValueError('configure approved public search topics before enabling')
    router=binding.session_router(scope.platform)
    attach_configured_continuity(binding,configured)
    Sensitivity=kernel('events').Sensitivity
    # Probe actual owning adapter and Core parsers before minting any grant.
    router.standard_send_parameters(scope,continuity=binding._continuity,clearance=Sensitivity.PRIVATE)
    runtime=kernel('autonomous_cycle_runtime').AutonomousCycleRuntime(store.journal,content_vault=store.vault)
    interrupted=_unfinished(runtime,configured.subject)
    host=runtime.preparation.authorizer.host
    from hermes_cli.version_info import get_version_info
    version=get_version_info()
    operation=uuid4().hex
    now=datetime.now(timezone.utc)
    snapshot=host.observe_snapshot(snapshot_id='core:'+operation,hermes_version=version.display_version,
        plugin_api_version=1,capabilities={'hermes.channel.send':{'interface':'core.adapter.send',
            'available':True,'public_api':True,'receipt_level':'request_accepted'}},observed_at=now)
    policies=kernel('autonomy_policy').AutonomyPolicyProjection(store.journal)
    previous=policies.current(configured.subject)
    changed=policies.append_update(subject=configured.subject,actor=configured.subject,
        expected_revision=previous.revision if previous else 0,enabled=True,
        context=kernel('deliberation').PolicyContext(can_interrupt=True),operation_id='core-enable:'+operation)
    policies.apply(changed)
    policy=policies.current(configured.subject)
    route_id='core-route:'+operation
    EventEnvelope=kernel('events').EventEnvelope
    authority=store.journal.append(EventEnvelope(event_type='conversation.inbound',
        source='hermes.command.alive.enable',actor=configured.subject,subject=configured.subject,
        sensitivity=Sensitivity.PRIVATE,causation_id=configured.event_id,
        payload={'authorizes_route_binding_id':route_id,'authorizes_host_snapshot_event_id':snapshot.event_id,
                 'authorizes_receipt_requirement':'request_accepted'}))
    ReceiptLevel=kernel('host_capabilities').ReceiptLevel
    host.bind_route(binding_id=route_id,subject=configured.subject,capability='hermes.channel.send',
        snapshot_event_id=snapshot.event_id,route=dict(scope.route),
        authority_event_id=authority.event.event_id,receipt_requirement=ReceiptLevel.REQUEST_ACCEPTED)
    delegation=kernel('action_delegation').ActionDelegationStore(store.journal).grant(
        subject=configured.subject,actor=configured.subject,policy_event_id=policy.event_id,
        route_binding_id=route_id,action_kinds=('share','ask'),maximum_sensitivity=Sensitivity.PRIVATE,
        expires_at=None,until_revoked=True,operation_id='core-enable:'+operation,allow_natural_expression=True)
    store.record_activation(configured,policy_event_id=policy.event_id,route_binding_id=route_id,
        delegation_event_id=delegation.event.event_id,expires_at=None,until_revoked=True,
        supersedes_cycle_event_id=interrupted.event.event_id if interrupted else None)
    # Do not overwrite setup/intent hints: journal remains authoritative.
    return assemble(binding)


def pause(binding,scope):
    store,configured=configured_owner(binding,scope)
    policies=kernel('autonomy_policy').AutonomyPolicyProjection(store.journal)
    previous=policies.current(configured.subject)
    if previous is not None and previous.enabled:
        policies.apply(policies.append_update(subject=configured.subject,actor=configured.subject,
            expected_revision=previous.revision,enabled=False,context=previous.context,
            operation_id='core-pause:'+uuid4().hex))
    if binding.arguments is not None:binding.arguments['stop'].set()
    return binding.runtime_status()


def assemble(binding):
    """Restore current signed authority; never renew or create it on startup."""
    if runtime_engine(binding)!='kernel':return None
    store=setup_store(binding)
    configured=store.configuration()
    active=store.activation()
    if configured is None or active is None:return None
    _retired(binding)
    Sensitivity=kernel('events').Sensitivity
    router=binding.session_router(configured.scope['platform'])
    def target():
        current=router.capture_target(session_key=configured.scope['session_key'],
            user_id=configured.scope['user_id'],platform=configured.scope['platform'])
        configured_owner(binding,current)
        return current
    target()
    attach_configured_continuity(binding,configured)
    def validate():
        binding._require_home()
        if binding.closed or store.configuration()!=configured or store.activation()!=active:
            raise ValueError('current Alive execution authority changed or expired')
    runtime=kernel('autonomous_cycle_runtime').AutonomousCycleRuntime(store.journal,content_vault=store.vault)
    _complete_supersession(runtime,configured,active)
    host=kernel('autonomous_host_runtime').AutonomousHostRuntime(runtime,subject=configured.subject,
        configuration_id=active['activation_event_id'],execute=True)
    discovery=kernel('configured_discovery_cycle').ConfiguredDiscoveryCycle(binding.context,
        kernel('discovery_opportunities').DiscoveryOpportunityIngestor(store.journal,content_vault=store.vault),
        subject=configured.subject,approved_queries=tuple(configured.options['public_queries']),
        follow_citations=configured.options['cited_reads'],record_reading_assessment=True,
        validate_consent=validate)
    class Preparation:
        supports_bounded_retry=discovery.supports_bounded_retry
        @property
        def pending(self):return discovery.pending
        async def reap_pending(self,*,timeout_seconds=0):
            return await discovery.reap_pending(timeout_seconds=timeout_seconds)
        async def bind_parameters(self,*,cycle,parameters,read_binding):
            validate()
            authorization={'authorization_operation_id':'core-auth:'+store.vault.digest_json(
                {'cycle':cycle.operation_id,'activation':active['activation_event_id']})[:40],
                'route_binding_id':active['route_binding_id'],'delegation_event_id':active['delegation_event_id']}
            return {**parameters,'authorization_parameters':authorization,'defer_until_eligible':True}
        async def observe(self,**kwargs):
            validate()
            return await discovery.observe(**kwargs)
        async def reason(self,observed,**kwargs):
            validate()
            return await discovery.reason(observed,**kwargs)
        def restore_parameters(self,**kwargs):
            validate()
            return discovery.restore_parameters(**kwargs)
        async def __call__(self,*,cycle,parameters,call,read_binding):
            # Direct embedding retains the same behavior; NativeCognitionHost
            # uses the exposed binder and phases to reconcile/wait FIRST.
            parameters=await self.bind_parameters(cycle=cycle,parameters=parameters,read_binding=read_binding)
            now=datetime.now(timezone.utc)
            if runtime.outbox.next_delegated_start(active['delegation_event_id'],subject=configured.subject,
                    policy_event_id=active['policy_event_id'],route_binding_id=active['route_binding_id'],now=now)>now:
                return parameters
            return await discovery(cycle=cycle,parameters=parameters,call=call,read_binding=read_binding)
    context_reads=(kernel('core_context_read').CoreContextRead(binding.context)
        if configured.options.get('use_hermes_user_profile') is True else None)
    native=kernel('core_shadow_assembly').native_for_host(binding.context,host,home=binding.home,
        preparation=Preparation(),validate_consent=validate,context_reads=context_reads)
    def parameters():
        if not runtime.reconciliation._owner_policy(configured.subject).enabled:
            # A cross-process operator pause must enter the existing paused
            # cycle, without route resolution, public tools or model invocation.
            return dict(expression_parameters={},resolve_binding=lambda _:None,
                channel_execution='standard',worker_id='core-native',
                authorization_parameters={},send_parameters={})
        validate()
        return dict(expression_parameters={'requested_model':configured.options['model'],'grounding':True,
            'language':expression_language(configured),
            'authority':kernel('deliberation').ActionAuthority.USER_DELEGATED,
            'recipient_meaning':True,'require_independent_grounding':False,
            'model_timeout_seconds':kernel('model_timeouts').DEFAULT_STAGE_SECONDS},
            resolve_binding=lambda _:None,channel_execution='standard',worker_id='core-native',
            authorization_parameters={},send_parameters=router.standard_send_parameters(target(),
                continuity=binding._continuity,clearance=Sensitivity.PRIVATE),
            interpret_feedback=False,reconsider_after_seconds=600)
    return native,dict(build_parameters=parameters,continuous=True,max_cycles=None,interval_seconds=600)


def attach(binding,assembled):
    if assembled is None:raise ValueError('current execution authority unavailable')
    _retired(binding)
    native,arguments=assembled
    # Explicit trusted replacement of a terminal generation, never an active one.
    binding.native=None;binding.arguments=None;binding.task=None;binding.started=False
    binding.attach(native,**arguments)
