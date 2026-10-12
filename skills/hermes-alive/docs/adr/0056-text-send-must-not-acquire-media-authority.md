# ADR-0056: Text send must not acquire media authority

Status: compiler implemented and isolated command path verified; live executor pending

## Evidence and decision

Current audited Hermes source (`3f2abce7f468cf194bb7f9ff9c6a033b075d834c`)
interprets `MEDIA:` and document/voice directives in message bodies. A known
attachment extension can be recognized even when the file does not exist.
Extensionless paths can depend on later filesystem state. An empty extraction
at one instant therefore does not prove a later send remains text-only.

The current `hermes.channel.send` action contract grants text, not file access.
Passing arbitrary generated text to this backend without qualification would
silently broaden authority. Reserve the backend's media-control namespace,
including quoted examples and case variants, and reject rather than rewrite
such actions. This is a protocol/capability boundary, not a topic filter or
per-example content patch. Future media sharing needs its own explicit typed
authority and a qualified transport; this restriction is not a permanent
reduction of the Alive objective.

`compile_text_cli_plan` additionally requires an explicit, complete route,
an existing absolute operator-owned profile home, matching actual host profile
discovery, exact host destination resolution, and unchanged text extraction.
The body is passed through stdin, not command arguments. Plan representation
hides the body, home and destination. No destination is inferred or selected
from model output. The current public CLI cannot force plain rendering, so
this compiler rejects plain-mode requests rather than silently changing their
meaning. Markdown rendering still belongs to each platform and needs its own
qualification.

## Validation and limits

- Unit tests exercise route/profile mismatch, altered parsing, media controls,
  multiline Unicode preservation, threaded routes and representation privacy.
  Their stub callbacks are not evidence of host compatibility.
- The separate current-source command probe uses actual public profile lookup,
  destination resolution and media extraction before the real public command
  handler. It proves host media interpretation and preflight rejection before
  any fixture delivery. All six discovered-local-platform cases pass with the
  compiled stdin plan: success, refusal, partial effect, duplicate skip, wrong
  receiver and disabled channel.
- The compiler is not an authorization, lease or executable permit. A trusted
  executor must bind its callbacks to the runtime/profile it will actually use,
  acquire a fresh authenticated execution start, and recheck runtime identity
  before launch. Caller-supplied callbacks cannot establish this by themselves.
- Full CLI bootstrap, PM-installed runtime, process launch, real platform
  receipts, ambiguity recovery and human usefulness remain unqualified.

No production deployment, real message, profile change or restart occurred.
