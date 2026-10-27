# Experimental kernel configuration guide

Development branch only. This guide describes configuration choices; it does
not establish live functionality, migration, fleet or production acceptance.
The stable README must be aligned with the final engine before release.

## Guide the owner before staging setup

Use Hermes' existing profile, models, authentication and channels. Do not copy
the developer's interests, provider names, addresses or schedule. Ask which
authorized conversation should receive proactive contact; the one-time `/alive confirm`
command must be used in that actual conversation. Configuration does not enable
sending. Installation, guided configuration and `/alive enable` are distinct.

Model selection defaults to inheriting Hermes' main and fallback chain. A custom
selection names an existing Hermes model. Alive does not configure API keys or
install its own provider router.

Interests are optional soft preferences, with room for unfamiliar discoveries.
Ask about language and communication preferences without inventing shared
history. No developer research topic is a recommended default. Public search
topics are a separate choice: explain that those strings will be disclosed to
Hermes' configured search service. Private profile and chat text do not become
public queries automatically.

## Enable without a content feed

Public queries are optional. An owner may configure and confirm the native
kernel without `--public-query` or public-read consent. It uses the same agenda,
policy, decision and authorized channel path; an empty agenda remains quiet.
Existing admitted commitments do not need public search to become eligible.
This does not imply that ordinary chat has already been admitted as commitments,
or that all tool-action and long-term-memory integrations are complete.

Alive's role is continuous attentive assistance: remember the reason for pending
work, respond to changes and outcomes, make useful contact or stay quiet, and
carry context into subsequent conversation. Content discovery is an optional
input to that loop. Proactive contact should be a short natural contribution;
requested reports or detailed work may need a different level of detail.

## Continuing items from conversation

The target normal experience is one guided authorization, followed by direct
acceptance of clearly assigned follow-up work; ask only for unclear intentions.
An optional per-item confirmation mode remains available. As of 2026-10-26 both
paths are implemented under isolated qualification (ADR0241), not deployed or
production-accepted.

During initial guidance, explain this choice and the item retention period. Add
`--confirm-explicit-followup-intake` to the staged setup only after consent;
`--retention-days` is the disclosed period for accepted items as well as outbound
context. The actual target conversation confirmation protects these choices.
Existing configurations stay off unless the owner explicitly updates them.

If the owner also wants natural completion/cancel/snooze/resume, guide that
separate choice and use `--confirm-followup-management` (which includes intake).
An earlier intake-only grant does not acquire management during an upgrade.
These commands affect Alive items, not external jobs or previously sent messages.

New guidance also explains retaining each clearly admitted request's current
message, bounded to 6000 characters, separately from the interpreted item. Use the
chosen item lifetime for its encrypted source content. This is not a whole-chat
archive: other messages are not collected. Oversized requests need clarification
or the optional preview path; never silently truncate. Older grants without this
choice keep their original retention scope; historical wording cannot be recovered
from a description and must never be presented as an exact quote.

Ordinary item inventory reports source availability without copying every original
message into context. Exact item lookup can supply the retained original with its
own label; Native cognition uses it with the current interpreted item. Original
wording does not turn delegated interpretation into literal confirmation or grant
external execution authority. Expired/erased source is unavailable, not reconstructed.

The main agent can then record clear ongoing assignments directly. It asks about
ambiguous intent rather than treating casual/quoted material as obligations.
`/alive intake off` stops new intake while keeping existing items; `on` resumes
only a previously guided grant, and `status` reports the actual choice. This
does not start the proactive host or authorize unrelated external tools. Check
`/alive status` and separately enable the host when appropriate. A saved active
item is not evidence that a reminder is running or has been delivered.

For optional per-item confirmation, Hermes can use `alive_agenda` to propose an ongoing
item in the configured conversation. It shows the task, constraints, any explicit
dates, retention period and a `/alive agenda accept <handle>` command. The
proposal is temporary and not yet a saved obligation; use the exact command to
save it. `/alive agenda preview <handle>` shows the exact pending content.
Handles expire after ten minutes or a Gateway reload/session reset.

`/alive agenda list` shows at most eight retained items, not a complete inventory.
`/alive agenda done <item-id>` marks a known item complete; `cancel <item-id>`
ends it without claiming completion. Saving an item never grants external tool
execution or sending authority. It also does not enable Alive: the separate
`/alive enable` authorization still controls proactive work. No entire incoming
chat is retained by creating a temporary proposal. Interpretation remains the
main agent's responsibility; long-term adaptation and all action kinds have not
been qualified merely by installing these commands.

## Optional experience from Core tool activity

