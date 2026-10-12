# ADR-0050: Real package placement is not runtime admission

Status: accepted test/installation contract; complete admission remains unproven

## Decision

Add an opt-in installation smoke runner requiring an explicit Hermes source
root and dependency-install consent. It uses a disposable profile and local
fixture Git package, keeps security scanning enabled, verifies the imported
Hermes source location and invokes the public package CLI. It must verify the
plugin's status command loads in the intended profile before installing hooks.
Planned lifecycle checks cover repeated runtime install, owned hook removal,
reinstall and retention of synthetic user state. It never starts a gateway.

Neither the Installed banner nor a zero CLI exit code proves dependencies were
admitted. A refusal stops before runtime writes. Dependency management remains
Hermes-owned; the plugin must not add its own pip/provider repair path.

## Evidence on 2026-10-12

- The bare historical image CLI has no `--yes-deps`. It cannot qualify the
  current installation contract. Used read-only official source snapshot
  `f925b01791fe052e7d55dc975750c0bd985aff91` instead, with a `/core` working
  directory and verified module path. PYTHONPATH alone did not override the
  old image's working-directory import priority.
- Real scanning refused a negative URL-validation test citing a sensitive
  system filename, before dependencies. The validator rejects schemes and
  never opens that URL. Replaced that unnecessary host-specific sample with
  four synthetic non-web schemes, preserving and expanding rejection coverage.
  No scanner setting or dangerous-verdict override was changed. Ordinary
  reviewed fixture installation still uses the contract's `--force`.
- Offline admission then failed while fetching Hermes-managed Python. No
  lifecycle runtime command ran; this is a failed attempt, not qualification.
- A resource-limited disposable container used the user's NAS proxy and
  fetched Hermes-managed Python/uv. Core psutil Git fetch later disconnected
  with HTTP/2 CANCEL/early EOF. The CLI printed Installed but explicitly kept
  the plugin disabled; the following Alive CLI was unavailable. Full runtime
  lifecycle checks were therefore not reached.
- This exposed the need for the status-readiness gate, added to the runner and
  SKILL installation contract. Do not claim dependency/lifecycle success.
- Injected runner-contract regression verifies zero-exit installed-but-unloaded,
  malformed status, wrong profile, failed status and already-proactive state
  cannot reach `install-runtime`. This is test-runner fault proof, not a real
  dependency-install pass. The local expanded discovery scheme test also passes.
- Test containers terminated; their temporary source archives and directories
  were removed. Production was still running with its original start time.

## Limits and next work

The source snapshot is not a claim about today's newest upstream commit.
The initial tzdata warning came from bare PluginManager loading, which does
not exercise dependency preparation; it was not proof of a missing declaration
or a broken package-manager contract. Successful current-runtime admission and
the full install/upgrade/uninstall/reinstall matrix remain open. Core dependency
transport is not an Alive model problem and production is unchanged.
