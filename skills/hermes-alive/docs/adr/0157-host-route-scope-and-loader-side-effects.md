# ADR-0157 — Host route scope and Core loader side effects

Date: 2026-10-16. Status: diagnostic evidence, not an activated route factory.

## Purpose in the full objective

The native worker must inherit the actual owner's configured model capabilities
without leaking another profile's credentials or dropping fallback/privacy
policy. Correct JSON/process mechanics cannot replace that responsibility or
prove useful long-lived intelligence. Canonical memory/agenda/outcomes,
reflection, external Halo, erasure/migration/rollback and production acceptance
remain required.

## Actual evidence

`probe_alive_native_host_routing.py --core PATH` runs the real Core profile,
config, alias and credential functions in an isolated process. It creates only
two synthetic profiles, synthetic keys and `.invalid` endpoints. Physical
metadata HTTP returns503; DNS/connect/subprocess audit refuses external IO.
No resolver/config/alias/auth function is replaced. There are no native model
calls or channel sends, foreground history reads or production changes.

The successful run uses the complete official Git object archive at
`548e66ff0c3beccec4141d04be88aa6314ada479` — not a partial working-tree overlay.
It reuses retained managed dependencies and is therefore not a fresh official
installation or universal dependency-version proof. The Windows clone fetched
the commit but failed long-path checkout; `git archive HEAD` exports committed
objects regardless of that incomplete checkout. Its cleanup was separately
denied by environment policy and is not retried or bypassed.

For A→B→A, both profiles share the alias spelling `chosen` but not endpoint,
model or key. Actual Core resolves primary, alias and declared fallback to the
proper profile each time, including `key_env` through the secret scope. A
present ambient secret absent from the owner mapping remains invisible under
the explicit multiplex context. The model/config and dotenv source bytes stay
unchanged. Home/secret/multiplex contexts reset after success and exception;
the process environment remains exactly the test's initial ambient environment.

These are **sequential interleaving** checks, not multi-thread race or credential
refresh/pool/OAuth qualification. Core's alias cache is process-global, though
keyed by config identity; this experiment does not prove that every concurrent
host reader is serialized. Do not replace the current-binding check with a
profile name or global last-route cache.

## Failed assumptions retained

1. The older retained Core lacks `frozen_runtime_config`; import failed. This
   does not justify silently dropping isolation or adding a private Core patch.
2. A first latest-Core test tried reading every root entry as bytes and failed
   on a newly created `backups` directory. The next strict-only-backups check
   exposed additional Core first-use scaffolding.
3. Core `load_config_readonly()` means a shared, non-deepcopied mapping, **not
   filesystem read-only**. Config reads keep last-known-good backups. The real
   import/profile helpers also scaffold SOUL/cache/log/hook/skill directories.
   Tests now explicitly enumerate these permitted synthetic first-use effects,
   preserve original config/env bytes, and verify session/memory/pairing/cron
   directories remain empty. They do not claim a zero-write host read.

No unexpected business mutation is reclassified as a success, and no Core
writer is patched out to make a read-only claim pass. Source config mapping
mutations would corrupt Core's shared cache and are prohibited.

## Integration decision

Prefer a trusted host-owned, already bound configuration/capability snapshot,
then resolve/run in a private owned process. A home path alone is not a secret
scope: the host must bind Core's home and owner secret semantics and validate
the current subject/operation before and after work. Never temporarily rewrite
the live Gateway's process environment to serve another owner.

Use Core's actual startup alias/provider/fallback semantics. Do not implement a
homegrown slash split, assume all aliases identify the same endpoint, mistake
requested model for served model, or silently resolve an unknown alias to an
unrelated cloud backend. Preserve endpoint/key pairing and explicit empty
fallback. Refresh/rotating credentials belong to Core; caller-owned factories
must not serialize callable or pool objects as strings or drop them.

ADR0156's admitted route fields do not yet cover every host policy. Full factory
qualification must account for configured request overrides/reasoning/tier,
provider routing/data-collection restrictions, custom headers/TLS/capabilities
and each fallback's own transport settings. Unsupported modes or unqualified
policy must be visible, not erased to obtain a passing text request. Project
only necessary model capability/consented identity, not whole private profiles,
mailboxes, foreground sessions, memories or unrelated credentials.

No automatic factory or Gateway registration is introduced by this diagnostic.
Next implement the explicit host snapshot/projection, connect it to native
worker operation binding and canonical Alive shadow, then compare sustained
real synthetic/public behavior. Keep prior semantic failures from ADR0151/0152
as failures; successful routing is not ten clean intelligent calls.
