"""Synthetic subprocess only: no network, real models, channels or user data."""
import os
from pathlib import Path
import signal
import sys
import time

os.umask(0o077)
mode=sys.argv[1]
payload=sys.stdin.buffer.read()
if mode=='echo':
    sys.stdout.buffer.write(payload)
    sys.stderr.write('synthetic diagnostic')
elif mode=='fail':
    sys.stderr.buffer.write(payload)
    raise SystemExit(7)
elif mode in ('slow','ignore-term'):
    if mode=='ignore-term': signal.signal(signal.SIGTERM,signal.SIG_IGN)
    Path(sys.argv[2]).write_text(str(os.getpid()),encoding='ascii')
    time.sleep(30)
elif mode=='flood':
    sys.stdout.buffer.write(b'x'*32768)
else: raise SystemExit(9)
