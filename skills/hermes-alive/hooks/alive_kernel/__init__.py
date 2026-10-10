"""Hermes Alive kernel foundations.

The package is deliberately not imported by the production watcher yet.  Phase
1 develops the durable history boundary in shadow before it can affect sends.
"""

from .events import EventEnvelope, EventValidationError, Sensitivity
from .event_store import (
    AppendResult,
    EventConflictError,
    EventIntegrityError,
    ExperienceJournal,
)
from .privacy import LocalIdentityProtector, structural_hook_payload
from .shadow_bridge import ShadowKernelBridge, mirror_hook_event, shadow_enabled
from .content_vault import (
    ContentErasedError,
    ContentIntegrityError,
    ContentReference,
    ContentUnavailableError,
    ContentVault,
    ContentVaultError,
    ErasureResult,
)
from .memory import (
    MemoryAuthority,
    MemoryKind,
    MemoryProjection,
    MemoryProposal,
    MemoryRecord,
    MemoryState,
    MemoryValidationError,
    ProjectionDecision,
    ProjectionDecisionKind,
)

__all__ = [
    "AppendResult",
    "ContentErasedError",
    "ContentIntegrityError",
    "ContentReference",
    "ContentUnavailableError",
    "ContentVault",
    "ContentVaultError",
    "EventConflictError",
    "EventEnvelope",
    "EventIntegrityError",
    "EventValidationError",
    "ErasureResult",
    "ExperienceJournal",
    "LocalIdentityProtector",
    "MemoryAuthority",
    "MemoryKind",
    "MemoryProjection",
    "MemoryProposal",
    "MemoryRecord",
    "MemoryState",
    "MemoryValidationError",
    "ProjectionDecision",
    "ProjectionDecisionKind",
    "Sensitivity",
    "ShadowKernelBridge",
    "mirror_hook_event",
    "shadow_enabled",
    "structural_hook_payload",
]
