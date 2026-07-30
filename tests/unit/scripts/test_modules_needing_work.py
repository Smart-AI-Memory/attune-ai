"""Tests for scripts/modules_needing_work.py (pure logic, no network).

The fetch is a thin urllib wrapper; everything else is pure and
tested here against a fixture payload shaped like Codecov's
``/report/`` response.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "modules_needing_work.py"
_spec = importlib.util.spec_from_file_location("modules_needing_work", _SCRIPT)
mnw = importlib.util.module_from_spec(_spec)
sys.modules["modules_needing_work"] = mnw
_spec.loader.exec_module(mnw)


PAYLOAD = {
    "totals": {"coverage": 93.82, "files": 4},
    "files": [
        {
            "name": "src/attune/ops/collab_data.py",
            "totals": {"coverage": 77.0, "lines": 139, "misses": 26},
            "line_coverage": [[80, 1], [81, 1], [83, 1], [90, 0], [104, 1]],
        },
        {
            "name": "src/attune/diagnosis/triage.py",
            "totals": {"coverage": 68.3, "lines": 104, "misses": 30},
            "line_coverage": [[55, 1], [59, 1], [60, 1], [61, 1]],
        },
        {
            "name": "src/attune/covered.py",
            "totals": {"coverage": 99.0, "lines": 10, "misses": 0},
            "line_coverage": [],
        },
        {
            "name": "tests/unit/not_production.py",
            "totals": {"coverage": 10.0, "lines": 5, "misses": 4},
            "line_coverage": [],
        },
        {
            "name": "src/attune/no_data.py",
            "totals": {"coverage": None, "lines": 0, "misses": 0},
            "line_coverage": [],
        },
    ],
}

PYPROJECT = """
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/site-packages/*",
    "*/*_example.py",
    "*/models/auth_cli.py",  # Interactive auth setup
    "*/workflows/progress_server.py",
]
branch = true
"""


class TestCompressRanges:
    def test_mixed_runs_and_singletons(self) -> None:
        assert mnw.compress_ranges([1, 2, 3, 7, 10, 11]) == "1-3, 7, 10-11"

    def test_empty(self) -> None:
        assert mnw.compress_ranges([]) == ""

    def test_single(self) -> None:
        assert mnw.compress_ranges([42]) == "42"


class TestExtractGaps:
    def test_filters_sorts_and_compresses(self) -> None:
        gaps = mnw.extract_gaps(PAYLOAD, bar=85.0)
        # Non-production and above-bar and no-data files excluded;
        # ascending coverage order.
        assert [g.path for g in gaps] == [
            "src/attune/diagnosis/triage.py",
            "src/attune/ops/collab_data.py",
        ]
        assert gaps[0].miss_ranges == "55, 59-61"
        assert gaps[1].miss_ranges == "80-81, 83, 104"
        assert gaps[1].cluster == "ops"

    def test_bar_is_exclusive_of_equal(self) -> None:
        gaps = mnw.extract_gaps(PAYLOAD, bar=68.3)
        assert gaps == []


class TestExtractOmitEntries:
    def test_meta_globs_skipped_comments_carried(self) -> None:
        entries = mnw.extract_omit_entries(PYPROJECT)
        assert entries == [
            "`*/models/auth_cli.py` — Interactive auth setup",
            "`*/workflows/progress_server.py`",
        ]

    def test_missing_omit_block(self) -> None:
        assert mnw.extract_omit_entries("[tool.other]\nx = 1\n") == []


class TestClusterSummary:
    def test_sorted_by_miss_volume(self) -> None:
        gaps = mnw.extract_gaps(PAYLOAD, bar=85.0)
        assert mnw.cluster_summary(gaps) == [
            ("diagnosis", 1, 30),
            ("ops", 1, 26),
        ]


class TestRendering:
    def _report(self) -> object:
        return mnw.build_report(PAYLOAD, PYPROJECT, bar=85.0)

    def test_report_contains_tiers_and_tables(self) -> None:
        text = mnw.render_report(self._report(), bar=85.0)
        assert "# Modules needing work" in text
        assert "project total 93.82%" in text
        assert "## Tier 1 — measured below the 85% bar (2 modules)" in text
        assert "| 68.30% | 104 | 30 | `src/attune/diagnosis/triage.py` |" in text
        assert "`*/models/auth_cli.py` — Interactive auth setup" in text
        assert "## How lanes run (parallel delegation)" in text

    def test_report_empty_state(self) -> None:
        report = mnw.build_report({"totals": {}, "files": []}, PYPROJECT, bar=85.0)
        text = mnw.render_report(report, bar=85.0)
        assert "Nothing below 85%" in text

    def test_brief_is_self_contained(self) -> None:
        gap = mnw.extract_gaps(PAYLOAD, bar=85.0)[0]
        brief = mnw.render_brief(gap)
        assert "raise `src/attune/diagnosis/triage.py` from 68.3% to >=85%" in brief
        assert "codex/coverage-diagnosis-triage" in brief
        assert "Missed line ranges (Codecov main): 55, 59-61" in brief
        assert "TESTS-ONLY" in brief
        assert "suite:" in brief and "metric:" in brief
        assert "NOT the suite receipt" in brief


class TestValidatedOutPath:
    def test_relative_path_lands_in_repo(self) -> None:
        resolved = mnw._validated_out_path(Path("docs/reports/x.md"))
        assert resolved.is_relative_to(mnw.REPO_ROOT)

    def test_escape_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside the repo"):
            mnw._validated_out_path(Path("/etc/passwd"))
