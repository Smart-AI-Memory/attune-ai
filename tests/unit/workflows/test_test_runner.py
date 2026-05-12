"""Tests for attune.workflows.test_runner — Tier 1 test/coverage tracking.

Mocks `subprocess.run` (would actually run pytest) and
`get_telemetry_store` (would write to disk). All other paths
(pytest output parsing, coverage.xml parsing, FileTestRecord
construction, staleness detection) use real implementations.

Note: this module's filename starts with `test_` because that's
its production name (`workflows/test_runner.py`). The
`*/test_*.py` coverage omit pattern in pyproject.toml does match
it but coverage.xml still reports a measurement, so we treat it
as a normal coverage target.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.test_runner import (
    get_file_test_status,
    get_files_needing_tests,
    run_tests_with_tracking,
    track_coverage,
    track_file_tests,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess:
    """Build a CompletedProcess for mock side_effect."""
    return subprocess.CompletedProcess(
        args=["pytest"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


_PYTEST_PASSING_OUTPUT = """\
============================= test session starts =============================
collected 5 items

tests/unit/sample_test.py .....                                         [100%]

============================= 5 passed in 0.42s ===============================
"""

_PYTEST_FAILING_OUTPUT = """\
============================= test session starts =============================
collected 3 items

tests/unit/sample_test.py .F.                                            [100%]

==================================== FAILURES =================================
________________________________ test_broken _________________________________
def test_broken():
>   assert 1 == 2
E   assert 1 == 2

tests/unit/sample_test.py:5: AssertionError
========================= 1 failed, 2 passed in 0.31s =========================
"""


# ---------------------------------------------------------------------------
# run_tests_with_tracking() — happy + error paths
# ---------------------------------------------------------------------------


class TestRunTestsWithTracking:
    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_default_unit_suite_invokes_pytest(self, mock_run, mock_store):
        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        mock_store.return_value = MagicMock()

        record = run_tests_with_tracking()

        assert record.success is True
        assert record.exit_code == 0
        assert record.passed == 5
        assert record.total_tests == 5
        assert record.test_suite == "unit"
        assert record.triggered_by == "manual"
        # Default command targets tests/unit/
        cmd = mock_run.call_args.args[0]
        assert "pytest" in cmd
        assert "tests/unit/" in cmd
        # Logged to telemetry store
        mock_store.return_value.log_test_execution.assert_called_once_with(record)

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_specific_test_files_used_in_command(self, mock_run, mock_store):
        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        mock_store.return_value = MagicMock()

        record = run_tests_with_tracking(test_files=["tests/foo.py", "tests/bar.py"])

        cmd = mock_run.call_args.args[0]
        assert "tests/foo.py" in cmd
        assert "tests/bar.py" in cmd
        assert record.test_files == ["tests/foo.py", "tests/bar.py"]

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_all_suite_uses_full_pattern(self, mock_run, mock_store):
        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        mock_store.return_value = MagicMock()

        run_tests_with_tracking(test_suite="all")
        cmd = mock_run.call_args.args[0]
        assert "tests/" in cmd

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_custom_command_overrides_defaults(self, mock_run, mock_store):
        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        mock_store.return_value = MagicMock()

        record = run_tests_with_tracking(command="pytest -x tests/specific.py")
        assert record.command == "pytest -x tests/specific.py"

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_failed_tests_parsed(self, mock_run, mock_store):
        mock_run.return_value = _make_completed_process(1, _PYTEST_FAILING_OUTPUT)
        mock_store.return_value = MagicMock()

        record = run_tests_with_tracking()
        assert record.success is False
        assert record.exit_code == 1
        assert record.failed >= 1

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_timeout_recorded_as_exit_124(self, mock_run, mock_store):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=600)
        mock_store.return_value = MagicMock()

        record = run_tests_with_tracking()
        assert record.success is False
        assert record.exit_code == 124
        assert record.errors == 1
        assert any("timeout" in t["name"].lower() for t in record.failed_tests)

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_generic_subprocess_exception(self, mock_run, mock_store):
        mock_run.side_effect = OSError("permission denied")
        mock_store.return_value = MagicMock()

        record = run_tests_with_tracking()
        assert record.success is False
        assert record.exit_code == 1
        assert record.errors == 1
        assert any("execution_error" in t["name"] for t in record.failed_tests)

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner.subprocess.run")
    def test_telemetry_log_failure_swallowed(self, mock_run, mock_store):
        """If logging to the telemetry store raises, the record is
        still returned (the run already happened — logging is
        best-effort).
        """
        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        store = MagicMock()
        store.log_test_execution.side_effect = RuntimeError("disk full")
        mock_store.return_value = store

        record = run_tests_with_tracking()
        assert record.success is True


# ---------------------------------------------------------------------------
# track_coverage() — happy + error paths
# ---------------------------------------------------------------------------


_COVERAGE_XML = """<?xml version="1.0" ?>
<coverage version="7.0" lines-valid="1000" lines-covered="850" branches-valid="200" branches-covered="170" complexity="0" timestamp="123">
  <packages>
    <package name="attune" line-rate="0.85" branch-rate="0.85" complexity="0">
      <classes>
        <class name="example.py" filename="src/attune/example.py" line-rate="0.85" branch-rate="0.85" complexity="0">
          <methods/>
          <lines>
            <line number="1" hits="1"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


