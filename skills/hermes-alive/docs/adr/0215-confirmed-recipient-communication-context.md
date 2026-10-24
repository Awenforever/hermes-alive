# ADR0215 — Connect confirmed recipient choices to existing cognition

Date: 2026-10-24 (Asia/Shanghai)
Status: implementation under qualification, no quality pass.

Actual activated-chain review found English restatement despite Chinese material
and an unnecessarily defensive conversation. The renderer already accepts a
language, and both discovery and expression already read explicit owner context.
Ordinary setup supplied neither. Do not solve a missing recipient contract with
case-specific phrase bans, forced intimacy, more judges or source-language guesses.

Setup now offers optional language and communication-preference choices. Defaults
contain no developer persona: language follows Core's locale, with an explicit
Alive-only language override when chosen; free-text style customization is absent
unless supplied. Preserve old configuration bytes rather than inserting new keys
into authenticated historical records. Confirmation binds choices to the actual
owner/profile/thread, never the installer or whichever chat happens to be current.

Language goes through the existing expression language argument. The owner's own
bounded communication wording goes through existing encrypted USER_EXPLICIT memory
and CognitionContextReader, so source selection, interpretation and authoring can
use the same evidenced preference. No new profile service, transcript mining,
model permission, physical queue or Core configuration write is introduced.

The memory proposal names the authenticated confirmation as its evidence. A
deterministic proposal identity makes recovery idempotent; a repeated confirmation
must not resurrect forgotten content. A new explicit setup preference supersedes
an active earlier setup-derived preference of that same owner, not a foreign
record. Omission is not an erasure command. Style memory has its existing update/
forget lifecycle, distinct from finite outward-history retention and authorization.

Qualify actual CLI/control wiring, scope isolation, private storage, replacement,
forget/replay and language inheritance; then inspect complete real-model originals
in the activated chain. A configured language does not prove a natural message,
and correct context delivery does not establish semantic preference adherence.

The first real comparison fixes language but remains overly defensive. Its test
corpus blended operator scope notes into the purported source passage. New
captures can optionally report a bounded content representation (extract,
operator paraphrase, machine summary) as provenance metadata, not article prose
or independent verification. Unknown formats stay unspecified without rejecting
otherwise usable content. Old captures without the field retain their metadata
shape. Carry the same reported representation into authoring and main-turn
grounding; never claim that an operator digest is a raw/full-page read. Keep the
original annotated corpus and failed/weak outputs rather than overwrite them.
