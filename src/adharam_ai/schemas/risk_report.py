"""Pydantic v2 schemas for deterministic verification outputs and LSR synthesis."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskSeverity = Literal["PASS", "WARNING", "CRITICAL_RED_FLAG"]


class AreaAuditResult(BaseModel):
    """Deterministic extent reconciliation across Deeds and BTR."""

    deed_extent_ares: float
    deed_extent_cents: float
    btr_extent_ares: float
    btr_extent_cents: float
    variance_pct: float
    status: Literal["EXACT_MATCH", "ACCEPTABLE_ROUNDING", "RECTIFICATION_NEEDED", "FORM_10_DEMARCATION_NEEDED"]
    residual_extent_ares: float | None = None
    notes: str


class ChainLinkIssue(BaseModel):
    """Missing link deed, subdivision break, or cycle detected in title DAG."""

    issue_type: Literal["MISSING_LINK_DEED", "SURVEY_SUBDIVISION_MISMATCH", "CYCLE_DETECTED", "ORPHAN_DEED"]
    source_doc_number: str
    referenced_doc_number: str | None = None
    detail: str


class ChainVerificationResult(BaseModel):
    """Output of NetworkX Chain-of-Title DAG verification."""

    is_complete: bool
    chronological_doc_numbers: list[str] = Field(default_factory=list)
    root_doc_numbers: list[str] = Field(default_factory=list)
    present_doc_number: str
    issues: list[ChainLinkIssue] = Field(default_factory=list)


class ECVerificationResult(BaseModel):
    """Output of PEARL Encumbrance Certificate cross-verification."""

    coverage_years: float
    covers_minimum_13_years: bool
    covers_full_30_years: bool
    unmatched_deeds: list[str] = Field(default_factory=list)
    active_liens: list[str] = Field(default_factory=list)
    owner_name_matched: bool
    notes: list[str] = Field(default_factory=list)


class RiskFinding(BaseModel):
    """Single rule evaluation from the 12-point Kerala Statutory Risk Rubric."""

    rule_id: str
    title: str
    statute: str
    severity: RiskSeverity
    finding: str
    curative_action: str | None = None


class TitleAuditResult(BaseModel):
    """Complete deterministic audit output used to compile the Bank LSR."""

    dossier_id: str
    overall_marketable_title: bool
    chain_verification: ChainVerificationResult
    area_audit: AreaAuditResult
    ec_verification: ECVerificationResult
    risk_findings: list[RiskFinding] = Field(default_factory=list)
    sec58f_deposit_checklist: list[str] = Field(default_factory=list)
