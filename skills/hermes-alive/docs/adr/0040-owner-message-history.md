# ADR-0040: Discoverable owner-scoped semantic history

Status: accepted for shadow kernel; live integration pending

## Decision

Add `/memory alive messages [before-event-id]` to discover semantic content
identifiers for inspection, correction and withdrawal. Display recorded time,
current state and at most 120 characters of currently resolvable content. Show
authenticated successor references for corrected or interrupted corrections.
This is content history, not delivery history: definition, selection, attempt
and acknowledged delivery remain distinct, and no send status is invented.

Filter subject and event type in SQL before materialization or decryption.
Add an idempotent `(subject, event_type, sequence)` index without rewriting
events or changing journal schema. Read newest-first with at most 21 records
to produce a page of at most 20. The user command uses ten items per page.
Existing ascending replay and consumer checkpoints are unchanged.

The pagination anchor is an event ID, not a positional offset or a shared
sequence number. Require the anchor to be a semantic definition belonging to
the host-authenticated user. Page by strictly smaller sequence. Inserts after
the first page cannot shift or duplicate older entries. The cursor only grants
an owner-filtered seek: a definition with invalid semantic authentication can
anchor pagination but cannot expose content or grant action authority.

## Current states and privacy

Before showing content, authenticate its semantic definition and resolve it
through owner-scoped meaning inspection. Withdrawal is checked separately:
withdrawn and corrected versions never expose plaintext previews. An absent
successor is `correcting`, not completed; a present successor must have valid
definition authentication before the old version is labeled `corrected`.
Expired, erased or otherwise unavailable content has no preview. Permanent
structural history can remain after subject-content erasure, as documented by
the retention contract.

States are read-time observations, not leases or send authority. Corrupt
journal integrity raises an error; failed semantic authentication is shown as
unavailable without decrypting. SQL filtering assumes the integrity-checked
host journal, not an adversary with unrestricted host/installation-key access.
Do not cache previews in another plaintext history database.

## Evidence and limits

Tests cover two interleaved users, newest-first ordering, multiple pages,
inserts between pages, foreign/missing/non-message cursors, SQL index usage,
invalid page bounds, withdrawal/correction/interrupted correction, expiry,
erasure, invalid semantic authentication, and command-level anonymous refusal.

Live gateway integration and linking semantic history to real delivery and
user outcome feedback remain separate qualification work. This lookup makes
the typed user controls discoverable; it does not complete the learning loop.

On 2026-10-12 the history, journal, correction, withdrawal and retention tests
passed on Windows and in a disposable container based on production image
`hermes-agent:v0.21.3-weekly-20260918`. The container had no network and only
read-only test-source access; production data was not mounted. Production
was not updated or restarted. This is isolated runtime proof, not live-user
or longitudinal qualification.
