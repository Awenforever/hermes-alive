# Public command transport — local integration evidence

Date: 2026-10-12

Upstream: `3f2abce7f468cf194bb7f9ff9c6a033b075d834c`

Host: native Windows; independent test venv, not a PM-installed Hermes profile.

## Actual path

`register_send_subparser` → `cmd_send` → real gateway config loader → actual
plugin discovery → public `register_platform` → official standalone sender
routing → test-only local file sink → actual CLI JSON/exit status.

No core function, gateway reference, adapter map, registry lookup or result
emitter is patched. The fixture registers a custom **platform**, not the
intentionally absent `send_message` model tool. Each case has a separate
temporary home and explicitly enabled fixture plugin/configuration.

| Case | Exit | Local fixture effect | Actual result |
|---|---:|---|---|
| Success | 0 | One complete synthetic body | `success=true`, fixture receipt ID |
| Refusal | 1 | None | Error |
| Partial | 1 | One partial synthetic effect | `partial_success=true`, error |
| Cron duplicate | 0 | None | `skipped=true`, `success=true` |
| Other destination | 1 | None | Receiver fixture refuses the route |
| Disabled channel | 1 | None | Core rejects unconfigured/disabled channel |

Wrong-destination refusal is the test receiver's policy, not proof of Alive's
outbox authorization. No fixture receipt establishes real-user delivery,
reading, task completion or usefulness. All cases explicitly retain
`external_delivery_proven=false`.

## Isolation and diagnostics

- Environment allowlist excludes production profile, providers, proxies and
  credentials. Only synthetic bodies and fixture chat identifiers are used.
- DNS, datagram sends and non-loopback connections are refused by audit hooks.
  Loopback sockets remain available for CPython's Windows asyncio internals.
  This is not an OS network sandbox or a hostile-plugin isolation claim.
- Process launch is refused except exact read-only Git provenance queries in
  the named upstream checkout. System/global Git configuration, optional
  locks and lazy fetch are disabled for the child. No shell command is allowed.
- Negative checks prove a documentation-address connection and Python child
  launch are refused before those external effects occur.
- An initial blanket subprocess prohibition broke core Git version lookup;
  this was not a system-version query or a transport bug. Kept the narrow
  provenance allowance instead of patching Hermes or allowing arbitrary calls.
- Missing `dotenv`/`httpx` prevented relay-route validation. Installed actual
  dependencies only in the independent test venv, never fabricated an absent
  relay module or bypassed its guard. Test dependencies include declared
  `ruamel.yaml=0.18.16`, `python-dotenv=1.2.2`, `rich=14.3.3`,
  `certifi=2026.5.20`, and `httpx=0.28.1`. This is not full lockfile/PM parity.
- Fixed UTF-8 child environment and capture decoding after Windows locale
  decoding failed on diagnostic text; refusal diagnostics remain visible.

## Remaining qualification

The six-case probe additionally passes compiled input through `OperatorCliProcess`
to a separate child, which rechecks the plan with actual host callbacks before
calling the public command handler. Executable and four exercised source files
have pre-launch hash checks; this is not full runtime/import-graph identity.
ADR-0058 documents timeout/capture semantics and resource/privacy limitations.

The command probe now compiles its text action through the actual host profile
getter, destination resolver and media parser, then supplies the unchanged body
through stdin. Negative preflight checks verify actual host attachment controls
are refused before fixture delivery. Six cases passed again with this path.
This closes a text-plan integration check only; it does not prove an authorized
process launch. ADR-0056 records the media/format limits and required follow-up.

The full CLI bootstrap, PM-managed runtime, real external channel and its
acknowledgement contract, Alive's authorized outbox bridge, crash recovery,
human usefulness and longitudinal behavior remain open. Production remains
unchanged. This test is a transport-integration step, not production acceptance.
