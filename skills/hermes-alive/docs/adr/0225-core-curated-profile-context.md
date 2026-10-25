# ADR0225 — Current Core-curated profile as separately consented advice

Date: 2026-10-25 (Asia/Shanghai).
Status: implemented; native qualification in progress.

The native loop previously saw optional explicit Alive preferences but not the
profile Hermes already curates. Do not create another raw-chat logger or silently
read a profile shared by several people. Add a default-off owner-confirmed choice
for a personal Hermes profile and a private target conversation. Existing setup,
encrypted configuration and native confirmation carry that independent choice.

Use Core's MemoryStore and threat-sanitized frozen load snapshot, with read-only
configuration resolution and explicit user-profile enable checks. The formatter
itself returns snapshots even for disabled targets; it is not an access gate.
Bind the actual current Core home to the kernel root, canonical owner and signed
configuration before loading. Do not create a missing memories directory or read
unbounded files; reject oversized material rather than silently truncate it.
Core's normal loader reads both curated files; only USER context is exposed.
No external provider is initialized and no file, memory entry or profile is edited.

Expose current text as core_curated_advisory, not USER_EXPLICIT or a permanent
MemoryProposal. Explicit owner corrections outrank inferred or stale Core recall.
The existing private generation pipeline may retain its input; public structural
history retains only keyed content identity and the confirmation/observation
relationship. No inferred preference becomes permission or a public query.

Every context reconstruction reads the current Core snapshot. Content changes,
deletion or a disabled target change or remove the advice; old planning/context
proof cannot claim the old value is current. Whole-subject forgetting blocks an
older read grant while physical erasure is still pending and does not modify
Core's separately owned files. A new explicit confirmation is necessary to opt in
again. The read path grants no action, learning operation or background task.

Qualification must use actual installed Core CLI/confirmation, synthetic profile
files, foreign owner/home and public-clearance refusal before file loading,
disabled-target refusal, no file mutation or plaintext journal content, current
updates/deletion, replay and pending forgetting. Component code and a synthetic
MemoryProvider protocol probe do not prove external-provider recall, automatic
daily learning, migration or private production use; those remain separate gates.

## Actual main-model curation handoff, 2026-10-26

A separate disposable personal Core profile starts with no USER content. Four
actual main-model turns, using only the builtin memory toolset and synthetic
statements/quoted noise/corrections, make five real memory tool calls. No fixture
manually seeds USER. After each turn, this Alive reader returns exactly the
current Core-formatted USER advice without changing either Core memory file.
All four turns use the configured main route, without fallback; no native host,
external memory provider or channel send runs. Credentials audited and removed.

The final state preserves the stable interests, the later qualification and the
explicit soft-preference/exploration distinction. It also retains unnecessary
negative reminders about quoted material. One intermediate model patch removed
a qualification before a subsequent actual patch restored it. This is evidence
for Core-owned curation and current advisory handoff, not perfect noise removal,
atomic semantics, long-term completeness or fact authority. Keep inferred recall
advisory and separate from explicit owner records. Complete native discovery
using this automatic profile and provider-specific external recall are separate
gates, not established by these four turns.

The irrelevant third-party reminder also changed its quoted polarity. Its denial
of owner attribution survived, but this is not faithful transcript retention. Do
not interpret the curation record as a direct user statement or use its quoted
keywords as an interest filter. File-content equality in the live probe proves
unchanged content; by itself it is not a system-call or metadata-write audit.
