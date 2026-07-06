# Debugging: Session ID Format Change Breaks Context Capture

## Symptom

Proactive messages fire immediately after user activity (e.g., 4 minutes instead of 30+). Activity guard appears non-functional.

## Root Cause

Hermes Agent changed its session ID format. The `context_tracker.py` matched sessions with:

```python
WEIXIN_SESSION_PREFIX = "agent:main:weixin:dm:"
cursor.execute("SELECT id FROM sessions WHERE id LIKE ?", (f"{WEIXIN_SESSION_PREFIX}%",))
```

New format uses timestamp-based IDs like `20260706_083535_397de254`. The LIKE query returns zero rows.

`capture_recent_context()` returns `{}` silently. `recent_context.json` is never written. The activity guard in `proactive_watcher._user_active_recently()` sees no file → returns False → allows messages through.

## Detection

```bash
# Check if recent_context.json exists
ls /opt/data/hermes_alive_shared/recent_context.json
# If missing, test capture directly:
cd /opt/data/hooks/hermes-alive
python3 -c "
import os; os.environ['HERMES_PROACTIVE_WEIXIN_CHAT_ID']='YOUR_CHAT_ID'
from context_tracker import capture_recent_context
r = capture_recent_context()
print('session:', r.get('session_id', 'MISSING'))
print('last_user_ts:', r.get('last_user_timestamp', 'MISSING'))
"
```

## Fix

Changed from ID prefix match to source + user_id match:

```python
WEIXIN_SOURCE = "weixin"
WEIXIN_USER_ID = os.getenv("HERMES_PROACTIVE_WEIXIN_CHAT_ID", "").strip()

cursor.execute(
    "SELECT id FROM sessions WHERE source = ? AND user_id = ? ORDER BY started_at DESC LIMIT 1",
    (WEIXIN_SOURCE, WEIXIN_USER_ID)
)
```

This is format-independent — works regardless of how Hermes generates session IDs.

## Verification

After fix + gateway restart:
1. Send a message in WeChat
2. Wait for agent:end to fire (check errors.log for "Hermes Alive] handle() called, event=agent:end")
3. Check `ls /opt/data/hermes_alive_shared/recent_context.json` — should exist
4. Check `python3 scripts/logs.py --reason user_active --tail 3` — should show suppress skips for <30min activity