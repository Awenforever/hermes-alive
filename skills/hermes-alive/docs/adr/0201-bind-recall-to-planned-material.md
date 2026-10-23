# ADR0201 — One bound material pool for recall and interpretation

Status: implemented; qualification pending

## Actual mismatch

The semantic recall query used the ordinary collector-ranked32-source view.
Interpretation independently used a chronological fairness cursor and could also
prioritize a verified research-read group. These views need not contain the same
material. A model can choose sensible memories for the wrong set of resources;
good JSON and successful recovery do not detect this relevance failure.

The initial flat-priority fixture did not exercise that difference. A skewed
collector-priority fixture does: earlier low-ranked observations belong in the
fair window but not the ordinary ranked view. Do not describe ordinary ranking
as necessarily newest-first, or turn collector rank into recipient relevance.

## Single current pool, not a topic gate

Extract the existing source-pool assembly without changing its historical
default: fairness cursor, owned commitments and a verified research group retain
their original ordering. New semantic planning captures a material descriptor
before inference: original ordered source IDs, research focus IDs, fair-pool IDs,
cursor and journal frontier. No body text or preference is added to the journal
descriptor, and no action/disclosure authority is granted.

An explicitly bound empty pool skips recall entirely: no model spend and no
private feedback-consent requirement just to establish that no material exists.
Retained empty completion is still invalidated when new material becomes available;
never turn that old result into proof that a later world remains empty.

Recall resolves that descriptor instead of querying an unrelated ranked view.
Interpretation receives the same descriptor. Later prompt packing may admit only
a complete bounded prefix: the recall pool is available planned material, not a
claim that every item was written about, shared or even admitted to that prompt.
Do not remove difficult source qualifications to force the whole pool to fit.
The original fairness scan advances only over the actually admitted prefix.

Validate the entire reference scope for owner, sensitivity and pre-freeze
chronology before body access. Resolve each current original observation; never
silently replace missing, expired, withdrawn or erased material with new arrivals.
Research provenance still comes from actual completed read receipts/current
inquiry, not a caller-supplied hostname or asserted focus label.

## Dependency lifetime and recovery

All pool material could affect recall, including a tail not later admitted to
interpretation. Check it before/after model waits and when resolving retained
interpretation. Derived proposal/recovery content cannot outlive the shortest
pool source. Erasing an unadmitted dependency invalidates dependent use rather
than leaving a seemingly unrelated completed proposal valid.

New arrivals stay available for a later operation; they do not change the query
of an already bound operation. Completed work reopens without inference even
after the fairness cursor advances. Existing semantic planning records without
the new descriptor keep their original query and source behavior: do not charge
another model call to retrofit a historical operation. Corrective interpretation
retains its already admitted original sources, never expands back to an unused
tail merely because that tail appeared in initial recall.

This descriptor is not a snapshot of the entire world or all user state.
Existing current owner policy, explicit context, literal feedback, inquiry,
intent and source validations still apply. It is not execution permission.

## Evidence and remaining work

Controlled tests use real journals, encrypted source storage, projections and
planning/recovery APIs with synthetic callbacks. They cover collector/fairness
divergence, material arriving during recall, actual receipt-backed research pages
outside the ordinary ranked window, foreign/future-reference rejection before
body access, short-lived unadmitted dependency retention/erasure, and a frozen
pre-descriptor planning contract. They prove dataflow, not model relevance or
recipient satisfaction. Qualify canonical bytes and installed behavior next.

Synchronous-read responsiveness/physical cancellation, installed activation,
cross-cycle continuation, configured external memory, sustained agenda and
feedback/reflection usefulness, platform lifecycle/migration/rollback, ten fresh
complete clean rounds and production acceptance remain required. No production
change or completion follows from this material-consistency component.
