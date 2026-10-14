# ADR 0095 — Compose confirmed expression with actual host command

Status: network-disabled synthetic-authority integration; no external delivery,
production activation, semantic admission or portable installation qualification.

## Separate green components were not a composed chain

Earlier opportunity-execution tests validated real kernel authorization/outbox
APIs but did not invoke Hermes. Earlier command probes invoked actual Hermes
commands but did not consume that kernel authorization. The new opt-in
run_alive_kernel_host_expression_chain.py joins these paths without changing
runtime permissions or adding a model-driven transport.

Synthetic discovery, profile, model interpretation and selection produce a retained
expression. The existing test fixture supplies an explicit user confirmation of
both selection and expression, enabled policy and authenticated test-host route.
Source review reads the exact expression and returns an intentionally uncertain
synthetic finding. That assessment remains uncertain and grants no delivery
authority. Permission comes only from the separate exact-confirmation fixture;
the test does not silently turn uncertainty into supported or learned preference.

The real kernel authorizer, attempt projection, leased outbox, start fence,
destination-free contract compiler and pre-launch verifier then pass the exact
expression into OperatorCliProcess. Its child uses the actual pinned Hermes plugin
discovery, platform registry, target/media callbacks, public send command parser
and command handler. The only registered recipient is a disposable local fixture
plugin writing its own profile file, never Weixin, email or a real provider.

The child retains the existing command probe's tested external-network/process
barriers. Docker additionally has network none and only a read-only scratch mount,
no production volume. Parent compiler callbacks and host authority remain synthetic;
the child rechecks with actual host callbacks. This is explicit source command-handler
integration, not an installed console-entry test, genuine user ingress or runtime
capability discovery. Declared test-host version/receipt capability is fixture data,
not an observation that the real host exposes an external-delivery receipt API.

Four command modes exercise success, rejection, partial effect and skip. Local
effect counts are 1/0/1/0 respectively. Every effect preserves the exact confirmed
body and route. The actual command's structured result and inner exit code become
a local authenticated CLI observation; the wrapper instrumentation is not treated
as the command's result. No delivery.succeeded or preference.observed is produced.
Reusing the consumed lease is rejected before another child launch in all modes.
Partial and skipped observations cannot be reclassified as completed delivery.

## Managed-interpreter defect uncovered, not a model outage

Initial child launch failed. A second isolated diagnostic identified missing
ruamel, despite its presence in the parent runtime: Path(sys.executable).resolve()
followed the managed virtualenv symlink to base Python and lost its dependencies.
Both the new test and existing command probe now keep the lexical absolute virtualenv
entry. Operator file pins still hash the underlying executable bytes; no production
dependency was installed or modified. The fix does not qualify an entire import graph.

The first two containers are verified terminal failures before fresh disposable
fixtures are started. They are not reported green or retried on observation timeout.
Also corrected the new observation assertion to use the real report_kind field,
before claiming its success. Failure diagnostics contain only isolated synthetic
content and a bounded exception message; no exported model credentials are used.

## Immutable anchors and results

First snapshot tree 9f2d7c1c33e99ae3b2fdff3d187fcc08f2a35c6c, archive SHA256
21c453386682bb693663a2bc3690781453f59261d4e291f6a9f166f02535ccab.
alive-host-expression-offline-20261014-r1 exited 1, from
2026-10-13T19:56:10.00745621Z to 2026-10-13T19:56:12.42322113Z.
Diagnostic tree 592a6973eedf7ed4d7906e0350ea39442922d98f, archive SHA256
d2e68ea15690ec82155395d90fc67a18f6fab66be8d5f7a16bcfb496c318b16e.
alive-host-expression-offline-20261014-r2 exited 1, from
2026-10-13T19:57:20.438613558Z to 2026-10-13T19:57:23.040380533Z.

Corrected tree 8fccebcd89612f5372d3fb669c3ac8f557381a75, archive SHA256
226f0fdf6dddb2cff8222bd540c25d1418f5ac7c1a6a9a2ba0618ad80f431858.
alive-host-expression-offline-20261014-r3 exited 0, from
2026-10-13T19:58:28.449224475Z to 2026-10-13T19:58:47.577707016Z.
The four-mode composed test passes against explicit core revision
3f2abce7f468cf194bb7f9ff9c6a033b075d834c in the PM-managed Python environment.
This revision is pinned experimental evidence, not a claim of today's latest Hermes.
The first expanded regression alive-host-expression-regression-20261014-r3
exits 1 after expression_support passes: opportunity_execution hits the concurrent
discovery-projector defect investigated in ADR-0096. This failed batch is not
reported green. Independently, alive-host-command-regression-20261014-r3 exits 0,
from 2026-10-14T01:09:18.749922432Z to 2026-10-14T01:09:43.577924454Z:
host_capabilities, cli_execution_bridge and the actual module-bootstrap command
probe pass, including six disposable success/reject/partial/skip/wrong-route/
disabled cases. That module bootstrap is not an installed console entry or a
combined real-user/provider test. ADR-0096 records corrected expanded regression.

No real model/HTTP calls: cumulative actual totals remain 95 logical / 107 HTTP
attempts. No private conversation access, production deployment/restart/model/
channel/auth change, wmw change or other-plugin change. No temporary credential
export. Full goal remains open: calibrated provenance/semantics, genuine host
ingress and grants, trusted delivery/outcome attribution, useful feedback learning,
layered/external memory, sustained agenda/adaptation, physical forgetting,
migration/rollback, current portable installation lifecycle and production acceptance.
