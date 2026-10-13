# ADR-0066: Natural expression uses current presentation, never invented meaning

Status: accepted for shadow comparison

## Decision

Connect the existing replayable presentation projection to the model renderer.
Only current explicit preferences affect its bounded style values; advisory and
legacy observations remain advisory. Neutral values remain public defaults, not
an installation-specific persona. The optional language code is trusted host
input, not source text, recipient selection or inferred user identity.

The renderer receives meaning, current style and language as data. It may change
phrasing, not claims, uncertainty, negation, speech act, authority or protected
literals. Warmth and humor cannot manufacture intimacy, feelings, experience,
commitments or actions. The independent reviewer sees meaning and candidate,
not style or renderer identity, so elegance is not a fidelity criterion.

Check current meaning/validated selection and style before/after each async
model boundary. Changed or corrupted context aborts rather than accepting a
stale expression. No inference, route, truth or delivery authority is granted by
style, generation or independent comparison.

## Evidence and remaining work

The composition test selects a typed synthetic share, supplies explicit warmth
and a host language, generates and independently reviews a candidate through
fake providers with distinct family domains. It rejects style changes during
generation/review, meaning withdrawal and invalid language input. Existing
semantic-review-store scenarios still pass. Fake provider success is not model
quality evidence.

The opt-in paired live probe exercises only the exact renderer prompt and
presentation resolution on synthetic public content. It explicitly does NOT
select intent, create a reviewed render, prove semantic entailment or send.
Its two generations need qualitative review; structural checks alone cannot
declare them faithful or useful. Different endpoints serving the same model
family are not independent reviewers. Do not relabel official/USTC DeepSeek as
independent merely to pass a gate.

Still required: generated-opportunity to typed-meaning binding without changing
intent, source lifetime through presentation/dispatch, reviewed render admission,
human-calibrated semantics and naturalness, longitudinal useful outcomes and
current published installation/canary qualification. Atomic network transitions
and retries hidden in the Hermes provider remain outside this boundary.
