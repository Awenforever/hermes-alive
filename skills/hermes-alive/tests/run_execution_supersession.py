"""Pure retirement mechanics; authenticated command authority is tested in Core.

No Core, model, transport, foreign state or implied delivery. The private helper
receives an already-verified activation in production; this is not its auth gate.
"""
import importlib
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace

repo=Path(__file__).resolve().parents[3]
namespace=ModuleType('alive_control_pure_fixture');namespace.__path__=[str(repo)]
sys.modules[namespace.__name__]=namespace
bridge=importlib.import_module(namespace.__name__+'.kernel_execution_bridge')


def test(root):
    Journal=bridge.kernel('event_store').ExperienceJournal
    Runtime=bridge.kernel('autonomous_cycle_runtime').AutonomousCycleRuntime
    Host=bridge.kernel('autonomous_host_runtime').AutonomousHostRuntime
    journal=Journal(root/'journal.sqlite3');runtime=Runtime(journal)
    configured=SimpleNamespace(subject='user:synthetic')
    first=Host(runtime,subject=configured.subject,configuration_id='first',execute=True)
    assert bridge._unfinished(runtime,configured.subject) is None
    opened=first.open_cycle()
    assert bridge._unfinished(runtime,configured.subject).event.event_id==opened.event_id
    active={'supersedes_cycle_event_id':opened.event_id}
    bridge._complete_supersession(runtime,configured,active)
    closed=journal.get(opened.event_id+':closed')
    assert closed.event.payload['disposition']=='paused'
    assert closed.event.payload['external_delivery_proven'] is False
    assert bridge._unfinished(runtime,configured.subject) is None
    second=Host(runtime,subject=configured.subject,configuration_id='second',execute=True)
    following=second.open_cycle()
    bridge._complete_supersession(runtime,configured,active)
    assert journal.get(following.event_id+':closed') is None
    assert bridge._unfinished(runtime,configured.subject).event.event_id==following.event_id
    try:bridge._complete_supersession(runtime,SimpleNamespace(subject='user:foreign'),
                                     {'supersedes_cycle_event_id':following.event_id})
    except ValueError:pass
    else:raise AssertionError('foreign intent was retired')
    assert journal.get(following.event_id+':closed') is None
    before=journal.last_sequence()
    bridge._complete_supersession(runtime,configured,{})
    assert journal.last_sequence()==before
    assert not journal.read(event_type='delivery.succeeded')
    assert not journal.read(event_type='dispatch.started')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='alive-supersession-') as directory:test(Path(directory))
    print('HERMES_ALIVE_EXECUTION_SUPERSESSION_OK')