Offer `--confirm-core-tool-observation` only as a separate, default-off choice.
It records tool names, durations and terminal classifications in this exact owner
conversation, not arguments, result/error bodies or whole chats. Diagnostic validity
uses the selected retention period; structural journal entries remain until removed.
Explain that ordinary tool success labels are not independently verified task
success and that this choice grants neither tool execution nor automatic learning.
Reconfigure without the flag to stop new observations. No background activation is
needed to observe explicitly authorized tool activity in the configured conversation.

Guide the owner's permitted scope first and require per-operation confirmation
outside it. The current main-turn handoff is described below; autonomous Native
work selection and automatic result followup remain under development.

## Native background work — development qualification

The current main-turn handoff can send a clear request to perform an existing
item to native Hermes jobs. It is independently off for existing configurations.
Only after guidance add `--confirm-core-background-work`, alongside explicit
follow-up intake. This authorizes Core's normal model/profile-memory context and
Core's separately retained task records, not just Alive's optional profile advice.
That record includes the exact current owner message for the work handoff, bounded
to 6000 characters, alongside the prior agenda context. No silent truncation or
whole-chat collection. Explain this retention before confirming the guided scope.
Older background grants without this choice remain readable but require renewed
guidance before another handoff; an upgrade does not silently expand retention.
Explain that these are the profile's normal Core capabilities and context; do not
silently enable this on an upgrade or shared installation.

Guide which Core toolsets may run automatically and repeat
`--automatic-core-toolset <approved-core-toolset>` for those choices. None means
model-only work. Explain the actual capabilities in the user's language. File
tools use Hermes' existing access; this choice does not restrict them to one
directory or create an OS sandbox. No developer-specific toolset is a default.
Requests outside the set show their exact item and toolset preview and require
the owner's one-time `/alive agenda work-confirm ...` command before submission.

Core owns execution and saves the result locally. Submitting the job is not
proof that it ran or met the goal. `alive_agenda work_status` can query an exact
work ID or recover its association from the known item ID, without resubmission.
While Alive is active, its existing owner cycle observes changed Core lifecycle
facts and brings them into cognitive decisions. Unchanged state may stay quiet.
By default this does not inspect output bodies or verify that the assigned goal was met.
Independent automatic result followup and autonomous Native work selection remain
unfinished; do not promise them. The current owner can inspect an exact known
work with `work_evidence`: its bound request or bounded execution evidence.
Statements, requests and tool results are distinct; history is not a fresh
inspection. Large bodies have explicit pages. The reader retains no body;
small encrypted session links persist until removed for restart continuity.
Pause stops new cognitive cycles and handoffs; minimal association bookkeeping
for already-accepted Core work may continue. Accepted Core
tasks require Core's own task management. This experimental slice still needs
project-context, cancellation, lifecycle, migration and fleet qualification.

## Explain the public reading choices

| Choice | Installation flags | Scope |
|---|---|---|
| Initial public discovery | `--public-query "owner-selected public topic" --confirm-public-reads` | Search approved strings and read selected public results |
| Read actual citations too | Add `--confirm-cited-reads` | One bounded followup group, at most two actual cited targets |
| Refine public evidence too | Also add `--confirm-public-refinement` | The followup may instead perform one source-only public query and read at most two selected results |

Refinement requires the preceding public/cited-read choices. It is default off;
an earlier citation grant does not imply it. The citation and query paths share
one followup budget rather than opening a recursive crawl. The query planner
receives public material and already-public queries, excluding private profile,
conversation and inquiry bodies. This does not promise zero indirect information
about which public topics were selected.

Present the actual confirmation summary before giving the confirmation command.
It includes the model choice, approved topics, optional refinement and retention
choices. Do not hide a new reading scope behind a routine plugin upgrade.

## Keep memory and retention choices separate

Confirm retention of Alive's outbound share/source context and its duration.
This is separate from Hermes' own conversation history. It does not grant
inbound chat collection, automatic profile learning or external-provider recall.

`--confirm-hermes-profile-memory` separately permits current Core-curated USER
advice for the confirmed private conversation. It does not import it as an
explicit personal fact or authorize reading unrelated conversations. Disabling,
updating or deleting the Core profile affects subsequent reads; forgetting
retains its existing precedence. External-provider and ordinary feedback
integration remain open work.

## Verify the actual state

After scope confirmation, check that state remains configured but inactive.
The authorized `/alive enable` command starts the selected installed engine;
`/alive pause` prevents new proactive work. Already-submitted transport work is
owned by Hermes and, for Weixin, Enhance. Installing hooks, an empty error list
or a successful setup is not proof that a useful share was delivered.

Preserve existing state and key identity across update/uninstall/reinstall.
Incomplete or unknown state is a recovery condition, not permission to create
replacement keys or silently fall back to the legacy sender. Production
updates, restarts and real sends still require the concrete authorized window.


