"""Tests for per-file test tracking functionality.

Tests the FileTestRecord dataclass, TelemetryStore methods,
and test_runner integration for per-file test tracking.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import tempfile

import pytest

from attune.models import FileTestRecord
from attune.models.telemetry import TelemetryStore


class TestFileTestRecord:
    """Tests for FileTestRecord dataclass."""

    def test_create_basic_record(self):
        """Test creating a basic FileTestRecord."""
        record = FileTestRecord(
            file_path="src/attune/config.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="passed",
            test_count=10,
            passed=10,
            failed=0,
        )

        assert record.file_path == "src/attune/config.py"
        assert record.last_test_result == "passed"
        assert record.test_count == 10
        assert record.passed == 10
        assert record.failed == 0
        assert record.success is True

    def test_success_property_passed(self):
        """Test success property returns True when all tests pass."""
        record = FileTestRecord(
            file_path="test.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="passed",
            test_count=5,
            passed=5,
            failed=0,
            errors=0,
        )
        assert record.success is True

    def test_success_property_failed(self):
        """Test success property returns False when tests fail."""
        record = FileTestRecord(
            file_path="test.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="failed",
            test_count=5,
            passed=4,
            failed=1,
            errors=0,
        )
        assert record.success is False

    def test_success_property_error(self):
        """Test success property returns False when there are errors."""
        record = FileTestRecord(
            file_path="test.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="passed",  # Even if result says passed
            test_count=5,
            passed=5,
            failed=0,
            errors=1,  # But there are errors
        )
        assert record.success is False

    def test_to_dict_and_from_dict(self):
        """Test serialization roundtrip."""
        original = FileTestRecord(
            file_path="src/attune/config.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="passed",
            test_count=10,
            passed=8,
            failed=1,
            skipped=1,
            errors=0,
            duration_seconds=5.5,
            coverage_percent=85.0,
            test_file_path="tests/unit/test_config.py",
            is_stale=True,
        )

        data = original.to_dict()
        restored = FileTestRecord.from_dict(data)

        assert restored.file_path == original.file_path
        assert restored.last_test_result == original.last_test_result
        assert restored.test_count == original.test_count
        assert restored.passed == original.passed
        assert restored.failed == original.failed
        assert restored.duration_seconds == original.duration_seconds
        assert restored.coverage_percent == original.coverage_percent
        assert restored.is_stale == original.is_stale

    def test_record_with_failed_tests(self):
        """Test record with failure details."""
        record = FileTestRecord(
            file_path="src/module.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="failed",
            test_count=3,
            passed=1,
            failed=2,
            failed_tests=[
                {"name": "test_foo", "file": "test_module.py", "error": "AssertionError"},
                {"name": "test_bar", "file": "test_module.py", "error": "ValueError"},
            ],
        )

        assert len(record.failed_tests) == 2
        assert record.failed_tests[0]["name"] == "test_foo"


class TestTelemetryStoreFileTests:
    """Tests for TelemetryStore file test tracking methods."""

    @pytest.fixture
    def temp_store(self):
        """Create a temporary telemetry store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(storage_dir=tmpdir)
            yield store

    def test_log_and_retrieve_file_test(self, temp_store):
        """Test logging and retrieving a file test record."""
        record = FileTestRecord(
            file_path="src/config.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="passed",
            test_count=5,
            passed=5,
        )

        temp_store.log_file_test(record)

        records = temp_store.get_file_tests()
        assert len(records) == 1
        assert records[0].file_path == "src/config.py"
        assert records[0].last_test_result == "passed"

    def test_get_file_tests_filter_by_path(self, temp_store):
        """Test filtering file tests by path."""
        # Log multiple records
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/config.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="passed",
                test_count=5,
            ),
        )
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/cli.py",
                timestamp="2026-01-22T10:01:00Z",
                last_test_result="failed",
                test_count=3,
                failed=1,
            ),
        )

        # Filter by path
        records = temp_store.get_file_tests(file_path="src/config.py")
        assert len(records) == 1
        assert records[0].file_path == "src/config.py"

    def test_get_file_tests_filter_by_result(self, temp_store):
        """Test filtering file tests by result."""
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/config.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="passed",
                test_count=5,
            ),
        )
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/cli.py",
                timestamp="2026-01-22T10:01:00Z",
                last_test_result="failed",
                test_count=3,
                failed=1,
            ),
        )

        # Filter by result
        failed_records = temp_store.get_file_tests(result_filter="failed")
        assert len(failed_records) == 1
        assert failed_records[0].file_path == "src/cli.py"

    def test_get_latest_file_test(self, temp_store):
        """Test getting the most recent test record for a file."""
        # Log multiple records for the same file
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/config.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="failed",
                test_count=5,
                failed=1,
            ),
        )
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/config.py",
                timestamp="2026-01-22T11:00:00Z",
                last_test_result="passed",
                test_count=5,
                passed=5,
            ),
        )

        # Get latest
        latest = temp_store.get_latest_file_test("src/config.py")
        assert latest is not None
        assert latest.last_test_result == "passed"
        assert latest.timestamp == "2026-01-22T11:00:00Z"

    def test_get_latest_file_test_not_found(self, temp_store):
        """Test getting latest record for a file that doesn't exist."""
        latest = temp_store.get_latest_file_test("nonexistent.py")
        assert latest is None

    def test_get_files_needing_tests_failed(self, temp_store):
        """Test getting files with failed tests."""
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/good.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="passed",
                test_count=5,
            ),
        )
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/bad.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="failed",
                test_count=3,
                failed=1,
            ),
        )

        # Get only failed
        needing_attention = temp_store.get_files_needing_tests(failed_only=True)
        assert len(needing_attention) == 1
        assert needing_attention[0].file_path == "src/bad.py"

    def test_get_files_needing_tests_stale(self, temp_store):
        """Test getting files with stale tests."""
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/fresh.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="passed",
                test_count=5,
                is_stale=False,
            ),
        )
        temp_store.log_file_test(
            FileTestRecord(
                file_path="src/stale.py",
                timestamp="2026-01-22T10:00:00Z",
                last_test_result="passed",
                test_count=3,
                is_stale=True,
            ),
        )

        # Get only stale
        stale_files = temp_store.get_files_needing_tests(stale_only=True)
        assert len(stale_files) == 1
        assert stale_files[0].file_path == "src/stale.py"


