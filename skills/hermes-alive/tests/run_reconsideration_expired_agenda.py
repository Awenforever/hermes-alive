"""Expired agenda cannot permanently exhaust the bounded temporal wait scan."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal,EventEnvelope,AutonomyPolicyProjection,PolicyContext
from alive_kernel.agenda import AgendaProposal,AgendaItemKind,AgendaAuthority
from alive_kernel.autonomous_cycle_runtime import AutonomousCycleRuntime

with tempfile.TemporaryDirectory(prefix='alive-expired-agenda-wait-') as d:
    journal=ExperienceJournal(Path(d)/'experience.sqlite3')
    runtime=AutonomousCycleRuntime(journal)
    policies=AutonomyPolicyProjection(journal)
    policies.apply(policies.append_update(subject='user:synthetic',actor='user:synthetic',
        expected_revision=0,enabled=True,context=PolicyContext(can_interrupt=True),operation_id='synthetic-policy'))
    source=journal.append(EventEnvelope(event_type='conversation.inbound',source='synthetic-fixture',
        actor='user:synthetic',subject='user:synthetic',payload={'synthetic':True}))
    now=datetime.now(timezone.utc);expires=now+timedelta(hours=1)
    later=now+timedelta(hours=2)
    agenda=runtime.preparation.expression.planning.synth.reader.agenda
    def add(identity,**bounds):
        proposed=agenda.append_proposal(AgendaProposal(kind=AgendaItemKind.OPPORTUNITY,
            subject='user:synthetic',item_id=identity,details={'synthetic':'unrelated opportunity'},
            authority=AgendaAuthority.USER_EXPLICIT,source_event_ids=(source.event.event_id,),
            confidence=1,**bounds),actor='user:synthetic')
        assert agenda.apply(proposed).outcome=='active'
    for index in range(129):add('expired-probe:'+str(index),expires_at=expires)
    # Clock progression, not sleep or direct projection-table mutation. Rows
    # intentionally remain ACTIVE; ordinary expiry must not need housekeeping.
    runtime.reconsideration.clock=lambda:later
    def capture():
        return runtime.reconsideration.capture(subject='user:synthetic',configuration_id='synthetic-config',
            execute=False,policy=policies.current('user:synthetic'),parameters={},window_seconds=300)
    assert capture().valid_until==later+timedelta(seconds=300)
    due=later+timedelta(seconds=30)
    add('future-probe',due_at=due,expires_at=later+timedelta(hours=1))
    assert capture().valid_until==due,'expired history hid a real upcoming boundary'
    for index in range(128):add('unexpired-probe:'+str(index))
    assert capture().valid_until<=later,'genuinely incomplete current agenda became safe wait'
    assert not journal.read(event_type='action.attempted')
    assert not journal.read(event_type='dispatch.externally_delivered')
print('HERMES_ALIVE_RECONSIDERATION_EXPIRED_AGENDA_OK')
