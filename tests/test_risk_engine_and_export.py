"""End-to-end tests for 12-point risk engine, .docx LSR exporter, CLI, and AdharamBench."""

import json
from pathlib import Path

from adharam_ai.cli import main as cli_main
from adharam_ai.exporters.docx_lsr_builder import build_lsr_docx
from adharam_ai.schemas.deed_record import DossierInput
from adharam_ai.verifiers.risk_engine import run_title_audit


def test_clean_kozhikode_dossier_and_docx_export(tmp_path: Path) -> None:
    dossier_path = Path("adharam_bench/dossiers/01_kozhikode_clean_malabar.json")
    dossier = DossierInput.model_validate(json.loads(dossier_path.read_text(encoding="utf-8")))
    audit = run_title_audit(dossier)

    assert audit.overall_marketable_title is True
    assert len(audit.risk_findings) == 12
    assert all(f.severity == "PASS" for f in audit.risk_findings)

    out_docx = tmp_path / "sample_lsr.docx"
    saved = build_lsr_docx(dossier, audit, out_docx)
    assert saved.exists()
    assert saved.stat().st_size > 10_000


def test_cli_audit_command(tmp_path: Path) -> None:
    out_docx = tmp_path / "cli_lsr.docx"
    exit_code = cli_main(
        [
            "audit",
            "adharam_bench/dossiers/02_ernakulam_clean_travancore.json",
            "-o",
            str(out_docx),
        ]
    )
    assert exit_code == 0
    assert out_docx.exists()


def test_adharam_bench_scores_100_pct() -> None:
    from adharam_bench.evaluate import run_benchmark

    metrics = run_benchmark(Path("adharam_bench"))
    assert metrics["dossiers_evaluated"] == 4.0
    assert metrics["marketable_title_accuracy_pct"] == 100.0
    assert metrics["chain_dag_accuracy_pct"] == 100.0
    assert metrics["statutory_defect_recall_pct"] == 100.0
