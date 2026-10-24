"""Explicit bounded communication delegation, independent of model judgments."""
from datetime import datetime, timedelta, timezone
import re

from .deliberation import ActionKind
from .event_store import ExperienceJournal
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


class ActionDelegationError(ValueError):
    pass


class ActionDelegationStore:
    """Trusted user-command API; no model may infer or expand these grants.

    This establishes permission scope, not factual quality, interruption value,
    trusted gateway ingress or qualified automatic delivery.
    """
    def __init__(self, journal: ExperienceJournal):
        self.journal = journal
        self.protector = LocalIdentityProtector(journal.path.parent / 'identity.key')

    @staticmethod
    def _utc(value):
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ActionDelegationError('delegation time must be timezone-aware')
        return current.astimezone(timezone.utc)

    def grant(self, *, subject, actor, policy_event_id, route_binding_id,
              action_kinds, maximum_sensitivity, expires_at, operation_id, now=None,
              minimum_interval_seconds=3600, max_starts_per_24h=3,
              allow_natural_expression=False, until_revoked=False):
        if type(until_revoked) is not bool or until_revoked and expires_at is not None:
            raise ActionDelegationError('explicit consistent delegation lifetime required')
        if expires_at is None and not until_revoked:
            raise ActionDelegationError('missing expiry is not persistent authorization')
        current = self._utc(now)
        expiry = None if until_revoked else self._utc(expires_at)
        if (actor != subject or not subject or not policy_event_id or not route_binding_id
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}', operation_id)
                or not until_revoked and not current < expiry <= current + timedelta(days=30)):
            raise ActionDelegationError('invalid self-authorized delegation scope')
        kinds = sorted({ActionKind(kind).value for kind in action_kinds})
        if not kinds or not set(kinds) <= {'share', 'ask'}:
            raise ActionDelegationError('delegation supports only share/ask communication')
        sensitivity = Sensitivity(maximum_sensitivity)
        if type(allow_natural_expression) is not bool:
            raise ActionDelegationError('natural expression permission must be explicit boolean')
        if (type(minimum_interval_seconds) is not int or not 0 <= minimum_interval_seconds <= 86400
                or type(max_starts_per_24h) is not int or not 1 <= max_starts_per_24h <= 100):
            raise ActionDelegationError('invalid delegated start cadence')
        payload = {'operation_id': operation_id, 'policy_event_id': policy_event_id,
            'route_binding_id': route_binding_id, 'capability': 'hermes.channel.send',
            'action_kinds': kinds, 'maximum_sensitivity': sensitivity.value,
            'minimum_interval_seconds': minimum_interval_seconds,
            'max_starts_per_24h': max_starts_per_24h,
            'expires_at': expiry.isoformat() if expiry is not None else None, 'quality_qualified': False}
        if until_revoked:payload['lifetime']='until_revoked'
        # Absence in historical grants means NO permission expansion on upgrade.
        if allow_natural_expression:
            payload['allow_natural_expression'] = True
        payload['integrity_authenticator'] = self.protector.authenticate_json('action.delegation.v1', payload)
        return self.journal.append(EventEnvelope(event_id='action.delegation:' + operation_id,
            event_type='action.delegation_granted', source='hermes.command.alive', actor=actor,
            subject=subject, sensitivity=Sensitivity.PRIVATE, observed_at=current,
            occurred_at=current, expires_at=expiry, payload=payload))

    def revoke(self, *, delegation_event_id, subject, actor, now=None):
        grant = self.journal.get(delegation_event_id)
        if (actor != subject or grant is None or grant.event.subject != subject
                or grant.event.event_type != 'action.delegation_granted'):
            raise ActionDelegationError('cannot revoke a foreign or missing delegation')
        current = self._utc(now)
        payload = {'delegation_event_id': delegation_event_id}
        payload['integrity_authenticator'] = self.protector.authenticate_json('action.delegation.revoke.v1', payload)
        return self.journal.append(EventEnvelope(event_id=delegation_event_id + ':revoked',
            event_type='action.delegation_revoked', source='hermes.command.alive', actor=actor,
            subject=subject, sensitivity=Sensitivity.PRIVATE, occurred_at=current,
            observed_at=current, causation_id=delegation_event_id, payload=payload))

    def permits(self, delegation_event_id, *, subject, policy_event_id, route_binding_id,
                capability, action_kind, sensitivity, now=None, connection=None,
                natural_expression=False):
        """Read-only check, safe inside existing writer transactions."""
        def read(event_id):
            if connection is None:
                return self.journal.get(event_id)
            row = connection.execute('SELECT * FROM experience_events WHERE event_id=?', (event_id,)).fetchone()
            return self.journal._record(row) if row is not None else None
        record = read(str(delegation_event_id))
        if record is None:
            return False
        event = record.event
        current = self._utc(now)
        payload = _thaw_json(event.payload)
        authenticator = payload.pop('integrity_authenticator', None)
        if type(natural_expression) is not bool:
            return False
        try:
            if payload.get('lifetime')=='until_revoked':
                valid_lifetime=event.expires_at is None and payload['expires_at'] is None
            else:
                valid_lifetime=(payload.get('lifetime') is None and event.expires_at is not None
                    and current<event.expires_at
                    and event.expires_at==datetime.fromisoformat(payload['expires_at']))
            return bool(event.event_type == 'action.delegation_granted'
                and event.source == 'hermes.command.alive' and event.actor == subject
                and event.subject == subject and event.sensitivity is Sensitivity.PRIVATE
                and event.event_id == 'action.delegation:' + payload['operation_id']
                and event.observed_at <= current and valid_lifetime
                and self.protector.verify_json('action.delegation.v1', payload, authenticator)
                and (not natural_expression or payload.get('allow_natural_expression') is True)
                and read(event.event_id + ':revoked') is None
                and payload['policy_event_id'] == policy_event_id
                and payload['route_binding_id'] == route_binding_id
                and payload['capability'] == capability == 'hermes.channel.send'
                and ActionKind(action_kind).value in payload['action_kinds']
                and tuple(Sensitivity).index(Sensitivity(sensitivity)) <=
                    tuple(Sensitivity).index(Sensitivity(payload['maximum_sensitivity'])))
        except (KeyError, TypeError, ValueError):
            return False
