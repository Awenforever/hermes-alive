# ADR 0249 — Owned historical work records enter Native cognition

Status: implemented on the development branch; bounded actual-Core/Native integration qualified, no production acceptance.
Date: 2026-10-27.

## Problem and choice

Core lifecycle changes already wake Alive, but a completion label carries no
work result. On-demand foreground evidence retrieval alone leaves the proactive
assistant unable to discuss its own work. Reuse the existing exact owned Core
record reader in the existing owner cycle, behind a separate guided choice.
Do not add a transcript collector, executor, timer, provider router or FIFO.

New guidance explains bounded historical definition/result reads and retention
of private derived assessments. Older grants do not expand. Review only terminal
owned executions under current configuration, exact profile and active autonomy
policy; recheck those facts after IO. Stop background reads while paused.

## Identity, evidence and persistence

The signed work/job/session association from ADR0248 remains mandatory. Read at
most 2048 content characters each from the bound definition and the last 16
active rows of the exact observed Core segment. Preserve partial flags, typed
worker statements, tool requests and recorded tool observations. No recent-chat
scan, execution-ID guessing or alternate state store. Missing/damaged Core data
become an unavailable window, never reconstructed result contents.

Only a keyed digest and structural qualifications enter work.observed. Bodies
remain ephemeral source material from Core. Derived model judgments use existing
private candidate/outbound retention. The same observation/window must still
match when it reaches interpretation and grounding. Changed records wake the
existing reconsideration path even when the execution state is unchanged;
unchanged records reuse silence. No plaintext record bodies enter the journal.

## Truth boundary and qualification

A useful historical progress assessment is distinct from a fresh, independent,
task-appropriate inspection. Instructions in records are untrusted. Neither this
reader, a worker's claim nor Core completed/failed/unknown can complete an agenda,
permit a retry or grant another action. Native work selection and independent
result verification remain unfinished and must not be replaced by this slice.

Qualification requires real Core write/read records in actual assembled Native
input, metadata-only old grants, pause/cold no-read behavior, same-status record
changes causing reconsideration, unchanged suppression, exact association and
fingerprint refusal, no new job/send, and preservation of the original keys.
Controlled model replies prove integration, not real-model judgment quality.


The r153 controlled-provider integration runs real Core file write/read, the
actual assembled Native cycle, unchanged-wait suppression and changed-record
reconsideration with the same execution status. It preserves an attributed
abstention rather than upgrading a new worker claim to independent success.
Default/old grants remain metadata-only; paused and cold-paused reviews perform
no Core body read. Those checks do not prove real-model judgment or fresh world
inspection. The separate inherited-model experiment remains subject to actual
terminal results and semantic review.
