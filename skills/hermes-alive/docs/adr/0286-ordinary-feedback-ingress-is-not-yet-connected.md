# ADR-0286 — Connect ordinary feedback, not just seeded interpretation

Audience: maintainers and QA. Purpose: record an observed integration gap and
the implementation/acceptance boundary for closing it.

Date: 2026-11-05. Status: gap reproduced; product integration pending.

## Evidence

The configured Kernel path in `admitted_inbound_bridge.py` calls
`record_configured_input`, which validates the current route and records a
metadata-only wake. It neither retains replies nor associates them with Alive
actions. The older shadow capture uses another identity contract and also
does not produce ordinary user feedback outcomes; it is not a drop-in fix.

`FeedbackContextReader` and `FeedbackAssimilationRuntime` consume validated
user response outcomes. Earlier composed feedback tests seed synthetic
historical response outcomes. Their interpretation/recovery/erasure proofs
remain bounded component evidence, not evidence of everyday learning.

`run_core_feedback_ingress.py` installs the plugin, uses actual Core 0.22.5
setup/confirmation and route binding, then dispatches three synthetic owner
inputs through actual `run_post_admission_hook`. Synthetic retention and
consolidation consents are present; no response outcomes are preseeded. All
three inputs remain unconsumed and are observed, but no feedback body, user
outcome or readable feedback context results. This diagnoses missing integration.

The supplier hook snapshot omits quote metadata even when the incoming event
has it. Arbitrary extra reply fields, temporal adjacency or a model-selected
recent action must not become proof of an actual quoted reply. This probe
starts at the post-admission dispatcher; preceding real-account authorization
and physical delivery are not independently qualified.

## Decision and implementation direction

Prioritize ordinary feedback integration before more share-style prompt
iterations. Reuse the journal, erasable vault, Core-scoped continuity and
feedback interpretation/erasure machinery. No new profile database, general
transcript reader, transport queue or model router.

- **Observation:** capture needs guided inbound-retention consent. Outbound
  retention, interest profiles and external-memory read permission do not imply it.
- **Association:** a verified quote and a main-agent semantic association have
  distinct provenance. Preserve the latter as a delegated interpretation;
  do not manufacture explicit reply/correction/approval evidence. Missing or
  ambiguous targets remain unassociated; the next message is not proof.
- **Learning:** interpret only with separate consent. Keep original scope,
  qualifications and contradictions. A sample-specific length opinion is not
  a permanent interest or an always-short rule. It grants no operation authority.

Core already presents scoped retained shares to the normal main turn. Prefer
that turn for semantic association, using a task-bound share reference and exact
current-input evidence, over a separate model invocation on every message.
This is an integration proposal, not an implemented or qualified interface.
Normal conversation and Enhance's independent token/FIFO ownership remain intact.

Guide new users through optional capture/interpretation. Existing installs remain
unopted-in; upgrades must not expand old consent. Unsent QA drafts plus this
conversation's reviews must not be imported as physically delivered feedback.

## Completion evidence required

Use an installed public-source plugin and actual Core normal turn, a real local
adapter submission, then fresh admitted feedback. Do not preseed response
outcomes or relabel submission certainty as a human having seen the message.
Cover immediate/delayed feedback, multiple possible targets, topical followup
without evaluation, quotations, situational refusal, correction and contradiction.

Verify opt-out, foreign scope, reset, missing/expired source, replay, revocation
during interpretation, cold recovery and erasure of originals/dependent advice.
A subsequent full Native cycle must receive correctly scoped evidence. Actual
models must demonstrate useful adaptation while preserving truthfulness, depth,
unrelated exploration and normal conversation. No automatic permanent-interest
update or operation grant follows from this path.

The known-gap probe must eventually become a full intake journey; retaining its
zero-outcome expectation is not the product goal. No sharing-quality credit.

## Diagnostic run record

r815 completed: three observations, zero retained feedback bodies, zero user
outcomes/context items, zero model calls and sends. r812 failed on the probe's
embedded-module lookup; r813/r814 counted the activation observation among the
test inputs. Failed traces are retained. r815 uses a pre-input event-ID baseline.
These fixture repairs do not repair the product gap.
