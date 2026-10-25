"""Replay accounting cannot hide failures or overstate incomplete labels."""
from pathlib import Path
import importlib.util
import json
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "semantic_replay", ROOT / "scripts/semantic-review-replay.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    fixture = module.load_fixture()
    assert fixture["annotation_scope"] == "targeted_non_exhaustive"
    cases = (fixture["cases"][0], fixture["cases"][3])
    results = [
        {"case_id": cases[0]["case_id"], "status": "scored", "actual_model": "model/a",
         "predicted_risks": [], "expected_risks": []},
        {"case_id": cases[1]["case_id"], "status": "scored", "actual_model": "model/a",
         "predicted_risks": ["omission", "contradiction"], "expected_risks": ["omission"]},
    ]
    with tempfile.TemporaryDirectory(prefix="semantic-replay-report-") as directory:
        output = Path(directory) / "report.json"
        assert module.summarize(fixture, cases, results, output) == 0
        report = json.loads(output.read_text())
        assert report["complete"]
        assert report["metrics"]["issue_precision"] is None
        assert report["metrics"]["macro_risk_recall"] == 1
        assert not report["qualification"]["qualified"]
        assert not report["production_delivery_qualified"]
        failed = [results[0], {"case_id": cases[1]["case_id"], "status": "failed",
                               "error_class": "TimeoutError"}]
        assert module.summarize(fixture, cases, failed, output) == 2
        incomplete = json.loads(output.read_text())
        assert not incomplete["complete"] and incomplete["metrics"] is None
        for invalid in (results[:1], results + [results[0]]):
            try:
                module.summarize(fixture, cases, invalid, output)
            except ValueError:
                pass
            else:
                raise AssertionError("partial or duplicated cohort was scored")
    print("HERMES_ALIVE_SEMANTIC_REPLAY_REPORTING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
