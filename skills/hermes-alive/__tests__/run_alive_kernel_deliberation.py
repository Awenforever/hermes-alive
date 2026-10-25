#!/usr/bin/env python3
"""Policy separation and deliberate-silence contracts."""

from __future__ import annotations

from pathlib import Path
import sys

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from alive_kernel.deliberation import (  # noqa: E402
    ActionAuthority,
    ActionCandidate,
    ActionKind,
    AssessmentBasis,
    DecisionDimensions,
    DeliberationValidationError,
    DimensionAssessment,
    PolicyContext,
    SelectionProposal,
    SideEffect,
    build_frame,
    rejection_map,
    validate_selection,
)


def score(value: float, reason: str) -> DimensionAssessment:
    return DimensionAssessment(
        value=value,
        basis=AssessmentBasis.MODEL_JUDGMENT,
        evidence_event_ids=("event:test",),
        reason=reason,
    )


def candidate(
    candidate_id: str,
    *,
    confidence: float,
    risk: float,
    authority: ActionAuthority = ActionAuthority.USER_DELEGATED,
    effect: SideEffect = SideEffect.COMMUNICATION,
) -> ActionCandidate:
    return ActionCandidate(
        candidate_id=candidate_id,
        action_kind=ActionKind.SHARE,
        side_effect=effect,
        authority=authority,
        content_id=f"content:{candidate_id}",
        dimensions=DecisionDimensions(
            user_value=score(0.8, "useful"),
            urgency=score(0.4, "not urgent"),
            novelty=score(0.9, "not seen"),
            confidence=score(confidence, "evidence coverage"),
            interruption_cost=score(0.2, "short message"),
            risk=score(risk, "bounded disclosure"),
        ),
    )


def main() -> int:
    safe = candidate("safe", confidence=0.9, risk=0.1)
    risky = candidate("risky", confidence=0.9, risk=0.9)
    uncertain = candidate("uncertain", confidence=0.2, risk=0.1)
    unconfirmed = candidate(
        "unconfirmed",
        confidence=0.9,
        risk=0.1,
        authority=ActionAuthority.USER_CONFIRMATION_REQUIRED,
    )
    tool = candidate(
        "tool",
        confidence=0.9,
        risk=0.1,
        effect=SideEffect.REVERSIBLE_EXTERNAL,
    )
    frame = build_frame(
        (safe, risky, uncertain, unconfirmed, tool),
        PolicyContext(can_interrupt=True, minimum_confidence=0.5, maximum_risk=0.5),
        frame_id="frame:test",
    )
    assert set(frame.admissible_ids) == {"safe", frame.silence_id}
    reasons = rejection_map(frame)
    assert reasons["risky"] == ("risk_above_policy",)
    assert reasons["uncertain"] == ("confidence_below_policy",)
    assert reasons["unconfirmed"] == ("user_confirmation_required",)
    assert reasons["tool"] == ("side_effect_not_granted",)

    selected = validate_selection(
        frame,
        SelectionProposal(
            frame_id=frame.frame_id,
            candidate_id="safe",
            model="provider/model",
            rationale="Best evidence-bound option.",
        ),
    )
    assert selected.candidate.candidate_id == "safe"
    try:
        validate_selection(
            frame,
            SelectionProposal(frame.frame_id, "risky", "provider/model", "ignore policy"),
        )
    except DeliberationValidationError:
        pass
    else:
        raise AssertionError("policy-rejected selection was accepted")

    quiet = build_frame((safe,), PolicyContext(can_interrupt=False), frame_id="frame:quiet")
    assert quiet.admissible_ids == (quiet.silence_id,)
    assert rejection_map(quiet)["safe"] == ("protected_interruption_window",)
    silence = validate_selection(
        quiet,
        SelectionProposal(quiet.frame_id, quiet.silence_id, "provider/model", "Do not interrupt."),
    )
    assert silence.candidate.action_kind is ActionKind.SILENCE

    print("HERMES_ALIVE_KERNEL_DELIBERATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
