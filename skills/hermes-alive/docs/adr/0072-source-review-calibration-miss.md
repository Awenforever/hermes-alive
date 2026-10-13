# ADR 0072 — Independent source review remains advisory until calibrated

Status: shadow implementation present; semantic acceptance and delivery gate open.

## Actual experiment

Reviewed the retained `learning-probe:explicit-detailed` candidate rather than
regenerating it. One logical call, one observed HTTP 200, actual reviewer
`claude-haiku-4-5` / `custom:ustc`, distinct from the DeepSeek generator family.
The model returned `supported` and explicitly reported no unsupported guarantee.
The original draft still says "nothing is lost since there's no signup or cost
involved." No signup or monetary cost does not establish zero attention/time or
other loss. This is a missed support problem under ADR 0071, not a successful
calibration or automatic-delivery qualification. The raw output is retained.

Different model families reduce one dependency; they do not confer correctness.
Do not turn this miss into a banned phrase, regenerate a cleaner draft, silently
correct the reviewer verdict, or count a structurally valid verdict as zero error.

## Implemented boundary

The shadow reviewer compares role-labeled, current pinned discovery excerpts,
explicit user context, tentative learned advice and the exact retained candidate.
It records actual model/provider, a host-supplied independence domain, an encrypted
snapshot/findings reference and a durable one-attempt fence. Contradictory results,
same-family review, changed context and erased sources cannot yield a usable
current receipt. Findings grant neither send permission nor real-world truth.
The atomic journal insertion must actually create the start event; an identical
competing insertion returning `created=False` cannot proceed to a model call.
An offline competing-insert fixture verifies zero calls on that losing path.

After the live snapshot, added source publication times and the recorded
interpretation start as a stable historical anchor. The start is NOT claimed to
be the original prompt's exact `as_of` instant; that exact clock was not retained.
This changes the review snapshot and invalidates the old receipt for current-code
reuse. The paid report remains historical evidence of the earlier input, not
qualification of this updated code. No paid rerun was made to conceal the miss.

## Next investigation, not a narrowed goal

Use diverse claim-level synthetic/public cases with expected distinctions recorded
before reviewer calls: faithful compression, supported tentative suggestions,
unsupported guarantees, invented verification, stale time claims, missing caveats
and adversarial instructions. Measure misses and unresolved results separately;
retain raw diagnostic output and bound retries. Explore explicit claim/evidence
reasoning and adversarial counterexamples without requiring literal copying or
tailoring a prompt to this one sentence. No reviewed proposal may become eligible
solely because this uncalibrated assessor says `supported`.

Public users must not be required to acquire a third model/key merely to install
Alive. Model selection remains Hermes-owned. Same-family primary/fallback cannot
be called independent; lack of independent review remains explicit unresolved
evidence, not a covert authority upgrade. The full admission/policy/dispatch/outcome
integration, real user benefit, memory migration and lifecycle acceptance remain
required. Production is still the legacy runtime and was not changed.
