"""Tiny pricing module carrying the SEEDED bug for the canonical
outcome-first Fix scenario (docs/specs/outcome-first-fix/).

The bug: ``tier_for_units`` uses ``>`` where the documented
contract requires ``>=`` — exactly 100 units must already be
"bulk". Deliberate; do not fix in place (Phase 2 fixes a copy).
"""

from __future__ import annotations

BULK_THRESHOLD = 100
BULK_RATE = 0.80
STANDARD_RATE = 1.00


def tier_for_units(units: int) -> str:
    """Return the pricing tier for an order size.

    Contract: orders of BULK_THRESHOLD units OR MORE are "bulk";
    everything below is "standard". Negative counts are invalid.
    """
    if units < 0:
        raise ValueError(f"units must be non-negative, got {units}")
    # SEEDED BUG: should be `>=` — the boundary order (exactly 100
    # units) is misclassified as "standard".
    if units > BULK_THRESHOLD:
        return "bulk"
    return "standard"


def price_for_units(units: int) -> float:
    """Total price: bulk orders get the discounted per-unit rate."""
    rate = BULK_RATE if tier_for_units(units) == "bulk" else STANDARD_RATE
    return round(units * rate, 2)
