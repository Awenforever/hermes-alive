"""Remove a real long tree without a system setting change or swallowed error."""
from pathlib import Path
import os
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from portable_filesystem import filesystem_path,remove_tree

with tempfile.TemporaryDirectory(prefix='alive-filesystem-') as folder:
    root=Path(folder)/'owned-tree'
    root.mkdir()
    deep=root/('a'*100)/('b'*100)
    os.makedirs(filesystem_path(deep))
    leaf=deep/('c'*70+'.txt')
    with open(filesystem_path(leaf),'w') as out:out.write('synthetic owned file')
    assert len(str(leaf))>260
    remove_tree(root)
    assert not root.exists()
    try:remove_tree(root)
    except FileNotFoundError:pass
    else:raise AssertionError('missing tree error swallowed')
    remove_tree(root,ignore_errors=True)
print('HERMES_ALIVE_PORTABLE_FILESYSTEM_OK')
