# ADR0229 — A slow review needs an assessed interval, not a newer timestamp

Date: 2026-10-25 (Asia/Shanghai).
Status: real slow-review refusal reproduced; interval protocol under qualification.

The real r73 final review itself took408seconds after primary timeouts and Core
fallback. It assessed value at its start; the existing five-minute freshness
check correctly refused the now-old point assessment. Relabeling that receipt
with its completion time would assert something the model was never asked.
Increasing a global TTL would also conceal the mismatch.

For discretionary discovery final reviews, request an explicit bounded interval
from the host review start to its configured stage deadline, at most600seconds.
Supported must mean the exact message remains temporally faithful and useful
throughout that interval under unchanged supplied source and owner context.
Known dates/conditions must not be assumed frozen. A review unable to support
the interval must remain negative or uncertain; no unknown-world prediction or
delivery permission is implied. No extra inference or verdict field is added.

Record review-window-v2 and the bounded duration in both host receipts; retain
the exact as-of and end timestamps in the protected review body. Reconstruct the
request/prompt, require matching original chronology and reject a completion
outside its interval. A valid interval receipt can be used at completion only
inside that originally assessed interval. Authorizer caps its usual short
physical permit at the interval end. Old permits never renew, and old point
receipts retain their original five-minute semantics rather than becoming
interval proofs. Generic fact-only reviews and admitted commitments are not
promoted. Protected discovery warnings keep their exact meaning constraints.

All original route, delegation, policy, source, retention and unchanged-owner-input
checks still apply. Qualify negative, missing, copied/retimed, expired, future,
over-budget and protected-warning cases through actual encrypted APIs. This
timing repair establishes no content quality: r73's data-heavy message remains
a failed intelligibility sample. Do not count it as a useful acceptance round.
