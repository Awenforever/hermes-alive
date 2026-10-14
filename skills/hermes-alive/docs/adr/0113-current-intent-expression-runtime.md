# ADR 0113 — Current-intent natural expression and crash-safe recovery

Date: 2026-10-14

## Runtime composition

`ExpressionRuntime` runs the actual recoverable planning runtime, then binds the
selected opportunity's meaning to the existing natural renderer and independent
semantic-review lifecycle. Silence returns no text and never invokes expression
models. Model routes and independence classification are host-supplied; no vendor,
private interest, channel or sender identity is hardcoded.

Expression model IDs and language are validated before any planning spend.
A structural start binds selection, meaning, requested render/review models,
language and a digest of current presentation evidence. Reusing the same cycle
with another language/style/model contract is rejected, not silently reworded.
Plaintext remains in the existing encrypted content vault, not wrapper events.

This connects planning and natural expression; it does not invoke the production
watcher, authorize sending, implement a channel FIFO, or establish user benefit.
Every result explicitly has `delivery_authorized=False`. A favorable semantic
review is an assessment, not a truth certificate or an automatic delivery grant.
Source support, current authorization, host delivery and trustworthy feedback
still need integration and qualification.

## Recovery and crash seam

Completed expression recovery resolves the current retained interpretation and
selection first, then verifies the authenticated expression and review against
the exact selection/meaning/execution. Erased or expired inputs, changed style,
superseded intent and foreign review bindings must not recover usable text.

An interrupted renderer/reviewer does not trigger an implicit provider retry.
When the underlying comparison has completed but the outer runtime record was
not committed, the runtime instead verifies its exact completed-stage receipt
and authenticated review, reconstructing the outer structural record without
calling providers. A failed/missing native completion cannot take this path.
This distinction prevents charging again merely because one outer receipt was
lost, while refusing to invent success for an unfinished operation.

## Evidence

`run_alive_kernel_expression_runtime.py` uses four controlled scenarios:
sharing with exact source provenance, silence, render cancellation, and a crash
injected immediately before writing the outer completion record. Reopened
recovery performs no additional model calls. Language changes are refused and
erasing the original interpretation prevents further recovery. No attempts or
external dispatches are created. These are synthetic model families/responses,
not real independent semantic qualification or a complete production test.

Windows Python 3.14 passes all four. Linux isolated container
`alive-expression-runtime-offline-20261014-r1` exits 0 for the expression test
and the adjacent planning-runtime regression. Network is disabled; its scratch
mount is read-only, resources bounded to 1 CPU/2 GiB/256 PIDs. The dependency
snapshot is ADR-0112's unchanged source plus these exact files:

- runtime SHA-256: `d949b26d55fb03959470fbefc13395d89baf095edc6895763ccbf9b7d9581380`
- test SHA-256: `fb3e56c07f62aa889c1f3b988472b1ba37c65987698f283eda14c7d0e7010f07`

Next compose current send-time authorization and qualified host transport without
another platform queue. Preserve real-model independence/quality limitations,
privacy and outcome attribution rather than promoting these controlled tests to
production approval. Production and other plugins remain unchanged.
