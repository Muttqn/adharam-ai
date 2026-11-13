"""Command-line interface for AdharamAI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adharam_ai.exporters.docx_lsr_builder import build_lsr_docx
from adharam_ai.schemas.deed_record import DossierInput
from adharam_ai.verifiers.risk_engine import run_title_audit


def run_audit_command(dossier_path: Path, output_docx: Path | None) -> int:
    """Load a dossier JSON, run deterministic verification, and optionally write .docx LSR."""
    raw = json.loads(dossier_path.read_text(encoding="utf-8"))
    dossier = DossierInput.model_validate(raw)
    audit = run_title_audit(dossier)

    print(f"Dossier: {audit.dossier_id}")
    print(f"Marketable Title: {'YES' if audit.overall_marketable_title else 'NO (DEFECTS FOUND)'}")
    print(f"Chain Complete: {audit.chain_verification.is_complete}")
    print(f"Area Audit: {audit.area_audit.status} ({audit.area_audit.variance_pct}% variance)")
    print(f"Active EC Liens: {len(audit.ec_verification.active_liens)}")

    flagged = [f for f in audit.risk_findings if f.severity != "PASS"]
    if flagged:
        print("Flagged Statutory Checks:")
        for f in flagged:
            print(f"  - [{f.severity}] {f.rule_id} {f.title}: {f.finding}")

    if output_docx is not None:
        saved = build_lsr_docx(dossier, audit, output_docx)
        print(f"Generated LSR: {saved}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entrypoint for the `adharam-ai` CLI."""
    parser = argparse.ArgumentParser(
        prog="adharam-ai",
        description="AdharamAI: Kerala Property Conveyancing & Bank Title Scrutiny CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit a property dossier JSON")
    audit_parser.add_argument("dossier", type=Path, help="Path to DossierInput JSON file")
    audit_parser.add_argument(
        "-o", "--output", type=Path, default=None, help="Output .docx LSR path"
    )

    args = parser.parse_args(argv)
    if args.command == "audit":
        return run_audit_command(args.dossier, args.output)
    return 1


if __name__ == "__main__":
    sys.exit(main())
