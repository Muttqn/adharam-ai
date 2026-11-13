"""AdharamBench: Deterministic evaluation runner across Malabar & Travancore dossiers."""

from __future__ import annotations

import json
from pathlib import Path

from adharam_ai.schemas.deed_record import DossierInput
from adharam_ai.verifiers.risk_engine import run_title_audit


def run_benchmark(bench_dir: Path | None = None) -> dict[str, float]:
    """Evaluate all dossiers in adharam_bench/dossiers against ground_truth/expected.json."""
    root = bench_dir or Path(__file__).resolve().parent
    dossiers_dir = root / "dossiers"
    gt_path = root / "ground_truth" / "expected.json"
    expected_map: dict[str, dict] = json.loads(gt_path.read_text(encoding="utf-8"))

    total = 0
    marketable_correct = 0
    chain_correct = 0
    planted_defects_total = 0
    planted_defects_recalled = 0

    for json_file in sorted(dossiers_dir.glob("*.json")):
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        dossier = DossierInput.model_validate(raw)
        audit = run_title_audit(dossier)
        gt = expected_map[dossier.dossier_id]

        total += 1
        if audit.overall_marketable_title == gt["overall_marketable_title"]:
            marketable_correct += 1
        if audit.chain_verification.is_complete == gt["chain_complete"]:
            chain_correct += 1

        flagged_ids = {f.rule_id for f in audit.risk_findings if f.severity != "PASS"}
        for expected_rule in gt["expected_flagged_rules"]:
            planted_defects_total += 1
            if expected_rule in flagged_ids:
                planted_defects_recalled += 1

    defect_recall = (
        (planted_defects_recalled / planted_defects_total * 100.0)
        if planted_defects_total
        else 100.0
    )
    metrics = {
        "dossiers_evaluated": float(total),
        "marketable_title_accuracy_pct": round(marketable_correct / total * 100.0, 2),
        "chain_dag_accuracy_pct": round(chain_correct / total * 100.0, 2),
        "statutory_defect_recall_pct": round(defect_recall, 2),
    }
    return metrics


if __name__ == "__main__":
    results = run_benchmark()
    print("=== AdharamBench Evaluation Results ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
