"""Independent semantic-review contracts and blinded replay evaluation.

Review is deliberately weaker than authority.  It may qualify a model render
for shadow comparison, but it cannot prove source truth, choose an action,
select a route, or authorize delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import hmac
import re
from typing import Any, Iterable, Mapping

from .content_vault import ContentReference, ContentVault, ContentVaultError
from .deliberation import ActionKind, SideEffect
from .deliberation_store import DeliberationProjection
from .event_store import EventConflictError, ExperienceJournal, JournalRecord
from .events import EventEnvelope, _thaw_json
from .privacy import LocalIdentityProtector
from .semantic_rendering import (
    FidelityStatus,
    MeaningDocument,
    MeaningStore,
    RendererClass,
    SemanticRenderingError,
    assess_fidelity,
)


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,254}$")
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class SemanticReviewError(ValueError):
    """A semantic review is incomplete, unbound, or not independent."""


class SemanticRisk(StrEnum):
    OMISSION = "omission"
    CONTRADICTION = "contradiction"
    UNSUPPORTED_ADDITION = "unsupported_addition"
    POLARITY_SHIFT = "polarity_shift"
    UNCERTAINTY_SHIFT = "uncertainty_shift"
    TEMPORAL_SHIFT = "temporal_shift"
    QUANTITY_SHIFT = "quantity_shift"
    REFERENCE_MISMATCH = "reference_mismatch"
    SPEECH_ACT_SHIFT = "speech_act_shift"


class ReviewerKind(StrEnum):
    HUMAN = "human"
    MODEL = "model"


class ReviewDisposition(StrEnum):
    SHADOW_ELIGIBLE = "shadow_eligible"
    CORRELATED = "correlated_review"
    REJECTED = "rejected"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class AtomReview:
    atom_id: str
    preserved: bool
    risks: tuple[SemanticRisk, ...] = ()

    def __post_init__(self) -> None:
        atom_id = str(self.atom_id).strip().lower()
        risks = tuple(dict.fromkeys(SemanticRisk(item) for item in self.risks))
        if not _ID_RE.fullmatch(atom_id):
            raise SemanticReviewError("invalid reviewed atom ID")
        if not isinstance(self.preserved, bool):
            raise SemanticReviewError("atom preservation must be boolean")
        if self.preserved and risks:
            raise SemanticReviewError("a preserved atom cannot carry semantic risks")
        if not self.preserved and not risks:
            raise SemanticReviewError("an unpreserved atom requires a risk class")
        object.__setattr__(self, "atom_id", atom_id)
        object.__setattr__(self, "risks", risks)


def candidate_digest(text: str) -> str:
    """Bind review to the exact UTF-8 candidate without retaining plaintext."""

    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IndependentSemanticReview:
    review_id: str
    meaning_event_id: str
    candidate_digest: str
    renderer_execution_id: str
    renderer_model: str
    renderer_independence_domain: str
    reviewer_kind: ReviewerKind
    reviewer_execution_id: str
    reviewer_model: str | None
    reviewer_independence_domain: str
    atom_reviews: tuple[AtomReview, ...]
    added_claims_detected: bool
    speech_act_preserved: bool
    protected_literals_preserved: bool

    def __post_init__(self) -> None:
        for name in (
            "review_id",
            "meaning_event_id",
            "renderer_execution_id",
            "renderer_independence_domain",
            "reviewer_execution_id",
            "reviewer_independence_domain",
        ):
            value = str(getattr(self, name)).strip()
            if not _ID_RE.fullmatch(value):
                raise SemanticReviewError(f"invalid {name}")
            object.__setattr__(self, name, value)
        digest = str(self.candidate_digest).strip().lower()
        if not _DIGEST_RE.fullmatch(digest):
            raise SemanticReviewError("invalid candidate digest")
        object.__setattr__(self, "candidate_digest", digest)
        renderer_model = str(self.renderer_model).strip()
        if not _MODEL_RE.fullmatch(renderer_model):
            raise SemanticReviewError("actual renderer model is required")
        object.__setattr__(self, "renderer_model", renderer_model)
        kind = ReviewerKind(self.reviewer_kind)
        object.__setattr__(self, "reviewer_kind", kind)
        reviewer_model = (
            str(self.reviewer_model).strip()
            if self.reviewer_model is not None
            else None
        )
        if kind is ReviewerKind.MODEL:
            if reviewer_model is None or not _MODEL_RE.fullmatch(reviewer_model):
                raise SemanticReviewError("actual reviewer model is required")
        elif reviewer_model is not None:
            raise SemanticReviewError("human review cannot claim a reviewer model")
        object.__setattr__(self, "reviewer_model", reviewer_model)
        atom_reviews = tuple(self.atom_reviews)
        ids = [review.atom_id for review in atom_reviews]
        if not atom_reviews or len(ids) != len(set(ids)):
            raise SemanticReviewError("atom reviews must be nonempty and unique")
        object.__setattr__(self, "atom_reviews", atom_reviews)
        for name in (
            "added_claims_detected",
            "speech_act_preserved",
            "protected_literals_preserved",
        ):
            if not isinstance(getattr(self, name), bool):
                raise SemanticReviewError(f"{name} must be boolean")

    @property
    def structurally_independent(self) -> bool:
        if self.renderer_execution_id == self.reviewer_execution_id:
            return False
        if (
            self.renderer_independence_domain
            == self.reviewer_independence_domain
        ):
            return False
        return not (
            self.reviewer_kind is ReviewerKind.MODEL
            and self.renderer_model == self.reviewer_model
        )


@dataclass(frozen=True, slots=True)
class ReviewAssessment:
    disposition: ReviewDisposition
    risks: tuple[SemanticRisk, ...]
    reasons: tuple[str, ...]

    @property
    def eligible_for_shadow_comparison(self) -> bool:
        return self.disposition is ReviewDisposition.SHADOW_ELIGIBLE

    @property
    def safe_for_automatic_delivery(self) -> bool:
        """Semantic review never grants action, route, or delivery authority."""

        return False


def assess_independent_review(
    document: MeaningDocument,
    candidate_text: str,
    review: IndependentSemanticReview,
) -> ReviewAssessment:
    """Validate binding, completeness and independence before reading verdicts."""
    return _assess_review(document, candidate_text, review, require_independence=True)


def _assess_review(document, candidate_text, review, *, require_independence):

    reasons: list[str] = []
    expected_meaning_event_id = f"message.meaning:{document.message_id}"
    if review.meaning_event_id != expected_meaning_event_id:
        reasons.append("meaning_event_mismatch")
    if review.candidate_digest != candidate_digest(candidate_text):
        reasons.append("candidate_digest_mismatch")
    expected_ids = tuple(atom.atom_id for atom in document.atoms)
    reviewed_ids = tuple(item.atom_id for item in review.atom_reviews)
    if len(reviewed_ids) != len(expected_ids) or set(reviewed_ids) != set(expected_ids):
        reasons.append("atom_review_set_incomplete")
    if require_independence and not review.structurally_independent:
        reasons.append("reviewer_not_independent")
    if reasons:
        return ReviewAssessment(ReviewDisposition.INVALID, (), tuple(reasons))

    missing_literals = tuple(
        literal
        for atom in document.atoms
        for literal in atom.protected_literals
        if literal not in candidate_text
    )
    risks = tuple(
        dict.fromkeys(
            risk for item in review.atom_reviews for risk in item.risks
        )
    )
    if review.added_claims_detected:
        risks += tuple(
            risk
            for risk in (SemanticRisk.UNSUPPORTED_ADDITION,)
            if risk not in risks
        )
    if not review.speech_act_preserved:
        risks += tuple(
            risk
            for risk in (SemanticRisk.SPEECH_ACT_SHIFT,)
            if risk not in risks
        )
    if missing_literals:
        reasons.append("protected_literal_missing_from_candidate")
    if not review.protected_literals_preserved:
        reasons.append("protected_literal_check_failed")
    if any(not item.preserved for item in review.atom_reviews):
        reasons.append("semantic_atom_not_preserved")
    if risks or reasons:
        return ReviewAssessment(
            ReviewDisposition.REJECTED,
            risks,
            tuple(dict.fromkeys(reasons or ("semantic_risk_detected",))),
        )
    return ReviewAssessment(
        ReviewDisposition.SHADOW_ELIGIBLE if review.structurally_independent else ReviewDisposition.CORRELATED,
        (),
        (("complete_independent_review_found_no_semantic_change" if review.structurally_independent
          else "correlated_review_is_not_independent_evidence"),),
    )


@dataclass(frozen=True, slots=True)
class SemanticReplayPrediction:
    case_id: str
    candidate_id: str
    language_tag: str
    renderer_model: str
    reviewer_model: str
    renderer_independence_domain: str
    reviewer_independence_domain: str
    accepted_as_preserved: bool
    predicted_risks: tuple[SemanticRisk, ...]

    def __post_init__(self) -> None:
        for name in (
            "case_id",
            "candidate_id",
            "renderer_independence_domain",
            "reviewer_independence_domain",
        ):
            value = str(getattr(self, name)).strip()
            if not _ID_RE.fullmatch(value):
                raise SemanticReviewError(f"invalid {name}")
            object.__setattr__(self, name, value)
        language = str(self.language_tag).strip()
        if not _LANGUAGE_RE.fullmatch(language):
            raise SemanticReviewError("invalid language tag")
        object.__setattr__(self, "language_tag", language.lower())
        for name in ("renderer_model", "reviewer_model"):
            model = str(getattr(self, name)).strip()
            if not _MODEL_RE.fullmatch(model):
                raise SemanticReviewError(f"invalid {name}")
            object.__setattr__(self, name, model)
        if not isinstance(self.accepted_as_preserved, bool):
            raise SemanticReviewError("accepted_as_preserved must be boolean")
        risks = tuple(dict.fromkeys(SemanticRisk(item) for item in self.predicted_risks))
        if self.accepted_as_preserved == bool(risks):
            raise SemanticReviewError("acceptance and predicted risks conflict")
        object.__setattr__(self, "predicted_risks", risks)

    @property
    def structurally_independent(self) -> bool:
        return bool(
            self.renderer_model != self.reviewer_model
            and self.renderer_independence_domain
            != self.reviewer_independence_domain
        )


@dataclass(frozen=True, slots=True)
class SemanticCaseJudgment:
    case_id: str
    language_tag: str
    expected_risks: tuple[SemanticRisk, ...]

    def __post_init__(self) -> None:
        case_id = str(self.case_id).strip()
        language = str(self.language_tag).strip().lower()
        if not _ID_RE.fullmatch(case_id) or not _LANGUAGE_RE.fullmatch(language):
            raise SemanticReviewError("invalid semantic case judgment")
        object.__setattr__(self, "case_id", case_id)
        object.__setattr__(self, "language_tag", language)
        object.__setattr__(
            self,
            "expected_risks",
            tuple(dict.fromkeys(SemanticRisk(item) for item in self.expected_risks)),
        )

    @property
    def faithful(self) -> bool:
        return not self.expected_risks


@dataclass(frozen=True, slots=True)
class SemanticReviewQualityReport:
    cases: int
    languages: tuple[str, ...]
    faithful_cases: int
    risky_cases: int
    unsafe_acceptances: int
    faithful_acceptances: int
    independence_violations: int
    unsafe_acceptance_rate: float | None
    faithful_acceptance_rate: float | None
    issue_precision: float | None
    macro_risk_recall: float | None
    risk_recall: tuple[tuple[SemanticRisk, float], ...]
    renderer_models: tuple[str, ...]
    reviewer_models: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticReviewQualification:
    qualified: bool
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoredModelCandidate:
    event_id: str
    selection_event_id: str
    meaning_event_id: str
    frame_id: str
    candidate_id: str
    text: str
    digest: str
    renderer_execution_id: str
    renderer_model: str
    renderer_independence_domain: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class StoredReviewReceipt:
    event_id: str
    candidate_event_id: str
    review_id: str
    assessment: ReviewAssessment


class SemanticReviewStore:
    """Persist encrypted model candidates and authenticated review receipts."""

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
        self.meanings = MeaningStore(
            journal, content_vault=self.content_vault, protector=self.protector
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

    @staticmethod
    def _utc(value: datetime, name: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise SemanticReviewError(f"{name} must be timezone-aware")
        return value.astimezone(timezone.utc)

    def _selection_context(
        self,
        *,
        selection_event_id: str,
        meaning_event_id: str,
        subject: str,
        observed_at: datetime,
    ) -> tuple[JournalRecord, MeaningDocument, str, str]:
        source = self.journal.get(selection_event_id)
        if (
            source is None
            or source.event.event_type != "deliberation.selected"
            or source.event.subject != subject
        ):
            raise SemanticReviewError("selection evidence is missing or foreign")
        frame_id = str(source.event.payload.get("frame_id") or "")
        self.deliberation.project_new()
        if self.deliberation.latest_selection_event_id(frame_id) != selection_event_id:
            raise SemanticReviewError("selection is not the latest validated intent")
        stored = self.deliberation.inspect(frame_id, clearance=source.event.sensitivity)
        if stored is None or stored.selection is None:
            raise SemanticReviewError("validated selection is unavailable")
        selected = stored.selection.candidate
        if (
            selected.action_kind is ActionKind.SILENCE
            or selected.side_effect is not SideEffect.COMMUNICATION
        ):
            raise SemanticReviewError("selected action is not renderable communication")
        expected = {
            "schema_version": 1,
            "kind": "semantic_message",
            "meaning_event_id": meaning_event_id,
        }
        if dict(stored.candidate_contents).get(str(selected.content_id)) != expected:
            raise SemanticReviewError("selected candidate does not bind this meaning")
        try:
            document = self.meanings.resolve(meaning_event_id)
        except SemanticRenderingError as exc:
            raise SemanticReviewError("meaning is unavailable") from exc
        if (
            document.subject != subject
            or observed_at < source.event.observed_at
            or observed_at >= document.expires_at
        ):
            raise SemanticReviewError(
                "meaning is foreign, expired, or reviewed out of causal order"
            )
        return source, document, frame_id, selected.candidate_id

    def record_model_candidate(
        self,
        *,
        selection_event_id: str,
        meaning_event_id: str,
        subject: str,
        text: str,
        renderer_execution_id: str,
        renderer_model: str,
        renderer_independence_domain: str,
        observed_at: datetime | None = None,
    ) -> StoredModelCandidate:
        candidate_text = str(text)
        if not candidate_text or len(candidate_text.encode("utf-8")) > 256_000:
            raise SemanticReviewError("model candidate is empty or too large")
        current = self._utc(
            observed_at or datetime.now(timezone.utc), "observed_at"
        )
        for name, value, pattern in (
            ("renderer_execution_id", renderer_execution_id, _ID_RE),
            ("renderer_model", renderer_model, _MODEL_RE),
            ("renderer_independence_domain", renderer_independence_domain, _ID_RE),
        ):
            if not pattern.fullmatch(str(value).strip()):
                raise SemanticReviewError(f"invalid {name}")
        source, document, frame_id, selected_candidate_id = self._selection_context(
            selection_event_id=selection_event_id,
            meaning_event_id=meaning_event_id,
            subject=subject,
            observed_at=current,
        )
        assessment = assess_fidelity(
            document,
            candidate_text,
            renderer_class=RendererClass.MODEL_CANDIDATE,
        )
        if assessment.status is FidelityStatus.REJECTED:
            raise SemanticReviewError(
                "model candidate failed deterministic protected-literal checks"
            )
        digest = candidate_digest(candidate_text)
        output_id = self.protector.pseudonym(
            "semantic-model-candidate",
            f"{selection_event_id}\0{renderer_execution_id}\0{digest}",
        )
        if output_id is None:
            raise SemanticReviewError("model candidate identity is unavailable")
        content = self.content_vault.put_json(
            {"text": candidate_text},
            subject=subject,
            purpose="message.model_candidate",
            sensitivity=source.event.sensitivity,
            retention_until=document.expires_at,
            content_id=f"message-model-candidate:{output_id}",
        )
        payload: dict[str, Any] = {
            "meaning_event_id": meaning_event_id,
            "selection_event_id": selection_event_id,
            "frame_id": frame_id,
            "candidate_id": selected_candidate_id,
            "candidate_digest": digest,
            "renderer_execution_id": str(renderer_execution_id).strip(),
            "renderer_model": str(renderer_model).strip(),
            "renderer_independence_domain": str(
                renderer_independence_domain
            ).strip(),
            "fidelity_status": assessment.status.value,
            "changed_atom_ids": list(assessment.missing_atom_ids),
            "content": content.to_event_payload(),
            "raw_content_stored_in_journal": False,
            "independent_review_required": True,
            "truth_claimed": False,
            "evidence_entailment_proven": False,
            "action_authority_granted": False,
            "route_authority_granted": False,
            "delivery_authority_granted": False,
        }
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "message.model_candidate.v1",
            self._authentication_document("message.model_candidate.v1", payload),
        )
        event = EventEnvelope(
            event_id=f"message.model_candidate:{output_id.split(':', 1)[-1]}",
            event_type="message.model_candidate",
            source="alive.semantic-review",
            actor="system:alive-model-renderer",
            subject=subject,
            correlation_id=frame_id,
            causation_id=selection_event_id,
            occurred_at=source.event.observed_at,
            observed_at=current,
            sensitivity=source.event.sensitivity,
            expires_at=document.expires_at,
            payload=payload,
        )
        record = self._append_idempotent(event)
        resolved = self.resolve_model_candidate(
            record.event.event_id, as_of=current
        )
        if resolved is None:
            raise SemanticReviewError("stored model candidate failed verification")
        return resolved

    def resolve_model_candidate(
        self, event_id: str, *, as_of: datetime | None = None
    ) -> StoredModelCandidate | None:
        record = self.journal.get(event_id)
        if record is None:
            return None
        event = record.event
        payload = event.payload
        try:
            current = self._utc(as_of or datetime.now(timezone.utc), "as_of")
            if (
                event.expires_at is None
                or current < event.observed_at
                or current >= event.expires_at
            ):
                return None
            supplied = str(payload["integrity_authenticator"])
            if not self.protector.verify_json(
                "message.model_candidate.v1",
                self._authentication_document("message.model_candidate.v1", payload),
                supplied,
            ):
                return None
            content = ContentReference.from_event_payload(payload["content"])
            stored = self.content_vault.resolve_json(
                content.content_id,
                expected_subject=event.subject,
                expected_purpose="message.model_candidate",
                expected_sensitivity=event.sensitivity,
            )
            text = str(stored["text"])
            digest = candidate_digest(text)
            selection_id = str(payload["selection_event_id"])
            meaning_id = str(payload["meaning_event_id"])
            _source, document, frame_id, selected_candidate_id = (
                self._selection_context(
                    selection_event_id=selection_id,
                    meaning_event_id=meaning_id,
                    subject=str(event.subject),
                    observed_at=event.observed_at,
                )
            )
            assessment = assess_fidelity(
                document, text, renderer_class=RendererClass.MODEL_CANDIDATE
            )
            valid = bool(
                event.event_type == "message.model_candidate"
                and event.source == "alive.semantic-review"
                and event.actor == "system:alive-model-renderer"
                and event.causation_id == selection_id
                and event.correlation_id == frame_id
                and event.expires_at == document.expires_at
                and event.observed_at < document.expires_at
                and payload.get("frame_id") == frame_id
                and payload.get("candidate_id") == selected_candidate_id
                and payload.get("candidate_digest") == digest
                and payload.get("fidelity_status")
                == FidelityStatus.REVIEW_REQUIRED.value
                and tuple(payload.get("changed_atom_ids") or ())
                == assessment.missing_atom_ids
                and assessment.status is FidelityStatus.REVIEW_REQUIRED
                and payload.get("raw_content_stored_in_journal") is False
                and payload.get("independent_review_required") is True
                and payload.get("truth_claimed") is False
                and payload.get("evidence_entailment_proven") is False
                and payload.get("action_authority_granted") is False
                and payload.get("route_authority_granted") is False
                and payload.get("delivery_authority_granted") is False
            )
            if not valid:
                return None
            return StoredModelCandidate(
                event.event_id,
                selection_id,
                meaning_id,
                frame_id,
                selected_candidate_id,
                text,
                digest,
                str(payload["renderer_execution_id"]),
                str(payload["renderer_model"]),
                str(payload["renderer_independence_domain"]),
                document.expires_at,
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            ContentVaultError,
            SemanticReviewError,
        ):
            return None

    def _assessment_scope(self,candidate,subject):
        from .review_contracts import SPLIT_SOURCE_REVIEW_CONTRACTS,BOUNDARY_ASSESSMENT
        reader=getattr(self,'expression_context_for_selection',None)
        context=reader(candidate.selection_event_id,subject) if reader else None
        if (context and context.get('method') in ('discovery-source-authoring-v2','discovery-source-authoring-v3')
                and context.get('semantic_source_contract') in SPLIT_SOURCE_REVIEW_CONTRACTS):
            return BOUNDARY_ASSESSMENT
        return None

    def record_review(
        self,
        *,
        candidate_event_id: str,
        review: IndependentSemanticReview,
        actor: str,
        observed_at: datetime | None = None,
        require_independence: bool = True,
        protocol_recovery_event_id: str | None = None,
    ) -> StoredReviewReceipt:
        if type(require_independence) is not bool:
            raise SemanticReviewError('invalid independence mode')
        current = self._utc(
            observed_at or datetime.now(timezone.utc), "observed_at"
        )
        candidate = self.resolve_model_candidate(candidate_event_id, as_of=current)
        if candidate is None:
            raise SemanticReviewError("model candidate is unavailable or stale")
        candidate_record = self.journal.get(candidate_event_id)
        if candidate_record is None:
            raise SemanticReviewError("model candidate event is unavailable")
        if current < candidate_record.event.observed_at or current >= candidate.expires_at:
            raise SemanticReviewError("review is outside the candidate lifetime")
        if not (
            review.meaning_event_id == candidate.meaning_event_id
            and review.candidate_digest == candidate.digest
            and review.renderer_execution_id == candidate.renderer_execution_id
            and review.renderer_model == candidate.renderer_model
            and review.renderer_independence_domain
            == candidate.renderer_independence_domain
        ):
            raise SemanticReviewError("review does not bind the stored renderer evidence")
        scope=self._assessment_scope(candidate,candidate_record.event.subject)
        if scope is not None and review.added_claims_detected:
            raise SemanticReviewError('boundary-only review cannot assert a source-addition verdict')
        document = self.meanings.resolve(candidate.meaning_event_id)
        assessment = _assess_review(document, candidate.text, review, require_independence=require_independence)
        if assessment.disposition is ReviewDisposition.INVALID:
            raise SemanticReviewError("invalid independent review cannot be recorded")
        payload: dict[str, Any] = {
            "require_independence": require_independence,
            "independent_review": review.structurally_independent,
            "review_id": review.review_id,
            "candidate_event_id": candidate_event_id,
            "meaning_event_id": candidate.meaning_event_id,
            "selection_event_id": candidate.selection_event_id,
            "candidate_digest": candidate.digest,
            "reviewer_kind": review.reviewer_kind.value,
            "reviewer_execution_id": review.reviewer_execution_id,
            "reviewer_model": review.reviewer_model,
            "reviewer_independence_domain": review.reviewer_independence_domain,
            "atom_reviews": [
                {
                    "atom_id": item.atom_id,
                    "preserved": item.preserved,
                    "risks": [risk.value for risk in item.risks],
                }
                for item in review.atom_reviews
            ],
            "added_claims_detected": review.added_claims_detected,
            "speech_act_preserved": review.speech_act_preserved,
            "protected_literals_preserved": review.protected_literals_preserved,
            "disposition": assessment.disposition.value,
            "risks": [risk.value for risk in assessment.risks],
            "safe_for_automatic_delivery": False,
            "raw_review_prose_stored_in_journal": False,
            "truth_claimed": False,
            "evidence_entailment_proven": False,
            "action_authority_granted": False,
            "route_authority_granted": False,
            "delivery_authority_granted": False,
        }
        if scope is not None:
            payload['assessment_scope']=scope
        if protocol_recovery_event_id is not None:
            if not isinstance(protocol_recovery_event_id,str) or not _ID_RE.fullmatch(protocol_recovery_event_id):
                raise SemanticReviewError('invalid semantic protocol recovery reference')
            payload['protocol_recovery_event_id']=protocol_recovery_event_id
        payload["integrity_authenticator"] = self.protector.authenticate_json(
            "message.semantic_review.v1",
            self._authentication_document("message.semantic_review.v1", payload),
        )
        event = EventEnvelope(
            event_id=f"message.semantic_review:{review.review_id}",
            event_type="message.semantic_reviewed",
            source="alive.semantic-review",
            actor=str(actor),
            subject=candidate_record.event.subject,
            correlation_id=candidate.frame_id,
            causation_id=candidate_event_id,
            occurred_at=candidate_record.event.observed_at,
            observed_at=current,
            sensitivity=candidate_record.event.sensitivity,
            expires_at=candidate.expires_at,
            payload=payload,
        )
        record = self._append_idempotent(event)
        verified = self.verify_review(record, as_of=current, allow_correlated=not require_independence)
        if verified is None:
            raise SemanticReviewError("stored semantic review failed verification")
        return verified

    def verify_review(
        self, record: JournalRecord, *, as_of: datetime | None = None, allow_correlated: bool = False
    ) -> StoredReviewReceipt | None:
        if type(allow_correlated) is not bool:
            raise SemanticReviewError('invalid correlated review mode')
        event = record.event
        payload = event.payload
        try:
            current = self._utc(as_of or datetime.now(timezone.utc), "as_of")
            if (
                event.expires_at is None
                or current < event.observed_at
                or current >= event.expires_at
            ):
                return None
            supplied = str(payload["integrity_authenticator"])
            if not self.protector.verify_json(
                "message.semantic_review.v1",
                self._authentication_document("message.semantic_review.v1", payload),
                supplied,
            ):
                return None
            candidate_event_id = str(payload["candidate_event_id"])
            candidate = self.resolve_model_candidate(
                candidate_event_id, as_of=current
            )
            candidate_record = self.journal.get(candidate_event_id)
            if candidate is None or candidate_record is None:
                return None
            scope=self._assessment_scope(candidate,event.subject)
            if payload.get('assessment_scope')!=scope or scope is not None and payload['added_claims_detected'] is not False:
                return None
            atom_reviews_raw = payload["atom_reviews"]
            if not isinstance(atom_reviews_raw, (list, tuple)):
                return None
            review = IndependentSemanticReview(
                review_id=str(payload["review_id"]),
                meaning_event_id=str(payload["meaning_event_id"]),
                candidate_digest=str(payload["candidate_digest"]),
                renderer_execution_id=candidate.renderer_execution_id,
                renderer_model=candidate.renderer_model,
                renderer_independence_domain=candidate.renderer_independence_domain,
                reviewer_kind=ReviewerKind(payload["reviewer_kind"]),
                reviewer_execution_id=str(payload["reviewer_execution_id"]),
                reviewer_model=(
                    str(payload["reviewer_model"])
                    if payload.get("reviewer_model") is not None
                    else None
                ),
                reviewer_independence_domain=str(
                    payload["reviewer_independence_domain"]
                ),
                atom_reviews=tuple(
                    AtomReview(
                        str(item["atom_id"]),
                        item["preserved"],
                        tuple(SemanticRisk(value) for value in item["risks"]),
                    )
                    for item in atom_reviews_raw
                ),
                added_claims_detected=payload["added_claims_detected"],
                speech_act_preserved=payload["speech_act_preserved"],
                protected_literals_preserved=payload[
                    "protected_literals_preserved"
                ],
            )
            document = self.meanings.resolve(candidate.meaning_event_id)
            required = payload.get('require_independence', True)
            if (type(required) is not bool
                    or payload.get('independent_review', review.structurally_independent) is not review.structurally_independent
                    or (not review.structurally_independent and (required or not allow_correlated))):
                return None
            assessment = _assess_review(document, candidate.text, review, require_independence=required)
            from .semantic_comparator import SemanticComparator
            if not SemanticComparator.verify_protocol_recovery_v1(self,record,candidate,document):
                return None
            return (
                StoredReviewReceipt(
                    event.event_id,
                    candidate_event_id,
                    review.review_id,
                    assessment,
                )
                if event.event_type == "message.semantic_reviewed"
                and event.source == "alive.semantic-review"
                and event.causation_id == candidate_event_id
                and event.correlation_id == candidate.frame_id
                and event.subject == candidate_record.event.subject
                and event.observed_at >= candidate_record.event.observed_at
                and event.observed_at < candidate.expires_at
                and event.expires_at == candidate.expires_at
                and payload.get("selection_event_id")
                == candidate.selection_event_id
                and payload.get("disposition") == assessment.disposition.value
                and tuple(payload.get("risks") or ())
                == tuple(risk.value for risk in assessment.risks)
                and assessment.disposition is not ReviewDisposition.INVALID
                and payload.get("safe_for_automatic_delivery") is False
                and payload.get("raw_review_prose_stored_in_journal") is False
                and payload.get("truth_claimed") is False
                and payload.get("evidence_entailment_proven") is False
                and payload.get("action_authority_granted") is False
                and payload.get("route_authority_granted") is False
                and payload.get("delivery_authority_granted") is False
                else None
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            ContentVaultError,
            SemanticRenderingError,
            SemanticReviewError,
        ):
            return None

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
            raise SemanticReviewError(
                "semantic review identity was reused with different semantics"
            )
        return existing


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate_semantic_reviews(
    predictions: Iterable[SemanticReplayPrediction],
    judgments: Iterable[SemanticCaseJudgment],
    *,
    expected_case_ids: Iterable[str],
) -> SemanticReviewQualityReport:
    """Score a complete blinded cohort without collapsing distinct failures."""

    predicted = tuple(predictions)
    judged = tuple(judgments)
    expected_raw = tuple(str(item).strip() for item in expected_case_ids)
    expected = tuple(dict.fromkeys(expected_raw))
    if (
        not expected
        or len(expected) != len(expected_raw)
        or any(not _ID_RE.fullmatch(item) for item in expected)
    ):
        raise SemanticReviewError("expected semantic case IDs must be unique")
    prediction_ids = [item.case_id for item in predicted]
    judgment_ids = [item.case_id for item in judged]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise SemanticReviewError("each case requires exactly one prediction")
    if len(judgment_ids) != len(set(judgment_ids)):
        raise SemanticReviewError("each case requires exactly one judgment")
    if set(prediction_ids) != set(expected) or set(judgment_ids) != set(expected):
        raise SemanticReviewError("the complete expected cohort must be scored")
    by_case = {item.case_id: item for item in judged}
    for item in predicted:
        if item.language_tag != by_case[item.case_id].language_tag:
            raise SemanticReviewError("prediction language crosses case boundary")

    faithful = sum(item.faithful for item in judged)
    risky = len(judged) - faithful
    faithful_acceptances = sum(
        prediction.accepted_as_preserved and by_case[prediction.case_id].faithful
        for prediction in predicted
    )
    unsafe_acceptances = sum(
        prediction.accepted_as_preserved and not by_case[prediction.case_id].faithful
        for prediction in predicted
    )
    independence_violations = sum(
        not prediction.structurally_independent for prediction in predicted
    )
    all_expected_risks = tuple(
        sorted(
            {risk for item in judged for risk in item.expected_risks},
            key=lambda risk: risk.value,
        )
    )
    risk_recall: list[tuple[SemanticRisk, float]] = []
    for risk in all_expected_risks:
        relevant = [item for item in judged if risk in item.expected_risks]
        caught = sum(
            risk in next(
                prediction.predicted_risks
                for prediction in predicted
                if prediction.case_id == item.case_id
            )
            for item in relevant
        )
        risk_recall.append((risk, caught / len(relevant)))
    predicted_issues = sum(len(item.predicted_risks) for item in predicted)
    correct_issues = sum(
        len(set(item.predicted_risks) & set(by_case[item.case_id].expected_risks))
        for item in predicted
    )
    macro = (
        sum(value for _risk, value in risk_recall) / len(risk_recall)
        if risk_recall
        else None
    )
    return SemanticReviewQualityReport(
        cases=len(judged),
        languages=tuple(sorted({item.language_tag for item in judged})),
        faithful_cases=faithful,
        risky_cases=risky,
        unsafe_acceptances=unsafe_acceptances,
        faithful_acceptances=faithful_acceptances,
        independence_violations=independence_violations,
        unsafe_acceptance_rate=_ratio(unsafe_acceptances, risky),
        faithful_acceptance_rate=_ratio(faithful_acceptances, faithful),
        issue_precision=_ratio(correct_issues, predicted_issues),
        macro_risk_recall=macro,
        risk_recall=tuple(risk_recall),
        renderer_models=tuple(sorted({item.renderer_model for item in predicted})),
        reviewer_models=tuple(sorted({item.reviewer_model for item in predicted})),
    )


def qualify_semantic_review_report(
    report: SemanticReviewQualityReport,
    *,
    minimum_cases: int = 100,
    minimum_languages: int = 3,
) -> SemanticReviewQualification:
    """Minimum gate for a shadow comparator, never for automatic delivery."""

    failures: list[str] = []
    if report.cases < minimum_cases:
        failures.append("insufficient_cases")
    if len(report.languages) < minimum_languages:
        failures.append("insufficient_languages")
    if report.faithful_cases == 0 or report.risky_cases == 0:
        failures.append("missing_faithful_or_risky_controls")
    if report.independence_violations:
        failures.append("reviewer_independence_violation")
    if report.unsafe_acceptance_rate is None or report.unsafe_acceptance_rate > 0:
        failures.append("unsafe_candidate_accepted")
    if (
        report.faithful_acceptance_rate is None
        or report.faithful_acceptance_rate < 0.98
    ):
        failures.append("faithful_acceptance_below_0.98")
    if report.issue_precision is None or report.issue_precision < 0.95:
        failures.append("issue_precision_below_0.95")
    if report.macro_risk_recall is None or report.macro_risk_recall < 0.95:
        failures.append("macro_risk_recall_below_0.95")
    if any(value < 0.90 for _risk, value in report.risk_recall):
        failures.append("per_risk_recall_below_0.90")
    return SemanticReviewQualification(not failures, tuple(failures))
