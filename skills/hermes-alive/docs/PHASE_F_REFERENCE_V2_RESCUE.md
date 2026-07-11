# Phase F Rich Delivery Reference Hardening V2 Rescue

Markers:

- `RICH_CONTENT_REFERENCE_V1`
- `RICH_CONTENT_IMAGE_SOURCE_V1`
- `RICH_CONTENT_REFERENCE_RESCUE_V2`

Scope: `hermes-alive-v2-dev` only.

This rescue handles the known partial-write state produced by V1:

- The four runtime files may already contain the V1 code.
- V1 stopped because the composer marker assertion failed.
- V1 also removed `CONTENT_REF` before extraction and omitted the extraction method.

V2 guarantees:

1. `_generate_candidate()` returns raw model text.
2. `compose()` validates `CONTENT_REF` before sanitization.
3. `_sanitize()` removes the internal marker before user-visible delivery.
4. Unknown content IDs are ignored.
5. Message type alone cannot attach the first discovery item.
6. Bilibili `pic` is carried as `image_url`.
7. Protocol-relative image URLs are normalized to HTTPS.
8. The script modifies only an accepted known dev baseline.
