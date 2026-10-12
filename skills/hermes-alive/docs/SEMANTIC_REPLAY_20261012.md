# Real reviewer replay — 2026-10-12

Scope: isolated reviewer calls over the public Chinese/English/Japanese seed.
This is preliminary empirical evidence, not production qualification or an
evaluation of a complete renderer/reviewer pair.

The supported production image ran with the profile mounted read-only. The
runner copied only `config.yaml` and `.env` into a private temporary profile;
sessions, memories, cron state and channel credentials were not operated on.
No gateway restart, outbound message or production configuration change was
performed. Hermes owned auxiliary routing and fallback.

## Observations

The inherited route resolved to `custom:ustc`, response model
`deepseek-flash`. Twelve distinct cases were called exactly once, in two
batches (three faithful controls, then nine risky cases).

| Measure | Observation |
|---|---:|
| Completed reviews | 12/12 |
| Faithful paraphrases accepted | 3/3 |
| Risky candidates accepted | 0/9 |
| Focal risk classes detected | 9/9 |
| Error-class precision | Not estimable from this seed |

Some responses added related classifications: contradiction also marked
polarity, negation removal also marked speech act, and uncertainty removal also
marked polarity. These may be debatable annotations; they are not established
false positives simply because the seed named only one focal class.

The seed is now explicitly marked `targeted_non_exhaustive`. Saved batches can
be combined and rescored without calling a provider again. Reports retain all
failed cases, withhold metrics for incomplete cohorts, refuse duplicates and
label their scope. Production qualification is always false for this runner.

A second requested selector, `qwen3.6-chat`, returned
`PermissionDeniedError` for all three faithful controls. The actual second
model could not be established. This is a route-availability limitation; it
does not justify modifying the user's model configuration or assuming a
second independent reviewer exists.

Evidence: [DeepSeek batch report](evidence/deepseek-seed-20261012.json) and
[Qwen route report](evidence/qwen-route-20261012.json). Reports retain a
canonical fixture digest, actual successful response models and structural
results; they contain no credentials or private mail/chat content.

## Next evidence required

- An available, verified second model family for full comparison calls.
- A larger held-out corpus with exhaustive human judgments and naturalness
  assessments; this 12-case seed is insufficient.
- Full candidate/selection/review persistence and recovery in real calls.
- User correction controls, longitudinal shadow behavior and bounded canary.