class TestTrackCoverage:
    def test_missing_file_raises_filenotfounderror(self, tmp_path):
        missing = tmp_path / "nope.xml"
        with pytest.raises(FileNotFoundError):
            track_coverage(coverage_file=str(missing))

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner._get_previous_coverage", return_value=None)
    def test_happy_path_returns_record(self, mock_prev, mock_store, tmp_path):
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text(_COVERAGE_XML)
        mock_store.return_value = MagicMock()

        record = track_coverage(coverage_file=str(cov_file))

        assert record.overall_percentage == pytest.approx(85.0)
        assert record.lines_total == 1000
        assert record.lines_covered == 850
        assert record.branches_total == 200
        assert record.branches_covered == 170
        assert record.trend == "stable"  # no previous
        mock_store.return_value.log_coverage.assert_called_once_with(record)

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner._get_previous_coverage", return_value=70.0)
    def test_trend_improving(self, mock_prev, mock_store, tmp_path):
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text(_COVERAGE_XML)
        mock_store.return_value = MagicMock()

        record = track_coverage(coverage_file=str(cov_file))
        assert record.trend == "improving"  # 85% vs prior 70%

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner._get_previous_coverage", return_value=95.0)
    def test_trend_declining(self, mock_prev, mock_store, tmp_path):
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text(_COVERAGE_XML)
        mock_store.return_value = MagicMock()

        record = track_coverage(coverage_file=str(cov_file))
        assert record.trend == "declining"  # 85% vs prior 95%

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner._get_previous_coverage", return_value=85.5)
    def test_trend_stable_within_tolerance(self, mock_prev, mock_store, tmp_path):
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text(_COVERAGE_XML)
        mock_store.return_value = MagicMock()

        record = track_coverage(coverage_file=str(cov_file))
        # 85 vs 85.5 → diff 0.5 → within 1.0 tolerance → stable
        assert record.trend == "stable"

    def test_invalid_xml_raises_valueerror(self, tmp_path):
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text("not xml at all")
        with pytest.raises(ValueError, match="Invalid coverage.xml"):
            track_coverage(coverage_file=str(cov_file))

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner._get_previous_coverage", return_value=None)
    def test_zero_lines_yields_zero_percentage(self, mock_prev, mock_store, tmp_path):
        zero_xml = _COVERAGE_XML.replace('lines-valid="1000"', 'lines-valid="0"').replace(
            'lines-covered="850"', 'lines-covered="0"'
        )
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text(zero_xml)
        mock_store.return_value = MagicMock()

        record = track_coverage(coverage_file=str(cov_file))
        assert record.overall_percentage == 0.0

    @patch("attune.workflows.test_runner.get_telemetry_store")
    @patch("attune.workflows.test_runner._get_previous_coverage", return_value=None)
    def test_log_failure_swallowed(self, mock_prev, mock_store, tmp_path):
        cov_file = tmp_path / "coverage.xml"
        cov_file.write_text(_COVERAGE_XML)
        store = MagicMock()
        store.log_coverage.side_effect = RuntimeError("disk full")
        mock_store.return_value = store

        record = track_coverage(coverage_file=str(cov_file))
        # Still returns the parsed record
        assert record.overall_percentage == pytest.approx(85.0)


# ---------------------------------------------------------------------------
# track_file_tests()
# ---------------------------------------------------------------------------


