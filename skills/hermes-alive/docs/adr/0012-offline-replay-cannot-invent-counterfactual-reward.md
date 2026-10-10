# ADR-0012: Offline replay cannot invent counterfactual reward

Status: accepted for the shadow kernel

## Decision

Alive evaluates learning on time-separated, factual action episodes. A
prediction must have existed no later than the action attempt and may cite only
earlier journal evidence. Feedback recorded after the evaluation snapshot is
excluded. Missing feedback remains unknown.

Calibration may be compared only on the same executed-attempt cohort and the
same explicitly labelled outcomes. Replay may measure delivery reliability,
usefulness, interruption regret, factual error and user-control violations when
the journal contains compatible evidence. It may not assign a reward to an
action that was never executed or claim that a different action-selection
policy would have been superior without randomized or otherwise defensible
overlap/propensity evidence.

A correction is not automatically an “unhelpful” label, and dismissing an item
is not automatically interruption regret. Those conclusions require explicit
feedback or a typed downstream result; otherwise the narrower observed fact is
retained without inventing sentiment.

## Why

Historical logs reveal what followed the chosen action, not what would have
happened after an unchosen action. Treating non-response as rejection, future
evidence as a feature, or model-written retrospective labels as facts would
make longitudinal improvement look better while making the assistant less
trustworthy.

## Consequences

- Held-out calibration can qualify estimators and deliberation assessments.
- Operational and safety rates remain directly observable for executed work.
- Strategy reports explicitly deny counterfactual policy claims.
- A future live canary or defensible off-policy design is still required before
  replacing the production selection policy.
