# ADR-0162 — Native feedback budget and prospective longitudinal failure

Date: 2026-10-16. Status: real-model interpretation observed; NOT clean acceptance.

## Actual integration defect

FeedbackSynthesizer calls the shared model interface with timeout=40. The new
native callers did not accept that argument, so the native feedback path could
fail before inference despite previous native opportunity/alias/fallback tests.
Those tests did not cover interpret_feedback, and must not be read as full
learning-chain qualification.

Native host/worker callers now admit a bounded optional per-invocation timeout.
It can narrow but not extend the owned worker lifetime or its native conversation
budget. Invalid/nonfinite/bool timeouts reject before resolution. For timeout40
under lifetime90 the owned child lifetime is45 and conversation budget40; a
timeout120 under lifetime60 still yields lifetime60/budget55. The protocol test
checks these values and captures the actual ManagedModelProcess/request pair,
not only a helper return. Existing protocol/cancellation and host caller tests pass.

## Prospective actual-model experiment

`probe_alive_native_longitudinal.py` runs real Core/native child/caller and
FeedbackAssimilationRuntime/OpportunitySynthesizer with a synthetic owner and
fictional public material. It reopens the journal/synthesizer between phases.
It does not run selection, grounding review, final expression or dispatch.

The operator's explicit private model-only export inherits the existing configured
primary and official fallback. This isolated export is not proof of automatic
production-host scope/grant capture. No model configuration is changed. Inputs
exclude private chats/memory; a generic synthetic identity is installed in the
private worker. Outputs are private experiment evidence, not a message to a user.

Evidence root:
`/tmp/hermes-alive-installed-RJbQNAiD/native-longitudinal-real-20261016-r1`.
The process completed, its --rm container is absent, pending_workers=0. The
temporary model-profile.json was removed and absence verified after terminal
state. Do not regenerate it or restart this completed experiment on continuation.

Four logical native invocations completed, each reporting deepseek-flash. The
experiment did not instrument every physical HTTP attempt; do not invent a new
physical count or infer which provider endpoint from the shared model label.
No WeChat/email sends occurred. Prior real logical count290 becomes294 if that
prior counter remains authoritative; prior observed physical304 remains a prior
observation, not a current total.

Observed, not an independent semantic grade:

1. Feedback interpretation distinguishes liking repair topics from disliking long
   delivery, quotes the user and retains uncertainties about durability/scope.
   Its internal interpretations remain advisory, not automatic profile changes.
2. After feedback, a concise repair-guide candidate is generated and explicitly
   discloses that the material/link are synthetic placeholders.
3. With a newer explicit topic-pause memory, the model abstains and explains why
   this overrides older positive topic feedback. It does not recast the pause as
   permanent dislike or invent a time to resume.
4. After the operator explicitly withdraws that memory item, a concise candidate
   returns. Withdrawal is not a model-inferred permission to send; no execution
   authority is granted.

## Important failure, kept open

The fourth draft omits the material qualification that this is fictional
experiment material, while its own risk rationale falsely says the synthetic
nature was retained. The parser accepts the candidate (rejected_count0). This is
direct evidence that structural acceptance and a model's self-assessment do not
establish source fidelity. The series is NOT a zero-error round or production
readiness evidence.

Do not add a synthetic/example.invalid keyword rule or retrospectively append
missing words to make this run pass. The general problem is losing material
source uncertainty between interpretation, recipient meaning and final wording.
The next experiment must exercise the existing versioned recipient-plan and
source/purpose-review/revision pipeline, with the exact source and an actually
qualified independent family when required, then inspect final recipient wording.
Default shadow interpretation options are not proof that the NativeCognitionHost
execution configuration has enabled and qualified every such stage.

Also test genuinely new real/public materials and multiple kinds of material
qualification, time shifts, consent withdrawal, erasure, agenda outcomes and
feedback across restarts. The persistent full objective remains memory/agenda/
decision/outcome/reflection/learning, Halo, forgetting, migration/rollback,
portable lifecycle and production acceptance, not just this interpretation slice.
