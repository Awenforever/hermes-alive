# ADR-0014: Content retention requires per-user Hermes authority

Status: accepted for the shadow kernel

## Decision

Conversation content retention is off by default and scoped to a stable,
installation-local pseudonymous user. It can be enabled only through Hermes'
own authorized slash-command path:

```text
/memory alive retain on [1-365] [inbound|outbound|both]
```

The plugin intercepts only the `alive` sub-namespace; every other `/memory`
operation remains owned by Hermes. The gateway performs pairing and slash
access control before the hook runs, so Alive does not duplicate channel-
specific authorization or depend on Weixin Enhance.

Authorized content goes to the AES-GCM content vault with a fixed expiry and
`restricted` sensitivity. The immutable journal receives only an authenticated
opaque reference and consent event ID. Hermes currently gives hooks at most 500
characters, so the record declares that it may be truncated and never claims
to be a complete transcript. Tool arguments/results remain excluded.

Stopping future capture and erasing existing content are distinct:

- `retain off` stops new content but preserves existing expiry;
- `forget` durably records a self-authorized request, erases live ciphertext
  and affected managed backups, then records completion.

Pending erasure and ordinary retention expiry resume at gateway startup even
when decision-kernel shadow capture is disabled. A model-authored event cannot
grant consent.

## Consequences

- Fresh installs and silent users remain structural-only.
- Different users of one Hermes instance cannot grant retention for each other.
- Journal replay reconstructs the latest consent without plaintext commands.
- Erased content remains visibly unavailable rather than being reconstructed
  from model output or append-only history.
- Content interpretation and memory promotion remain later, separately gated
  operations; retention alone grants neither.
