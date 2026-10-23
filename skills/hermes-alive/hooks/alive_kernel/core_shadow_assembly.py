"""Opt-in persisted configuration -> current Core-owned non-sending host."""
import hashlib
from pathlib import Path
import sys

from .native_worker_protocol import identifier,canonical
from .native_cognition_host import NativeCognitionHost
from .native_core_scope import core_profile_cycle_scope
from .core_plugin_model_call import CorePluginModelCaller
from .core_context_read import CoreContextRead
from .event_store import ExperienceJournal
from .content_vault import ContentVault
from .autonomy_policy import AutonomyPolicyProjection
from .deliberation import PolicyContext
from .autonomous_cycle_runtime import AutonomousCycleRuntime
from .autonomous_host_runtime import AutonomousHostRuntime
from .model_timeouts import DEFAULT_REQUEST_SECONDS,DEFAULT_STAGE_SECONDS


def subject_for_user(home,user_id):
    from .privacy import LocalIdentityProtector
    identity=LocalIdentityProtector(Path(home)/'plugin-data/hermes-alive/runtime/kernel/identity.key')
    subject=identity.pseudonym('user',user_id)
    if subject is None:raise ValueError('current authorized Hermes user identity required')
    return subject


def validate_settings(settings):
    if not isinstance(settings,dict) or settings.get('enabled') is not True:
        raise ValueError('explicit enabled shadow settings required')
    if (settings.get('consent')!='model_calls_no_delivery'
            or set(settings)-{'enabled','consent','subject','max_cycles','interval_seconds','model','public_discovery'}):
        raise ValueError('explicit shadow model consent and supported settings required')
    subject=identifier(settings.get('subject'))
    max_cycles=settings.get('max_cycles',1)
    interval=settings.get('interval_seconds',600)
    model=settings.get('model')
    if (type(max_cycles) is not int or not 1<=max_cycles<=1000
            or type(interval) not in (int,float) or not 0<=interval<=86400
            or model is not None and (not isinstance(model,str) or not model.strip() or len(model)>512)):
        raise ValueError('bounded shadow schedule and optional Core model alias required')
    if 'public_discovery' in settings:
        public_discovery_settings(settings['public_discovery'])
    return subject,max_cycles,interval,model


def public_discovery_settings(value):
    if (not isinstance(value,dict) or not {'consent','queries'}<=set(value)
            or set(value)-{'consent','queries','follow_citations'}
            or ('follow_citations' in value and value['follow_citations'] is not True)
            or value['consent']!='approved_public_queries_no_delivery'
            or not isinstance(value['queries'],list) or not 1<=len(value['queries'])<=3
            or any(not isinstance(q,str) or not q.strip() or len(q)>128 for q in value['queries'])
            or len(set(value['queries']))!=len(value['queries'])):
        raise ValueError('separate explicit consent and bounded public search queries required')
    normalized=dict(consent=value['consent'],queries=list(value['queries']))
    if 'follow_citations' in value:normalized['follow_citations']=True
    return normalized


def normalize_settings(settings):
    subject,max_cycles,interval,model=validate_settings(settings)
    normalized=dict(enabled=True,consent='model_calls_no_delivery',subject=subject,
        max_cycles=max_cycles,interval_seconds=float(interval),model=model)
    if 'public_discovery' in settings:
        normalized['public_discovery']=public_discovery_settings(settings['public_discovery'])
    return normalized


def assemble(context):
    settings=context.get_config('kernel_shadow',{})
    if not isinstance(settings,dict) or settings.get('enabled') is not True:
        return None
    subject,max_cycles,interval,model=validate_settings(settings)
    settings=normalize_settings(settings)
    from hermes_constants import get_hermes_home
    from hermes_cli.config import load_config_readonly
    import hermes_cli
    home=Path(get_hermes_home()).resolve()
    if home!=Path(context._manager.scope_key).resolve():
        raise ValueError('shadow setup belongs to another Core profile')
    task_state={}
    consent_snapshot=canonical(settings)
    def validate_consent():
        if canonical(normalize_settings(context.get_config('kernel_shadow',{})))!=consent_snapshot:
            raise ValueError('configured shadow consent changed; new host assembly required')
    def refresh_task():
        validate_consent()
        from hermes_cli.fallback_config import get_fallback_chain
        # Forward Core's normalized current chain into its own task slot. Do not
        # persist a copied chain in plugin settings or implement retries here.
        # Background work must allow ordinary ~100s reasoning responses.
        # Core auxiliary user configuration and candidate timeouts still win.
        defaults={'provider':'auto','model':'','timeout':DEFAULT_REQUEST_SECONDS,
            'fallback_chain':get_fallback_chain(load_config_readonly())}
        revision=canonical(defaults)
        if task_state.get('revision')!=revision:
            context.register_auxiliary_task('hermes_alive_kernel',display_name='Hermes Alive kernel',
                description='Alive model work; inherits Hermes routing/auth and configured fallback.',defaults=defaults)
            task_state['revision']=revision
    refresh_task()
    root=home/'plugin-data/hermes-alive/runtime/kernel'
    journal=ExperienceJournal(root/'experience.sqlite3')
    vault=ContentVault(root/'content-vault',backup_root=root/'content-backups')
    policies=AutonomyPolicyProjection(journal)
    if policies.current(subject) is None:
        policies.apply(policies.append_update(subject=subject,actor=subject,expected_revision=0,
            enabled=True,context=PolicyContext(can_interrupt=True),
            operation_id='configured-shadow-consent:'+hashlib.sha256(subject.encode()).hexdigest()[:24]))
    # Never re-enable a journal policy paused by the owner on a later restart.
    identity=hashlib.sha256(str(home).encode()).hexdigest()[:24]
    configuration='core-shadow:'+hashlib.sha256(canonical(settings)).hexdigest()[:24]
    host=AutonomousHostRuntime(AutonomousCycleRuntime(journal,content_vault=vault),
        subject=subject,configuration_id=configuration,execute=False)
    preparation=None
    if 'public_discovery' in settings:
        from .configured_discovery_cycle import ConfiguredDiscoveryCycle
        from .discovery_opportunities import DiscoveryOpportunityIngestor
        preparation=ConfiguredDiscoveryCycle(context,
            DiscoveryOpportunityIngestor(journal,content_vault=vault),subject=subject,
            approved_queries=tuple(settings['public_discovery']['queries']),
            follow_citations=settings['public_discovery'].get('follow_citations',False),
            validate_consent=validate_consent)
    native=NativeCognitionHost(host,profile_id='profile:'+identity,profile_home=home,
        read_configuration=load_config_readonly,read_credential_names=lambda **_:(),
        interpreter=sys.executable,core=Path(hermes_cli.__file__).resolve().parent.parent,
        private_root=root,environment={},resolve_domain=lambda *labels:'unverified-family',
        profile_scope=lambda:core_profile_cycle_scope(home),
        preparation=preparation,
        context_reads=CoreContextRead(context),
        caller_factory=lambda *,cycle,read_binding:CorePluginModelCaller(context,read_binding=read_binding,refresh_task=refresh_task))
    parameters=dict(expression_parameters={'requested_model':model,'grounding':True,
        'recipient_meaning':True,'require_independent_grounding':False,
        'model_timeout_seconds':DEFAULT_STAGE_SECONDS},resolve_binding=lambda _:None,
        interpret_feedback=True,reconsider_after_seconds=600)
    return native,dict(build_parameters=lambda:parameters,max_cycles=max_cycles,interval_seconds=interval)
