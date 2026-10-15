"""Bounded registered-intent context, not a second transport queue.

A recorded attempt is not proof of execution, queue membership or delivery.
Only independently validated canonical outcomes are exposed as outcome facts.
"""
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime

from .content_vault import ContentReference, ContentVaultError
from .events import Sensitivity, _thaw_json
from .expression_history import ExpressionHistoryReader
from .outcomes import OutcomeProjection


@dataclass(frozen=True, slots=True)
class PriorAction:
    attempt_event_id: str
    expression_event_id: str
    selection_event_id: str
    recorded_at: str
    wording_excerpt: str = field(repr=False)
    outcomes: tuple = ()

    def to_prompt(self):
        return {'attempt_event_id':self.attempt_event_id,
            'expression_event_id':self.expression_event_id,
            'selection_event_id':self.selection_event_id, 'recorded_at':self.recorded_at,
            'wording_excerpt':self.wording_excerpt,
            'status':'registered_intent_only', 'execution_and_queue_membership':'not_assessed',
            'observed_outcomes':[{'event_id':event,'kind':kind,'recorded_at':at}
                                 for event,kind,at in self.outcomes],
            'observed_outcomes_order':'newest_record_first',
            'complete_outcome_inventory':False, 'user_preference_evidence':False,
            'action_authority':False}


class ActionHistoryReader:
    def __init__(self, journal, *, content_vault=None, context_vault=None):
        self.journal = journal
        self.wording = ExpressionHistoryReader(journal,content_vault=content_vault,
                                               context_vault=context_vault)
        # Match SendPreparationRuntime/DispatchOutbox's explicit content vault.
        # Never search unrelated vaults or treat unavailable content as a fact.
        self.outcomes = OutcomeProjection(journal,content_vault=content_vault)

    def read(self, *, subject, clearance, before_sequence=None):
        history = self.wording.read(subject=subject,clearance=clearance,
                                     before_sequence=before_sequence)
        expressions = {item.event_id:item for item in history}
        result = []
        with closing(self.outcomes._connect()) as connection:
            for record in self.journal.iter_reverse(event_types=('action.attempted',),
                    subject=subject,batch_size=16,max_records=64,before_sequence=before_sequence):
                event, p = record.event, record.event.payload
                if list(Sensitivity).index(event.sensitivity) > list(Sensitivity).index(Sensitivity(clearance)):
                    continue
                permit = self.journal.get(str(p.get('authorization_event_id','')))
                if permit is None:
                    continue
                auth = _thaw_json(permit.event.payload)
                signature = auth.pop('integrity_authenticator',None)
                prior = expressions.get(auth.get('expression_event_id'))
                if (prior is None or permit.event.subject != subject
                        or permit.event.sensitivity is not event.sensitivity
                        or permit.event.event_type != 'action.authorization_evaluated'
                        or permit.event.source != 'alive.authorization'
                        or permit.event.actor != 'system:alive-authorizer'
                        or not self.outcomes.receipt_protector.verify_json('action.authorization.v1',auth,signature)
                        or auth.get('outcome') != 'authorized' or auth.get('executes_action') is not False
                        or auth.get('capability') != 'hermes.channel.send'
                        or event.source != 'alive.outcomes'
                        or event.event_id != 'action.attempt:' + str(p.get('attempt_id',''))
                        or event.causation_id != permit.event.event_id
                        or permit.sequence >= record.sequence
                        or auth.get('selection_event_id') != p.get('selection_event_id')
                        or prior.selection_event_id != p.get('selection_event_id')
                        or auth.get('candidate_id') != p.get('candidate_id')
                        or auth.get('capability') != p.get('executor')):
                    continue
                try:
                    until = datetime.fromisoformat(auth['valid_until'])
                    if not permit.event.observed_at <= event.observed_at < until:
                        continue
                except (KeyError,TypeError,ValueError):
                    continue
                row = connection.execute('SELECT a.* FROM action_attempts_v1 a '
                    'JOIN outcome_projection_decisions_v1 d ON a.event_id=d.event_id '
                    "WHERE a.event_id=? AND a.subject=? AND d.outcome='recorded'",
                    (event.event_id,subject)).fetchone()
                if (row is None or any(row[key] != p.get(key) for key in (
                        'attempt_id','authorization_event_id','selection_event_id',
                        'candidate_id','executor','idempotency_key'))
                        or row['frame_id'] != auth.get('frame_id')
                        or row['sensitivity'] != event.sensitivity.value
                        or row['attempted_at'] != event.observed_at.isoformat()):
                    continue
                facts = []
                # Bound metadata work and owner scope before resolving content.
                rows = connection.execute('SELECT * FROM action_outcomes_v1 '
                    'WHERE attempt_id=? AND subject=? ORDER BY rowid DESC LIMIT 8',
                    (row['attempt_id'],subject)).fetchall()
                for outcome in rows:
                    if list(Sensitivity).index(Sensitivity(outcome['sensitivity'])) > list(Sensitivity).index(Sensitivity(clearance)):
                        continue
                    original = self.journal.get(outcome['event_id'])
                    if (original is None or original.sequence <= record.sequence
                            or not self.outcomes._row_matches_record(outcome,original)
                            or not self.outcomes.canonical_evidence_valid_for(self.journal,connection,original)):
                        continue
                    try:
                        ref = ContentReference.from_event_payload(original.event.payload['content'])
                        details = self.outcomes.content_vault.resolve_json(ref.content_id,
                            expected_subject=subject,expected_purpose='outcome.' + outcome['kind'],
                            expected_sensitivity=Sensitivity(outcome['sensitivity']))
                        if self.outcomes.content_vault.digest_json(details) != ref.digest:
                            continue
                    except (KeyError,TypeError,ValueError,ContentVaultError):
                        continue
                    facts.append((original.event.event_id,outcome['kind'],outcome['observed_at']))
                result.append(PriorAction(event.event_id,prior.event_id,prior.selection_event_id,
                    event.observed_at.isoformat(),prior.excerpt,tuple(facts)))
                if len(result) == 4:
                    break
        return tuple(result)
