"""Unit tests for deterministic Kerala conveyancing area math."""

import pytest

from adharam_ai.schemas.deed_record import ExtentMeasurement
from adharam_ai.verifiers.area_math import (
    ares_to_cents,
    calculate_residual_extent_ares,
    cents_to_ares,
    normalize_extent_to_ares,
)


def test_ares_cents_roundtrip() -> None:
    assert ares_to_cents(4.05) == pytest.approx(10.008, abs=0.01)
    assert cents_to_ares(10.0) == pytest.approx(4.0469, abs=0.001)


def test_normalize_extent_from_acres_and_cents() -> None:
    ext = ExtentMeasurement(acres=1.0, cents=25.0)
    # 125 cents = ~50.5857 Ares
    assert normalize_extent_to_ares(ext) == pytest.approx(50.5857, abs=0.001)


def test_normalize_extent_from_historical_kole() -> None:
    ext = ExtentMeasurement(historical_unit="KOLE_6FT", historical_value=100.0)
    assert normalize_extent_to_ares(ext) == pytest.approx(3.3445, abs=0.001)


def test_calculate_residual_extent() -> None:
    assert calculate_residual_extent_ares(6.07, 4.05) == pytest.approx(2.02, abs=0.0001)
    with pytest.raises(ValueError):
        calculate_residual_extent_ares(4.0, 5.0)
