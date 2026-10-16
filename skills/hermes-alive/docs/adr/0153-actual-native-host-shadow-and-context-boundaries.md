# ADR 0153 — Actual native-host shadow composition and evidence boundaries

Date: 2026-10-16. Status: offline integration evidence; no installed-host activation.

## Why this follows the failed auxiliary wording experiments

ADR0151/0152 did not justify another purpose stage or a direct-expression runtime
switch. Their auxiliary calls did not contain the actual Hermes system/persona
assembly. Before spending on more language samples, establish how the native host
can consume Alive's current retained context without borrowing the foreground
session, tools, external memory manager or unconsented history.

`tests/probe_alive_native_host.py` runs the retained actual Core AIAgent constructor,
prompt assembly, SDK HTTP request construction and conversation facade. It does not
replace these with a high-level fake worker. Only physical HTTP responses are
controlled: metadata queries return explicit503; provider.invalid returns a bounded
synthetic completion. DNS/connect are denied by an audit hook and the Docker network
is disabled. The profile/home/project are synthetic tmpfs paths, Core/dependencies
are read-only, and no production mounts, keys or channels are needed.

This is an opt-in Core integration probe, **not a mandatory portable-CI test using
the small ci/fakes package**. Missing Core/dependencies must fail, not silently skip.
Run it inside an isolated read-only/no-network environment, providing actual Core:

```bash
python -B skills/hermes-alive/tests/probe_alive_native_host.py --core /path/to/hermes-core
```

The optional `--kernel-package` locates a complete hooks/tests package for retained
container experiments. It is not permission to patch a production install. A
90-second process watchdog bounds constructor/turn/test hangs; individual native
turns also have a ten-second host budget. The watchdog terminates the test process,
not a remote production process. Fake calls are not counted as actual model usage.

## Actual native boundary observations

With explicit empty enabled_toolsets, skip_memory, skip_background_review,
skip_context_files and load_soul_identity:

- Actual tools and valid tool names are empty; built-in store and external manager
  are absent. Synthetic SOUL identity is retained. Sentinel MEMORY.md, USER.md and
  project AGENTS.md do not enter the cached system prompt or actual provider body.
- `ephemeral_system_prompt` is deliberately absent from the cached prompt and
  present in the actual API request. SOUL identity and current context also reach
  the request. Cache inspection alone is an invalid task-injection test.
- Init attempts model metadata lookup even though no generation was requested:
  openrouter `/api/v1/models`, custom `/v1/models`, `/models`, `/api/show` in this
  retained version. The controlled503 path completes. Constructor flags are not
  a promise of zero initialization IO; isolated execution must enforce it.
- A plain synthetic final answer returns through the actual turn facade; this is
  not an actual channel send or a quality assessment.

The first two exploratory invocations failed an incorrect assertion about the
cached ephemeral prompt and recorded blocked DNS attempts. They do not demonstrate
a Core bug. The next corrected HTTP-controlled boundary invocation passed.

## Canonical Alive -> real host -> shadow/reopen/withdrawal

The integrated fixture uses canonical journal/projections and synthetic testkit
provenance, not arbitrary prompt strings alone:

1. A user-explicit typed interest, active user-admitted commitment, discovery and
   attributed prior delivery/reply are registered in separate retained stores.
   Another owner's typed interest is also present as a negative control.
2. The existing AutonomousCycleRuntime's non-executing planning builds its current
   view. Its callback constructs a fresh actual AIAgent session with no old history
   and no tools. Its task prompt is ephemeral, alongside native synthetic SOUL.
3. Captured provider requests contain the current owner's interest, commitment,
   discovery and literal attributed feedback, but not the foreign interest.
   A controlled abstention becomes a shadow silence through the existing runtime.
4. Reopening the same completed operation adds no provider call.
5. Revoking consolidation consent and forgetting the typed interest removes both
   from the next newly identified operation/request. Commitment/discovery remain.
   A new native session does not resurrect erased inputs from the old conversation.
6. Action-attempt, dispatch-start, memory-proposal and preference-observation counts
   do not increase beyond fixture setup. No native profile file contains the two
   removed sentinels in this run. This last scan is not a complete physical-forgetting
   guarantee for a real host, backups, external providers or arbitrary future Core.

The final expanded Linux invocation is terminal PASS for both markers:

```text
HERMES_ALIVE_NATIVE_CONSTRUCTOR_PROMPT_BOUNDARY_OK
HERMES_ALIVE_NATIVE_SHADOW_SOURCE_BOUNDARY_OK
```

It uses three fake provider replies total (one boundary, two shadow), zero actual
model calls, zero actual sends and zero DNS/connect attempts. It uses the complete
retained current kernel package/Core dependencies, not a fresh installed device.

The first composed invocation also exposed two fixture mistakes: importing a test
helper ran that module's unguarded suite, and a new policy update incorrectly used
revision0 despite a seeded policy. The probe now constructs its small agenda fixture
directly and reconciles/uses the actual policy revision. Neither failure is hidden
as a model or production defect.

## Model provenance: do not infer more than the host returns

Another real boundary failure was the test assuming `served_model` equals the
completion JSON body's model. In the inspected Core it is a routing-proxy response
header (or explicit Core fallback route). Without those headers the actual native
turn reports model=synthetic-model and served_model=null even though the fake body
reports synthetic-returned-model. That distinction is explicit in Core's
`agent/served_model.py`, not proof the foreground production footer is defective.

The shadow test adapter obtains its model from the **controlled physical response
body recorded by this diagnostic**, not from that configured route or a guessed
fallback. This is deliberately a diagnostic adapter, not a ready production
attribution bridge. Actual adoption needs scoped completion evidence (for example a
qualified post-API lifecycle observation), accounting for multiple requests,
streaming, fallback and transformations. No global last-model shortcut is allowed.
Enhance remains Qoder-owned; no Core or Enhance change follows this observation.

## Decision and remaining requirements

The actual host can be exercised with Alive's retained sources and current-context
withdrawal without reopening the user's foreground session. This removes one
integration uncertainty; it does not solve the wording/appropriateness defects or
complete a long-lived agent. Do not activate this diagnostic adapter in production.

Next qualify a scoped host-call boundary with recoverable operation identity,
actual completion provenance, cooperative cancellation and provider limits before
real-model shadow comparisons. Preserve current consent/freshness/owner checks
across the await. If direct contribution replaces intermediate plans, define how
source support and current action authority apply without inventing a new FIFO.

The original full objective remains active: sustained agenda and layered memory,
useful longitudinal decisions and silence, attributable outcomes, cautious reflection
learning, external-memory integration, complete erasure, migration/rollback,
installation/upgrade/reinstallation and production acceptance. This probe does not
prove external Halo integration, authenticated live ingress, Windows support,
full installed lifecycle, real-model quality or real channel behavior.

Actual cumulative usage remains290 logical/304 observed async HTTP starts; fake
calls above do not increase it. No main merge, release, deployment, production
restart or changes to models/other plugins/network occur in this stage.
