# ADR 0176: select the reviewed recipient contribution, not an illustrative draft

Date: 2026-10-18. Status: implemented; qualification in progress.

## Measured problem

The preceding real unsent trial completes all stages, but manual review rejects
its abstract-like message. The generator's generic editorial instruction alone
does not establish useful sharing. Source fidelity and conversational value are
separate requirements; reviewers' agreement is not recipient satisfaction.

Code inspection also finds an actual contract mismatch: purpose review and final
expression use the retained communication plan, while selection sees the action
contract's illustrative draft. A polished draft can mask an inappropriate plan,
and a poor draft can misrepresent a good plan. Fix the model-input view, not the
immutable frame, action or accepted history.

## Decision

During existing candidate-source validation, resolve the owner/current, authenticated
retained proposal. Return its recipient plan as a model-input view. For generated
plan-bearing candidates, selection receives that plan instead of the illustrative
draft. Other/legacy candidates retain their existing view. The old action contract
stays unchanged; rendering and sending retain their original safeguards. Current
source/profile validation still runs before and after model waits. No new storage,
model router, queue or review tier is introduced.

Clarify the existing generator, purpose review and selector responsibilities:

- The goal describes a substantive contribution, not merely announcing a subject.
  That contribution must be in the actual contents; an external goal cannot add
  meaning after approval. Do not invent an implication or personal relevance.
- Purpose review distinguishes topic-match/source compression from worthwhile
  explanation, surprise, possibility or a grounded question. Judge the evidence,
  not a keyword, length limit or blanket rule against summaries. Requested detailed
  reports, direct answers and admitted reminders can require more information.
  Out-of-profile discovery remains eligible. Do not require artificial excitement,
  a relevance slogan, advice or a question at the end of every message.
- Selector scores remain separate tentative assessments, not a calibrated utility
  formula. Compare actual contributions and retain silence for marginal value;
  an assertion that a candidate has the highest self-assigned scores is not itself
  an evidence-grounded reason to share. Policy/authority gates remain binding.

Prompt digests bind review receipts. Prior approvals do not become approvals under
the new criterion; no historical receipt or accepted meaning is rewritten. Existing
canonical historical runtime remains available for audit. This is experimental
development, not a production upgrade or migration qualification.

## Qualification discipline

Focused suites pass actual-plan/illustrative-draft divergence, foreign-owner
refusal, plaintext sentinel absence and unchanged retained contracts, plus adjacent
commitment, selection, grounded repair and protocol recovery regressions. The first
new fixture reused a content-vault parent across independent journals; separating
test roots resolves its authenticated-identity collision, without storage changes.

Run fixed synthetic positive/negative contrasts before interpreting actual new
public-source messages. Compare the previous criterion on the same controls; if
both already handle them, do not claim a measured intelligence improvement. Include
valuable unfamiliar material and requested detail to catch over-rejection. Retain
errors and unsolicited-silence outcomes. These diagnostics do not count as ten
fresh complete clean rounds, real transport or production usefulness acceptance.

ADR0175 final qualification: commit 3a5e7d1, tree14e2a1c, full portable CI passes
with 65 retained logs, source553/repository576 and exact archive permissions.
That trial's one-shot structural correction is covered by controlled tests; its
actual successful generation did not exercise correction. No live proof is claimed.
