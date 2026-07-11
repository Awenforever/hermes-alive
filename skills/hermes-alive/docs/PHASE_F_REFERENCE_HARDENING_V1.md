# Phase F Rich Delivery V1.1 Reference Hardening

Markers:

- `RICH_CONTENT_REFERENCE_V1`
- `RICH_CONTENT_IMAGE_SOURCE_V1`

Scope: `hermes-alive-v2-dev` only.

## Selection contract

- An LLM may reference a discovery item only with a validated internal marker:
  `[[CONTENT_REF:<known content_id>]]`.
- The marker is extracted before sanitization, validated against the current discovery list, then removed from user-visible text.
- A fabricated or unknown ID is ignored.
- Without a valid reference, rich delivery requires real lexical evidence from the visible message.
- Message type alone must never attach the first discovery item.

## Image source contract

- Bilibili popular-video cover URLs are carried as `image_url`.
- Protocol-relative image URLs are normalized to HTTPS before delivery.
- Native image sending still uses verified adapter capability detection and safe fallback.

## Safety

- The internal content reference cannot select local file paths or call platform methods.
- Raw `MEDIA:` directives remain stripped.
- Production remains read-only.
