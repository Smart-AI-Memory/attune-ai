"""Tests for ``scripts/ci_spend_gate.py`` — DEC-8 CI spend enforcement.

Loaded via importlib.util because ``scripts/`` is not a Python package —
matches the repo convention used in ``tests/unit/github_scripts/
test_analyze_security_results.py``.

Mock-only per testing-conventions.md: never hits the real Anthropic
admin cost-report API. ``attune.ops.anthropic_cost.fetch_summary`` is
patched at its import site inside the loaded module (``ci_spend_gate``
does ``from attune.ops.anthropic_cost import fetch_summary``, so the
patch target is the module's own bound name, not the origin module —
patching the origin would miss this bound reference).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.ops.anthropic_cost import CostFetchError, CostSummary
from attune.ops.data import MONTHLY_API_CEILING_USD

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci_spend_gate.py"


@pytest.fixture
def gate():
    spec = importlib.util.spec_from_file_location("_ci_spend_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ci_spend_gate"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_ci_spend_gate", None)


def _summary(month_to_date_usd: float) -> CostSummary:
    return CostSummary(
        today_usd=0.0,
        seven_day_usd=0.0,
        month_to_date_usd=month_to_date_usd,
        thirty_day_usd=0.0,
        by_day=[],
        by_model=[],
        by_cost_type=[],
        fetched_at=datetime.now(timezone.utc),
        source="live",
    )


class TestCheckBudget:
    """check_budget's three outcomes: under, over, unverifiable."""

    def test_under_ceiling_passes(self, gate) -> None:
        with patch.object(gate, "fetch_summary", return_value=(_summary(100.0), None)):
            assert gate.check_budget(ceiling=350.0) == 0

    def test_exactly_at_ceiling_blocks(self, gate) -> None:
        # The alarm uses >= for its ceiling trigger; the gate matches.
        with patch.object(gate, "fetch_summary", return_value=(_summary(350.0), None)):
            assert gate.check_budget(ceiling=350.0) == 1

    def test_over_ceiling_blocks(self, gate) -> None:
        with patch.object(gate, "fetch_summary", return_value=(_summary(1700.0), None)):
            assert gate.check_budget(ceiling=350.0) == 1

    def test_no_admin_key_fails_open(self, gate) -> None:
        # Missing ANTHROPIC_ADMIN_API_KEY must never block a keyed
        # workflow before the secret exists — see the module docstring.
        error = CostFetchError(kind="no_key", message="No Anthropic admin key configured.")
        with patch.object(gate, "fetch_summary", return_value=(None, error)):
            assert gate.check_budget(ceiling=350.0) == 0

    def test_transient_fetch_error_fails_open(self, gate) -> None:
        error = CostFetchError(kind="rate_limited", message="429 from Anthropic")
        with patch.object(gate, "fetch_summary", return_value=(None, error)):
            assert gate.check_budget(ceiling=350.0) == 0

    def test_custom_ceiling_respected(self, gate) -> None:
        with patch.object(gate, "fetch_summary", return_value=(_summary(50.0), None)):
            assert gate.check_budget(ceiling=20.0) == 1
            assert gate.check_budget(ceiling=100.0) == 0


class TestMainCLI:
    """argparse wiring: default ceiling, --ceiling override, exit code passthrough."""

    def test_main_uses_default_ceiling(self, gate) -> None:
        with patch.object(
            gate,
            "fetch_summary",
            return_value=(_summary(MONTHLY_API_CEILING_USD + 1), None),
        ) as mock_fetch:
            assert gate.main([]) == 1
        mock_fetch.assert_called_once_with(refresh=True)

    def test_main_ceiling_override(self, gate) -> None:
        with patch.object(gate, "fetch_summary", return_value=(_summary(5.0), None)):
            assert gate.main(["--ceiling", "1"]) == 1
            assert gate.main(["--ceiling", "10"]) == 0
