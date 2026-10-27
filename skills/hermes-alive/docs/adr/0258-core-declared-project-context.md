# ADR 0258 — Keep delegated work in its Core-declared project

Status: implemented; focused actual-Core qualification passed; real-model and full regression pending.
Date: 2026-10-27.

## Product problem and boundary

A retained assignment must not lose its project when the foreground conversation
switches directories or the Gateway restarts. Core already supports a job workdir
and loads that directory's project instructions. Alive previously omitted workdir;
adding a private executor, guessing the process cwd or copying AGENTS into its own
prompt would create a second and unreliable interpretation of the workspace.

New background-work guidance therefore includes versioned private retention of
the Core-declared directory and its physical identity. The capture happens only
inside an authenticated owner intake tool turn. Prefer Core's recorded task cwd,
then its scoped session cwd, then bound/durable session records. Do not search the
filesystem, use environment/process/profile cwd as a substitute, or collect project
files. No declared project is an explicit state, not a guessed home directory.
An unavailable/nonlocal declared project blocks local execution instead of falling
back. Existing grants without protocol v1 do not silently gain metadata retention.

## Use Core, retain identity

The private source body carries the bounded directory metadata; the journal carries
only protected references and fingerprints. Each admitted work request binds its
own retained reference, original item expiry and identity. Core's public create_job
receives the normalized workdir. Core remains responsible for model selection,
approval, scheduling, context/rule loading and actual tools. No context_from chat
import, hand-written project-rule parser, scheduler or new queue is introduced.

Validate the declared and resolved paths plus filesystem device/inode before
admission, before activation and at owned pre-tool guards. Missing or replaced
directories stop later tools and new assessment/inspection, without claiming that
in-flight effects were undone or that the process was cancelled. The directory
is not a filesystem sandbox: normal Core file capabilities still apply. Inode
identity is a continuity check, not a portable migration identifier or proof of
unchanged project contents. These checks are not an atomic filesystem transaction: Core may load
current context files between admission and a later tool guard. They do not prove
that no read occurred during a directory-replacement race. Core reads current
project rules; rules are not frozen or silently elevated to user permission.

A foreground project switch and task/deadline amendment do not rebind the original
project. An old item missing retained context can use the existing exact operation
preview to choose the current Core-declared context explicitly; the automatic
within-scope path cannot silently make that choice. General project rebinding,
necessary dependency planning and automatic continuation remain separate work.

The independent read-only inspector inherits the producer's protected context.
A relative recorded read target is resolved only against the authenticated
producer job's retained directory and definition, never the inspector/host cwd.
Unknown legacy context cannot turn a relative path into an invented exact target.

## Qualification and limits

Actual installed Core cases pass task-directory precedence over another session
directory, foreground switching, explicit manual work in another foreground
project, missing-directory refusal before admission, replaced-directory refusal
before actual tool effects, and automatic startup in a fresh process. Project A
rules occur in actual worker requests while project B rules and file effects do
not. An independent actual Core inspection reads a producer-relative target in A
after the owner moved to B, rejects an unapproved read and observes the separately
changed file. Cold associations remain readable without replaying tools.

These controlled-provider cases prove routing, native context loading and guards,
not real-model judgment or whole-product acceptance. A separate real inherited
main/Native/worker probe and the portable regression are pending. Coordinated
source-derived erasure, old-grant migration/rollback, independent Git/fleet and
production remain release gates. This stage does not advance the 0/10 natural
sharing subgate or authorize production changes.


## Subsequent real-model finding — 2026-10-27

The first independent-Agent fixture supplied AIAgent(cwd=A) but omitted Core's
public session cwd binding. The hook cannot read the private Agent property;
capture correctly returned no_declared_project and the fixture failed before
Native/job execution. Official session policy declares cwd through Core's scoped
context. The next fixture uses that public declaration; no cwd guessing or Core
patch was added. This qualifies declared context, not arbitrary embedding callers.

That real run retained A across a foreground B query and Native selected work in
A. Its worker nevertheless reinterpreted the historical registration-only turn
as its present turn and did no file work. Outcome assessment kept the task open;
missing files made the run fail. This is a real semantic failure, not project
routing success or an excuse to automatically retry the same owned work. The
subsequent candidate explicitly supplies the later execution phase and time,
keeps original text verbatim and distinguishes original-turn conditions from
lasting constraints or outstanding owner-start approval. Requalification uses
a fresh isolated profile and the unchanged synthetic request. Its result and
new full qualification remain pending at this note.


The later-turn candidate passes five focused actual-Core cases: project work,
normal cold startup, explicit owner wait, partial-result retention and finite
attained-goal closure. The unchanged real-model scenario is still in flight at
this note; controlled responses do not establish real temporal interpretation.


## Subsequent qualification — 2026-10-27

The project-context baseline passed the portable 99-suite regression. The later
phase-context delta consists only of the worker prompt and factual turn DTO,
plus focused phase assertions; removing those exact additions restores the
whole runtime module byte for byte. Its five actual-Core controls passed, and
a fresh inherited-model main/Native/canonical-worker chain now writes/reads the
correct artifact in A, closes the supported goal, and answers a reduced-history
query from foreground B without moving or repeating work. Windows NTFS identity
also distinguishes missing and replaced directories in a thin helper check.
These are bounded qualifications, not an exact whole-suite run of the derivative,
Core Windows installation, independent Git/fleet or production acceptance.

The real trace also exposed limitations in the explanation layer: replies are
overly technical, call project rules an authorization basis and offer a general
project-rebinding operation that is not implemented. No such operation occurred;
the actual grant and tool guards were unchanged. Preserve these as open semantic
issues for the broader capability/provenance presentation, rather than scoring
the whole dialogue zero-error or patching individual phrases.

Two observation-fixture errors are retained separately from runtime evidence:
a foreground hook cannot observe a canonical worker's other process, and Core's
request-record kind is worker_tool_request. One known-invalid run was stopped
and cleaned instead of wasting further inference. The corrected exact fixture
helper first passed actual prior records and wrong-project/missing-result
counterexamples, then verified the new actual worker records. It does not claim
that an unobserved API payload was captured. All completed real-model reports
were read only after process/container termination, credential audit and removal.
