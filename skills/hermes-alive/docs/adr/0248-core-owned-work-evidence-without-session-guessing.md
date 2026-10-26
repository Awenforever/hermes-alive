# ADR 0248 — Core-owned work evidence without session guessing

2026-10-26, Codex. Development qualification; not automatic goal verification.

## Association, not guessed identity

An actual Core job wrote and read its artifact, but a dependency test could not
find a session under the execution ID. Canonical Core admission has a separate
session identity. Do not scan transcripts, construct a plausible ID or treat
missing evidence as failed work.

The public `PluginContext.current_cron_execution()` and native pre-API/tool hooks
supply the actual execution and session. Associate only a signed Alive-owned
bound job in the current profile, with unchanged authored definition, matching
execution ledger and current guided background-work grant. Ordinary main turns,
unowned work and delegated children cannot mint this association. Deduplicate
each observed segment. Private session identifiers belong in the existing
encrypted vault; the signed journal contains protected references, execution
identity and causation, never identifiers or transcript bodies.

These small associations persist until removed, like structural work history.
Bookkeeping for already-accepted Core work may continue while proactive cognition
is paused; pausing does not cancel Core work. Removing the background grant stops
new associations. Capturing a link is neither body collection nor an action grant.

## Foreground evidence reads

`alive_agenda work_evidence` requires an exact known work ID and the existing
current owner/task/profile gate. Its request part reads the unchanged bound Core
job definition when conversation context was reduced. Its records part reads only
an actually observed Core session segment for the matching execution. Missing
associations are unavailable; no default session, recent-chat lookup or scan.

Use Core's state API against the exact existing profile store. Never create a
replacement store, follow an unapproved alternate path, or read a caller-named
session. User/system prompt rows are not exposed. Recent statements and tool
results have distinct labels; tool requests are indexed but arguments are omitted
from the default body window and retrieved only through a specific bounded page.
Known message IDs cannot cross sessions. Page fingerprints bind content and its
recorded role/tool/time metadata; continued pages reject changed data.

The reader does not persist bodies or create models, jobs, channels or queues.
The foreground Core conversation retains ordinary tool results under Core's own
policy. Alive retains only the encrypted association. This is separate from the
opt-in ordinary main-tool structural observer.

## Truth and remaining work

Core statements, issued requests and recorded results are different evidence.
A request does not prove execution. Historical returned data does not prove
current world state or the entire goal. Only a bounded active segment is read;
compaction, delegated work and older records may be absent. `task_success_proven`
and automatic result-followup remain false. Original assignment versions
accompany evidence; no agenda completion or retry occurs.

Actual file-tool execution/readback, real association, foreign-owner and
foreign-message refusal, fingerprinting and cold retrieval are integration
requirements. Fresh independent inspection and semantic goal assessment must
then enter Native decisions; a foreground endpoint is not that closed loop.
Privacy/dependency erasure, Core retention, uninstall/reinstall/migration, custom
state locations and the final fleet remain release gates.
