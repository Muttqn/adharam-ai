# AdharamAI

**Neuro-Symbolic Malayalam ↔ English Property Conveyancing & Automated Bank Title Scrutiny Engine**

AdharamAI audits 13-to-30-year chains of Kerala property deeds (*Adharangal*), prior title deeds (*Munnadharam*), ReLIS Basic Land Tax Receipts (BTR), and PEARL Encumbrance Certificates (EC) using deterministic Python graph, area-math, and statutory risk verifiers, compiling ready-to-review **5-Part Bank Legal Scrutiny Reports (`.docx`)**.

## Architecture

```text
Multi-Document Dossier (JSON / Vision-OCR Provenance)
  │
  ├──▶ Chain-of-Title DAG (chain_verifier.py)
  │      └─ NetworkX Munnadharam graph + Survey subdivision tree (42/3 -> 42/3A1)
  ├──▶ Conveyancing Area Math (area_math.py)
  │      └─ Exact Decimal Ares/Cents/Acres/6-ft Kole math + Form 10 variance thresholds
  ├──▶ PEARL EC Cross-Verifier (ec_verifier.py)
  │      └─ Order-independent Indic name matching + active lien/Gahan detector
  └──▶ 12-Point Statutory Risk Engine (risk_engine.py)
         └─ Paddy Land (Form 5/6), Life Estate, Senior Citizens Sec. 23, KLR Sec. 81,
            Pattayam lock-in, Personal Law (1975 JHF / Shariat Wasiyat / ISA), SARFAESI access
  │
  ▼
5-Part Bank LSR (.docx) + Sec. 58(f) Equitable Mortgage Checklist (docx_lsr_builder.py)
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run the test suite and linter:
```powershell
pytest -v
ruff check src tests adharam_bench
```

Audit a dossier and generate a Bank LSR `.docx`:
```powershell
adharam-ai audit adharam_bench/dossiers/01_kozhikode_clean_malabar.json -o examples/sample_kozhikode_lsr.docx
```

Run the `AdharamBench` evaluation suite:
```powershell
python -m adharam_bench.evaluate
```

## Repository Structure

```text
adharam-ai/
├── pyproject.toml
├── glossary/
│   ├── kerala_legal_glossary.json       # Malabar & Travancore-Cochin conveyancing terms
│   └── historical_units_table.json      # Ares, Cents, Acres, 6-ft/8-ft Kole conversions
├── src/adharam_ai/
│   ├── schemas/                         # Pydantic v2 DeedRecord, ECRecord, BTRRecord, TitleAuditResult
│   ├── verifiers/                       # area_math, chain_verifier, ec_verifier, 12-point risk_engine
│   ├── exporters/                       # 5-part Bank LSR .docx builder
│   └── cli.py                           # adharam-ai CLI entrypoint
├── adharam_bench/                       # Multi-document Malabar & Travancore evaluation dossiers
├── examples/                            # Sample generated Bank LSR (.docx)
├── docs/WHITEPAPER.md                   # Full technical whitepaper & legal taxonomy
└── tests/                               # Unit & end-to-end pytest suite
```
