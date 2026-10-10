"""Compatibility tombstone for the retired legacy Dream mutator.

The former implementation read raw conversation rows from ``state.db`` and
let model confidence directly rewrite MEMORY.md, fact storage and voice state.
That violates Alive's explicit-retention and reviewable-memory boundaries.

The public class remains importable while deployments migrate, but it is
permanently inert. Consent-aware consolidation belongs to ``alive_kernel``
and may emit reviewable proposals only; it must never revive this mutation
path.
"""

from __future__ import annotations

from pathlib import Path
import os

from dream_diff_store import DreamDiff, save_diff


RETIRED_REASON = (
    "Legacy Dream is retired: raw transcript scanning and automatic memory, "
    "fact, or voice mutation are not permitted."
)


class DreamEngine:
    """Inert compatibility surface; never reads conversations or mutates memory."""

    def __init__(self, diff_path: str | None = None) -> None:
        hermes_home = Path(
            os.getenv("HERMES_HOME", str(Path.home() / ".hermes"))
        ).expanduser()
        self._diff_path = str(
            Path(
                diff_path
                or os.getenv(
                    "DREAM_DIFF_PATH",
                    str(
                        hermes_home
                        / "plugin-data"
                        / "hermes-alive"
                        / "runtime"
                        / "dream_diff.json"
                    ),
                )
            ).expanduser()
        )

    def should_run(self) -> bool:
        """The unsafe legacy engine cannot be re-enabled by environment flags."""

        return False

    async def run_dream_cycle(self) -> DreamDiff:
        """Persist an explicit no-op receipt for callers from older runtimes."""

        diff = DreamDiff(
            operations=[],
            prune_candidates=[],
            summary=RETIRED_REASON,
            applied=False,
            applied_at=None,
        )
        save_diff(diff, self._diff_path)
        return diff

    def get_current_model(self) -> str:
        """No model is routed because the retired engine never invokes one."""

        return ""
