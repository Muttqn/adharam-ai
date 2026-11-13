"""Generate a 5-part Bank Legal Scrutiny Report (.docx) from a TitleAuditResult."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt

from adharam_ai.schemas.deed_record import DossierInput
from adharam_ai.schemas.risk_report import TitleAuditResult


def _add_kv_table(doc: Document, rows: list[tuple[str, str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for idx, (key, value) in enumerate(rows):
        cells = table.rows[idx].cells
        cells[0].text = key
        cells[1].text = value
        for run in cells[0].paragraphs[0].runs:
            run.bold = True


def build_lsr_docx(
    dossier: DossierInput,
    audit: TitleAuditResult,
    output_path: str | Path,
) -> Path:
    """Compile a 5-part Bank Legal Scrutiny Report (.docx) and write it to disk."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)

    sorted_deeds = sorted(dossier.deeds, key=lambda d: d.registration_meta.execution_date)
    present_deed = sorted_deeds[-1]
    sched = present_deed.property_schedule
    claimants_str = ", ".join(c.name_en for c in present_deed.claimants)

    title = doc.add_heading("TITLE INVESTIGATION REPORT / LEGAL SCRUTINY REPORT (LSR)", level=1)
    title.alignment = 1
    subtitle = doc.add_paragraph("Generated via AdharamAI Engine — Advocate Review Draft")
    subtitle.alignment = 1

    # PART I
    doc.add_heading("PART I: DOSSIER METADATA & PROPERTY SCHEDULE", level=2)
    _add_kv_table(
        doc,
        [
            ("Dossier ID", dossier.dossier_id),
            ("Bank & Branch", f"{dossier.bank_name} — {dossier.branch_name}"),
            ("Applicant / Borrower", dossier.applicant_name),
            ("Present Title Holder(s)", claimants_str),
            ("Nature of Facility", dossier.facility_type),
            ("Revenue Region / Taluk", f"{sched.revenue_region} / {sched.taluk}, {sched.district}"),
            ("Village / Local Body", f"{sched.village} ({sched.amsom_desom_or_kara})"),
            (
                "Survey & Re-Survey",
                (
                    f"Old Sy: {sched.old_survey_no} | Re-Sy Block {sched.resurvey_block or '-'}, "
                    f"Re-Sy No: {sched.resurvey_no or '-'}"
                ),
            ),
            (
                "Extent Verified",
                (
                    f"{audit.area_audit.deed_extent_ares} Ares ({audit.area_audit.deed_extent_cents} Cents) — "
                    f"Status: {audit.area_audit.status}"
                ),
            ),
            (
                "Boundaries (E / S / W / N)",
                (
                    f"E: {sched.boundaries_en.east} | S: {sched.boundaries_en.south} | "
                    f"W: {sched.boundaries_en.west} | N: {sched.boundaries_en.north}"
                ),
            ),
        ],
    )

    # PART II
    doc.add_heading("PART II: CHRONOLOGICAL DEVOLUTION OF TITLE", level=2)
    for idx, deed in enumerate(sorted_deeds, start=1):
        exec_names = ", ".join(p.name_en for p in deed.executants)
        claim_names = ", ".join(p.name_en for p in deed.claimants)
        doc.add_paragraph(
            f"Step {idx} ({deed.registration_meta.execution_date}): "
            f"{deed.doc_type_en} ({deed.doc_type_ml}) No. {deed.registration_meta.doc_number.value} "
            f"of {deed.registration_meta.sro_name} executed by {exec_names} in favor of {claim_names} "
            f"(Old Sy. No. {deed.property_schedule.old_survey_no}).",
            style="List Bullet",
        )
    if not audit.chain_verification.is_complete:
        for issue in audit.chain_verification.issues:
            p = doc.add_paragraph()
            run = p.add_run(f"[CHAIN DEFECT — {issue.issue_type}] {issue.detail}")
            run.bold = True

    # PART III
    doc.add_heading("PART III: REVENUE, PORTAL & ENCUMBRANCE VERIFICATION", level=2)
    btr = dossier.btr_record
    ec = dossier.ec_record
    _add_kv_table(
        doc,
        [
            ("ReLIS Basic Tax Receipt", f"No. {btr.receipt_number} dated {btr.receipt_date} (Thandapper {btr.thandapper_no})"),
            ("BTR Classification", f"{btr.land_nature_btr} — {audit.area_audit.notes}"),
            ("PEARL Encumbrance Cert.", f"No. {ec.ec_number} ({ec.period_from} to {ec.period_to}, {audit.ec_verification.coverage_years} yrs)"),
            ("Active Liens / Attachments", "NONE" if not audit.ec_verification.active_liens else "; ".join(audit.ec_verification.active_liens)),
            ("BTR Owner Name Match", "VERIFIED" if audit.ec_verification.owner_name_matched else "MISMATCH — VERIFY MUTATION"),
        ],
    )

    # PART IV
    doc.add_heading("PART IV: 12-POINT KERALA STATUTORY RISK AUDIT", level=2)
    risk_table = doc.add_table(rows=len(audit.risk_findings) + 1, cols=4)
    risk_table.style = "Table Grid"
    headers = ["Rule", "Statutory Check", "Status", "Finding / Curative Action"]
    for col_idx, text in enumerate(headers):
        cell = risk_table.rows[0].cells[col_idx]
        cell.text = text
        for run in cell.paragraphs[0].runs:
            run.bold = True

    for row_idx, finding in enumerate(audit.risk_findings, start=1):
        cells = risk_table.rows[row_idx].cells
        cells[0].text = finding.rule_id
        cells[1].text = f"{finding.title}\n({finding.statute})"
        cells[2].text = finding.severity
        detail = finding.finding
        if finding.curative_action:
            detail += f"\nCurative Action: {finding.curative_action}"
        cells[3].text = detail

    # PART V
    doc.add_heading("PART V: CERTIFICATE OF TITLE & SEC. 58(f) DEPOSIT CHECKLIST", level=2)
    verdict = doc.add_paragraph()
    verdict_text = (
        "OPINION: Title is CLEAR, MARKETABLE, and FREE FROM ENCUMBRANCES for creation of Equitable Mortgage under Sec. 58(f), Transfer of Property Act, 1882."
        if audit.overall_marketable_title
        else "OPINION: TITLE DEFECTS / STATUTORY RED FLAGS DETECTED. Subject to curative compliance listed in Part IV before mortgage."
    )
    v_run = verdict.add_run(verdict_text)
    v_run.bold = True

    doc.add_paragraph("Mandatory Original Documents to be Deposited with the Bank:")
    for item in audit.sec58f_deposit_checklist:
        doc.add_paragraph(item, style="List Number")

    doc.save(str(out_file))
    return out_file
