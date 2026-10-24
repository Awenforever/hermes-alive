# ADR0216 — Narrow initial additions rejection can reach existing correction

Date: 2026-10-24 (Asia/Shanghai)
Status: implementation under qualification; long-lived attention recovery open.

The actual r32 activated chain rejected a generated discovery for an unsupported
addition before reaching the final-source review. SendPreparationRuntime already
has once-per-intent source finding, localized correction and re-review; the
initial rejection prevented that established recovery path from running.

An authenticated, current initial semantic rejection may now obtain concrete
final-source findings ONLY when its sole risk is unsupported_addition, all
meaning atoms remain preserved without other risks, speech act and protected
literals are preserved, grounded planning is enabled, and repair is allowed.
No critical meaning/authority/protected-content failure or invalid/missing review
enters this bridge. An already corrected invocation cannot reopen recovery.

Source findings still cannot approve a rejected original. If the source reviewer
disagrees and supports it, retain final_semantic_rejected. If actionable negative
source findings exist, reuse the SAME existing correction slot and its original
digest, ancestry, local-edit constraints, stage/response admission and replay
fences. The new body must pass its own semantic AND final-source review, then the
normal independent send-time authority/route/cadence checks. No old body, second
repair generation, new grant, retry of unknown work or physical send is invented.

Test successful correction, repeated rejection, disagreement, critical rejection,
cancelled model work, incomplete review, erased proof and no-spend recovery using
the existing correction suite. Preserve the original negative observations.

This does NOT yet solve long-lived behavior after an exhausted content rejection:
continuous host still exits on content_review_attention. Do not simply continue
and repeatedly regenerate on unchanged material. Next qualify change-sensitive,
durable waiting/reconsideration separately from authorization/pending-work/unknown
external effects. Initial vs final overlapping review contracts and naturalness
remain under examination; no production or quality completion is claimed.
