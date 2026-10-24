# ADR0222 — Current agenda boundaries before the wait limit

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: implemented; qualification in progress.

An isolated reproduction with 129 admitted agenda opportunities showed a long-life
failure: after their expiry, lifecycle rows can still be ACTIVE. The bounded wait
scan counted all of them and refused reuse forever, although none could impose a
future temporal boundary. Requiring a janitor to transition every row would make
normal temporal semantics depend on unrelated housekeeping.

Apply canonical UTC expiry at the current capture clock before the existing
129-row limit. Keep active and snoozed state, owner and sensitivity filters. Do
not rewrite, delete or complete history. Future available/due/expiry boundaries
still cap the wait. More than 128 genuinely current rows still make the bounded
view incomplete and prohibit silence reuse. This is temporal eligibility, not
preference, source judgment, transport scheduling or action permission.

The regression advances a synthetic clock after 129 real admitted proposals,
without editing projection tables. Expired rows no longer consume the bound;
one new upcoming deadline remains visible; 129 unexpired rows still fail closed.
No model, external channel, production state or real-user data is involved.
