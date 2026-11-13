"""AdharamAI: Neuro-Symbolic Kerala Property Conveyancing & Bank LSR Engine."""

__version__ = "0.1.0"

VALID_REVENUE_REGIONS: tuple[str, ...] = ("MALABAR", "TRAVANCORE_COCHIN")


def normalize_revenue_region(region: str) -> str:
    """Normalize and validate a Kerala revenue region name.

    Args:
        region: Raw region string (e.g., "malabar", "  Travancore-Cochin ").

    Returns:
        Normalized uppercase region string ("MALABAR" or "TRAVANCORE_COCHIN").

    Raises:
        ValueError: If the normalized region is not in VALID_REVENUE_REGIONS.
    """
    cleaned = region.strip().upper().replace("-", "_").replace(" ", "_")
    if cleaned not in VALID_REVENUE_REGIONS:
        raise ValueError(
            f"Unsupported Kerala revenue region: {region!r}. "
            f"Expected one of {VALID_REVENUE_REGIONS}."
        )
    return cleaned