class TestTrackFileTests:
    def test_no_test_file_returns_no_tests_record(self, tmp_path):
        source = tmp_path / "src.py"
        source.write_text("x = 1")
        with patch("attune.workflows.test_runner._log_file_test"):
            record = track_file_tests(source_file=str(source))
        assert record.last_test_result == "no_tests"
        assert record.test_count == 0
        assert record.is_stale is False

    @patch("attune.workflows.test_runner.subprocess.run")
    @patch("attune.workflows.test_runner._log_file_test")
    def test_existing_test_passes(self, mock_log, mock_run, tmp_path):
        source = tmp_path / "src.py"
        source.write_text("x = 1")
        tf = tmp_path / "tests" / "test_src.py"
        tf.parent.mkdir()
        tf.write_text("def test_x(): pass")

        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        record = track_file_tests(source_file=str(source), test_file=str(tf))

        assert record.last_test_result == "passed"
        assert record.test_count == 5
        assert record.failed == 0
        # Both source and test mtimes are recorded
        assert record.source_modified_at is not None
        assert record.tests_modified_at is not None
        mock_log.assert_called_once()

    @patch("attune.workflows.test_runner.subprocess.run")
    @patch("attune.workflows.test_runner._log_file_test")
    def test_failing_tests_classified(self, mock_log, mock_run, tmp_path):
        source = tmp_path / "src.py"
        source.write_text("x = 1")
        tf = tmp_path / "test_src.py"
        tf.write_text("def test_x(): assert False")

        mock_run.return_value = _make_completed_process(1, _PYTEST_FAILING_OUTPUT)
        record = track_file_tests(source_file=str(source), test_file=str(tf))
        assert record.last_test_result == "failed"

    @patch("attune.workflows.test_runner.subprocess.run")
    @patch("attune.workflows.test_runner._log_file_test")
    def test_timeout_recorded_as_error(self, mock_log, mock_run, tmp_path):
        source = tmp_path / "src.py"
        source.write_text("x = 1")
        tf = tmp_path / "test_src.py"
        tf.write_text("def test_x(): pass")

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=300)
        record = track_file_tests(source_file=str(source), test_file=str(tf))
        assert record.last_test_result == "error"
        assert record.errors == 1

    @patch("attune.workflows.test_runner.subprocess.run")
    @patch("attune.workflows.test_runner._log_file_test")
    def test_generic_exception_recorded_as_error(self, mock_log, mock_run, tmp_path):
        source = tmp_path / "src.py"
        source.write_text("x = 1")
        tf = tmp_path / "test_src.py"
        tf.write_text("def test_x(): pass")

        mock_run.side_effect = OSError("file not found")
        record = track_file_tests(source_file=str(source), test_file=str(tf))
        assert record.last_test_result == "error"

    @patch("attune.workflows.test_runner.subprocess.run")
    @patch("attune.workflows.test_runner._log_file_test")
    def test_staleness_when_source_newer_than_test(self, mock_log, mock_run, tmp_path):
        """is_stale=True when source_modified_at > tests_modified_at."""
        source = tmp_path / "src.py"
        source.write_text("x = 1")
        tf = tmp_path / "test_src.py"
        tf.write_text("def test_x(): pass")

        # Make source newer than test (artificially).
        import os

        old = (datetime.now() - timezone.utc.utcoffset(datetime.now())).timestamp() - 86400
        os.utime(str(tf), (old, old))

        mock_run.return_value = _make_completed_process(0, _PYTEST_PASSING_OUTPUT)
        record = track_file_tests(source_file=str(source), test_file=str(tf))
        assert record.is_stale is True


# ---------------------------------------------------------------------------
# get_file_test_status() / get_files_needing_tests() — thin wrappers
# ---------------------------------------------------------------------------


class TestStatusWrappers:
    @patch("attune.workflows.test_runner.get_telemetry_store")
    def test_status_returns_store_value(self, mock_store):
        rec = MagicMock(name="record")
        mock_store.return_value.get_latest_file_test.return_value = rec
        assert get_file_test_status("src/foo.py") is rec
        mock_store.return_value.get_latest_file_test.assert_called_once_with("src/foo.py")

    @patch("attune.workflows.test_runner.get_telemetry_store")
    def test_needing_tests_forwards_filters(self, mock_store):
        mock_store.return_value.get_files_needing_tests.return_value = [1, 2, 3]
        assert get_files_needing_tests(stale_only=True, failed_only=False) == [1, 2, 3]
        mock_store.return_value.get_files_needing_tests.assert_called_once_with(
            stale_only=True, failed_only=False
        )
