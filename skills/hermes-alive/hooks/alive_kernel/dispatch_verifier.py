"""Read-only verification of canonical dispatch evidence, without queue setup."""
from datetime import datetime

from .dispatch_outbox import DispatchOutbox
from .event_store import ExperienceJournal, JournalRecord
from .privacy import LocalIdentityProtector


class DispatchEvidenceVerifier:
    """Reuse canonical predicates without exposing dispatch action methods.

    The caller supplies an already-validated attempt. This verifies receipt
    attribution, not action authorization, factual benefit or future authority.
    Construction performs no schema initialization or key creation.
    """

    RESULT_OUTCOMES = DispatchOutbox.RESULT_OUTCOMES
    _start_event_id = staticmethod(DispatchOutbox._start_event_id)
    _authenticated_start_payload = DispatchOutbox._authenticated_start_payload
    _authenticated_result_payload = DispatchOutbox._authenticated_result_payload
    _valid_start_evidence = DispatchOutbox._valid_start_evidence
    _valid_result_evidence = DispatchOutbox._valid_result_evidence

    def __init__(self, journal: ExperienceJournal, protector: LocalIdentityProtector):
        self.journal, self.protector = journal, protector

    def verify(
        self, result: JournalRecord, attempt: JournalRecord, *, observed_by: datetime | None = None,
    ) -> bool:
        if attempt.event.event_type != "action.attempted":
            return False
        payload = self._authenticated_result_payload(result)
        if payload is None:
            return False
        start = self.journal.get(str(payload.get("start_event_id") or ""))
        start_payload = self._authenticated_start_payload(start)
        if start is None or start_payload is None:
            return False
        generation = payload.get("lease_generation")
        if type(generation) is not int or generation < 1:
            return False
        if type(start_payload.get("lease_generation")) is not int:
            return False
        authorization = self.journal.get(str(attempt.event.payload.get("authorization_event_id") or ""))
        if authorization is None:
            return False
        args = dict(
            dispatch_id=str(payload.get("dispatch_id") or ""),
            attempt_id=str(attempt.event.payload.get("attempt_id") or ""),
            idempotency_key=str(attempt.event.payload.get("idempotency_key") or ""),
            capability=str(attempt.event.payload.get("executor") or ""),
            subject=attempt.event.subject, sensitivity=attempt.event.sensitivity,
            generation=generation,
        )
        return self._valid_start_evidence(
            start, start_payload, attempt,
            policy_event_id=str(authorization.event.payload.get("policy_event_id") or ""), **args,
        ) and self._valid_result_evidence(
            result, payload, attempt, start, observed_by=observed_by, **args,
        )
