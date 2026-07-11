# Contributing

Contributions should preserve the repository's lifecycle, safety, and testing
contracts.

Before submitting a change:

1. Do not commit Provider credentials, platform tokens, real chat identifiers,
   `.env` files, generated archives, or runtime state.
2. Run the matrix suite:

   ```bash
   python3 skills/hermes-alive/tests/run_matrix.py
   ```

3. Run shell and Python compile checks.
4. For runtime, lifecycle, persistence, or delivery changes, run the full
   stress suite:

   ```bash
   python3 skills/hermes-alive/tests/run_stress.py
   ```

5. Keep installation centered on the complete GitHub repository, root
   `bootstrap.sh`, and `hermes-alive-lifecycle`.
6. Preserve default-uninstall state retention and purge zero-residue behavior.

Pull requests should describe the user-visible behavior, validation performed,
rollback considerations, and whether runtime files changed.
