"""Cold recovery and rollback against an actual prior vault runtime."""

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hooks'))
from alive_kernel.content_vault import ContentErasedError, ContentVault


def previous_runtime(hooks, root, action):
    subprocess.run([sys.executable, '-B', '-c', """
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
from alive_kernel.content_vault import ContentVault, ContentVaultError
root = Path(sys.argv[2])
try:
    vault = ContentVault(root / 'vault', backup_root=root / 'backups')
except ContentVaultError as error:
    assert sys.argv[3] == 'refuse' and str(error) == 'unsupported content-vault schema'
else:
    assert sys.argv[3] == 'seed', 'prior writer opened the upgraded vault'
    vault.put_json('original feedback', subject='user:test', purpose='feedback', content_id='feedback:old')
    vault.put_json('independent history', subject='user:test', purpose='history', content_id='history:other')
    vault.create_managed_backup('previous-runtime')
""", str(hooks.resolve()), str(root.resolve()), action], check=True)


def check_erased(vault):
    for content_id in ('feedback:old', 'plan:new'):
        try:
            vault.resolve_json(content_id)
            raise AssertionError('withdrawn content survived restart or restore')
        except ContentErasedError:
            assert vault.explicit_erasure_recorded(content_id)
    assert vault.resolve_json('history:other') == 'independent history'


def exercise(root, previous_hooks):
    previous_runtime(previous_hooks, root, 'seed')
    directory, backups = root / 'vault', root / 'backups'
    with closing(sqlite3.connect(directory / 'content.sqlite3')) as connection:
        assert connection.execute("SELECT value FROM vault_meta WHERE key='schema_version'").fetchone() == ('2',)
    previous_backup = backups / 'previous-runtime'
    restored = ContentVault.restore_managed_backup(previous_backup, root / 'restore-prior',
                                                   backup_root=root / 'restore-prior-backups')
    assert restored.resolve_json('feedback:old') == 'original feedback'
    # Only the managed source is in the erasure boundary. The compatibility
    # probe has its own tombstone before the main test starts.
    restored.erase_item('feedback:old')
    vault = ContentVault(directory, backup_root=backups)
    assert vault.resolve_json('feedback:old') == 'original feedback'
    vault.put_json('dependent planning body', subject='user:test', purpose='plan',
                   content_id='plan:new', depends_on=('feedback:old',))
    newer_backup = vault.create_managed_backup('with-dependent-copy')
    with patch.object(vault, '_purge_affected_backups', side_effect=OSError('interrupted purge')):
        try:
            vault.erase_item('feedback:old')
            raise AssertionError('interruption was not exercised')
        except OSError as error:
            assert str(error) == 'interrupted purge'
    check_erased(vault)
    assert vault.pending_erasure_jobs() and previous_backup.exists() and newer_backup.exists()
    previous_runtime(previous_hooks, root, 'refuse')
    assert vault.pending_erasure_jobs() and previous_backup.exists() and newer_backup.exists()
    cold = ContentVault(directory, backup_root=backups)
    assert not cold.pending_erasure_jobs()
    assert not previous_backup.exists() and not newer_backup.exists()
    check_erased(cold)
    previous_runtime(previous_hooks, root, 'refuse')
    recovered = ContentVault.restore_managed_backup(cold.create_managed_backup('after-erasure'),
                                                    root / 'restore-after')
    check_erased(recovered)
    print('HERMES_ALIVE_FEEDBACK_VAULT_ROLLBACK_OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous-hooks', required=True, type=Path)
    with tempfile.TemporaryDirectory(prefix='alive-feedback-rollback-') as directory:
        exercise(Path(directory), parser.parse_args().previous_hooks)
