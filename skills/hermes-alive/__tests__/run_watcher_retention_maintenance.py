#!/usr/bin/env python3
"""Paused decisions still maintain privacy; cancellation is not thread completion."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import threading
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

HOOKS = Path(__file__).resolve().parents[1] / 'hooks'
sys.path.insert(0, str(HOOKS))

async def exercise(root):
    os.environ['HERMES_ALIVE_SHARED_DIR'] = str(root)
    os.environ['HERMES_HOME'] = str(root / 'home')
    import proactive_watcher as module
    import alive_kernel.retention_command as retention
    logs = []
    class Disabled(module.ProactivePlatformWatcher):
        @property
        def enabled(self): return False
        def _log(self, decision, **kw): logs.append((decision, kw))
        def _resolve_adapter_and_chat_id(self): raise AssertionError('paused maintenance attempted delivery')
    calls = []
    clock = [0.0]
    def maintain(path):
        calls.append(path)
        return {'history_derivatives_unresolved':0, 'history_derivatives_erased':0}
    with patch.object(module, 'BASE', root), patch.object(module.time, 'monotonic', lambda:clock[0]), \
            patch.object(retention, 'resume_retention_maintenance', maintain):
        watcher = Disabled({}, None)
        assert not await watcher.tick() and calls == []
        assert not (root / 'kernel').exists()
        reached = []
        class NoAdapter(Disabled):
            @property
            def enabled(self): return True
            def _resolve_adapter_and_chat_id(self):
                reached.append(True)
                return None, None
        assert not await NoAdapter({}, None).tick() and reached == [True]
        (root / 'kernel').mkdir()
        (root / 'kernel/experience.sqlite3').touch()
        assert not await watcher.tick() and len(calls) == 1
        assert not await watcher.tick() and len(calls) == 1
        clock[0] += 301
        assert not await watcher.tick() and len(calls) == 2
        # Delivery interval must not be the privacy cadence. Advance the clock
        # in the existing waiter and stop via its real one-shot wake condition.
        async def advance(_seconds): clock[0] += 301
        watcher._discovery_once_pending = lambda:True
        with patch.object(module.asyncio, 'sleep', advance), patch.dict(os.environ,
                {module.INTERVAL_ENV:'6000'}):
            await watcher._wait_for_next_tick()
        assert len(calls) == 3
        clock[0] += 301
        with patch.object(retention, 'resume_retention_maintenance', lambda _: {'history_derivatives_unresolved':1}):
            assert not await watcher._maintain_retention()
            assert not await watcher.tick()
    started, released = threading.Event(), threading.Event()
    finished = threading.Event()
    count = [0]
    def blocked(_path):
        count[0] += 1
        started.set()
        if not released.wait(10): raise AssertionError('test failed to release its worker')
        finished.set()
        return {'history_derivatives_unresolved':0}
    with patch.object(module, 'BASE', root), patch.object(retention, 'resume_retention_maintenance', blocked):
        watcher = Disabled({}, None)
        first = asyncio.create_task(watcher._maintain_retention())
        assert await asyncio.to_thread(started.wait, 5)
        owned = watcher._retention_maintenance_task
        first.cancel()
        try: await first
        except asyncio.CancelledError: pass
        assert watcher._retention_maintenance_task is owned and not owned.done()
        second = asyncio.create_task(watcher._maintain_retention())
        await asyncio.sleep(0)
        assert count[0] == 1
        released.set()
        assert await second and owned.done() and count[0] == 1
        assert watcher._retention_maintenance_task is None
        started.clear(); released.clear(); finished.clear()
        watcher = Disabled({}, None)
        third = asyncio.create_task(watcher._maintain_retention())
        assert await asyncio.to_thread(started.wait, 5)
        owned = watcher._retention_maintenance_task
        owned.cancel()
        try: await third
        except asyncio.CancelledError: pass
        assert not await watcher._maintain_retention() and count[0] == 2
        released.set()
        assert await asyncio.to_thread(finished.wait, 5)
        # Cancellation of the wrapper is still not evidence of thread completion
        # available to the watcher; it must not guess/restart that worker.
        assert not await watcher._maintain_retention() and count[0] == 2
    # Execute the actual storage/maintenance APIs through the disabled watcher,
    # not just the scheduling spy. No consent or kernel is implicitly created
    # on a real fresh install; this fixture deliberately supplies an owned store.
    from alive_kernel import ExperienceJournal
    from alive_kernel.content_vault import ContentVault, ContentErasedError
    real = root / 'real-runtime'
    ExperienceJournal(real / 'kernel/experience.sqlite3')
    vault = ContentVault(real / 'kernel/content-vault', backup_root=real / 'kernel/content-backups')
    expired = vault.put_json({'value':'synthetic expired sentinel'}, subject='user:synthetic',
        purpose='memory.episode', retention_until=datetime.now(timezone.utc) - timedelta(seconds=1))
    with patch.object(module, 'BASE', real):
        assert not await Disabled({}, None).tick()
    try:
        vault.resolve_json(expired.content_id)
    except ContentErasedError:
        pass
    else:
        raise AssertionError('periodic watcher did not physically erase expired fixture')
    assert not vault.explicit_erasure_recorded(expired.content_id)
    # Two watcher objects must coordinate through the actual recovery lock,
    # not through a Python task field that is lost during watcher replacement.
    started.clear(); released.clear(); finished.clear(); count[0] = 0
    with patch.object(module, 'BASE', real), patch.object(retention,
            '_resume_retention_maintenance_locked', blocked):
        old = Disabled({}, None)
        old_wait = asyncio.create_task(old._maintain_retention())
        assert await asyncio.to_thread(started.wait, 5)
        owned = old._retention_maintenance_task
        owned.cancel()
        try: await old_wait
        except asyncio.CancelledError: pass
        new = NoAdapter({}, None)
        reached.clear()
        assert not await new.tick()
        assert reached == [] and count[0] == 1
        assert new._retention_maintenance_report == {'maintenance_busy':1}
        released.set()
        assert await asyncio.to_thread(finished.wait, 5)
        # Real lock acquisition is authoritative; a busy observation can persist
        # briefly after the test worker's own completion marker is written.
        for _ in range(20):
            if await new._maintain_retention(): break
            await asyncio.sleep(.01)
        else: raise AssertionError('replacement watcher did not recover after lock release')
        assert count[0] == 2
    # Presence of a lock file alone is never proof of a running owner.
    assert (real / 'kernel/recovery.lock').is_file()
    assert retention.resume_retention_maintenance(real).get('maintenance_busy', 0) == 0
    # A separate process holds the same OS lock. Its live handle and handshake,
    # not a PID/lock file alone, establish the precondition for busy rejection.
    child_code = ("import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); "
        "from safe_io import file_lock\nwith file_lock(Path(sys.argv[2])):\n"
        " print('LOCK_HELD', flush=True)\n sys.stdin.readline()\n")
    child = subprocess.Popen([str(Path(sys.executable).absolute()), '-B', '-c', child_code,
        str(HOOKS), str(real / 'kernel/recovery.lock')], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        ready = await asyncio.wait_for(asyncio.to_thread(child.stdout.readline), timeout=5)
        assert ready.strip() == 'LOCK_HELD' and child.poll() is None
        assert retention.resume_retention_maintenance(real) == {'maintenance_busy':1}
    finally:
        child.communicate('\n', timeout=5)
    assert child.returncode == 0
    assert retention.resume_retention_maintenance(real).get('maintenance_busy', 0) == 0

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='alive-watcher-maintenance-') as directory:
        asyncio.run(exercise(Path(directory)))
    print('HERMES_ALIVE_WATCHER_RETENTION_MAINTENANCE_OK')
