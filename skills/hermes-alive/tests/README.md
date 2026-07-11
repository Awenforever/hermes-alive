# Hermes Alive Phase H tests

Markers:

- `HERMES_ALIVE_MATRIX_SUITE_V1`
- `HERMES_ALIVE_STRESS_SUITE_V1`
- `HERMES_ALIVE_INSTALL_TRANSACTION_ROLLBACK_V1`

Run matrix tests:

```bash
python3 tests/run_matrix.py
```

Run full stress tests:

```bash
python3 tests/run_stress.py
```

A reduced scale may be used only for developer smoke tests:

```bash
HERMES_ALIVE_STRESS_SCALE=0.05 python3 tests/run_stress.py
```

Final acceptance must use the default scale `1.0`.
