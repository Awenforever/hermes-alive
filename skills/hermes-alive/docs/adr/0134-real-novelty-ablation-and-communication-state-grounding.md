# ADR 0134 — Real novelty ablation and communication-state grounding

Date: 2026-10-15

## Experiment

Use six opt-in model calls per pass: unchanged evidence, substantive development,
and source correction, each with/without authenticated prior expression history.
All user preferences, organizer notices and protected histories are synthetic.
Seed generation/review is explicitly fake; only opportunity interpretation is
real. Generated history is NOT sent history. The probe asserts the exact history
entry count and no action attempts/dispatch starts. A disconnected dry run makes
zero HTTP requests. No real channels or production configuration are changed.

Both real passes use the current configured USTC main model. All 12 HTTP requests
return 200 and actual response model is `deepseek-flash`. With history, unchanged
evidence yields abstention, while developments/corrections still yield proposals.
Without history, unchanged-case behavior differs between passes. This is a tiny
ablation, not calibrated utility, stable novelty control or ten clean cycles.

## Failure, not a passing acceptance

First-pass correction-with-history says “I mentioned” despite no sends. A generic
state-evidence clarification in the second pass does not fix the underlying
problem: correction drafts still say “I noted earlier,” including a no-history
control. A control abstention invents that the user already engaged with material.
These are unsupported shared-context/user-history inferences. Counts and HTTP
success do not qualify the text, and adding another wording rule is not root repair.

## Design change

The independent source-support snapshot now includes the exact pre-interpretation
expression history, with its explicit generated-only/delivery-unknown status.
Interpretation and review distinguish internal generation, attempted action,
transport observation, receipt and user feedback; evidence of one stage cannot
establish a later stage. This extends generic evidence grounding, not a phrase
blacklist or hard-coded correction rule. Retained review prompt/snapshot digests
make old-method reviews non-current rather than silently trusting them.

Current autonomous planning does NOT yet require this review or recover a revised
draft. The diagnostic receipt grants no delivery authority. Neither a passing
shadow review nor this change authorizes production activation.

## Independent diagnostic

Using the existing USTC credentials in a model-only isolated profile, explicitly
try the user-suggested `qwen3.8-reasoner`; production main/backup are unchanged.
Two initial logical review calls start three HTTP requests: bad correction review
times out (one ReadTimeout and another request without terminal status), while
the substantive development gets 200, actual Qwen model, and `supported`.
One explicitly recorded new review operation retries only the failed sample:
200, actual Qwen model, `unsupported`, accurately identifying the unsupported
prior-communication claim. This establishes availability and two correct diagnostic
judgments, NOT latency stability, broad accuracy or mandatory Qwen dependency.

This turn: 15 logical / 16 observed async HTTP starts, including failures and an
interrupted request. Cumulative real totals: 110 logical / 123 HTTP starts. Synthetic
dry-run calls do not enter these real totals. No actual messages are sent.

Local raw synthetic reports: `work/novelty-evidence-20261015/first-pass.json`,
`second-pass.json`, `independent-review.json`, `independent-review-retry.json`.
NAS evidence stays in the corresponding `model-only-novelty*20261015*` directories
under the retained isolated test root; do not publish credentials or private profiles.
Windows expression and source-support/history checks pass; Linux uses minimal
current overlays over retained dependency modules, not fresh-install qualification.

## Next requirement

Integrate grounded critique and bounded correction/reselection into autonomous
planning/expression, then verify useful multi-cycle behavior. Do not turn one bad
candidate into whole-cycle failure, require a public hard-coded reviewer model,
or claim model judgments are truth proofs. Keep pending/delivery/feedback state
distinct, retain current consent checks, and continue agenda/memory/learning,
installation/migration/rollback and full production acceptance.
