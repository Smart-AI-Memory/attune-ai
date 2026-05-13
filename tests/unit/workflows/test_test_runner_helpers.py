"""Tests for attune.workflows.test_runner_helpers — private helpers.

Pure functions for the most part: pytest output parsing,
coverage XML analysis, test-file discovery. Only the telemetry
helpers (`_get_previous_coverage`, `_log_file_test`) interact
with state and are mocked.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

from attune.models import FileTestRecord
from attune.workflows.test_runner_helpers import (
    _analyze_coverage_files,
    _find_test_file,
    _get_previous_coverage,
    _log_file_test,
    _parse_pytest_failures,
    _parse_pytest_output,
)

# ---------------------------------------------------------------------------
# _parse_pytest_output() — pytest summary line parsing
# ---------------------------------------------------------------------------


class TestParsePytestOutput:
    def test_all_passing(self):
        out = "============= 5 passed in 0.42s =============="
        total, passed, failed, skipped, errors = _parse_pytest_output(out)
        assert total == 5
        assert passed == 5
        assert failed == 0
        assert skipped == 0
        assert errors == 0

    def test_mixed_results(self):
        out = "============= 3 failed, 2 passed, 1 skipped in 1.23s ============"
        total, passed, failed, skipped, errors = _parse_pytest_output(out)
        assert passed == 2
        assert failed == 3
        assert skipped == 1
        assert errors == 0
        assert total == 6

    def test_error_count(self):
        out = "============= 1 failed, 2 errors in 0.5s ============"
        total, passed, failed, skipped, errors = _parse_pytest_output(out)
        assert errors == 2

    def test_no_summary_returns_zeros(self):
        total, passed, failed, skipped, errors = _parse_pytest_output("")
        assert total == passed == failed == skipped == errors == 0

    def test_unparseable_returns_zeros(self):
        total, _, _, _, _ = _parse_pytest_output("garbage with no pytest line")
        assert total == 0


# ---------------------------------------------------------------------------
# _parse_pytest_failures() — extracting failure entries
# ---------------------------------------------------------------------------


class TestParsePytestFailures:
    def test_extracts_failed_lines(self):
        out = (
            "test session starts\n"
            "FAILED tests/unit/foo.py::test_one - assertion error\n"
            "FAILED tests/unit/bar.py::test_two - runtime error\n"
            "===== 2 failed in 0.5s ====="
        )
        result = _parse_pytest_failures(out)
        assert len(result) == 2
        assert result[0]["file"] == "tests/unit/foo.py"
        assert result[0]["name"] == "test_one"
        assert result[0]["error"] == "Test failed"

    def test_no_failed_lines_returns_empty(self):
        result = _parse_pytest_failures("all good, 5 passed")
        assert result == []

    def test_caps_at_10_failures(self):
        out = "\n".join(f"FAILED tests/f{i}.py::test_{i} - oops" for i in range(20))
        result = _parse_pytest_failures(out)
        assert len(result) == 10

    def test_handles_missing_test_part(self):
        """A FAILED line with no '::' is silently skipped."""
        out = "FAILED tests/sometest.py-malformed"  # No `::` separator
        result = _parse_pytest_failures(out)
        assert result == []


# ---------------------------------------------------------------------------
# _get_previous_coverage() — telemetry-store lookup with graceful fallback
# ---------------------------------------------------------------------------


class TestGetPreviousCoverage:
    @patch("attune.workflows.test_runner_helpers.get_telemetry_store")
    def test_two_or_more_records_returns_second_to_last(self, mock_store):
        rec1 = MagicMock(overall_percentage=70.0)
        rec2 = MagicMock(overall_percentage=80.0)
        rec3 = MagicMock(overall_percentage=85.0)
        mock_store.return_value.get_coverage_history.return_value = [rec1, rec2, rec3]

        # Second-to-last is rec2.
        assert _get_previous_coverage() == 80.0

    @patch("attune.workflows.test_runner_helpers.get_telemetry_store")
    def test_single_record_returns_it(self, mock_store):
        rec = MagicMock(overall_percentage=60.0)
        mock_store.return_value.get_coverage_history.return_value = [rec]
        assert _get_previous_coverage() == 60.0

    @patch("attune.workflows.test_runner_helpers.get_telemetry_store")
    def test_empty_history_returns_none(self, mock_store):
        mock_store.return_value.get_coverage_history.return_value = []
        assert _get_previous_coverage() is None

    @patch("attune.workflows.test_runner_helpers.get_telemetry_store")
    def test_store_exception_returns_none(self, mock_store):
        mock_store.side_effect = RuntimeError("store offline")
        assert _get_previous_coverage() is None


# ---------------------------------------------------------------------------
# _analyze_coverage_files() — file-level coverage classification
# ---------------------------------------------------------------------------


def _build_coverage_root(file_specs: list[tuple[str, float]]) -> ET.Element:
    """Build a minimal coverage XML root with the given (filename, line_rate) tuples."""
    root = ET.Element("coverage")
    pkg = ET.SubElement(root, "packages")
    p = ET.SubElement(pkg, "package")
    classes = ET.SubElement(p, "classes")
    for filename, line_rate in file_specs:
        c = ET.SubElement(classes, "class", filename=filename, **{"line-rate": str(line_rate)})
        ET.SubElement(c, "methods")
        ET.SubElement(c, "lines")
    return root


class TestAnalyzeCoverageFiles:
    def test_well_covered_threshold(self):
        root = _build_coverage_root([("a.py", 0.85)])
        result = _analyze_coverage_files(root)
        assert result["total"] == 1
        assert result["well_covered"] == 1
        assert result["critical"] == 0
        assert result["untested"] == []
        assert result["gaps"] == []

    def test_critical_threshold(self):
        root = _build_coverage_root([("low.py", 0.30)])
        result = _analyze_coverage_files(root)
        assert result["critical"] == 1
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["file"] == "low.py"
        assert result["gaps"][0]["priority"] == "high"

    def test_untested_collected_separately(self):
        root = _build_coverage_root([("zero.py", 0.0)])
        result = _analyze_coverage_files(root)
        # 0% is both critical AND untested.
        assert "zero.py" in result["untested"]
        assert result["critical"] == 1

    def test_mid_coverage_neither_well_nor_critical(self):
        """50-80% range falls between thresholds."""
        root = _build_coverage_root([("mid.py", 0.65)])
        result = _analyze_coverage_files(root)
        assert result["well_covered"] == 0
        assert result["critical"] == 0

    def test_caps_at_10_each(self):
        # 11 untested files
        root = _build_coverage_root([(f"f{i}.py", 0.0) for i in range(11)])
        result = _analyze_coverage_files(root)
        assert len(result["untested"]) == 10
        assert len(result["gaps"]) == 10
        assert result["total"] == 11


# ---------------------------------------------------------------------------
# _find_test_file() — test file discovery
# ---------------------------------------------------------------------------


class TestFindTestFile:
    def test_init_files_have_no_dedicated_tests(self):
        """__init__.py paths short-circuit to None."""
        assert _find_test_file("src/attune/foo/__init__.py") is None

    def test_finds_test_in_module_unit_dir(self, tmp_path, monkeypatch):
        """src/attune/models/registry.py finds tests/unit/models/test_registry.py."""
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "tests" / "unit" / "models" / "test_registry.py"
        target.parent.mkdir(parents=True)
        target.write_text("def test_x(): pass")

        result = _find_test_file("src/attune/models/registry.py")
        assert result is not None
        assert "test_registry.py" in result

    def test_finds_test_in_standard_unit_dir(self, tmp_path, monkeypatch):
        """Falls back to tests/unit/test_foo.py when no module dir."""
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "tests" / "unit" / "test_foo.py"
        target.parent.mkdir(parents=True)
        target.write_text("def test_x(): pass")

        result = _find_test_file("src/attune/foo.py")
        assert result is not None
        assert "test_foo.py" in result

    def test_returns_none_when_no_match(self, tmp_path, monkeypatch):
        """No matching test file anywhere → None."""
        monkeypatch.chdir(tmp_path)
        # Create empty tests/ dir
        (tmp_path / "tests").mkdir()
        result = _find_test_file("src/attune/nonexistent.py")
        assert result is None

    def test_glob_fallback_finds_deeply_nested(self, tmp_path, monkeypatch):
        """Priority 3: rglob finds test_X.py at arbitrary depth in tests/."""
        monkeypatch.chdir(tmp_path)
        # Put the test file at an unexpected depth — none of the
        # explicit patterns will match, but rglob should find it.
        deep = tmp_path / "tests" / "weird" / "deep" / "test_thing.py"
        deep.parent.mkdir(parents=True)
        deep.write_text("def test_x(): pass")

        result = _find_test_file("src/attune/thing.py")
        assert result is not None
        assert result.endswith("test_thing.py")

    def test_no_tests_directory(self, tmp_path, monkeypatch):
        """No tests/ dir at all → None."""
        monkeypatch.chdir(tmp_path)
        result = _find_test_file("src/attune/foo.py")
        assert result is None


# ---------------------------------------------------------------------------
# _log_file_test() — telemetry logging with graceful degradation
# ---------------------------------------------------------------------------


class TestLogFileTest:
    @patch("attune.workflows.test_runner_helpers.get_telemetry_store")
    def test_logs_to_store(self, mock_store):
        rec = FileTestRecord(
            file_path="src/foo.py",
            timestamp="2026-05-12T00:00:00Z",
            last_test_result="passed",
            test_count=1,
        )
        _log_file_test(rec)
        mock_store.return_value.log_file_test.assert_called_once_with(rec)

    @patch("attune.workflows.test_runner_helpers.get_telemetry_store")
    def test_store_exception_is_swallowed(self, mock_store):
        mock_store.return_value.log_file_test.side_effect = RuntimeError("disk full")
        rec = FileTestRecord(
            file_path="src/foo.py",
            timestamp="2026-05-12T00:00:00Z",
            last_test_result="passed",
            test_count=1,
        )
        # Must NOT raise.
        _log_file_test(rec)
