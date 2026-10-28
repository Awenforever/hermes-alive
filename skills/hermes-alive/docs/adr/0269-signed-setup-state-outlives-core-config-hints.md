# ADR 0269 — Signed setup state outlives removable Core config hints

Date: 2026-10-28. Status: candidate; actual installed consumer requalification
required. No production change.

## Observation

An Ubuntu native consumer installed the previous immutable development commit
through Core's Git installer, staged personalized choices, updated to the next
commit, removed runtime and plugin, and reinstalled them. All five existing
kernel-state files survived. Status reported awaiting confirmation. However,
the actual installed Core confirmation command failed before its challenge
expired. Core plugin removal had cleared the plugin config entry, including
`pending_intent_id`. The handler treated that removable hint as indispensable,
despite retaining the authoritative signed intent and its identity.

The later observation that the challenge had expired was not the cause: the
failed attempt's timestamp precedes the recorded expiry. Preserve that failed
consumer record. File preservation and status alone did not qualify recovery.

## Decision

When both pending/configured config hints are absent, recover only the latest
intent identifier from Alive's retained journal. Pass it to the existing
`confirm()` path, which authenticates the signed latest intent, original
challenge, expiry and exact authorized Core conversation. It rereads the latest
intent, so a concurrent replacement still fails closed. An existing conflicting
hint is not silently replaced. No signature, key, grant or token is regenerated;
delivery is not activated by this recovery.

Expired challenges still fail. Fresh guidance may explicitly replace an expired
intent with the same selected preferences; it cannot extend old token validity.
Wrong conversations and missing Core sessions remain rejected.

## Verification

The actual-Core guided regression clears the Core config hint before loading
the plugin, then exercises native confirmation and its existing session,
foreign-owner, repeat, retention and inactive-delivery checks. A separate native
Git consumer must confirm after a real Core remove/reinstall, within the new
challenge's lifetime. It must not be replaced by a same-process simulated flag.
No real account, model, transport or daemon acceptance is implied.

## Verification addendum — 2026-10-29

The bounded implementation is qualified. Frozen r312 passed the actual-Core
guided regression in two cases after removing the config hint, plus the pure
setup regression. The original process exited zero and its disposable container
was destroyed; the Core supplier remained clean.

The Ubuntu native consumer then installed immutable development commit
`cb7c0a5dcd040cdfbae58f17e724702ccc483a9a` through Core's public Git installer.
After fresh explicit setup, actual runtime uninstall, Core plugin removal, Git
reinstallation and runtime installation, the real installed Core command handler
confirmed the retained intent using a synthetic authorized adapter/session.
Explicit interests remained readable from protected state; no external-memory
grant appeared and delivery remained inactive. Consumer r313 exited zero.

The earlier before-expiry r310 failure remains recorded. The successful run used
a fresh explicit replacement after the earlier intent expired; it did not bypass
expiry or revive the old challenge. No real model, account, message or daemon
was used by this lifecycle check. Full four-platform and active-task lifecycle
acceptance remain separate gates.
