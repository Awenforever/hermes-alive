# ADR0218 — Deferred discovery reasoning and retained silence

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: implemented in development; qualification in progress.

Extends ADR0217's phase boundary. Native configured discovery now observes
approved listings before the runtime, but defers model selection and extraction
until after reconciliation, cadence and the existing reconsideration checks.
Other preparation capabilities keep their established callable path. The host
validates unchanged owner/model/context capabilities around deferred reasoning.

The discovery reader retains only its derived inquiry/read-receipt arguments in
the encrypted vault, with exact owner/operation/search receipt provenance and a
listing fingerprint. Never persist callbacks, provider configuration, authority
or send parameters here. When a prior wait has matching host configuration and
complete listings, these arguments let the existing expression runtime replay
and validate the original silence with a model callback that refuses inference.
Missing parameter content disables reuse; it does not resurrect the old spend.
The current operation reasons afresh only if retained waiting cannot be proved.
The fingerprint uses the cycle's effective durable research modes, not newer
requested settings: replaying an interrupted old cycle must not relabel the
material or its modes, extend retention or conflict with its original receipt.

Reconsideration v3 includes the listing fingerprint. Successful observation's
own read/mode control records are not new semantic inputs. Real source versions,
inbound identities, memory/context, feedback, agenda boundaries, policy, unknown
owner events and retained-proof availability still invalidate or bound waiting.
No message body is read merely to detect new inbound. Earlier v1/v2 records
remain historical and authenticated; they are not promoted to the new contract.
Reusing a wait does not renew its deadline, authority or material retention.

If retained waiting fails, the runtime invokes the deferred reasoning capability,
checks policy again, rebuilds current expression parameters and captures a new
baseline after discovery. It never starts new inference with the previous
cycle's inquiry arguments as if they belonged to the new cycle. Failed/partial
observation has no complete fingerprint and cannot reuse a discovery wait.

This work reuses verified silence only. It does NOT relabel content-review
rejection as silence, implement source-specific deferral after exhausted repair,
or make stopping on quality attention a solved problem. Those remain necessary
for the long-lived agent, alongside source fairness and bounded revisits of
linked pages whose bodies can change without a changed search listing. The
existing finite wait window bounds reuse, not a claim that the web is static.
No second physical queue, scheduler, model fallback or action authority is added.
