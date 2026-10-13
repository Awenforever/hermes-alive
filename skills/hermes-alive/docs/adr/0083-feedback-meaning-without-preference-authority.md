# ADR 0083 — Interpret delivered-message feedback before proposing learning

Status: opt-in research stage with synthetic structural tests. No real model
semantic qualification or automatic learning authority. Not a production feature.

## Why this stage exists

The previous learning tests supplied an already interpreted topic/presentation
target and direction. They proved bounded influence and owner control, not the
ability to understand the user's actual reply. The personal-owner checks in ADR
0081/0082 cannot decide whether a reply is politeness, a one-off circumstance,
an enduring preference, a factual correction, or several conflicting meanings.

`FeedbackSynthesizer` now accepts an attributed owner outcome, not an arbitrary
model-produced summary. It binds the original complete retained input to an
authenticated-shaped successful delivery preceding that input and resolves the
exact signed executed text, including a confirmed expression when present.
Its caller supplies Hermes' model client: inherited model/fallback/credentials
remain Hermes' responsibility. No public model/channel/personal content default.

## Meaning representation, not a keyword classifier

The model interprets the complete reply against the delivered text. It may return
several separately qualified topic, presentation, timing and interruption signals,
or no signal. Descriptive keys/options remain open; there is no sentiment keyword
matching, fixed preference vocabulary, weight update or guessed permanent fact.
Each hypothesis retains its literal reply quote, situational/durable/uncertain
scope, direction and limitations. Questions, politeness, factual correction and
ambiguous targets should remain distinct from positive useful-benefit labels.

The diagnostic receipt always states automatic_learning_authority=false and
semantic_accuracy_proven=false. It cannot create preferences, approved reflection,
profile facts, reminder jobs or messages. No hook/command/default-runtime wiring.

## Consent, causality and recovery

- Latest raw owner retention and model-consolidation consents must still be active;
  cached enabled flags cannot override a later withdrawal. The retained source is
  bound to the current retention epoch, inbound direction, owner, sensitivity,
  bounded expiry, digest and explicit non-truncation. Existing 500-character hook
  evidence marked truncated is not silently treated as a complete reply.
- Delivery must precede the input in both journal order and observed clock.
  A later success cannot retroactively identify what an earlier reply was about.
- Executed content is verified against its signed action contract, not today's
  default model, most recent message or an unconfirmed alternative expression.
- No model call before valid context. Started/completed/failed records retain
  actual model/provider and only structural metadata in the journal. Interpretation
  prose/quotes are encrypted, with a retention bound inherited from the raw source;
  no complete private input snapshot is duplicated into the output bundle.
- Model wait and recovery revalidate the original context/consents. Changed,
  erased or unavailable evidence blocks completion/recovery. Spent operation IDs
  cannot silently retry; failed/completed conflicts reject recovery.

## Synthetic evidence and explicit limits

Local Python 3.14 tests exercise mixed topic-interest and situational-interruption
signals, ordinary USER_REPLIED input without fabricated explicit-feedback metadata,
missing consent, no delivery, receipt arriving too late, truncated input, exact
executed text, private journal hygiene, idempotency, fabricated quotation rejection,
consent withdrawal during a model wait and input erasure before recovery.
Existing learning-context, preference, reflection and outcome suites also pass.

The generated output in these tests is a deterministic fake, not an empirical
model-quality result. A deliberately wrong durable-topic interpretation with a
valid literal quote still passes structural validation. This counterexample is
intentional: provenance/schema success does not establish semantic correctness.
The actual primary/fallback routes and independent review must qualify meaning
across public synthetic cases before any automatic learning pathway is considered.

Real gateway owner authentication, quoted delivery linkage and full untruncated
input capture remain unqualified. Actor equality and synthetic authenticated-shaped
receipts do not prove those capabilities. Individual source erasure invalidates
recovery but does not yet propagate physical erasure to every derived encrypted
interpretation; the general derived-copy forgetting requirement remains open.
The caller must supply the correct shared content vault, not assume similarly
named default vaults are interchangeable.

## Next work without narrowing the objective

The five focused suites also pass in NAS managed Python 3.13 with network disabled
and only the owned scratch tree mounted read-only. Input tree
`1590f881bc3da5df5df5527c0aa52ead54326999`; archive SHA256
`2be4be6dddea670f5bdd4a3ca0cf51dac6b5c093caccd60a350f0ac5fd4b72b3`.
Container `alive-feedback-meaning-offline-20261013-r1` exited 0, started
`2026-10-13T15:37:13.195878401Z`, finished `2026-10-13T15:37:18.171024639Z`.
No code changed after this snapshot; only this evidence note and manifests follow.
This is focused testing, not full installation/lifecycle or semantic qualification.
Production remained running, original start `2026-10-11T07:43:25.630569081Z`.

Run prospective model comparisons on varied public scenarios (mixed sentiment,
irony, politeness, factual correction, relative timing, situational exceptions,
topic/reference ambiguity and injection-like text); distinguish wrong, uncertain
and useful interpretations independently from parser success. Decide how qualified
tentative learning integrates without demanding per-message human babysitting or
silently turning model suggestions into durable user authority.

Keep natural expression quality, authenticated onboarding/feedback, actual delivery
and long-term benefit, layered/external memory, agenda/adaptation, migration,
forgetting/rollback, portable lifecycle and real production acceptance in scope.
