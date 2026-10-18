# Personalized discovery: bounded delivery plan

Status: planned, not deployed or accepted. Reviewed: 2026-10-18.

## Product outcome

Alive should notice something genuinely worth sharing with this recipient,
explain its interest naturally, remember meaningful feedback, and remain silent
when nothing is worthwhile. Source count, successful model calls and schema
validity are not substitutes for this outcome. Interests are open-ended semantic
descriptions, not an exhaustive fixed topic taxonomy.

## One thin end-to-end milestone

1. Connect explicit onboarding/preferences to durable per-owner memory and actual
   discovery/selection. Retain origin, time, scope and corrections. Public defaults
   must be neutral; do not ship the developer's preferences or accounts.
2. Separate durable explicit preferences, tentative inferred interests and temporary
   task context. Model-assisted extraction uses conversational attribution: quoted
   mail, troubleshooting, hypothetical examples and third-party statements are not
   automatically personal interests. Repeated evidence may strengthen a hypothesis;
   one mention must not silently become a permanent trait. No reply is ambiguous,
   not negative feedback. Topic, medium, depth, frequency and timing are separate.
3. Retrieve relevant memories when discovering AND choosing; do not merely decorate
   the final prompt with a profile. Apply correction/withdrawal on later cycles and
   after restart. Learned relevance never grants sending or private-data access.
4. Admit a small, qualified domestic source set alongside international primary
   sources. Existing collector presence is not qualification. Prefer relevant
   domestic candidates modestly for opted-in network/source preferences, while
   retaining quality and diversity. Record collection success, source freshness,
   recipient accessibility and evidential confidence separately. A server fetching
   a page does not establish that the recipient can open it. No access-control
   circumvention or invented mirrors; disclose inaccessible originals where needed.
5. Let the model judge novelty and recipient value across research, tools, company
   developments, videos, history and other user-defined interests. Do not make
   papers the default output or fill a domestic quota with irrelevant trending
   items. Preserve some bounded exploration rather than a permanent filter bubble.
   Aggregate duplicate coverage of the same event; frequency never increases just
   because more sources exist. Distinguish verified reporting, analysis and rumor.
6. Close the actual feedback loop with attributed natural replies and existing
   memory/outcome primitives. Keep external memory behind an adapter with explicit
   ownership, erasure/export and retrieval contracts. Do not claim an external
   memory integration is active merely because a dependency or directory exists.

## Finite acceptance batch

Before expanding sources or architecture, run a held-out longitudinal batch with
at least these scenario families: explicit cold start; noisy task/quoted content;
changed or withdrawn preference; no response; repeated event coverage; research
versus non-research interests; accessible domestic versus unavailable original;
rumor versus verified fact; and restart with retained corrections. Compare the
same candidate pools with and without profile context, and inspect reasons and
actual final messages. Different family review is useful, not ground truth.

Keep technical error-free runs separate from usefulness assessment. Record each
wrong inference, misleading claim, irrelevant choice and unwanted repetition;
do not label silence or a model's approval as recipient satisfaction. Complete
the previously required ten clean full-chain rounds on fresh scenarios before
deployment acceptance, with usefulness checked separately. Production observation
and owner feedback follow a separately authorized deployment, not test-message
spam. If the batch exposes poor value, revise the failing stage and repeat the
affected holdouts; do not indefinitely add abstractions or narrowly ban phrases.

Initial non-goals: a new graph database, reinforcement-learning training service,
exhaustive web coverage, mandatory account login across all communities, or a
second platform queue. Reuse the existing journal, protected memory and host
transport. Fix safety/data loss and measured user-facing blockers first.

## Research basis, not acceptance claims

- [Mem0](https://arxiv.org/abs/2504.19413): extract, consolidate and retrieve salient
  conversation memories; adopting the principle does not require its service.
- [LongMemEval](https://arxiv.org/abs/2410.10813): evaluate temporal reasoning,
  knowledge updates and abstention, not just recall of a stable fact.
- [Generative Agents](https://arxiv.org/abs/2304.03442): observations, reflection
  and planning inform behavior; a research architecture does not prove this
  product's recommendation quality or safety.
