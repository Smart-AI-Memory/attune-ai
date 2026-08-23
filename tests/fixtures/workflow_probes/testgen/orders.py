"""Fixture module for the test-gen probe.

No planted defect — this is a small, correct, branchy module with
NO tests. The test-gen probe generates tests for it, then EXECUTES
the emitted tests: they must import, run, and pass against this
code. That round trip (not just "exit 0") is the receipt.

Not collected by pytest (filename avoids test_* / *_test patterns).
"""

from __future__ import annotations


def order_total(prices: list[float], discount: float = 0.0) -> float:
    """Sum ``prices`` and apply a fractional ``discount`` (0.0-1.0).

    Raises ValueError when ``discount`` is outside [0, 1].
    """
    if discount < 0.0 or discount > 1.0:
        raise ValueError("discount must be between 0 and 1")
    subtotal = sum(prices)
    return subtotal * (1.0 - discount)


def classify_order(total: float) -> str:
    """Bucket an order total into a shipping tier."""
    if total <= 0:
        return "empty"
    if total < 50:
        return "standard"
    if total < 200:
        return "priority"
    return "free-shipping"
