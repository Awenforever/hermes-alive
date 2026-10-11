"""Ordered, idempotent startup recovery for Alive kernel projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from safe_io import file_lock

from .agenda import AgendaProjection
from .availability import AvailabilityProjection
from .autonomy_policy import AutonomyPolicyProjection
from .consolidation import ConsolidationPolicyProjection
from .content_vault import ContentVault
from .deliberation_store import DeliberationProjection
from .dispatch_outbox import DispatchOutbox
from .event_store import ExperienceJournal
from .exploration_store import ExplorationProjection
from .memory import MemoryProjection
from .outcomes import OutcomeProjection
from .preference_learning import PreferenceLearningProjection
from .reflection import ReflectionProjection
from .retention import RetentionProjection


@dataclass(frozen=True, slots=True)
class ProjectionRecoveryReport:
    name: str
    checkpoint_before: int
    checkpoint_after: int
    decisions: int
    batches: int


@dataclass(frozen=True, slots=True)
class KernelRecoveryReport:
    target_sequence: int
    final_sequence: int
    projections: tuple[ProjectionRecoveryReport, ...]
    erasures_resumed: int
    expired_content_erased: int
    dispatch_evidence_checkpoint_before: int
    dispatch_evidence_checkpoint_after: int
    dispatch_evidence_indexed: int
    dispatches_reconciled: int
    dispatch_outcomes_reconciled: int
    started_at: datetime
    completed_at: datetime


class KernelRecoveryError(RuntimeError):
    """A projection failed to make deterministic replay progress."""


class KernelRecoverySupervisor:
    """Catch every projection up in dependency order without external effects."""

    def __init__(self, shared_dir: str | Path) -> None:
        self.shared_dir = Path(shared_dir).expanduser().resolve()
        self.kernel_dir = self.shared_dir / "kernel"
        self.database = self.kernel_dir / "experience.sqlite3"
        self.lock_path = self.kernel_dir / "recovery.lock"

    @property
    def exists(self) -> bool:
        return self.database.is_file()

    def _runtime(self) -> tuple[ExperienceJournal, ContentVault]:
        journal = ExperienceJournal(self.database)
        vault = ContentVault(
            self.kernel_dir / "content-vault",
            backup_root=self.kernel_dir / "content-backups",
        )
        return journal, vault

    @staticmethod
    def _catch_up(
        journal: ExperienceJournal,
        *,
        name: str,
        checkpoint: str,
        project: Callable[..., list[Any]],
        target_sequence: int,
        batch_size: int,
    ) -> ProjectionRecoveryReport:
        before = journal.checkpoint(checkpoint)
        decisions = 0
        batches = 0
        while journal.checkpoint(checkpoint) < target_sequence:
            prior = journal.checkpoint(checkpoint)
            decisions += len(project(limit=batch_size))
            batches += 1
            current = journal.checkpoint(checkpoint)
            if current <= prior:
                raise KernelRecoveryError(
                    f"projection {name!r} made no progress from sequence {prior}"
                )
        return ProjectionRecoveryReport(
            name=name,
            checkpoint_before=before,
            checkpoint_after=journal.checkpoint(checkpoint),
            decisions=decisions,
            batches=batches,
        )

    def recover(self, *, batch_size: int = 1000) -> KernelRecoveryReport | None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if not self.exists:
            return None
        started = datetime.now(timezone.utc)
        with file_lock(self.lock_path, timeout=30.0):
            journal, vault = self._runtime()
            retention = RetentionProjection(journal, content_vault=vault)
            pending = retention.resume_pending_erasures()
            expired = vault.erase_expired(now=started)
            target = journal.last_sequence()
            deliberation = DeliberationProjection(journal, content_vault=vault)
            exploration = ExplorationProjection(journal, content_vault=vault)

            ordered = (
                ("retention", retention),
                ("autonomy-policy", AutonomyPolicyProjection(journal)),
                ("consolidation-consent", ConsolidationPolicyProjection(journal)),
                ("memory", MemoryProjection(journal, content_vault=vault)),
                ("agenda", AgendaProjection(journal, content_vault=vault)),
                ("availability", AvailabilityProjection(journal)),
                ("deliberation-frames", deliberation),
                ("exploration", exploration),
                ("deliberation", deliberation),
                ("outcomes", OutcomeProjection(journal, content_vault=vault)),
                ("reflection", ReflectionProjection(journal, content_vault=vault)),
                (
                    "preference-learning",
                    PreferenceLearningProjection(journal, content_vault=vault),
                ),
            )
            reports = tuple(
                self._catch_up(
                    journal,
                    name=name,
                    checkpoint=(
                        projection.FRAME_CHECKPOINT
                        if name == "deliberation-frames"
                        else projection.CHECKPOINT
                    ),
                    project=(
                        projection.project_frames_new
                        if name == "deliberation-frames"
                        else projection.project_new
                    ),
                    target_sequence=target,
                    batch_size=batch_size,
                )
                for name, projection in ordered
            )
            outbox = DispatchOutbox(journal, content_vault=vault)
            evidence_before = outbox.evidence_checkpoint()
            evidence_indexed = outbox.project_evidence(batch_size=batch_size)
            evidence_after = outbox.evidence_checkpoint()
            dispatches = outbox.reconcile(now=started, recovering=True)
            dispatch_outcomes = outbox.reconcile_outcomes()
            completed = datetime.now(timezone.utc)
            return KernelRecoveryReport(
                target_sequence=target,
                final_sequence=journal.last_sequence(),
                projections=reports,
                erasures_resumed=pending,
                expired_content_erased=expired.newly_erased,
                dispatch_evidence_checkpoint_before=evidence_before,
                dispatch_evidence_checkpoint_after=evidence_after,
                dispatch_evidence_indexed=evidence_indexed,
                dispatches_reconciled=dispatches,
                dispatch_outcomes_reconciled=dispatch_outcomes,
                started_at=started,
                completed_at=completed,
            )


def recover_kernel_state(
    shared_dir: str | Path, *, batch_size: int = 1000
) -> KernelRecoveryReport | None:
    """Recover an existing kernel store; never creates one on a fresh install."""

    return KernelRecoverySupervisor(shared_dir).recover(batch_size=batch_size)
