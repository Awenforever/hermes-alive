# ADR-0030: Discovery observes opportunities and never sends

Status: accepted for the shadow kernel

## Context

Legacy Discovery combines network/local collection, freshness heuristics,
interest mutation, ranking, cache rotation and delivery deduplication. The
monolithic watcher then exposes that batch directly to composition and sends a
selected item. This makes “a source returned a document” too close to “the user
should be interrupted now” and prevents independent replay of perception,
judgment and action.

Collector scores are also not authority. They describe source quality,
freshness or a legacy preference estimate; they cannot establish user value,
timing, route or permission to communicate.

## Decision

Introduce a discovery ingestion boundary that accepts a typed, bounded
observation and may do only two durable things:

1. append `discovery.opportunity_observed` evidence; and
2. propose an active `OPPORTUNITY` agenda item backed by that evidence.

All title, summary, URL, source label, author and collector attributes are kept
in the encrypted content vault. The journal and rebuildable entity projection
hold only structural IDs, installation-keyed fingerprints, timestamps,
confidence, expiry and encrypted content references.

Identity and content version are separate. Re-observing the exact version is
idempotent. A new content version for the same upstream entity creates a new
observation and opportunity and dismisses the superseded opportunity. Source
failures are health observations only and never agenda items.

The compatibility adapter may consume the legacy external candidate shape, but
does not import legacy interest state, topic reservations, composition or send
logic. A dual opt-in shadow bridge can mirror a bounded legacy batch. It is off
by default and its result is not read by the legacy watcher.

This boundary exposes no route, adapter, send, reservation or dispatch API.
Whether an opportunity deserves attention remains a later cognition decision;
whether it may become an external action remains a later policy and authority
decision.

## Consequences

- Discovery can be evaluated against real candidates without changing user
  behavior.
- One failed or malformed candidate is rejected independently; valid siblings
  survive.
- URLs and private source details no longer leak into the append-only journal.
- Collector rankings remain visible as encrypted hints but cannot authorize an
  interruption.
- The legacy collector can be replaced source by source without rewriting the
  agenda, deliberation or delivery contracts.
- Local filesystem discovery is not migrated by this decision. It requires a
  separate, narrower consent and privacy design before it may enter the kernel.
