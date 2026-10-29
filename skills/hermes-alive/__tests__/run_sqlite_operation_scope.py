"""Resource reuse must preserve current reads, every audit and physical erasure."""
import asyncio,json,sqlite3,sys,tempfile,threading
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel import ExperienceJournal,EventEnvelope
from alive_kernel.content_vault import ContentVault,ContentUnavailableError
from alive_kernel.sqlite_operation_scope import sqlite_operation_scope,hold_sqlite_resource


async def test(root):
    with sqlite_operation_scope() as scope:
        journal=ExperienceJournal(root/'experience.sqlite3')
        vault=ContentVault(root/'vault')
        ref=vault.put_json({'fact':'public synthetic value'},subject='user:test',purpose='test')
        for _ in range(3):
            assert vault.resolve_json(ref.content_id,expected_subject='user:test',expected_purpose='test')=={'fact':'public synthetic value'}
        assert len(scope.keepers)==2
        with sqlite_operation_scope() as nested:
            assert nested is scope
            event=journal.append(EventEnvelope(event_type='synthetic.changed',source='test',actor='user:test',subject='user:test',payload={}))
            assert journal.get(event.event.event_id).event==event.event
        assert not scope.closed
        # A separate writer's commit must be visible through ordinary fresh
        # reads: the keeper never opens a read transaction or caches a value.
        def worker():
            other=ExperienceJournal(journal.path)
            added=other.append(EventEnvelope(event_type='synthetic.external',source='test',actor='user:test',subject='user:test',payload={}))
            assert vault.resolve_json(ref.content_id,expected_subject='user:test',expected_purpose='test')
            return added.event.event_id
        identity=await asyncio.to_thread(worker)
        assert journal.get(identity) is not None
        assert len(scope.keepers)==2
        with closing(sqlite3.connect(vault.path)) as db:
            assert db.execute("SELECT count(*) FROM access_audit WHERE action='resolve' AND outcome='resolved'").fetchone()[0]==4
        erased=vault.erase_item(ref.content_id)
        assert erased.newly_erased==1
        with closing(sqlite3.connect(vault.path)) as db:
            assert db.execute('SELECT count(*) FROM content_items').fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM erasure_jobs WHERE backups_purged_at IS NULL').fetchone()[0]==0
            assert db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]==0
        try:vault.resolve_json(ref.content_id,expected_subject='user:test',expected_purpose='test')
        except ContentUnavailableError:pass
        else:raise AssertionError('operation scope cached erased content')
    assert scope.closed and not scope.keepers
    # No hidden handles survive a scope, which matters to Windows rotation.
    moved=journal.path.with_suffix('.moved');journal.path.rename(moved);moved.rename(journal.path)
    try:
        with sqlite_operation_scope() as failed:
            assert journal.get(identity)
            raise RuntimeError('synthetic cancellation/failure')
    except RuntimeError:pass
    assert failed.closed and not failed.keepers
    entered=threading.Event();release=threading.Event()
    with sqlite_operation_scope() as retired:
        def late_worker():
            entered.set();assert release.wait(5)
            # ContextVars reached this worker before retirement. It cannot
            # reopen a keeper after its parent operation finished.
            assert journal.get(identity)
        pending=asyncio.create_task(asyncio.to_thread(late_worker))
        while not entered.is_set():await asyncio.sleep(.001)
    release.set();await pending
    assert retired.closed and not retired.keepers
    missing=root/'must-not-be-created.sqlite3'
    with sqlite_operation_scope() as empty:
        hold_sqlite_resource(missing)
        assert not missing.exists() and not empty.keepers


with tempfile.TemporaryDirectory(prefix='alive-sqlite-scope-') as folder:
    asyncio.run(test(Path(folder)))
print('HERMES_ALIVE_SQLITE_OPERATION_SCOPE_OK')
