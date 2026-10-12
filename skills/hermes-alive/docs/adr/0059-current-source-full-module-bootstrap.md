# ADR-0059: Current-source full module bootstrap

Status: six native Windows bootstrap cases passed; installed-runtime gate remains open

## Evidence and correction

The earlier local platform test entered the real command handler but not
`hermes_cli.main` bootstrap. Its new opt-in `--full-bootstrap` path enters
the actual module as `__main__`, retaining Hermes's bootstrap, profile selection,
dependency activation and dispatch. It receives compiled arguments and stdin
body, discovering the disposable local-platform plugin through the public loader.

All six cases passed on native Windows against audited source
`3f2abce7f468cf194bb7f9ff9c6a033b075d834c`: success, refusal, partial effect,
cron duplicate skip, wrong receiver and disabled channel. The initial full run
failed cron-skip because the new harness omitted its cron context variables;
three preceding cases passed. Restored the test precondition and reran all six.
No core or production fix was required; a fixture omission is not a transport bug.

## Isolation and limits

Every case uses an independent temporary profile, synthetic config and local
platform. No production credentials, history or model routing are copied; no
gateway runs. Existing network/process barriers run before bootstrap. Selected
Python filesystem audit checks refuse writes outside the disposable profile to
avoid source self-recovery mutations. The upstream tree remains clean afterward.
These checks are not an OS sandbox, hostile native-code protection or complete
filesystem mediation. Diagnostics belong to the synthetic fixture environment.
No dependency was added and no upstream file changed during this test.

This proves actual source module bootstrap/local routing on the independent test
venv, not the generated installed console entry, PM-selected installed generation,
full dependency parity, profile migration, external delivery or useful autonomous
behavior. The stdout wrapper is test instrumentation, not a host receipt API.
Older PM admission/lifecycle evidence remains separate and cannot be promoted
into a current installed-runtime pass. Next qualify that installed path while
continuing semantic shadow and longitudinal quality work. Production unchanged.
