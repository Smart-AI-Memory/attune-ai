"""Fixture test suite for the canonical Fix scenario.

Filename intentionally avoids the repo's pytest discovery
patterns (``test_*.py`` / ``*_test.py``) so the main suite never
collects the seeded failure. Run explicitly:

    pytest tests/fixtures/outcome_first_fix/pricing_suite.py

Expected on the unmodified fixture: 1 failed (the target test),
all siblings passed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from pricing import price_for_units, tier_for_units  # noqa: E402


def test_boundary_order_is_bulk() -> None:
    """TARGET TEST — fails until the seeded off-by-one is fixed."""
    assert tier_for_units(100) == "bulk"


def test_small_order_is_standard() -> None:
    assert tier_for_units(1) == "standard"
    assert tier_for_units(99) == "standard"


def test_large_order_is_bulk() -> None:
    assert tier_for_units(101) == "bulk"
    assert tier_for_units(10_000) == "bulk"


def test_negative_units_rejected() -> None:
    with pytest.raises(ValueError):
        tier_for_units(-1)


def test_standard_price_is_full_rate() -> None:
    assert price_for_units(10) == 10.0


def test_large_bulk_price_is_discounted() -> None:
    assert price_for_units(200) == 160.0
