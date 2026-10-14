# ADR 0111 — Reopened feedback-aware planning, not a usefulness claim

Date: 2026-10-14

## Purpose

Move from ingress prerequisites back to the Alive autonomous-loop milestone.
Verify that discovery, retained feedback advice, explicit memory and cognition
selection remain connected across separate reopened instances and withdrawals.
This exercise owns no platform FIFO and sends no messages.

## Evidence

`run_alive_kernel_longitudinal_planning.py` runs four distinct planning cycles
against one journal, reopening all planning collaborators for every cycle:

1. No current interest evidence: a controlled interpreter abstains; the actual
   cognition coordinator closes with silence without calling a selector.
2. A synthetic authored-feedback observation is added through existing real
   outcome/preference projection APIs. The reopened interpreter receives its
   rationale and advisory scope; an actual model-planning frame selects the
   fixture proposal. Candidate dimensions retain the observation's evidence ID.
3. An explicit user-authored memory boundary is added. Both learned advice and
   explicit context reach the interpreter; the controlled model oracle gives
   precedence to the explicit boundary and actual cognition selects silence.
4. Explicit memory and the learned observation are withdrawn. Reopened cognition
   sees neither. It stays silent; the previously completed interpretation cannot
   be loaded as a current executable draft. Historical selection bytes remain
   unchanged rather than rewriting history.

Another subject's feedback is seeded but never enters the owner's prompt.
Recovery without a renewed trusted host authority yields `ActionAuthority.NONE`;
passing a trusted synthetic authority explicitly recovers the original draft.
None of the four cycles creates an action attempt or external dispatch. The two
attempts in the journal are explicitly seeded synthetic feedback fixtures.

Windows Python 3.14 test passed. Linux test passed in
`alive-longitudinal-planning-offline-20261014-r3`, exit 0, network disabled,
1 CPU/2 GiB/256 PIDs, read-only isolated scratch mount. Test-file SHA-256:
`8a69f6e58bc19082e53db9f00973dafcc630f015f0ba29e8d1ce14d665d8563b`.
Its dependency source is the unchanged ADR-0110 r4 snapshot. This is not a new
whole-repository installed-runtime qualification or a production deployment.

Initial Windows failures were test expectation errors: implicit recovered
authority is deliberately NONE, and a successful withdrawal's projection result
is `retracted`, not `recorded`. Product code was not relaxed to fit those assertions.
Linux r1/r2 failed before Python execution (read-only nested mount creation and
missing host-managed interpreter mount). r3 uses the existing carrier's actual
read-only `/test` mount. Preserve these distinctions rather than calling failed
attempts product regressions or hiding them in a success count.

## Limits and next integration step

All model responses, feedback ownership and attribution are controlled synthetic
fixtures. The model oracle deliberately reads the expected prompt state; this
does NOT prove semantic intelligence, satisfaction, calibrated confidence or
natural expression. Feedback is not collected through real chat ingress here.
It does not establish delivery or automatically derive an action grant from
advice. It is only a cross-cycle structural regression.

The next milestone remains the runtime composition of discovery, model planning,
expression, authorized host delivery and trustworthy feedback. Qualify actual
model interpretation on new public/synthetic longitudinal scenarios separately;
do not turn these controlled responses into deterministic production rules.
Production, public release versions and other plugins remain unchanged.