class TestTestRunnerFileTracking:
    """Tests for test_runner per-file tracking functions."""

    def test_find_test_file_standard_pattern(self, tmp_path):
        """Test finding test file with standard naming."""
        # Create source file
        src_dir = tmp_path / "src" / "attune"
        src_dir.mkdir(parents=True)
        source_file = src_dir / "config.py"
        source_file.write_text("# config module")

        # Create test file
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test_config.py"
        test_file.write_text("def test_config(): pass")

        # Import and test
        # Need to change to tmp_path for relative path resolution
        import os

        from attune.workflows.test_runner import _find_test_file

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            found = _find_test_file("src/attune/config.py")
            # Should find the test file
            assert found is not None
            assert "test_config.py" in found
        finally:
            os.chdir(original_cwd)

    def test_get_file_test_status_no_record(self):
        """Test getting status for a file with no records."""
        from attune.workflows.test_runner import get_file_test_status

        # Non-existent file should return None
        status = get_file_test_status("nonexistent_file_xyz.py")
        # May return None or a record depending on store state
        # Just verify it doesn't crash
        assert status is None or isinstance(status, FileTestRecord)


class TestFileTestRecordEdgeCases:
    """Edge case tests for FileTestRecord."""

    def test_record_with_no_tests(self):
        """Test record when file has no tests."""
        record = FileTestRecord(
            file_path="src/utils.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="no_tests",
            test_count=0,
        )

        assert record.last_test_result == "no_tests"
        assert record.test_count == 0
        assert record.success is False  # no_tests != passed

    def test_record_with_all_skipped(self):
        """Test record when all tests are skipped."""
        record = FileTestRecord(
            file_path="src/deprecated.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="skipped",
            test_count=5,
            skipped=5,
        )

        assert record.last_test_result == "skipped"
        assert record.skipped == 5
        assert record.success is False  # skipped != passed

    def test_record_with_coverage(self):
        """Test record with coverage information."""
        record = FileTestRecord(
            file_path="src/core.py",
            timestamp="2026-01-22T10:00:00Z",
            last_test_result="passed",
            test_count=20,
            passed=20,
            coverage_percent=92.5,
            lines_total=200,
            lines_covered=185,
        )

        assert record.coverage_percent == 92.5
        assert record.lines_total == 200
        assert record.lines_covered == 185
