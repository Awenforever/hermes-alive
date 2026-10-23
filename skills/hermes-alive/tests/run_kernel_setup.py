"""Explicit setup, one-time scope confirmation and retention recovery, no Core IO."""
from datetime import datetime,timedelta,timezone
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.kernel_setup import KernelSetupStore,KernelSetupError
from alive_kernel.retention import RetentionProjection,RetentionDirection,RetentionValidationError
from alive_kernel.events import Sensitivity
from alive_kernel.content_vault import ContentErasedError

SCOPE={'contract':'hermes-core-conversation-v1','runtime_profile':'default','transport_profile':'default',
    'platform':'telegram','chat_id':'PRIVATE_SETUP_PEER','chat_type':'dm','thread_id':'7',
    'user_id':'PRIVATE_SETUP_USER','scope_id':'','guild_id':'','parent_chat_id':'',
    'session_key':'PRIVATE_SETUP_KEY','session_id':'PRIVATE_SETUP_SESSION'}
OPTIONS={'model_calls':True,'delivery':True,'outbound_retention_days':30,
         'outbound_retention_confirmed':True,'model':None,'public_queries':['public synthetic query'],'cited_reads':False}


def refuse(fn,kind=KernelSetupError):
    try:fn()
    except kind:return
    raise AssertionError('invalid setup accepted')


def test(root):
    store=KernelSetupStore(root,initialize=True)
    assert store.configuration() is None
    refuse(lambda:store.stage({**OPTIONS,'model_calls':False}))
    refuse(lambda:store.stage({**OPTIONS,'outbound_retention_confirmed':False}))
    refuse(lambda:store.stage({**OPTIONS,'outbound_retention_days':True}))
    intent,token=store.stage(OPTIONS)
    assert store.configuration() is None
    assert token.encode() not in store.journal.path.read_bytes()
    for change in ({'expires_at':intent.event.expires_at+timedelta(days=1)},
                   {'actor':'system:other'},{'observed_at':intent.event.observed_at-timedelta(minutes=1)},
                   {'event_id':'alive.setup:forged'}):
        forged=replace(intent,event=replace(intent.event,**change))
        refuse(lambda:store._payload(forged,store.INTENT_TYPE))
    refuse(lambda:store.stage(OPTIONS))
    refuse(lambda:store.confirm(intent.event.event_id,'bad-token',scope=SCOPE))
    refuse(lambda:store.confirm(intent.event.event_id,token,scope=SCOPE,
        now=datetime.now(timezone.utc)+timedelta(minutes=16)))
    configured=store.confirm(intent.event.event_id,token,scope=SCOPE)
    assert configured.subject.startswith('user:core-v2:') and configured.options['model'] is None
    assert store.configuration()==configured
    pending_id=intent.event.payload['content']['content_id']
    assert store.vault.explicit_erasure_recorded(pending_id)
    try:configured.options['model']='injected'
    except TypeError:pass
    else:raise AssertionError('setup snapshot is mutable')
    assert store.confirm(intent.event.event_id,token,scope=SCOPE)==configured
    refuse(lambda:store.confirm(intent.event.event_id,token,scope={**SCOPE,'thread_id':'other'}))
    refuse(lambda:store.confirm(intent.event.event_id,token,scope={**SCOPE,'user_id':'other'}))
    assert not store.journal.read(event_type='action.delegation_granted')
    assert not store.journal.read(event_type='autonomy.policy_changed')
    assert not store.journal.read(event_type='host.route_bound')
    policy=RetentionProjection(store.journal,content_vault=store.vault)
    assert policy.policy(configured.subject).allows(RetentionDirection.OUTBOUND)
    assert not policy.policy(configured.subject).allows(RetentionDirection.INBOUND)
    # An ordinary OFF after configuration must survive duplicate confirmation.
    off=policy.append_consent(subject=configured.subject,actor=configured.subject,enabled=False,
        retention_days=30,directions=(RetentionDirection.OUTBOUND,),sensitivity=Sensitivity.PRIVATE,
        operation_id='later-off')
    policy.apply(off)
    assert store.confirm(intent.event.event_id,token,scope=SCOPE)==configured
    assert policy.policy(configured.subject).enabled is False
    # Explicit replacement preserves history, invalidates the old code and does
    # not borrow/migrate the previous subject's state.
    second,new_token=store.stage(OPTIONS,replace=True)
    assert store.configuration() is None
    refuse(lambda:store.confirm(intent.event.event_id,token,scope=SCOPE))
    other=store.confirm(second.event.event_id,new_token,scope={**SCOPE,'user_id':'other'})
    assert other.subject!=configured.subject and not policy.policy(configured.subject).enabled
    assert len(store.journal.read(event_type=store.CONFIRMED_TYPE))==2
    raw=store.journal.path.read_bytes()
    canonical='\n'.join(record.event.canonical_json() for record in store.journal.iter_replay()).encode()
    assert b'PRIVATE_SETUP_' not in canonical and b'public synthetic query' not in canonical
    assert token.encode() not in canonical and new_token.encode() not in canonical
    assert b'PRIVATE_SETUP_' not in raw and b'public synthetic query' not in raw
    assert token.encode() not in raw and new_token.encode() not in raw
    # Forgetting the protected configuration cannot be undone by an old token.
    store.vault.erase_subject(other.subject)
    refuse(lambda:store.confirm(second.event.event_id,new_token,scope={**SCOPE,'user_id':'other'}),ContentErasedError)


