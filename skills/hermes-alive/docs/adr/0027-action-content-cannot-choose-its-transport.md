# ADR-0027: Action content cannot choose its transport

Status: accepted for the shadow kernel

## Context

The first outbox accepted any JSON stored behind a selected candidate. That was
safe while no executor existed, but it is not a capability contract. A model
could place a platform, recipient, profile, thread or tool name inside the same
document as prose and a future adapter might accidentally treat it as routing
authority.

An audit of upstream Hermes main at commit
`79b45d1647f6b5680768d851c4c406e8cc550a1e` found useful public surfaces:
platform adapters expose `send()` and `SendResult`, the platform registry owns
adapters, and `PluginContext.inject_message()` can ask a live gateway to start a
turn. Injection returning true means only that a host accepted the request; it
does not prove that a response reached an external channel. Reaching into a
gateway runner or adapter map is explicitly outside the supported plugin
contract.

## Decision

Candidate action content is a versioned contract. The first executable schema
supports only `hermes.channel.send` and contains exactly:

```json
{
  "schema_version": 1,
  "capability": "hermes.channel.send",
  "operation": {"text": "...", "format": "plain|markdown"}
}
```

Unknown fields are rejected at both the top level and operation level. In
particular, content cannot name a platform, profile, recipient, chat, thread or
adapter. Text is non-empty and bounded. Tool execution and internal review are
not executable until they receive independent schemas and authority analysis.

The send-time authorizer validates the selected encrypted document and binds
its installation-keyed canonical authenticator and schema version into the
authenticated permit. Attempt projection revalidates the document against
that binding. Outbox
materialization and `begin_execution` validate it again before a future bridge
can receive the normalized document.

Transport routing will be supplied later by a user-authorized Hermes capability
binding, not by model-authored content. A host-accepted injection must never be
recorded as delivery success.

## Consequences

- Model output can propose wording but cannot redirect a message.
- A changed, malformed or capability-mismatched document cannot become an
  action attempt or dispatch.
- Existing untyped candidate documents are intentionally not executable.
- The live capability bridge remains disconnected until Hermes exposes or the
  plugin can use a supported route with trustworthy terminal semantics.
