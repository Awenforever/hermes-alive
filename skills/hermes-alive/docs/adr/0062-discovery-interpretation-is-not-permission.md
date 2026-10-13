# ADR-0062: Discovery interpretation is not permission

Status: accepted for explicit, unscheduled shadow experiments

## Problem

The coordinator can deliberate, but previously callers fabricated its candidate
drafts and dimension scores. A model must interpret source meaning instead of
using topic-specific keyword patches. That must not turn an untrusted source or
a fluent model response into permission to act.

## Decision

- Query active discovery opportunities by owner and kind before applying limits.
  Validate current authenticated observations, clearance, retention, erasure and
  supersession before resolving source text. Model waits revalidate that evidence.
- An explicit host-supplied Hermes model capability interprets at most eight
  sources into zero to four tentative SHARE/ASK candidates. Source excerpts are
  untrusted data; truncation and current time are disclosed. User preferences,
  destinations, deadlines, facts and authority must not be invented.
- Six separately reasoned dimensions remain model judgments, not measurements or
  user-benefit evidence. Parse bounded JSON with duplicate/nonfinite rejection;
  malformed individual proposals do not invalidate other proposals. These are
  interface and permission checks, not a semantic topic classifier.
- Authority defaults to NONE. Only trusted host policy can supply a delegation;
  the model cannot specify it. Fixed destination-free communication contracts
  express drafts, not action attempts, dispatch, tool execution or permission.
- Persist an exclusive start before inference. Reuse, cancellation and interrupted
  operations cannot silently spend again. Keep actual returned model attribution,
  structural failure receipts and encrypted accepted proposals, not raw prompts,
  raw responses or provider exception bodies in the event journal.
- Provider choice and fallback belong to Hermes, not this interpreter. Public
  defaults contain no installation-specific provider or model preferences.

## Qualification and open work

Deterministic contracts cover owner filtering, partial rejection, delegation
separation, model attribution, cancellation, erasure during inference and
composition with the model selector. A separate opt-in synthetic live probe has
six logical-call and twelve observed async-HTTP request caps. It is excluded from
default tests, does not send, and cannot qualify human usefulness by itself.

This does not yet incorporate user-profile memory retrieval, generalized ongoing
commitment generation, production user-policy integration, live scheduling and
budgets, full semantic fidelity review or longitudinal benefit. The bounded scan
and source excerpt limits also need coverage/performance qualification. Arbitrary
projection tampering and atomic network/consent transitions are not solved here.
Production scheduling, legacy runtime retirement and release remain gated.
