"""Opt-in current Core USER profile as advice, never an explicit user memory.

Use Core's configured store and threat-sanitized snapshot. No chat harvesting,
provider initialization, file rewriting, permanent imported MemoryProposal, model
call or disclosure through a public search. Kernel setup owns the read consent.
"""
from datetime import datetime, timezone
from pathlib import Path

from .events import EventEnvelope, Sensitivity


def read_core_profile_evidence(journal, *, subject):
    root = journal.path.parent
    if (journal.path.name != 'experience.sqlite3'
            or not all((root / name).is_file() for name in (
                'identity.key', 'content-vault/content.key', 'content-vault/content.sqlite3'))):
        return None
    from .kernel_setup import KernelSetupStore
    setup = KernelSetupStore(root)
    configured = setup.configuration()
    if (configured is None or configured.subject != subject
            or configured.options.get('use_hermes_user_profile') is not True
            or configured.scope['chat_type'] != 'dm'):
        return None
    # Whole-subject forgetting wins over an old configuration even while the
    # physical erase worker is pending. A new owner confirmation is required.
    confirmed_sequence = journal.get(configured.event_id).sequence
    def forgotten():
        return any(item.sequence > confirmed_sequence
            and item.event.source == 'hermes.command.memory' and item.event.actor == subject
            and item.event.payload.get('scope') == 'subject'
            for item in journal.iter_reverse(event_types=('retention.erasure_requested',), subject=subject))
    if forgotten():
        return None
    from hermes_constants import get_hermes_home
    home = Path(get_hermes_home()).resolve()
    if root.resolve() != (home / 'plugin-data/hermes-alive/runtime/kernel').resolve():
        return None
    from hermes_cli.config import load_config_readonly
    from tools.memory_tool import MemoryStore, get_builtin_memory_config, get_builtin_memory_store_flags
    config = load_config_readonly()
    notes_enabled, user_enabled = get_builtin_memory_store_flags(config)
    if not user_enabled or not (home / 'memories').is_dir():
        return None
    # The public formatter itself is NOT an access gate and returns disabled
    # snapshots too. Check both the resolved config and the actual store flag.
    # Resolve configuration read-only, rather than the convenience loader which
    # calls Core's write-capable config loader and falls back to enabled defaults.
    # Core's standard snapshot loader reads both curated files. Consent is for
    # this personal profile's curated memory; only USER advice is exposed here.
    for name in ('MEMORY.md', 'USER.md'):
        path = home / 'memories' / name
        if path.is_file() and path.stat().st_size > 32768:
            raise ValueError('Core curated memory exceeds the admitted read bound')
    limits = get_builtin_memory_config(config)
    store = MemoryStore(int(limits.get('memory_char_limit', 2200)),
        int(limits.get('user_char_limit', 1375)), memory_enabled=notes_enabled,
        user_profile_enabled=user_enabled)
    store.load_from_disk()
    if not store.target_enabled('user'):
        return None
    text = store.format_for_system_prompt('user')
    if not text or not text.strip():
        return None
    if not isinstance(text, str) or len(text) > 6000:
        raise ValueError('Core curated profile exceeds the admitted context bound')
    if Path(get_hermes_home()).resolve() != home:
        raise ValueError('Core profile context changed homes during read')
    if not get_builtin_memory_store_flags(load_config_readonly())[1]:
        return None
    latest = setup.configuration()
    if latest is None or latest.event_id != configured.event_id:
        raise ValueError('Core profile read consent changed during read')
    if forgotten():
        return None
    digest = setup.protector.authenticate_json('core.user-profile.snapshot.v1', text)
    payload = dict(method='core-curated-user-profile-v1', configuration_event_id=configured.event_id,
        snapshot_digest=digest, target='user', user_explicit_statement=False,
        learning_authority_granted=False, execution_authority_granted=False, raw_content_stored=False)
    event_id = 'core.profile-context:' + setup.protector.authenticate_json(
        'core.user-profile.observation.v1', dict(subject=subject, **payload))
    record = journal.get(event_id)
    if record is None:
        appended = journal.append(EventEnvelope(event_id=event_id,
            event_type='memory.core_profile_observed', source='alive.core-profile-context',
            actor='system:alive-core-profile-reader', subject=subject,
            sensitivity=Sensitivity.PRIVATE, causation_id=configured.event_id, payload=payload))
        record = journal.get(appended.event.event_id)
    event = record.event
    if (event.event_type != 'memory.core_profile_observed' or event.subject != subject
            or event.source != 'alive.core-profile-context' or event.actor != 'system:alive-core-profile-reader'
            or event.causation_id != configured.event_id or dict(event.payload) != payload
            or event.observed_at > datetime.now(timezone.utc)):
        raise ValueError('Core profile observation conflicts with current consent or contents')
    return dict(memory_id=event_id, proposal_event_id=event_id,
        source_event_ids=(configured.event_id, event_id), predicate='profile.hermes_curated',
        kind='core_curated_advisory', value=text,
        source_observations=((event_id, event.observed_at.isoformat()),))
