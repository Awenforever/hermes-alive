# ADR 0175: reuse bounded model recovery for inadmissible recipient plans

Date: 2026-10-18. Status: implemented; full regression and live follow-up pending.

## Problem and decision

A fresh isolated public-source trial completes generation but fails before source
review because a translated plan protects a literal absent from its own content.
More instructions about each date, language or phrase would be brittle. Do not
repair model meaning deterministically, remove literal protection, relax source
checks or count rejected plans as a successful silence decision.

Extend the existing one-shot JSON correction to pure proposal admission when
recipient-meaning mode is enabled. Use the original evidence, current authority,
same operation and remaining deadline. Supply bounded validator findings and the
failed response as untrusted data, never as new facts or permission. The model
returns a complete replacement. Keep the original failed output and findings in
the encrypted vault, with only structural references in the journal.

This is not a new fallback model registry, judge layer, retry loop or sender.
Hermes still owns routing and model fallback. Provider/host failures propagate;
withdrawal, cancellation and timeout prevent further use. A terminal failed
operation cannot spend another inference on reopening. Source, recipient-purpose,
selection, meaning, final support and execution checks remain downstream.

## Admission and recovery proof

- Preserve valid proposals in a mixed response; one bad proposal must not erase
  another or cause unnecessary correction. Legitimate initial empty output and
  disabled recovery retain their previous behavior.
- If every proposed plan fails admission, allow at most one correction. A second
  malformed plan fails. A correction cannot hide the failure by returning empty,
  unassessed output: it needs an admissible candidate or an explicit valid,
  source-linked abstention. This is not proof that its editorial choice is good.
- Reopening validates the recovery event's owner, cause, model, prompt bindings
  and encrypted artifact. Rerun the versioned pure admission probe on the original
  failed output; a label cannot declare an actually valid response invalid.
  Validate the retained final assessment too. Historical syntax-only receipts
  remain distinct; legacy draft mode does not gain structural correction.
- Keep `proposal-shape-v1` available when adding successor schemas. It documents
  the actual validation contract, not a promise to reinterpret old evidence under
  future rules. No accepted meaning is rewritten in place.

## Qualification and remaining work

Focused tests pass correction, invalid envelopes and foreign source IDs, mixed
valid/invalid proposals, explicit abstention, refusal of empty correction,
authenticated-but-false failure artifacts, provider failure, withdrawal before
and during correction, cancellation, timeout, terminal replay and encrypted-only
private content. Communication-plan regression also passes. An initial standalone
test harness failed to establish its writable temporary Hermes home; it was
corrected without changing production, dependencies or storage protections.

Live follow-up uses the same newly collected public-source batch to validate the
fix, not another fresh acceptance round. Preserve both the original failure and
follow-up result. Even a successful model correction or reviewers' approval does
not prove useful recommendation quality, production embedding or ten fresh
complete clean rounds. No production deployment, send or restart is authorized
by this ADR. Individual interests and unsent samples stay outside distribution.
