# Discovery Development

## Collection and sharing are separate

Discovery collection can gather and rank several candidates in one batch.
Proactive sharing consumes at most one eligible candidate per action.

A cached batch may be reused across watcher ticks. Every read revalidates
external candidates against persistent topic history:

```text
collect batch
  -> normalize and rank
  -> filter duplicate/reserved/delivered topics
  -> expose eligible cached view
  -> share one
  -> commit delivery or release reservation
  -> next tick selects another unseen candidate
```

The complete cached batch is not mutated when an item is shared. Exhausted
caches return no external candidates instead of replaying old content.

## Final source witnesses

A source reviewer can cite the exact Markdown wording or the contiguous visible
inline wording of a claim. The host derives visible wording with the CommonMark
parser and retains the original message and passage identifiers. A witness
cannot join separate blocks or span an image. Evidence quotations and numeric
occurrence coverage still use the original retained material.

Numeric coverage distinguishes structured names from quantities. A witnessed
model or version name must occur as a whole in the same retained source.
Measurements still need local evidence in the cited passage. The source review
also checks whether that measurement applies to the named model, track and
conditions. Retained decisions use the contract under which they were made.

## Topic identity

Identity combines:

- canonical URL when available;
- semantic topic signature when URL is absent;
- content/update fingerprint for material changes.

Equivalent URL spelling, language changes, tracking parameters, percent-encoding
variants, and semantic rephrasing must not bypass deduplication. IPv6 authority
and invalid-port handling are normalized safely.

Persistent history stores hashes rather than raw URLs or titles.

## Topic states

Conceptual states:

```text
UNSEEN
RESERVED
DELIVERED
SUPPRESSED
MATERIAL_UPDATED
```

Reservation and delivery are atomic across processes. Failed sends release the
reservation. A delivered topic may return only when a verifiable material-update
fingerprint changes.

## Current source types

Hermes Alive supports API, RSS/Atom, ordinary HTTP, and optional browser-backed
collectors. Current integrations include papers, repositories, technology news,
Chinese community feeds, video trends, and selected lifestyle/discussion
sources.

Candidates are normalized into editorial lanes (`current_affairs`,
`local_hefei`, `culture_people`, `social_fun`, `technology`, and `academic`).
Freshness is enforced per lane and the final batch is round-robin interleaved;
source type alone never awards a paper or repository a higher score. Configured
news-search queries are editorial inputs, so regions and interests can be
personalized without changing Python code.

Authenticated social platforms are not treated as reliable anonymous sources.
They require an explicitly authorized, private browser state; when unavailable,
the source is reported as unavailable and other lanes continue normally.

Browser-backed discovery is optional and outside the core lifecycle contract.
When enabled in a container, browser assets need a persistent path such as:

```text
$HERMES_HOME/.playwright-browsers
```

## Adding a source

Prefer, in order:

1. official public API;
2. RSS or Atom;
3. permitted ordinary HTTP;
4. browser automation only when necessary and allowed.

Then:

1. add the collector in `hooks/discovery.py`;
2. add configuration in `templates/sources.yaml`;
3. normalize URL and bounded metadata;
4. preserve timeouts and failure isolation;
5. ensure item identity and material-update fingerprint are stable;
6. run topic contracts, matrix, and stress;
7. verify no credentials, browser profiles, or private sessions enter the
   repository.

## Rich content selection

The model may select only a validated internal content reference from the current
eligible Discovery set. Unknown or stale references are ignored. Message type
alone must not attach the first available item.

Images and files use adapter capabilities only when available. Unsupported rich
payloads fall back to text/link delivery. Local files are restricted to allowed
roots and size limits; raw container paths are never exposed.
