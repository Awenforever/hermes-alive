# Hermes Alive Phase F / Rich Content Delivery V1

Markers:

- `RICH_CONTENT_DELIVERY_V1`
- `RICH_CONTENT_CAPABILITY_FALLBACK_V1`
- `RICH_CONTENT_METADATA_V1`
- `RICH_CONTENT_ITEM_FIELDS_V1`

Scope: `hermes-alive-v2-dev` only.

## Delivery payloads

Supported semantic kinds:

- text
- link
- image
- file

## Platform behavior

- Text always uses `adapter.send`.
- Images use verified `adapter.send_image` when present.
- Files use verified `adapter.send_document` when present.
- Link cards use `adapter.send_link_card` only when present.
- Unsupported links fall back to text plus URL.
- Unsupported images fall back to text plus image URL.
- Unsafe or unavailable local files are never exposed as raw container paths.
- Local files are restricted to configured allowed roots and a size limit.

## Attribution

- LLM-authored text keeps the real routed model metadata.
- Deterministic rich payloads use `hermes` system metadata.
- A false `SendResult.success` is treated as delivery failure.
- `content_seen` is written only after text evidence or a successful structured delivery.

## Safety

- Raw `MEDIA:` directives remain stripped from LLM output.
- The LLM does not select local paths or directly invoke platform methods.
- No production changes are made in Phase F development.
