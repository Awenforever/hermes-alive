"""Bounded explicit memory and separately consented Core profile advice."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from .events import Sensitivity, _freeze_json, _thaw_json
from .memory import ContentStatus, MemoryAuthority, MemoryKind, MemoryProjection, StoredMemoryProposal


@dataclass(frozen=True, slots=True)
class CognitionContextEvidence:
    memory_id: str
    proposal_event_id: str
    source_event_ids: tuple[str, ...]
    predicate: str
    kind: str
    value: Any = field(repr=False)
    source_observations: tuple = ()

    def to_prompt(self) -> dict[str, Any]:
        return {"memory_id": self.memory_id, "proposal_event_id": self.proposal_event_id,
                "source_event_ids": list(self.source_event_ids), "predicate": self.predicate,
                "kind": self.kind, "value": _thaw_json(self.value),
                "source_observations":[{"event_id":e,"observed_at":at}
                                       for e,at in self.source_observations]}


class CognitionContextReader:
    """Explicit memories plus separately consented, current Core profile advice."""

    def __init__(self, journal, *, content_vault=None):
        self.journal = journal
        self.memory = MemoryProjection(journal, content_vault=content_vault)

    def read(self, *, subject: str, clearance: Sensitivity, limit: int = 8):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}", subject) or not 1 <= limit <= 16:
            raise ValueError("invalid cognition context scope")
        target = self.journal.last_sequence()
        while self.journal.checkpoint(self.memory.CHECKPOINT) < target:
            before = self.journal.checkpoint(self.memory.CHECKPOINT)
            self.memory.project_new(limit=1000)
            after = self.journal.checkpoint(self.memory.CHECKPOINT)
            if after < target and after <= before:
                raise ValueError("memory context projection made no progress")
        accepted = []
        preferences=self.memory.retrieve(subject=subject,clearance=clearance,limit=512,
            kinds=(MemoryKind.PREFERENCE,))
        situational=self.memory.retrieve(subject=subject,clearance=clearance,limit=512,
            kinds=(MemoryKind.FACT,MemoryKind.COMMITMENT))
        # Keep typed, durable preferences from being displaced by a run of
        # recent task facts. This is not inference that every chat is an interest.
        for item in (*preferences,*situational):
            if item.authority is not MemoryAuthority.USER_EXPLICIT or item.content_status is not ContentStatus.AVAILABLE:
                continue
            origin = self.journal.get(item.created_from_event_id)
            if (origin is None or origin.event.event_type != "memory.proposed"
                    or origin.event.actor != subject or origin.event.subject != subject):
                continue
            proposal = StoredMemoryProposal.from_payload(origin.event.payload)
            # A mutable projection label is not enough to turn model output into
            # an explicit user statement. Bind its value to original retained evidence.
            if (proposal.authority is not MemoryAuthority.USER_EXPLICIT
                    or proposal.subject != subject or proposal.kind is not item.kind
                    or proposal.predicate != item.predicate
                    or proposal.proposal_id != item.memory_id
                    or self.memory.content_vault.digest_json(item.value) != proposal.content.digest):
                continue
            sources = [self.journal.get(e) for e in proposal.source_event_ids]
            if any(s is None or s.event.actor != subject or s.event.subject != subject for s in sources):
                continue
            if len(json.dumps(_thaw_json(item.value), ensure_ascii=False)) > 1500:
                # Do not silently truncate a preference into a different meaning.
                continue
            accepted.append(CognitionContextEvidence(
                item.memory_id, item.created_from_event_id, proposal.source_event_ids,
                item.predicate, item.kind.value, _freeze_json(item.value),
                tuple((s.event.event_id,s.event.observed_at.isoformat()) for s in sources),
            ))
            if len(accepted) == limit:
                break
        if len(accepted) < limit and Sensitivity(clearance) in (Sensitivity.PRIVATE, Sensitivity.RESTRICTED):
            from .core_profile_context import read_core_profile_evidence
            profile = read_core_profile_evidence(self.journal, subject=subject)
            if profile is not None:
                accepted.append(CognitionContextEvidence(**profile))
        return tuple(accepted)
