"""Unit tests for Chain-of-Title DAG and survey subdivision matching."""

import json
from pathlib import Path

from adharam_ai.schemas.deed_record import DossierInput
from adharam_ai.verifiers.chain_verifier import (
    is_survey_subdivision_compatible,
    normalize_survey_token,
    verify_chain_of_title,
)


def test_survey_subdivision_matching() -> None:
    assert normalize_survey_token("Re-Sy. No. 42/3 A 1") == "42/3A1"
    assert is_survey_subdivision_compatible("42/3", "42/3A1")
    assert is_survey_subdivision_compatible("118/4", "118/4")
    assert not is_survey_subdivision_compatible("42/3", "43/1")


def test_complete_malabar_chain() -> None:
    path = Path("adharam_bench/dossiers/01_kozhikode_clean_malabar.json")
    dossier = DossierInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
    result = verify_chain_of_title(dossier.deeds)
    assert result.is_complete
    assert result.chronological_doc_numbers == ["614/1994", "1108/2004", "2145/2019"]
    assert result.root_doc_numbers == ["614/1994"]
    assert result.present_doc_number == "2145/2019"


def test_missing_munnadharam_flagged() -> None:
    path = Path("adharam_bench/dossiers/04_malappuram_wasiyat_missing_link_area.json")
    dossier = DossierInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
    result = verify_chain_of_title(dossier.deeds)
    assert not result.is_complete
    assert any(i.issue_type == "MISSING_LINK_DEED" for i in result.issues)
