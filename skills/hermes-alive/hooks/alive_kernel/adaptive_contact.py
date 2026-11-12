"""Advance only the confirmed owner's detached contact-timing state."""
from contextlib import closing
from datetime import timezone
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import sqlite3
from uuid import uuid4

from .content_vault import ContentReference, ContentVaultError
from .events import EventEnvelope, Sensitivity, _thaw_json


@lru_cache(maxsize=2)
def _legacy_module(name):
    # Load the two shipped timing modules directly. Importing hooks/__init__.py
    # would initialize other legacy runtime code and its process-level paths.
    source=Path(__file__).resolve().parents[1]/f'{name}.py'
    spec=spec_from_file_location(f'{__package__}._adaptive_{name}',source)
    module=module_from_spec(spec)
    sys.modules[spec.name]=module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name,None)
        raise
    return module


class AdaptiveContactChanged(ValueError):
    """Another generation or advance already won the journal transaction."""


def status(store, configured, at):
    result={'state':'adaptive_staged','window':None,
            'timezone':configured.options['adaptive_contact']['config']['timezone']}
    if store.activation() is None:
        return result
    try:
        projection=AdaptiveContactProjection(store,configured)
        _,checkpoint=projection.current()
        allowed,_=projection.evaluate(checkpoint,at)
        result['state']='adaptive_open' if allowed else 'adaptive_quiet'
    except (ValueError,OSError,sqlite3.Error,ContentVaultError):
        result['state']='adaptive_unavailable'
    return result


class AdaptiveContactProjection:
    EVENT='alive.contact.adaptive_advanced'
    PURPOSE='contact.adaptive.checkpoint'

    def __init__(self, store, configured):
        self.store=store
        self.configured=configured
        self.engine=_legacy_module('circadian_engine')
        self.policy=_legacy_module('circadian_sleep_quiet_policy')
        imported=configured.options['adaptive_contact']
        self.baseline=dict(imported['checkpoint'])
        self.config=self.engine.CircadianConfig.from_mapping(dict(imported['config']))
        if not self.config.enabled or self.config.mode!='live':
            raise ValueError('confirmed adaptive policy must use live timing')

    def evaluate(self, checkpoint, at):
        """Pure civil-time projection used immediately before channel handoff."""
        if at.utcoffset() is None:
            raise ValueError('adaptive contact requires absolute time')
        engine=self.engine.CircadianEngine(config=self.config,checkpoint=checkpoint)
        decision=self.policy.evaluate_sleep_quiet_live(engine.shadow_decision(now=at),now=at,
            environ={'TZ':self.config.timezone})
        return decision['would_allow_dynamic'],engine.contact_checkpoint()

    def _latest(self, connection):
        return connection.execute('SELECT sequence,canonical_json,integrity_hash,event_id FROM experience_events '
            'WHERE event_type=? AND subject=? AND correlation_id=? ORDER BY sequence DESC LIMIT 1',
            (self.EVENT,self.configured.subject,self.configured.event_id)).fetchone()

    def current(self):
        if self.store.configuration()!=self.configured:
            raise AdaptiveContactChanged('confirmed contact owner changed')
        with closing(self.store.journal._connect()) as connection:
            row=self._latest(connection)
        if row is None:
            return None,self.baseline.copy()
        event=self.store.journal._record(row).event
        payload=_thaw_json(event.payload)
        signature=payload.pop('integrity_authenticator',None)
        if (event.actor!='system:alive-contact' or event.source!='alive.contact'
                or event.sensitivity is not Sensitivity.PRIVATE
                or event.causation_id!=(payload.get('previous_event_id') or self.configured.event_id)
                or not self.store.protector.verify_json(self.EVENT+'.v1',
                    {'event_id':event.event_id,'subject':event.subject,'configuration':event.correlation_id,
                     'observed_at':event.observed_at.isoformat(),'payload':payload},signature)):
            raise ValueError('adaptive contact checkpoint provenance unavailable')
        reference=ContentReference.from_event_payload(payload['content'])
        checkpoint=self.store.vault.resolve_json(reference.content_id,expected_subject=self.configured.subject,
            expected_purpose=self.PURPOSE,expected_sensitivity=Sensitivity.PRIVATE)
        if self.store.vault.digest_json(checkpoint)!=reference.digest:
            raise ValueError('adaptive contact checkpoint changed')
        return event,checkpoint

    def advance(self, activation, at):
        if at.utcoffset() is None:
            raise ValueError('adaptive contact requires absolute time')
        at=at.astimezone(timezone.utc)
        if self.store.activation()!=activation or activation is None:
            raise AdaptiveContactChanged('adaptive contact activation changed')
        previous,checkpoint=self.current()
        if previous is not None and at<previous.observed_at:
            raise AdaptiveContactChanged('clock precedes last adaptive contact checkpoint')
        _,updated=self.evaluate(checkpoint,at)
        if updated==checkpoint:
            return updated
        owner=self.configured.subject
        config_id=self.configured.event_id
        activation_id=activation['activation_event_id']
        previous_id=previous.event_id if previous is not None else None
        event_id='contact-adaptive:'+uuid4().hex
        config_record=self.store.journal.get(config_id)
        config_ref=ContentReference.from_event_payload(config_record.event.payload['content'])
        reference=self.store.vault.put_json(updated,subject=owner,purpose=self.PURPOSE,
            content_id=event_id,withdraw_with=(config_ref.content_id,))
        payload={'previous_event_id':previous_id,'activation_event_id':activation_id,
                 'content':reference.to_event_payload()}
        payload['integrity_authenticator']=self.store.protector.authenticate_json(self.EVENT+'.v1',
            {'event_id':event_id,'subject':owner,'configuration':config_id,
             'observed_at':at.isoformat(),'payload':payload})
        event=EventEnvelope(event_id=event_id,event_type=self.EVENT,source='alive.contact',
            actor='system:alive-contact',subject=owner,correlation_id=config_id,
            causation_id=previous_id or config_id,observed_at=at,occurred_at=at,
            sensitivity=Sensitivity.PRIVATE,payload=payload)

        def current_generation(connection):
            head=self._latest(connection)
            if (head['event_id'] if head else None)!=previous_id:
                raise AdaptiveContactChanged('adaptive contact checkpoint advanced concurrently')
            for event_type,expected in ((self.store.INTENT_TYPE,config_id.removesuffix(':confirmed')),
                    ('alive.setup.activated',activation_id),('autonomy.policy_changed',activation['policy_event_id'])):
                query='SELECT event_id FROM experience_events WHERE event_type=?'
                args=(event_type,)
                if event_type=='autonomy.policy_changed':
                    query+=' AND subject=?'
                    args+=(owner,)
                latest=connection.execute(query+' ORDER BY sequence DESC LIMIT 1',args).fetchone()
                if latest is None or latest['event_id']!=expected:
                    raise AdaptiveContactChanged('adaptive contact authority changed before commit')

        self.store.journal.append(event,precondition=current_generation)
        return updated
