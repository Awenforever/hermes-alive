"""Synthetic process protocol fixture; no host or network delivery."""
import json
import sys
import time

mode = sys.argv[1]
body = sys.stdin.buffer.read().decode("utf-8")
target = "test:test-chat:user:causal-recovery" if mode == "bridge" else "test:chat"
assert sys.argv[2:] == ["send", "--to", target, "--file", "-", "--json"]
if mode == "bridge":
    assert body == "encrypted causal recovery candidate"
    sys.stdout.write('{"success":true,"message_id":"PRIVATE_CLI_REPORT_MARKER"}')
elif mode == "timeout":
    time.sleep(5)
elif mode == "overflow":
    sys.stdout.write("x" * 70000)
elif mode == "invalid_utf8":
    sys.stdout.buffer.write(b"\xff")
else:
    print(json.dumps({"success": True, "body": body}, ensure_ascii=False))
