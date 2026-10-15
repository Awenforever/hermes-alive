"""Meaning-first rendering with a provable deterministic baseline."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hmac
import re
from typing import Any, Mapping

from .content_vault import (
    ContentReference,
    ContentVault,
    ContentVaultError,
)
from .deliberation import ActionKind, SideEffect
from .deliberation_store import DeliberationProjection
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, Sensitivity, _thaw_json
from .privacy import LocalIdentityProtector


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_ATOM_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_MAX_ATOMS = 24
_MAX_ATOM_CHARS = 1200
_MAX_LITERAL_CHARS = 240
_MAX_HORIZON = timedelta(days=7)


class SemanticRenderingError(ValueError):
    """Meaning or rendering crossed a fidelity, privacy, or causal boundary."""


class SemanticAtomKind(StrEnum):
    PROPOSED_CONTENT = "proposed_content"
    FACT = "fact"
    REQUEST = "request"
    QUESTION = "question"
    DEADLINE = "deadline"
    AMOUNT = "amount"
    LINK = "link"
    CONTACT = "contact"
    CAVEAT = "caveat"
    UNCERTAINTY = "uncertainty"
    NEGATION = "negation"
    SOURCE_ATTRIBUTION = "source_attribution"


class MessageSpeechAct(StrEnum):
    INFORM = "inform"
    ASK = "ask"
    REMIND = "remind"
    REQUEST = "request"
    WARN = "warn"
    SHARE = "share"


class RenderLayout(StrEnum):
    PARAGRAPHS = "paragraphs"
    BULLETS = "bullets"


class RendererClass(StrEnum):
    DETERMINISTIC = "deterministic"
    MODEL_CANDIDATE = "model_candidate"


class FidelityStatus(StrEnum):
    PROVEN = "proven"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class LiteralPolicy(StrEnum):
    LEGACY = 'legacy'
    SEMANTIC = 'semantic'


_LITERAL_REQUIRED = {
    SemanticAtomKind.DEADLINE,
    SemanticAtomKind.AMOUNT,
    SemanticAtomKind.LINK,
    SemanticAtomKind.CONTACT,
    SemanticAtomKind.UNCERTAINTY,
    SemanticAtomKind.NEGATION,
}


@dataclass(frozen=True, slots=True)
class SemanticAtom:
    atom_id: str
    kind: SemanticAtomKind
    text: str
    evidence_event_ids: tuple[str, ...]
    protected_literals: tuple[str, ...] = ()
    literal_policy: LiteralPolicy = LiteralPolicy.LEGACY

    def __post_init__(self) -> None:
        atom_id = str(self.atom_id).strip().lower()
        text = str(self.text).strip()
        evidence = tuple(
            dict.fromkeys(str(item).strip() for item in self.evidence_event_ids)
        )
        literals = tuple(
            dict.fromkeys(str(item) for item in self.protected_literals if str(item))
        )
        kind = SemanticAtomKind(self.kind)
        policy = LiteralPolicy(self.literal_policy)
        if policy is LiteralPolicy.SEMANTIC and kind not in {
                SemanticAtomKind.NEGATION, SemanticAtomKind.UNCERTAINTY}:
            raise SemanticRenderingError('semantic literal policy cannot relax exact-value kinds')
        if not _ATOM_ID_RE.fullmatch(atom_id):
            raise SemanticRenderingError("invalid atom_id")
        # Discovery accepts canonical source URLs up to 4096 characters. Keeping
        # source provenance must not quietly truncate a valid long URL.
        maximum_text = (4096 if kind is SemanticAtomKind.LINK else
                        1600 if kind is SemanticAtomKind.PROPOSED_CONTENT else _MAX_ATOM_CHARS)
        if not text or len(text) > maximum_text:
            raise SemanticRenderingError("semantic atom text is empty or too long")
        if not evidence or any(not _ID_RE.fullmatch(item) for item in evidence):
            raise SemanticRenderingError("semantic atom requires valid evidence")
        if len(literals) > 16 or any(
            len(value) > (4096 if kind is SemanticAtomKind.LINK else
                          1600 if kind is SemanticAtomKind.PROPOSED_CONTENT else _MAX_LITERAL_CHARS)
            or value not in text for value in literals
        ):
            raise SemanticRenderingError("protected literal is invalid or absent")
        if kind in _LITERAL_REQUIRED and not literals and policy is not LiteralPolicy.SEMANTIC:
            raise SemanticRenderingError(
                f"{kind.value} atom requires an exact protected literal"
            )
        object.__setattr__(self, "atom_id", atom_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "evidence_event_ids", evidence)
        object.__setattr__(self, "protected_literals", literals)
        object.__setattr__(self, "literal_policy", policy)


@dataclass(frozen=True, slots=True)
class MeaningDocument:
    message_id: str
    subject: str
    speech_act: MessageSpeechAct
    atoms: tuple[SemanticAtom, ...]
    created_at: datetime
    expires_at: datetime
    sensitivity: Sensitivity = Sensitivity.PRIVATE

    def __post_init__(self) -> None:
        message_id = str(self.message_id).strip()
        subject = str(self.subject).strip()
        atoms = tuple(self.atoms)
        created = _utc(self.created_at, "created_at")
        expires = _utc(self.expires_at, "expires_at")
        if not _ID_RE.fullmatch(message_id) or not _ID_RE.fullmatch(subject):
            raise SemanticRenderingError("invalid meaning identity")
        if not 1 <= len(atoms) <= _MAX_ATOMS:
            raise SemanticRenderingError("meaning document has invalid atom count")
        if len({atom.atom_id for atom in atoms}) != len(atoms):
            raise SemanticRenderingError("semantic atom IDs must be unique")
        if expires <= created or expires - created > _MAX_HORIZON:
            raise SemanticRenderingError("meaning lifetime is invalid")
        object.__setattr__(self, "message_id", message_id)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "speech_act", MessageSpeechAct(self.speech_act))
        object.__setattr__(self, "atoms", atoms)
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "expires_at", expires)
        object.__setattr__(self, "sensitivity", Sensitivity(self.sensitivity))


@dataclass(frozen=True, slots=True)
class FidelityAssessment:
    status: FidelityStatus
    renderer_class: RendererClass
    missing_atom_ids: tuple[str, ...]
    missing_literals: tuple[str, ...]
    unexpected_content: bool
    reasons: tuple[str, ...]

    @property
    def fidelity_proven(self) -> bool:
        return self.status is FidelityStatus.PROVEN

    @property
    def safe_for_automatic_rendering(self) -> bool:
        """This proves form preservation only, never truth or send authority."""

        return self.fidelity_proven


@dataclass(frozen=True, slots=True)
class RenderedMessage:
    event_id: str
    text: str
    layout: RenderLayout
    assessment: FidelityAssessment


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SemanticRenderingError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def serialize_meaning(document: MeaningDocument) -> dict[str, Any]:
    return {
        "schema_version": (2 if any(a.literal_policy is LiteralPolicy.SEMANTIC
                                   for a in document.atoms) else 1),
        "message_id": document.message_id,
        "subject": document.subject,
        "speech_act": document.speech_act.value,
        "created_at": document.created_at.isoformat(),
        "expires_at": document.expires_at.isoformat(),
        "sensitivity": document.sensitivity.value,
        "atoms": [
            {
                "atom_id": atom.atom_id,
                "kind": atom.kind.value,
                "text": atom.text,
                "evidence_event_ids": list(atom.evidence_event_ids),
                "protected_literals": list(atom.protected_literals),
                **({'literal_policy':atom.literal_policy.value}
                   if atom.literal_policy is not LiteralPolicy.LEGACY else {}),
            }
            for atom in document.atoms
        ],
    }


def deserialize_meaning(value: Mapping[str, Any]) -> MeaningDocument:
    if set(value) != {
        "schema_version",
        "message_id",
        "subject",
        "speech_act",
        "created_at",
        "expires_at",
        "sensitivity",
        "atoms",
    } or type(value.get('schema_version')) is not int or value.get("schema_version") not in (1, 2):
        raise SemanticRenderingError("invalid meaning document schema")
    atoms_raw = value.get("atoms")
    if not isinstance(atoms_raw, list):
        raise SemanticRenderingError("meaning atoms must be a list")
    atoms = []
    for raw in atoms_raw:
        required = {
            "atom_id",
            "kind",
            "text",
            "evidence_event_ids",
            "protected_literals",
        }
        if (not isinstance(raw, Mapping) or not required <= set(raw)
                or set(raw) - required - ({'literal_policy'} if value['schema_version']==2 else set())):
            raise SemanticRenderingError("invalid semantic atom schema")
        if 'literal_policy' in raw and raw['literal_policy'] != LiteralPolicy.SEMANTIC.value:
            raise SemanticRenderingError('noncanonical explicit literal policy')
        atoms.append(
            SemanticAtom(
                atom_id=str(raw["atom_id"]),
                kind=SemanticAtomKind(raw["kind"]),
                text=str(raw["text"]),
                evidence_event_ids=tuple(raw["evidence_event_ids"]),
                protected_literals=tuple(raw["protected_literals"]),
                literal_policy=LiteralPolicy(raw.get('literal_policy','legacy')),
            )
        )
    if value['schema_version']==2 and not any(a.literal_policy is LiteralPolicy.SEMANTIC for a in atoms):
        raise SemanticRenderingError('noncanonical semantic-policy document')
    return MeaningDocument(
        message_id=str(value["message_id"]),
        subject=str(value["subject"]),
        speech_act=MessageSpeechAct(value["speech_act"]),
        atoms=tuple(atoms),
        created_at=datetime.fromisoformat(str(value["created_at"])),
        expires_at=datetime.fromisoformat(str(value["expires_at"])),
        sensitivity=Sensitivity(value["sensitivity"]),
    )


def deterministic_text(
    document: MeaningDocument, layout: RenderLayout = RenderLayout.PARAGRAPHS
) -> str:
    """Render exact atoms with formatting-only separators."""

    selected = RenderLayout(layout)
    if len(document.atoms) == 1:
        return document.atoms[0].text
    if selected is RenderLayout.BULLETS:
        return "\n".join(f"- {atom.text}" for atom in document.atoms)
    return "\n\n".join(atom.text for atom in document.atoms)


def assess_fidelity(
    document: MeaningDocument,
    text: str,
    *,
    renderer_class: RendererClass,
    layout: RenderLayout = RenderLayout.PARAGRAPHS,
) -> FidelityAssessment:
    candidate = str(text)
    renderer = RendererClass(renderer_class)
    missing_atoms = tuple(
        atom.atom_id for atom in document.atoms if atom.text not in candidate
    )
    missing_literals = tuple(
        literal
        for atom in document.atoms
        for literal in atom.protected_literals
        if literal not in candidate
    )
    expected = deterministic_text(document, layout)
    unexpected = candidate != expected
    reasons: list[str] = []
    if missing_atoms:
        reasons.append("semantic_atoms_changed_or_paraphrased")
    if missing_literals:
        reasons.append("protected_literals_missing_or_changed")
    if renderer is RendererClass.DETERMINISTIC and unexpected:
        reasons.append("deterministic_output_mismatch")
    if missing_literals or (renderer is RendererClass.DETERMINISTIC and unexpected):
        status = FidelityStatus.REJECTED
    elif renderer is RendererClass.DETERMINISTIC:
        status = FidelityStatus.PROVEN
        reasons.append("exact_deterministic_reconstruction")
    else:
        # Exact atom/literal coverage cannot prove that free surrounding prose
        # introduced no claim, changed no relation, or shifted uncertainty.
        status = FidelityStatus.REVIEW_REQUIRED
        reasons.append("free_generation_requires_independent_semantic_review")
    return FidelityAssessment(
        status,
        renderer,
        missing_atoms,
        missing_literals,
        unexpected,
        tuple(reasons),
    )


class MeaningStore:
    """Persist encrypted meaning and prove its selected-candidate dependency."""

    def __init__(
        self,
        journal: ExperienceJournal,
        *,
        content_vault: ContentVault | None = None,
        protector: LocalIdentityProtector | None = None,
    ) -> None:
        self.journal = journal
        self.content_vault = content_vault or ContentVault(
            journal.path.parent / f"{journal.path.stem}-content-vault",
            backup_root=journal.path.parent / f"{journal.path.stem}-content-backups",
        )
        self.protector = protector or LocalIdentityProtector(
            journal.path.parent / "identity.key"
        )
        self.deliberation = DeliberationProjection(
            journal, content_vault=self.content_vault
        )

    @staticmethod
    def _authentication_document(
        contract: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        value = _thaw_json(payload)
        value.pop("integrity_authenticator", None)
        return {"contract": contract, "payload": value}

    def define(
        self,
        document: MeaningDocument,
        *,
        actor: str,
        observed_at: datetime | None = None,
    ) -> JournalRecord:
        current = _utc(observed_at or document.created_at, "observed_at")
        if current < document.created_at or current >= document.expires_at:
            raise SemanticRenderingError("meaning observation is outside its lifetime")
        evidence_ids = tuple(
            dict.fromkeys(
                event_id
                for atom in document.atoms
                for event_id in atom.evidence_event_ids
            )
        )
        for event_id in evidence_ids:
            source = self.journal.get(event_id)
            if (
                source is None
                or source.event.subject not in {None, document.subject}
                or source.event.observed_at > current
            ):
                raise SemanticRenderingError("meaning evidence is missing, foreign, or future")
        content = self.content_vault.put_json(
            serialize_meaning(document),
            subject=document.subject,
            purpose="message.meaning",
            sensitivity=document.sensitivity,
            retention_until=document.expires_at,
            content_id=f"message-meaning:{document.message_id}",
        )
        payload: dict[str, Any] = {
            "message_id": document.message_id,
            "speech_act": document.speech_act.value,
            "atom_ids": [atom.atom_id for atom in document.atoms],
            "atom_kinds": [atom.kind.value for atom in document.atoms],
            "evidence_event_ids": list(evidence_ids),
            "content": content.to_event_payload(),
            "raw_content_stored_in_journal": False,
            "truth_claimed": False,
            "evidence_entailment_proven": False,
            "action_authority_granted": False,
            "route_authority_granted": False,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "message.meaning.v1",
            self._authentication_document("message.meaning.v1", payload),
        )
        event = EventEnvelope(
            event_id=f"message.meaning:{document.message_id}",
            event_type="message.meaning_defined",
            source="alive.semantic-rendering",
            actor=actor,
            subject=document.subject,
            occurred_at=document.created_at,
            observed_at=current,
            sensitivity=document.sensitivity,
            expires_at=document.expires_at,
            payload=payload,
        )
        return self._append_idempotent(event)

    def resolve(self, meaning_event_id: str) -> MeaningDocument:
        record = self.journal.get(meaning_event_id)
        if record is None or record.event.event_type != "message.meaning_defined":
            raise SemanticRenderingError("meaning event is unavailable")
        event = record.event
        payload = event.payload
        withdrawal = self.journal.get(
            f"message.meaning_retracted:{payload.get('message_id', '')}"
        )
        if withdrawal is not None:
            if not self._valid_withdrawal(withdrawal, record):
                raise SemanticRenderingError("meaning withdrawal integrity is invalid")
            raise SemanticRenderingError("meaning was withdrawn by its user")
        try:
            supplied = str(payload["integrity_authenticator"])
            content = ContentReference.from_event_payload(payload["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SemanticRenderingError("invalid meaning event") from exc
        if not self.protector.verify_json(
            "message.meaning.v1",
            self._authentication_document("message.meaning.v1", payload),
            supplied,
        ):
            raise SemanticRenderingError("meaning authenticator is invalid")
        try:
            document = deserialize_meaning(
                self.content_vault.resolve_json(
                    content.content_id,
                    expected_subject=event.subject,
                    expected_purpose="message.meaning",
                    expected_sensitivity=event.sensitivity,
                )
            )
        except (ContentVaultError, KeyError, TypeError, ValueError) as exc:
            raise SemanticRenderingError("meaning content is unavailable") from exc
        if not (
            document.subject == event.subject
            and document.message_id == payload.get("message_id")
            and document.speech_act.value == payload.get("speech_act")
            and [atom.atom_id for atom in document.atoms] == list(payload.get("atom_ids") or ())
            and [atom.kind.value for atom in document.atoms] == list(payload.get("atom_kinds") or ())
            and tuple(payload.get("evidence_event_ids") or ())
            == tuple(
                dict.fromkeys(
                    event_id
                    for atom in document.atoms
                    for event_id in atom.evidence_event_ids
                )
            )
            and event.expires_at == document.expires_at
            and payload.get("raw_content_stored_in_journal") is False
            and payload.get("truth_claimed") is False
            and payload.get("evidence_entailment_proven") is False
            and payload.get("action_authority_granted") is False
            and payload.get("route_authority_granted") is False
        ):
            raise SemanticRenderingError("meaning event and encrypted document diverged")
        return document

    def _valid_withdrawal(
        self, withdrawal: JournalRecord, meaning: JournalRecord
    ) -> bool:
        event, source = withdrawal.event, meaning.event
        payload = event.payload
        try:
            return bool(
                event.event_type == "message.meaning_retracted"
                and event.source == "alive.semantic-control"
                and event.subject == source.subject
                and event.actor == source.subject
                and event.causation_id == source.event_id
                and payload.get("meaning_event_id") == source.event_id
                and payload.get("subject") == source.subject
                and payload.get("reason") in {
                    "explicit_user_withdrawal", "explicit_user_correction"
                }
                and (
                    payload.get("reason") != "explicit_user_correction"
                    or (
                        isinstance(payload.get("request_digest"), str)
                        and isinstance(payload.get("replacement_content"), Mapping)
                        and isinstance(payload.get("replacement_event_id"), str)
                        and payload.get("action_authority_granted") is False
                        and payload.get("truth_claimed") is False
                    )
                )
                and event.expires_at is None
                and withdrawal.sequence > meaning.sequence
                and self.protector.verify_json(
                    "message.meaning_retracted.v1",
                    self._authentication_document("message.meaning_retracted.v1", payload),
                    str(payload["integrity_authenticator"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            return False

    def retract(
        self, meaning_event_id: str, *, subject: str, actor: str
    ) -> JournalRecord:
        """Withdraw this user's meaning and invalidate all dependent receipts.

        The host command boundary supplies the authenticated subject/actor;
        model proposals cannot call this as authority for another user.
        Withdrawal is durable and idempotent, and does not erase history.
        """
        source = self.journal.get(meaning_event_id)
        if (
            source is None or source.event.event_type != "message.meaning_defined"
            or source.event.subject != subject or actor != subject
        ):
            raise SemanticRenderingError("meaning is unavailable for this user")
        event_id = f"message.meaning_retracted:{source.event.payload.get('message_id', '')}"
        existing = self.journal.get(event_id)
        if existing is not None:
            if not self._valid_withdrawal(existing, source):
                raise SemanticRenderingError("meaning withdrawal integrity is invalid")
            return existing
        self.resolve(meaning_event_id)
        payload = {
            "meaning_event_id": meaning_event_id, "subject": subject,
            "reason": "explicit_user_withdrawal",
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "message.meaning_retracted.v1",
            self._authentication_document("message.meaning_retracted.v1", payload),
        )
        event = EventEnvelope(
            event_id=event_id, event_type="message.meaning_retracted",
            source="alive.semantic-control", actor=actor, subject=subject,
            causation_id=meaning_event_id, sensitivity=source.event.sensitivity,
            payload=payload,
        )
        try:
            appended = self.journal.append(event)
            return JournalRecord(appended.sequence, appended.event)
        except EventConflictError:
            existing = self.journal.get(event_id)
            if existing is None or not self._valid_withdrawal(existing, source):
                raise SemanticRenderingError("conflicting meaning withdrawal")
            return existing

    def inspect_for_user(self, meaning_event_id: str, *, subject: str) -> MeaningDocument:
        source = self.journal.get(meaning_event_id)
        if source is None or source.event.subject != subject:
            raise SemanticRenderingError("meaning is unavailable for this user")
        return self.resolve(meaning_event_id)

    def correct_atom(
        self, meaning_event_id: str, *, subject: str, actor: str,
        atom_id: str, kind: SemanticAtomKind, text: str,
    ) -> JournalRecord:
        """Replace one user-selected atom without granting new action authority.

        A permanent authenticated withdrawal is the durable preparation point.
        It encrypts the complete successor so identical retries can finish after
        a crash. Different corrections of the same original conflict; a later
        correction must target the successor. Old meaning never revives.
        """
        source = self.journal.get(meaning_event_id)
        if (
            source is None or source.event.event_type != "message.meaning_defined"
            or source.event.subject != subject or actor != subject
        ):
            raise SemanticRenderingError("meaning is unavailable for this user")
        kind = SemanticAtomKind(kind)
        atom_id, text = str(atom_id).strip().lower(), str(text).strip()
        request_digest = self.content_vault.digest_json({
            "meaning_event_id": meaning_event_id, "subject": subject,
            "atom_id": atom_id, "kind": kind.value, "text": text,
        })
        withdrawal_id = f"message.meaning_retracted:{source.event.payload.get('message_id', '')}"
        pending = self.journal.get(withdrawal_id)
        if pending is None:
            original = self.inspect_for_user(meaning_event_id, subject=subject)
            current = datetime.now(timezone.utc)
            if not original.created_at <= current < original.expires_at:
                raise SemanticRenderingError("meaning correction is outside its lifetime")
            if atom_id not in {atom.atom_id for atom in original.atoms}:
                raise SemanticRenderingError("correction atom is unavailable")
            # Protect exactly the user-authored replacement, not model-inferred
            # dates, quantities or polarities. Chunk only to bound literal size.
            literals = tuple(
                text[offset:offset + _MAX_LITERAL_CHARS]
                for offset in range(0, len(text), _MAX_LITERAL_CHARS)
            ) if kind in _LITERAL_REQUIRED else ()
            replacement_atom = SemanticAtom(atom_id, kind, text, (withdrawal_id,), literals)
            replacement = replace(
                original, message_id=f"corrected:{request_digest}", created_at=current,
                atoms=tuple(replacement_atom if atom.atom_id == atom_id else atom
                            for atom in original.atoms),
            )
            content_id = f"message-correction:{request_digest}"
            try:
                content = self.content_vault.put_json(
                    serialize_meaning(replacement), subject=subject, purpose="message.correction",
                    sensitivity=original.sensitivity, retention_until=original.expires_at,
                    content_id=content_id,
                )
            except ContentVaultError:
                # An earlier identical request may have prepared content before
                # crashing, or another worker may have won the preparation race.
                # Keep its real creation time, not the original's or retry's.
                try:
                    prepared = deserialize_meaning(self.content_vault.resolve_json(
                        content_id, expected_subject=subject, expected_purpose="message.correction",
                        expected_sensitivity=original.sensitivity,
                    ))
                except (ContentVaultError, KeyError, TypeError, ValueError) as exc:
                    raise SemanticRenderingError("correction preparation is unavailable") from exc
                if (
                    replace(replacement, created_at=prepared.created_at) != prepared
                    or not source.event.observed_at <= prepared.created_at <= datetime.now(timezone.utc)
                ):
                    raise SemanticRenderingError("correction preparation diverged")
                replacement = prepared
                content = self.content_vault.put_json(
                    serialize_meaning(replacement), subject=subject, purpose="message.correction",
                    sensitivity=original.sensitivity, retention_until=original.expires_at,
                    content_id=content_id,
                )
            current = datetime.now(timezone.utc)
            payload = {
                "meaning_event_id": meaning_event_id, "subject": subject,
                "reason": "explicit_user_correction", "request_digest": request_digest,
                "replacement_event_id": f"message.meaning:{replacement.message_id}",
                "replacement_content": content.to_event_payload(),
                "action_authority_granted": False, "truth_claimed": False,
            }
            payload["integrity_authenticator"] = self.protector.authenticate_json(
                "message.meaning_retracted.v1",
                self._authentication_document("message.meaning_retracted.v1", payload),
            )
            event = EventEnvelope(
                event_id=withdrawal_id, event_type="message.meaning_retracted",
                source="alive.semantic-control", actor=actor, subject=subject,
                causation_id=meaning_event_id, sensitivity=original.sensitivity,
                occurred_at=current, observed_at=current, payload=payload,
            )
            try:
                appended = self.journal.append(event)
                pending = JournalRecord(appended.sequence, appended.event)
            except EventConflictError:
                pending = self.journal.get(withdrawal_id)
        if pending is None or not self._valid_withdrawal(pending, source):
            raise SemanticRenderingError("meaning correction integrity is invalid")
        payload = pending.event.payload
        if (
            payload.get("reason") != "explicit_user_correction"
            or not hmac.compare_digest(str(payload.get("request_digest", "")), request_digest)
        ):
            raise SemanticRenderingError("meaning was withdrawn or replaced by a different correction")
        try:
            content = ContentReference.from_event_payload(payload["replacement_content"])
            replacement = deserialize_meaning(self.content_vault.resolve_json(
                content.content_id, expected_subject=subject,
                expected_purpose="message.correction", expected_sensitivity=source.event.sensitivity,
            ))
        except (ContentVaultError, KeyError, TypeError, ValueError) as exc:
            raise SemanticRenderingError("correction content is unavailable") from exc
        if (
            replacement.subject != subject
            or not hmac.compare_digest(
                self.content_vault.digest_json(serialize_meaning(replacement)), content.digest
            )
            or content.sensitivity != source.event.sensitivity
            or content.retention_until != source.event.expires_at
            or f"message.meaning:{replacement.message_id}" != payload.get("replacement_event_id")
            or replacement.sensitivity != source.event.sensitivity
            or replacement.expires_at != source.event.expires_at
            or not source.event.observed_at <= replacement.created_at <= pending.event.observed_at
            or not replacement.created_at <= datetime.now(timezone.utc) < replacement.expires_at
            or not any(
                atom.atom_id == atom_id and atom.kind == kind and atom.text == text
                and atom.evidence_event_ids == (withdrawal_id,)
                for atom in replacement.atoms
            )
        ):
            raise SemanticRenderingError("correction document and event diverged")
        result = self.define(replacement, actor=actor, observed_at=pending.event.observed_at)
        self.resolve(result.event.event_id)  # Never resurrect a withdrawn successor.
        return result

    def candidate_reference(self, meaning_event_id: str) -> dict[str, Any]:
        """Strict candidate content shape used by deliberation."""

        self.resolve(meaning_event_id)
        return {
            "schema_version": 1,
            "kind": "semantic_message",
            "meaning_event_id": meaning_event_id,
        }

    def render_selected(
        self,
        *,
        selection_event_id: str,
        meaning_event_id: str,
        subject: str,
        layout: RenderLayout = RenderLayout.PARAGRAPHS,
        observed_at: datetime | None = None,
    ) -> RenderedMessage:
        source = self.journal.get(selection_event_id)
        if (
            source is None
            or source.event.event_type != "deliberation.selected"
            or source.event.subject != subject
        ):
            raise SemanticRenderingError("selection evidence is missing or foreign")
        frame_id = str(source.event.payload.get("frame_id") or "")
        self.deliberation.project_new()
        if self.deliberation.latest_selection_event_id(frame_id) != selection_event_id:
            raise SemanticRenderingError("selection is not the latest validated intent")
        stored = self.deliberation.inspect(frame_id, clearance=source.event.sensitivity)
        if stored is None or stored.selection is None:
            raise SemanticRenderingError("validated selection is unavailable")
        candidate = stored.selection.candidate
        if (
            candidate.action_kind is ActionKind.SILENCE
            or candidate.side_effect is not SideEffect.COMMUNICATION
        ):
            raise SemanticRenderingError("selected action is not renderable communication")
        contents = dict(stored.candidate_contents)
        candidate_content = contents.get(str(candidate.content_id))
        expected_reference = {
            "schema_version": 1,
            "kind": "semantic_message",
            "meaning_event_id": meaning_event_id,
        }
        if candidate_content != expected_reference:
            raise SemanticRenderingError("selected candidate does not bind this meaning")
        document = self.resolve(meaning_event_id)
        now = _utc(observed_at or datetime.now(timezone.utc), "observed_at")
        if (
            document.subject != subject
            or document.expires_at <= source.event.observed_at
            or now < source.event.observed_at
            or now >= document.expires_at
        ):
            raise SemanticRenderingError(
                "meaning is foreign, expired, or rendered out of causal order"
            )
        selected_layout = RenderLayout(layout)
        text = deterministic_text(document, selected_layout)
        assessment = assess_fidelity(
            document,
            text,
            renderer_class=RendererClass.DETERMINISTIC,
            layout=selected_layout,
        )
        if not assessment.safe_for_automatic_rendering:
            raise SemanticRenderingError("deterministic rendering did not prove fidelity")
        output_id = self.protector.pseudonym(
            "semantic-render", f"{selection_event_id}\0{selected_layout.value}"
        )
        if output_id is None:
            raise SemanticRenderingError("render identity is unavailable")
        content = self.content_vault.put_json(
            {"text": text},
            subject=subject,
            purpose="message.rendered",
            sensitivity=source.event.sensitivity,
            retention_until=document.expires_at,
            content_id=f"message-rendered:{output_id}",
        )
        payload: dict[str, Any] = {
            "meaning_event_id": meaning_event_id,
            "selection_event_id": selection_event_id,
            "frame_id": frame_id,
            "candidate_id": candidate.candidate_id,
            "renderer": "deterministic-v1",
            "renderer_class": RendererClass.DETERMINISTIC.value,
            "layout": selected_layout.value,
            "fidelity_status": assessment.status.value,
            "covered_atom_ids": [atom.atom_id for atom in document.atoms],
            "content": content.to_event_payload(),
            "free_generation_used": False,
            "independent_review_required": False,
            "truth_claimed": False,
            "evidence_entailment_proven": False,
            "action_authority_granted": False,
            "route_authority_granted": False,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "message.rendered.v1",
            self._authentication_document("message.rendered.v1", payload),
        )
        event = EventEnvelope(
            event_id=f"message.rendered:{output_id.split(':', 1)[-1]}",
            event_type="message.rendered",
            source="alive.semantic-rendering",
            actor="system:alive-deterministic-renderer",
            subject=subject,
            correlation_id=frame_id,
            causation_id=selection_event_id,
            occurred_at=source.event.observed_at,
            observed_at=now,
            sensitivity=source.event.sensitivity,
            expires_at=document.expires_at,
            payload=payload,
        )
        record = self._append_idempotent(event)
        if not self.verify_render(record):
            raise SemanticRenderingError("render receipt verification failed")
        return RenderedMessage(record.event.event_id, text, selected_layout, assessment)

    def verify_render(self, record: JournalRecord) -> bool:
        event = record.event
        payload = event.payload
        try:
            supplied = str(payload["integrity_authenticator"])
            if not self.protector.verify_json(
                "message.rendered.v1",
                self._authentication_document("message.rendered.v1", payload),
                supplied,
            ):
                return False
            if payload.get("renderer") != "deterministic-v1":
                return False
            document = self.resolve(str(payload["meaning_event_id"]))
            content = ContentReference.from_event_payload(payload["content"])
            rendered = self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose="message.rendered",
                expected_sensitivity=event.sensitivity,
            )
            text = str(rendered["text"])
            layout = RenderLayout(payload["layout"])
            assessment = assess_fidelity(
                document,
                text,
                renderer_class=RendererClass.DETERMINISTIC,
                layout=layout,
            )
            source = self.journal.get(str(payload["selection_event_id"]))
            frame_id = str(payload["frame_id"])
            self.deliberation.project_new()
            stored = self.deliberation.inspect(
                frame_id, clearance=event.sensitivity
            )
            selected_candidate = (
                stored.selection.candidate
                if stored is not None and stored.selection is not None
                else None
            )
            selected_content = (
                dict(stored.candidate_contents).get(
                    str(selected_candidate.content_id)
                )
                if stored is not None and selected_candidate is not None
                else None
            )
            expected_reference = {
                "schema_version": 1,
                "kind": "semantic_message",
                "meaning_event_id": str(payload["meaning_event_id"]),
            }
            return bool(
                event.event_type == "message.rendered"
                and event.source == "alive.semantic-rendering"
                and event.actor == "system:alive-deterministic-renderer"
                and event.causation_id == payload.get("selection_event_id")
                and event.correlation_id == payload.get("frame_id")
                and event.observed_at >= source.event.observed_at
                and event.expires_at == document.expires_at
                and event.observed_at < document.expires_at
                and source is not None
                and source.event.event_type == "deliberation.selected"
                and source.event.subject == event.subject
                and self.deliberation.latest_selection_event_id(frame_id)
                == payload.get("selection_event_id")
                and selected_candidate is not None
                and selected_candidate.candidate_id == payload.get("candidate_id")
                and selected_content == expected_reference
                and payload.get("renderer_class") == RendererClass.DETERMINISTIC.value
                and payload.get("fidelity_status") == FidelityStatus.PROVEN.value
                and tuple(payload.get("covered_atom_ids") or ())
                == tuple(atom.atom_id for atom in document.atoms)
                and payload.get("free_generation_used") is False
                and payload.get("independent_review_required") is False
                and payload.get("truth_claimed") is False
                and payload.get("evidence_entailment_proven") is False
                and payload.get("action_authority_granted") is False
                and payload.get("route_authority_granted") is False
                and assessment.safe_for_automatic_rendering
            )
        except (KeyError, TypeError, ValueError, ContentVaultError, SemanticRenderingError):
            return False

    def _append_idempotent(self, event: EventEnvelope) -> JournalRecord:
        existing = self.journal.get(event.event_id)
        if existing is not None:
            return self._compatible(existing, event)
        try:
            result = self.journal.append(event)
            return JournalRecord(result.sequence, result.event)
        except EventConflictError:
            existing = self.journal.get(event.event_id)
            if existing is None:
                raise
            return self._compatible(existing, event)

    @staticmethod
    def _compatible(existing: JournalRecord, proposed: EventEnvelope) -> JournalRecord:
        fields = (
            "event_type",
            "source",
            "actor",
            "subject",
            "correlation_id",
            "causation_id",
            "occurred_at",
            "sensitivity",
            "confidence",
            "expires_at",
            "payload",
        )
        if any(
            getattr(existing.event, name) != getattr(proposed, name) for name in fields
        ):
            raise SemanticRenderingError("event identity was reused with different semantics")
        return existing
