# ADR 0148 — Recipient meaning is not the whole illustrative draft

Date: 2026-10-16. Status: explicit isolated mode; quality remains unqualified.

## Decision and immutable boundary

ADR 0147's actual reminders revealed that protecting all proposed prose as one
semantic atom also protects unnecessary guardrail recital. Introduce an explicit
`recipient_meaning=True` planning mode. The original opportunity contains a
versioned `communication_plan`: recipient goal, speech act, essential recipient
content units and separate proposed behavior constraints. The illustrative draft
and original action contract stay immutable; the plan is part of the encrypted,
digest-bound original proposal, not a later paraphrase of a confirmed message.

Natural expression binds to content atoms, not every incidental draft clause.
The renderer sees goal and constraints as contextual limits, not additional text
to recite. Material factual negation, eligibility, uncertainty and source caveats
must remain contents. Neither constraints nor a model's goal grants authority.
Share maps only to share/inform/remind/warn; ask maps to ask. The actual reminder
speech act is now representable, rather than always masquerading as share.
Canonical source links remain separately protected even when the plan omits them.

The existing send-time authorizer is unchanged: exact expression confirmation or
current explicit delegation allowing natural expression is still required. No
model review, plan or intended goal creates a route, grant, tool action or send.
Revalidation across awaits/recovery still resolves the current original proposal,
agenda and context; completed tasks and erased dependencies invalidate it.

Legacy proposals keep their old draft/atom binding; they are never retroactively
compiled to new meaning. Old mode does not request or accept new plan fields.
Strict mode rejects absent plans rather than silently reverting to legacy wording.
Planning operation binding prevents changing the mode on reopen. Production has
not opted into either this new kernel or its recipient-meaning mode.

## Bounded structure is not semantic intelligence

Plans have at most six content units (800 characters each), six behavior constraints
(300 each), a 512-character goal and a 4000-character aggregate JSON budget. Actual
semantic atom/literal bounds also apply. Unknown fields, changed action/speech-act
scope, an undifferentiated proposed-content unit or invalid exact literals fail.
For kinds without required literal protection, omitted protected_literals means an
empty list, without rewriting the retained proposal. For deadline, amount, link,
contact, uncertainty and negation the established nonempty literal requirement
remains. This has proven a model reliability concern, not a semantic success.

All-malformed strict-mode proposals now raise an unresolved planning error rather
than qualifying as silence/wait. Reopen preserves that result without another
provider call. A wholly malformed correction is also unresolved; independent
supported candidates may survive. Structurally rejected items remain unassessed,
not inferred user dislike. General bounded protocol recovery and a less fragile
semantic contract remain open design questions, not permission to invent fields.

## Purpose and factual support are different assessments

Source review receives the plan as tentative interpretation alongside exact
source/context; it must not treat the plan as additional factual evidence.
`CommunicationPurposeReviewer` separately asks whether recipient contents serve
the actual purpose and distinguish meaningful caveats from operating constraints.
It uses a `recipient-purpose-v1` snapshot in a distinct canonical planning lane.
A purpose receipt cannot verify as a source-support receipt, or vice versa.
Both retain raw encrypted reasoning and current input/dependency validation.

Grounded strict-mode planning first reviews source support, then purpose for
surviving candidates. Either negative/uncertain result can use the existing single
correction generation, followed by fresh factual and purpose review. Failed or
interrupted reviews do not silently spend again or count as qualified silence.
This is bounded model reasoning, not phrase deletion, a blacklist or a rule to
remove all negations. Same-family checks are explicitly correlated, not independent
semantic certification. Without grounding there is no claim of either assessment.
Final expression still has its own fidelity/source checks; purpose of the actual
rendered wording has not yet been separately qualified end to end.

## Actual observations, including failures

Terminal synthetic-only evidence remains under the retained isolated root:
`/tmp/hermes-alive-installed-RJbQNAiD/`.

- `model-only-commitments-20261016-r3`: one actual call. The model omitted empty
  literal lists on nonliteral content kinds; the overly strict first parser
  rejected it. Nonliteral omission is now accepted explicitly, not as model fallback.
- `...-r4`: five actual calls, reached expression. The model classified operating
  constraints as a caveat; source/fidelity accepted and the reminder still recited
  constraints. Splitting fields alone did not solve meaning classification.
- `...-r5`: one actual call; generated negation with an empty required literal list,
  structurally rejected. The older experiment reported silence. The new unresolved
  planning guard prevents treating this failure as qualified silence.
- `model-only-purpose-20261016-r1`: four actual purpose assessments of **fixed
  synthetic proposals**, not actual opportunity generation or a full live loop.
  Operational recital was rejected; a concise reminder and visible eligibility
  were accepted. A fourth proposal hiding eligibility inside constraints was
  accepted contrary to the diagnostic expectation. That fixture asks to check a
  notice rather than explicitly explain eligibility, so necessity is also worth
  examining; keep the mismatch, do not declare general preservation solved.
- `model-only-commitments-20261016-r6`: six actual calls. Original source review
  rejected uncertain timing; a corrected proposal cited the absolute deadline.
  Factual/purpose reviews accepted it, but selection chose silence for missing
  current time. Its plan still classified operational limits as a recipient caveat,
  which purpose review accepted as user-requested assurance. No clean natural
  expression was produced; this is not a passing acceptance cycle.

All these jobs ended with exports removed and production StartedAt unchanged
within each job; zero actual messages sent. Totals: **204 logical calls / 217
observed async HTTP starts**, including failures. Earlier bad examples remain.

## Time context defect found by actual selection

Selection previously received candidate content/scores but no explicit current
decision-time anchor. It was reasonable for a model to identify missing time, but
not a reason to patch silence to share. Supply host `selection_as_of` in the prompt
header and persist the same value in the exclusive start receipt. Bounded retries
reuse the exact same prompt/clock. This is decision time, not delivery-time evidence
or a send grant. Recipient-mode source snapshots also expose the original recorded
`interpretation_as_of`, distinct from collection/start and transport time. The
time-context correction has fixture evidence, not a subsequent real-model success
claim. General time semantics, scheduling usefulness and delayed-transport intent
withdrawal still require qualification.

## Verification and remaining scope

Windows tests cover legacy/new binding, protected deadline, separate constraints,
synthetic delegated preparation/delivered history, factual-vs-purpose receipt
separation, one purpose correction and no mode downgrade on reopen. Structure tests
cover missing plans, literal failures, mixed partial rejection/stable indices,
material negation versus agent constraints, and no provider spend on failed reopen.
The selector fixture checks exact persisted timezone-bearing prompt time and
unchanged retry prompt. Offline read-only/resource-limited Linux runs adjacent
cognition, authorization, delivered history, interpretation, learning/reconsideration
and expression preparation/repair through current-module overlays. These are not
fresh-device lifecycle or full portable CI evidence.
The final terminal suite reports ten individual completed scripts, including
communication-plan structure and selector synthesis; all exit successfully.

Do not deploy this as a solved language system. Needed next: robust plan production
without silent format losses; fresh purpose contrasts where information necessity
is unambiguous; independently qualified meaning classification and final-wording
purpose; current-time model behavior and sustained agenda usefulness; full installed
host/authenticated feedback, privacy/forgetting/migration/rollback and eventual
production acceptance. FIFO/Token remain Qoder/Enhance responsibilities.
