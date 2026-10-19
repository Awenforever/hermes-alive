# ADR 0185: Admit Core's explicit launch-profile scope, not ambient credentials

Date: 2026-10-19
Status: reproduced and corrected; composed/packaging checks pending at writing

## Actual mismatch

Core548e66f `launch_profile_runtime_scope` binds an explicit home override and
its launch secret mapping, but intentionally leaves the optional secret-home
stamp unset. The old acquisition adapter required that stamp unconditionally.
An isolated real-Core reproduction fails inside `_scope` before model invocation.
Earlier synthetic stamped-scope tests did not cover this actual host shape.

## Correction and boundary

Keep requiring an existing Core secret mapping and the exact effective profile.
An explicit stamp must match; an explicit foreign stamp always rejects. When
the stamp is absent, require BOTH an explicit matching home override AND Core's
matching routing-process home. A routed profile cannot borrow this exception,
even with a matching override. An unbound process cannot substitute environment
keys. Never enumerate or load an ambient credential store in the adapter.

This follows Core's launch-versus-routed distinction, not a provider/model-name
special case. Existing lifecycle generation, mapping identity, model-config and
permitted-key currentness checks remain. Replacing the mapping with equal bytes
still invalidates the prior capability. The trusted embedding host remains
responsible for constructing a correct scope and granting explicit secret names;
optional stamps are not cryptographic attestations of a host's correctness.

## Evidence

`probe_alive_core_launch_scope.py` uses actual Core launch and routed context
managers, the Core config loader, native child and AIAgent. Network is disabled;
only model HTTP is intercepted. Two single/multiplex launch modes and two routed
modes pass, with four controlled native calls. `.env`'s synthetic model key beats
a conflicting ambient sentinel without changing parent environment bytes.
Foreign stamps, borrowed unstamped launch maps, absent scope, absent home binding
and expired capabilities reject. No real model calls, channel sends or production
configuration changes occur.

`run_native_core_scope_contract.py` adds portable branch/currentness regression
coverage; it explicitly replaces Core accessors and is not actual Core proof.
The real-Core probe remains separate from source-only portable CI.

`probe_alive_native_living_cycle.py --core-scope launch` replaces manually installed
test scope with the actual Core launch binder and config loader for the complete
feedback/generation/crash/restart/forgetting composition. The first launch of this
new variant fails before model invocation because importing Core creates its home
under the not-yet-created fixture output. Create the new output before Core import,
retain the failure and rerun into a different new output; do not delete history or
relax runtime authority. Its terminal result is recorded separately.

## Not closed by this fix

This corrects an actual host integration prerequisite, not installed off-turn
scheduling or host-owned source-read leases. OAuth/credential-pool renewal and all
provider/platform lifecycle qualification remain open. No production deployment,
independent intelligence proof, personalized quality acceptance or clean real-model
round is inferred from controlled protocol tests. Continue the full long-term
memory/agenda/outcome, useful sharing and migration/acceptance objective.
