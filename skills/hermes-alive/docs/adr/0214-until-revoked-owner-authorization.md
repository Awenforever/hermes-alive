# ADR0214 — Owner authorization lasts until pause or revocation

Date: 2026-10-24 (Asia/Shanghai)
Status: accepted product choice; qualification in progress.

The owner explicitly chose lasting proactive authorization rather than mandatory
monthly reconfirmation. Ordinary native enable therefore creates an explicitly
signed `lifetime: until_revoked` activation and communication delegation. The
event and payload both have no expiry. A missing expiry alone is NOT authority.

Historical finite grants retain their original expiry and authenticated meaning;
no startup, upgrade or replay converts them to lasting grants. Finite experiments
remain supported. Persistent grants retain the exact owner, confirmed setup,
current enabled policy, route, communication-only scope and cadence checks.
Pause, revocation, a replacement setup, changed policy or lost authority still
prevent new work. Restart restores valid authority, never creates or renews it.

This choice is independent of source/history retention, model credentials,
physical queue ownership and per-window production/test-send authorization.
It does not retain private material forever, grant background chat mining, change
Core provider configuration, or authorize production activation or deployment.

Qualification must include both finite expiry and persistent validity beyond a
month, forged/missing lifetime refusal, owner/scope isolation, revocation and
pause, restoration without new grants, and late checks before external IO.
