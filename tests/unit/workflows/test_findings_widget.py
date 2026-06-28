"""Tests for the shared findings-widget primitives (spec FR-1)."""

from __future__ import annotations

import pytest

from attune.workflows import findings_widget as fw

pytestmark = pytest.mark.unit


class TestEsc:
    def test_escapes_html(self):
        assert fw.esc("<script>") == "&lt;script&gt;"
        assert fw.esc("a&b") == "a&amp;b"

    def test_none_is_empty(self):
        assert fw.esc(None) == ""

    def test_non_str_coerced(self):
        assert fw.esc(42) == "42"


class TestSeverity:
    def test_severity_of_defaults_info(self):
        assert fw.severity_of({}) == "info"
        assert fw.severity_of({"severity": "HIGH"}) == "high"

    def test_rank_orders_critical_first(self):
        assert fw.severity_rank({"severity": "critical"}) < fw.severity_rank({"severity": "low"})

    def test_unknown_severity_ranks_last(self):
        assert fw.severity_rank({"severity": "bogus"}) == len(fw.SEV_ORDER)

    def test_colour_for_known_and_unknown(self):
        assert fw.colour_for({"severity": "critical"}) == fw.SEV_COLOUR["critical"]
        assert fw.colour_for({"severity": "bogus"}) == fw.SEV_COLOUR["info"]


class TestLocation:
    def test_file_and_line(self):
        assert fw.location({"file": "src/x.py", "line": 10}) == "src/x.py:10"

    def test_file_without_line(self):
        assert fw.location({"file": "src/x.py", "line": None}) == "src/x.py"

    def test_missing_file_is_dash(self):
        assert fw.location({"file": None, "line": 5}) == "—"

    def test_location_escapes(self):
        assert fw.location({"file": "a<b>", "line": 1}) == "a&lt;b&gt;:1"


class TestPaletteShape:
    def test_order_matches_colour_keys(self):
        assert set(fw.SEV_ORDER) == set(fw.SEV_COLOUR)
        assert fw.SEV_ORDER[0] == "critical"
