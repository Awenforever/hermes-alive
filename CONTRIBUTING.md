# Contributing

## Development rules

1. Keep Hermes Alive changes inside `skills/hermes-alive`.
2. Do not modify Hermes Core or the WeChat adapter.
3. Add or update tests for behavioral changes.
4. Preserve the documented `shadow`, `observe_only`, and `enforce` boundaries.
5. Never add credentials, runtime state, browser profiles, caches, or private
   conversation data.
6. Run:

```bash
bash scripts/portable-ci.sh
```

before submitting a change.

## Release changes

A passing portable CI run is not full release acceptance. Runtime attribution,
fresh-container lifecycle, repository transport, real GitHub URL installation,
spare-WeChat E2E, and production verification are separate gates.
