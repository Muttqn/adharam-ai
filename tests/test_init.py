import pytest

from adharam_ai import __version__, normalize_revenue_region


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_normalize_revenue_region_valid() -> None:
    assert normalize_revenue_region("malabar") == "MALABAR"
    assert normalize_revenue_region("  Travancore-Cochin ") == "TRAVANCORE_COCHIN"


def test_normalize_revenue_region_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_revenue_region("KARNATAKA")