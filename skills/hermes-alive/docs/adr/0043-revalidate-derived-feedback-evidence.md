# ADR-0043: Revalidate feedback behind reflection and learned estimates

Status: accepted for shadow projection paths; transport audit remains pending

## Decision

Direct SQL consumers cannot bypass ADR-0041/0042. Expose the user-attribution
predicate as a stateless journal check so it can be reused inside existing
projection transactions without constructing another projection or running
schema initialization under a write lock.

Reflection proposal admission checks each original outcome event. Acceptance
and current reflection reads also recheck the joined outcome evidence: it
must be complete, belong to the reflection's user, agree with original outcome
identifiers/kinds/attempts and satisfy current user-attribution rules.
Rejection and retraction remain possible even when evidence is invalid.

Explicit-feedback preference admission rechecks original outcome attribution.
Accepted-reflection preference admission rechecks that reflection's outcome
evidence. Every estimate read reruns source validation for each observation
before adding its bounded weight. A source reflection must remain accepted
and unexpired at the requested observation time; its expired evidence cannot
continue influencing a longer-lived signal.

Bind cached observation identity, source, target, direction, weight and expiry
to its original journal event before accumulation. A changed cache weight is
not new user evidence and cannot alter the estimate.

Do not delete old accepted reflections or learned observation events merely
because their evidence fails current rules. Exclude invalid influence and
retain historical records for explanation and deliberate rebuild.

## Evidence and limits

An integration regression inserts an old unlinked feedback outcome, then
emulates old admission to produce accepted reflection and active preference
caches. Without rebuilding or deleting history, current reads exclude the
reflection and its invalid feedback weight. Original proposal/observation
events remain. A separate test expires the source reflection before its signal
and proves that only still-valid explicit feedback contributes.

The shared predicate certifies user attribution, not non-user transport/task
receipts. Generic receipt causation and full cache-to-journal integrity outside
these feedback bindings remain separate audits. This milestone does not prove
longitudinal learning usefulness, live feedback ingress or production readiness.

On 2026-10-12 outcome, reflection and preference-learning regressions passed
on Windows and in an isolated production-image container with no networking
or production-data mounts. Production was not deployed or restarted.
