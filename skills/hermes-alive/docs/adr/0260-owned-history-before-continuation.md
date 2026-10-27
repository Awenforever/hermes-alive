# ADR 0260 — Read the earlier owned work before deciding what remains

Status: active-segment paging qualified in an isolated actual-Core case. Autonomous continuation is not implemented.
Date: 2026-10-28.

## Finding

The existing autonomous admission deliberately refuses an item with any previous
perform-work record. It can start first work, assess retained results and close
an attained finite goal, but cannot yet advance an unfinished multi-step task.
Removing that check would be unsafe: a completed Core execution is not task
success, and a model's next-step recommendation supplies no additional permission.

There is a concrete evidence prerequisite. The owned reader can hydrate known
message bodies but discovers only the last 16 active rows of the observed Core
session segment. An earlier effect can fall outside that window. Reading a body
with an offset does not discover earlier messages. A continuation design must
not mistake the newest window for the work history or repeat an omitted effect.

## Bounded chronological reads through Core

Extend the existing owner-scoped `work_evidence` operation with
`after_message_id`. Zero begins chronological paging of the current observed
active segment. Further pages use the returned cursor and the exact same
authenticated evidence reference; they cannot select an arbitrary session.
The existing work ownership, Core definition, execution/session association,
private session reference and original body fingerprint checks remain in force.

Each page asks Core's public scoped keyset reader for at most 17 rows and returns
at most 16. The extra row indicates whether another page exists. Cursor progress
uses scanned rows, including rows that are not exposed as work evidence, so a
page of non-evidence rows cannot stall the caller. Body limits remain independent:
a discovered message may require its existing fingerprinted body pages.

The default newest-window and exact-message reads retain their behavior.
History paging cannot be combined with a message/body selector or request text.
Invalid combinations fail before opening the Core state store. Bodies remain
on demand; this adds no transcript importer, event-body copy, model call,
permission, executor, scheduler or transport queue.

## Coverage is explicit

Exhausting these pages means no later active row was observed in this segment
at that read. It does not prove a complete execution history: compacted,
inactive, erased and ancestral records are excluded. Pages do not form an atomic
snapshot and previously returned evidence can change. Keep those limitations in
the returned contract instead of exposing a misleading global complete flag.
Instructions in old records remain untrusted evidence, not current owner intent.

## Subsequent continuation requirements

The next change must preserve the owner's first-guidance automatic scope, ask
outside it, and retain explicit waits and later amendments. Old first-work-only
grants must not silently expand. Reuse Core scheduling, execution, context,
permissions and models. Keep one admitted work step tied to its actual parent
results and current goal version, with a single durable identity across recovery.
An uncertain handoff, failed/unknown execution or owner stop cannot become an
automatic retry. Re-check the source, scope and parent basis before submission
and before tools. New evidence or a changed goal requires reassessment.

Qualification must include a useful multi-step assignment, an already-observed
effect outside the newest window, a required dependency outside automatic scope,
an explicit owner wait, correction between steps, restart between admission and
execution, and an unknown physical outcome. Verify actual effects and absence
of duplicate submissions. A pleasing recommendation alone cannot pass this gate.

## Qualification scope

The candidate test first runs the installed plugin's real Core work/file path.
It then appends explicitly labelled synthetic history fixtures through Core's
store in that isolated profile, pushing the actual earlier readback outside the
default window. Chronological results must match independently read Core IDs
without gaps or duplication, retain ownership/body bounds, reject mixed selectors
before body IO, and survive cold reopening. Fixture messages are not claimed as
additional worker calls or real-model proof. This does not qualify continuation,
external memory recall, deleted-history reconstruction, fleet or production.

The r250 installed-Core case passed with its original process exit 0, actual
container die 0/destroy/absence, and unchanged official Core supplier. It includes
normal work/file execution, current operation-contract checks, chronological
comparison against actual Core message IDs, pre-IO mixed-selector rejection and
a separate cold process. The parent test captures child output and verifies both
normal and cold completion; the child fixture marker is not separately printed
in the parent log. The launcher explicitly sets the history-test option, inherited
by both child processes. Do not describe these fixture rows as real-model work,
an atomic historical snapshot or a new complete portable/fleet qualification.
