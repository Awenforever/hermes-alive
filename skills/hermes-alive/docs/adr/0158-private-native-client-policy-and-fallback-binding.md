# ADR-0158 — Private client policy and fallback binding

Date: 2026-10-16. Status: implemented opt-in boundary; incomplete host factory.

## Why this advances the full objective

Long-lived useful intelligence must respect the actual owner's model and privacy
policy, not just obtain a valid JSON response. ADR0156's resolved API route did
not carry provider routing restrictions or endpoint-specific client settings.
This change adds a model-only client policy projection to the private native
worker. It does not activate the experimental kernel in production, replace
Hermes model configuration, own a platform FIFO, or prove semantic usefulness.

## Implementation and qualification

The finite private request now admits AIAgent provider allow/ignore/order,
sort/require-parameters/data-collection/quality-floor and boolean capability
arguments. Common headers and endpoint-specific headers/TLS-verification flags
are detached into the worker's own config before real Core imports. Core owns
client construction, protocol normalization, fallback and completion events.
Private config cannot inject plugins, hooks, sessions, tools, mail credentials
or arbitrary files. A header policy may cover only declared primary/fallback
endpoints; duplicate/unbound routes and CR/LF header injection reject before a
worker starts. Secret header values are not printed in diagnostics.

Named custom provider identity is preserved in the private provider entries;
generated positional names must not replace an existing named identity. Primary
and fallback therefore retain separate endpoint header policies. Explicit empty
fallback remains empty. Existing worker checks bind completion to owner,
operation, context and native API evidence; no authority is granted.

Windows `run_native_client_policy.py` and `run_native_worker_protocol.py` pass.
The actual Core probe uses complete official commit548e66f, retained managed
dependencies, no network, private synthetic profiles and controlled physical
HTTP only. r3 proves actual primary403 -> named backup uses the corresponding
key, common header and endpoint header; both requests are observed, followed by
native completion and canonical Alive shadow/replay success. Existing primary,
alias and fallback probes also pass. No model endpoint, chat or mail was called.
This is not a fresh install or production test. Routing arguments are admitted
and forwarded, but this run does not prove OpenRouter privacy fields on wire,
every transport or TLS trust-store behavior.

## Failures retained and present limitations

r1 timed out. r2's operator-only diagnostic recorded primary key/common/route
header correct; anonymous custom fallback key/common correct but route header
incorrect. The assertion remained a failure and Core retries ended at the owned
process timeout. No production Core was patched, no assertion weakened, and no
timeout was reclassified as success. r1/r2 test snapshots remain evidence.

Actual Core's anonymous custom fallback resolution does not carry the named
endpoint header block in this configuration. The new boundary explicitly
rejects anonymous fallback + endpoint headers before any request. It does not
invent a provider name or silently drop the header. The r3 positive test uses
an explicitly supplied synthetic named fallback; it does not resolve the
anonymous case. That remains required before broad host-factory admission.

Client policies on non-chat transports and external CA-file paths are currently
unqualified and explicitly rejected. Existing no-policy worker routes retain
their previous behavior. Full host projection still needs actual Core alias/
credential resolution in the private worker, per-model routing, model-scoped
request/reasoning/tier settings, TLS/headers across every admitted fallback,
rotating/OAuth/pool capabilities and safe credential selection. None may be
silently discarded. A host factory must surface these limits rather than claim
complete config inheritance from this intermediate boundary.

Next connect the trusted bound snapshot and real private resolver, qualify the
remaining policies, then run sustained real public/synthetic autonomous cycles.
Prior semantic failures, reflection/outcome learning, Halo, erasure, portability,
migration/rollback and production acceptance remain open in the living plan.
