"""Canonical Pydantic v2 schemas for Kerala conveyancing documents."""

from __future__ import annotations

from datetime import date
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

RevenueRegion = Literal["MALABAR", "TRAVANCORE_COCHIN"]
PersonalLaw = Literal["HINDU", "MUSLIM", "CHRISTIAN", "OTHER"]
DeedClass = Literal[
    "SALE_DEED",
    "PARTITION_DEED",
    "SETTLEMENT_DEED",
    "GIFT_DEED",
    "RELEASE_DEED",
    "EXCHANGE_DEED",
    "WILL_TESTAMENT",
    "PATTAYAM_PURCHASE_CERT",
    "RECTIFICATION_DEED",
]


class ProvenanceField(BaseModel, Generic[T]):
    """Extracted token anchored to source Malayalam page and bounding box."""

    value: T
    raw_ml: str | None = None
    page: int = Field(default=1, ge=1)
    bbox: list[int] | None = Field(
        default=None,
        description="Normalized [ymin, xmin, ymax, xmax] coordinates (0-1000 scale).",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Party(BaseModel):
    """Executant or claimant in a registered instrument."""

    name_en: str = Field(..., min_length=1)
    name_ml: str | None = None
    relation_type: Literal["S/o", "D/o", "W/o", "H/o", "C/o", "Rep_by"] = "S/o"
    relative_name_en: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    religion_personal_law: PersonalLaw = "OTHER"
    capacity: str = "ABSOLUTE_OWNER"
    share_fraction: str = "1/1"


class PriorDeedRef(BaseModel):
    """Munnadharam (prior link deed) reference recited inside a deed."""

    doc_number: str = Field(..., pattern=r"^\d+/\d{4}$")
    sro_name: str
    deed_type: str
    schedule_allotted: str | None = None
    extent_acquired_ares: float | None = Field(default=None, ge=0.0)
    extent_acquired_cents: float | None = Field(default=None, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtentMeasurement(BaseModel):
    """Land area stated in a deed or revenue record."""

    ares: float | None = Field(default=None, ge=0.0)
    sq_meters: float | None = Field(default=None, ge=0.0)
    cents: float | None = Field(default=None, ge=0.0)
    acres: float | None = Field(default=None, ge=0.0)
    historical_unit: Literal["KOLE_6FT", "KOLE_8FT", "KUZHI_MALABAR", "PERUKKU"] | None = None
    historical_value: float | None = Field(default=None, ge=0.0)


class Boundaries(BaseModel):
    """Four-direction boundary description (കിഴക്ക്, തെക്ക്, പടിഞ്ഞാറ്, വടക്ക്)."""

    east: str = ""
    south: str = ""
    west: str = ""
    north: str = ""


class SARFAESIAccess(BaseModel):
    """Motorable access & right-of-way attributes for SARFAESI enforceability."""

    has_vehicular_access: bool = True
    pathway_width_meters: float | None = Field(default=None, ge=0.0)
    access_type: str = "DIRECT_PUBLIC_ROAD"
    easement_grant_recited: bool = True


class PropertySchedule(BaseModel):
    """Vaka Vivaram (Schedule of Property) extracted from a deed."""

    revenue_region: RevenueRegion
    district: str
    taluk: str
    village: str
    amsom_desom_or_kara: str = ""
    local_body: str = ""
    old_survey_no: str
    resurvey_block: str | None = None
    resurvey_no: str | None = None
    thandapper_no: str | None = None
    land_nature_deed: str = "Purayidam"
    land_nature_btr: Literal["Purayidam", "Nilam", "Nanja", "Wetland"] = "Purayidam"
    extent_stated: ExtentMeasurement
    building_door_no: str | None = None
    boundaries_en: Boundaries = Field(default_factory=Boundaries)
    sarfaesi_motorable_access: SARFAESIAccess = Field(default_factory=SARFAESIAccess)


class StatutoryFlagsExtracted(BaseModel):
    """Raw statutory clause indicators extracted from deed text."""

    life_interest_reserved: bool = False
    life_interest_holder_name: str | None = None
    life_interest_released_or_deceased: bool = False
    minor_executant_or_share: bool = False
    court_guardian_order_no: str | None = None
    revocable_or_conditional_clause: bool = False
    donor_non_revocation_undertaking: bool = False
    existing_encumbrance_recited: bool = False
    poa_used_for_execution: bool = False
    poa_registered: bool = True
    foreign_poa_adjudicated_within_3m: bool = True
    principal_life_cert_attached: bool = True
    pattayam_type: Literal["NONE", "KRAYA_SEC_72K", "LA_PATTAYAM"] = "NONE"
    pattayam_lock_in_years: int = Field(default=0, ge=0)
    klr_sec81_plantation_origin: bool = False
    wasiyat_exceeds_one_third: bool = False
    wasiyat_to_heir_without_consent: bool = False
    missing_faraid_or_legal_heirs: bool = False
    tharavadu_pre_1976_unaccounted_member: bool = False
    data_bank_notified_nilam: bool = False
    has_form5_exclusion_order: bool = False
    has_form6_sec27a_order: bool = False
    has_pre2017_klu_order: bool = False


class RegistrationMeta(BaseModel):
    """SRO registration identifiers."""

    doc_number: ProvenanceField[str]
    sro_name: str
    execution_date: date
    registration_date: date | None = None
    book_number: str = "Book 1"
    consideration_inr: int | None = Field(default=None, ge=0)

    @field_validator("doc_number")
    @classmethod
    def validate_doc_number_pattern(cls, field: ProvenanceField[str]) -> ProvenanceField[str]:
        """Ensure registration number follows '<number>/<YYYY>'."""
        parts = field.value.strip().split("/")
        if len(parts) != 2 or not parts[0].isdigit() or len(parts[1]) != 4 or not parts[1].isdigit():
            raise ValueError(f"doc_number must be '<num>/<YYYY>', got {field.value!r}")
        field.value = field.value.strip()
        return field


class DeedRecord(BaseModel):
    """Canonical representation of a single registered Kerala conveyancing deed."""

    doc_id: str
    doc_class: DeedClass
    doc_type_ml: str
    doc_type_en: str
    registration_meta: RegistrationMeta
    executants: list[Party] = Field(..., min_length=1)
    claimants: list[Party] = Field(..., min_length=1)
    prior_deeds_cited: list[PriorDeedRef] = Field(default_factory=list)
    statutory_flags_extracted: StatutoryFlagsExtracted = Field(
        default_factory=StatutoryFlagsExtracted
    )
    property_schedule: PropertySchedule


class ECEntry(BaseModel):
    """Single transaction row on a PEARL Encumbrance Certificate."""

    doc_number: str = Field(..., pattern=r"^\d+/\d{4}$")
    sro_name: str
    execution_date: date
    nature_of_deed: str
    executant_name: str
    claimant_name: str
    survey_no: str
    is_encumbrance_or_lien: bool = False
    released_by_doc_number: str | None = None


class ECRecord(BaseModel):
    """PEARL Encumbrance Certificate (Kudikkada Certificate)."""

    ec_number: str
    sro_name: str
    period_from: date
    period_to: date
    entries: list[ECEntry] = Field(default_factory=list)


class BTRRecord(BaseModel):
    """Basic Land Tax Receipt & Thandapper ROR summary from ReLIS."""

    receipt_number: str
    receipt_date: date
    village: str
    thandapper_no: str
    owner_name_en: str
    resurvey_block: str | None = None
    resurvey_no: str
    old_survey_no: str | None = None
    land_nature_btr: Literal["Purayidam", "Nilam", "Nanja", "Wetland"]
    extent_ares: float = Field(..., ge=0.0)
    possession_cert_no: str | None = None
    possession_cert_date: date | None = None
    building_tax_receipt_no: str | None = None


class DossierInput(BaseModel):
    """Complete multi-document loan dossier passed into the verification engine."""

    dossier_id: str
    bank_name: str
    branch_name: str
    applicant_name: str
    facility_type: str = "Housing Loan — Equitable Mortgage (Sec. 58(f) TP Act)"
    deeds: list[DeedRecord] = Field(..., min_length=1)
    ec_record: ECRecord
    btr_record: BTRRecord
