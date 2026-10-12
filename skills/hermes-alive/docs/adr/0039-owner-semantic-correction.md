# ADR-0039: Owner-authored semantic correction with crash-safe succession

Status: accepted for shadow kernel; live activation pending

## Decision

Add `/memory alive correct-message <meaning-event-id> <atom-id> <kind>` with
replacement text on the following line. User inspection displays atom IDs.
The host-authenticated owner chooses the atom and its semantic kind. The model
does not rewrite the user's correction or infer authorization from its prose.

Only the specified atom changes. Other atoms retain their original evidence;
the new atom cites the authenticated correction event, distinguishing a user
assertion from its previous observation. Preserve speech act, sensitivity and
the original expiration. Correction does not extend retention or correct all
downstream beliefs and memories; those have their own provenance controls.

For literal-bearing kinds, protect the whole submitted text in bounded literal
chunks. This avoids guessing which date, quantity or qualifier matters. It
does not establish factual truth or replace semantic review of model wording.

## Durable protocol

1. Authenticate ownership and validate the requested atom, kind and text.
2. Store the complete successor document encrypted, with a stable keyed request
   identity and the original lifetime. This preparation is repeatable.
3. Append the original's permanent withdrawal event, binding the keyed request
   digest, encrypted successor reference and successor event identity.
4. Define the successor from that exact encrypted document and return its ID.

The permanent withdrawal is the fail-closed transition point. A failure before
it means no correction committed; an identical retry can reuse prepared
content, including the first preparation's actual creation timestamp. Neither
the original creation date nor the retry time masquerades as correction time.
A failure after it cannot reactivate the original. Repeating the exact
request after reopening the store completes the same successor definition.
A different correction of that original conflicts rather than silently winning;
later edits must target the successor. A successor withdrawn or corrected later
cannot be revived by retrying an earlier correction.

The encrypted request and successor have the same subject and expiry. Subject
erasure applies to both, and recovery cannot reuse erased content identities.
The journal contains structural metadata and keyed digests only, not the text.
Abandoned encrypted preparation can persist until normal retention/erasure;
there is no automatic background retry or live delivery side effect.

## Authority and limits

Old deterministic renders, candidates and reviews become invalid through the
ADR-0038 withdrawal check. The successor receives no selection or delivery
authority. It must be selected and reviewed anew. A changed deadline atom is
not an instruction to modify a calendar or reminder. This bounded correction
surface complements, rather than substitutes for, broader natural-language
feedback and memory correction work.

## Evidence

Tests cover foreign-user refusal, invalid atoms/text, unchanged evidence and
lifetime, repeat requests, conflicting requests, successive corrections,
failures before/after withdrawal, recovery after reopening, no resurrection,
multi-line command text, concurrent identical/conflicting requests,
encrypted-only storage, erasure during recovery and old-review invalidation.
Live user experience, discoverable message history and long-term quality
qualification remain pending.

On 2026-10-12 the correction, withdrawal, rendering, review-store and retention
tests passed on Windows and in a disposable container using production image
`hermes-agent:v0.21.3-weekly-20260918`. Network was disabled; only test source
was mounted read-only. Production data was not mounted and the production
gateway retained its original start timestamp. These are isolated execution
proofs, not live-delivery or longitudinal quality qualification.
