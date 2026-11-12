# ADR-0290 — Continue after a settled Core model timeout

Status: implemented, controlled qualification in progress.

The real edge-VLM discovery trial obtained sources and three candidates.
The final review had no response and ended with `APITimeoutError`. There was
no admitted draft, adapter submission or ordinary continuation. The continuous
host ended with `cycle_failed`. That result would leave a live installation
idle after an ordinary provider interruption.

Classify a timeout only at the Core completion await, after the pending task
has settled and the model scope still verifies. Let Core own its existing
provider and fallback attempts. The host records a signed
`model_temporarily_unavailable` outcome and closes the current cycle. Its next
scheduled wake uses a fresh operation, current evidence and current owner
authority. The spent operation and any earlier job IDs stay in the journal.
The old read-only transport receipt cursor can be observed again. There is no
immediate extra provider request, renewed send permit or draft replay.

Other exceptions, unsettled work, revoked authority and unqualified model
responses follow their existing paths. A controlled test must establish the
timeout classification, a distinct subsequent wake, no dispatch and unchanged
failure handling. A new real trial is still needed for the quality streak.
