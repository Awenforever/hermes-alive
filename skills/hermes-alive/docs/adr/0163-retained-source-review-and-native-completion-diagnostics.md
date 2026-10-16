# ADR 0163 — Retained source review and native completion diagnostics

Date: 2026-10-17
Status: active investigation; no production deployment

## Why

ADR0162 retained a real semantic failure: after explicit withdrawal of a topic
pause, a concise candidate returned but lost the material qualification that its
source was fictional. A model's self-assessment and rejected_count0 did not catch
this. Review must consume the exact retained source, feedback and candidate;
correction must remain a new model decision, not a keyword patch or appended text.

## Decisions

- Preserve the original longitudinal journal and encrypted content. The opt-in
  retained-review probe copies the original kernel into a new private case. Its
  explicit vault selection matches the original fixture's shared outcome vault;
  never search other vaults after a failed lookup or alter the original evidence.
- Source review accepts a finite per-call timeout in [1,240] seconds. Invalid
  values reject before reading its snapshot or recording a started operation.
  The existing default remains40. The native caller still cannot exceed its
  host-owned lifetime. The probe sizes its owned lifetime explicitly, not by
  silently widening production budgets.
- Different-family isolated review preferentially requests qwen3.8-reasoner,
  following the user's successful service records. Actual completion model and
  provider, not the requested label, determine the observed route. A DeepSeek
  fallback cannot qualify as independent review of DeepSeek generation.
- Native completion failures expose bounded structural diagnostics: terminal
  kind, text length, tool count, result flags and equality checks. No raw failed
  output, opaque finish-reason text, provider exception, prompt or secret is
  retained in these diagnostics. Acceptance is not relaxed by diagnostic matches.
- Native completion evidence v3 binds both raw source hash/length and projected
  final hash/length. Its only admitted projection is `outer-whitespace-v1`, the
  exact Python strip operation observed in Core's turn_final_response. Raw text
  remains transient; fingerprints retain its provenance. There is no fuzzy match,
  internal whitespace collapse, JSON repair, semantic rewrite or think-block
  removal. Those changes still fail. Session/turn/route/flags/attempt checks all
  remain mandatory. Private protocol fixtures now supply the v3 evidence; this
  is not a production migration of persisted Alive content.

## Evidence and limitations

Cases are under /tmp/hermes-alive-installed-RJbQNAiD on the NAS. All use synthetic
public scenarios, inherited model-only credentials and isolated native Core.
There are no channel sends, private-chat reads or production model edits.

- retained-review r1 failed the experiment's vault choice before inference (0).
- r2/r3 requested Qwen3.8 but lacked accepted completion and sufficient structural
  diagnostics. Do not retroactively infer why those attempts failed.
- r4 requested Qwen3.6, actually completed through official DeepSeek fallback;
  its unsupported verdict identified the lost qualification. Independence refused.
- r5 was explicitly correlated diagnostic work, not independent acceptance.
  USTC DeepSeek review rejected the unsupported candidate; model revision using
  recipient meaning then abstained. Two calls, no forced suggestion or send.
- r6 requested Qwen3.8 with90 seconds and timed out with its owned lease closed.
- r7 requested Qwen3.8 with180 seconds. Native Core reported completed=true,
  all failure/transformation/reuse flags=false, one observed stop response,
  876 content characters and no tool calls. The final completion proof still
  failed. This contradicts 'model unavailable' and narrows the problem to final
  text/coordinate matching. It does not yet identify the mismatched field.
- r8's result proves the particular mismatch: one stop response has959
  characters, the final has957, all four coordinates match, exact text=false
  and raw.strip()==final=true. This is direct evidence of the inspected Core
  outer-whitespace step, not speculation about unavailable models or parsing.
  It remains a failed original attempt, not retrospectively promoted to success.
- r9 runs the v3 fix prospectively, requesting Qwen3.8. The actual route falls
  back to official DeepSeek, which produces an accepted native completion and
  unsupported verdict. Independence rejects it; correction does not start. One
  logical call, not evidence that Qwen was used or that repair succeeded.
- r10 prospectively completes with actual qwen3.8-reasoner, provider custom:ustc,
  one logical call, no error and independent_review_proven=true. Its unsupported
  verdict identifies the omitted fictional-source caveat. This validates the
  requested cross-family review path, not universal reviewer correctness or
  automatic delivery permission. No correction/final expression occurs in r10.

Cases r1-r10 are terminal, containers absent, temporary credential projections
removed and absence verified. No live worker remains. r2-r10 used ten logical attempts including
failures; physical HTTP totals were not instrumented. Do not count these cases
as zero-error acceptance rounds.

New diagnostic tests prove bounded replay storage, opaque-reason redaction,
bool/count rejection and no raw partial-response disclosure. Exact-completion
and protocol tests pass locally, including rejection of changed internal lines,
think removal, unsupported projections and malformed source metadata. These
four new regression entries are now part of run_all.sh rather than only operator
commands. Source-support/history/completion/protocol/host-caller/host-snapshot/
client-policy all pass in a network-disabled retained Hermes runtime; the default Windows Python
lacks cryptography, so its source-support attempt failed before model work.
No dependencies were installed globally to hide that environment difference.

## Next

Resolve native proof mismatch without arbitrary normalization, route guessing
or disabling provenance checks. Then exercise the composed recipient-meaning,
source/purpose review, bounded correction and final-expression path on new
materials and across restarts. An independent reviewer can still be wrong;
neither one good verdict nor safe abstention proves sustained usefulness.
Layered/external memory, agenda, learning, erasure, migration/rollback, portable
lifecycle and production acceptance remain required, not replaced by this probe.

Actual Core548e66f managed-host probes also pass constructor/prompt boundaries,
shadow/source boundaries, scoped completion, and pending-request cancellation
with observed child termination. Their physical HTTP replies are controlled
synthetic fixtures with networking disabled; these are integration proofs, not
additional real-model calls. All seven adjacent contract entries above pass
under the same installed Hermes interpreter. No production Core was modified.
