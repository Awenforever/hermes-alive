# ADR 0250 — Qualify Core's read-only inspection composition before autonomous use

Status: bounded actual-Core capability qualified in isolated Linux Docker; autonomous inspection is not connected.
Date: 2026-10-27.

Historical work records cannot prove the current result. A fresh inspection must
use Hermes' own execution/permission machinery and must not silently repair the
artifact it is checking. First qualify a narrow file-read composition through
Core's public create_custom_toolset API, rather than aliasing a handler, calling
the raw tool registry, changing Core, or inventing a script executor.

The composition references only existing Core read_file. It registers no handler,
grants no operation, selects no model and starts no job. Core still subtracts
user-disabled toolsets and owns dispatch/approval. Before any future handoff,
inspect Core's actual ordinary cron tool selection; missing/conflicting or
broadened composition must fail closed. no_mcp prevents an implicit MCP expansion.

Core custom compositions are process-local metadata; supported plugin loading
registers the same public composition in each worker/cold process. The public API
has no unregister operation. It contains only an existing tool name, no callback,
secret or action authority; process exit removes the metadata. Unload/disabled
plugin and prepared-job behavior still require lifecycle qualification before
this can authorize a product action. Do not mutate Core's private registry or
TOOLSETS dictionary to manufacture cleanup or bypass a disabled file toolset.

The integration test must use actual Core cron/Agent/read_file, a controlled
provider attempting a forbidden write, independently changed current file data,
no external delivery, disabled-file and disabled-composition checks, and a fresh
process loading the installed plugin. Read results must contain the fresh data;
file contents must survive the forbidden write attempt unchanged. This is a Core
capability qualification, not autonomous task assessment, arbitrary API inspection
or an argument that every tool called read-only has no possible side effects.

Next: bind inspection intent to the exact owner, original assignment/version,
owned producer work and current guided automatic scope; reuse Core job ownership
and crash uncertainty. Carry the attributable fresh observation into Native's
next decision. Keep autonomous work selection and agenda closure distinct from
record review and from a file-read capability test.


## Observed capability qualification

r159 uses the installed candidate in actual Core cron/Agent execution. The model
request exposes only read_file; the controlled model's write_file attempt is
refused, the subsequent read returns independently changed fresh contents and
the OS-level artifact remains unchanged. Both file and composition disablement
remove the effective read capability. A separate cold process reloads the plugin
and obtains the same composition. Only one local-result Core job exists; no
real provider/account/channel is involved. Process and container cleanup complete.

Earlier fixture runs are retained as failures: metadata/model probes without
tools were incorrectly counted as job inference steps, and provider assertion
failures disconnected HTTP rather than producing a diagnostic response. The
corrected fixture distinguishes its synthetic task from auxiliary probes and
honors requested stream/nonstream responses. It does not relax the real job's
scope or fresh-result assertions. These proofs do not certify every Core topology,
future release, independent goal judgment or automatic inspection authorization.
