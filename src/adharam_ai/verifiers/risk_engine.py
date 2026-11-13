"""12-Point Kerala Statutory Title Risk Rubric & Dossier Audit Orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from adharam_ai.schemas.deed_record import DeedRecord, DossierInput
from adharam_ai.schemas.risk_report import (
    AreaAuditResult,
    ChainVerificationResult,
    ECVerificationResult,
    RiskFinding,
    TitleAuditResult,
)
from adharam_ai.verifiers.area_math import audit_deed_vs_btr_area
from adharam_ai.verifiers.chain_verifier import verify_chain_of_title
from adharam_ai.verifiers.ec_verifier import verify_ec_and_btr

RuleEvaluator = Callable[
    [DossierInput, ChainVerificationResult, AreaAuditResult, ECVerificationResult],
    RiskFinding,
]

SENIOR_CITIZENS_KERALA_EFFECTIVE_DATE = date(2008, 9, 24)


def _check_r01_paddy_land(
    dossier: DossierInput, *_: object
) -> RiskFinding:
    btr_nature = dossier.btr_record.land_nature_btr
    present = max(dossier.deeds, key=lambda d: d.registration_meta.execution_date)
    flags = present.statutory_flags_extracted
    if btr_nature in ("Nilam", "Nanja", "Wetland"):
        if flags.data_bank_notified_nilam and not flags.has_form5_exclusion_order:
            return RiskFinding(
                rule_id="R-01",
                title="Paddy Land & Wetland Classification (Nilam / Nanja)",
                statute="Kerala Conservation of Paddy Land and Wetland Act, 2008 (Secs. 5, 27A)",
                severity="CRITICAL_RED_FLAG",
                finding=f"BTR records land as '{btr_nature}' and property is in notified Data Bank without Form 5 exclusion.",
                curative_action="Obtain Form 5 Data Bank exclusion order followed by Form 6 / Sec. 27A RDO conversion order.",
            )
        if not (flags.has_form6_sec27a_order or flags.has_pre2017_klu_order):
            return RiskFinding(
                rule_id="R-01",
                title="Paddy Land & Wetland Classification (Nilam / Nanja)",
                statute="Kerala Conservation of Paddy Land and Wetland Act, 2008 (Sec. 27A) & KLU Order, 1967",
                severity="CRITICAL_RED_FLAG",
                finding=f"BTR records land as '{btr_nature}' without a Form 6 (Sec. 27A) or pre-30.12.2017 KLU Clause 6(2) conversion order.",
                curative_action="Produce certified RDO Form 6 / Sec. 27A conversion order and updated BTR entry as 'Purayidam'.",
            )
        return RiskFinding(
            rule_id="R-01",
            title="Paddy Land & Wetland Classification (Nilam / Nanja)",
            statute="Kerala Conservation of Paddy Land and Wetland Act, 2008 (Sec. 27A)",
            severity="PASS",
            finding=f"Land recorded as '{btr_nature}' in BTR, but valid statutory conversion order (Form 6 / KLU) is verified.",
        )
    return RiskFinding(
        rule_id="R-01",
        title="Paddy Land & Wetland Classification (Nilam / Nanja)",
        statute="Kerala Conservation of Paddy Land and Wetland Act, 2008",
        severity="PASS",
        finding=f"Categorized as '{btr_nature}' in BTR (Thandapper {dossier.btr_record.thandapper_no}). Form 5 / Form 6 conversion not required.",
    )


def _check_r02_life_estate(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        flags = deed.statutory_flags_extracted
        if flags.life_interest_reserved and not flags.life_interest_released_or_deceased:
            holder = flags.life_interest_holder_name or "Reserved Life-Estate Holder"
            return RiskFinding(
                rule_id="R-02",
                title="Reserved Life Estate / Usufructs (Ayushkala Avakasham)",
                statute="Transfer of Property Act, 1882 (Secs. 13, 19)",
                severity="CRITICAL_RED_FLAG",
                finding=f"Deed {deed.registration_meta.doc_number.value} reserves life interest in favor of {holder}.",
                curative_action="Life-estate holder must join as co-mortgagor, execute a Registered Release Deed, or Death Certificate must be produced.",
            )
    return RiskFinding(
        rule_id="R-02",
        title="Reserved Life Estate / Usufructs (Ayushkala Avakasham)",
        statute="Transfer of Property Act, 1882",
        severity="PASS",
        finding="No subsisting life-interest reservations across the title chain.",
    )


def _check_r03_senior_citizens(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        if deed.doc_class in ("GIFT_DEED", "SETTLEMENT_DEED"):
            exec_date = deed.registration_meta.execution_date
            senior_executant = any((p.age or 0) >= 60 for p in deed.executants)
            flags = deed.statutory_flags_extracted
            if (
                exec_date >= SENIOR_CITIZENS_KERALA_EFFECTIVE_DATE
                and senior_executant
                and not flags.donor_non_revocation_undertaking
            ):
                return RiskFinding(
                    rule_id="R-03",
                    title="Senior Citizens Revocation Risk",
                    statute="Maintenance and Welfare of Parents and Senior Citizens Act, 2007 (Sec. 23)",
                    severity="WARNING",
                    finding=(
                        f"{deed.doc_type_en} No. {deed.registration_meta.doc_number.value} ({exec_date}) "
                        "was executed by a senior citizen (age >= 60) post-24.09.2008."
                    ),
                    curative_action="Obtain Donor Co-Obligant / Non-Revocation Undertaking or join donor as guarantor per bank policy.",
                )
    return RiskFinding(
        rule_id="R-03",
        title="Senior Citizens Revocation Risk",
        statute="Maintenance and Welfare of Parents and Senior Citizens Act, 2007 (Sec. 23)",
        severity="PASS",
        finding="No unmitigated Section 23 Senior Citizens revocation exposure detected.",
    )


def _check_r04_minor_alienation(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        flags = deed.statutory_flags_extracted
        if flags.minor_executant_or_share and not flags.court_guardian_order_no:
            return RiskFinding(
                rule_id="R-04",
                title="Minor's Property Alienation",
                statute="Hindu Minority and Guardianship Act, 1956 (Sec. 8) / Guardians and Wards Act, 1890 (Sec. 29)",
                severity="CRITICAL_RED_FLAG",
                finding=f"Deed {deed.registration_meta.doc_number.value} alienates a minor's share without citing a District Court OP(G&W) permission order.",
                curative_action="Produce certified copy of District Court permission order or ratification deed executed by minor upon attaining majority.",
            )
    return RiskFinding(
        rule_id="R-04",
        title="Minor's Property Alienation",
        statute="Hindu Minority and Guardianship Act, 1956 (Sec. 8)",
        severity="PASS",
        finding="No unauthorized alienation of minor's property interest in the chain.",
    )


def _check_r05_klr_plantation(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        if deed.statutory_flags_extracted.klr_sec81_plantation_origin:
            return RiskFinding(
                rule_id="R-05",
                title="KLR Act Ceiling & Plantation Fragmentation",
                statute="Kerala Land Reforms Act, 1963 (Secs. 81, 82, 87)",
                severity="CRITICAL_RED_FLAG",
                finding=f"Deed {deed.registration_meta.doc_number.value} traces to Sec. 81 exempted plantation land.",
                curative_action="Verify Taluk Land Board clearance and confirm plot is not subject to ceiling reopening or conversion ban.",
            )
    return RiskFinding(
        rule_id="R-05",
        title="KLR Act Ceiling & Plantation Fragmentation",
        statute="Kerala Land Reforms Act, 1963 (Sec. 81)",
        severity="PASS",
        finding="Property is not carved out of Sec. 81 exempted plantation land.",
    )


def _check_r06_pattayam_lockin(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        flags = deed.statutory_flags_extracted
        if flags.pattayam_type == "LA_PATTAYAM" and flags.pattayam_lock_in_years > 0:
            years_elapsed = (date.today() - deed.registration_meta.execution_date).days / 365.25
            if years_elapsed < flags.pattayam_lock_in_years:
                return RiskFinding(
                    rule_id="R-06",
                    title="Pattayam Alienation Lock-In & Tree Rights",
                    statute="Kerala Land Assignment Rules, 1964 (Rule 8)",
                    severity="CRITICAL_RED_FLAG",
                    finding=(
                        f"LA Pattayam {deed.registration_meta.doc_number.value} carries a "
                        f"{flags.pattayam_lock_in_years}-year non-alienation lock-in (only {years_elapsed:.1f} years elapsed)."
                    ),
                    curative_action="Property is non-alienable during lock-in period; mortgage cannot be accepted without Government exemption.",
                )
    return RiskFinding(
        rule_id="R-06",
        title="Pattayam Alienation Lock-In & Tree Rights",
        statute="Kerala Land Assignment Rules, 1964; KLR Act Sec. 72K",
        severity="PASS",
        finding="No active LA Pattayam non-alienation lock-in period applies.",
    )


def _check_r07_hindu_joint_family(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        if deed.statutory_flags_extracted.tharavadu_pre_1976_unaccounted_member:
            return RiskFinding(
                rule_id="R-07",
                title="Kerala Hindu Joint Family Abolition Compliance",
                statute="Kerala Joint Hindu Family System (Abolition) Act, 1975 (Sec. 4)",
                severity="CRITICAL_RED_FLAG",
                finding=f"Deed {deed.registration_meta.doc_number.value} involves pre-01.12.1976 Tharavadu/joint family tenure with unaccounted co-tenants.",
                curative_action="Obtain Release Deeds (Ozhimuri) or Family Membership Certificate confirming all 01.12.1976 coparceners joined.",
            )
    return RiskFinding(
        rule_id="R-07",
        title="Kerala Hindu Joint Family Abolition Compliance",
        statute="Kerala Joint Hindu Family System (Abolition) Act, 1975",
        severity="PASS",
        finding="No unpartitioned pre-1976 Tharavadu / joint family share defects detected.",
    )


def _check_r08_muslim_succession(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        flags = deed.statutory_flags_extracted
        if flags.wasiyat_exceeds_one_third or flags.wasiyat_to_heir_without_consent:
            return RiskFinding(
                rule_id="R-08",
                title="Muslim Testamentary & Faraid Share Audit",
                statute="Muslim Personal Law (Shariat) Application Act, 1937",
                severity="CRITICAL_RED_FLAG",
                finding=f"Will/Deed {deed.registration_meta.doc_number.value} violates Shariat Wasiyat limit (>1/3rd estate or bequest to heir without consent).",
                curative_action="Obtain Registered Consent / Relinquishment Deed from all surviving Faraid legal heirs.",
            )
    return RiskFinding(
        rule_id="R-08",
        title="Muslim Testamentary & Faraid Share Audit",
        statute="Muslim Personal Law (Shariat) Application Act, 1937",
        severity="PASS",
        finding="No Shariat 1/3rd testamentary or Faraid share violations detected.",
    )


def _check_r09_christian_hindu_devolution(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        if deed.statutory_flags_extracted.missing_faraid_or_legal_heirs:
            return RiskFinding(
                rule_id="R-09",
                title="Testamentary & Intestate Legal Heir Devolution",
                statute="Indian Succession Act, 1925 (Secs. 33, 213) & Hindu Succession Act, 1956 (Sec. 6)",
                severity="CRITICAL_RED_FLAG",
                finding=f"Deed {deed.registration_meta.doc_number.value} omits one or more statutory legal heirs (widow/daughters/lineal descendants).",
                curative_action="Produce Legal Heirship Certificate and obtain registered Release/Ratification Deed from omitted heirs.",
            )
    return RiskFinding(
        rule_id="R-09",
        title="Testamentary & Intestate Legal Heir Devolution",
        statute="Indian Succession Act, 1925 & Hindu Succession Act, 1956",
        severity="PASS",
        finding="Legal heirship and testamentary devolution across the chain are consistent.",
    )


def _check_r10_survey_and_area(
    dossier: DossierInput,
    chain: ChainVerificationResult,
    area: AreaAuditResult,
    *_: object,
) -> RiskFinding:
    subdiv_issues = [i for i in chain.issues if i.issue_type == "SURVEY_SUBDIVISION_MISMATCH"]
    if subdiv_issues:
        return RiskFinding(
            rule_id="R-10",
            title="Survey Subdivision & Area Deficit Check",
            statute="Kerala Survey and Boundaries Act, 1961 (Form 8 / Form 10)",
            severity="CRITICAL_RED_FLAG",
            finding=subdiv_issues[0].detail,
            curative_action="Obtain Village Officer Old-to-ReSurvey Correlation Certificate and Survey Sketch.",
        )
    if area.status in ("RECTIFICATION_NEEDED", "FORM_10_DEMARCATION_NEEDED"):
        return RiskFinding(
            rule_id="R-10",
            title="Survey Subdivision & Area Deficit Check",
            statute="Kerala Survey and Boundaries Act, 1961 (Form 8 / Form 10)",
            severity="CRITICAL_RED_FLAG",
            finding=area.notes,
            curative_action="Execute Rectification Deed or complete Form 10 survey demarcation before mortgage.",
        )
    return RiskFinding(
        rule_id="R-10",
        title="Survey Subdivision & Area Deficit Check",
        statute="Kerala Survey and Boundaries Act, 1961",
        severity="PASS",
        finding=area.notes,
    )


def _check_r11_sarfaesi_access(dossier: DossierInput, *_: object) -> RiskFinding:
    present = max(dossier.deeds, key=lambda d: d.registration_meta.execution_date)
    access = present.property_schedule.sarfaesi_motorable_access
    if not access.has_vehicular_access:
        return RiskFinding(
            rule_id="R-11",
            title="SARFAESI Independent Motorable Access",
            statute="SARFAESI Act, 2002 (Sec. 13(4)) & Bank Credit Policy",
            severity="CRITICAL_RED_FLAG",
            finding=f"Property lacks independent vehicular access ({access.access_type}).",
            curative_action="Obtain registered Easement / Right-of-Way Deed (>= 3.0m motorable width).",
        )
    if access.pathway_width_meters is not None and access.pathway_width_meters < 3.0:
        return RiskFinding(
            rule_id="R-11",
            title="SARFAESI Independent Motorable Access",
            statute="SARFAESI Act, 2002 (Sec. 13(4))",
            severity="WARNING",
            finding=f"Access pathway width is {access.pathway_width_meters}m (< 3.0m standard bank motorable norm).",
            curative_action="Confirm local branch credit waiver or registered widening agreement.",
        )
    return RiskFinding(
        rule_id="R-11",
        title="SARFAESI Independent Motorable Access",
        statute="SARFAESI Act, 2002 (Sec. 13(4))",
        severity="PASS",
        finding=f"Independent motorable access verified ({access.access_type}). Enforceable under SARFAESI.",
    )


def _check_r12_poa_validity(dossier: DossierInput, *_: object) -> RiskFinding:
    for deed in dossier.deeds:
        flags = deed.statutory_flags_extracted
        if flags.poa_used_for_execution:
            if not flags.poa_registered:
                return RiskFinding(
                    rule_id="R-12",
                    title="Power of Attorney (POA) & Registration Validity",
                    statute="Registration Act, 1908 (Secs. 17, 32, 33)",
                    severity="CRITICAL_RED_FLAG",
                    finding=f"Deed {deed.registration_meta.doc_number.value} was executed via an unregistered POA.",
                    curative_action="Obtain registered Ratification Deed directly from the Principal.",
                )
            if not flags.foreign_poa_adjudicated_within_3m or not flags.principal_life_cert_attached:
                return RiskFinding(
                    rule_id="R-12",
                    title="Power of Attorney (POA) & Registration Validity",
                    statute="Kerala Stamp Act, 1959 & Registration Act, 1908 (Sec. 33)",
                    severity="WARNING",
                    finding=f"POA used in Deed {deed.registration_meta.doc_number.value} lacks timely Kerala Stamp Act adjudication or Principal Life Certificate.",
                    curative_action="Verify embassy attestation, RDO/Collector stamp adjudication within 3 months, and Principal's Life Certificate.",
                )
    return RiskFinding(
        rule_id="R-12",
        title="Power of Attorney (POA) & Registration Validity",
        statute="Registration Act, 1908 (Secs. 32, 33)",
        severity="PASS",
        finding="All instruments executed directly by principals or via compliant registered POA.",
    )


RULE_REGISTRY: tuple[RuleEvaluator, ...] = (
    _check_r01_paddy_land,
    _check_r02_life_estate,
    _check_r03_senior_citizens,
    _check_r04_minor_alienation,
    _check_r05_klr_plantation,
    _check_r06_pattayam_lockin,
    _check_r07_hindu_joint_family,
    _check_r08_muslim_succession,
    _check_r09_christian_hindu_devolution,
    _check_r10_survey_and_area,
    _check_r11_sarfaesi_access,
    _check_r12_poa_validity,
)


def _build_sec58f_checklist(dossier: DossierInput) -> list[str]:
    """Generate mandatory list of original documents for Sec. 58(f) Equitable Mortgage."""
    sorted_deeds = sorted(dossier.deeds, key=lambda d: d.registration_meta.execution_date)
    checklist: list[str] = []
    for idx, deed in enumerate(sorted_deeds):
        is_present = idx == len(sorted_deeds) - 1
        prefix = "ORIGINAL" if is_present else "Original / Certified Copy of"
        checklist.append(
            f"{prefix} {deed.doc_type_en} No. {deed.registration_meta.doc_number.value} "
            f"dated {deed.registration_meta.execution_date} of {deed.registration_meta.sro_name}."
        )
    btr = dossier.btr_record
    checklist.append(
        f"Original Basic Land Tax Receipt No. {btr.receipt_number} dated {btr.receipt_date} "
        f"issued by Village Officer, {btr.village} (Thandapper No. {btr.thandapper_no})."
    )
    if btr.possession_cert_no:
        checklist.append(
            f"Original Possession & Non-Attachment Certificate No. {btr.possession_cert_no} "
            f"dated {btr.possession_cert_date or 'latest'}."
        )
    ec = dossier.ec_record
    checklist.append(
        f"Original Encumbrance Certificate No. {ec.ec_number} covering {ec.period_from} to "
        f"{ec.period_to} issued by {ec.sro_name}."
    )
    if btr.building_tax_receipt_no:
        checklist.append(
            f"Original Local Body Building Tax Receipt No. {btr.building_tax_receipt_no} & Ownership Certificate."
        )
    return checklist


def run_title_audit(dossier: DossierInput) -> TitleAuditResult:
    """Run the full deterministic verification suite and 12-point rubric on a dossier."""
    sorted_deeds: list[DeedRecord] = sorted(
        dossier.deeds, key=lambda d: d.registration_meta.execution_date
    )
    present_deed = sorted_deeds[-1]

    chain_res = verify_chain_of_title(sorted_deeds)
    area_res = audit_deed_vs_btr_area(present_deed, dossier.btr_record)
    ec_res = verify_ec_and_btr(sorted_deeds, dossier.ec_record, dossier.btr_record)

    findings = [rule(dossier, chain_res, area_res, ec_res) for rule in RULE_REGISTRY]

    has_critical_rule = any(f.severity == "CRITICAL_RED_FLAG" for f in findings)
    overall_marketable = (
        chain_res.is_complete
        and ec_res.covers_minimum_13_years
        and not ec_res.active_liens
        and ec_res.owner_name_matched
        and not has_critical_rule
    )

    return TitleAuditResult(
        dossier_id=dossier.dossier_id,
        overall_marketable_title=overall_marketable,
        chain_verification=chain_res,
        area_audit=area_res,
        ec_verification=ec_res,
        risk_findings=findings,
        sec58f_deposit_checklist=_build_sec58f_checklist(dossier),
    )
