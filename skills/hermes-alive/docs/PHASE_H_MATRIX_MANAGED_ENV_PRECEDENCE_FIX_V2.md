# Phase H managed environment precedence matrix fix V2

Marker: `HERMES_ALIVE_MATRIX_MANAGED_ENV_PRECEDENCE_FIX_V2`

The managed-configuration matrix now tests the intended contract directly:

- a missing process environment value is loaded from managed configuration;
- an explicitly set process environment value wins when `overwrite=False`;
- `overwrite=True` is tested separately as an explicit tooling operation;
- the test restores the original process environment after completion.

The runtime loader implementation is unchanged.
