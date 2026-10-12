# ADR-0046: Factual replay has sequence and observation-time boundaries

Status: accepted for shadow evaluation

## Decision

`build_factual_episodes` accepts an optional timezone-aware `observed_by`.
Sequence bounds describe journal availability; clock bounds describe when
evidence had been observed. Historical clock evaluation requires both, not a
sequence-only approximation. Attempts later than the clock boundary are
excluded. An outcome label requires its outcome record and originating
observation to be inside both boundaries. Equality is included.

Naive timestamps are rejected rather than guessed in a local timezone.
Omitting the clock bound retains the existing sequence-snapshot API; it must
not be presented as a retrospective wall-clock evaluation. This is a read-only
filter: no history alteration, receipt rewriting, resend or production change.

## Evidence

The outcome integration regression exercises authenticated dispatch evidence
at the microsecond boundary, equality, an attempt not yet observed and naive
timestamp rejection. A separate mocked host-clock-skew case places the source
receipt after the cutoff while keeping the outcome record before it; this
label is excluded as well. Existing evaluation leakage and outcome rebuild
tests remain valid.

## Limits

This does not repair skewed host clocks or define an operational reconciliation
clock. Duplicate observations, the difference between task completion and
user benefit, remaining projection integrity, human calibration and live
longitudinal qualification remain open. Production is unchanged.
