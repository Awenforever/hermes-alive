# Proactive Silence — Diagnosis and Recovery

## What silence means

Hermes Alive can stay silent because of current activity, fixed quiet hours,
cooldown, interruption policy, unanswered interaction evidence, no eligible
Discovery candidate, or a quality rejection.

`ignored_proactive_count` is a raw observation. It is not a permanent “silent
mode” switch, and ordinary inbound messages do not mechanically reset every
relationship signal.

Do not edit `alive_state.json` or other runtime JSON files to force a reset.

## Read current status

From the installed skill root:

```bash
scripts/hermes-alive-lifecycle status
python3 hooks/alive_control.py status
python3 scripts/logs.py --tail 30
```

Useful log reasons include:

```text
quiet_hours
cooldown
user_active
personality_disposition_silent
unanswered_no_novel_value
unanswered_budget_exhausted
safety_unanswered_ceiling
quality_candidate_rejected
no_eligible_discovery_candidate
```

A raw unanswered count should be interpreted together with
`interaction_evidence`, current flow, cooldown, recent delivery records, and
Discovery eligibility.

## Verify the installation

```bash
bash scripts/verify.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS
```

If verify fails, stop and repair the installation or configuration before
changing runtime controls.

## Controlled disable and enable

To pause proactive delivery without deleting data:

```bash
python3 hooks/alive_control.py disable
```

To remove the manual disable override:

```bash
python3 hooks/alive_control.py enable
```

Check status again after the next watcher cycle.

## Test requests

```bash
python3 hooks/alive_control.py test
```

This queues a real proactive test request. Run it only with explicit approval to
send a real message. If a request was queued accidentally:

```bash
python3 hooks/alive_control.py clear-test-queue
```

## Discovery-specific silence

When a cached Discovery batch is exhausted, Hermes Alive remains silent rather
than replaying an old URL/topic. Check logs for cached, eligible, and suppressed
candidate counts. A new collection or a verified material update can make a
candidate eligible again.

## Escalation

If status and logs do not explain the silence, collect:

- lifecycle status and verify output;
- the last 30 proactive log entries;
- relevant cooldown/control state through the supported status command;
- recent watcher errors;
- current managed mode inventory.

Do not include Provider secrets, raw private chat content, or manually edited
state files in the diagnostic package.
