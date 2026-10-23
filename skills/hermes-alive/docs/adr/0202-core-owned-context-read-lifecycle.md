# ADR0202 — Context reads belong to the existing Core-owned lifecycle

Status: implemented; exact-tree qualification pending

## Problem and decision

An actual Core feasibility probe measured a roughly 1.27-second event-loop gap
while reading an 18-episode synthetic retained context index synchronously.
Moving that same read to Core's context-bound thread reduced the measured gap to
roughly 0.012 seconds. These fixture measurements motivate integration, not a
production latency guarantee.

Use `agent.memory_provider.spawn_context_thread`, preserving Core's profile
context. The existing native cognition host lends a current-cycle capability;
it supervises this work alongside its model caller and public preparation.
No separate service, memory backend, delivery queue or configuration authority.
Default synchronous library embedding remains available when no capability is
provided. Callbacks are neither serialized nor part of semantic option hashes.

## Physical ownership and authority

The worker, not its async waiter, holds a profile-local OS file lock. Cancellation,
timeout and unload cannot release it early. Pending/reap report physical thread
liveness. A replacement module generation checks the same lock before preparing
public/model work. Unload retires the capability; an escaped callback from a
finished cycle cannot start another read. Check profile and trusted current-cycle
binding before starting, inside the physical lock, and before returning a result.

A local timeout does not kill Python threads or promise bounded execution of an
arbitrary provider. It stops waiting while preserving ownership until settlement.
Closed-loop publication is dropped, never transferred to a replacement runtime.
Exceptions expose only a sanitized class name, not private provider/parser text.
Only trusted synchronous closures are supported. Reject returned awaitables;
this is an API boundary, not a sandbox against malicious Python code.

## Integrated consumers and limits

Offload feedback-window acquisition/currentness and exact-pair resolution, bound
material capture/resolution, opportunity input capture/currentness, completed
proposal recovery and reconsideration snapshots. Keep model calls on their
existing supervised path. Other snapshot/review/assimilation and receipt-write
paths still include synchronous work; do not claim the whole pipeline nonblocking.
External Core memory-provider integration remains a separate open requirement.

## Evidence

The synthetic contract exercises actual threads and OS locks: cancellation,
timeout, changed authority, unload/new module generation, replacement native-host
fencing before preparation, callback expiry, private exception sanitization and
foreign-profile rejection. Actual retained-feedback selection is checked for
off-main-thread acquisition with a live event-loop heartbeat.

The installed pinned-Core controlled cycle observes four off-main-thread reads,
each under the actual profile, and unload retires the capability with no pending
work. Search/HTTP/model replies are controlled, network is disabled, and sends
are zero. Known managed dependency warnings remain; this is not a clean-machine
dependency install, real recommendation-quality round or production acceptance.
Exact-tree portable qualification and broader lifecycle tests remain necessary.
