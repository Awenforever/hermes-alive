# Phase H test secret sentinel fix V3

Marker: `HERMES_ALIVE_TEST_SECRET_SENTINEL_FIX_V3`

The no-secret-output matrix test still injects a realistic fake API-key shape at
runtime, but the repository no longer contains a contiguous secret-like token.

This preserves both guarantees:

- runtime output must not reveal the fake key;
- strict repository and test-artifact secret scans remain enabled.
