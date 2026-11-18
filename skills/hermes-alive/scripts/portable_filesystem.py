"""Tree removal without depending on Windows' system-wide long-path setting."""
import os
import shutil


def filesystem_path(path):
    value=os.path.abspath(os.fspath(path))
    if os.name=='nt' and not value.startswith('\\\\?\\'):
        value=('\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value)
    return value


def remove_tree(path,*,ignore_errors=False):
    # Preserve rmtree's symlink, permission and failure semantics. The caller
    # still owns target selection; this changes only the Windows API spelling.
    shutil.rmtree(filesystem_path(path),ignore_errors=ignore_errors)
