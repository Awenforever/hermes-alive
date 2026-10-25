# ADR0231 — A bounded public-source refinement, if the evidence warrants it

Date: 2026-10-25 (Asia/Shanghai).
Status: proposal, not an implemented capability or production authorization.

One real discovery run reached a useful technical topic through a search listing,
but could not open the aggregator page. The existing exact-query and cited-link
capabilities could not independently search for its original paper or project.
A separate actual-Core public research experiment found substantive model-card,
paper and project extracts, including recovering from an unavailable HTML page.
It also demonstrated why a generic Agent loop is not a drop-in replacement: the
final composition did not finish within the requested runtime, and a requested
three-page limit did not prevent four attempted page targets. Those are failed
qualification boundaries, not reasons to change the user's model configuration.

## Decision to test before implementation

Hold the writer and its model interface fixed; compare the actual initial
listing with the actual primary extracts. Better reading must improve concrete
understanding, not merely produce a longer inventory or more confident claims.
If it does not, stop expanding this branch of work. Do not add another reviewer,
provider router, agent framework or model-specific workaround to justify it.

## Candidate contract

- New, explicit installation consent for public-topic refinement, default off.
  Existing literal-query and citation-only grants do not silently broaden.
- At most one additional public query and one bounded read group per cycle,
  sharing the existing followup budget rather than creating a recursive search.
- Query planning receives only already-public source material and approved
  public topics. Private interests, curated memory, conversation bodies, private
  inquiry rationales and feedback are excluded from that model request.
- Hermes owns models, fallback, search, extraction and URL safety. Reuse the
  current supervised model/read capabilities and retained tool evidence.
- A model's proposed query is data, not permission. Validate the current signed
  choice, owner/profile/cycle binding and consent before external disclosure.
  Preserve distinct source evidence, exact original URLs and actual read scope.
- Stop, revoke, replace and timeout must fence new work without claiming an
  unfinished physical request was cancelled. No sibling capability may hide
  pending work from the current native supervisor.
- Durable start-before-I/O and existing uncertain-outcome handling apply.
  Restart or candidate rejection must not replenish the per-cycle budget.
  Old started cycles keep their old scope. No physical delivery/FIFO change.

The exact implementation may change after the controlled experiment. An
approved design must fit these ownership and privacy boundaries without turning
the small source-recovery need into an unbounded infrastructure project.

## Required proof

Use synthetic actual-Core tests for default-off/onboarding, source-only model
input, query/read budgets, lifecycle revocation, changed owner context, replay,
pending work and failures. Then run fresh real-source complete-chain cases with
original output and realistic followup. Neither a successful tool call nor this
proposal counts toward the ten useful error-free rounds. Ordinary feedback,
memory, fleet lifecycle and production acceptance remain separate open work.
