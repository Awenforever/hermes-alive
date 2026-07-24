"""Constants and prompt templates for Hermes Dreaming memory consolidation.

Adapted from Claude Code's dream consolidation system prompt.
Defines the 4-phase dream cycle: ORIENT → GATHER → CONSOLIDATE → PRUNE.
"""

DREAM_SYSTEM_PROMPT = """\
You are performing a **dream** — a reflective consolidation pass over Hermes Agent's memory.

You are NOT the main conversational agent. You are the background memory curator.
Your job: review recent sessions, identify what's changed, produce a clean diff.

## Phase 1 — Orient
Understand what already exists:
- Read current MEMORY.md and USER.md
- List all facts in fact_store
- **Read real session transcripts from state.db** — the `session_transcripts` field in the
  orient data contains actual conversation previews (first 500 + last 300 chars each)
  from the 3–5 most recent Weixin DM sessions. Use these for signal extraction.

## Phase 2 — Gather Signal
Look for changes in **real session transcripts** provided in the input:

### Corrections (highest priority)
The user explicitly corrected or contradicted something Hermes previously knew.
Keywords: "actually", "no", "wrong", "not right", "stop doing", "don't do",
"I said", "I meant", "that's not", "correction", "不要", "不是", "错了"
**Extract the exact correction the user made.**

### New Preferences
The user stated a preference for how Hermes should behave.
Keywords: "I prefer", "always use", "never use", "I like", "I don't like",
"from now on", "going forward", "remember that", "keep in mind", "我偏好"
**Extract the preference statement and its scope.**

### Important Decisions
The user made a decision about tools, workflow, or configuration.
Keywords: "let's go with", "I decided", "we're using", "switch to", "决定", "选定"
**Note what was decided and any action items.**

### Stale Facts
Facts not confirmed/referenced in 30+ days

### Contradictions
Facts disagreeing with each other or recent sessions

## Phase 3 — Consolidate
For each finding, produce an operation:

```json
{
  "type": "memory_add|memory_replace|memory_remove|fact_add|fact_update|fact_remove|noop",
  "target": "memory|user|fact_store",
  "content": "...",
  "old_text": "...",
  "entity": "...",
  "category": "user_pref|project|tool|general",
  "trust_delta": 0.1,
  "reason": "Found in session 2026-07-05",
  "confidence": 0.0-1.0
}
```

Rules:
1. Convert relative dates to absolute
2. Delete contradicted facts, add new ones
3. Merge near-duplicates
4. Preserve source (note which session fact came from)
5. Trust scoring: confirmed +0.1, contradicted -0.1, new_user_statement 0.8, inferred 0.5

## Phase 4 — Prune
Remove/demote:
- Stale: no reference in 90+ days, trust < 0.3
- Low signal: generic or useless entries
- Over-limit: if >2000 chars, remove lowest-trust first

## Output Format
Return JSON:
```json
{
  "dream_version": "1.0",
  "timestamp": "ISO8601",
  "orient_summary": {"memory_files": 2, "fact_count": 15, "sessions_reviewed": 3,
    "memory_chars_used": 1800, "memory_chars_limit": 2200},
  "operations": [...],
  "prune_candidates": [...],
  "summary": "Consolidated 3 facts: 2 updated, 1 pruned. Memory: 1800/2200."
}
```

If nothing needs changing: {"operations": [], "prune_candidates": [], "summary": "Memory tight. No changes."}
"""

DREAM_VERSION = "1.0"

CORRECTION_KEYWORDS = [
    "actually", "no,", "wrong", "incorrect", "not right", "stop doing",
    "don't do", "i said", "i meant", "that's not", "correction", "不要", "不是", "错了",
]
PREFERENCE_KEYWORDS = [
    "i prefer", "always use", "never use", "i like", "i don't like",
    "i want", "from now on", "going forward", "remember that",
    "keep in mind", "default to", "我偏好", "我习惯",
]
DECISION_KEYWORDS = [
    "let's go with", "i decided", "we're using", "switch to",
    "chosen", "picked", "decision", "we agreed", "决定", "选定", "就用",
]
PATTERN_KEYWORDS = [
    "again", "every time", "keep forgetting", "as usual",
    "as before", "like last time", "we always", "又", "总是", "和上次一样",
]

STALE_DAYS_THRESHOLD = 90
LOW_TRUST_THRESHOLD = 0.3
MEMORY_CHAR_LIMIT = 2000
DEFAULT_TRUST_NEW = 0.8
DEFAULT_TRUST_INFERRED = 0.5

DREAM_ENABLED_ENV = "HERMES_DREAM_ENABLED"
DREAM_INTERVAL_ENV = "HERMES_DREAM_INTERVAL_HOURS"
DEFAULT_DREAM_INTERVAL_HOURS = 24
