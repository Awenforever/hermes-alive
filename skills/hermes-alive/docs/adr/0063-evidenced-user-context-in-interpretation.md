# ADR-0063: Evidenced user context in interpretation

Status: accepted for unscheduled shadow interpretation

The first live opportunity experiment returned only silence with unknown user
interests. Forcing candidates would mask missing context. Interpretation now
reads bounded active, retained owner-scoped preferences, facts and commitments
from typed memory, rather than embedding one installation's interests.

This initial context admission accepts only USER_EXPLICIT records whose original
proposal and source actors/subjects match the requested owner. It binds kind,
predicate, identity and value digest to the original proposal; a mutable authority
label alone is insufficient. Expired, contested, unavailable, model-inferred and
foreign memories are excluded. Oversized values are skipped rather than silently
truncated. The model sees provenance and typed values, not raw conversations.

Model dimension receipts cite the supplied memory proposals and source evidence.
Both context and discovery are revalidated after inference: revocation, correction
or expiry cannot silently admit a decision based on its old profile. The provider
may already have received authorized data before revocation; this cannot erase
remote processing or govern internal SDK retries. Prompt input remains data, not
permission, and default action authority remains NONE. No scheduler or sender is
connected here.

The conservative initial admission excludes user-reviewed model proposals and
system migrations even when legitimate. Generalized provenance-aware retrieval,
purpose/consent policy, trusted gateway-to-memory ingestion, coverage beyond the
512-record scan/eight-context cap, arbitrary cache-tamper protection and semantic
quality remain open. Explicit host identity must still be authenticated by Hermes.
This is not a complete user-profile or production authorization solution.

Deterministic tests cover foreign/private clearance, forged explicit labels,
inferred and expired exclusions, provenance receipts, revocation during model
wait and plaintext exclusion from journal files. Live paired positive/negative
validation has not been performed for this revision. Three of the six previously
approved logical live calls remain; continuation must preserve that accounting.
