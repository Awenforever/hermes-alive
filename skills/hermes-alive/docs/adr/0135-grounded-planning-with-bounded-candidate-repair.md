# ADR 0135 — Grounded planning with bounded candidate repair

Date: 2026-10-15

## Integration

PlanningRuntime now has an explicit isolated-qualification `grounding=True` mode.
Before framing/selection it reviews each proposal against canonical source,
explicit context, learned advice and typed expression history. Unsupported or
uncertain proposals cannot simply pass through. Independently supported proposals
remain eligible even if another review/provider fails. If there are no eligible
proposals and a review is unresolved, raise an explicit problem, not successful
silence. Actual negative judgments can lead to silence.

Corrective review receipts give the interpreter one bounded repair generation,
limited to affected agenda items. Original supported proposals remain; repaired
proposals receive their own source reviews before selection. Repair failure does
not erase original supported choices; its disposition is reported. At most two
interpretation generations and eight source reviews exist per operation. This is
an operation-count bound, not a hard latency/cost bound or semantic truth proof.

Corrective input comes only from current retained review findings/snapshots, not
arbitrary host/model text. It is advisory, not new world facts or permission.
Its event IDs and digest are bound to interpretation start and checked on await
and recovery. A review of an already repaired interpretation cannot open another
repair chain. Candidate/source/meaning validation still follows the proper
original or repair receipt. Source and review/context changes refuse stale use.

Completed work reopens without new provider calls. Started/uncompleted and failed
reviews/repair generations are not implicitly retried. Cancellation propagates.
Grounding mode/model/independence requirements bind the planning operation so a
reopen cannot silently bypass the mode. After selection, retained review evidence
and current trusted model-family mapping are checked again.

## Model responsibility

Review model defaults to the same inherited/configured model capability, with
optional explicit selection of another Hermes-configured model. No Qwen, USTC,
user preference or platform is a public dependency. Correlated review explicitly
records `independent_review=false`; it cannot satisfy the existing strict
independent-review reader. Strict mode requires a trusted family resolver and
actually different resolved models/families. Review is always model judgment,
never user confirmation, delivery authority or verified world truth.

The older ungrounded research path remains identifiable, not silently rewritten
on reopen. This is an opt-in integration during qualification, NOT the final
public activation policy or an installed production hook. Activation still needs
real-model end-to-end qualification and migration/rollback review.

## Evidence and remaining scope

Windows and isolated Linux synthetic tests exercise repaired selection, retained
good proposals after another rejection, repeated rejection/silence, all-provider
failure, partial review failure, cancellation/reopen, strict same-family refusal,
repair-provider failure without losing a good proposal, and refusal to reopen
without grounding. The existing expression fixture also runs grounded planning
through retained final expression/review and no-spend reopen. Original planning,
opportunity and source-support/history regressions pass. Linux uses minimal
current overlays over retained dependency modules, not fresh-install proof.
An initial fixture incorrectly assumed silence candidates had content dictionaries;
the fixture was corrected, not the model/runtime failure boundary.

No real model calls or channel sends this turn: totals remain 110 logical / 123
observed async HTTP starts. No production changes or public release. Next use real
models for the full grounded decision/expression chain, including failed/slow
critic and actual retained error repair. Final expression can introduce claims
after draft review; final-wording grounding and its single-family/independence
semantics still need integration/qualification. Keep longitudinal utility,
pending-intent deduplication, attributed delivery/feedback/memory/agenda/learning,
portable lifecycle, migration/rollback and full production acceptance open.