### Optional owned-work record review

Separately explain `--confirm-core-work-result-review` alongside the Core-work
grant. This permits active Alive cognition to read a bounded retained definition
and record window of its own terminal work, including recorded tool outputs and
worker statements. Core keeps the original records; Alive retains only a keyed
window digest in its structural journal, while derived assessments follow its
existing private candidate/outbound retention. It reads no unrelated sessions.
Old grants remain metadata-only. Pausing stops these background body reads;
accepted-work session-link bookkeeping and foreground explicit evidence queries
have their separately documented scope. Missing records stay unavailable.

The current window is at most 2048 content characters for the definition and
2048 for the last 16 active rows of its observed Core session. Tool arguments
remain indexed rather than inlined by default. Partial flags matter. A changed
window can wake the existing cognition cycle without a new scheduler; unchanged
records do not cause another inference. Historical records are not fresh
independent inspection, task completion, retry permission or a new action grant.
Do not promise autonomous verification or work selection from this option.


### Optional automatic file inspection — development qualification

Only after a separate explanation offer `--confirm-core-file-inspection` together
with owned-record review. It permits a new Core read_file-only job on a file target
already recorded in that owner's work; Core's permissions/model/profile context
and task-record retention apply. It is a limited automatic scope independent of
whether broader file-writing work was approved automatically. No unrelated path
scan, writes, messages, work repetition or item completion is included. Existing
grants remain off. Pausing or changed current authority stops new inspections.

The model may inspect one supplied target or wait with a revisit time. A prior
inspection is not automatically retried, including uncertain handoffs. Its target,
reason and binding are retained privately for at most seven days or the earlier
item expiry; the original Core task record follows Core retention. Historical
producer output and the later inspection readback remain different evidence.
General autonomous work and automatic goal closure are still under development.
## Stopping an owned background task

In the configured owner conversation, ask Hermes to stop the exact continuing
work. With explicit management enabled, it can use `alive_agenda work_stop` after
identifying the owned work and the current request. You can also send
`/alive agenda stop-work <work-id>`. This remains available while Alive is paused.

The operation stops further authorized work, pauses its existing Core schedule
and asks Core to cancel the current execution and its inspection. Acknowledgment
is not proof that execution has ended; pending or unknown outcomes are reported
honestly. Already-performed or in-flight effects are not undone. The agenda item
is retained, so stopping execution and dismissing the item remain explicit choices.


## Optional autonomous first work

After guiding automatic Core tool scope, ask separately whether explicit ongoing
assignments may start on a later Alive wake. `--confirm-autonomous-core-work`
requires background work and retained original intake/Core request permission.
Existing installations keep it off. If the original asks to wait for another
instruction, wait. Outside the chosen scope, request operation confirmation.
The original request will be retained in Core's local task record under Core's
retention policy; Alive's private source expiry does not erase Core records.
This option admits first work only, never automatic retry or agenda completion.

## Optional owned-work outcome management

Separately ask whether Alive may assess retained owned Core results and close a
goal it judges attained. `--confirm-core-work-outcomes` needs guided item
management and result review, including retained original intent. Existing setups
keep it off. Uncertain, ongoing or blocked items remain open. You can explicitly
ask Hermes to reopen a completed item; doing so does not redo the work.


### Optional task amendments

After intake/management guidance, separately offer `--confirm-followup-revisions`
if the owner wants explicit task/deadline edits in ordinary conversation. Requires
`--confirm-followup-management`; it retains those admitted amendment messages,
not whole chat. Existing grants remain unchanged. Explain that edits fence old
execution versions, do not undo effects/prove cancellation, and do not start a
replacement automatically. Omitted fields are preserved; a null deadline clears
it. Conflicts with attention/retention require a clear owner choice. This is a
development candidate under isolated qualification, not a production migration.


### Project context follows the assignment

New `--confirm-core-background-work` guidance includes private retention of the
Core-declared project directory and directory identity. Explain this alongside
the exact bounded owner request and Core task-record retention. The directory is
captured when the item is accepted; switching the current conversation's project
does not move the assignment. Core loads its own project rules at execution.
Alive does not read/copy those rules or infer a directory from the process/home.
Missing/replaced or unavailable project directories block later tools; this does
not cancel an in-flight effect or restrict Core's file access to a sandbox.

Old configurations do not silently acquire directory retention. If an older item
has no retained project, a new guided work request must preview and explicitly
confirm the selected current Core context, even inside the automatic tool range.
Do not describe unknown project metadata as a verified current project. No new
per-item question is required for a newly admitted item with retained context.
