# ADR-0291 — Distinguish search failure from silence

Status: implemented and verified in isolated configured-discovery cases.

A real public discovery wake received a settled TLS error from the Hermes
search tool. The read receipt recorded the failure, but the host closed the
wake as ordinary silence. This made a tool outage look like a decision to
stay quiet.

If planning ends in system no-material silence and the current wake's
configured search receipt contains only failed searches and no observations,
close the wake as `discovery_search_unavailable`. Keep that disposition in
the authenticated host completion. Do not remember this as a content-based
decision to wait. The next normal wake remains eligible; the search failure
does not trigger an immediate retry or change provider ownership.

Successful empty searches and informed abstention keep their silence
disposition. Usable observations and independent agenda work can still
reach planning. Unsettled reads retain their physical cancellation and
reconciliation behavior.
