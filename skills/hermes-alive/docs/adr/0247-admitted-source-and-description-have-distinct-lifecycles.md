# ADR 0247 — Admitted source and description have distinct lifecycles

2026-10-26, Codex. Development qualification; not production acceptance.

## Problem

A real main reply called an interpreted agenda constraint “original wording”.
Passing the current work request to Core fixes execution context but cannot
recover the initial instruction or prove that a description preserves its
qualifications. Source representation needs its own truthful lifetime.

## Decision

New follow-up intake/management guidance discloses retaining the exact current
admitted request, bounded to 6000 characters, in the existing encrypted vault for
the selected item lifetime. The journal contains a signed content reference and
keyed fingerprints, not plaintext. This is purpose-bound request evidence, not
collection of casual conversation. Old grants do not gain source retention.
Oversized messages are refused without truncation or reconstruction.

Keep the model-interpreted agenda description distinct. Ordinary inventory
reports source availability; exact item lookup can return the original. Native
cognition, factual source excerpts and follow-on context preserve that distinction.
The original can reveal omitted constraints and quotations; it still does not
convert delegated semantic interpretation into literal approval or execution
authority. Source interpretation must remain open to clarification and correction.

Carry the signed intake-recording timestamp with the original. It is explicitly
not a sender timestamp: relative dates cannot be resolved by silently pretending
the two are identical. Preserve explicit interpreted deadlines and clarify any
material remaining ambiguity.

## Historical authority is not current body availability

An independently exercised rebuild counterexample against r145 showed that
requiring body decryption while validating historical admission erased an item
from the rebuilt projection after its original source was removed. The cached
projection had hidden this loss. Keep that failed evidence.

Verify the historical owner/configuration/grant/signature, exact source-reference
identity and retention bounds without requiring current body availability.
Decrypt and validate body fingerprints only for source retrieval. Rebuilding must
preserve the admitted item's structural state while reporting its original as
unavailable. Erasure must never restore an original from the interpretation.
The cold-process test verifies both a retained original and an independently
erased source after rebuilding with unchanged original keys.

Erasing only source ciphertext is distinct from forgetting the whole item. It
does not erase the interpreted item or revoke a previously issued grant. Complete
user-facing forgetting must cover dependent retained content and the appropriate
item, source and Core records. That dependency/migration matrix remains a release
gate; these tests do not claim complete erasure across every store or channel.

## Qualification scope

Installed Core/Alive tests cover exact lookup, inventory minimization, expiry
refusal, source erasure, projection replay and a new process. Controlled Native
prompts receive the separately labeled original alongside current work facts.
A three-turn inherited-DeepSeek test clears actual conversation history before
each source query: it quotes the retained original exactly, then reports it
unavailable after deletion. Its replies remain verbose and attempt an unsupported
reference-handle lookup; correct source fidelity in this case is not a general
conversation-quality verdict or a useful-sharing round.

Continue with task/deadline revision, meaningful source use in actual decisions,
independent results and later actions, safe forgetting/migration and distribution.
Do not turn this into another chat archive, source store or model executor.
