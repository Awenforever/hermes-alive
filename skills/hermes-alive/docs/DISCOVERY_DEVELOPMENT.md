# Discovery Development

## Current source types

Hermes Alive supports API, RSS, ordinary HTTP, and optional browser-backed
collectors. Current integrations include academic papers, repositories,
technology news, Chinese community feeds, video trends, and selected lifestyle
or discussion sources.

Browser-backed discovery is optional and outside the core lifecycle contract.
When enabled in a container, keep browser assets on a persistent path such as:

```text
/opt/data/.playwright-browsers
```

## Adding a source

Use this order:

1. official public API;
2. RSS or Atom feed;
3. `robots.txt` and ordinary HTTP access;
4. Playwright only when necessary and permitted.

Then:

1. add the collector in `hooks/discovery.py`;
2. add source configuration in `templates/sources.yaml`;
3. normalize URLs and bounded metadata;
4. preserve timeouts and failure isolation;
5. run matrix and stress tests;
6. verify that no credentials, raw browser profiles, or private session data are
   committed.

## Rich content selection

The model may select a discovery item only through a validated internal content
reference associated with the current discovery set. Unknown references are
ignored. Message type alone must not attach the first available item.

Images and files use adapter capabilities only when available. Unsupported rich
payloads fall back safely to text/link output. Local file delivery is restricted
to allowed roots and size limits, and raw container paths are never exposed.
