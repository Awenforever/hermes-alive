#!/usr/bin/env python3
"""Opt-in real Hermes reviewer replay over the public synthetic seed.

This evaluates a reviewer, not the renderer/reviewer pair or production safety.
No gateway hooks, production state, messages, or real user content are used.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import hashlib
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
from alive_kernel.semantic_comparator import SemanticComparator, _REVIEW_PROMPT
from alive_kernel.semantic_review import (
    SemanticRisk, SemanticReplayPrediction, SemanticCaseJudgment,
    evaluate_semantic_reviews,
)


def load_fixture():
    return json.loads((ROOT / "__tests__/fixtures/semantic_fidelity_seed_v1.json").read_text(
        encoding="utf-8"
    ))


def summarize(fixture, cases, results, output_path, requested_model=None):
    case_map = {case["case_id"]: case for case in cases}
    result_ids = [item["case_id"] for item in results]
    if len(result_ids) != len(set(result_ids)) or set(result_ids) != set(case_map):
        raise ValueError("results must cover the exact cohort once")
    predictions, judgments = [], []
    for item in results:
        if item["status"] != "scored":
            continue
        case = case_map[item["case_id"]]
        if item["expected_risks"] != case["expected_risks"]:
            raise ValueError("saved labels disagree with fixture")
        risks = tuple(SemanticRisk(value) for value in item["predicted_risks"])
        predictions.append(SemanticReplayPrediction(
            case_id=case["case_id"], candidate_id=f"seed:{case['case_id']}",
            language_tag=case["language_tag"], renderer_model="synthetic/seed",
            reviewer_model=item["actual_model"], renderer_independence_domain="synthetic/source",
            reviewer_independence_domain="empirical/reviewer",
            accepted_as_preserved=not risks, predicted_risks=risks,
        ))
        judgments.append(SemanticCaseJudgment(
            case["case_id"], case["language_tag"], tuple(case["expected_risks"])
        ))
    complete = len(predictions) == len(cases)
    report = evaluate_semantic_reviews(
        predictions, judgments, expected_case_ids=list(case_map)
    ) if complete else None
    metrics = asdict(report) if report else None
    if metrics is not None:
        # Labels specify focal risks, not all defensible risk classes.
        metrics["issue_precision"] = None
    output = {
        "schema_version": 1, "scope": "reviewer_only_synthetic_seed",
        "requested_model": requested_model,
        "fixture_sha256": hashlib.sha256(json.dumps(
            fixture, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "qualification_evidence": False, "complete": complete,
        "requested_cases": len(cases), "results": results,
        "annotation_scope": fixture["annotation_scope"], "metrics": metrics,
        "qualification": {"qualified": False, "failures": [
            "nonexhaustive_seed_annotations", "insufficient_cases", "no_human_calibration"
        ]},
        "production_delivery_qualified": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("REVIEWER_REPLAY_COMPLETE=" + str(complete), flush=True)
    return 0 if complete else 2


async def replay(args):
    from agent.auxiliary_client import async_call_llm

    fixture = load_fixture()
    cases = fixture["cases"][args.offset:args.offset + args.limit]
    results = []
    for case in cases:
        route = {}
        try:
            # Neither gold labels nor challenge tags enter the review prompt.
            payload = {
                "meaning": {"atoms": [{"atom_id": "body", "text": case["meaning"]}]},
                "candidate": case["candidate"],
            }
            response = await asyncio.wait_for(async_call_llm(
                task="alive_semantic_review", model=args.model,
                messages=[{"role": "system", "content": _REVIEW_PROMPT},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                temperature=0, max_tokens=1500, timeout=args.timeout, route_info=route,
            ), timeout=args.timeout)
            text, model, provider = SemanticComparator._response(response, route)
            findings = SemanticComparator._findings(text)
            atoms = findings["atom_reviews"]
            if len(atoms) != 1 or atoms[0].atom_id != "body":
                raise ValueError("incomplete atom findings")
            risks = list(atoms[0].risks)
            if findings["added_claims_detected"]:
                risks.append(SemanticRisk.UNSUPPORTED_ADDITION)
            if not findings["speech_act_preserved"]:
                risks.append(SemanticRisk.SPEECH_ACT_SHIFT)
            if any(not isinstance(findings[key], bool) for key in (
                "added_claims_detected", "speech_act_preserved", "protected_literals_preserved"
            )):
                raise ValueError("nonboolean findings")
            # A literal failure without a classified issue is an incomplete
            # review, not an invented generic risk or an accepted candidate.
            if not findings["protected_literals_preserved"] and not risks:
                raise ValueError("unclassified literal failure")
            unique_risks = tuple(dict.fromkeys(risks))
            result = {"case_id": case["case_id"], "status": "scored",
                      "actual_model": model, "provider": provider,
                      "predicted_risks": [risk.value for risk in unique_risks],
                      "expected_risks": case["expected_risks"]}
        except Exception as exc:
            result = {"case_id": case["case_id"], "status": "failed",
                      "error_class": type(exc).__name__}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return summarize(fixture, cases, results, args.output, args.model)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-profile", type=Path,
                        help="Read-only source profile; only config.yaml/.env are copied")
    parser.add_argument("--hermes-source", default="/opt/hermes")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--rescore", nargs="+", type=Path,
                        help="Combine/rescore saved batches without provider calls")
    args = parser.parse_args()
    if (
        not 1 <= args.limit <= 12 or not 0 <= args.offset < 12
        or args.offset + args.limit > 12 or not 0 < args.timeout <= 120
    ):
        parser.error("case range must stay in 0..11 and timeout must be in (0,120]")
    if args.rescore:
        results = []
        for path in args.rescore:
            batch = json.loads(path.read_text(encoding="utf-8"))
            if batch.get("scope") != "reviewer_only_synthetic_seed":
                parser.error("saved report has an incompatible scope")
            results.extend(batch["results"])
        fixture = load_fixture()
        cases = fixture["cases"][args.offset:args.offset + args.limit]
        return summarize(fixture, cases, results, args.output, args.model)
    if args.hermes_profile is None:
        parser.error("--hermes-profile is required for real calls")
    # Hermes gets a disposable writable profile; user memories, sessions,
    # cron jobs and channel state are never copied into it.
    with tempfile.TemporaryDirectory(prefix="alive-reviewer-replay-") as tmp:
        for name in ("config.yaml", ".env"):
            source = args.hermes_profile / name
            if source.is_file():
                target = Path(tmp) / name
                shutil.copyfile(source, target)
                os.chmod(target, 0o600)
        os.environ["HERMES_HOME"] = tmp
        sys.path.insert(0, args.hermes_source)
        from dotenv import load_dotenv
        load_dotenv(Path(tmp) / ".env", override=False)
        logging.disable(logging.CRITICAL)
        return asyncio.run(replay(args))


if __name__ == "__main__":
    raise SystemExit(main())