def recovery(root):
    store=KernelSetupStore(root,initialize=True)
    intent,token=store.stage(OPTIONS)
    # Crash after durable confirmation but before the separate retention write.
    with patch.object(RetentionProjection,'append_consent',side_effect=OSError('crash fixture')):
        refuse(lambda:store.confirm(intent.event.event_id,token,scope=SCOPE),OSError)
    configured=store.configuration()
    assert configured is not None
    assert RetentionProjection(store.journal).policy(configured.subject) is None
    store.confirm(intent.event.event_id,token,scope=SCOPE)
    assert RetentionProjection(store.journal).policy(configured.subject).enabled


def later_choice(root):
    store=KernelSetupStore(root,initialize=True)
    intent,token=store.stage(OPTIONS)
    with patch.object(RetentionProjection,'append_consent',side_effect=OSError('crash fixture')):
        refuse(lambda:store.confirm(intent.event.event_id,token,scope=SCOPE),OSError)
    configured=store.configuration()
    retention=RetentionProjection(store.journal)
    off=retention.append_consent(subject=configured.subject,actor=configured.subject,enabled=False,
        retention_days=30,directions=(RetentionDirection.OUTBOUND,),sensitivity=Sensitivity.PRIVATE,operation_id='off')
    retention.apply(off)
    store.confirm(intent.event.event_id,token,scope=SCOPE)
    assert not retention.policy(configured.subject).enabled
    refuse(lambda:retention.append_consent(subject=configured.subject,actor=configured.subject,enabled=True,
        retention_days=30,directions=(RetentionDirection.OUTBOUND,),sensitivity=Sensitivity.PRIVATE,
        operation_id='late-recovery',not_after_sequence=off.sequence-1),RetentionValidationError)
    # Out-of-order replay cannot revive an earlier unprojected permission.
    early=retention.append_consent(subject='user:ordering',actor='user:ordering',enabled=True,
        retention_days=30,directions=(RetentionDirection.OUTBOUND,),sensitivity=Sensitivity.PRIVATE,operation_id='early')
    late=retention.append_consent(subject='user:ordering',actor='user:ordering',enabled=False,
        retention_days=30,directions=(RetentionDirection.OUTBOUND,),sensitivity=Sensitivity.PRIVATE,operation_id='late')
    retention.apply(late)
    assert retention.apply(early).outcome=='ignored'
    assert not retention.policy('user:ordering').enabled


def lost_key(root):
    refuse(lambda:KernelSetupStore(root))
    assert not root.exists()
    store=KernelSetupStore(root,initialize=True)
    intent,token=store.stage(OPTIONS)
    key=store.protector.key_path
    original=key.read_bytes()
    key.unlink()
    refuse(lambda:KernelSetupStore(root))
    refuse(lambda:KernelSetupStore(root,initialize=True))
    assert not key.exists()
    key.write_bytes(original)
    assert KernelSetupStore(root).latest_intent().event.event_id==intent.event.event_id
    key.write_bytes(b'bad')
    refuse(lambda:KernelSetupStore(root),RuntimeError)
    assert key.read_bytes()==b'bad'
    key.write_bytes(original)
    vault_key=store.vault.key_path
    encoded=vault_key.read_bytes()
    vault_key.unlink()
    refuse(lambda:KernelSetupStore(root,initialize=True))
    assert not vault_key.exists()
    vault_key.write_bytes(encoded)
    assert KernelSetupStore(root).confirm(intent.event.event_id,token,scope=SCOPE)


def preserve_legacy(root):
    store=KernelSetupStore(root,initialize=True)
    old=store.protector.pseudonym('user',SCOPE['user_id'])
    identity=store.protector.key_path.read_bytes()
    content=store.vault.put_json({'text':'LEGACY_PRIVATE_STATE_SENTINEL'},subject=old,
        purpose='conversation.inbound',sensitivity=Sensitivity.PRIVATE,
        retention_until=datetime.now(timezone.utc)+timedelta(days=30))
    retention=RetentionProjection(store.journal)
    original=retention.append_consent(subject=old,actor=old,enabled=True,retention_days=30,
        directions=(RetentionDirection.INBOUND,RetentionDirection.OUTBOUND),
        sensitivity=Sensitivity.PRIVATE,operation_id='legacy')
    retention.apply(original)
    intent,token=store.stage(OPTIONS)
    configured=store.confirm(intent.event.event_id,token,scope=SCOPE)
    assert configured.subject != old
    assert store.protector.key_path.read_bytes()==identity
    assert store.vault.resolve_json(content.content_id,expected_subject=old)['text']=='LEGACY_PRIVATE_STATE_SENTINEL'
    assert retention.policy(old).consent_event_id==original.event.event_id
    assert retention.policy(old).allows(RetentionDirection.INBOUND)
    assert store.journal.get(configured.event_id).event.payload['legacy_subjects_migrated'] is False


with tempfile.TemporaryDirectory(prefix='alive-guided-setup-') as directory:
    test(Path(directory)/'setup')
    recovery(Path(directory)/'recovery')
    later_choice(Path(directory)/'later')
    lost_key(Path(directory)/'lost-key')
    preserve_legacy(Path(directory)/'legacy')
print('HERMES_ALIVE_KERNEL_SETUP_OK')
