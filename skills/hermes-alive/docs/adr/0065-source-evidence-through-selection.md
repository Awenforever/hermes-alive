# ADR-0065: Source evidence remains live through model selection

Status: accepted for shadow cognition

## Problem

A completed interpretation checked its discovery and explicit profile sources,
but later selection checked only the retained frame and exploration gate. A
profile withdrawal during the selector await left the old frame unchanged and
still allowed SHARE. An encrypted copy is not evidence that its sources remain
current or that another owner may use it.

## Decision

Before copying generated content into a new frame, recover its completed
interpretation using the original owner, receipt clearance and current authority.
Check owner before decrypting. Match stable candidate identity, all action fields
and the retained content. Reserved interpretation evidence identifies generated
candidates even if the caller relabels their IDs. Missing, ambiguous or altered
proof is refused, not treated as an ordinary native candidate.

Repeat this validation before each selector call and after each await. Discovery
supersession, source erasure or explicit profile withdrawal ends that decision as
context-changed, without committing a choice or retrying the stale prompt. The
memory vault may be provided explicitly; its existing independent default is
unchanged. This introduces no implicit memory migration or reauthorization.

This is a provenance/lifetime boundary, not semantic keyword filtering. The
unchanged positive control must still allow a model to select a useful share.
Native candidates without interpretation receipts retain their caller-owned
provenance contract; this check does not invent proof for arbitrary inputs.

## Evidence and limits

The regression first reproduced selection after profile withdrawal. It now
covers withdrawal and source erasure during selection, discovery supersession,
withdrawal before retry, withdrawal before frame creation, relabeled identity,
foreign owner, and an unchanged successful SHARE. None attempts an action.

This does not make checks atomic with networking, cover retries hidden inside a
provider SDK, erase every derived copy, or bind later presentation and dispatch.
Generalized composite/multi-origin candidates, historical audit ingestion,
production policy wiring and human usefulness remain separate work. Existing
historical projections remain available; preparing a new frame with invalid
generated evidence is deliberately refused even for an audit baseline.
