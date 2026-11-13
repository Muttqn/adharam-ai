"""PEARL Encumbrance Certificate (EC) cross-verifier & Indic phonetic name matcher."""

from __future__ import annotations

import re

from adharam_ai.schemas.deed_record import BTRRecord, DeedRecord, ECRecord
from adharam_ai.schemas.risk_report import ECVerificationResult

HONORIFICS_PATTERN = re.compile(
    r"\b(sri|smt|mr|mrs|ms|dr|adv|late|shaik|haji)\b\.?", re.IGNORECASE
)


def normalize_person_name_tokens(name: str) -> set[str]:
    """Normalize an English/transliterated Kerala name into order-independent tokens.

    Handles 'K. Raghavan Nair' vs 'Raghavan Nair K.' vs 'Sri. K. Raghavan Nair'.
    """
    cleaned = HONORIFICS_PATTERN.sub(" ", name)
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", cleaned).lower()
    tokens = {tok for tok in cleaned.split() if tok}
    return tokens


def names_phonetically_match(name_a: str, name_b: str) -> bool:
    """Return True if two name strings refer to the same person across initial orderings."""
    tokens_a = normalize_person_name_tokens(name_a)
    tokens_b = normalize_person_name_tokens(name_b)
    if not tokens_a or not tokens_b:
        return False
    if tokens_a == tokens_b:
        return True

    # Strip single-letter initials and compare core given/family name tokens
    core_a = {t for t in tokens_a if len(t) > 1}
    core_b = {t for t in tokens_b if len(t) > 1}
    return bool(core_a and core_b and (core_a.issubset(core_b) or core_b.issubset(core_a)))


def verify_ec_and_btr(
    deeds: list[DeedRecord],
    ec_record: ECRecord,
    btr_record: BTRRecord,
) -> ECVerificationResult:
    """Verify EC temporal coverage, deed presence, active liens, and BTR owner match."""
    days = (ec_record.period_to - ec_record.period_from).days
    coverage_years = round(days / 365.25, 1)
    covers_13 = coverage_years >= 13.0
    covers_30 = coverage_years >= 30.0

    ec_doc_numbers = {entry.doc_number.strip() for entry in ec_record.entries}

    unmatched_deeds: list[str] = []
    for deed in deeds:
        doc_num = deed.registration_meta.doc_number.value
        exec_date = deed.registration_meta.execution_date
        if ec_record.period_from <= exec_date <= ec_record.period_to and doc_num not in ec_doc_numbers:
            unmatched_deeds.append(doc_num)

    active_liens: list[str] = []
    for entry in ec_record.entries:
        if entry.is_encumbrance_or_lien:
            release_doc = entry.released_by_doc_number
            if not release_doc or release_doc not in ec_doc_numbers:
                active_liens.append(
                    f"{entry.nature_of_deed} (Doc No. {entry.doc_number} dated {entry.execution_date})"
                )

    sorted_deeds = sorted(deeds, key=lambda d: d.registration_meta.execution_date)
    present_deed = sorted_deeds[-1]
    owner_matched = any(
        names_phonetically_match(claimant.name_en, btr_record.owner_name_en)
        for claimant in present_deed.claimants
    )

    notes: list[str] = []
    if not covers_13:
        notes.append(
            f"EC coverage is only {coverage_years} years; minimum 13-year EC required."
        )
    elif not covers_30:
        notes.append(
            f"EC covers {coverage_years} years (satisfies 13-year minimum; 30-year EC recommended for full trace)."
        )
    else:
        notes.append(
            f"EC No. {ec_record.ec_number} covers {coverage_years} years ({ec_record.period_from} to {ec_record.period_to})."
        )

    if unmatched_deeds:
        notes.append(
            f"Deeds executed within EC window missing from EC rows: {', '.join(unmatched_deeds)}."
        )
    if active_liens:
        notes.append(f"Active undischarged liens/attachments found: {'; '.join(active_liens)}.")
    if not owner_matched:
        notes.append(
            f"BTR owner '{btr_record.owner_name_en}' does not match present deed claimant(s)."
        )

    return ECVerificationResult(
        coverage_years=coverage_years,
        covers_minimum_13_years=covers_13,
        covers_full_30_years=covers_30,
        unmatched_deeds=unmatched_deeds,
        active_liens=active_liens,
        owner_name_matched=owner_matched,
        notes=notes,
    )
