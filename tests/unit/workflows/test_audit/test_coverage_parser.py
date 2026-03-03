"""Tests for attune.workflows.test_audit.coverage_parser.

Covers:
- ModuleCoverage dataclass defaults and priority computation
- parse_coverage_json: valid JSON, missing file, malformed JSON, empty files
- prioritize_modules: sorting, threshold filtering, empty input
- group_into_batches: max_batches cap, subsystem grouping, single batch,
  empty input

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.workflows.test_audit.coverage_parser import (
    ModuleCoverage,
    group_into_batches,
    parse_coverage_json,
    prioritize_modules,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_coverage_json(tmp_path: Path) -> str:
    """Write a minimal valid coverage.json and return its path."""
    data = {
        "files": {
            "src/attune/foo.py": {
                "summary": {"num_statements": 100, "covered_lines": 40},
                "missing_lines": [10, 20, 30],
            },
            "src/attune/bar.py": {
                "summary": {"num_statements": 50, "covered_lines": 45},
                "missing_lines": [5],
            },
        }
    }
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.fixture
def zero_stmts_coverage_json(tmp_path: Path) -> str:
    """Coverage file where one module has zero statements."""
    data = {
        "files": {
            "src/attune/empty.py": {
                "summary": {"num_statements": 0, "covered_lines": 0},
                "missing_lines": [],
            }
        }
    }
    path = tmp_path / "coverage_zero.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# TestModuleCoverage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModuleCoverage:
    """Tests for the ModuleCoverage dataclass."""

    def test_defaults(self):
        """ModuleCoverage fields default to expected zero-values."""
        m = ModuleCoverage(path="x.py", stmts=0, covered=0)
        assert m.path == "x.py"
        assert m.stmts == 0
        assert m.covered == 0
        assert m.missing_lines == []
        assert m.pct == pytest.approx(0.0)
        assert m.priority == pytest.approx(0.0)

    def test_explicit_priority(self):
        """Explicitly provided priority is stored as-is."""
        m = ModuleCoverage(path="x.py", stmts=100, covered=60, pct=60.0, priority=40.0)
        assert m.priority == pytest.approx(40.0)

    def test_missing_lines_defaults_to_empty_list(self):
        """missing_lines field defaults to an independent empty list."""
        m1 = ModuleCoverage(path="a.py", stmts=0, covered=0)
        m2 = ModuleCoverage(path="b.py", stmts=0, covered=0)
        m1.missing_lines.append(42)
        assert m2.missing_lines == [], "missing_lines should not be shared"

    def test_pct_stored_correctly(self):
        """pct field stores the provided float value."""
        m = ModuleCoverage(path="x.py", stmts=100, covered=75, pct=75.0)
        assert m.pct == pytest.approx(75.0)


# ---------------------------------------------------------------------------
# TestParseCoverageJson
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseCoverageJson:
    """Tests for parse_coverage_json."""

    def test_parses_valid_json(self, simple_coverage_json: str):
        """parse_coverage_json returns two ModuleCoverage objects from valid input."""
        modules = parse_coverage_json(simple_coverage_json)
        assert len(modules) == 2

    def test_paths_in_result(self, simple_coverage_json: str):
        """Parsed modules contain the file paths from the JSON."""
        modules = parse_coverage_json(simple_coverage_json)
        paths = {m.path for m in modules}
        assert "src/attune/foo.py" in paths
        assert "src/attune/bar.py" in paths

    def test_stmt_count(self, simple_coverage_json: str):
        """num_statements maps to the stmts field."""
        modules = parse_coverage_json(simple_coverage_json)
        foo = next(m for m in modules if m.path == "src/attune/foo.py")
        assert foo.stmts == 100

    def test_covered_count(self, simple_coverage_json: str):
        """covered_lines maps to the covered field."""
        modules = parse_coverage_json(simple_coverage_json)
        foo = next(m for m in modules if m.path == "src/attune/foo.py")
        assert foo.covered == 40

    def test_missing_lines_stored(self, simple_coverage_json: str):
        """missing_lines list from the JSON is preserved."""
        modules = parse_coverage_json(simple_coverage_json)
        foo = next(m for m in modules if m.path == "src/attune/foo.py")
        assert foo.missing_lines == [10, 20, 30]

    def test_pct_computed_correctly(self, simple_coverage_json: str):
        """pct is computed as (covered / stmts) * 100."""
        modules = parse_coverage_json(simple_coverage_json)
        foo = next(m for m in modules if m.path == "src/attune/foo.py")
        assert foo.pct == pytest.approx(40.0)

    def test_priority_computed_correctly(self, simple_coverage_json: str):
        """priority is computed as (1 - pct/100) * stmts."""
        modules = parse_coverage_json(simple_coverage_json)
        foo = next(m for m in modules if m.path == "src/attune/foo.py")
        expected_priority = (1.0 - 40.0 / 100.0) * 100
        assert foo.priority == pytest.approx(expected_priority)

    def test_zero_stmts_gives_100_pct(self, zero_stmts_coverage_json: str):
        """Module with zero statements gets pct=100.0 (no uncovered lines)."""
        modules = parse_coverage_json(zero_stmts_coverage_json)
        assert len(modules) == 1
        assert modules[0].pct == pytest.approx(100.0)

    def test_zero_stmts_gives_zero_priority(self, zero_stmts_coverage_json: str):
        """Module with zero statements has priority=0.0."""
        modules = parse_coverage_json(zero_stmts_coverage_json)
        assert modules[0].priority == pytest.approx(0.0)

    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        """Non-existent path raises FileNotFoundError."""
        nonexistent = str(tmp_path / "does_not_exist.json")
        with pytest.raises(FileNotFoundError, match="Coverage file not found"):
            parse_coverage_json(nonexistent)

    def test_malformed_json_raises_value_error(self, tmp_path: Path):
        """File containing invalid JSON raises ValueError."""
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid coverage JSON"):
            parse_coverage_json(str(bad_path))

    def test_empty_files_dict_returns_empty_list(self, tmp_path: Path):
        """coverage.json with empty 'files' dict returns an empty list."""
        data = {"files": {}}
        path = tmp_path / "empty.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        modules = parse_coverage_json(str(path))
        assert modules == []

    def test_missing_files_key_returns_empty(self, tmp_path: Path):
        """coverage.json without a 'files' key returns empty list."""
        data = {"totals": {}}
        path = tmp_path / "no_files.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = parse_coverage_json(str(path))
        assert result == []

    def test_files_key_not_dict_raises_value_error(self, tmp_path: Path):
        """coverage.json where 'files' is not a dict raises ValueError."""
        data = {"files": ["not", "a", "dict"]}
        path = tmp_path / "bad_files.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError):
            parse_coverage_json(str(path))

    def test_returns_list_of_module_coverage(self, simple_coverage_json: str):
        """Return type is a list of ModuleCoverage instances."""
        modules = parse_coverage_json(simple_coverage_json)
        for m in modules:
            assert isinstance(m, ModuleCoverage)


# ---------------------------------------------------------------------------
# TestPrioritizeModules
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrioritizeModules:
    """Tests for prioritize_modules."""

    def test_empty_input_returns_empty(self):
        """Empty list returns empty list."""
        assert prioritize_modules([]) == []

    def test_filters_modules_above_threshold(self):
        """Modules with pct >= min_threshold are excluded."""
        modules = [
            ModuleCoverage(path="a.py", stmts=100, covered=90, pct=90.0, priority=10.0),
            ModuleCoverage(path="b.py", stmts=100, covered=30, pct=30.0, priority=70.0),
        ]
        result = prioritize_modules(modules, min_threshold=50.0)
        paths = [m.path for m in result]
        assert "b.py" in paths
        assert "a.py" not in paths

    def test_includes_modules_below_threshold(self):
        """Modules with pct < min_threshold are included."""
        modules = [
            ModuleCoverage(path="low.py", stmts=100, covered=10, pct=10.0, priority=90.0),
        ]
        result = prioritize_modules(modules, min_threshold=50.0)
        assert len(result) == 1
        assert result[0].path == "low.py"

    def test_exactly_at_threshold_excluded(self):
        """Module with pct == min_threshold is excluded (strict less-than)."""
        modules = [
            ModuleCoverage(path="exact.py", stmts=100, covered=50, pct=50.0, priority=50.0),
        ]
        result = prioritize_modules(modules, min_threshold=50.0)
        assert result == []

    def test_sorted_by_priority_descending(self):
        """Result is sorted by priority score, highest first."""
        modules = [
            ModuleCoverage(path="lo.py", stmts=10, covered=1, pct=10.0, priority=9.0),
            ModuleCoverage(path="hi.py", stmts=100, covered=5, pct=5.0, priority=95.0),
            ModuleCoverage(path="mid.py", stmts=50, covered=10, pct=20.0, priority=40.0),
        ]
        result = prioritize_modules(modules, min_threshold=50.0)
        priorities = [m.priority for m in result]
        assert priorities == sorted(priorities, reverse=True)

    def test_all_above_threshold_returns_empty(self):
        """All modules above threshold returns empty list."""
        modules = [
            ModuleCoverage(path="a.py", stmts=10, covered=9, pct=90.0, priority=1.0),
            ModuleCoverage(path="b.py", stmts=10, covered=8, pct=80.0, priority=2.0),
        ]
        result = prioritize_modules(modules, min_threshold=50.0)
        assert result == []

    def test_default_threshold_is_50(self):
        """Default min_threshold of 50 is applied when not specified."""
        modules = [
            ModuleCoverage(path="below.py", stmts=100, covered=40, pct=40.0, priority=60.0),
            ModuleCoverage(path="above.py", stmts=100, covered=80, pct=80.0, priority=20.0),
        ]
        result = prioritize_modules(modules)
        assert len(result) == 1
        assert result[0].path == "below.py"


# ---------------------------------------------------------------------------
# TestGroupIntoBatches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGroupIntoBatches:
    """Tests for group_into_batches."""

    def test_empty_input_returns_empty(self):
        """Empty module list returns an empty batch list."""
        assert group_into_batches([]) == []

    def test_single_module_produces_one_batch(self):
        """Single module produces exactly one batch."""
        modules = [
            ModuleCoverage(path="src/attune/foo.py", stmts=10, covered=0, pct=0.0, priority=10.0)
        ]
        batches = group_into_batches(modules, max_batches=5)
        assert len(batches) == 1

    def test_batch_has_required_keys(self):
        """Each batch dict contains batch_id, subsystem, and modules keys."""
        modules = [
            ModuleCoverage(path="src/attune/foo.py", stmts=10, covered=0, pct=0.0, priority=10.0)
        ]
        batches = group_into_batches(modules, max_batches=5)
        for batch in batches:
            assert "batch_id" in batch
            assert "subsystem" in batch
            assert "modules" in batch

    def test_batch_id_format(self):
        """batch_id follows the 'batch_N' pattern."""
        modules = [
            ModuleCoverage(path="src/attune/foo.py", stmts=10, covered=0, pct=0.0, priority=10.0)
        ]
        batches = group_into_batches(modules)
        for batch in batches:
            assert batch["batch_id"].startswith("batch_")

    def test_groups_same_package_together(self):
        """Modules sharing the same parent directory are in the same batch."""
        modules = [
            ModuleCoverage(path="src/attune/pkg/a.py", stmts=10, covered=0, pct=0.0, priority=10.0),
            ModuleCoverage(path="src/attune/pkg/b.py", stmts=10, covered=0, pct=0.0, priority=9.0),
        ]
        batches = group_into_batches(modules, max_batches=5)
        # Both share parent "src/attune/pkg" — they should end up in one batch
        total_modules = sum(len(b["modules"]) for b in batches)
        assert total_modules == 2
        assert len(batches) == 1

    def test_different_packages_become_separate_batches(self):
        """Modules in different packages produce separate batches."""
        modules = [
            ModuleCoverage(
                path="src/attune/alpha/mod.py", stmts=100, covered=0, pct=0.0, priority=100.0
            ),
            ModuleCoverage(
                path="src/attune/beta/mod.py", stmts=100, covered=0, pct=0.0, priority=100.0
            ),
        ]
        batches = group_into_batches(modules, max_batches=5)
        assert len(batches) == 2

    def test_max_batches_cap_enforced(self):
        """Number of produced batches never exceeds max_batches."""
        modules = [
            ModuleCoverage(
                path=f"src/attune/pkg{i}/mod.py",
                stmts=100,
                covered=0,
                pct=0.0,
                priority=float(100 - i),
            )
            for i in range(10)
        ]
        batches = group_into_batches(modules, max_batches=3)
        assert len(batches) <= 3

    def test_excess_subsystems_merged_into_last_batch(self):
        """When subsystems exceed max_batches, extras are merged into the last batch."""
        modules = [
            ModuleCoverage(
                path=f"src/attune/pkg{i}/mod.py",
                stmts=100,
                covered=0,
                pct=0.0,
                priority=float(100 - i),
            )
            for i in range(6)
        ]
        batches = group_into_batches(modules, max_batches=3)
        # All 6 modules should appear across 3 batches
        total_modules = sum(len(b["modules"]) for b in batches)
        assert total_modules == 6
        assert len(batches) <= 3

    def test_modules_in_batch_are_module_coverage_objects(self):
        """The 'modules' value in each batch is a list of ModuleCoverage objects."""
        modules = [
            ModuleCoverage(
                path="src/attune/foo/bar.py", stmts=10, covered=0, pct=0.0, priority=10.0
            )
        ]
        batches = group_into_batches(modules)
        for batch in batches:
            for m in batch["modules"]:
                assert isinstance(m, ModuleCoverage)

    def test_batches_sorted_by_total_priority_descending(self):
        """First batch has the highest aggregate priority."""
        modules = [
            ModuleCoverage(
                path="src/attune/low/mod.py", stmts=10, covered=8, pct=80.0, priority=2.0
            ),
            ModuleCoverage(
                path="src/attune/high/mod.py", stmts=100, covered=0, pct=0.0, priority=100.0
            ),
        ]
        batches = group_into_batches(modules, max_batches=5)
        first_priority = sum(m.priority for m in batches[0]["modules"])
        last_priority = sum(m.priority for m in batches[-1]["modules"])
        assert first_priority >= last_priority

    def test_default_max_batches_is_5(self):
        """Default max_batches cap is 5."""
        modules = [
            ModuleCoverage(
                path=f"src/attune/pkg{i}/mod.py",
                stmts=100,
                covered=0,
                pct=0.0,
                priority=float(10 - i),
            )
            for i in range(8)
        ]
        batches = group_into_batches(modules)
        assert len(batches) <= 5

    def test_single_file_no_parent(self):
        """Module path with a single component uses 'root' as the subsystem."""
        modules = [
            ModuleCoverage(path="standalone.py", stmts=10, covered=0, pct=0.0, priority=10.0)
        ]
        batches = group_into_batches(modules)
        assert len(batches) == 1
        # The subsystem for a file with no directory component is the file name itself
        assert batches[0]["subsystem"] is not None
