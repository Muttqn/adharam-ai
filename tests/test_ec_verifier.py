"""Unit tests for PEARL EC verification and phonetic name matching."""

import json
from pathlib import Path

from adharam_ai.schemas.deed_record import DossierInput
from adharam_ai.verifiers.ec_verifier import names_phonetically_match, verify_ec_and_btr


def test_phonetic_name_matching() -> None:
    assert names_phonetically_match("George Mathew", "Mathew George")
    assert names_phonetically_match("Sri. K. Raghavan Nair", "Raghavan Nair K.")
    assert not names_phonetically_match("Anwar Sadath", "Suresh Babu")


def test_ec_active_lien_detected() -> None:
    path = Path("adharam_bench/dossiers/03_thrissur_nilam_life_estate_lien.json")
    dossier = DossierInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
    res = verify_ec_and_btr(dossier.deeds, dossier.ec_record, dossier.btr_record)
    assert len(res.active_liens) == 1
    assert "889/2018" in res.active_liens[0]
