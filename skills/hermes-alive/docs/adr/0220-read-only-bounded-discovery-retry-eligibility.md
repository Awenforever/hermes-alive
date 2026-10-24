# ADR0220 — Read-only bounded discovery retry eligibility

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: eligibility view and candidate-reader boundary implemented; ordinary-loop wiring open.

Reuse authenticated host completion history, not another queue or lifecycle
database. V2 rejection witnesses retain exact interpretation references so the
reader can revalidate current negative proof directly, with no inference or
model-operation replay. V1 history remains untouched and is not promoted into
this new scope. Identity, wording/selection, source ancestry and current
sensitivity checks remain mandatory before protected content is resolved.

New cycle openings capture an authenticated owner event frontier. A retry view
requires matching host configuration and no newer owner input/policy. Inbound
wakes by authorized subject even when its normalized actor differs; no body is
read to establish that fact. Verify inputs again after reading. Legacy openings
without a frontier cannot justify a hold, and paused policy/pending model work
cannot produce an eligibility capture.

When configured with the existing bounded reconsideration window, completion
retains a retry boundary derived from the original completed review time,
capped by proof validity. Reads/restarts never renew it. The reader also checks
the one-hour maximum independently. No configured window means no implied hold.
Query usable v2 rejections before applying the history limit: ordinary quiet
cycles must not displace a still-live failure. The explicit completeness flag is
about this bounded rejection history, never all sources or the whole world.

The view holds only the selected primary discovery URL, not every related source
in a research group. Original sources remain available. New/erased source
ancestry, changed context, input/policy or expiry invalidate the old proof/hold.
Internal negative advice is neither user dislike nor permanent topic exclusion.

`candidate_evidence(excluded_urls=...)` is a separate, explicit attempt-reader
API, with exclusion before its result limit and the existing bounded material
horizon. `active_evidence`, including pinned retained proofs, remains unchanged.
Candidate exclusions never filter user-admitted commitments; mixed opportunity
ordering/reservation semantics remain the same. No persistent source/agenda
mutation, secret-bearing URL index, model/provider configuration, scheduler,
transport retry, action permission or second FIFO is introduced.

This is not completed recovery. The ordinary host still stops on content
attention and does not consume this view yet. Next wire source choice and fresh
planning to this explicit eligibility boundary, retain all facts needed for
grounding, distinguish exhaustion from silence and verify bounded continuation
with alternative sources. Do not solve it by globally parking on one rejection
or applying candidate exclusions to historical evidence resolution.
