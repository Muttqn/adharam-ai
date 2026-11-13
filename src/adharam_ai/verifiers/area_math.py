"""Deterministic conveyancing area math and Kerala unit conversions."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from adharam_ai.schemas.deed_record import BTRRecord, DeedRecord, ExtentMeasurement
from adharam_ai.schemas.risk_report import AreaAuditResult

SQ_METERS_PER_ARE = Decimal(100)
SQ_METERS_PER_ACRE = Decimal("4046.8564224")
CENTS_PER_ARE = Decimal("2.471053814671653")
SQ_METERS_PER_CENT = Decimal("40.468564224")

HISTORICAL_TO_SQ_METERS: dict[str, Decimal] = {
    "KOLE_6FT": Decimal("3.344509"),
    "KOLE_8FT": Decimal("5.945794"),
    "KUZHI_MALABAR": Decimal("13.378038"),
    "PERUKKU": Decimal("4.046856"),
}

ACCEPTABLE_ROUNDING_PCT = 2.5
RECTIFICATION_DEED_PCT = 5.0


def _to_decimal(value: float | Decimal) -> Decimal:
    return Decimal(str(value))


def ares_to_cents(ares: float) -> float:
    """Convert Ares to Cents using exact metric-to-imperial conveyancing constant."""
    result = (_to_decimal(ares) * CENTS_PER_ARE).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    return float(result)


def cents_to_ares(cents: float) -> float:
    """Convert Cents to Ares rounded to 4 decimal places."""
    result = (_to_decimal(cents) / CENTS_PER_ARE).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )
    return float(result)


def normalize_extent_to_ares(extent: ExtentMeasurement) -> float:
    """Normalize any ExtentMeasurement (Ares, Sq.m, Cents, Acres, or Kole) into Ares."""
    if extent.ares is not None:
        return round(extent.ares, 4)
    if extent.sq_meters is not None:
        return float((_to_decimal(extent.sq_meters) / SQ_METERS_PER_ARE).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ))
    total_cents = Decimal(0)
    if extent.acres is not None:
        total_cents += _to_decimal(extent.acres) * Decimal(100)
    if extent.cents is not None:
        total_cents += _to_decimal(extent.cents)
    if total_cents > 0:
        ares_val = (total_cents * SQ_METERS_PER_CENT) / SQ_METERS_PER_ARE
        return float(ares_val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    if extent.historical_unit and extent.historical_value is not None:
        factor = HISTORICAL_TO_SQ_METERS[extent.historical_unit]
        ares_val = (_to_decimal(extent.historical_value) * factor) / SQ_METERS_PER_ARE
        return float(ares_val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    raise ValueError("ExtentMeasurement contains no convertible area fields.")


def calculate_residual_extent_ares(
    acquired_ares: float, conveyed_ares: float
) -> float:
    """Compute remaining extent after a partial alienation from a parent schedule."""
    residual = _to_decimal(acquired_ares) - _to_decimal(conveyed_ares)
    if residual < Decimal("-0.02"):
        raise ValueError(
            f"Conveyed extent ({conveyed_ares} Ares) exceeds acquired extent ({acquired_ares} Ares)."
        )
    return float(max(residual, Decimal(0)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def audit_deed_vs_btr_area(
    present_deed: DeedRecord,
    btr_record: BTRRecord,
) -> AreaAuditResult:
    """Reconcile Present Title Deed extent against ReLIS Basic Tax Receipt extent."""
    deed_ares = normalize_extent_to_ares(present_deed.property_schedule.extent_stated)
    deed_cents = ares_to_cents(deed_ares)
    btr_ares = round(btr_record.extent_ares, 4)
    btr_cents = ares_to_cents(btr_ares)

    if deed_ares == 0:
        raise ValueError("Present deed extent cannot be zero.")

    variance_pct = round(abs(deed_ares - btr_ares) / deed_ares * 100.0, 2)

    residual_ares: float | None = None
    if present_deed.prior_deeds_cited:
        prior_acquired = [
            p.extent_acquired_ares
            for p in present_deed.prior_deeds_cited
            if p.extent_acquired_ares is not None
        ]
        if prior_acquired:
            total_acquired = sum(prior_acquired)
            if total_acquired >= deed_ares:
                residual_ares = calculate_residual_extent_ares(total_acquired, deed_ares)

    if variance_pct == 0.0:
        status = "EXACT_MATCH"
        notes = f"Deed extent ({deed_ares} Ares / {deed_cents} Cents) exactly matches BTR."
    elif variance_pct <= ACCEPTABLE_ROUNDING_PCT:
        status = "ACCEPTABLE_ROUNDING"
        notes = (
            f"Minor variance of {variance_pct}% between Deed ({deed_ares} Ares) and "
            f"BTR ({btr_ares} Ares) within {ACCEPTABLE_ROUNDING_PCT}% Village Office tolerance."
        )
    elif variance_pct <= RECTIFICATION_DEED_PCT:
        status = "RECTIFICATION_NEEDED"
        notes = (
            f"Variance of {variance_pct}% exceeds {ACCEPTABLE_ROUNDING_PCT}% tolerance. "
            "Registered Rectification Deed (Thettu Thiruthal Adharam) recommended."
        )
    else:
        status = "FORM_10_DEMARCATION_NEEDED"
        notes = (
            f"Material discrepancy of {variance_pct}% between Deed ({deed_ares} Ares) and "
            f"BTR ({btr_ares} Ares). Form 10 Survey Demarcation under Kerala Survey & Boundaries Rules required."
        )

    return AreaAuditResult(
        deed_extent_ares=deed_ares,
        deed_extent_cents=deed_cents,
        btr_extent_ares=btr_ares,
        btr_extent_cents=btr_cents,
        variance_pct=variance_pct,
        status=status,
        residual_extent_ares=residual_ares,
        notes=notes,
    )
